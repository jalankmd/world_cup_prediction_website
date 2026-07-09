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

    try:
        db.session.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS favourite_team VARCHAR(50)"))
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

    # ── Round of 32 qualifier columns ─────────────────────────────────────────
    try:
        db.session.execute(db.text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS advancing_team VARCHAR(50)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    try:
        db.session.execute(db.text(
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS predicted_qualifier VARCHAR(50)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # ── Replace TBD knockout matches with actual fixtures ────────────────────────
    # Only for stages whose real fixtures are now in seed_matches.py (R32/R16/QF).
    # Leftover TBD placeholders (and any predictions on them) are removed so the
    # date-based idempotency check in seed_knockout_matches can't collide with them.
    try:
        from app.models import Prediction, OddsPrediction
        tbd_knockouts = Match.query.filter(
            Match.stage.in_(["round_of_32", "round_of_16", "quarter_final"]),
            Match.home_team == "TBD",
        ).all()
        if tbd_knockouts:
            tbd_ids = [m.id for m in tbd_knockouts]
            Prediction.query.filter(Prediction.match_id.in_(tbd_ids)).delete(synchronize_session=False)
            OddsPrediction.query.filter(OddsPrediction.match_id.in_(tbd_ids)).delete(synchronize_session=False)
            Match.query.filter(Match.id.in_(tbd_ids)).delete(synchronize_session=False)
            db.session.commit()
            print(f"Cleared {len(tbd_ids)} TBD knockout matches (R32/R16/QF).")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to clear TBD knockout matches: {e}")

    # ── Seed knockout matches (idempotent — skips slots already present by date) ──
    try:
        from scripts.seed_matches import seed_knockout_matches
        seed_knockout_matches()
    except Exception as e:
        db.session.rollback()
        print(f"seed_knockout_matches failed: {e}")

    # ── Verify quarter-final fixtures (dedupes, fixes dates/teams/stadiums) ──────
    try:
        from scripts.update_qf_teams import update_qf
        update_qf()
    except Exception as e:
        db.session.rollback()
        print(f"update_qf failed: {e}")

    # ── Fix match group_name assignments (groups C/D, G/H, K/L were wrong) ──────
    group_fixes = {
        "C": ("Brazil", "Morocco", "Haiti", "Scotland"),
        "D": ("USA", "Paraguay", "Australia", "Turkey"),
        "G": ("Belgium", "Egypt", "Iran", "New Zealand"),
        "H": ("Spain", "Cape Verde", "Saudi Arabia", "Uruguay"),
        "K": ("Portugal", "Uzbekistan", "Colombia", "DR Congo"),
        "L": ("England", "Croatia", "Ghana", "Panama"),
    }
    for grp, teams in group_fixes.items():
        placeholders = ", ".join(f"'{t}'" for t in teams)
        try:
            db.session.execute(db.text(
                f"UPDATE matches SET group_name = '{grp}' WHERE home_team IN ({placeholders})"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # ── Fix duplicate Portugal vs Uzbekistan (June 17 should be Portugal vs DR Congo) ──
    # The seed file incorrectly had Portugal vs Uzbekistan twice (Jun 17 + Jun 23).
    # Fix: rename the lower-ID duplicate to Portugal vs DR Congo.
    try:
        db.session.execute(db.text("""
            UPDATE matches
            SET home_team = 'Portugal', away_team = 'DR Congo'
            WHERE id = (
                SELECT MIN(id) FROM matches
                WHERE home_team = 'Portugal' AND away_team = 'Uzbekistan'
                  AND (SELECT COUNT(*) FROM matches WHERE home_team = 'Portugal' AND away_team = 'Uzbekistan') > 1
            )
        """))
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

    # ── Fix all group-stage kickoff times (UTC) ────────────────────────────────
    # All times converted from official ET schedule (EDT = UTC-4).
    # Idempotent: safe to run on every deploy.
    match_times = [
        # Group A
        ("Mexico",                  "South Africa",      "2026-06-11 19:00:00"),
        ("South Korea",             "Czech Republic",    "2026-06-12 02:00:00"),
        ("Czech Republic",          "South Africa",      "2026-06-18 16:00:00"),
        ("Mexico",                  "South Korea",       "2026-06-19 01:00:00"),
        ("Czech Republic",          "Mexico",            "2026-06-25 01:00:00"),
        ("South Africa",            "South Korea",       "2026-06-25 01:00:00"),
        # Group B
        ("Canada",                  "Bosnia and Herzegovina", "2026-06-12 19:00:00"),
        ("Qatar",                   "Switzerland",       "2026-06-13 19:00:00"),
        ("Switzerland",             "Bosnia and Herzegovina", "2026-06-18 19:00:00"),
        ("Canada",                  "Qatar",             "2026-06-18 22:00:00"),
        ("Switzerland",             "Canada",            "2026-06-24 19:00:00"),
        ("Bosnia and Herzegovina",  "Qatar",             "2026-06-24 19:00:00"),
        # Group C
        ("USA",                     "Paraguay",          "2026-06-13 01:00:00"),
        ("Australia",               "Turkey",            "2026-06-14 04:00:00"),
        ("USA",                     "Australia",         "2026-06-19 19:00:00"),
        ("Turkey",                  "Paraguay",          "2026-06-20 04:00:00"),
        ("Turkey",                  "USA",               "2026-06-25 17:00:00"),
        ("Paraguay",                "Australia",         "2026-06-25 17:00:00"),
        # Group D
        ("Brazil",                  "Morocco",           "2026-06-13 22:00:00"),
        ("Haiti",                   "Scotland",          "2026-06-14 01:00:00"),
        ("Scotland",                "Morocco",           "2026-06-19 22:00:00"),
        ("Brazil",                  "Haiti",             "2026-06-20 01:00:00"),
        ("Brazil",                  "Scotland",          "2026-06-24 22:00:00"),
        ("Morocco",                 "Haiti",             "2026-06-24 22:00:00"),
        # Group E
        ("Germany",                 "Curaçao",           "2026-06-14 17:00:00"),
        ("Ivory Coast",             "Ecuador",           "2026-06-14 23:00:00"),
        ("Germany",                 "Ivory Coast",       "2026-06-20 20:00:00"),
        ("Ecuador",                 "Curaçao",           "2026-06-21 00:00:00"),
        ("Ecuador",                 "Germany",           "2026-06-25 20:00:00"),
        ("Curaçao",                 "Ivory Coast",       "2026-06-25 20:00:00"),
        # Group F
        ("Netherlands",             "Japan",             "2026-06-14 20:00:00"),
        ("Sweden",                  "Tunisia",           "2026-06-15 02:00:00"),
        ("Netherlands",             "Sweden",            "2026-06-20 17:00:00"),
        ("Tunisia",                 "Japan",             "2026-06-21 04:00:00"),
        ("Japan",                   "Sweden",            "2026-06-25 23:00:00"),
        ("Tunisia",                 "Netherlands",       "2026-06-25 23:00:00"),
        # Group G
        ("Spain",                   "Cape Verde",        "2026-06-15 16:00:00"),
        ("Belgium",                 "Egypt",             "2026-06-15 19:00:00"),
        ("Spain",                   "Belgium",           "2026-06-21 16:00:00"),
        ("Cape Verde",              "Egypt",             "2026-06-21 19:00:00"),
        ("Uruguay",                 "Cape Verde",        "2026-06-21 22:00:00"),
        ("New Zealand",             "Egypt",             "2026-06-22 01:00:00"),
        ("Cape Verde",              "Saudi Arabia",      "2026-06-27 00:00:00"),
        ("Uruguay",                 "Spain",             "2026-06-27 00:00:00"),
        ("Egypt",                   "Iran",              "2026-06-27 03:00:00"),
        ("New Zealand",             "Belgium",           "2026-06-27 03:00:00"),
        # Group H
        ("Saudi Arabia",            "Uruguay",           "2026-06-15 22:00:00"),
        ("Iran",                    "New Zealand",       "2026-06-16 01:00:00"),
        ("Spain",                   "Saudi Arabia",      "2026-06-21 16:00:00"),
        ("Belgium",                 "Iran",              "2026-06-21 19:00:00"),
        # Group I
        ("France",                  "Senegal",           "2026-06-16 19:00:00"),
        ("Iraq",                    "Norway",            "2026-06-16 22:00:00"),
        ("France",                  "Iraq",              "2026-06-22 21:00:00"),
        ("Norway",                  "Senegal",           "2026-06-23 00:00:00"),
        ("Norway",                  "France",            "2026-06-26 19:00:00"),
        ("Senegal",                 "Iraq",              "2026-06-26 19:00:00"),
        # Group J
        ("Argentina",               "Algeria",           "2026-06-17 01:00:00"),
        ("Austria",                 "Jordan",            "2026-06-17 04:00:00"),
        ("Argentina",               "Austria",           "2026-06-22 17:00:00"),
        ("Jordan",                  "Algeria",           "2026-06-23 03:00:00"),
        ("Algeria",                 "Austria",           "2026-06-28 02:00:00"),
        ("Jordan",                  "Argentina",         "2026-06-28 02:00:00"),
        # Group K
        ("England",                 "Croatia",           "2026-06-17 20:00:00"),
        ("Ghana",                   "Panama",            "2026-06-17 23:00:00"),
        ("England",                 "Ghana",             "2026-06-23 20:00:00"),
        ("Panama",                  "Croatia",           "2026-06-23 23:00:00"),
        ("Panama",                  "England",           "2026-06-27 21:00:00"),
        ("Croatia",                 "Ghana",             "2026-06-27 21:00:00"),
        # Group L
        ("Portugal",                "DR Congo",          "2026-06-17 17:00:00"),
        ("Uzbekistan",              "Colombia",          "2026-06-18 02:00:00"),
        ("Portugal",                "Uzbekistan",        "2026-06-23 17:00:00"),
        ("Colombia",                "DR Congo",          "2026-06-24 02:00:00"),
        ("Colombia",                "Portugal",          "2026-06-27 23:30:00"),
        ("DR Congo",                "Uzbekistan",        "2026-06-27 23:30:00"),
    ]
    for home, away, utc_str in match_times:
        try:
            db.session.execute(db.text(
                "UPDATE matches SET match_date = :dt WHERE home_team = :home AND away_team = :away"
            ), {"dt": utc_str, "home": home, "away": away})
            db.session.commit()
        except Exception:
            db.session.rollback()
