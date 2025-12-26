# World Cup Prediction Website

A Flask-based web application for users to predict World Cup match scores and compete on a leaderboard.

## Features

- User registration and login
- Match prediction submission
- Leaderboard based on prediction accuracy
- Admin dashboard for updating match results

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set up the database: `flask db upgrade`
3. Seed matches: `python seed_matches.py`
4. Create admin account: `python create_admin_account.py`
5. Run the app: `python app.py`

## Environment Variables

- `FLASK_APP=app.py`
- `FLASK_ENV=development`
- `SECRET_KEY=your-secret-key`
- `DATABASE_URL=sqlite:///app.db`
