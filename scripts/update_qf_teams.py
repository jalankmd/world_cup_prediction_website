"""
Ensure the four real quarter-final fixtures exist, replacing TBD placeholders.

All 4 matchups confirmed (sources: Al Jazeera / Sky Sports, July 2026).
Times are UTC (EDT = UTC-4).

Safe to run in any DB state: removes leftover TBD quarter_final placeholder
rows (and any predictions on them), then upserts each real fixture by team
pair. Running on every deploy is handled by scripts/startup.py; this script
exists for manual runs:

    railway run python scripts/update_qf_teams.py
"""

from datetime import datetime
from app import create_app, db
from app.models import Match, Prediction, OddsPrediction

# All times UTC (EDT+4h).
QF_MATCHES = [
    {"home_team": "France",    "away_team": "Morocco",     "match_date": "2026-07-09 20:00", "stadium": "Boston Stadium"},        # 4pm ET Jul 9
    {"home_team": "Spain",     "away_team": "Belgium",     "match_date": "2026-07-10 19:00", "stadium": "Los Angeles Stadium"},   # 3pm ET Jul 10
    {"home_team": "Norway",    "away_team": "England",     "match_date": "2026-07-11 21:00", "stadium": "Miami Stadium"},         # 5pm ET Jul 11
    {"home_team": "Argentina", "away_team": "Switzerland", "match_date": "2026-07-12 01:00", "stadium": "Kansas City Stadium"},   # 9pm ET Jul 11
]


def update_qf():
    tbd = Match.query.filter_by(stage="quarter_final", home_team="TBD").all()
    if tbd:
        tbd_ids = [m.id for m in tbd]
        Prediction.query.filter(Prediction.match_id.in_(tbd_ids)).delete(synchronize_session=False)
        OddsPrediction.query.filter(OddsPrediction.match_id.in_(tbd_ids)).delete(synchronize_session=False)
        Match.query.filter(Match.id.in_(tbd_ids)).delete(synchronize_session=False)
        print(f"Removed {len(tbd_ids)} TBD quarter_final placeholders.")

    for new in QF_MATCHES:
        match_date = datetime.strptime(new["match_date"], "%Y-%m-%d %H:%M")
        match = Match.query.filter_by(
            stage="quarter_final", home_team=new["home_team"], away_team=new["away_team"]
        ).first()
        if match:
            match.match_date = match_date
            match.stadium = new["stadium"]
            print(f"  updated: {match.home_team} vs {match.away_team} @ {match.match_date}")
        else:
            db.session.add(Match(
                home_team=new["home_team"],
                away_team=new["away_team"],
                stadium=new["stadium"],
                group_name=None,
                stage="quarter_final",
                match_date=match_date,
            ))
            print(f"  added:   {new['home_team']} vs {new['away_team']} @ {match_date}")

    db.session.commit()
    print("\nDone. All 4 quarter-final fixtures are in place.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_qf()
