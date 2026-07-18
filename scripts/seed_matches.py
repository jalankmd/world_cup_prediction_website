# scripts/seed_matches.py
"""
Seed all World Cup 2026 matches into the database.
"""

from datetime import datetime
from app import create_app, db
from app.models import Match

TEAM_TO_GROUP = {
    "Mexico": "A", "South Africa": "A", "South Korea": "A", "Czech Republic": "A",
    "Canada": "B", "Bosnia and Herzegovina": "B", "Qatar": "B", "Switzerland": "B",
    "Brazil": "C", "Morocco": "C", "Haiti": "C", "Scotland": "C",
    "USA": "D", "Paraguay": "D", "Australia": "D", "Turkey": "D",
    "Germany": "E", "Curaçao": "E", "Ivory Coast": "E", "Ecuador": "E",
    "Netherlands": "F", "Japan": "F", "Sweden": "F", "Tunisia": "F",
    "Belgium": "G", "Egypt": "G", "Iran": "G", "New Zealand": "G",
    "Spain": "H", "Cape Verde": "H", "Saudi Arabia": "H", "Uruguay": "H",
    "France": "I", "Senegal": "I", "Iraq": "I", "Norway": "I",
    "Argentina": "J", "Algeria": "J", "Austria": "J", "Jordan": "J",
    "Portugal": "K", "Uzbekistan": "K", "Colombia": "K", "DR Congo": "K",
    "England": "L", "Croatia": "L", "Ghana": "L", "Panama": "L",
}

# ---------------------------
# List of World Cup 2026 matches
# ---------------------------
world_cup_2026_matches = [
    # June 11
    {"home_team": "Mexico", "away_team": "South Africa", "match_date": "2026-06-11 15:00"},
    {"home_team": "South Korea", "away_team": "Czech Republic", "match_date": "2026-06-11 20:00"},

    # June 12
    {"home_team": "Canada", "away_team": "Bosnia and Herzegovina", "match_date": "2026-06-12 15:00"},
    {"home_team": "USA", "away_team": "Paraguay", "match_date": "2026-06-12 18:00"},

    # June 13
    {"home_team": "Haiti", "away_team": "Scotland", "match_date": "2026-06-13 21:00"},
    {"home_team": "Australia", "away_team": "Turkey", "match_date": "2026-06-13 21:00"},
    {"home_team": "Qatar", "away_team": "Switzerland", "match_date": "2026-06-13 00:01"},
    {"home_team": "Brazil", "away_team": "Morocco", "match_date": "2026-06-13 00:01"},

    # June 14
    {"home_team": "Germany", "away_team": "Curaçao", "match_date": "2026-06-14 00:01"},
    {"home_team": "Netherlands", "away_team": "Japan", "match_date": "2026-06-14 00:01"},
    {"home_team": "Ivory Coast", "away_team": "Ecuador", "match_date": "2026-06-14 00:01"},
    {"home_team": "Sweden", "away_team": "Tunisia", "match_date": "2026-06-14 00:01"},

    # June 15
    {"home_team": "Spain", "away_team": "Cape Verde", "match_date": "2026-06-15 00:01"},
    {"home_team": "Belgium", "away_team": "Egypt", "match_date": "2026-06-15 00:01"},
    {"home_team": "Saudi Arabia", "away_team": "Uruguay", "match_date": "2026-06-15 00:01"},
    {"home_team": "Iran", "away_team": "New Zealand", "match_date": "2026-06-15 00:01"},

    # June 16
    {"home_team": "France", "away_team": "Senegal", "match_date": "2026-06-16 00:01"},
    {"home_team": "Iraq", "away_team": "Norway", "match_date": "2026-06-16 00:01"},
    {"home_team": "Argentina", "away_team": "Algeria", "match_date": "2026-06-16 00:01"},
    {"home_team": "Austria", "away_team": "Jordan", "match_date": "2026-06-16 00:01"},

    # June 17
    {"home_team": "Portugal", "away_team": "DR Congo", "match_date": "2026-06-17 00:01"},
    {"home_team": "England", "away_team": "Croatia", "match_date": "2026-06-17 00:01"},
    {"home_team": "Ghana", "away_team": "Panama", "match_date": "2026-06-17 00:01"},
    {"home_team": "Uzbekistan", "away_team": "Colombia", "match_date": "2026-06-17 00:01"},

    # June 18
    {"home_team": "Czech Republic", "away_team": "South Africa", "match_date": "2026-06-18 00:01"},
    {"home_team": "Switzerland", "away_team": "Bosnia and Herzegovina", "match_date": "2026-06-18 00:01"},
    {"home_team": "Canada", "away_team": "Qatar", "match_date": "2026-06-18 15:00"},
    {"home_team": "Mexico", "away_team": "South Korea", "match_date": "2026-06-18 00:01"},

    # June 19
    {"home_team": "USA", "away_team": "Australia", "match_date": "2026-06-19 00:01"},
    {"home_team": "Scotland", "away_team": "Morocco", "match_date": "2026-06-19 00:01"},
    {"home_team": "Brazil", "away_team": "Haiti", "match_date": "2026-06-19 00:01"},
    {"home_team": "Turkey", "away_team": "Paraguay", "match_date": "2026-06-19 00:01"},

    # June 20
    {"home_team": "Netherlands", "away_team": "Sweden", "match_date": "2026-06-20 00:01"},
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
    {"home_team": "France", "away_team": "Iraq", "match_date": "2026-06-22 00:01"},
    {"home_team": "Norway", "away_team": "Senegal", "match_date": "2026-06-22 00:01"},
    {"home_team": "Jordan", "away_team": "Algeria", "match_date": "2026-06-22 00:01"},

    # June 23
    {"home_team": "Portugal", "away_team": "Uzbekistan", "match_date": "2026-06-23 00:01"},
    {"home_team": "England", "away_team": "Ghana", "match_date": "2026-06-23 00:01"},
    {"home_team": "Panama", "away_team": "Croatia", "match_date": "2026-06-23 00:01"},
    {"home_team": "Colombia", "away_team": "DR Congo", "match_date": "2026-06-23 00:01"},

    # June 24
    {"home_team": "Switzerland", "away_team": "Canada", "match_date": "2026-06-24 15:00"},
    {"home_team": "Bosnia and Herzegovina", "away_team": "Qatar", "match_date": "2026-06-24 00:01"},
    {"home_team": "Brazil", "away_team": "Scotland", "match_date": "2026-06-24 00:01"},
    {"home_team": "Morocco", "away_team": "Haiti", "match_date": "2026-06-24 00:01"},
    {"home_team": "Czech Republic", "away_team": "Mexico", "match_date": "2026-06-24 00:01"},
    {"home_team": "South Africa", "away_team": "South Korea", "match_date": "2026-06-24 00:01"},

    # June 25
    {"home_team": "Curaçao", "away_team": "Ivory Coast", "match_date": "2026-06-25 00:01"},
    {"home_team": "Ecuador", "away_team": "Germany", "match_date": "2026-06-25 00:01"},
    {"home_team": "Japan", "away_team": "Sweden", "match_date": "2026-06-25 00:01"},
    {"home_team": "Tunisia", "away_team": "Netherlands", "match_date": "2026-06-25 00:01"},
    {"home_team": "Turkey", "away_team": "USA", "match_date": "2026-06-25 00:01"},
    {"home_team": "Paraguay", "away_team": "Australia", "match_date": "2026-06-25 00:01"},

    # June 26
    {"home_team": "Norway", "away_team": "France", "match_date": "2026-06-26 00:01"},
    {"home_team": "Senegal", "away_team": "Iraq", "match_date": "2026-06-26 00:01"},
    {"home_team": "Cape Verde", "away_team": "Saudi Arabia", "match_date": "2026-06-26 00:01"},
    {"home_team": "Uruguay", "away_team": "Spain", "match_date": "2026-06-26 00:01"},
    {"home_team": "Egypt", "away_team": "Iran", "match_date": "2026-06-26 00:01"},
    {"home_team": "New Zealand", "away_team": "Belgium", "match_date": "2026-06-26 00:01"},

    # June 27
    {"home_team": "Panama", "away_team": "England", "match_date": "2026-06-27 00:01"},
    {"home_team": "Croatia", "away_team": "Ghana", "match_date": "2026-06-27 00:01"},
    {"home_team": "Colombia", "away_team": "Portugal", "match_date": "2026-06-27 00:01"},
    {"home_team": "DR Congo", "away_team": "Uzbekistan", "match_date": "2026-06-27 00:01"},
    {"home_team": "Algeria", "away_team": "Austria", "match_date": "2026-06-27 00:01"},
    {"home_team": "Jordan", "away_team": "Argentina", "match_date": "2026-06-27 00:01"},
]

# ---------------------------
# Knockout stage fixtures
# Teams are TBD until group stage completes.
# Stages use values recognised by scoring.py _stage_bonus().
# ---------------------------
knockout_matches = [
    # Round of 32 – June 28 – July 3 2026 (all times UTC, EDT+4)
    {"home_team": "South Africa",          "away_team": "Canada",                  "match_date": "2026-06-28 19:00", "stage": "round_of_32"},  # 3pm ET Jun 28
    {"home_team": "Brazil",                "away_team": "Japan",                   "match_date": "2026-06-29 17:00", "stage": "round_of_32"},  # 1pm ET Jun 29
    {"home_team": "Germany",               "away_team": "Paraguay",                "match_date": "2026-06-29 20:30", "stage": "round_of_32"},  # 4:30pm ET Jun 29
    {"home_team": "Netherlands",           "away_team": "Morocco",                 "match_date": "2026-06-30 01:00", "stage": "round_of_32"},  # 9pm ET Jun 29
    {"home_team": "Ivory Coast",           "away_team": "Norway",                  "match_date": "2026-06-30 17:00", "stage": "round_of_32"},  # 1pm ET Jun 30
    {"home_team": "France",                "away_team": "Sweden",                  "match_date": "2026-06-30 21:00", "stage": "round_of_32"},  # 5pm ET Jun 30
    {"home_team": "Mexico",                "away_team": "Ecuador",                 "match_date": "2026-07-01 01:00", "stage": "round_of_32"},  # 9pm ET Jun 30
    {"home_team": "England",               "away_team": "DR Congo",                "match_date": "2026-07-01 16:00", "stage": "round_of_32"},  # 12pm ET Jul 1
    {"home_team": "Belgium",               "away_team": "Senegal",                 "match_date": "2026-07-01 20:00", "stage": "round_of_32"},  # 4pm ET Jul 1
    {"home_team": "USA",                   "away_team": "Bosnia and Herzegovina",  "match_date": "2026-07-02 00:00", "stage": "round_of_32"},  # 8pm ET Jul 1
    {"home_team": "Spain",                 "away_team": "Austria",                 "match_date": "2026-07-02 19:00", "stage": "round_of_32"},  # 3pm ET Jul 2
    {"home_team": "Portugal",              "away_team": "Croatia",                 "match_date": "2026-07-02 23:00", "stage": "round_of_32"},  # 7pm ET Jul 2
    {"home_team": "Switzerland",           "away_team": "Algeria",                 "match_date": "2026-07-03 03:00", "stage": "round_of_32"},  # 11pm ET Jul 2
    {"home_team": "Australia",             "away_team": "Egypt",                   "match_date": "2026-07-03 18:00", "stage": "round_of_32"},  # 2pm ET Jul 3
    {"home_team": "Argentina",             "away_team": "Cape Verde",              "match_date": "2026-07-03 22:00", "stage": "round_of_32"},  # 6pm ET Jul 3
    {"home_team": "Colombia",              "away_team": "Ghana",                   "match_date": "2026-07-04 01:30", "stage": "round_of_32"},  # 9:30pm ET Jul 3

    # Round of 16 – July 4-7 2026 (8 matches, times UTC)
    {"home_team": "Morocco",   "away_team": "Canada",      "match_date": "2026-07-04 17:00", "stage": "round_of_16"},  # 1pm ET Jul 4
    {"home_team": "France",    "away_team": "Paraguay",    "match_date": "2026-07-04 21:00", "stage": "round_of_16"},  # 5pm ET Jul 4
    {"home_team": "Brazil",    "away_team": "Norway",      "match_date": "2026-07-05 20:00", "stage": "round_of_16"},  # 4pm ET Jul 5
    {"home_team": "Mexico",    "away_team": "England",     "match_date": "2026-07-06 00:00", "stage": "round_of_16"},  # 8pm ET Jul 5
    {"home_team": "Spain",     "away_team": "Portugal",    "match_date": "2026-07-06 19:00", "stage": "round_of_16"},  # 3pm ET Jul 6
    {"home_team": "USA",       "away_team": "Belgium",     "match_date": "2026-07-07 00:00", "stage": "round_of_16"},  # 8pm ET Jul 6
    {"home_team": "Argentina", "away_team": "Egypt",       "match_date": "2026-07-07 16:00", "stage": "round_of_16"},  # noon ET Jul 7
    {"home_team": "Colombia",  "away_team": "Switzerland", "match_date": "2026-07-07 20:00", "stage": "round_of_16"},  # 4pm ET Jul 7

    # Quarter-finals – July 9-11 2026 (4 matches, times UTC)
    {"home_team": "France",    "away_team": "Morocco",     "match_date": "2026-07-09 20:00", "stage": "quarter_final"},  # 4pm ET Jul 9, Boston
    {"home_team": "Spain",     "away_team": "Belgium",     "match_date": "2026-07-10 19:00", "stage": "quarter_final"},  # 3pm ET Jul 10, Los Angeles
    {"home_team": "Norway",    "away_team": "England",     "match_date": "2026-07-11 21:00", "stage": "quarter_final"},  # 5pm ET Jul 11, Miami
    {"home_team": "Argentina", "away_team": "Switzerland", "match_date": "2026-07-12 01:00", "stage": "quarter_final"},  # 9pm ET Jul 11, Kansas City

    # Semi-finals – July 14-15 2026 (2 matches, times UTC)
    {"home_team": "France",  "away_team": "Spain",     "match_date": "2026-07-14 19:00", "stage": "semi-final"},  # 3pm ET Jul 14, Dallas
    {"home_team": "England", "away_team": "Argentina", "match_date": "2026-07-15 19:00", "stage": "semi-final"},  # 3pm ET Jul 15, Atlanta

    # Third-place play-off – July 18 2026
    {"home_team": "France", "away_team": "England", "match_date": "2026-07-18 21:00", "stage": "third-place"},  # 5pm ET Jul 18, Miami

    # Final – July 19 2026
    {"home_team": "Spain", "away_team": "Argentina", "match_date": "2026-07-19 19:00", "stage": "final"},  # 3pm ET Jul 19, New York New Jersey
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
            stadium=m.get("stadium", "TBD Stadium"),
            group_name=TEAM_TO_GROUP.get(m["home_team"]),
            stage="group",
            match_date=match_date,
            home_score=None,
            away_score=None
        )
        db.session.add(match)

    db.session.commit()
    print(f"Seeded {len(world_cup_2026_matches)} group stage matches into the database!")


def seed_knockout_matches():
    """Seed knockout stage placeholder matches. Idempotent — skips individual slots already present by date."""
    existing_dates = {
        m.match_date for m in Match.query.filter(Match.stage != "group").all()
        if m.match_date
    }
    added = 0
    for m in knockout_matches:
        match_date = datetime.strptime(m["match_date"], "%Y-%m-%d %H:%M")
        if match_date in existing_dates:
            continue
        match = Match(
            home_team=m["home_team"],
            away_team=m["away_team"],
            stadium="TBD",
            group_name=None,
            stage=m["stage"],
            match_date=match_date,
            home_score=None,
            away_score=None,
        )
        db.session.add(match)
        existing_dates.add(match_date)
        added += 1
    db.session.commit()
    print(f"Seeded {added} knockout stage matches.")


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

        # Seed group stage matches
        seed_matches()

        # Seed knockout stage placeholder matches
        seed_knockout_matches()