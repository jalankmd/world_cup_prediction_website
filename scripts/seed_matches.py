# scripts/seed_matches.py
"""
Seed all World Cup 2026 matches into the database.
"""

from datetime import datetime
from app import create_app, db
from app.models import Match

# ---------------------------
# List of World Cup 2026 matches
# ---------------------------
world_cup_2026_matches = [
    # June 11
    {"home_team": "Mexico", "away_team": "South Africa", "match_date": "2026-06-11 15:00"},
    {"home_team": "South Korea", "away_team": "UEFA Path D Winner", "match_date": "2026-06-11 20:00"},

    # June 12
    {"home_team": "Canada", "away_team": "UEFA Path A Winner", "match_date": "2026-06-12 15:00"},
    {"home_team": "USA", "away_team": "Paraguay", "match_date": "2026-06-12 18:00"},

    # June 13
    {"home_team": "Haiti", "away_team": "Scotland", "match_date": "2026-06-13 21:00"},
    {"home_team": "Australia", "away_team": "UEFA Path C Winner", "match_date": "2026-06-13 21:00"},
    {"home_team": "Qatar", "away_team": "Switzerland", "match_date": "2026-06-13 00:01"},
    {"home_team": "Brazil", "away_team": "Morocco", "match_date": "2026-06-13 00:01"},

    # June 14
    {"home_team": "Germany", "away_team": "Curaçao", "match_date": "2026-06-14 00:01"},
    {"home_team": "Netherlands", "away_team": "Japan", "match_date": "2026-06-14 00:01"},
    {"home_team": "Ivory Coast", "away_team": "Ecuador", "match_date": "2026-06-14 00:01"},
    {"home_team": "UEFA Path B Winner", "away_team": "Tunisia", "match_date": "2026-06-14 00:01"},

    # June 15
    {"home_team": "Spain", "away_team": "Cape Verde", "match_date": "2026-06-15 00:01"},
    {"home_team": "Belgium", "away_team": "Egypt", "match_date": "2026-06-15 00:01"},
    {"home_team": "Saudi Arabia", "away_team": "Uruguay", "match_date": "2026-06-15 00:01"},
    {"home_team": "Iran", "away_team": "New Zealand", "match_date": "2026-06-15 00:01"},

    # June 16
    {"home_team": "France", "away_team": "Senegal", "match_date": "2026-06-16 00:01"},
    {"home_team": "UEFA Path 2 Winner", "away_team": "Norway", "match_date": "2026-06-16 00:01"},
    {"home_team": "Argentina", "away_team": "Algeria", "match_date": "2026-06-16 00:01"},
    {"home_team": "Austria", "away_team": "Jordan", "match_date": "2026-06-16 00:01"},

    # June 17
    {"home_team": "Portugal", "away_team": "Uzbekistan", "match_date": "2026-06-17 00:01"},
    {"home_team": "England", "away_team": "Croatia", "match_date": "2026-06-17 00:01"},
    {"home_team": "Ghana", "away_team": "Panama", "match_date": "2026-06-17 00:01"},
    {"home_team": "Uzbekistan", "away_team": "Colombia", "match_date": "2026-06-17 00:01"},

    # June 18
    {"home_team": "UEFA Path D Winner", "away_team": "South Africa", "match_date": "2026-06-18 00:01"},
    {"home_team": "Switzerland", "away_team": "UEFA Path A Winner", "match_date": "2026-06-18 00:01"},
    {"home_team": "Canada", "away_team": "Qatar", "match_date": "2026-06-18 15:00"},
    {"home_team": "Mexico", "away_team": "South Korea", "match_date": "2026-06-18 00:01"},

    # June 19
    {"home_team": "USA", "away_team": "Australia", "match_date": "2026-06-19 00:01"},
    {"home_team": "Scotland", "away_team": "Morocco", "match_date": "2026-06-19 00:01"},
    {"home_team": "Brazil", "away_team": "Haiti", "match_date": "2026-06-19 00:01"},
    {"home_team": "UEFA Path C Winner", "away_team": "Paraguay", "match_date": "2026-06-19 00:01"},

    # June 20
    {"home_team": "Netherlands", "away_team": "UEFA Path B Winner", "match_date": "2026-06-20 00:01"},
    {"home_team": "Germany", "away_team": "Ivory Coast", "match_date": "2026-06-20 18:00"},
    {"home_team": "Ecuador", "away_team": "Curaçao", "match_date": "2026-06-20 00:01"},
    {"home_team": "Tunisia", "away_team": "Japan", "match_date": "2026-06-20 00:01"},

    # June 21
    {"home_team": "Spain", "away_team": "Saudi Arabia", "match_date": "2026-06-21 00:01"},
    {"home_team": "Belgium", "away_team": "Iran", "match_date": "2026-06-21 00:01"},
    {"home_team": "Uruguay", "away_team": "Cape Verde", "match_date": "2026-06-21 00:01"},
    {"home_team": "New Zealand", "away_team": "Egypt", "match_date": "2026-06-21 00:01"},

    # June 22
    {"home_team": "Argentina", "away_team": "Austria", "match_date": "2026-06-22 00:01"},
    {"home_team": "France", "away_team": "UEFA Path 2 Winner", "match_date": "2026-06-22 00:01"},
    {"home_team": "Norway", "away_team": "Senegal", "match_date": "2026-06-22 00:01"},
    {"home_team": "Jordan", "away_team": "Algeria", "match_date": "2026-06-22 00:01"},

    # June 23
    {"home_team": "Portugal", "away_team": "Uzbekistan", "match_date": "2026-06-23 00:01"},
    {"home_team": "England", "away_team": "Ghana", "match_date": "2026-06-23 00:01"},
    {"home_team": "Panama", "away_team": "Croatia", "match_date": "2026-06-23 00:01"},
    {"home_team": "Colombia", "away_team": "UEFA Path 1 Winner", "match_date": "2026-06-23 00:01"},

    # June 24
    {"home_team": "Switzerland", "away_team": "Canada", "match_date": "2026-06-24 15:00"},
    {"home_team": "UEFA Path A Winner", "away_team": "Qatar", "match_date": "2026-06-24 00:01"},
    {"home_team": "Brazil", "away_team": "Scotland", "match_date": "2026-06-24 00:01"},
    {"home_team": "Morocco", "away_team": "Haiti", "match_date": "2026-06-24 00:01"},
    {"home_team": "UEFA Path D Winner", "away_team": "Mexico", "match_date": "2026-06-24 00:01"},
    {"home_team": "South Africa", "away_team": "South Korea", "match_date": "2026-06-24 00:01"},

    # June 25
    {"home_team": "Curaçao", "away_team": "Ivory Coast", "match_date": "2026-06-25 00:01"},
    {"home_team": "Ecuador", "away_team": "Germany", "match_date": "2026-06-25 00:01"},
    {"home_team": "Japan", "away_team": "UEFA Path B Winner", "match_date": "2026-06-25 00:01"},
    {"home_team": "Tunisia", "away_team": "Netherlands", "match_date": "2026-06-25 00:01"},
    {"home_team": "UEFA Path C Winner", "away_team": "USA", "match_date": "2026-06-25 00:01"},
    {"home_team": "Paraguay", "away_team": "Australia", "match_date": "2026-06-25 00:01"},

    # June 26
    {"home_team": "Norway", "away_team": "France", "match_date": "2026-06-26 00:01"},
    {"home_team": "Senegal", "away_team": "UEFA Path 2 Winner", "match_date": "2026-06-26 00:01"},
    {"home_team": "Cape Verde", "away_team": "Saudi Arabia", "match_date": "2026-06-26 00:01"},
    {"home_team": "Uruguay", "away_team": "Spain", "match_date": "2026-06-26 00:01"},
    {"home_team": "Egypt", "away_team": "Iran", "match_date": "2026-06-26 00:01"},
    {"home_team": "New Zealand", "away_team": "Belgium", "match_date": "2026-06-26 00:01"},

    # June 27
    {"home_team": "Panama", "away_team": "England", "match_date": "2026-06-27 00:01"},
    {"home_team": "Croatia", "away_team": "Ghana", "match_date": "2026-06-27 00:01"},
    {"home_team": "Colombia", "away_team": "Portugal", "match_date": "2026-06-27 00:01"},
    {"home_team": "UEFA Path 1 Winner", "away_team": "Uzbekistan", "match_date": "2026-06-27 00:01"},
    {"home_team": "Algeria", "away_team": "Austria", "match_date": "2026-06-27 00:01"},
    {"home_team": "Jordan", "away_team": "Argentina", "match_date": "2026-06-27 00:01"},
]

def seed_matches():
    """Seed matches into the database."""
    for m in world_cup_2026_matches:
        raw_date = m["match_date"]
        # Convert string to datetime object, or None if TBD
        match_date = None if raw_date.upper() == "TBD" else datetime.strptime(raw_date, "%Y-%m-%d %H:%M")
        
        match = Match(
            home_team=m["home_team"],
            away_team=m["away_team"],
            match_date=match_date,
            home_score=None,
            away_score=None
        )
        db.session.add(match)
    
    db.session.commit()
    print(f"Seeded {len(world_cup_2026_matches)} matches into the database!")

# ---------------------------
# Run script standalone
# ---------------------------
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Clear existing matches first
        db.session.query(Match).delete()
        db.session.commit()
        print("Deleted existing matches.")

        # Seed new matches
        seed_matches()