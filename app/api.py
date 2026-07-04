"""JSON API Blueprint — consumed by the React Native mobile app."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import (
    User, Match, Prediction, OddsPrediction, GroupQualifierPrediction,
    GroupResult, PodiumPrediction, TournamentOutcome, RankSnapshot, Competition,
)
from app import db
from datetime import datetime, timezone, timedelta

api_bp = Blueprint("api", __name__, url_prefix="/api")

SIGNUP_DEADLINE_UTC = datetime(2026, 6, 11, 15, 59, 0)

TEAM_FLAG_CODES = {
    "Algeria": "dz", "Argentina": "ar", "Australia": "au", "Austria": "at",
    "Belgium": "be", "Bosnia and Herzegovina": "ba", "DR Congo": "cd", "Iraq": "iq",
    "Brazil": "br", "Canada": "ca", "Cape Verde": "cv", "Colombia": "co",
    "Croatia": "hr", "Curaçao": "cw", "Czech Republic": "cz", "Ecuador": "ec",
    "Egypt": "eg", "England": "gb-eng", "France": "fr", "Germany": "de",
    "Ghana": "gh", "Haiti": "ht", "Iran": "ir", "Ivory Coast": "ci",
    "Italy": "it", "Japan": "jp", "Jordan": "jo", "Mexico": "mx",
    "Morocco": "ma", "Netherlands": "nl", "New Zealand": "nz", "Norway": "no",
    "Panama": "pa", "Paraguay": "py", "Portugal": "pt", "Qatar": "qa",
    "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn", "Serbia": "rs",
    "South Africa": "za", "South Korea": "kr", "Spain": "es", "Sweden": "se",
    "Switzerland": "ch", "Tunisia": "tn", "Turkey": "tr", "USA": "us",
    "Uruguay": "uy", "Uzbekistan": "uz", "Wales": "gb-wls",
}

GROUP_TEAMS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def _t1_points_for_competition(user, competition_id):
    classic = sum(p.points for p in user.predictions if p.competition_id == competition_id)
    group_q = sum(p.points for p in user.group_qualifier_predictions if p.competition_id == competition_id)
    podium = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=competition_id).first()
    return classic + group_q + (podium.points if podium else 0)


def _t2_points_for_competition(user, competition_id):
    return round(sum(p.points for p in user.odds_predictions if p.competition_id == competition_id), 1)


def _assign_ranks(users_sorted, points_dict):
    ranks = {}
    current_rank = 1
    prev_pts = None
    for i, u in enumerate(users_sorted):
        pts = points_dict[u.id]
        if pts != prev_pts:
            current_rank = i + 1
        ranks[u.id] = current_rank
        prev_pts = pts
    return ranks


def _group_deadline(group_name):
    teams = GROUP_TEAMS.get(group_name, [])
    first_match = (
        Match.query.filter(Match.home_team.in_(teams) | Match.away_team.in_(teams))
        .filter(Match.match_date.isnot(None))
        .order_by(Match.match_date.asc())
        .first()
    )
    return first_match.match_date if first_match else None


def _podium_deadline():
    first_match = Match.query.filter(Match.match_date.isnot(None)).order_by(Match.match_date.asc()).first()
    return first_match.match_date if first_match else None


def _allowed_competitions_for_user(user, competition_id=None):
    if getattr(user, "is_admin", False):
        return None, True, True
    target_group = None
    if competition_id:
        for comp in user.competitions:
            if comp.id == competition_id:
                target_group = comp
                break
    if not target_group:
        target_group = user.group
    if not target_group:
        return None, False, False
    return target_group, bool(target_group.include_tournament1), bool(target_group.include_tournament2)


def _serialize_match(match, classic_pred=None, odds_pred=None):
    return {
        "id": match.id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "home_flag": TEAM_FLAG_CODES.get(match.home_team, ""),
        "away_flag": TEAM_FLAG_CODES.get(match.away_team, ""),
        "stage": match.stage,
        "group_name": match.group_name,
        "match_date": match.match_date.strftime("%Y-%m-%dT%H:%M:%SZ") if match.match_date else None,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "home_odds": match.home_odds,
        "draw_odds": match.draw_odds,
        "away_odds": match.away_odds,
        "is_locked": match.is_locked(),
        "is_finished": match.is_finished(),
        "advancing_team": match.advancing_team,
        "classic_prediction": {
            "predicted_home_score": classic_pred.predicted_home_score,
            "predicted_away_score": classic_pred.predicted_away_score,
            "predicted_qualifier": classic_pred.predicted_qualifier,
            "points": classic_pred.points,
        } if classic_pred else None,
        "odds_prediction": {
            "predicted_outcome": odds_pred.predicted_outcome,
            "points": float(odds_pred.points),
        } if odds_pred else None,
    }


# ── Auth ───────────────────────────────────────────────────────────────────────

@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
        },
    })


@api_bp.route("/auth/register", methods=["POST"])
def register():
    if _utc_now_naive() >= SIGNUP_DEADLINE_UTC:
        return jsonify({"error": "Sign-up is now closed."}), 403
    data = request.get_json() or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    group_code = (data.get("group_code") or "").strip()
    if not all([first_name, last_name, username, password, group_code]):
        return jsonify({"error": "All fields are required"}), 400
    group = Competition.query.filter_by(code=group_code).first()
    if not group:
        return jsonify({"error": "Invalid group code"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400
    user = User(
        first_name=first_name, last_name=last_name, username=username,
        competition_id=group.id, email_verified=True,
    )
    user.set_password(password)
    user.competitions.append(group)
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error. Please try again."}), 500
    return jsonify({"message": "Account created! You can now log in."}), 201


# ── User / Settings ────────────────────────────────────────────────────────────

@api_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = _get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_admin": user.is_admin,
        "favourite_team": user.favourite_team,
        "primary_competition_id": user.competition_id,
        "competitions": [
            {"id": c.id, "name": c.name, "include_tournament1": c.include_tournament1, "include_tournament2": c.include_tournament2}
            for c in user.competitions
        ],
    })


@api_bp.route("/settings/join_group", methods=["POST"])
@jwt_required()
def join_group():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    if _utc_now_naive() >= SIGNUP_DEADLINE_UTC:
        return jsonify({"error": "Sign-up is now closed."}), 403
    data = request.get_json() or {}
    group_code = (data.get("group_code") or "").strip()
    if not group_code:
        return jsonify({"error": "Group code required"}), 400
    group = Competition.query.filter_by(code=group_code).first()
    if not group:
        return jsonify({"error": "Invalid group code"}), 400
    if any(c.id == group.id for c in user.competitions):
        return jsonify({"error": f"You are already a member of '{group.name}'"}), 400
    user.competitions.append(group)
    db.session.commit()
    return jsonify({"message": f"Joined '{group.name}'!"})


# ── Home ───────────────────────────────────────────────────────────────────────

@api_bp.route("/home", methods=["GET"])
@jwt_required()
def home():
    user = _get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    podium_picks = None
    celebrating_teams = []

    if not user.is_admin:
        comp_id = user.competition_id
        if comp_id:
            podium_picks = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=comp_id).first()
        if not podium_picks:
            for comp in user.competitions:
                podium_picks = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=comp.id).first()
                if podium_picks:
                    break

        if podium_picks:
            pick_teams = [podium_picks.champion_team, podium_picks.runner_up_team, podium_picks.third_place_team]
            qualified_teams = set()
            for r in GroupResult.query.all():
                if r.qualified_team_1:
                    qualified_teams.add(r.qualified_team_1)
                if r.qualified_team_2:
                    qualified_teams.add(r.qualified_team_2)
            for team in pick_teams:
                recent = (
                    Match.query.filter(
                        (Match.home_team == team) | (Match.away_team == team),
                        Match.home_score.isnot(None), Match.away_score.isnot(None),
                    ).order_by(Match.match_date.desc()).first()
                )
                won = recent and (
                    (recent.home_team == team and recent.home_score > recent.away_score) or
                    (recent.away_team == team and recent.away_score > recent.home_score)
                )
                if won or team in qualified_teams:
                    celebrating_teams.append(team)

    return jsonify({
        "signup_open": _utc_now_naive() < SIGNUP_DEADLINE_UTC,
        "podium_picks": {
            "champion_team": podium_picks.champion_team,
            "champion_flag": TEAM_FLAG_CODES.get(podium_picks.champion_team, ""),
            "runner_up_team": podium_picks.runner_up_team,
            "runner_up_flag": TEAM_FLAG_CODES.get(podium_picks.runner_up_team, ""),
            "third_place_team": podium_picks.third_place_team,
            "third_place_flag": TEAM_FLAG_CODES.get(podium_picks.third_place_team, ""),
            "points": podium_picks.points,
        } if podium_picks else None,
        "celebrating_teams": celebrating_teams,
    })


# ── Matches ────────────────────────────────────────────────────────────────────

@api_bp.route("/matches", methods=["GET"])
@jwt_required()
def matches():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403

    group_id = request.args.get("group_id", type=int) or user.competition_id
    user_group, allow_comp1, allow_comp2 = _allowed_competitions_for_user(user, group_id)
    if not (allow_comp1 or allow_comp2):
        return jsonify({"error": "You are not assigned to a group yet"}), 400

    active_group_id = user_group.id
    _edt = timedelta(hours=-4)

    all_matches = Match.query.filter(
        Match.stage.in_(["group", "round_of_32", "round_of_16"])
    ).order_by(Match.match_date).all()

    available_dates = sorted({(m.match_date + _edt).date() for m in all_matches if m.match_date})
    date_tabs = [{"value": "all", "label": "All"}] + [
        {"value": d.strftime("%Y-%m-%d"), "label": d.strftime("%b %d")} for d in available_dates
    ]

    selected_date = request.args.get("date", "all")
    if selected_date == "all":
        filtered_matches = all_matches
    else:
        try:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            filtered_matches = [m for m in all_matches if m.match_date and (m.match_date + _edt).date() == target_date]
        except ValueError:
            filtered_matches = all_matches

    classic_preds = {
        p.match_id: p
        for p in Prediction.query.filter_by(user_id=user.id, competition_id=active_group_id)
    }
    odds_preds = {
        p.match_id: p
        for p in OddsPrediction.query.filter_by(user_id=user.id, competition_id=active_group_id)
    }
    group_qualifier_preds = {
        p.group_name: p
        for p in GroupQualifierPrediction.query.filter_by(user_id=user.id, competition_id=active_group_id).all()
    }
    group_results = {r.group_name: r for r in GroupResult.query.all()}

    now_utc = _utc_now_naive()
    group_cards = []
    for group_name, teams in GROUP_TEAMS.items():
        deadline = _group_deadline(group_name)
        locked = bool(deadline and now_utc >= deadline)
        pred = group_qualifier_preds.get(group_name)
        result = group_results.get(group_name)
        group_cards.append({
            "group_name": group_name,
            "teams": [{"name": t, "flag": TEAM_FLAG_CODES.get(t, "")} for t in teams],
            "deadline": deadline.strftime("%Y-%m-%dT%H:%M:%SZ") if deadline else None,
            "locked": locked,
            "prediction": {"team_1": pred.team_1, "team_2": pred.team_2, "points": pred.points} if pred else None,
            "result": {"qualified_team_1": result.qualified_team_1, "qualified_team_2": result.qualified_team_2} if result else None,
        })

    podium_prediction = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=active_group_id).first()
    all_teams_list = sorted({m.home_team for m in all_matches} | {m.away_team for m in all_matches})
    podium_deadline = _podium_deadline()
    podium_locked = bool(podium_deadline and now_utc >= podium_deadline)

    return jsonify({
        "matches": [_serialize_match(m, classic_preds.get(m.id), odds_preds.get(m.id)) for m in filtered_matches],
        "date_tabs": date_tabs,
        "group_cards": group_cards,
        "podium_prediction": {
            "champion_team": podium_prediction.champion_team,
            "runner_up_team": podium_prediction.runner_up_team,
            "third_place_team": podium_prediction.third_place_team,
            "points": podium_prediction.points,
        } if podium_prediction else None,
        "podium_deadline": podium_deadline.strftime("%Y-%m-%dT%H:%M:%SZ") if podium_deadline else None,
        "podium_locked": podium_locked,
        "all_teams": [{"name": t, "flag": TEAM_FLAG_CODES.get(t, "")} for t in all_teams_list],
        "active_group_id": active_group_id,
        "allow_tournament1": allow_comp1,
        "allow_tournament2": allow_comp2,
        "user_competitions": [{"id": c.id, "name": c.name} for c in user.competitions],
    })


@api_bp.route("/matches/<int:match_id>/predict", methods=["POST"])
@jwt_required()
def predict_match(match_id):
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    match = db.session.get(Match, match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404
    data = request.get_json() or {}
    group_id = data.get("group_id") or user.competition_id
    _, allow_comp1, _ = _allowed_competitions_for_user(user, group_id)
    if not allow_comp1:
        return jsonify({"error": "Your group does not include Competition 1"}), 400
    if match.is_locked() or match.is_finished():
        return jsonify({"error": "Match is locked"}), 400
    try:
        home_score = int(data["predicted_home_score"])
        away_score = int(data["predicted_away_score"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid score values"}), 400
    qualifier_val = None
    if match.stage in {"round_of_32", "round_of_16"}:
        q = (data.get("predicted_qualifier") or "").strip()
        if home_score != away_score:
            qualifier_val = match.home_team if home_score > away_score else match.away_team
        elif q in {match.home_team, match.away_team}:
            qualifier_val = q
    prediction = Prediction.query.filter_by(user_id=user.id, match_id=match_id, competition_id=group_id).first()
    if prediction:
        prediction.predicted_home_score = home_score
        prediction.predicted_away_score = away_score
        if match.stage in {"round_of_32", "round_of_16"}:
            prediction.predicted_qualifier = qualifier_val
        msg = "Prediction updated!"
    else:
        db.session.add(Prediction(
            user_id=user.id, match_id=match_id, competition_id=group_id,
            predicted_home_score=home_score, predicted_away_score=away_score,
            predicted_qualifier=qualifier_val,
        ))
        msg = "Prediction saved!"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": msg})


@api_bp.route("/matches/<int:match_id>/predict_odds", methods=["POST"])
@jwt_required()
def predict_match_odds(match_id):
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    match = db.session.get(Match, match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404
    data = request.get_json() or {}
    group_id = data.get("group_id") or user.competition_id
    _, _, allow_comp2 = _allowed_competitions_for_user(user, group_id)
    if not allow_comp2:
        return jsonify({"error": "Your group does not include Competition 2"}), 400
    if match.is_locked() or match.is_finished():
        return jsonify({"error": "Match is locked"}), 400
    outcome = (data.get("predicted_outcome") or "").lower()
    if outcome not in {"home", "draw", "away"}:
        return jsonify({"error": "Invalid outcome. Choose home, draw or away"}), 400
    prediction = OddsPrediction.query.filter_by(user_id=user.id, match_id=match_id, competition_id=group_id).first()
    if prediction:
        prediction.predicted_outcome = outcome
        msg = "Prediction updated!"
    else:
        db.session.add(OddsPrediction(
            user_id=user.id, match_id=match_id, competition_id=group_id,
            predicted_outcome=outcome,
        ))
        msg = "Prediction saved!"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": msg})


@api_bp.route("/qualifiers", methods=["POST"])
@jwt_required()
def predict_qualifiers():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    data = request.get_json() or {}
    group_name = (data.get("group_name") or "").strip().upper()
    team_1 = (data.get("team_1") or "").strip()
    team_2 = (data.get("team_2") or "").strip()
    group_id = data.get("group_id") or user.competition_id
    _, allow_comp1, _ = _allowed_competitions_for_user(user, group_id)
    if not allow_comp1:
        return jsonify({"error": "Your group does not include Competition 1"}), 400
    teams = GROUP_TEAMS.get(group_name)
    if not teams:
        return jsonify({"error": "Invalid group"}), 400
    if team_1 == team_2 or team_1 not in teams or team_2 not in teams:
        return jsonify({"error": "Invalid teams for this group"}), 400
    deadline = _group_deadline(group_name)
    if deadline and _utc_now_naive() >= deadline:
        return jsonify({"error": f"Group {group_name} is locked"}), 400
    prediction = GroupQualifierPrediction.query.filter_by(
        user_id=user.id, group_name=group_name, competition_id=group_id
    ).first()
    if prediction:
        prediction.team_1 = team_1
        prediction.team_2 = team_2
        msg = f"Group {group_name} qualifiers updated!"
    else:
        db.session.add(GroupQualifierPrediction(
            user_id=user.id, group_name=group_name, competition_id=group_id,
            team_1=team_1, team_2=team_2,
        ))
        msg = f"Group {group_name} qualifiers saved!"
    db.session.commit()
    return jsonify({"message": msg})


@api_bp.route("/podium", methods=["POST"])
@jwt_required()
def predict_podium():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    data = request.get_json() or {}
    champion_team = (data.get("champion_team") or "").strip()
    runner_up_team = (data.get("runner_up_team") or "").strip()
    third_place_team = (data.get("third_place_team") or "").strip()
    group_id = data.get("group_id") or user.competition_id
    _, allow_comp1, _ = _allowed_competitions_for_user(user, group_id)
    if not allow_comp1:
        return jsonify({"error": "Your group does not include Competition 1"}), 400
    if len({champion_team, runner_up_team, third_place_team}) != 3:
        return jsonify({"error": "Champion, runner-up and third place must be different teams"}), 400
    deadline = _podium_deadline()
    if deadline and _utc_now_naive() >= deadline:
        return jsonify({"error": "Podium picks are locked"}), 400
    prediction = PodiumPrediction.query.filter_by(user_id=user.id, competition_id=group_id).first()
    if prediction:
        prediction.champion_team = champion_team
        prediction.runner_up_team = runner_up_team
        prediction.third_place_team = third_place_team
        msg = "Podium picks updated!"
    else:
        db.session.add(PodiumPrediction(
            user_id=user.id, competition_id=group_id,
            champion_team=champion_team, runner_up_team=runner_up_team,
            third_place_team=third_place_team,
        ))
        msg = "Podium picks saved!"
    db.session.commit()
    return jsonify({"message": msg})


# ── Leaderboard ────────────────────────────────────────────────────────────────

@api_bp.route("/leaderboard", methods=["GET"])
@jwt_required()
def leaderboard():
    user = _get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_comps = list(user.competitions)
    if not user_comps:
        return jsonify({"error": "Not assigned to a group"}), 400
    selected_comp_id = request.args.get("group_id", type=int)
    if not selected_comp_id or not any(c.id == selected_comp_id for c in user_comps):
        selected_comp_id = user.competition_id or user_comps[0].id
    selected_comp = next(c for c in user_comps if c.id == selected_comp_id)
    members = [u for u in selected_comp.members if not u.is_admin]
    t1_pts = {u.id: _t1_points_for_competition(u, selected_comp_id) for u in members}
    t2_pts = {u.id: _t2_points_for_competition(u, selected_comp_id) for u in members}
    classic_sorted = sorted(members, key=lambda u: (-t1_pts[u.id], u.username.lower()))
    odds_sorted = sorted(members, key=lambda u: (-t2_pts[u.id], u.username.lower()))
    t1_ranks = _assign_ranks(classic_sorted, t1_pts)
    t2_ranks = _assign_ranks(odds_sorted, t2_pts)

    def _row(u):
        return {
            "id": u.id, "username": u.username,
            "first_name": u.first_name, "last_name": u.last_name,
            "t1_points": t1_pts[u.id], "t2_points": t2_pts[u.id],
            "t1_rank": t1_ranks.get(u.id), "t2_rank": t2_ranks.get(u.id),
            "is_me": u.id == user.id,
        }

    return jsonify({
        "group_name": selected_comp.name,
        "include_tournament1": selected_comp.include_tournament1,
        "include_tournament2": selected_comp.include_tournament2,
        "classic_leaderboard": [_row(u) for u in classic_sorted],
        "odds_leaderboard": [_row(u) for u in odds_sorted],
        "user_competitions": [{"id": c.id, "name": c.name} for c in user_comps],
        "selected_comp_id": selected_comp_id,
    })


# ── H2H ───────────────────────────────────────────────────────────────────────

@api_bp.route("/h2h", methods=["GET"])
@jwt_required()
def h2h():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    user_comps = list(user.competitions)
    if not user_comps:
        return jsonify({"error": "Not assigned to a group"}), 400
    selected_comp_id = request.args.get("group_id", type=int)
    if not selected_comp_id or not any(c.id == selected_comp_id for c in user_comps):
        selected_comp_id = user.competition_id or user_comps[0].id
    selected_comp = next(c for c in user_comps if c.id == selected_comp_id)
    members = sorted([u for u in selected_comp.members if not u.is_admin], key=lambda u: u.username.lower())
    member_ids = {u.id for u in members}
    user1_id = request.args.get("user1", type=int)
    user2_id = request.args.get("user2", type=int)
    user1 = db.session.get(User, user1_id) if user1_id and user1_id in member_ids else None
    user2 = db.session.get(User, user2_id) if user2_id and user2_id in member_ids else None
    comparison = None
    if user1 and user2 and user1.id != user2.id:
        all_matches_list = Match.query.order_by(Match.match_date).all()
        u1_classic = {p.match_id: p for p in Prediction.query.filter_by(user_id=user1.id, competition_id=selected_comp_id)}
        u2_classic = {p.match_id: p for p in Prediction.query.filter_by(user_id=user2.id, competition_id=selected_comp_id)}
        u1_odds = {p.match_id: p for p in OddsPrediction.query.filter_by(user_id=user1.id, competition_id=selected_comp_id)}
        u2_odds = {p.match_id: p for p in OddsPrediction.query.filter_by(user_id=user2.id, competition_id=selected_comp_id)}
        match_rows = []
        for m in all_matches_list:
            if not m.is_finished():
                continue
            u1c = u1_classic.get(m.id)
            u2c = u2_classic.get(m.id)
            u1o = u1_odds.get(m.id)
            u2o = u2_odds.get(m.id)
            match_rows.append({
                "match_id": m.id,
                "home_team": m.home_team, "away_team": m.away_team,
                "home_score": m.home_score, "away_score": m.away_score,
                "match_date": m.match_date.strftime("%Y-%m-%dT%H:%M:%SZ") if m.match_date else None,
                "u1_classic": {"home": u1c.predicted_home_score, "away": u1c.predicted_away_score, "points": u1c.points} if u1c else None,
                "u2_classic": {"home": u2c.predicted_home_score, "away": u2c.predicted_away_score, "points": u2c.points} if u2c else None,
                "u1_odds": {"outcome": u1o.predicted_outcome, "points": float(u1o.points)} if u1o else None,
                "u2_odds": {"outcome": u2o.predicted_outcome, "points": float(u2o.points)} if u2o else None,
            })
        comparison = {
            "matches": match_rows,
            "u1_t1": _t1_points_for_competition(user1, selected_comp_id),
            "u2_t1": _t1_points_for_competition(user2, selected_comp_id),
            "u1_t2": _t2_points_for_competition(user1, selected_comp_id),
            "u2_t2": _t2_points_for_competition(user2, selected_comp_id),
        }
    return jsonify({
        "members": [{"id": u.id, "username": u.username} for u in members],
        "user1": {"id": user1.id, "username": user1.username} if user1 else None,
        "user2": {"id": user2.id, "username": user2.username} if user2 else None,
        "comparison": comparison,
        "selected_comp_id": selected_comp_id,
        "user_competitions": [{"id": c.id, "name": c.name} for c in user_comps],
        "include_tournament1": selected_comp.include_tournament1,
        "include_tournament2": selected_comp.include_tournament2,
    })


# ── Progress ───────────────────────────────────────────────────────────────────

@api_bp.route("/progress", methods=["GET"])
@jwt_required()
def progress():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    user_comps = list(user.competitions)
    if not user_comps:
        return jsonify({"error": "Not assigned to a group"}), 400
    selected_comp_id = request.args.get("group_id", type=int)
    if not selected_comp_id or not any(c.id == selected_comp_id for c in user_comps):
        selected_comp_id = user.competition_id or user_comps[0].id
    selected_comp = next(c for c in user_comps if c.id == selected_comp_id)
    snapshots = [
        s for s in RankSnapshot.query.filter_by(
            user_id=user.id, competition_id=selected_comp_id
        ).order_by(RankSnapshot.snapshot_date).all()
        if s.t1_points > 0 or float(s.t2_points) > 0
    ]
    members = [u for u in selected_comp.members if not u.is_admin]
    t1_pts = {u.id: _t1_points_for_competition(u, selected_comp_id) for u in members}
    t2_pts = {u.id: _t2_points_for_competition(u, selected_comp_id) for u in members}
    classic_sorted = sorted(members, key=lambda u: (-t1_pts[u.id], u.username.lower()))
    odds_sorted = sorted(members, key=lambda u: (-t2_pts[u.id], u.username.lower()))
    t1_ranks_now = _assign_ranks(classic_sorted, t1_pts)
    t2_ranks_now = _assign_ranks(odds_sorted, t2_pts)

    def _outcome(h, a):
        return "home" if h > a else ("away" if h < a else "draw")

    classic_finished = [
        p for p in Prediction.query.filter_by(user_id=user.id, competition_id=selected_comp_id).all()
        if p.match and p.match.is_finished()
    ]
    t1_total = len(classic_finished)
    t1_correct = sum(
        1 for p in classic_finished
        if _outcome(p.predicted_home_score, p.predicted_away_score) == _outcome(p.match.home_score, p.match.away_score)
    )
    t1_score_correct = sum(
        1 for p in classic_finished
        if p.predicted_home_score == p.match.home_score and p.predicted_away_score == p.match.away_score
    )

    odds_finished = [
        p for p in OddsPrediction.query.filter_by(user_id=user.id, competition_id=selected_comp_id).all()
        if p.match and p.match.is_finished()
    ]
    t2_total = len(odds_finished)
    t2_correct = sum(
        1 for p in odds_finished
        if _outcome(p.match.home_score, p.match.away_score) == p.predicted_outcome
    )

    other_members = [u for u in members if u.id != user.id]
    compare_user_id = request.args.get("compare_user", type=int)
    compare_snap_map = {}
    compare_user_info = None
    if compare_user_id and compare_user_id != user.id:
        compare_obj = next((u for u in other_members if u.id == compare_user_id), None)
        if compare_obj:
            compare_user_info = {"id": compare_obj.id, "username": compare_obj.username}
            compare_snap_map = {
                s.snapshot_date: s
                for s in RankSnapshot.query.filter_by(
                    user_id=compare_user_id, competition_id=selected_comp_id
                ).order_by(RankSnapshot.snapshot_date).all()
                if s.t1_points > 0 or float(s.t2_points) > 0
            }

    my_snap_map = {s.snapshot_date: s for s in snapshots}
    all_dates = sorted(set(my_snap_map.keys()) | set(compare_snap_map.keys()))

    return jsonify({
        "chart_data": {
            "labels": [d.strftime("%b %d") for d in all_dates],
            "t1_rank": [my_snap_map[d].t1_rank if d in my_snap_map else None for d in all_dates],
            "t2_rank": [my_snap_map[d].t2_rank if d in my_snap_map else None for d in all_dates],
            "t1_points": [my_snap_map[d].t1_points if d in my_snap_map else None for d in all_dates],
            "t2_points": [round(float(my_snap_map[d].t2_points), 2) if d in my_snap_map else None for d in all_dates],
            "cmp_t1_rank": [compare_snap_map[d].t1_rank if d in compare_snap_map else None for d in all_dates] if compare_user_info else None,
            "cmp_t2_rank": [compare_snap_map[d].t2_rank if d in compare_snap_map else None for d in all_dates] if compare_user_info else None,
        },
        "has_data": len(all_dates) > 0,
        "total_members": len(members),
        "current_t1": t1_pts.get(user.id, 0),
        "current_t2": t2_pts.get(user.id, 0.0),
        "current_t1_rank": t1_ranks_now.get(user.id, 0),
        "current_t2_rank": t2_ranks_now.get(user.id, 0),
        "t1_accuracy": round(t1_correct / t1_total * 100) if t1_total else None,
        "t1_score_accuracy": round(t1_score_correct / t1_total * 100) if t1_total else None,
        "t2_accuracy": round(t2_correct / t2_total * 100) if t2_total else None,
        "t1_correct": t1_correct, "t1_score_correct": t1_score_correct, "t1_total": t1_total,
        "t2_correct": t2_correct, "t2_total": t2_total,
        "other_members": [{"id": u.id, "username": u.username} for u in other_members],
        "compare_user": compare_user_info,
        "include_tournament1": selected_comp.include_tournament1,
        "include_tournament2": selected_comp.include_tournament2,
        "selected_comp_id": selected_comp_id,
        "user_competitions": [{"id": c.id, "name": c.name} for c in user_comps],
    })


# ── Rules ──────────────────────────────────────────────────────────────────────

@api_bp.route("/rules", methods=["GET"])
@jwt_required()
def rules():
    user = _get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    prize_info = []
    if not user.is_admin:
        for comp in user.competitions:
            if comp.entry_fee and comp.entry_fee > 0:
                member_count = sum(1 for u in comp.members if not u.is_admin)
                total = comp.entry_fee * member_count
                prize_info.append({
                    "name": comp.name, "entry_fee": comp.entry_fee,
                    "member_count": member_count, "total_pool": total,
                    "comp1_winner": total * 0.50, "comp1_second": total * 0.20,
                    "comp2_winner": total * 0.30,
                    "include_tournament1": comp.include_tournament1,
                    "include_tournament2": comp.include_tournament2,
                })
    return jsonify({"competitions_prize_info": prize_info})


# ── All Predictions ────────────────────────────────────────────────────────────

@api_bp.route("/predictions", methods=["GET"])
@jwt_required()
def predictions():
    user = _get_current_user()
    if not user or user.is_admin:
        return jsonify({"error": "Not allowed"}), 403
    user_comps = list(user.competitions)
    if not user_comps:
        return jsonify({"error": "Not assigned to a group"}), 400
    selected_comp_id = request.args.get("group_id", type=int)
    if not selected_comp_id or not any(c.id == selected_comp_id for c in user_comps):
        selected_comp_id = user.competition_id or user_comps[0].id
    selected_comp = next(c for c in user_comps if c.id == selected_comp_id)
    tab = request.args.get("tab", "classic")
    if tab not in {"classic", "odds", "qualifiers", "podium"}:
        tab = "classic"
    users = sorted([u for u in selected_comp.members if not u.is_admin], key=lambda u: u.username.lower())
    all_matches = Match.query.filter(
        Match.stage.in_(["group", "round_of_32", "round_of_16"])
    ).order_by(Match.match_date).all()
    result = {
        "selected_comp_id": selected_comp_id, "tab": tab,
        "users": [{"id": u.id, "username": u.username} for u in users],
        "matches": [{"id": m.id, "home_team": m.home_team, "away_team": m.away_team, "is_finished": m.is_finished()} for m in all_matches],
        "user_competitions": [{"id": c.id, "name": c.name} for c in user_comps],
    }
    if tab == "classic":
        preds = Prediction.query.filter_by(competition_id=selected_comp_id).all()
        result["predictions"] = [{"user_id": p.user_id, "match_id": p.match_id, "home": p.predicted_home_score, "away": p.predicted_away_score, "points": p.points} for p in preds]
    elif tab == "odds":
        preds = OddsPrediction.query.filter_by(competition_id=selected_comp_id).all()
        result["predictions"] = [{"user_id": p.user_id, "match_id": p.match_id, "outcome": p.predicted_outcome, "points": float(p.points)} for p in preds]
    elif tab == "qualifiers":
        preds = GroupQualifierPrediction.query.filter_by(competition_id=selected_comp_id).all()
        result["predictions"] = [{"user_id": p.user_id, "group_name": p.group_name, "team_1": p.team_1, "team_2": p.team_2, "points": p.points} for p in preds]
    elif tab == "podium":
        preds = PodiumPrediction.query.filter_by(competition_id=selected_comp_id).all()
        result["predictions"] = [{"user_id": p.user_id, "champion": p.champion_team, "runner_up": p.runner_up_team, "third": p.third_place_team, "points": p.points} for p in preds]
    return jsonify(result)
