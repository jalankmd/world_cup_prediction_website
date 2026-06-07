# app/routes.py
"""
Main route handlers for the World Cup Prediction Website.
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
    user_competitions,
)
from app.forms import RegisterForm, LoginForm, PredictionForm, JoinCompetitionForm
from app.scoring import update_all_points
from app import db
from datetime import datetime, timezone

bp = Blueprint("main", __name__)

# Sign-up closes Thursday June 11, 2026 at 11:59 PM Eastern (EDT = UTC-4)
# 11:59 PM EDT = 03:59 UTC on June 12
SIGNUP_DEADLINE_UTC = datetime(2026, 6, 12, 3, 59, 0)
SIGNUP_DEADLINE_DISPLAY = "Thursday, June 11 at 11:59 PM Eastern Time"

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
    first_match = Match.query.filter(Match.match_date.isnot(None)).order_by(Match.match_date.asc()).first()
    return first_match.match_date if first_match else None


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _allowed_competitions_for_user(user, competition_id=None):
    """Return (group, allow_comp1, allow_comp2) for the given competition context.

    If competition_id is provided, verify the user is a member and use that group.
    Otherwise fall back to the user's primary (registration) group.
    """
    if getattr(user, "is_admin", False):
        return None, True, True

    target_group = None
    if competition_id:
        for comp in user.competitions:
            if comp.id == competition_id:
                target_group = comp
                break

    if not target_group:
        target_group = user.group  # FK-based primary group

    if not target_group:
        return None, False, False

    return target_group, bool(target_group.include_tournament1), bool(target_group.include_tournament2)


def _t1_points_for_competition(user, competition_id):
    """Sum Tournament 1 points for a user scoped to a specific competition."""
    classic = sum(p.points for p in user.predictions if p.competition_id == competition_id)
    group_q = sum(p.points for p in user.group_qualifier_predictions if p.competition_id == competition_id)
    podium = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=competition_id).first()
    return classic + group_q + (podium.points if podium else 0)


def _t2_points_for_competition(user, competition_id):
    """Sum Tournament 2 points for a user scoped to a specific competition."""
    return int(round(sum(p.points for p in user.odds_predictions if p.competition_id == competition_id)))


# ---------------------------
# Home Page
# ---------------------------
@bp.route("/")
def home():
    signup_open = _utc_now_naive() < SIGNUP_DEADLINE_UTC
    return render_template(
        "home.html",
        signup_open=signup_open,
        signup_deadline_display=SIGNUP_DEADLINE_DISPLAY,
    )


# ---------------------------
# User Registration
# ---------------------------
@bp.route("/register", methods=["GET", "POST"])
def register():
    if _utc_now_naive() >= SIGNUP_DEADLINE_UTC:
        return render_template("register.html", signup_closed=True, form=None)

    form = RegisterForm()
    if form.validate_on_submit():
        group = Competition.query.filter_by(code=form.group_code.data.strip()).first()
        if not group:
            flash("Invalid group code.", "danger")
            return render_template("register.html", form=form, signup_closed=False)

        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            competition_id=group.id,
            email_verified=True,
        )
        user.set_password(form.password.data)
        user.competitions.append(group)
        db.session.add(user)
        db.session.commit()

        flash("Account created! You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form, signup_closed=False)


# ---------------------------
# Join Another Competition
# ---------------------------
@bp.route("/join", methods=["GET", "POST"])
@login_required
def join_competition():
    if current_user.is_admin:
        flash("Admins cannot join competitions.", "info")
        return redirect(url_for("main.home"))

    if _utc_now_naive() >= SIGNUP_DEADLINE_UTC:
        flash("Sign-up is now closed. Please contact the site owner to join.", "warning")
        return redirect(url_for("main.home"))

    form = JoinCompetitionForm()
    if form.validate_on_submit():
        group = Competition.query.filter_by(code=form.group_code.data.strip()).first()
        if not group:
            flash("Invalid group code.", "danger")
            return render_template("join_competition.html", form=form)

        if any(c.id == group.id for c in current_user.competitions):
            flash(f"You are already a member of '{group.name}'.", "info")
            return redirect(url_for("main.matches"))

        current_user.competitions.append(group)
        db.session.commit()
        flash(f"Joined '{group.name}'!", "success")
        return redirect(url_for("main.matches", group_id=group.id))

    return render_template("join_competition.html", form=form)


# ---------------------------
# User Login
# ---------------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
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
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


# ---------------------------
# Match List
# ---------------------------
@bp.route("/matches")
@login_required
def matches():
    if current_user.is_admin:
        flash("Admins use the Results Entry page to enter outcomes.", "info")
        return redirect(url_for("main.admin_results", admin_tab="classic"))

    all_matches = Match.query.order_by(Match.match_date).all()

    # Determine the active competition context
    group_id = request.args.get("group_id", type=int) or current_user.competition_id
    user_group, allow_comp1, allow_comp2 = _allowed_competitions_for_user(current_user, group_id)
    if not (allow_comp1 or allow_comp2):
        flash("You are not assigned to a group yet.", "danger")
        return redirect(url_for("main.home"))

    active_group_id = user_group.id

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
        filtered_matches = all_matches
    else:
        try:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            filtered_matches = [m for m in all_matches if m.match_date and m.match_date.date() == target_date]
        except ValueError:
            selected_date = "all"
            filtered_matches = all_matches

    # Load predictions scoped to the active competition
    predictions = {
        p.match_id: p
        for p in Prediction.query.filter_by(user_id=current_user.id, competition_id=active_group_id)
    }
    odds_predictions = {
        p.match_id: p
        for p in OddsPrediction.query.filter_by(user_id=current_user.id, competition_id=active_group_id)
    }

    group_predictions = {
        p.group_name: p
        for p in GroupQualifierPrediction.query.filter_by(
            user_id=current_user.id, competition_id=active_group_id
        ).all()
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

    podium_prediction = PodiumPrediction.query.filter_by(
        user_id=current_user.id, competition_id=active_group_id
    ).first()
    all_teams = sorted({m.home_team for m in all_matches}.union({m.away_team for m in all_matches}))
    podium_deadline = _podium_deadline()
    podium_locked = bool(podium_deadline and now_utc >= podium_deadline)

    user_all_competitions = list(current_user.competitions)

    return render_template(
        "matches.html",
        matches=filtered_matches,
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
        active_group_id=active_group_id,
        user_all_competitions=user_all_competitions,
    )


# ---------------------------
# Inline Prediction Submission
# ---------------------------
@bp.route("/predict_inline/<int:match_id>", methods=["POST"])
@login_required
def predict_inline(match_id):
    match = db.session.get(Match, match_id)
    if match is None:
        abort(404)
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    group_id = request.form.get("group_id", type=int) or current_user.competition_id

    _, allow_comp1, _ = _allowed_competitions_for_user(current_user, group_id)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds", group_id=group_id))

    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    prediction = Prediction.query.filter_by(
        user_id=current_user.id, match_id=match.id, competition_id=group_id
    ).first()
    try:
        home_score = int(request.form["predicted_home_score"])
        away_score = int(request.form["predicted_away_score"])
    except (KeyError, ValueError):
        flash("Invalid prediction values.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    if prediction:
        prediction.predicted_home_score = home_score
        prediction.predicted_away_score = away_score
        flash("Prediction updated!", "success")
    else:
        db.session.add(Prediction(
            user_id=current_user.id,
            match_id=match.id,
            competition_id=group_id,
            predicted_home_score=home_score,
            predicted_away_score=away_score,
        ))
        flash("Prediction saved!", "success")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
        print(e)

    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))


@bp.route("/predict_outcome_inline/<int:match_id>", methods=["POST"])
@login_required
def predict_outcome_inline(match_id):
    match = db.session.get(Match, match_id)
    if match is None:
        abort(404)
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "odds")
    group_id = request.form.get("group_id", type=int) or current_user.competition_id
    outcome = (request.form.get("predicted_outcome") or "").lower()

    _, _, allow_comp2 = _allowed_competitions_for_user(current_user, group_id)
    if not allow_comp2:
        flash("Your group does not include Competition 2.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="classic", group_id=group_id))

    if match.is_locked() or match.is_finished():
        flash("Match is locked, cannot submit prediction.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    if outcome not in {"home", "draw", "away"}:
        flash("Invalid outcome. Choose home, draw or away.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    prediction = OddsPrediction.query.filter_by(
        user_id=current_user.id, match_id=match.id, competition_id=group_id
    ).first()
    if prediction:
        prediction.predicted_outcome = outcome
        flash("Odds prediction updated!", "success")
    else:
        db.session.add(OddsPrediction(
            user_id=current_user.id,
            match_id=match.id,
            competition_id=group_id,
            predicted_outcome=outcome,
        ))
        flash("Odds prediction saved!", "success")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Database error. Please try again.", "danger")
        print(e)

    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))


@bp.route("/predict_group_qualifiers", methods=["POST"])
@login_required
def predict_group_qualifiers():
    group_name = (request.form.get("group_name") or "").strip().upper()
    team_1 = (request.form.get("team_1") or "").strip()
    team_2 = (request.form.get("team_2") or "").strip()
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    group_id = request.form.get("group_id", type=int) or current_user.competition_id

    _, allow_comp1, _ = _allowed_competitions_for_user(current_user, group_id)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds", group_id=group_id))

    teams = GROUP_TEAMS.get(group_name)
    if not teams:
        flash("Invalid group selected.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    if team_1 == team_2:
        flash("Select two different teams for group qualifiers.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    if team_1 not in teams or team_2 not in teams:
        flash("Selected teams must belong to the chosen group.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    deadline = _group_deadline(group_name)
    if deadline and _utc_now_naive() >= deadline:
        flash(f"Group {group_name} is locked for qualifier picks.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    prediction = GroupQualifierPrediction.query.filter_by(
        user_id=current_user.id,
        group_name=group_name,
        competition_id=group_id,
    ).first()

    if prediction:
        prediction.team_1 = team_1
        prediction.team_2 = team_2
        flash(f"Group {group_name} qualifiers updated!", "success")
    else:
        db.session.add(GroupQualifierPrediction(
            user_id=current_user.id,
            group_name=group_name,
            competition_id=group_id,
            team_1=team_1,
            team_2=team_2,
        ))
        flash(f"Group {group_name} qualifiers saved!", "success")

    db.session.commit()
    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))


@bp.route("/predict_podium", methods=["POST"])
@login_required
def predict_podium():
    champion_team = (request.form.get("champion_team") or "").strip()
    runner_up_team = (request.form.get("runner_up_team") or "").strip()
    third_place_team = (request.form.get("third_place_team") or "").strip()
    selected_date = request.form.get("selected_date", "all")
    selected_competition = request.form.get("competition", "classic")
    group_id = request.form.get("group_id", type=int) or current_user.competition_id

    _, allow_comp1, _ = _allowed_competitions_for_user(current_user, group_id)
    if not allow_comp1:
        flash("Your group does not include Competition 1.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition="odds", group_id=group_id))

    if len({champion_team, runner_up_team, third_place_team}) != 3:
        flash("Champion, runner-up and third place must be different teams.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    deadline = _podium_deadline()
    if deadline and _utc_now_naive() >= deadline:
        flash("Tournament podium picks are locked after the first game starts.", "danger")
        return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))

    prediction = PodiumPrediction.query.filter_by(user_id=current_user.id, competition_id=group_id).first()
    if prediction:
        prediction.champion_team = champion_team
        prediction.runner_up_team = runner_up_team
        prediction.third_place_team = third_place_team
        flash("Podium picks updated!", "success")
    else:
        db.session.add(PodiumPrediction(
            user_id=current_user.id,
            competition_id=group_id,
            champion_team=champion_team,
            runner_up_team=runner_up_team,
            third_place_team=third_place_team,
        ))
        flash("Podium picks saved!", "success")

    db.session.commit()
    return redirect(url_for("main.matches", date=selected_date, competition=selected_competition, group_id=group_id))


# ---------------------------
# Rules
# ---------------------------
@bp.route("/rules")
@login_required
def rules():
    competitions_prize_info = []
    if not current_user.is_admin:
        for comp in current_user.competitions:
            if comp.entry_fee and comp.entry_fee > 0:
                member_count = sum(1 for u in comp.members if not u.is_admin)
                total = comp.entry_fee * member_count
                competitions_prize_info.append({
                    "name": comp.name,
                    "entry_fee": comp.entry_fee,
                    "member_count": member_count,
                    "total_pool": total,
                    "comp1_winner": total * 0.50,
                    "comp1_second": total * 0.20,
                    "comp2_winner": total * 0.30,
                    "include_tournament1": comp.include_tournament1,
                    "include_tournament2": comp.include_tournament2,
                })
    return render_template("rules.html", competitions_prize_info=competitions_prize_info)


# ---------------------------
# Leaderboard
# ---------------------------
@bp.route("/leaderboard")
@login_required
def leaderboard():
    """Display leaderboards per competition group."""
    if current_user.is_admin:
        selected_group = request.args.get("group", "all")
        groups = Competition.query.order_by(Competition.name.asc()).all()
        group_tabs = [{"value": "all", "label": "All Groups"}] + [
            {"value": str(g.id), "label": g.name} for g in groups
        ]

        if selected_group == "all":
            users = User.query.filter_by(is_admin=False).all()
            group_label = "All Groups"
            show_t1 = True
            show_t2 = True
            t1_points = {u.id: u.tournament1_points for u in users}
            t2_points = {u.id: u.tournament2_points for u in users}
        else:
            if selected_group.isdigit():
                group_id = int(selected_group)
                selected_group_obj = db.session.get(Competition, group_id)
                if selected_group_obj:
                    users = [u for u in selected_group_obj.members if not u.is_admin]
                    group_label = selected_group_obj.name
                    show_t1 = bool(selected_group_obj.include_tournament1)
                    show_t2 = bool(selected_group_obj.include_tournament2)
                    t1_points = {u.id: _t1_points_for_competition(u, group_id) for u in users}
                    t2_points = {u.id: _t2_points_for_competition(u, group_id) for u in users}
                else:
                    users = User.query.filter_by(is_admin=False).all()
                    group_label = "All Groups"
                    selected_group = "all"
                    show_t1 = True
                    show_t2 = True
                    t1_points = {u.id: u.tournament1_points for u in users}
                    t2_points = {u.id: u.tournament2_points for u in users}
            else:
                users = User.query.filter_by(is_admin=False).all()
                group_label = "All Groups"
                selected_group = "all"
                show_t1 = True
                show_t2 = True
                t1_points = {u.id: u.tournament1_points for u in users}
                t2_points = {u.id: u.tournament2_points for u in users}

        classic_users = sorted(users, key=lambda u: t1_points[u.id], reverse=True)
        odds_users = sorted(users, key=lambda u: t2_points[u.id], reverse=True)
        return render_template(
            "leaderboard.html",
            classic_users=classic_users,
            odds_users=odds_users,
            t1_points=t1_points,
            t2_points=t2_points,
            group_label=group_label,
            group_tabs=group_tabs,
            selected_group=selected_group,
            show_tournament1=show_t1,
            show_tournament2=show_t2,
        )

    # Non-admin path
    user_comps = list(current_user.competitions)
    if not user_comps:
        flash("You are not assigned to a group yet.", "danger")
        return redirect(url_for("main.home"))

    # Which competition to display
    selected_comp_id = request.args.get("group", type=int)
    if not selected_comp_id or not any(c.id == selected_comp_id for c in user_comps):
        selected_comp_id = current_user.competition_id or user_comps[0].id

    selected_comp = next(c for c in user_comps if c.id == selected_comp_id)
    users = [u for u in selected_comp.members if not u.is_admin]
    group_label = selected_comp.name
    show_t1 = bool(selected_comp.include_tournament1)
    show_t2 = bool(selected_comp.include_tournament2)

    t1_points = {u.id: _t1_points_for_competition(u, selected_comp_id) for u in users}
    t2_points = {u.id: _t2_points_for_competition(u, selected_comp_id) for u in users}
    classic_users = sorted(users, key=lambda u: t1_points[u.id], reverse=True)
    odds_users = sorted(users, key=lambda u: t2_points[u.id], reverse=True)

    # Tabs if user is in multiple groups
    if len(user_comps) > 1:
        group_tabs = [{"value": str(c.id), "label": c.name} for c in user_comps]
        selected_group = str(selected_comp_id)
    else:
        group_tabs = []
        selected_group = "all"

    return render_template(
        "leaderboard.html",
        classic_users=classic_users,
        odds_users=odds_users,
        t1_points=t1_points,
        t2_points=t2_points,
        group_label=group_label,
        group_tabs=group_tabs,
        selected_group=selected_group,
        show_tournament1=show_t1,
        show_tournament2=show_t2,
    )


# ---------------------------
# Admin Predictions View
# ---------------------------
@bp.route("/admin/predictions")
@login_required
def admin_predictions():
    if not getattr(current_user, "is_admin", False):
        return "Access denied", 403

    groups = Competition.query.order_by(Competition.name.asc()).all()

    selected_group_id = request.args.get("group", type=int)
    if not selected_group_id and groups:
        selected_group_id = groups[0].id

    pred_tab = request.args.get("tab", "classic")
    if pred_tab not in {"classic", "odds", "qualifiers", "podium"}:
        pred_tab = "classic"

    selected_comp = db.session.get(Competition, selected_group_id) if selected_group_id else None
    users = []
    pred_map = {}

    if selected_comp:
        users = sorted(
            [u for u in selected_comp.members if not u.is_admin],
            key=lambda u: u.username.lower(),
        )

        if pred_tab == "classic":
            preds = Prediction.query.filter_by(competition_id=selected_group_id).all()
            pred_map = {(p.user_id, p.match_id): p for p in preds}
        elif pred_tab == "odds":
            preds = OddsPrediction.query.filter_by(competition_id=selected_group_id).all()
            pred_map = {(p.user_id, p.match_id): p for p in preds}
        elif pred_tab == "qualifiers":
            preds = GroupQualifierPrediction.query.filter_by(competition_id=selected_group_id).all()
            pred_map = {(p.user_id, p.group_name): p for p in preds}
        elif pred_tab == "podium":
            preds = PodiumPrediction.query.filter_by(competition_id=selected_group_id).all()
            pred_map = {p.user_id: p for p in preds}

    all_matches = Match.query.order_by(Match.match_date).all()
    group_tabs = [{"value": str(g.id), "label": g.name} for g in groups]

    return render_template(
        "admin_predictions.html",
        group_tabs=group_tabs,
        selected_group_id=str(selected_group_id) if selected_group_id else None,
        selected_comp=selected_comp,
        users=users,
        matches=all_matches,
        pred_tab=pred_tab,
        pred_map=pred_map,
        group_teams=GROUP_TEAMS,
    )


# ---------------------------
# Admin Dashboard
# ---------------------------
@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin_dashboard():
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

            try:
                entry_fee = float(request.form.get("entry_fee") or 0)
                if entry_fee < 0:
                    entry_fee = 0.0
            except ValueError:
                entry_fee = 0.0

            db.session.add(Competition(
                name=name,
                code=code,
                include_tournament1=include_t1,
                include_tournament2=include_t2,
                entry_fee=entry_fee,
            ))
            db.session.commit()
            flash("Group created successfully.", "success")
            return redirect(url_for("main.admin_dashboard"))

        if form_action == "update_group_fee":
            group_id_raw = request.form.get("group_id", "")
            if not group_id_raw.isdigit():
                flash("Invalid group.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            try:
                fee = float(request.form.get("entry_fee") or 0)
                if fee < 0:
                    fee = 0.0
            except ValueError:
                flash("Invalid entry fee value.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            group = db.session.get(Competition, int(group_id_raw))
            if not group:
                flash("Group not found.", "danger")
                return redirect(url_for("main.admin_dashboard"))
            group.entry_fee = fee
            db.session.commit()
            label = f"${fee:.2f} CAD" if fee > 0 else "Free"
            flash(f"Entry fee for '{group.name}' set to {label}.", "success")
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

            # Delete all predictions tagged with this competition
            Prediction.query.filter_by(competition_id=group_id).delete(synchronize_session=False)
            OddsPrediction.query.filter_by(competition_id=group_id).delete(synchronize_session=False)
            GroupQualifierPrediction.query.filter_by(competition_id=group_id).delete(synchronize_session=False)
            PodiumPrediction.query.filter_by(competition_id=group_id).delete(synchronize_session=False)

            # Remove M2M memberships for this competition
            db.session.execute(
                user_competitions.delete().where(user_competitions.c.competition_id == group_id)
            )

            # Delete users whose primary group was this competition
            primary_users = User.query.filter_by(competition_id=group_id, is_admin=False).all()
            for user in primary_users:
                db.session.delete(user)

            db.session.delete(group)
            db.session.commit()
            flash("Group deleted successfully.", "success")
            return redirect(url_for("main.admin_dashboard"))

    groups = Competition.query.order_by(Competition.name.asc()).all()
    return render_template("admin_dashboard.html", groups=groups)


@bp.route("/admin/results", methods=["GET", "POST"])
@login_required
def admin_results():
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
