# GymSense AI 🏋️

**GymSense AI** is an end-to-end intelligent gym session analysis system powered by a Hybrid CNN-Dilated Self-Attention deep learning model. It processes wearable sensor data (accelerometer, gyroscope, and body capacitance) from gym sessions to produce activity timelines, rep counts, workout quality metrics, personalised AI coaching, and downloadable PDF reports.

Built on the **RecGym dataset** (10 subjects, 12 exercise classes, ~50 hours of annotated data) and designed to run on **Lightning AI** with an NVIDIA RTX 6000 GPU.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY (free from https://aistudio.google.com/apikey)
export GEMINI_API_KEY=AIzaSyBFHU2XNaofboeDfuwtGvd-dRpHegd-2OE
```

### 3. Place Dataset

Place `RecGym.csv` in the project root directory.

### 4. Train the Model

```bash
python train.py --data-path RecGym.csv --test-user 10 --sensor combine --epochs 150
```

This will:
- Train the Hybrid CNN-Dilated Self-Attention model using LOUO cross-validation
- Save the trained model to `models/best_model.keras`
- Save the scaler and label encoder to `models/`
- Generate confusion matrix and learning curves in `results/`
- Print accuracy, macro F1, and Cohen's kappa metrics

**Expected results (from paper):** ~94.4% accuracy at wrist position, combined sensor mode.

### 5. Run the Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 6. Run the Frontend (Development)

```bash
cd frontend
npm install
npm run dev
```

### 7. Build & Deploy (Production)

```bash
cd frontend
npm run build
```

The built frontend is served automatically by the FastAPI backend from `frontend/dist/`. Just run the backend and access it at `http://localhost:8000`.

---

## 📖 How to Use

1. Open the web interface at `http://localhost:3000` (dev) or `http://localhost:8000` (production)
2. Upload any wrist-position sensor session CSV file
3. Select a coaching focus (General, Form, Progressive Overload, or Recovery)
4. Click **Analyse Session**
5. View your results: activity timeline, exercise breakdown, quality metrics, and AI coaching
6. Download the PDF report

---

## 🏗️ Architecture

| Component | Technology |
|---|---|
| **DL Model** | Hybrid CNN-Dilated Self-Attention (TensorFlow/Keras) |
| **Rep Counting** | FFT/IFFT smoothing + scipy peak detection (HBC + IMU fusion) |
| **Quality Scoring** | Tempo consistency, fatigue detection, rest evaluation |
| **AI Coaching** | Google Gemini 2.0 Flash (free tier) |
| **PDF Reports** | WeasyPrint + Jinja2 HTML templates |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | React 18 + Vite + Tailwind CSS 3 + Plotly.js |

---

## 📁 Project Structure

```
gymsense-ai/
├── train.py                 # Training script (CLI)
├── session_processor.py     # Full inference pipeline
├── rep_counter.py           # Rep counting (HBC + IMU)
├── quality_scorer.py        # Workout quality metrics
├── report_builder.py        # PDF report generation
├── llm_coach.py             # Gemini AI coaching
├── backend/
│   └── main.py              # FastAPI backend
├── frontend/                # React + Vite + Tailwind
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadForm.jsx
│   │   │   ├── ResultsDashboard.jsx
│   │   │   ├── SummaryCards.jsx
│   │   │   ├── TimelineChart.jsx
│   │   │   ├── ExerciseCard.jsx
│   │   │   ├── CoachingPanel.jsx
│   │   │   └── DownloadButton.jsx
│   │   └── api.js
│   └── ...
├── templates/
│   └── report.html          # PDF template
├── models/                  # Saved models (after training)
├── results/                 # Training results
├── sessions/                # Session JSONs
├── reports/                 # Generated PDFs
├── requirements.txt
└── .env.example
```

---

## 📊 Dataset: RecGym

- **10 subjects**, 5 sessions each
- **3 sensor positions**: wrist, leg, pocket (wrist only used)
- **12 exercise classes**: Squat, BenchPress, LegPress, Adductor, LegCurl, ArmCurl, RopeSkipping, Running, Walking, StairClimber, Riding, Null
- **Sensors**: 3-axis accelerometer, 3-axis gyroscope, HBC (Human Body Capacitance)
- **Sampling rate**: 20 Hz

---

*GymSense AI — DA-IICT Course Project 2025–26*
*Base paper: Hybrid CNN-Dilated Self-Attention for Gym Workout Recognition (RecGym Dataset)*
# GymSense
