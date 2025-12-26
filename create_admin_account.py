from app import app, db
from models import User

with app.app_context():
    if User.query.filter_by(username="jalankmd").first() is None:
        admin_user = User(
            first_name="Mahir",
            last_name="Jalanko",
            username="jalankmd",
            email="jalankmd@gmail.com"
        )
        admin_user.set_password("totti10")
        admin_user.is_admin = True

        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")