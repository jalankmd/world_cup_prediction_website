# scoring.py
"""
Module for calculating and updating points for match predictions.
Tournament 1 (classic):
- Base points: 3 for exact score, 2 for correct outcome
- Bonus by stage: +1 for knockout, +2 for semifinal/final, +1 for third-place
- Group qualifier picks: 1 point per correct team
- Podium picks: champion=10, runner-up=6, third-place=3

Tournament 2 (odds):
- Pick winner/draw only
- Correct pick awards the corresponding odds value for that result
"""

from .models import (
    Prediction,
    OddsPrediction,
    GroupQualifierPrediction,
    GroupResult,
    PodiumPrediction,
    TournamentOutcome,
)
from . import db

def _stage_bonus(stage):
    """Return bonus points for the configured match stage."""
    stage = (stage or "group").lower()
    if stage in {"final", "semi_final", "semifinal", "semi-final"}:
        return 2
    if stage in {"third_place", "third-place", "third_place_playoff"}:
        return 1
    if stage in {"round_of_32", "round_of_16", "last_16", "quarter_final", "quarterfinal", "knockout"}:
        return 1
    return 0


def _match_outcome(home_score, away_score):
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"


def calculate_points(prediction):
    """
    Calculate points for a single prediction.

    Args:
        prediction (Prediction): A Prediction object containing user's predicted scores.

    Returns:
        int: Points earned for the prediction with stage bonus.
    """
    match = prediction.match

    # Ensure the match has been played
    if match.home_score is None or match.away_score is None:
        return 0  # Cannot score points if match result is unknown

    bonus = _stage_bonus(match.stage)

    # 1. Exact score prediction
    if (prediction.predicted_home_score == match.home_score and
        prediction.predicted_away_score == match.away_score):
        return 3 + bonus

    # 2. Correct outcome prediction (winner/draw)
    predicted_diff = prediction.predicted_home_score - prediction.predicted_away_score
    actual_diff = match.home_score - match.away_score

    # Outcome matches if both predicted and actual differences have the same sign
    # Positive diff: home wins, Negative diff: away wins, Zero: draw
    if (predicted_diff > 0 and actual_diff > 0) or \
       (predicted_diff < 0 and actual_diff < 0) or \
       (predicted_diff == 0 and actual_diff == 0):
        return 2 + bonus

    # 3. Wrong prediction
    return 0


def calculate_odds_points(prediction):
    """Calculate Tournament 2 points based on matching outcome and odds."""
    match = prediction.match
    if match.home_score is None or match.away_score is None:
        return 0.0

    actual = _match_outcome(match.home_score, match.away_score)
    predicted = (prediction.predicted_outcome or "").lower()
    if predicted != actual:
        return 0.0

    if actual == "home":
        return float(match.home_odds or 0.0)
    if actual == "draw":
        return float(match.draw_odds or 0.0)
    return float(match.away_odds or 0.0)


def update_group_qualifier_points():
    """Score each group pick with 1 point per correctly selected qualified team."""
    group_results = {r.group_name: r for r in GroupResult.query.all()}
    predictions = GroupQualifierPrediction.query.all()

    for pred in predictions:
        result = group_results.get(pred.group_name)
        if not result or not result.qualified_team_1 or not result.qualified_team_2:
            pred.points = 0
            continue
        actual_set = {result.qualified_team_1, result.qualified_team_2}
        pred_set = {pred.team_1, pred.team_2}
        pred.points = len(actual_set.intersection(pred_set))


def update_podium_points():
    """Score champion picks: all 3 picks are guesses for the World Cup winner.
    1st pick = 10 pts, 2nd pick = 6 pts, 3rd pick = 3 pts if it matches the champion."""
    outcome = TournamentOutcome.query.first()
    predictions = PodiumPrediction.query.all()

    for pred in predictions:
        points = 0
        if outcome and outcome.champion_team:
            champ = outcome.champion_team
            if pred.champion_team == champ:
                points += 10
            elif pred.runner_up_team == champ:
                points += 6
            elif pred.third_place_team == champ:
                points += 3
        pred.points = points


def update_all_points():
    """
    Recalculate and update points for all predictions in the database.

    Iterates through all Prediction records, calculates points using `calculate_points`,
    and commits the changes to the database.
    """
    predictions = Prediction.query.all()
    for p in predictions:
        p.points = calculate_points(p)

    odds_predictions = OddsPrediction.query.all()
    for p in odds_predictions:
        p.points = calculate_odds_points(p)

    update_group_qualifier_points()
    update_podium_points()

    db.session.commit()
    print(
        f"Updated points for {len(predictions)} classic predictions and "
        f"{len(odds_predictions)} odds predictions."
    )
