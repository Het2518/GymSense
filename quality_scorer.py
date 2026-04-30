# === FILE: quality_scorer.py ===
# GymSense AI — Workout quality scoring module

import numpy as np
from scipy.stats import linregress

EXPECTED_REPS = 10  # RecGym protocol: 3x10

REST_THRESHOLDS = {
    'strength': {'min': 60, 'max': 180},
    'aerobic':  {'min': 30, 'max': 120},
}

STRENGTH_EXERCISES = {'Squat', 'BenchPress', 'LegPress', 'Adductor', 'LegCurl', 'ArmCurl'}

AEROBIC_EXERCISES = {'Running', 'Walking', 'RopeSkipping', 'Riding', 'StairClimber'}


def compute_tempo_score(rep_timestamps):
    """
    Tempo Consistency Score (0–100).
    Based on coefficient of variation of inter-rep intervals.
    """
    if len(rep_timestamps) < 2:
        return 100  # Not enough data to judge inconsistency

    iri = np.diff(rep_timestamps)
    if len(iri) == 0:
        return 100

    mean_iri = np.mean(iri)
    cv = np.std(iri) / (mean_iri + 1e-8)
    score = max(0, min(100, int(100 * (1 - cv))))
    return score


def detect_fatigue(rep_timestamps):
    """
    Fatigue detection via linear regression on inter-rep intervals.
    Returns (fatigue_detected: bool, fatigue_onset_rep: int|None)
    """
    if len(rep_timestamps) < 4:
        return False, None

    iri = np.diff(rep_timestamps)
    if len(iri) < 3:
        return False, None

    slope, _, _, _, _ = linregress(range(len(iri)), iri)
    fatigue_detected = slope > 0.05  # > 0.05 s/rep increase

    fatigue_onset_rep = None
    if fatigue_detected:
        threshold = np.mean(iri) + np.std(iri)
        onset_indices = np.where(iri > threshold)[0]
        if len(onset_indices) > 0:
            fatigue_onset_rep = int(onset_indices[0]) + 1

    return fatigue_detected, fatigue_onset_rep


def compute_completion(detected_reps, expected=EXPECTED_REPS):
    """Set completion percentage."""
    return min(100, round(detected_reps / expected * 100))


def evaluate_rest(exercise_name, rest_duration_s):
    """
    Evaluate rest duration for the exercise type.
    Returns (rest_ok: bool, rest_flag: str)
    """
    if rest_duration_s is None or rest_duration_s < 0:
        return True, 'n/a'

    if exercise_name in STRENGTH_EXERCISES:
        thresholds = REST_THRESHOLDS['strength']
    elif exercise_name in AEROBIC_EXERCISES:
        thresholds = REST_THRESHOLDS['aerobic']
    else:
        return True, 'n/a'

    if rest_duration_s < thresholds['min']:
        return False, 'too_short'
    elif rest_duration_s > thresholds['max']:
        return False, 'too_long'
    else:
        return True, 'ok'


def score_segment(exercise_name, rep_timestamps, detected_reps, rest_duration_s=None):
    """
    Compute all quality metrics for one exercise segment.

    Args:
        exercise_name: str
        rep_timestamps: list of float (seconds)
        detected_reps: int
        rest_duration_s: float or None (rest before this segment)

    Returns:
        dict with all quality metrics
    """
    tempo_score = compute_tempo_score(rep_timestamps)
    fatigue_detected, fatigue_onset_rep = detect_fatigue(rep_timestamps)
    completion_pct = compute_completion(detected_reps)
    rest_ok, rest_flag = evaluate_rest(exercise_name, rest_duration_s)

    return {
        'tempo_score': tempo_score,
        'fatigue_detected': bool(fatigue_detected),
        'fatigue_onset_rep': fatigue_onset_rep,
        'completion_pct': completion_pct,
        'rest_ok': bool(rest_ok),
        'rest_duration_s': float(rest_duration_s) if rest_duration_s is not None else 0.0,
        'rest_flag': rest_flag,
    }
