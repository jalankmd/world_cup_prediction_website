"""
Update quarter-final match teams and dates from TBD placeholders to actuals.

All 4 matchups confirmed (sources: Al Jazeera / Sky Sports, July 2026).
Times are UTC (EDT = UTC-4).

Run via Railway CLI:
    railway run python scripts/update_qf_teams.py
"""

from datetime import datetime
from app import create_app, db
from app.models import Match

# All times UTC (EDT+4h).
QF_MATCHES = [
    {"home_team": "France",    "away_team": "Morocco",     "match_date": "2026-07-09 20:00", "stadium": "Boston Stadium"},        # 4pm ET Jul 9
    {"home_team": "Spain",     "away_team": "Belgium",     "match_date": "2026-07-10 19:00", "stadium": "Los Angeles Stadium"},   # 3pm ET Jul 10
    {"home_team": "Norway",    "away_team": "England",     "match_date": "2026-07-11 21:00", "stadium": "Miami Stadium"},         # 5pm ET Jul 11
    {"home_team": "Argentina", "away_team": "Switzerland", "match_date": "2026-07-12 01:00", "stadium": "Kansas City Stadium"},   # 9pm ET Jul 11
]


def update_qf():
    qf = Match.query.filter_by(stage="quarter_final").order_by(Match.match_date).all()
    print(f"Found {len(qf)} quarter_final matches in DB.")

    if len(qf) < len(QF_MATCHES):
        print(f"ERROR: only {len(qf)} QF slots in DB, need {len(QF_MATCHES)}.")
        return

    for i, new in enumerate(QF_MATCHES):
        db_match = qf[i]
        old_label = f"{db_match.home_team} vs {db_match.away_team} @ {db_match.match_date}"
        db_match.home_team = new["home_team"]
        db_match.away_team = new["away_team"]
        db_match.match_date = datetime.strptime(new["match_date"], "%Y-%m-%d %H:%M")
        db_match.stadium = new["stadium"]
        print(f"  [{i+1}] {old_label}")
        print(f"      → {db_match.home_team} vs {db_match.away_team} @ {db_match.match_date}")

    db.session.commit()
    print("\nDone. All 4 quarter-final matches updated.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_qf()
