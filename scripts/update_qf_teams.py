"""
Ensure exactly the four real quarter-final fixtures exist with correct dates.

All 4 matchups confirmed (sources: World Soccer Talk / Sky Sports, July 2026).
Times are UTC (EDT = UTC-4).

Self-healing — safe to run in any DB state (runs on every deploy via
scripts/startup.py, or manually with `railway run python scripts/update_qf_teams.py`):
- removes TBD placeholders and stray quarter_final rows that aren't one of
  the four real fixtures
- merges duplicate rows for the same fixture, keeping predictions
- fixes reversed home/away rows (swapping prediction scores/outcomes to match)
- force-corrects kickoff date and stadium on every fixture
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


def _delete_matches(matches, reason):
    if not matches:
        return
    ids = [m.id for m in matches]
    Prediction.query.filter(Prediction.match_id.in_(ids)).delete(synchronize_session=False)
    OddsPrediction.query.filter(OddsPrediction.match_id.in_(ids)).delete(synchronize_session=False)
    Match.query.filter(Match.id.in_(ids)).delete(synchronize_session=False)
    print(f"Removed {len(ids)} {reason} quarter_final rows.")


def _merge_into(kept, extra):
    """Move extra's predictions onto kept where the user doesn't already have one."""
    for pred in list(extra.predictions):
        exists = Prediction.query.filter_by(
            user_id=pred.user_id, match_id=kept.id, competition_id=pred.competition_id
        ).first()
        if exists:
            db.session.delete(pred)
        else:
            pred.match_id = kept.id
    for pred in list(extra.odds_predictions):
        exists = OddsPrediction.query.filter_by(
            user_id=pred.user_id, match_id=kept.id, competition_id=pred.competition_id
        ).first()
        if exists:
            db.session.delete(pred)
        else:
            pred.match_id = kept.id
    db.session.flush()


def update_qf():
    real = {frozenset((m["home_team"], m["away_team"])): m for m in QF_MATCHES}
    rows = Match.query.filter_by(stage="quarter_final").all()

    by_pair = {}
    stray = []
    for row in rows:
        key = frozenset((row.home_team, row.away_team))
        if key in real:
            by_pair.setdefault(key, []).append(row)
        else:
            stray.append(row)

    _delete_matches(stray, "stray/placeholder")

    for key, new in real.items():
        match_date = datetime.strptime(new["match_date"], "%Y-%m-%d %H:%M")
        group = by_pair.get(key, [])

        if group:
            # Keep the row with the most predictions (ties: lowest id), merge the rest in
            group.sort(key=lambda m: (-(len(m.predictions) + len(m.odds_predictions)), m.id))
            kept = group[0]
            for extra in group[1:]:
                _merge_into(kept, extra)
            _delete_matches(group[1:], "duplicate")

            if kept.home_team != new["home_team"]:
                # Reversed home/away: flip the row and every prediction on it
                for pred in kept.predictions:
                    pred.predicted_home_score, pred.predicted_away_score = (
                        pred.predicted_away_score, pred.predicted_home_score
                    )
                for pred in kept.odds_predictions:
                    if pred.predicted_outcome == "home":
                        pred.predicted_outcome = "away"
                    elif pred.predicted_outcome == "away":
                        pred.predicted_outcome = "home"
                kept.home_odds, kept.away_odds = kept.away_odds, kept.home_odds
                kept.home_team = new["home_team"]
                kept.away_team = new["away_team"]
                print(f"  flipped home/away: {new['home_team']} vs {new['away_team']}")

            kept.match_date = match_date
            kept.stadium = new["stadium"]
            print(f"  ok: {kept.home_team} vs {kept.away_team} @ {kept.match_date} (id {kept.id})")
        else:
            db.session.add(Match(
                home_team=new["home_team"],
                away_team=new["away_team"],
                stadium=new["stadium"],
                group_name=None,
                stage="quarter_final",
                match_date=match_date,
            ))
            print(f"  added: {new['home_team']} vs {new['away_team']} @ {match_date}")

    db.session.commit()
    print("\nDone. Quarter-final fixtures verified.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_qf()
