"""Run on every deploy: migrate DB, seed matches, create admin."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Match

app = create_app()

with app.app_context():
    db.create_all()
    # Fix password_hash column if it was created with the old VARCHAR(128) size
    try:
        db.session.execute(db.text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Make email nullable since it's no longer collected at registration
    try:
        db.session.execute(db.text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
        db.session.execute(db.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    if Match.query.count() == 0:
        from scripts.seed_matches import seed_matches, seed_knockout_matches
        seed_matches()
        seed_knockout_matches()

    from scripts.create_admin_account import create_admin
    create_admin()
