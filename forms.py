# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
from models import User

# -----------------------
# Registration Form
# -----------------------
class RegisterForm(FlaskForm):
    """Form for new users to register an account."""
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=50)])
    username = StringField("Username", validators=[DataRequired(), Length(max=50)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Register")

    # -----------------------
    # Custom Validators
    # -----------------------
    def validate_email(self, email):
        """Ensure the email is unique in the database."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already in use.")

    def validate_username(self, username):
        """Ensure the username is unique in the database."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username already taken.")

# -----------------------
# Login Form
# -----------------------
class LoginForm(FlaskForm):
    """Form for existing users to log in."""
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# -----------------------
# Prediction Form
# -----------------------
class PredictionForm(FlaskForm):
    """Form for submitting or updating predictions for a match."""
    predicted_home_score = IntegerField(
        "Home Team Score", 
        validators=[DataRequired(), NumberRange(min=0, max=20, message="Score must be between 0 and 20")]
    )
    predicted_away_score = IntegerField(
        "Away Team Score", 
        validators=[DataRequired(), NumberRange(min=0, max=20, message="Score must be between 0 and 20")]
    )
    submit = SubmitField("Submit Prediction")
