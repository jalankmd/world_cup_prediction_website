"""
Update Round of 16 match teams and dates from TBD placeholders to actuals.

All 8 matchups confirmed (source: Fox Sports, July 4 2026).
Times are UTC (EDT = UTC-4).

Run via Railway CLI:
    railway run python scripts/update_r16_teams.py
"""

from datetime import datetime
from app import create_app, db
from app.models import Match

# All times UTC (EDT+4h). Fox Sports source.
R16_MATCHES = [
    {"home_team": "Morocco",     "away_team": "Canada",      "match_date": "2026-07-04 17:00"},  # 1pm ET Jul 4
    {"home_team": "France",      "away_team": "Paraguay",    "match_date": "2026-07-04 21:00"},  # 5pm ET Jul 4
    {"home_team": "Brazil",      "away_team": "Norway",      "match_date": "2026-07-05 20:00"},  # 4pm ET Jul 5
    {"home_team": "Mexico",      "away_team": "England",     "match_date": "2026-07-06 00:00"},  # 8pm ET Jul 5
    {"home_team": "Spain",       "away_team": "Portugal",    "match_date": "2026-07-06 19:00"},  # 3pm ET Jul 6
    {"home_team": "USA",         "away_team": "Belgium",     "match_date": "2026-07-07 00:00"},  # 8pm ET Jul 6
    {"home_team": "Argentina",   "away_team": "Egypt",       "match_date": "2026-07-07 16:00"},  # noon ET Jul 7
    {"home_team": "Colombia",    "away_team": "Switzerland", "match_date": "2026-07-07 20:00"},  # 4pm ET Jul 7
]


def update_r16():
    r16 = Match.query.filter_by(stage="round_of_16").order_by(Match.match_date).all()
    print(f"Found {len(r16)} round_of_16 matches in DB.")

    if len(r16) < len(R16_MATCHES):
        print(f"ERROR: only {len(r16)} R16 slots in DB, need {len(R16_MATCHES)}.")
        return

    for i, new in enumerate(R16_MATCHES):
        db_match = r16[i]
        old_label = f"{db_match.home_team} vs {db_match.away_team} @ {db_match.match_date}"
        db_match.home_team = new["home_team"]
        db_match.away_team = new["away_team"]
        db_match.match_date = datetime.strptime(new["match_date"], "%Y-%m-%d %H:%M")
        print(f"  [{i+1}] {old_label}")
        print(f"      → {db_match.home_team} vs {db_match.away_team} @ {db_match.match_date}")

    db.session.commit()
    print("\nDone. All 8 Round of 16 matches updated.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_r16()
