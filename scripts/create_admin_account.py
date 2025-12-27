# scripts/create_admin.py
"""
Create an admin user in the database.
"""

from app import create_app, db
from app.models import User

def create_admin():
    """Create the admin user if it doesn't exist."""
    username = "jalankmd"
    email = "jalankmd@gmail.com"
    
    if User.query.filter_by(username=username).first():
        print("Admin user already exists.")
        return

    admin_user = User(
        first_name="Mahir",
        last_name="Jalanko",
        username=username,
        email=email,
        is_admin=True
    )
    admin_user.set_password("onlymahirallowed!")

    db.session.add(admin_user)
    db.session.commit()
    print("Admin user created.")

# ---------------------------
# Run script standalone
# ---------------------------
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        create_admin()
