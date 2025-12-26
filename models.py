# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()


# -----------------------
# User Model
# -----------------------
class User(UserMixin, db.Model):
    """
    User model representing a registered user in the system.
    Inherits from UserMixin for Flask-Login integration.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # <-- New field

    # Relationship to predictions made by the user
    predictions = db.relationship('Prediction', backref='user', lazy=True)

    # -----------------------
    # Password methods
    # -----------------------
    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check a plain password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # -----------------------
    # Helper properties
    # -----------------------
    @property
    def total_points(self):
        """Calculate total points from all predictions made by the user."""
        return sum(pred.points for pred in self.predictions)

    def __repr__(self):
        return f"<User {self.username}>"


# -----------------------
# Match Model
# -----------------------
class Match(db.Model):
    """
    Match model representing a scheduled soccer match.
    """
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(50), nullable=False)
    away_team = db.Column(db.String(50), nullable=False)
    match_date = db.Column(db.DateTime, nullable=True)  # Allow TBD matches
    home_score = db.Column(db.Integer, nullable=True)   # Can be null if match not played
    away_score = db.Column(db.Integer, nullable=True)   # Can be null if match not played

    # Relationship to predictions for this match
    predictions = db.relationship('Prediction', backref='match', lazy=True)

    def is_locked(self):
        """
        Check if the match is locked for predictions.
        Locked means match_date has passed.
        """
        return self.match_date and datetime.utcnow() >= self.match_date

    def is_finished(self):
        """
        Check if match has been played.
        Finished means both scores are set.
        """
        return self.home_score is not None and self.away_score is not None

    def __repr__(self):
        return f"<Match {self.home_team} vs {self.away_team} on {self.match_date}>"


# -----------------------
# Prediction Model
# -----------------------
class Prediction(db.Model):
    """
    Prediction model representing a user's predicted score for a match.
    """
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    predicted_home_score = db.Column(db.Integer, nullable=False)
    predicted_away_score = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=0)  # Points earned for this prediction

    # Ensure a user can only have one prediction per match
    __table_args__ = (db.UniqueConstraint('user_id', 'match_id', name='unique_user_match'),)

    def __repr__(self):
        return f"<Prediction User:{self.user_id} Match:{self.match_id} {self.predicted_home_score}-{self.predicted_away_score} Points:{self.points}>"
