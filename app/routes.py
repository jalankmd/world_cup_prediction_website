# app/routes.py
"""
Main route handlers for the World Cup Prediction Website.

This file defines all the Flask routes using a blueprint (`bp`).
- User authentication (register, login, logout)
- Match display and prediction submission
- Leaderboard
- Admin dashboard
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, login_user, logout_user, current_user
from app.models import User, Match, Prediction
from app.forms import RegisterForm, LoginForm, PredictionForm
from app.scoring import update_all_points
from app import db

# ---------------------------
# Blueprint Setup
# ---------------------------
bp = Blueprint("main", __name__)

# ---------------------------
# Home Page
# ---------------------------
@bp.route("/")
def home():
    """Render the homepage."""
    return render_template("home.html")


# ---------------------------
# User Registration
# ---------------------------
@bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Register a new user.
    - Validates form
    - Hashes password
    - Stores user in DB
    """
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)  # Hash password
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


# ---------------------------
# User Login
# ---------------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login an existing user.
    - Validates credentials
    - Uses Flask-Login to create session
    """
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


# ---------------------------
# User Logout
# ---------------------------
@bp.route("/logout")
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


# ---------------------------
# Match List
# ---------------------------
@bp.route("/matches")
@login_required
def matches():
    """
    Display all matches and current user's predictions.
    - Predictions are mapped by match_id for easy lookup in template.
    """
    matches = Match.query.order_by(Match.match_date).all()
    predictions = {p.match_id: p for p in Prediction.query.filter_by(user_id=current_user.id)}
    return render_template("matches.html", matches=matches, predictions=predictions)


# ---------------------------
# Inline Prediction Submission
# ---------------------------
@bp.route("/predict_inline/<int:match_id>", methods=["POST"])
@login_required
def predict_inline(match_id):
    """
    Submit or update a prediction for a match.
    - Prevents submission if match is locked or finished
    - Updates or creates prediction in DB
    """
    match = Match.query.get_or_404(match_id)

    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("main.matches"))

    prediction = Prediction.query.filter_by(user_id=current_user.id, match_id=match.id).first()
    home_score = int(request.form["predicted_home_score"])
    away_score = int(request.form["predicted_away_score"])

    if prediction:
        # Update existing prediction
        prediction.predicted_home_score = home_score
        prediction.predicted_away_score = away_score
        flash("Prediction updated!", "success")
    else:
        # Create new prediction
        new_pred = Prediction(
            user_id=current_user.id,
            match_id=match.id,
            predicted_home_score=home_score,
            predicted_away_score=away_score
        )
        db.session.add(new_pred)
        flash("Prediction saved!", "success")

    # Commit changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
        print(e)

    return redirect(url_for("main.matches"))


# ---------------------------
# Leaderboard
# ---------------------------
@bp.route("/leaderboard")
@login_required
def leaderboard():
    """
    Display leaderboard sorted by total points.
    - total_points is a property on User model
    """
    users = User.query.all()
    users_sorted = sorted(users, key=lambda u: u.total_points, reverse=True)
    return render_template("leaderboard.html", users=users_sorted)


# ---------------------------
# Admin Dashboard
# ---------------------------
@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    """
    Admin-only page for updating match results.
    - Only users with is_admin=True can access
    - Handles updating home/away scores via form
    - Recalculates points for all predictions
    """
    if not getattr(current_user, "is_admin", False):
        return "Access denied", 403

    if request.method == "POST":
        # Loop through form data to update match scores
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

        # Commit updated scores and recalc points
        db.session.commit()
        update_all_points()
        flash("Match results updated and user points recalculated!", "success")
        return redirect(url_for("main.admin_dashboard"))

    # GET request — render admin dashboard
    matches = Match.query.order_by(Match.match_date).all()
    return render_template("admin_dashboard.html", matches=matches)
