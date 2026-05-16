# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
from app import db


def _utc_now_naive():
    """Return current UTC datetime as naive value to match stored DB datetimes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Competition(db.Model):
    """Friend group with included competitions and signup code."""
    __tablename__ = "competitions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    include_tournament1 = db.Column(db.Boolean, nullable=False, default=True)
    include_tournament2 = db.Column(db.Boolean, nullable=False, default=True)

    users = db.relationship("User", backref="group", lazy=True)

    def __repr__(self):
        return f"<Competition {self.name} code={self.code}>"


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
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)

    # Relationship to predictions made by the user
    predictions = db.relationship('Prediction', backref='user', lazy=True)
    odds_predictions = db.relationship('OddsPrediction', backref='user', lazy=True)
    group_qualifier_predictions = db.relationship('GroupQualifierPrediction', backref='user', lazy=True)
    podium_prediction = db.relationship('PodiumPrediction', backref='user', uselist=False, lazy=True)

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
        """Combined points across Tournament 1 and Tournament 2."""
        return self.tournament1_points + self.tournament2_points

    @property
    def tournament1_points(self):
        """Tournament 1 points: score predictions + group qualifiers + podium picks."""
        return self.classic_match_points + self.group_qualifier_points + self.podium_points

    @property
    def tournament2_points(self):
        """Tournament 2 points: odds-based predictions."""
        return int(round(sum(pred.points for pred in self.odds_predictions)))

    @property
    def classic_match_points(self):
        """Points from scoreline predictions (Tournament 1 match picks)."""
        return sum(pred.points for pred in self.predictions)

    @property
    def group_qualifier_points(self):
        """Points from group qualifier picks."""
        return sum(pred.points for pred in self.group_qualifier_predictions)

    @property
    def podium_points(self):
        """Points from champion/runner-up/third-place picks."""
        if self.podium_prediction:
            return self.podium_prediction.points
        return 0

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
    stadium = db.Column(db.String(120), nullable=True)
    group_name = db.Column(db.String(5), nullable=True)
    stage = db.Column(db.String(20), nullable=False, default="group")
    match_date = db.Column(db.DateTime, nullable=True)  # Allow TBD matches
    home_score = db.Column(db.Integer, nullable=True)   # Can be null if match not played
    away_score = db.Column(db.Integer, nullable=True)   # Can be null if match not played
    home_odds = db.Column(db.Float, nullable=True)
    draw_odds = db.Column(db.Float, nullable=True)
    away_odds = db.Column(db.Float, nullable=True)

    # Relationship to predictions for this match
    predictions = db.relationship('Prediction', backref='match', lazy=True)
    odds_predictions = db.relationship('OddsPrediction', backref='match', lazy=True)

    def is_locked(self):
        """
        Check if the match is locked for predictions.
        Locked means match_date has passed.
        """
        return self.match_date and _utc_now_naive() >= self.match_date

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


class OddsPrediction(db.Model):
    """Tournament 2: winner/draw prediction scored by odds value."""
    __tablename__ = "odds_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    predicted_outcome = db.Column(db.String(10), nullable=False)  # home, draw, away
    points = db.Column(db.Float, default=0.0)

    __table_args__ = (db.UniqueConstraint('user_id', 'match_id', name='unique_user_match_odds'),)

    def __repr__(self):
        return f"<OddsPrediction User:{self.user_id} Match:{self.match_id} {self.predicted_outcome} Points:{self.points}>"


class GroupQualifierPrediction(db.Model):
    """Tournament 1: pick two teams that qualify from each group."""
    __tablename__ = "group_qualifier_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_name = db.Column(db.String(5), nullable=False)
    team_1 = db.Column(db.String(50), nullable=False)
    team_2 = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('user_id', 'group_name', name='unique_user_group_pick'),)


class GroupResult(db.Model):
    """Actual qualified teams for each group (entered by admin)."""
    __tablename__ = "group_results"

    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(5), unique=True, nullable=False)
    qualified_team_1 = db.Column(db.String(50), nullable=True)
    qualified_team_2 = db.Column(db.String(50), nullable=True)


class PodiumPrediction(db.Model):
    """Tournament 1: pick champion, runner-up and third-place."""
    __tablename__ = "podium_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    champion_team = db.Column(db.String(50), nullable=False)
    runner_up_team = db.Column(db.String(50), nullable=False)
    third_place_team = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)


class TournamentOutcome(db.Model):
    """Actual tournament podium (entered by admin when known)."""
    __tablename__ = "tournament_outcome"

    id = db.Column(db.Integer, primary_key=True)
    champion_team = db.Column(db.String(50), nullable=True)
    runner_up_team = db.Column(db.String(50), nullable=True)
    third_place_team = db.Column(db.String(50), nullable=True)
