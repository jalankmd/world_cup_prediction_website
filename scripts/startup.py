"""Run on every deploy: migrate DB, seed matches, create admin."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Match

app = create_app()

with app.app_context():
    # Create any tables that don't exist yet (safe — never drops existing tables)
    db.create_all()

    # ── Legacy column fixes ────────────────────────────────────────────────────
    try:
        db.session.execute(db.text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
        db.session.execute(db.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Multi-competition: competition_id on prediction tables ─────────────────

    # competitions.entry_fee
    try:
        db.session.execute(db.text(
            "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS entry_fee FLOAT NOT NULL DEFAULT 0.0"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # predictions.competition_id
    try:
        db.session.execute(db.text(
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS competition_id INTEGER REFERENCES competitions(id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # odds_predictions.competition_id
    try:
        db.session.execute(db.text(
            "ALTER TABLE odds_predictions ADD COLUMN IF NOT EXISTS competition_id INTEGER REFERENCES competitions(id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # group_qualifier_predictions.competition_id
    try:
        db.session.execute(db.text(
            "ALTER TABLE group_qualifier_predictions ADD COLUMN IF NOT EXISTS competition_id INTEGER REFERENCES competitions(id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # podium_predictions.competition_id
    try:
        db.session.execute(db.text(
            "ALTER TABLE podium_predictions ADD COLUMN IF NOT EXISTS competition_id INTEGER REFERENCES competitions(id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Populate competition_id from user's primary competition ────────────────

    for table in ("predictions", "odds_predictions", "group_qualifier_predictions", "podium_predictions"):
        try:
            db.session.execute(db.text(f"""
                UPDATE {table} SET competition_id = (
                    SELECT competition_id FROM users WHERE users.id = {table}.user_id
                ) WHERE competition_id IS NULL
            """))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # ── Populate user_competitions M2M table ───────────────────────────────────
    try:
        db.session.execute(db.text("""
            INSERT INTO user_competitions (user_id, competition_id)
            SELECT id, competition_id FROM users WHERE competition_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Update unique constraints on prediction tables ─────────────────────────
    # Drop old (user_id, match_id) constraints and add (user_id, match_id, competition_id)

    try:
        db.session.execute(db.text("ALTER TABLE predictions DROP CONSTRAINT IF EXISTS unique_user_match"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text(
            "ALTER TABLE predictions ADD CONSTRAINT unique_user_match_comp UNIQUE (user_id, match_id, competition_id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text("ALTER TABLE odds_predictions DROP CONSTRAINT IF EXISTS unique_user_match_odds"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text(
            "ALTER TABLE odds_predictions ADD CONSTRAINT unique_user_match_comp_odds UNIQUE (user_id, match_id, competition_id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text("ALTER TABLE group_qualifier_predictions DROP CONSTRAINT IF EXISTS unique_user_group_pick"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text(
            "ALTER TABLE group_qualifier_predictions ADD CONSTRAINT unique_user_group_pick_comp UNIQUE (user_id, group_name, competition_id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # podium_predictions: drop old single-column unique on user_id, add compound unique
    try:
        db.session.execute(db.text("ALTER TABLE podium_predictions DROP CONSTRAINT IF EXISTS podium_predictions_user_id_key"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text("ALTER TABLE podium_predictions DROP CONSTRAINT IF EXISTS unique_user_comp_podium"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text(
            "ALTER TABLE podium_predictions ADD CONSTRAINT unique_user_comp_podium UNIQUE (user_id, competition_id)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Seed matches and create admin ──────────────────────────────────────────
    if Match.query.count() == 0:
        from scripts.seed_matches import seed_matches, seed_knockout_matches
        seed_matches()
        seed_knockout_matches()

    from scripts.create_admin_account import create_admin
    create_admin()
