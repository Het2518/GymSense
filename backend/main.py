# === FILE: backend/main.py ===
# GymSense AI — FastAPI backend

import os
import sys
import json
import uuid
import logging
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Add project root to path so we can import our modules
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import tensorflow as tf
import joblib

import session_processor
import report_builder
import llm_coach

# MongoDB & Auth imports
from backend.database import get_db, get_sessions_collection
from backend.auth import router as auth_router, get_current_user
from backend.models import UserOut

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('gymsense')

# ──────────────────────────────────────────────
# Directories
# ──────────────────────────────────────────────
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
SESSIONS_DIR = os.path.join(PROJECT_ROOT, 'sessions')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')
FRONTEND_DIST = os.path.join(PROJECT_ROOT, 'frontend', 'dist')

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────
app = FastAPI(title='GymSense AI SaaS', version='2.0.0')

# CORS — wildcard works fine for Bearer-token auth (no cookies used)
_raw_origins = os.environ.get('ALLOWED_ORIGINS', '*')
if _raw_origins.strip() == '*':
    ALLOWED_ORIGINS = ['*']
else:
    ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(',') if o.strip()]
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # '*' works because allow_credentials is False
    allow_credentials=False,         # Bearer tokens don't need this; cookies would
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['Content-Disposition'],
)

# Include Authentication Router
app.include_router(auth_router)

# ──────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────
state = {
    'model': None,
    'scaler': None,
    'le': None,
    'model_loaded': False,
    'gpu_available': False,
    'gpu_name': 'N/A',
}


# ──────────────────────────────────────────────
# Request logging middleware
# ──────────────────────────────────────────────
@app.middleware('http')
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.2f}s)")
    return response


# ──────────────────────────────────────────────
# Startup: load model, scaler, label encoder, DB
# ──────────────────────────────────────────────
@app.on_event('startup')
async def startup_load_model():
    """Load trained model, preprocessors, and initialize DB at startup."""
    # Initialize DB connection
    get_db()
    
    # GPU configuration
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        state['gpu_available'] = True
        state['gpu_name'] = gpus[0].name
        logger.info(f"GPU found: {gpus[0].name}")
    else:
        logger.warning("No GPU found — using CPU")

    # Load model artifacts
    model_weights_path = os.environ.get('MODEL_WEIGHTS_PATH', os.path.join(MODELS_DIR, 'best_model.weights.h5'))
    scaler_path = os.environ.get('SCALER_PATH', os.path.join(MODELS_DIR, 'scaler.pkl'))
    le_path = os.environ.get('LABEL_ENCODER_PATH', os.path.join(MODELS_DIR, 'label_encoder.pkl'))

    try:
        if os.path.exists(scaler_path):
            state['scaler'] = joblib.load(scaler_path)
            logger.info(f"Scaler loaded from {scaler_path}")
        else:
            logger.warning(f"Scaler file not found: {scaler_path}")

        if os.path.exists(le_path):
            state['le'] = joblib.load(le_path)
            logger.info(f"Label encoder loaded from {le_path}")
        else:
            logger.warning(f"Label encoder not found: {le_path}")

        if os.path.exists(model_weights_path) and state['le'] is not None:
            import train
            n_classes = len(state['le'].classes_)
            state['model'] = train.build_hybrid_model(
                n_classes=n_classes, 
                n_channels=7, 
                window_size=80, 
                n_windows=4, 
                sensor_mode='combine'
            )
            state['model'].load_weights(model_weights_path)
            logger.info(f"Model weights loaded from {model_weights_path}")
        else:
            logger.warning(f"Model weights file not found: {model_weights_path} or label encoder missing")

        if state['model'] and state['scaler'] and state['le']:
            state['model_loaded'] = True
            logger.info("All model artifacts loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model artifacts: {e}", exc_info=True)


# ──────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────

@app.get('/api/health')
async def health():
    """Health check endpoint."""
    return {
        'status': 'ok',
        'model_loaded': state['model_loaded'],
        'gpu_available': state['gpu_available'],
        'gpu_name': state['gpu_name'],
    }


@app.post('/api/analyze')
async def analyze_session(
    file: UploadFile = File(...),
    coach_focus: str = Form(default='general'),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Full session analysis pipeline (Protected by JWT).
    """
    if not state['model_loaded']:
        raise HTTPException(
            status_code=503,
            detail='Model not loaded. Please train the model first (python train.py).'
        )

    session_id = str(uuid.uuid4())
    temp_csv = os.path.join(SESSIONS_DIR, f'{session_id}_input.csv')

    try:
        content = await file.read()
        with open(temp_csv, 'wb') as f:
            f.write(content)
        logger.info(f"[{session_id}] CSV uploaded ({len(content)} bytes) by user {current_user.id}")

        # Run session processing pipeline
        logger.info(f"[{session_id}] Running inference pipeline ...")
        session_json = session_processor.process_session(
            temp_csv, state['model'], state['scaler'], state['le']
        )
        session_json['session_id'] = session_id
        session_json['user_id'] = current_user.id
        session_json['user_name'] = current_user.name
        session_json['session_date'] = datetime.utcnow().isoformat()  # fix: was 'Unknown'

        # LLM Coaching
        logger.info(f"[{session_id}] Generating coaching (focus={coach_focus}) ...")
        
        user_profile = {
            'name': current_user.name,
            'age': getattr(current_user, 'age', None),
            'gender': getattr(current_user, 'gender', None),
            'weight': getattr(current_user, 'weight', None),
            'height': getattr(current_user, 'height', None),
            'target_weight': getattr(current_user, 'target_weight', None),
            'experience_level': getattr(current_user, 'experience_level', None),
            'primary_goal': getattr(current_user, 'primary_goal', None),
            'workout_frequency': getattr(current_user, 'workout_frequency', None),
            'preferred_workout_duration': getattr(current_user, 'preferred_workout_duration', None),
            'dietary_preference': getattr(current_user, 'dietary_preference', None),
            'sleep_quality': getattr(current_user, 'sleep_quality', None),
            'medical_conditions': getattr(current_user, 'medical_conditions', None),
        }
        logger.info(f"[{session_id}] User profile for coaching: {user_profile}")
        coaching = llm_coach.generate_coaching(session_json, focus=coach_focus, user_profile=user_profile)
        coaching_text = llm_coach.format_coaching_text(coaching)
        session_json['coaching'] = coaching

        # PDF Report
        logger.info(f"[{session_id}] Building PDF report ...")
        pdf_path = report_builder.build_report(session_json, coaching_text, session_id)

        # Save session to MongoDB instead of file system
        sessions_collection = get_sessions_collection()
        sessions_collection.insert_one(session_json)

        # Clean up temp CSV
        if os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except OSError as e:
                logger.warning(f"[{session_id}] Could not delete temp CSV: {e}")

        logger.info(f"[{session_id}] Analysis complete")

        return {
            'session_id': session_id,
            'pdf_url': f'/api/report/{session_id}',
            'coaching': coaching,
            'session_summary': {
                'total_duration_min': session_json['total_duration_min'],
                'total_exercises': session_json['total_exercises'],
                'total_reps': session_json['total_reps'],
                'total_sets': session_json['total_sets'],
                'avg_tempo_score': session_json['avg_tempo_score'],
            },
            'timeline': session_json.get('timeline', []),
            'exercises': session_json.get('exercises', []),
        }

    except Exception as e:
        if os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except OSError:
                pass
        logger.error(f"[{session_id}] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/report/{session_id}')
async def get_report(session_id: str):
    """Serve a generated PDF report."""
    pdf_path = os.path.join(REPORTS_DIR, f'{session_id}.pdf')
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail='Report not found')
    return FileResponse(
        pdf_path,
        media_type='application/pdf',
        filename=f'GymSense_Diagnostic_Report_{session_id[:8]}.pdf',
    )


@app.get('/api/sessions')
async def list_sessions(current_user: UserOut = Depends(get_current_user)):
    """List past session summaries for the authenticated user from MongoDB."""
    sessions_collection = get_sessions_collection()
    cursor = sessions_collection.find({"user_id": current_user.id}).sort("session_date", -1)
    
    sessions = []
    for doc in cursor:
        sessions.append({
            'session_id': doc.get('session_id'),
            'session_date': doc.get('session_date', 'Unknown'),
            'total_duration_min': doc.get('total_duration_min', 0),
            'total_exercises': doc.get('total_exercises', 0),
            'total_reps': doc.get('total_reps', 0),
            'avg_tempo_score': doc.get('avg_tempo_score', 0),
            'coaching': doc.get('coaching', {})
        })
    return sessions

@app.get('/api/dashboard/stats')
async def dashboard_stats(current_user: UserOut = Depends(get_current_user)):
    """Get aggregated lifetime stats for the dashboard."""
    sessions_collection = get_sessions_collection()
    cursor = sessions_collection.find({"user_id": current_user.id})
    
    total_workouts = 0
    total_duration = 0
    total_reps = 0
    muscle_counts = {}
    
    for doc in cursor:
        total_workouts += 1
        total_duration += doc.get('total_duration_min', 0)
        total_reps += doc.get('total_reps', 0)
        
        for muscle in doc.get('muscle_groups_trained', []):
            muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1
            
    return {
        "total_workouts": total_workouts,
        "total_duration_min": round(total_duration, 1),
        "total_reps": total_reps,
        "muscle_distribution": muscle_counts
    }


@app.get('/api/sessions/{session_id}')
async def get_session_detail(session_id: str, current_user: UserOut = Depends(get_current_user)):
    """Get full detail of a specific session for comparison."""
    sessions_collection = get_sessions_collection()
    doc = sessions_collection.find_one({"session_id": session_id, "user_id": current_user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc['_id'] = str(doc['_id'])  # make serializable
    logger.info(f"Session detail fetched: {session_id} for user {current_user.id}")
    return doc


# ── Goals endpoints ───────────────────────────────────────────────────────────
from bson import ObjectId

def get_goals_collection():
    from backend.database import get_db
    db = get_db()
    return db['goals']

@app.get('/api/goals')
async def list_goals(current_user: UserOut = Depends(get_current_user)):
    """List all goals for the authenticated user."""
    goals_col = get_goals_collection()
    cursor = goals_col.find({"user_id": current_user.id}).sort("created_at", -1)
    goals = []
    for doc in cursor:
        doc['_id'] = str(doc['_id'])
        goals.append(doc)
    logger.info(f"Listed {len(goals)} goals for user {current_user.id}")
    return goals

@app.post('/api/goals')
async def create_goal(goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    """Create a new goal."""
    goals_col = get_goals_collection()
    goal_data['user_id'] = current_user.id
    goal_data['created_at'] = datetime.utcnow().isoformat()
    goal_data['completed'] = False
    result = goals_col.insert_one(goal_data)
    goal_data['_id'] = str(result.inserted_id)
    logger.info(f"Goal created for user {current_user.id}: {goal_data.get('title')}")
    return goal_data

@app.put('/api/goals/{goal_id}')
async def update_goal(goal_id: str, goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    """Update a goal."""
    goals_col = get_goals_collection()
    goals_col.update_one(
        {"_id": ObjectId(goal_id), "user_id": current_user.id},
        {"$set": goal_data}
    )
    logger.info(f"Goal updated {goal_id} for user {current_user.id}")
    return {"message": "Goal updated"}

@app.delete('/api/goals/{goal_id}')
async def delete_goal(goal_id: str, current_user: UserOut = Depends(get_current_user)):
    """Delete a goal."""
    goals_col = get_goals_collection()
    goals_col.delete_one({"_id": ObjectId(goal_id), "user_id": current_user.id})
    logger.info(f"Goal deleted {goal_id} for user {current_user.id}")
    return {"message": "Goal deleted"}


# ──────────────────────────────────────────────
# Serve Frontend (production build)
# ──────────────────────────────────────────────
if os.path.isdir(FRONTEND_DIST):
    app.mount('/assets', StaticFiles(directory=os.path.join(FRONTEND_DIST, 'assets')), name='assets')

    @app.get('/{full_path:path}')
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))

