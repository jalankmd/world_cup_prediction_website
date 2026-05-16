"""Run on every deploy: migrate DB, seed matches, create admin."""

from app import create_app, db
from app.models import Match
from flask_migrate import upgrade

app = create_app()

with app.app_context():
    upgrade()

    if Match.query.count() == 0:
        from scripts.seed_matches import seed_matches, seed_knockout_matches
        seed_matches()
        seed_knockout_matches()

    from scripts.create_admin_account import create_admin
    create_admin()
