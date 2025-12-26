# seed_matches.py
from app import app, db
from models import Match
from datetime import datetime

# List of sample matches
world_cup_2026_matches = [
    # June 11
    {"home_team": "Mexico", "away_team": "South Africa", "match_date": "2025-06-11 15:00"},  # local MX time but convert: Mexico City is UTC−5 → 16:00 in Toronto
    {"home_team": "South Korea", "away_team": "UEFA Path D Winner", "match_date": "2026-06-11 20:00"},  # local MX time → 21:00 Toronto

    # June 12
    {"home_team": "Canada", "away_team": "UEFA Path A Winner", "match_date": "2026-06-12 15:00"},  # BMO Field, Toronto (given in source) :contentReference[oaicite:2]{index=2}
    {"home_team": "USA", "away_team": "Paraguay", "match_date": "2026-06-12 18:00"},  # Los Angeles 18:00 local → 21:00 Toronto

    # June 13
    {"home_team": "Haiti", "away_team": "Scotland", "match_date": "2026-06-13 21:00"},  # Boston 21:00 local → 22:00 Toronto
    {"home_team": "Australia", "away_team": "UEFA Path C Winner", "match_date": "2026-06-13 21:00"},  # Vancouver 21:00 local → 00:00 next day Toronto
    {"home_team": "Qatar", "away_team": "Switzerland", "match_date": "2026-06-13 TBD"},  # San Francisco local → TBD in Toronto
    {"home_team": "Brazil", "away_team": "Morocco", "match_date": "2026-06-13 TBD"},  # New York local → TBD in Toronto

    # June 14
    {"home_team": "Germany", "away_team": "Curaçao", "match_date": "2026-06-14 TBD"},
    {"home_team": "Netherlands", "away_team": "Japan", "match_date": "2026-06-14 TBD"},
    {"home_team": "Ivory Coast", "away_team": "Ecuador", "match_date": "2026-06-14 TBD"},
    {"home_team": "UEFA Path B Winner", "away_team": "Tunisia", "match_date": "2026-06-14 TBD"},

    # June 15
    {"home_team": "Spain", "away_team": "Cape Verde", "match_date": "2026-06-15 TBD"},
    {"home_team": "Belgium", "away_team": "Egypt", "match_date": "2026-06-15 TBD"},
    {"home_team": "Saudi Arabia", "away_team": "Uruguay", "match_date": "2026-06-15 TBD"},
    {"home_team": "Iran", "away_team": "New Zealand", "match_date": "2026-06-15 TBD"},

    # June 16
    {"home_team": "France", "away_team": "Senegal", "match_date": "2026-06-16 TBD"},
    {"home_team": "UEFA Path 2 Winner", "away_team": "Norway", "match_date": "2026-06-16 TBD"},
    {"home_team": "Argentina", "away_team": "Algeria", "match_date": "2026-06-16 TBD"},
    {"home_team": "Austria", "away_team": "Jordan", "match_date": "2026-06-16 TBD"},

    # June 17
    {"home_team": "Portugal", "away_team": "Uzbekistan", "match_date": "2026-06-17 TBD"},
    {"home_team": "England", "away_team": "Croatia", "match_date": "2026-06-17 TBD"},
    {"home_team": "Ghana", "away_team": "Panama", "match_date": "2026-06-17 TBD"},
    {"home_team": "Uzbekistan", "away_team": "Colombia", "match_date": "2026-06-17 TBD"},

    # June 18
    {"home_team": "UEFA Path D Winner", "away_team": "South Africa", "match_date": "2026-06-18 TBD"},
    {"home_team": "Switzerland", "away_team": "UEFA Path A Winner", "match_date": "2026-06-18 TBD"},
    {"home_team": "Canada", "away_team": "Qatar", "match_date": "2026-06-18 15:00"},  # Vancouver local 15:00 → 18:00 Toronto :contentReference[oaicite:3]{index=3}
    {"home_team": "Mexico", "away_team": "South Korea", "match_date": "2026-06-18 TBD"},

    # June 19
    {"home_team": "USA", "away_team": "Australia", "match_date": "2026-06-19 TBD"},
    {"home_team": "Scotland", "away_team": "Morocco", "match_date": "2026-06-19 TBD"},
    {"home_team": "Brazil", "away_team": "Haiti", "match_date": "2026-06-19 TBD"},
    {"home_team": "UEFA Path C Winner", "away_team": "Paraguay", "match_date": "2026-06-19 TBD"},

    # June 20
    {"home_team": "Netherlands", "away_team": "UEFA Path B Winner", "match_date": "2026-06-20 TBD"},
    {"home_team": "Germany", "away_team": "Ivory Coast", "match_date": "2026-06-20 18:00"},  # Toronto local (from Reddit) :contentReference[oaicite:4]{index=4}
    {"home_team": "Ecuador", "away_team": "Curaçao", "match_date": "2026-06-20 TBD"},
    {"home_team": "Tunisia", "away_team": "Japan", "match_date": "2026-06-20 TBD"},

    # June 21
    {"home_team": "Spain", "away_team": "Saudi Arabia", "match_date": "2026-06-21 TBD"},
    {"home_team": "Belgium", "away_team": "Iran", "match_date": "2026-06-21 TBD"},
    {"home_team": "Uruguay", "away_team": "Cape Verde", "match_date": "2026-06-21 TBD"},
    {"home_team": "New Zealand", "away_team": "Egypt", "match_date": "2026-06-21 TBD"},

    # June 22
    {"home_team": "Argentina", "away_team": "Austria", "match_date": "2026-06-22 TBD"},
    {"home_team": "France", "away_team": "UEFA Path 2 Winner", "match_date": "2026-06-22 TBD"},
    {"home_team": "Norway", "away_team": "Senegal", "match_date": "2026-06-22 TBD"},
    {"home_team": "Jordan", "away_team": "Algeria", "match_date": "2026-06-22 TBD"},

    # June 23
    {"home_team": "Portugal", "away_team": "Uzbekistan", "match_date": "2026-06-23 TBD"},
    {"home_team": "England", "away_team": "Ghana", "match_date": "2026-06-23 TBD"},
    {"home_team": "Panama", "away_team": "Croatia", "match_date": "2026-06-23 TBD"},
    {"home_team": "Colombia", "away_team": "UEFA Path 1 Winner", "match_date": "2026-06-23 TBD"},

    # June 24
    {"home_team": "Switzerland", "away_team": "Canada", "match_date": "2025-06-24 15:00"},  # Vancouver → 18:00 Toronto :contentReference[oaicite:5]{index=5}
    {"home_team": "UEFA Path A Winner", "away_team": "Qatar", "match_date": "2026-06-24 TBD"},
    {"home_team": "Brazil", "away_team": "Scotland", "match_date": "2026-06-24 TBD"},
    {"home_team": "Morocco", "away_team": "Haiti", "match_date": "2026-06-24 TBD"},
    {"home_team": "UEFA Path D Winner", "away_team": "Mexico", "match_date": "2026-06-24 TBD"},
    {"home_team": "South Africa", "away_team": "South Korea", "match_date": "2026-06-24 TBD"},

    # June 25
    {"home_team": "Curaçao", "away_team": "Ivory Coast", "match_date": "2026-06-25 TBD"},
    {"home_team": "Ecuador", "away_team": "Germany", "match_date": "2026-06-25 TBD"},
    {"home_team": "Japan", "away_team": "UEFA Path B Winner", "match_date": "2026-06-25 TBD"},
    {"home_team": "Tunisia", "away_team": "Netherlands", "match_date": "2026-06-25 TBD"},
    {"home_team": "UEFA Path C Winner", "away_team": "USA", "match_date": "2026-06-25 TBD"},
    {"home_team": "Paraguay", "away_team": "Australia", "match_date": "2026-06-25 TBD"},

    # June 26
    {"home_team": "Norway", "away_team": "France", "match_date": "2026-06-26 TBD"},
    {"home_team": "Senegal", "away_team": "UEFA Path 2 Winner", "match_date": "2026-06-26 TBD"},
    {"home_team": "Cape Verde", "away_team": "Saudi Arabia", "match_date": "2026-06-26 TBD"},
    {"home_team": "Uruguay", "away_team": "Spain", "match_date": "2026-06-26 TBD"},
    {"home_team": "Egypt", "away_team": "Iran", "match_date": "2026-06-26 TBD"},
    {"home_team": "New Zealand", "away_team": "Belgium", "match_date": "2026-06-26 TBD"},

    # June 27
    {"home_team": "Panama", "away_team": "England", "match_date": "2026-06-27 TBD"},
    {"home_team": "Croatia", "away_team": "Ghana", "match_date": "2026-06-27 TBD"},
    {"home_team": "Colombia", "away_team": "Portugal", "match_date": "2026-06-27 TBD"},
    {"home_team": "UEFA Path 1 Winner", "away_team": "Uzbekistan", "match_date": "2026-06-27 TBD"},
    {"home_team": "Algeria", "away_team": "Austria", "match_date": "2026-06-27 TBD"},
    {"home_team": "Jordan", "away_team": "Argentina", "match_date": "2026-06-27 TBD"},
]

with app.app_context():
    # Delete all existing matches first
    db.session.query(Match).delete()
    db.session.commit()  # Commit deletion

    # Add new matches
    for m in world_cup_2026_matches:
        raw_date = m["match_date"]
        if "TBD" in raw_date:
            match_date = None
        else:
            match_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M")

        match = Match(
            home_team=m["home_team"],
            away_team=m["away_team"],
            match_date=match_date,
            home_score=None,
            away_score=None
        )
        db.session.add(match)

    db.session.commit()  # Commit all new matches
    print(f"Seeded {len(world_cup_2026_matches)} matches into the database!")