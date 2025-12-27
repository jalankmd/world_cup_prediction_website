# scoring.py
"""
Module for calculating and updating points for match predictions.
Points system:
- 3 points for exact score (home and away correct)
- 2 points for correct outcome (win/draw/loss)
- 0 points otherwise
"""

from .models import Match, Prediction
from . import db

def calculate_points(prediction):
    """
    Calculate points for a single prediction.

    Args:
        prediction (Prediction): A Prediction object containing user's predicted scores.

    Returns:
        int: Points earned for the prediction (3, 2, or 0)
    """
    match = prediction.match

    # Ensure the match has been played
    if match.home_score is None or match.away_score is None:
        return 0  # Cannot score points if match result is unknown

    # 1. Exact score prediction
    if (prediction.predicted_home_score == match.home_score and
        prediction.predicted_away_score == match.away_score):
        return 3

    # 2. Correct outcome prediction (winner/draw)
    predicted_diff = prediction.predicted_home_score - prediction.predicted_away_score
    actual_diff = match.home_score - match.away_score

    # Outcome matches if both predicted and actual differences have the same sign
    # Positive diff: home wins, Negative diff: away wins, Zero: draw
    if (predicted_diff > 0 and actual_diff > 0) or \
       (predicted_diff < 0 and actual_diff < 0) or \
       (predicted_diff == 0 and actual_diff == 0):
        return 2

    # 3. Wrong prediction
    return 0


def update_all_points():
    """
    Recalculate and update points for all predictions in the database.

    Iterates through all Prediction records, calculates points using `calculate_points`,
    and commits the changes to the database.
    """
    predictions = Prediction.query.all()
    for p in predictions:
        p.points = calculate_points(p)  # Update points for each prediction
    db.session.commit()
    print(f"Updated points for {len(predictions)} predictions.")
