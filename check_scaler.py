import joblib
import numpy as np

try:
    scaler = joblib.load('models/scaler.pkl')
    print("Scaler means:", scaler.mean_)
    print("Scaler scale (std):", scaler.scale_)
except Exception as e:
    print("Error:", e)
