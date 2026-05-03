import pandas as pd
import numpy as np
import math
from session_processor import process_session
import tensorflow as tf
import joblib

model = tf.keras.models.load_model('models/best_model.keras', compile=False, safe_mode=False)
scaler = joblib.load('models/scaler.pkl')
le = joblib.load('models/label_encoder.pkl')

SR = 20
samples = 200 # 10 seconds

def randn():
    return np.random.randn()

# Simulate Squat
amp = [0.2,1.8,0.8,0.55,0.1,0.2,0.28]
freq = 0.45
phase = [0, 1.57, 0, 3.14, 0, 0.79, 0.3]
noise = 0.06

data = []
for i in range(samples):
    t = i / SR
    row = {}
    for ci, ch in enumerate(['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z', 'C_1']):
        v = amp[ci] * math.sin(2 * math.pi * freq * t + phase[ci])
        v += amp[ci] * 0.2 * math.sin(2 * math.pi * freq * 2 * t + phase[ci] * 1.2)
        v += randn() * noise * (amp[ci] + 0.01)
        row[ch] = v * 0.04 + 0.5 # New scaling
    row['Position'] = 'wrist'
    row['Subject'] = 1
    row['Session'] = 1
    row['Workout'] = 'Squat'
    data.append(row)

df = pd.DataFrame(data)
df.to_csv('test_sim.csv', index=False)

res = process_session('test_sim.csv', model, scaler, le)
print("Exercises:", res['total_exercises'])
print("Total Reps:", res['total_reps'])
print("Avg Tempo:", res['avg_tempo_score'])
