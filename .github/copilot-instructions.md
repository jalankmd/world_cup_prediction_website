# World Cup Prediction Website - AI Coding Guidelines

## Architecture Overview
This is a Flask web application using the app factory pattern. Core components:
- **Models** (`app/models.py`): User, Match, Prediction with SQLAlchemy relationships
- **Routes** (`app/routes.py`): Blueprint-based endpoints for auth, predictions, leaderboard
- **Scoring** (`app/scoring.py`): Points calculation (3 for exact score, 2 for correct outcome)
- **Forms** (`app/forms.py`): WTForms for registration, login, predictions
- **Config** (`config.py`): Environment-based configs (dev/prod)

## Developer Workflows
- **Setup**: `pip install -r requirements.txt` then `flask db upgrade`
- **Seed Data**: `python scripts/seed_matches.py` for World Cup 2026 matches
- **Create Admin**: `python scripts/create_admin_account.py` (hardcoded credentials)
- **Run App**: `python run.py` (debug mode) or `flask run`
- **Update Scores**: Call `update_all_points()` from `app/scoring.py` after entering match results

## Key Conventions
- **Predictions**: Inline submission via POST to `/predict_inline/<match_id>`, checks `match.is_locked()` before allowing
- **Unique Constraints**: One prediction per user-match pair
- **Admin Access**: Check `current_user.is_admin` for dashboard routes
- **Database**: SQLite for dev, configurable via `DATABASE_URL`
- **Templates**: Jinja2 in `templates/`, static files in `static/`

## Code Patterns
- Use `current_user` from Flask-Login for authenticated routes
- Flash messages for user feedback: `flash("message", "category")`
- Query predictions: `{p.match_id: p for p in Prediction.query.filter_by(user_id=current_user.id)}`
- Match locking: `if match.is_locked() or match.is_finished():` prevents submissions

## Dependencies
Flask ecosystem: SQLAlchemy, Migrate, Login, WTF. No external APIs - self-contained prediction system.