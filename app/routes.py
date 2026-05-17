# app/routes.py
"""
Main route handlers for the World Cup Prediction Website.

This file defines all the Flask routes using a blueprint (`bp`).
- User authentication (register, login, logout)
- Match display and prediction submission
- Leaderboard
- Admin dashboard
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, login_user, logout_user, current_user
from app.models import (
    Competition,
    User,
    Match,
    Prediction,
    OddsPrediction,
    GroupQualifierPrediction,
    GroupResult,
    PodiumPrediction,
    TournamentOutcome,
)
from app.forms import RegisterForm, LoginForm, PredictionForm
from app.scoring import update_all_points
from app import db
from datetime import datetime, timezone

# ---------------------------
# Blueprint Setup
# ---------------------------
bp = Blueprint("main", __name__)

TEAM_FLAG_CODES = {
    "Algeria": "dz",
    "Argentina": "ar",
    "Australia": "au",
    "Austria": "at",
    "Belgium": "be",
    "Bosnia and Herzegovina": "ba",
    "DR Congo": "cd",
    "Iraq": "iq",
    "Brazil": "br",
    "Canada": "ca",
    "Cape Verde": "cv",
    "Colombia": "co",
    "Croatia": "hr",
    "Curaçao": "cw",
    "Czech Republic": "cz",
    "Ecuador": "ec",
    "Egypt": "eg",
    "England": "gb-eng",
    "France": "fr",
    "Germany": "de",
    "Ghana": "gh",
    "Haiti": "ht",
    "Iran": "ir",
    "Ivory Coast": "ci",
    "Italy": "it",
    "Japan": "jp",
    "Jordan": "jo",
    "Mexico": "mx",
    "Morocco": "ma",
    "Netherlands": "nl",
    "New Zealand": "nz",
    "Norway": "no",
    "Panama": "pa",
    "Paraguay": "py",
    "Portugal": "pt",
    "Qatar": "qa",
    "Saudi Arabia": "sa",
    "Scotland": "gb-sct",
    "Senegal": "sn",
    "Serbia": "rs",
    "South Africa": "za",
    "South Korea": "kr",
    "Spain": "es",
    "Sweden": "se",
    "Switzerland": "ch",
    "Tunisia": "tn",
    "Turkey": "tr",
    "USA": "us",
    "Uruguay": "uy",
    "Uzbekistan": "uz",
    "Wales": "gb-wls",
}

GROUP_TEAMS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["USA", "Paraguay", "Australia", "Turkey"],
    "D": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Spain", "Cape Verde", "Belgium", "Egypt"],
    "H": ["Saudi Arabia", "Uruguay", "Iran", "New Zealand"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["England", "Croatia", "Ghana", "Panama"],
    "L": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
}

TEAM_TO_GROUP = {
    team: group_name
    for group_name, teams in GROUP_TEAMS.items()
    for team in teams
}


def _group_deadline(group_name):
    """Return first kickoff datetime for a group to lock qualifying picks."""
    teams = GROUP_TEAMS.get(group_name, [])
    first_match = (
        Match.query.filter(
            Match.home_team.in_(teams) | Match.away_team.in_(teams)
        )
        .filter(Match.match_date.isnot(None))
        .order_by(Match.match_date.asc())
        .first()
    )
    return first_match.match_date if first_match else None


def _podium_deadline():
    """Podium picks lock after the first match of the tournament starts."""
    first_match = Match.query.filter(Match.match_date.isnot(None)).order_by(Match.match_date.asc()).first()
    return first_match.match_date if first_match else None


def _utc_now_naive():
    """Return current UTC datetime as naive value to match stored DB datetimes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _allowed_competitions_for_user(user):
    """Return tuple (group_obj_or_none, allow_comp1, allow_comp2) for current user."""
    if getattr(user, "is_admin", False):
        return None, True, True

    group = user.group
    if not group:
        return None, False, False

    return group, bool(group.include_tournament1), bool(group.include_tournament2)



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
        group = Competition.query.filter_by(code=form.group_code.data.strip()).first()
        if not group:
            flash("Invalid group code.", "danger")
            return render_template("register.html", form=form)

        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            competition_id=group.id,
            email_verified=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account created! You can now log in.", "success")
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
    if current_user.is_admin:
        flash("Admins use the Results Entry page to enter outcomes.", "info")
        return redirect(url_for("main.admin_results", admin_tab="classic"))

    all_matches = Match.query.order_by(Match.match_date).all()
    user_group, allow_comp1, allow_comp2 = _allowed_competitions_for_user(current_user)
    if not (allow_comp1 or allow_comp2):
        flash("You are not assigned to a group yet.", "danger")
        return redirect(url_for("main.home"))

    selected_competition = request.args.get("competition", "classic")
    if selected_competition not in {"classic", "odds"}:
        selected_competition = "classic"
    if selected_competition == "classic" and not allow_comp1:
        selected_competition = "odds"
    if selected_competition == "odds" and not allow_comp2:
        selected_competition = "classic"

    selected_date = request.args.get("date", "all")

    available_dates = sorted({m.match_date.date() for m in all_matches if m.match_date})
    date_tabs = [{"value": "all", "label": "All"}] + [
        {"value": d.strftime("%Y-%m-%d"), "label": d.strftime("%b %d")} for d in available_dates
    ]

    if selected_date == "all":
        matches = all_matches
    else:
        try:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            matches = [m for m in all_matches if m.match_date and m.match_date.date() == target_date]
        except ValueError:
            selected_date = "all"
            matches = all_matches

    predictions = {p.match_id: p for p in Prediction.query.filter_by(user_id=current_user.id)}
    odds_predictions = {p.match_id: p for p in OddsPrediction.query.filter_by(user_id=current_user.id)}

    group_predictions = {
        p.group_name: p
        for p in GroupQualifierPrediction.query.filter_by(user_id=current_user.id).all()
    }
    group_results = {r.group_name: r for r in GroupResult.query.all()}

    group_cards = []
    now_utc = _utc_now_naive()
    for group_name, teams in GROUP_TEAMS.items():
        deadline = _group_deadline(group_name)
        locked = bool(deadline and now_utc >= deadline)
        group_cards.append(
            {
                "group_name": group_name,
                "teams": teams,
                "deadline": deadline,
                "locked": locked,
                "prediction": group_predictions.get(group_name),
                "result": group_results.get(group_name),
            }
        )

    podium_prediction = PodiumPrediction.query.filter_by(user_id=current_user.id).first()
    all_teams = sorted({m.home_team for m in all_matches}.union({m.away_team for m in all_matches}))
    podium_deadline = _podium_deadline()
    podium_locked = bool(podium_deadline and now_utc >= podium_deadline)

    return render_template(
        "matches.html",
        matches=matches,
        predictions=predictions,
        odds_predictions=odds_predictions,
        team_flag_codes=TEAM_FLAG_CODES,
        date_tabs=date_tabs,
        selected_date=selected_date,
        competition=selected_competition,
        group_cards=group_cards,
        podium_prediction=podium_prediction,
        podium_deadline=podium_deadline,
        podium_locked=podium_locked,
        all_teams=all_teams,
        allow_tournament1=allow_comp1,
        allow_tournament2=allow_comp2,
        user_group=user_group,
    )


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
    match = db.session.get(Match, match_id)
    if match is None:
        abort(404)
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    _, allow_comp1, _ = _allowed_competitions_for_user(current_user)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds"))

    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    prediction = Prediction.query.filter_by(user_id=current_user.id, match_id=match.id).first()
    try:
        home_score = int(request.form["predicted_home_score"])
        away_score = int(request.form["predicted_away_score"])
    except (KeyError, ValueError):
        flash("Invalid prediction values.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

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

    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))


@bp.route("/predict_outcome_inline/<int:match_id>", methods=["POST"])
@login_required
def predict_outcome_inline(match_id):
    """Submit or update Tournament 2 odds prediction for a match outcome."""
    match = db.session.get(Match, match_id)
    if match is None:
        abort(404)
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "odds")
    outcome = (request.form.get("predicted_outcome") or "").lower()
    _, _, allow_comp2 = _allowed_competitions_for_user(current_user)
    if not allow_comp2:
        flash("Your group does not include Competition 2.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="classic"))

    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    if outcome not in {"home", "draw", "away"}:
        flash("Invalid outcome. Choose home, draw or away.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    prediction = OddsPrediction.query.filter_by(user_id=current_user.id, match_id=match.id).first()
    if prediction:
        prediction.predicted_outcome = outcome
        flash("Odds prediction updated!", "success")
    else:
        db.session.add(
            OddsPrediction(user_id=current_user.id, match_id=match.id, predicted_outcome=outcome)
        )
        flash("Odds prediction saved!", "success")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
        print(e)

    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))


@bp.route("/predict_group_qualifiers", methods=["POST"])
@login_required
def predict_group_qualifiers():
    """Submit Tournament 1 group qualifier prediction for a group."""
    group_name = (request.form.get("group_name") or "").strip().upper()
    team_1 = (request.form.get("team_1") or "").strip()
    team_2 = (request.form.get("team_2") or "").strip()
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    _, allow_comp1, _ = _allowed_competitions_for_user(current_user)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds"))

    teams = GROUP_TEAMS.get(group_name)
    if not teams:
        flash("Invalid group selected.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    if team_1 == team_2:
        flash("Select two different teams for group qualifiers.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    if team_1 not in teams or team_2 not in teams:
        flash("Selected teams must belong to the chosen group.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    deadline = _group_deadline(group_name)
    if deadline and _utc_now_naive() >= deadline:
        flash(f"Group {group_name} is locked for qualifier picks.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    prediction = GroupQualifierPrediction.query.filter_by(
        user_id=current_user.id,
        group_name=group_name,
    ).first()

    if prediction:
        prediction.team_1 = team_1
        prediction.team_2 = team_2
        flash(f"Group {group_name} qualifiers updated!", "success")
    else:
        db.session.add(
            GroupQualifierPrediction(
                user_id=current_user.id,
                group_name=group_name,
                team_1=team_1,
                team_2=team_2,
            )
        )
        flash(f"Group {group_name} qualifiers saved!", "success")

    db.session.commit()
    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))


@bp.route("/predict_podium", methods=["POST"])
@login_required
def predict_podium():
    """Submit Tournament 1 podium prediction (champion, runner-up, third)."""
    champion_team = (request.form.get("champion_team") or "").strip()
    runner_up_team = (request.form.get("runner_up_team") or "").strip()
    third_place_team = (request.form.get("third_place_team") or "").strip()
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    _, allow_comp1, _ = _allowed_competitions_for_user(current_user)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds"))

    if len({champion_team, runner_up_team, third_place_team}) != 3:
        flash("Champion, runner-up and third place must be different teams.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    deadline = _podium_deadline()
    if deadline and _utc_now_naive() >= deadline:
        flash("Tournament podium picks are locked after the first game starts.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))

    prediction = PodiumPrediction.query.filter_by(user_id=current_user.id).first()
    if prediction:
        prediction.champion_team = champion_team
        prediction.runner_up_team = runner_up_team
        prediction.third_place_team = third_place_team
        flash("Podium picks updated!", "success")
    else:
        db.session.add(
            PodiumPrediction(
                user_id=current_user.id,
                champion_team=champion_team,
                runner_up_team=runner_up_team,
                third_place_team=third_place_team,
            )
        )
        flash("Podium picks saved!", "success")

    db.session.commit()
    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition))


# ---------------------------
# Rules
# ---------------------------
@bp.route("/rules")
@login_required
def rules():
    return render_template("rules.html")


# Leaderboard
# ---------------------------
@bp.route("/leaderboard")
@login_required
def leaderboard():
    """
    Display separate leaderboards for each competition.
    - Admin users are excluded from rankings
    """
    if current_user.is_admin:
        selected_group = request.args.get("group", "all")
        groups = Competition.query.order_by(Competition.name.asc()).all()
        group_tabs = [{"value": "all", "label": "All Groups"}] + [
            {"value": str(group.id), "label": group.name} for group in groups
        ]

        if selected_group == "all":
            users = User.query.filter_by(is_admin=False).all()
            group_label = "All Groups"
            show_t1 = True
            show_t2 = True
        else:
            if selected_group.isdigit():
                group_id = int(selected_group)
                selected_group_obj = db.session.get(Competition, group_id)
                if selected_group_obj:
                    users = User.query.filter_by(is_admin=False, competition_id=group_id).all()
                    group_label = selected_group_obj.name
                    show_t1 = bool(selected_group_obj.include_tournament1)
                    show_t2 = bool(selected_group_obj.include_tournament2)
                else:
                    users = User.query.filter_by(is_admin=False).all()
                    group_label = "All Groups"
                    selected_group = "all"
                    show_t1 = True
                    show_t2 = True
            else:
                users = User.query.filter_by(is_admin=False).all()
                group_label = "All Groups"
                selected_group = "all"
                show_t1 = True
                show_t2 = True
    else:
        if not current_user.group:
            flash("You are not assigned to a group yet.", "danger")
            return redirect(url_for("main.home"))
        users = User.query.filter_by(is_admin=False, competition_id=current_user.competition_id).all()
        group_label = current_user.group.name
        group_tabs = []
        selected_group = "all"
        show_t1 = bool(current_user.group.include_tournament1)
        show_t2 = bool(current_user.group.include_tournament2)

    classic_users = sorted(users, key=lambda u: u.tournament1_points, reverse=True)
    odds_users = sorted(users, key=lambda u: u.tournament2_points, reverse=True)
    return render_template(
        "leaderboard.html",
        classic_users=classic_users,
        odds_users=odds_users,
        group_label=group_label,
        group_tabs=group_tabs,
        selected_group=selected_group,
        show_tournament1=show_t1,
        show_tournament2=show_t2,
    )


# ---------------------------
# Admin Dashboard
# ---------------------------
@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    """
    Admin-only page for group management.
    - Only users with is_admin=True can access
    - Handles creating groups with signup code
    """
    if not getattr(current_user, "is_admin", False):
        return "Access denied", 403

    if request.method == "POST":
        form_action = request.form.get("form_action", "create_group")
        if form_action == "create_group":
            name = (request.form.get("group_name") or "").strip()
            code = (request.form.get("group_code") or "").strip()
            include_t1 = request.form.get("include_tournament1") == "on"
            include_t2 = request.form.get("include_tournament2") == "on"

            if not name or not code:
                flash("Group name and code are required.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            if not (include_t1 or include_t2):
                flash("Select at least one competition for the group.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            if Competition.query.filter_by(name=name).first():
                flash("Group name already exists.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            if Competition.query.filter_by(code=code).first():
                flash("Group code already exists.", "danger")
                return redirect(url_for("main.admin_dashboard"))

            db.session.add(
                Competition(
                    name=name,
                    code=code,
                    include_tournament1=include_t1,
                    include_tournament2=include_t2,
                )
            )
            db.session.commit()
            flash("Group created successfully.", "success")
            return redirect(url_for("main.admin_dashboard"))

        if form_action == "delete_group":
            group_id_raw = request.form.get("group_id", "")
            admin_password = request.form.get("admin_password", "")

            if not group_id_raw.isdigit():
                flash("Invalid group selected for deletion.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            if not current_user.check_password(admin_password):
                flash("Password confirmation failed. Group was not deleted.", "danger")
                return redirect(url_for("main.admin_dashboard"))

            group_id = int(group_id_raw)
            group = db.session.get(Competition, group_id)
            if not group:
                flash("Group not found.", "danger")
                return redirect(url_for("main.admin_dashboard"))

            group_users = User.query.filter_by(competition_id=group.id, is_admin=False).all()
            for user in group_users:
                Prediction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                OddsPrediction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                GroupQualifierPrediction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                PodiumPrediction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                db.session.delete(user)

            db.session.delete(group)
            db.session.commit()
            flash("Group deleted successfully.", "success")
            return redirect(url_for("main.admin_dashboard"))

    # GET request — render admin dashboard
    groups = Competition.query.order_by(Competition.name.asc()).all()
    return render_template("admin_dashboard.html", groups=groups)


@bp.route("/admin/results", methods=["GET", "POST"])
@login_required
def admin_results():
    """Admin-only page for entering results for Tournament 1 and Tournament 2."""
    if not getattr(current_user, "is_admin", False):
        return "Access denied", 403

    admin_tab = request.args.get("admin_tab", "classic")
    if admin_tab not in {"classic", "odds"}:
        admin_tab = "classic"

    if request.method == "POST":
        admin_tab = request.form.get("admin_tab", admin_tab)
        if admin_tab not in {"classic", "odds"}:
            admin_tab = "classic"

        editable_fields = {
            "classic": {"home_score", "away_score", "home_team", "away_team", "stadium", "stage", "group_name", "match_date"},
            "odds": {"home_score", "away_score", "home_odds", "draw_odds", "away_odds"},
        }

        for match_id, data in request.form.items():
            if "-" in match_id:
                field, mid = match_id.split("-")
                if field not in editable_fields[admin_tab]:
                    continue
                if not mid.isdigit():
                    continue
                mid = int(mid)
                match = db.session.get(Match, mid)
                if match:
                    try:
                        if field in {"home_score", "away_score"}:
                            val = int(data) if data != "" else None
                            if field == "home_score":
                                match.home_score = val
                            elif field == "away_score":
                                match.away_score = val
                        elif field == "home_team":
                            match.home_team = data.strip()
                        elif field == "away_team":
                            match.away_team = data.strip()
                        elif field == "stadium":
                            match.stadium = data.strip() if data.strip() else None
                        elif field == "stage":
                            match.stage = data.strip().lower() if data.strip() else "group"
                        elif field == "group_name":
                            match.group_name = data.strip().upper() if data.strip() else None
                        elif field == "match_date":
                            match.match_date = datetime.strptime(data, "%Y-%m-%dT%H:%M") if data else None
                        elif field in {"home_odds", "draw_odds", "away_odds"}:
                            odd_val = float(data) if data != "" else None
                            if field == "home_odds":
                                match.home_odds = odd_val
                            elif field == "draw_odds":
                                match.draw_odds = odd_val
                            elif field == "away_odds":
                                match.away_odds = odd_val
                    except ValueError:
                        continue

        if admin_tab == "classic":
            for group_name in GROUP_TEAMS:
                q1 = (request.form.get(f"group_result_q1-{group_name}") or "").strip()
                q2 = (request.form.get(f"group_result_q2-{group_name}") or "").strip()
                result = GroupResult.query.filter_by(group_name=group_name).first()
                if not result:
                    result = GroupResult(group_name=group_name)
                    db.session.add(result)
                result.qualified_team_1 = q1 or None
                result.qualified_team_2 = q2 or None

            outcome = TournamentOutcome.query.first()
            if not outcome:
                outcome = TournamentOutcome()
                db.session.add(outcome)
            outcome.champion_team = (request.form.get("outcome_champion") or "").strip() or None
            outcome.runner_up_team = (request.form.get("outcome_runner_up") or "").strip() or None
            outcome.third_place_team = (request.form.get("outcome_third") or "").strip() or None

        db.session.commit()
        update_all_points()
        flash("Results saved and user points recalculated!", "success")
        return redirect(url_for("main.admin_results", admin_tab=admin_tab))

    matches = Match.query.order_by(Match.match_date).all()
    group_results = {r.group_name: r for r in GroupResult.query.all()}
    outcome = TournamentOutcome.query.first()
    all_teams = sorted({m.home_team for m in matches}.union({m.away_team for m in matches}))
    return render_template(
        "admin_results.html",
        matches=matches,
        group_teams=GROUP_TEAMS,
        group_results=group_results,
        outcome=outcome,
        all_teams=all_teams,
        admin_tab=admin_tab,
    )
