# manage.py
"""
Command-line interface for administrative tasks.

Usage examples:
----------------
python manage.py run
python manage.py init_db
python manage.py seed_matches
python manage.py create_admin
python manage.py reset_db
"""

from flask.cli import FlaskGroup
from app import create_app
from app import db
from scripts.seed_matches import seed_matches
from scripts.create_admin_account import create_admin

app = create_app()
cli = FlaskGroup(app)


@cli.command("run")
def run():
    """Run the Flask development server."""
    print("Use 'python run.py' or 'flask run' instead.")


@cli.command("init_db")
def init_db():
    """Create database tables."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created.")


@cli.command("reset_db")
def reset_db():
    """Drop and recreate all database tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("⚠️ Database reset complete.")


@cli.command("seed_matches")
def seed_matches_command():
    """Seed World Cup matches."""
    with app.app_context():
        seed_matches()
        print("⚽ Matches seeded.")


@cli.command("create_admin")
def create_admin_command():
    """Create admin user."""
    with app.app_context():
        create_admin()
        print("👑 Admin user ensured.")


if __name__ == "__main__":
    cli()
