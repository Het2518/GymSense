# === FILE: backend/main.py ===
# GymSense AI — FastAPI backend (production-grade, crash-resistant)

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# ── project root on sys.path ──────────────────────────────────────────────────
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── MongoDB & Auth (lightweight — always safe to import) ──────────────────────
from backend.auth import get_current_user
from backend.auth import router as auth_router
from backend.database import (
    create_indexes,
    get_goals_collection,
    get_sessions_collection,
    ping_db,
)
from backend.models import UserOut

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("gymsense")

# ── Directories ───────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "sessions")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Global ML state ───────────────────────────────────────────────────────────
state: dict = {
    "model": None,
    "scaler": None,
    "le": None,
    "model_loaded": False,
    "gpu_available": False,
    "gpu_name": "N/A",
}


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. DB ping — non-fatal on failure
    try:
        await ping_db()
        logger.info("MongoDB reachable ✓")
    except Exception as exc:
        logger.error(f"MongoDB ping failed: {exc}")

    # 2. Indexes
    try:
        await create_indexes()
    except Exception as exc:
        logger.warning(f"Index creation skipped: {exc}")

    # ML model loaded lazily on first /api/analyze call — keeps startup fast
    logger.info("GymSense backend startup complete ✓")
    yield
    logger.info("GymSense backend shutting down …")


_model_load_lock = asyncio.Lock() if False else None  # initialised below


async def _ensure_model_loaded():
    """Lazy-load ML model on first call. Thread-safe via asyncio.Lock."""
    global _model_load_lock
    if _model_load_lock is None:
        _model_load_lock = asyncio.Lock()

    if state["model_loaded"]:
        return

    async with _model_load_lock:
        if state["model_loaded"]:  # double-check after acquiring lock
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_model_sync)


def _load_model_sync():
    """Synchronous ML loading — runs in thread pool, never on event loop."""
    try:
        import joblib
    except ImportError:
        logger.warning("joblib not installed — ML disabled")
        return
    try:
        import tensorflow as tf
    except ImportError:
        logger.warning("tensorflow not installed — ML disabled")
        return
    except Exception as exc:
        logger.warning(f"tensorflow import failed: {exc} — ML disabled")
        return

    try:
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            state["gpu_available"] = True
            state["gpu_name"] = gpus[0].name

        model_path = os.environ.get("MODEL_WEIGHTS_PATH", os.path.join(MODELS_DIR, "best_model.weights.h5"))
        scaler_path = os.environ.get("SCALER_PATH", os.path.join(MODELS_DIR, "scaler.pkl"))
        le_path = os.environ.get("LABEL_ENCODER_PATH", os.path.join(MODELS_DIR, "label_encoder.pkl"))

        if os.path.exists(scaler_path):
            state["scaler"] = joblib.load(scaler_path)
        if os.path.exists(le_path):
            state["le"] = joblib.load(le_path)

        if os.path.exists(model_path) and state["le"]:
            import train
            n_classes = len(state["le"].classes_)
            state["model"] = train.build_hybrid_model(
                n_classes=n_classes, n_channels=7, window_size=80, n_windows=4, sensor_mode="combine"
            )
            state["model"].load_weights(model_path)

        if state["model"] and state["scaler"] and state["le"]:
            state["model_loaded"] = True
            logger.info("All ML artifacts loaded ✓")
    except Exception as exc:
        logger.warning(f"ML model load failed (ML disabled): {exc}")


# ── CORS origins ──────────────────────────────────────────────────────────────
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    ["*"]
    if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="GymSense AI SaaS",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs" if os.environ.get("ENV") != "production" else None,
    redoc_url=None,
)

# ── IMPORTANT: CORS must be the FIRST middleware added ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=86400,  # cache preflight for 24 h — browsers won't re-send OPTIONS
)

# GZip after CORS
app.add_middleware(GZipMiddleware, minimum_size=1024)

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

# ── Auth router ───────────────────────────────────────────────────────────────
app.include_router(auth_router)


# ── Request-timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed = (time.monotonic() - t0) * 1000
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.1f} ms)"
    )
    return response


# ── Health check (unauthenticated, always responds) ───────────────────────────
@app.get("/api/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model_loaded": state["model_loaded"],
        "gpu_available": state["gpu_available"],
        "gpu_name": state["gpu_name"],
    }


# ── Analyze session ───────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_session(
    file: UploadFile = File(...),
    coach_focus: str = Form(default="general"),
    current_user: UserOut = Depends(get_current_user),
):
    """Full session analysis pipeline (JWT-protected)."""
    # Lazy-load ML model on first request
    await _ensure_model_loaded()

    if not state["model_loaded"]:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Model files (best_model.weights.h5, scaler.pkl, label_encoder.pkl) not found on server.",
        )

    session_id = str(uuid.uuid4())
    temp_csv = os.path.join(SESSIONS_DIR, f"{session_id}_input.csv")

    try:
        content = await file.read()
        with open(temp_csv, "wb") as f:
            f.write(content)
        logger.info(
            f"[{session_id}] CSV uploaded ({len(content)} bytes) by {current_user.id}"
        )

        loop = asyncio.get_event_loop()

        import session_processor

        session_json = await loop.run_in_executor(
            None,
            session_processor.process_session,
            temp_csv,
            state["model"],
            state["scaler"],
            state["le"],
        )
        session_json.update(
            {
                "session_id": session_id,
                "user_id": current_user.id,
                "user_name": current_user.name,
                "session_date": datetime.utcnow().isoformat(),
            }
        )

        import llm_coach

        user_profile = {
            k: getattr(current_user, k, None)
            for k in (
                "name", "age", "gender", "weight", "height",
                "target_weight", "experience_level", "primary_goal",
                "workout_frequency", "preferred_workout_duration",
                "dietary_preference", "sleep_quality", "medical_conditions",
            )
        }
        coaching = llm_coach.generate_coaching(
            session_json, focus=coach_focus, user_profile=user_profile
        )
        coaching_text = llm_coach.format_coaching_text(coaching)
        session_json["coaching"] = coaching

        import report_builder

        await loop.run_in_executor(
            None, report_builder.build_report, session_json, coaching_text, session_id
        )

        sessions_col = get_sessions_collection()
        await sessions_col.insert_one(session_json)

        logger.info(f"[{session_id}] Analysis complete ✓")
        return {
            "session_id": session_id,
            "pdf_url": f"/api/report/{session_id}",
            "coaching": coaching,
            "session_summary": {
                "total_duration_min": session_json["total_duration_min"],
                "total_exercises": session_json["total_exercises"],
                "total_reps": session_json["total_reps"],
                "total_sets": session_json["total_sets"],
                "avg_tempo_score": session_json["avg_tempo_score"],
            },
            "timeline": session_json.get("timeline", []),
            "exercises": session_json.get("exercises", []),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{session_id}] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
        except OSError:
            pass


# ── Report download ───────────────────────────────────────────────────────────
@app.get("/api/report/{session_id}")
async def get_report(session_id: str):
    pdf_path = os.path.join(REPORTS_DIR, f"{session_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"GymSense_Report_{session_id[:8]}.pdf",
    )


# ── Sessions ──────────────────────────────────────────────────────────────────
@app.get("/api/sessions")
async def list_sessions(current_user: UserOut = Depends(get_current_user)):
    sessions_col = get_sessions_collection()
    cursor = sessions_col.find(
        {"user_id": current_user.id},
        projection={
            "session_id": 1, "session_date": 1, "total_duration_min": 1,
            "total_exercises": 1, "total_reps": 1, "avg_tempo_score": 1, "coaching": 1,
        },
    ).sort("session_date", -1)

    sessions = []
    async for doc in cursor:
        sessions.append(
            {
                "session_id": doc.get("session_id"),
                "session_date": doc.get("session_date", "Unknown"),
                "total_duration_min": doc.get("total_duration_min", 0),
                "total_exercises": doc.get("total_exercises", 0),
                "total_reps": doc.get("total_reps", 0),
                "avg_tempo_score": doc.get("avg_tempo_score", 0),
                "coaching": doc.get("coaching", {}),
            }
        )
    return sessions


@app.get("/api/sessions/{session_id}")
async def get_session_detail(
    session_id: str, current_user: UserOut = Depends(get_current_user)
):
    sessions_col = get_sessions_collection()
    doc = await sessions_col.find_one(
        {"session_id": session_id, "user_id": current_user.id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc["_id"] = str(doc["_id"])
    return doc


# ── Dashboard stats ───────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def dashboard_stats(current_user: UserOut = Depends(get_current_user)):
    sessions_col = get_sessions_collection()
    pipeline = [
        {"$match": {"user_id": current_user.id}},
        {
            "$group": {
                "_id": None,
                "total_workouts": {"$sum": 1},
                "total_duration": {"$sum": "$total_duration_min"},
                "total_reps": {"$sum": "$total_reps"},
                "muscle_groups": {"$push": "$muscle_groups_trained"},
            }
        },
    ]
    results = await sessions_col.aggregate(pipeline).to_list(length=1)
    if not results:
        return {"total_workouts": 0, "total_duration_min": 0, "total_reps": 0, "muscle_distribution": {}}

    row = results[0]
    muscle_counts: dict = {}
    for group_list in row.get("muscle_groups", []):
        for muscle in (group_list or []):
            muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1

    return {
        "total_workouts": row["total_workouts"],
        "total_duration_min": round(row["total_duration"], 1),
        "total_reps": row["total_reps"],
        "muscle_distribution": muscle_counts,
    }


# ── Goals ─────────────────────────────────────────────────────────────────────
from bson import ObjectId


@app.get("/api/goals")
async def list_goals(current_user: UserOut = Depends(get_current_user)):
    goals_col = get_goals_collection()
    cursor = goals_col.find({"user_id": current_user.id}).sort("created_at", -1)
    goals = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        goals.append(doc)
    return goals


@app.post("/api/goals", status_code=201)
async def create_goal(goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    goals_col = get_goals_collection()
    goal_data["user_id"] = current_user.id
    goal_data["created_at"] = datetime.utcnow().isoformat()
    goal_data["completed"] = False
    result = await goals_col.insert_one(goal_data)
    goal_data["_id"] = str(result.inserted_id)
    return goal_data


@app.put("/api/goals/{goal_id}")
async def update_goal(
    goal_id: str, goal_data: dict, current_user: UserOut = Depends(get_current_user)
):
    goals_col = get_goals_collection()
    await goals_col.update_one(
        {"_id": ObjectId(goal_id), "user_id": current_user.id},
        {"$set": goal_data},
    )
    return {"message": "Goal updated"}


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: str, current_user: UserOut = Depends(get_current_user)):
    goals_col = get_goals_collection()
    await goals_col.delete_one({"_id": ObjectId(goal_id), "user_id": current_user.id})
    return {"message": "Goal deleted"}


# ── Serve frontend SPA ────────────────────────────────────────────────────────
if os.path.isdir(FRONTEND_DIST):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
