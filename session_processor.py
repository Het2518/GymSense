# === FILE: session_processor.py ===
# GymSense AI — Full session processing pipeline

import os
import json
import numpy as np
import pandas as pd
import joblib
from collections import Counter

import rep_counter
import quality_scorer

WINDOW_SIZE = 80
STRIDE = 40
SECONDS_PER_WINDOW = 2.0  # window_idx * 2 seconds

MUSCLE_GROUPS = {
    'Squat': ['quads', 'glutes', 'hamstrings'],
    'BenchPress': ['chest', 'triceps', 'shoulders'],
    'LegPress': ['quads', 'glutes'],
    'Adductor': ['adductors', 'inner thighs'],
    'LegCurl': ['hamstrings'],
    'ArmCurl': ['biceps'],
    'RopeSkipping': ['calves', 'cardio'],
    'Running': ['cardio', 'calves', 'quads'],
    'Walking': ['cardio', 'calves'],
    'StairClimber': ['quads', 'glutes', 'cardio'],
    'Riding': ['cardio', 'quads'],
}

SENSOR_COLS = ['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z', 'C_1']


def validate_csv(df):
    """Check that required columns exist."""
    required = ['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z', 'C_1']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True


def majority_vote_smooth(labels, window=5):
    """Apply sliding majority vote smoothing."""
    smoothed = labels.copy()
    half = window // 2
    for i in range(half, len(labels) - half):
        chunk = labels[i - half:i + half + 1]
        counts = Counter(chunk)
        smoothed[i] = counts.most_common(1)[0][0]
    return smoothed


def run_length_encode(labels):
    """Run-length encoding of a label sequence."""
    if len(labels) == 0:
        return [], [], []

    runs = []
    starts = []
    lengths = []

    current = labels[0]
    start = 0
    count = 1

    for i in range(1, len(labels)):
        if labels[i] == current:
            count += 1
        else:
            runs.append(current)
            starts.append(start)
            lengths.append(count)
            current = labels[i]
            start = i
            count = 1

    runs.append(current)
    starts.append(start)
    lengths.append(count)

    return runs, starts, lengths


def format_time(seconds):
    """Convert seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def process_session(csv_path, model, scaler, le):
    """
    Full session processing pipeline.

    Args:
        csv_path: path to a CSV file with sensor data
        model: trained Keras model
        scaler: fitted StandardScaler
        le: fitted LabelEncoder

    Returns:
        dict: complete session JSON with timeline, exercises, quality metrics
    """
    # 1. Load and validate
    df = pd.read_csv(csv_path)
    validate_csv(df)

    # 2. Filter to wrist position (if column exists)
    if 'Position' in df.columns:
        df_wrist = df[df['Position'] == 'wrist'].copy()
        if len(df_wrist) == 0:
            df_wrist = df.copy()  # fallback: use all data
    else:
        df_wrist = df.copy()

    df_wrist = df_wrist.dropna(subset=SENSOR_COLS).reset_index(drop=True)
    raw_df = df_wrist.copy()  # keep raw for rep counting

    # 3. Normalise using saved scaler (do NOT refit)
    sensor_data = scaler.transform(df_wrist[SENSOR_COLS].values)
    n_channels = len(SENSOR_COLS)

    # 4. Window the entire session
    n_samples = len(sensor_data)
    windows = []
    window_starts = []

    for start in range(0, n_samples - WINDOW_SIZE + 1, STRIDE):
        end = start + WINDOW_SIZE
        window = sensor_data[start:end]
        windows.append(window)
        window_starts.append(start)

    if len(windows) == 0:
        return _empty_session()

    X = np.array(windows).reshape(-1, 1, WINDOW_SIZE, n_channels)

    # 5. Inference: manual batching to prevent TF OOM on Render Free Tier (512MB RAM)
    y_probs_list = []
    batch_size = 16
    for i in range(0, len(X), batch_size):
        batch_X = X[i:i+batch_size]
        batch_probs = model(batch_X, training=False)
        y_probs_list.append(batch_probs.numpy())
    y_probs = np.vstack(y_probs_list)
    y_pred = np.argmax(y_probs, axis=1)

    # Decode labels
    pred_labels = le.inverse_transform(y_pred)

    # 6. Majority-vote smoothing (5-window)
    smoothed_labels = majority_vote_smooth(pred_labels, window=5)

    # 7. Segment detection
    runs, starts, lengths = run_length_encode(smoothed_labels)

    # Discard segments < 10 consecutive windows (< 20 seconds)
    MIN_WINDOWS = 10
    filtered_segments = []
    for label, start_win, length in zip(runs, starts, lengths):
        if length >= MIN_WINDOWS:
            filtered_segments.append({
                'label': label,
                'start_win': start_win,
                'length': length,
                'start_time_s': start_win * SECONDS_PER_WINDOW,
                'end_time_s': (start_win + length) * SECONDS_PER_WINDOW,
            })

    # Merge same-class segments separated by Null < 15 seconds
    merged_segments = []
    for seg in filtered_segments:
        if (merged_segments and
            seg['label'] != 'Null' and
            merged_segments[-1]['label'] == seg['label']):

            gap = seg['start_time_s'] - merged_segments[-1]['end_time_s']
            if gap < 15:
                merged_segments[-1]['end_time_s'] = seg['end_time_s']
                merged_segments[-1]['length'] += seg['length']
                continue

        merged_segments.append(dict(seg))

    # Convert to sample indices for rep counting
    for seg in merged_segments:
        seg['start_idx'] = int(seg['start_win'] * STRIDE)
        seg['end_idx'] = min(int((seg['start_win'] + seg['length']) * STRIDE + WINDOW_SIZE), n_samples)
        seg['exercise'] = seg['label']

    # 8. Rep counting for each non-Null segment
    for seg in merged_segments:
        if seg['exercise'] == 'Null':
            seg['rep_data'] = {'reps': 0, 'rep_timestamps': [], 'method': 'skip'}
        else:
            seg['rep_data'] = rep_counter.count_reps(raw_df, seg)

    # 9. Quality scoring for each segment
    for i, seg in enumerate(merged_segments):
        if seg['exercise'] == 'Null':
            seg['quality'] = {
                'tempo_score': 0, 'fatigue_detected': False,
                'fatigue_onset_rep': None, 'completion_pct': 0,
                'rest_ok': True, 'rest_duration_s': 0.0, 'rest_flag': 'n/a',
            }
            continue

        # Find rest duration before this segment
        rest_duration = None
        if i > 0:
            prev_end = merged_segments[i - 1]['end_time_s']
            rest_duration = seg['start_time_s'] - prev_end

        seg['quality'] = quality_scorer.score_segment(
            seg['exercise'],
            seg['rep_data']['rep_timestamps'],
            seg['rep_data']['reps'],
            rest_duration,
        )

    # 10. Assemble session JSON
    total_duration_s = merged_segments[-1]['end_time_s'] if merged_segments else 0.0
    total_duration_min = total_duration_s / 60.0

    # Group exercises
    exercise_groups = {}
    for seg in merged_segments:
        name = seg['exercise']
        if name == 'Null':
            continue
        if name not in exercise_groups:
            exercise_groups[name] = []
        exercise_groups[name].append(seg)

    # Calculate null time
    null_time = sum(seg['end_time_s'] - seg['start_time_s']
                    for seg in merged_segments if seg['exercise'] == 'Null')
    null_pct = (null_time / total_duration_s * 100) if total_duration_s > 0 else 0.0

    # Collect all muscle groups
    all_muscles = set()
    for name in exercise_groups:
        all_muscles.update(MUSCLE_GROUPS.get(name, []))

    # Build exercises list
    exercises_list = []
    total_reps = 0
    total_sets = 0
    tempo_scores = []

    for name, segments in exercise_groups.items():
        n_sets = len(segments)
        reps_per_set = [seg['rep_data']['reps'] for seg in segments]
        ex_total_reps = sum(reps_per_set)
        start_time = segments[0]['start_time_s']
        end_time = segments[-1]['end_time_s']
        duration = end_time - start_time

        # Average tempo score across sets
        set_tempos = [seg['quality']['tempo_score'] for seg in segments]
        avg_tempo = int(np.mean(set_tempos)) if set_tempos else 0

        # Fatigue: use data from the last set
        last_seg = segments[-1]

        # Rest times between sets
        rest_times = []
        rest_flags = []
        for j in range(1, len(segments)):
            gap = segments[j]['start_time_s'] - segments[j - 1]['end_time_s']
            rest_times.append(float(round(gap, 1)))
            _, flag = quality_scorer.evaluate_rest(name, gap)
            rest_flags.append(flag)

        exercises_list.append({
            'name': name,
            'start_time': format_time(start_time),
            'end_time': format_time(end_time),
            'duration_s': float(round(duration, 1)),
            'sets': n_sets,
            'reps_per_set': [int(r) for r in reps_per_set],
            'total_reps': int(ex_total_reps),
            'tempo_score': avg_tempo,
            'fatigue_detected': bool(last_seg['quality']['fatigue_detected']),
            'fatigue_onset_rep': last_seg['quality']['fatigue_onset_rep'],
            'completion_pct': int(last_seg['quality']['completion_pct']),
            'rest_times_sec': rest_times,
            'rest_flags': rest_flags,
        })

        total_reps += ex_total_reps
        total_sets += n_sets
        tempo_scores.append(avg_tempo)

    avg_tempo_score = float(np.mean(tempo_scores)) if tempo_scores else 0.0

    # Build timeline
    timeline = []
    for seg in merged_segments:
        t_type = 'rest' if seg['exercise'] == 'Null' else 'exercise'
        timeline.append({
            'exercise': seg['exercise'],
            'start': format_time(seg['start_time_s']),
            'end': format_time(seg['end_time_s']),
            'type': t_type,
            'duration_s': float(round(seg['end_time_s'] - seg['start_time_s'], 1)),
        })

    session_json = {
        'session_date': 'Unknown',
        'total_duration_min': float(round(total_duration_min, 1)),
        'total_exercises': len(exercise_groups),
        'total_reps': int(total_reps),
        'total_sets': int(total_sets),
        'avg_tempo_score': float(round(avg_tempo_score, 1)),
        'null_time_percent': float(round(null_pct, 1)),
        'muscle_groups_trained': sorted(list(all_muscles)),
        'exercises': exercises_list,
        'timeline': timeline,
    }

    return session_json


def _empty_session():
    """Return an empty session JSON for edge cases."""
    return {
        'session_date': 'Unknown',
        'total_duration_min': 0.0,
        'total_exercises': 0,
        'total_reps': 0,
        'total_sets': 0,
        'avg_tempo_score': 0.0,
        'null_time_percent': 0.0,
        'muscle_groups_trained': [],
        'exercises': [],
        'timeline': [],
    }
