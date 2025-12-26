# app.py
"""
Main Flask application for World Cup Prediction Website.
Handles user registration, login, logout, match display, prediction submission, admin dashboard, and leaderboard.
"""

import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate

from config import DevelopmentConfig, ProductionConfig
from models import db, User, Match, Prediction
from forms import RegisterForm, LoginForm, PredictionForm
from scoring import update_all_points

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# ---------------------------
# Create Flask app
# ---------------------------
app = Flask(__name__)

# Use DevelopmentConfig locally
env = os.environ.get("FLASK_ENV", "development")
if env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


# Initialize database
# ---------------------------
db.init_app(app)

migrate = Migrate(app, db)

# ---------------------------
# Flask-Login setup
# ---------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/matches")
@login_required
def matches():
    matches = Match.query.order_by(Match.match_date).all()
    predictions = {p.match_id: p for p in Prediction.query.filter_by(user_id=current_user.id)}
    return render_template("matches.html", matches=matches, predictions=predictions)


@app.route("/predict_inline/<int:match_id>", methods=["POST"])
@login_required
def predict_inline(match_id):
    match = Match.query.get_or_404(match_id)
    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("matches"))

    prediction = Prediction.query.filter_by(user_id=current_user.id, match_id=match.id).first()
    home_score = int(request.form["predicted_home_score"])
    away_score = int(request.form["predicted_away_score"])

    if prediction:
        prediction.predicted_home_score = home_score
        prediction.predicted_away_score = away_score
        flash("Prediction updated!", "success")
    else:
        new_pred = Prediction(
            user_id=current_user.id,
            match_id=match.id,
            predicted_home_score=home_score,
            predicted_away_score=away_score
        )
        db.session.add(new_pred)
        flash("Prediction saved!", "success")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
        print(e)

    return redirect(url_for("matches"))


@app.route("/leaderboard")
@login_required
def leaderboard():
    users = User.query.all()
    users_sorted = sorted(users, key=lambda u: u.total_points, reverse=True)
    return render_template("leaderboard.html", users=users_sorted)


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    if not getattr(current_user, "is_admin", False):
        return "Access denied", 403

    if request.method == "POST":
        for match_id, data in request.form.items():
            if "-" in match_id:
                field, mid = match_id.split("-")
                mid = int(mid)
                match = Match.query.get(mid)
                if match:
                    try:
                        val = int(data) if data != "" else None
                        if field == "home_score":
                            match.home_score = val
                        elif field == "away_score":
                            match.away_score = val
                    except ValueError:
                        continue

        db.session.commit()
        update_all_points()
        flash("Match results updated and user points recalculated!", "success")
        return redirect(url_for("admin_dashboard"))

    matches = Match.query.order_by(Match.match_date).all()
    return render_template("admin_dashboard.html", matches=matches)

# ---------------------------
# Run the app
# ---------------------------
if __name__ == "__main__":
    app.run()
    # app.run(debug=True)
