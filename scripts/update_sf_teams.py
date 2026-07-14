"""
Ensure exactly the two real semi-final fixtures exist with correct dates.

Both matchups confirmed (sources: SI / Al Jazeera, July 2026).
Times are UTC (EDT = UTC-4).

Self-healing — safe to run in any DB state (runs on every deploy via
scripts/startup.py, or manually with `railway run python scripts/update_sf_teams.py`).
Uses the same dedupe/merge/force-correct logic as the quarter-final updater.
"""

from app import create_app
from scripts.update_qf_teams import ensure_stage_fixtures

# All times UTC (EDT+4h).
SF_MATCHES = [
    {"home_team": "France",  "away_team": "Spain",     "match_date": "2026-07-14 19:00", "stadium": "Dallas Stadium"},    # 3pm ET Jul 14, Arlington
    {"home_team": "England", "away_team": "Argentina", "match_date": "2026-07-15 19:00", "stadium": "Atlanta Stadium"},   # 3pm ET Jul 15
]


def update_sf():
    ensure_stage_fixtures("semi-final", SF_MATCHES)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        update_sf()
