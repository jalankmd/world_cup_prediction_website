# scripts/init_db.py
"""
Script to initialize the database, run migrations,
seed matches, and create an admin account.
"""

from app import create_app, db
from app.admin import create_admin
from scripts.seed_matches import seed_matches

app = create_app()

with app.app_context():
    # Drop & recreate tables (optional)
    db.drop_all()
    db.create_all()
    print("Database created.")

    # Seed matches
    seed_matches()
    print("Matches seeded.")

    # Create admin
    create_admin()
