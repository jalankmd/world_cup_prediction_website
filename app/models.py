# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
from app import db


def _utc_now_naive():
    """Return current UTC datetime as naive value to match stored DB datetimes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Association table: many-to-many User <-> Competition
user_competitions = db.Table(
    'user_competitions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('competition_id', db.Integer, db.ForeignKey('competitions.id'), primary_key=True)
)


class Competition(db.Model):
    """Friend group with included competitions and signup code."""
    __tablename__ = "competitions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    include_tournament1 = db.Column(db.Boolean, nullable=False, default=True)
    include_tournament2 = db.Column(db.Boolean, nullable=False, default=True)
    entry_fee = db.Column(db.Float, nullable=False, default=0.0)

    # FK-based: users whose registration/primary group is this competition
    users = db.relationship("User", backref="group", lazy=True)

    def __repr__(self):
        return f"<Competition {self.name} code={self.code}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    favourite_team = db.Column(db.String(50), nullable=True)
    # Primary/registration group (FK). Kept for backward compat and as default context.
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)

    # M2M: all competitions this user belongs to (primary + any extra joined groups)
    competitions = db.relationship(
        'Competition',
        secondary=user_competitions,
        lazy=True,
        backref=db.backref('members', lazy=True)
    )

    predictions = db.relationship('Prediction', backref='user', lazy=True)
    odds_predictions = db.relationship('OddsPrediction', backref='user', lazy=True)
    group_qualifier_predictions = db.relationship('GroupQualifierPrediction', backref='user', lazy=True)
    # uselist=True because user can have one podium prediction per competition
    podium_predictions = db.relationship('PodiumPrediction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def total_points(self):
        """Combined points across all competitions and both tournaments."""
        return self.tournament1_points + self.tournament2_points

    @property
    def tournament1_points(self):
        return self.classic_match_points + self.group_qualifier_points + self.podium_points

    @property
    def tournament2_points(self):
        return int(round(sum(pred.points for pred in self.odds_predictions)))

    @property
    def classic_match_points(self):
        return sum(pred.points for pred in self.predictions)

    @property
    def group_qualifier_points(self):
        return sum(pred.points for pred in self.group_qualifier_predictions)

    @property
    def podium_points(self):
        return sum(p.points for p in self.podium_predictions)

    def __repr__(self):
        return f"<User {self.username}>"


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(50), nullable=False)
    away_team = db.Column(db.String(50), nullable=False)
    stadium = db.Column(db.String(120), nullable=True)
    group_name = db.Column(db.String(5), nullable=True)
    stage = db.Column(db.String(20), nullable=False, default="group")
    match_date = db.Column(db.DateTime, nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    home_odds = db.Column(db.Float, nullable=True)
    draw_odds = db.Column(db.Float, nullable=True)
    away_odds = db.Column(db.Float, nullable=True)
    advancing_team = db.Column(db.String(50), nullable=True)

    predictions = db.relationship('Prediction', backref='match', lazy=True)
    odds_predictions = db.relationship('OddsPrediction', backref='match', lazy=True)

    def is_locked(self):
        return self.match_date and _utc_now_naive() >= self.match_date

    def is_finished(self):
        return self.home_score is not None and self.away_score is not None

    def __repr__(self):
        return f"<Match {self.home_team} vs {self.away_team} on {self.match_date}>"


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)
    predicted_home_score = db.Column(db.Integer, nullable=False)
    predicted_away_score = db.Column(db.Integer, nullable=False)
    predicted_qualifier = db.Column(db.String(50), nullable=True)
    points = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'match_id', 'competition_id', name='unique_user_match_comp'),
    )

    def __repr__(self):
        return f"<Prediction User:{self.user_id} Match:{self.match_id} Comp:{self.competition_id} {self.predicted_home_score}-{self.predicted_away_score}>"


class OddsPrediction(db.Model):
    __tablename__ = "odds_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)
    predicted_outcome = db.Column(db.String(10), nullable=False)
    points = db.Column(db.Float, default=0.0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'match_id', 'competition_id', name='unique_user_match_comp_odds'),
    )

    def __repr__(self):
        return f"<OddsPrediction User:{self.user_id} Match:{self.match_id} Comp:{self.competition_id} {self.predicted_outcome}>"


class GroupQualifierPrediction(db.Model):
    __tablename__ = "group_qualifier_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    group_name = db.Column(db.String(5), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)
    team_1 = db.Column(db.String(50), nullable=False)
    team_2 = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'group_name', 'competition_id', name='unique_user_group_pick_comp'),
    )


class GroupResult(db.Model):
    __tablename__ = "group_results"

    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(5), unique=True, nullable=False)
    qualified_team_1 = db.Column(db.String(50), nullable=True)
    qualified_team_2 = db.Column(db.String(50), nullable=True)


class PodiumPrediction(db.Model):
    __tablename__ = "podium_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=True)
    champion_team = db.Column(db.String(50), nullable=False)
    runner_up_team = db.Column(db.String(50), nullable=False)
    third_place_team = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'competition_id', name='unique_user_comp_podium'),
    )


class TournamentOutcome(db.Model):
    __tablename__ = "tournament_outcome"

    id = db.Column(db.Integer, primary_key=True)
    champion_team = db.Column(db.String(50), nullable=True)
    runner_up_team = db.Column(db.String(50), nullable=True)
    third_place_team = db.Column(db.String(50), nullable=True)


class RankSnapshot(db.Model):
    __tablename__ = "rank_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False)
    t1_points = db.Column(db.Integer, nullable=False, default=0)
    t2_points = db.Column(db.Float, nullable=False, default=0.0)
    t1_rank = db.Column(db.Integer, nullable=False, default=0)
    t2_rank = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'competition_id', 'snapshot_date', name='unique_user_comp_date_snap'),
    )
