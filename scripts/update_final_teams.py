"""
Ensure the real third-place play-off and final fixtures exist with correct dates.

Both matchups confirmed (sources: FIFA / Al Jazeera, July 2026):
- Third place: France vs England, Jul 18 21:00 UTC (5pm ET, Miami)
- Final: Spain vs Argentina, Jul 19 19:00 UTC (3pm ET, East Rutherford)

Self-healing — safe to run in any DB state (runs on every deploy via
scripts/startup.py, or manually with `railway run python scripts/update_final_teams.py`).
Uses the same dedupe/merge/force-correct logic as the quarter-final updater.
"""

from app import create_app
from scripts.update_qf_teams import ensure_stage_fixtures

# All times UTC (EDT+4h).
THIRD_PLACE_MATCHES = [
    {"home_team": "France", "away_team": "England", "match_date": "2026-07-18 21:00", "stadium": "Miami Stadium"},  # 5pm ET Jul 18
]

FINAL_MATCHES = [
    {"home_team": "Spain", "away_team": "Argentina", "match_date": "2026-07-19 19:00", "stadium": "New York New Jersey Stadium"},  # 3pm ET Jul 19
]


def update_final():
    ensure_stage_fixtures("third-place", THIRD_PLACE_MATCHES)
    ensure_stage_fixtures("final", FINAL_MATCHES)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_final()
