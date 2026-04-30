# === FILE: rep_counter.py ===
# GymSense AI — Rep counting via HBC + IMU signal fusion

import numpy as np
from scipy.signal import find_peaks
from scipy.fft import fft, ifft

SAMPLING_RATE = 20  # Hz

EXERCISE_CUTOFFS = {
    'Walking': 2.5, 'RopeSkipping': 2.5, 'Riding': 2.5,
    'Running': 2.0, 'StairClimber': 2.0,
    'Squat': 0.8, 'BenchPress': 0.8, 'LegPress': 0.8,
    'Adductor': 0.6, 'LegCurl': 0.6, 'ArmCurl': 0.6,
}

PER_EXERCISE_PARAMS = {
    'Squat':        {'distance': 15, 'prominence': 0.3},
    'BenchPress':   {'distance': 15, 'prominence': 0.3},
    'LegPress':     {'distance': 15, 'prominence': 0.25},
    'Adductor':     {'distance': 20, 'prominence': 0.25},
    'LegCurl':      {'distance': 15, 'prominence': 0.25},
    'ArmCurl':      {'distance': 12, 'prominence': 0.3},
    'RopeSkipping': {'distance': 5,  'prominence': 0.2},
    'Running':      {'distance': 8,  'prominence': 0.2},
    'Walking':      {'distance': 10, 'prominence': 0.2},
    'StairClimber': {'distance': 12, 'prominence': 0.25},
    'Riding':       {'distance': 10, 'prominence': 0.2},
}


def lowpass_fft(signal, cutoff_freq, sampling_rate=SAMPLING_RATE):
    """Apply FFT-based low-pass filter: zero out frequencies above cutoff, then IFFT."""
    n = len(signal)
    if n < 4:
        return signal.copy()

    freq_spectrum = fft(signal)
    freqs = np.fft.fftfreq(n, d=1.0 / sampling_rate)

    # Zero out frequencies above cutoff
    freq_spectrum[np.abs(freqs) > cutoff_freq] = 0

    # Inverse FFT and take real part
    filtered = np.real(ifft(freq_spectrum))
    return filtered


def normalize_signal(signal):
    """Min-max normalize a signal to [0, 1]."""
    mn, mx = np.min(signal), np.max(signal)
    if mx - mn < 1e-10:
        return np.zeros_like(signal)
    return (signal - mn) / (mx - mn)


def count_peaks(signal, exercise_name):
    """Count peaks using scipy.signal.find_peaks with per-exercise parameters."""
    params = PER_EXERCISE_PARAMS.get(exercise_name, {'distance': 12, 'prominence': 0.25})
    peaks, properties = find_peaks(signal, **params)
    return len(peaks), peaks


def count_reps(raw_df, segment):
    """
    Count repetitions for an exercise segment using HBC + IMU fusion.

    Args:
        raw_df: DataFrame with raw sensor data (must have A_x, A_y, A_z, C_1 columns)
        segment: dict with keys: 'exercise', 'start_idx', 'end_idx' (sample indices into raw_df)

    Returns:
        dict with keys: 'reps', 'rep_timestamps', 'method'
    """
    exercise = segment['exercise']
    start_idx = segment['start_idx']
    end_idx = segment['end_idx']

    if exercise == 'Null' or exercise not in EXERCISE_CUTOFFS:
        return {'reps': 0, 'rep_timestamps': [], 'method': 'skip'}

    cutoff = EXERCISE_CUTOFFS[exercise]

    # Extract segment data
    seg_data = raw_df.iloc[start_idx:end_idx]
    if len(seg_data) < 10:
        return {'reps': 0, 'rep_timestamps': [], 'method': 'too_short'}

    # --- HBC channel ---
    hbc_signal = seg_data['C_1'].values.astype(float)
    hbc_filtered = lowpass_fft(hbc_signal, cutoff)
    hbc_norm = normalize_signal(hbc_filtered)
    hbc_count, hbc_peaks = count_peaks(hbc_norm, exercise)

    # --- IMU magnitude ---
    ax = seg_data['A_x'].values.astype(float)
    ay = seg_data['A_y'].values.astype(float)
    az = seg_data['A_z'].values.astype(float)
    imu_mag = np.sqrt(ax**2 + ay**2 + az**2)
    imu_filtered = lowpass_fft(imu_mag, cutoff)
    imu_norm = normalize_signal(imu_filtered)
    imu_count, imu_peaks = count_peaks(imu_norm, exercise)

    # --- Fusion: average of the two closest values ---
    # Since we only have 2 values, the "two closest" is just both of them
    final_count = int(round((hbc_count + imu_count) / 2.0))

    # Generate timestamps from HBC peaks (primary) in seconds
    if len(hbc_peaks) > 0:
        rep_timestamps = [float(p / SAMPLING_RATE) for p in hbc_peaks]
    elif len(imu_peaks) > 0:
        rep_timestamps = [float(p / SAMPLING_RATE) for p in imu_peaks]
    else:
        rep_timestamps = []

    # Trim timestamps to match final count
    rep_timestamps = rep_timestamps[:final_count] if len(rep_timestamps) > final_count else rep_timestamps

    return {
        'reps': max(0, final_count),
        'rep_timestamps': rep_timestamps,
        'method': 'HBC+IMU',
    }
