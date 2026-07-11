# scripts/create_review_account.py
"""
Create the Apple App Review demo account in its own demo group.

Registration closed on June 11, so App Store reviewers can't sign up —
Apple requires working demo credentials (guideline 2.1). The account
lives in a dedicated "App Review Demo" group so it never appears on
real players' leaderboards.
"""

from app import create_app, db
from app.models import User, Competition

REVIEW_USERNAME = "applereviewer"
REVIEW_PASSWORD = "ReviewWorldCup2026!"
DEMO_GROUP_NAME = "App Review Demo"
DEMO_GROUP_CODE = "APPLE-REVIEW-2026"


def create_review_account():
    """Create the demo group and reviewer user if they don't exist."""
    group = Competition.query.filter_by(name=DEMO_GROUP_NAME).first()
    if not group:
        group = Competition(
            name=DEMO_GROUP_NAME,
            code=DEMO_GROUP_CODE,
            include_tournament1=True,
            include_tournament2=True,
            entry_fee=0.0,
        )
        db.session.add(group)
        db.session.flush()
        print("App Review demo group created.")

    if User.query.filter_by(username=REVIEW_USERNAME).first():
        print("App Review demo user already exists.")
        return

    reviewer = User(
        first_name="Apple",
        last_name="Reviewer",
        username=REVIEW_USERNAME,
        email=None,
        is_admin=False,
        competition_id=group.id,
    )
    reviewer.set_password(REVIEW_PASSWORD)
    reviewer.competitions.append(group)

    db.session.add(reviewer)
    db.session.commit()
    print("App Review demo user created.")


# ---------------------------
# Run script standalone
# ---------------------------
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        create_review_account()
