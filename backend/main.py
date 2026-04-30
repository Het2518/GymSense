# === FILE: backend/main.py ===
# GymSense AI — FastAPI backend (production-grade)

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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Project root on sys.path so sibling modules (train, session_processor…) import ──
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Lightweight imports (DB + auth) — always safe, no heavy deps ──────────────
from backend.auth import get_current_user, router as auth_router
from backend.database import create_indexes, get_goals_collection, get_sessions_collection, ping_db
from backend.models import UserOut

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gymsense")

# ── Directories ───────────────────────────────────────────────────────────────
MODELS_DIR   = os.path.join(PROJECT_ROOT, "models")
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "sessions")
REPORTS_DIR  = os.path.join(PROJECT_ROOT, "reports")
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR,  exist_ok=True)

# ── ML state (populated lazily on first /api/analyze) ─────────────────────────
state: dict = {
    "model":        None,
    "scaler":       None,
    "le":           None,
    "model_loaded": False,
    "gpu_available": False,
    "gpu_name":     "N/A",
}

# Global lock created inside the running event loop (avoids deprecation warning)
_model_lock: asyncio.Lock | None = None


def _get_model_lock() -> asyncio.Lock:
    global _model_lock
    if _model_lock is None:
        _model_lock = asyncio.Lock()
    return _model_lock


# ── Lifespan: DB only — ML loaded lazily ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verify MongoDB is reachable (non-fatal)
    try:
        await ping_db()
        logger.info("MongoDB reachable ✓")
    except Exception as exc:
        logger.error(f"MongoDB ping failed (check MONGODB_URI env var): {exc}")

    # 2. Create indexes (idempotent, non-fatal)
    try:
        await create_indexes()
    except Exception as exc:
        logger.warning(f"Index creation skipped: {exc}")

    logger.info("GymSense startup complete ✓  (ML model loads on first /api/analyze)")
    yield
    logger.info("GymSense shutting down.")


# ── Lazy ML loader ────────────────────────────────────────────────────────────
async def _ensure_model_loaded() -> None:
    """Load TF model on first call, thread-safe. No-op if already loaded or TF missing."""
    if state["model_loaded"]:
        return
    lock = _get_model_lock()
    async with lock:
        if state["model_loaded"]:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _load_model_sync)


def _load_model_sync() -> None:
    """Runs in thread pool. Logs every path so we can see exactly why model fails to load."""
    try:
        import joblib
    except ImportError:
        logger.warning("joblib not installed — ML disabled")
        return

    try:
        import tensorflow as tf
    except (ImportError, Exception) as exc:
        logger.warning(f"tensorflow not available ({exc}) — ML disabled")
        return

    # Try multiple candidate roots so the model loads whether Render's CWD
    # is the project root OR the backend subdirectory.
    cwd = os.getcwd()
    candidates = [
        PROJECT_ROOT,                                    # computed from __file__
        cwd,                                             # actual CWD at runtime
        os.path.dirname(os.path.abspath(__file__)),      # backend/ dir itself
        os.path.join(cwd, ".."),                         # one level up from CWD
    ]

    mp = os.environ.get("MODEL_WEIGHTS_PATH")
    sp = os.environ.get("SCALER_PATH")
    lp = os.environ.get("LABEL_ENCODER_PATH")

    def _find(env_val, filename):
        if env_val and os.path.exists(env_val):
            return env_val
        for base in candidates:
            p = os.path.join(base, "models", filename)
            if os.path.exists(p):
                return p
        return None

    mp = _find(mp, "best_model.weights.h5")
    sp = _find(sp, "scaler.pkl")
    lp = _find(lp, "label_encoder.pkl")

    logger.info(f"ML paths — CWD:{cwd}  PROJECT_ROOT:{PROJECT_ROOT}")
    logger.info(f"  weights : {mp}")
    logger.info(f"  scaler  : {sp}")
    logger.info(f"  encoder : {lp}")

    try:
        gpus = tf.config.list_physical_devices("GPU")
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        if gpus:
            state["gpu_available"] = True
            state["gpu_name"] = gpus[0].name

        if sp and os.path.exists(sp):
            state["scaler"] = joblib.load(sp)
            logger.info("Scaler loaded ✓")
        else:
            logger.warning(f"Scaler not found: {sp}")

        if lp and os.path.exists(lp):
            state["le"] = joblib.load(lp)
            logger.info("Label encoder loaded ✓")
        else:
            logger.warning(f"Label encoder not found: {lp}")

        if mp and os.path.exists(mp) and state["le"] is not None:
            import train
            n_classes    = len(state["le"].classes_)
            state["model"] = train.build_hybrid_model(
                n_classes=n_classes, n_channels=7,
                window_size=80, n_windows=4, sensor_mode="combine",
            )
            state["model"].load_weights(mp)
            logger.info("Model weights loaded ✓")
        else:
            logger.warning(f"Model weights not found or LE missing: {mp}")

        if state["model"] and state["scaler"] and state["le"]:
            state["model_loaded"] = True
            logger.info("All ML artifacts ready ✓")
        else:
            logger.warning("ML model NOT loaded — /api/analyze will return 503")

    except Exception as exc:
        logger.warning(f"ML load failed: {exc}", exc_info=True)



# ── CORS: wildcard — allows all origins (safe because we use Bearer tokens, no cookies) ──
# Hardcoded here so it is NEVER affected by missing env vars or import-time ordering.
ALLOWED_ORIGINS = ["*"]

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="GymSense AI",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",   # keep docs available for debugging
    redoc_url=None,
)

# ── Middleware — ORDER MATTERS: CORS must be outermost (added first) ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,        # ["*"]
    allow_credentials=False,              # must be False when allow_origins=["*"]
    allow_methods=["*"],                  # GET POST PUT DELETE OPTIONS PATCH HEAD
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=86400,                        # cache OPTIONS preflight for 24 h
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

logger.info(f"CORS: allow_origins={ALLOWED_ORIGINS}")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)


# ── Request timing ────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    ms = (time.monotonic() - t0) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({ms:.0f}ms)")
    return response


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model_loaded": state["model_loaded"],
        "gpu_available": state["gpu_available"],
        "gpu_name": state["gpu_name"],
    }


# ── Analyze ───────────────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_session(
    file: UploadFile = File(...),
    coach_focus: str = Form(default="general"),
    current_user: UserOut = Depends(get_current_user),
):
    """Full workout analysis pipeline. JWT-protected."""
    await _ensure_model_loaded()

    if not state["model_loaded"]:
        raise HTTPException(
            status_code=503,
            detail="ML model not available on this server. Model files not found.",
        )

    session_id = str(uuid.uuid4())
    temp_csv   = os.path.join(SESSIONS_DIR, f"{session_id}_input.csv")

    try:
        content = await file.read()
        with open(temp_csv, "wb") as fh:
            fh.write(content)
        logger.info(f"[{session_id}] {len(content)} bytes from user {current_user.id}")

        loop = asyncio.get_running_loop()

        import session_processor
        session_json = await loop.run_in_executor(
            None, session_processor.process_session,
            temp_csv, state["model"], state["scaler"], state["le"],
        )
        session_json.update({
            "session_id":   session_id,
            "user_id":      current_user.id,
            "user_name":    current_user.name,
            "session_date": datetime.utcnow().isoformat(),
        })

        import llm_coach
        user_profile = {k: getattr(current_user, k, None) for k in (
            "name", "age", "gender", "weight", "height", "target_weight",
            "experience_level", "primary_goal", "workout_frequency",
            "preferred_workout_duration", "dietary_preference",
            "sleep_quality", "medical_conditions",
        )}
        coaching      = llm_coach.generate_coaching(session_json, focus=coach_focus, user_profile=user_profile)
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
            "session_id":  session_id,
            "pdf_url":     f"/api/report/{session_id}",
            "coaching":    coaching,
            "session_summary": {
                "total_duration_min": session_json["total_duration_min"],
                "total_exercises":    session_json["total_exercises"],
                "total_reps":         session_json["total_reps"],
                "total_sets":         session_json["total_sets"],
                "avg_tempo_score":    session_json["avg_tempo_score"],
            },
            "timeline":  session_json.get("timeline",  []),
            "exercises": session_json.get("exercises", []),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{session_id}] {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
        except OSError:
            pass


# ── Reports ───────────────────────────────────────────────────────────────────
@app.get("/api/report/{session_id}")
async def get_report(session_id: str):
    pdf = os.path.join(REPORTS_DIR, f"{session_id}.pdf")
    if not os.path.exists(pdf):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(pdf, media_type="application/pdf",
                        filename=f"GymSense_Report_{session_id[:8]}.pdf")


# ── Sessions ──────────────────────────────────────────────────────────────────
@app.get("/api/sessions")
async def list_sessions(current_user: UserOut = Depends(get_current_user)):
    col = get_sessions_collection()
    cursor = col.find(
        {"user_id": current_user.id},
        projection={"session_id": 1, "session_date": 1, "total_duration_min": 1,
                    "total_exercises": 1, "total_reps": 1, "avg_tempo_score": 1, "coaching": 1},
    ).sort("session_date", -1)
    result = []
    async for doc in cursor:
        result.append({
            "session_id":        doc.get("session_id"),
            "session_date":      doc.get("session_date", "Unknown"),
            "total_duration_min": doc.get("total_duration_min", 0),
            "total_exercises":    doc.get("total_exercises", 0),
            "total_reps":         doc.get("total_reps", 0),
            "avg_tempo_score":    doc.get("avg_tempo_score", 0),
            "coaching":           doc.get("coaching", {}),
        })
    return result


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str, current_user: UserOut = Depends(get_current_user)):
    col = get_sessions_collection()
    doc = await col.find_one({"session_id": session_id, "user_id": current_user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc["_id"] = str(doc["_id"])
    return doc


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def dashboard_stats(current_user: UserOut = Depends(get_current_user)):
    col      = get_sessions_collection()
    pipeline = [
        {"$match": {"user_id": current_user.id}},
        {"$group": {
            "_id": None,
            "total_workouts": {"$sum": 1},
            "total_duration": {"$sum": "$total_duration_min"},
            "total_reps":     {"$sum": "$total_reps"},
            "muscle_groups":  {"$push": "$muscle_groups_trained"},
        }},
    ]
    rows = await col.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {"total_workouts": 0, "total_duration_min": 0, "total_reps": 0, "muscle_distribution": {}}
    row = rows[0]
    muscle_counts: dict = {}
    for lst in row.get("muscle_groups", []):
        for m in (lst or []):
            muscle_counts[m] = muscle_counts.get(m, 0) + 1
    return {
        "total_workouts":    row["total_workouts"],
        "total_duration_min": round(row["total_duration"], 1),
        "total_reps":        row["total_reps"],
        "muscle_distribution": muscle_counts,
    }


# ── Goals ─────────────────────────────────────────────────────────────────────
from bson import ObjectId


@app.get("/api/goals")
async def list_goals(current_user: UserOut = Depends(get_current_user)):
    col    = get_goals_collection()
    cursor = col.find({"user_id": current_user.id}).sort("created_at", -1)
    goals  = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        goals.append(doc)
    return goals


@app.post("/api/goals", status_code=201)
async def create_goal(goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    col = get_goals_collection()
    goal_data["user_id"]    = current_user.id
    goal_data["created_at"] = datetime.utcnow().isoformat()
    goal_data["completed"]  = False
    result = await col.insert_one(goal_data)
    goal_data["_id"] = str(result.inserted_id)
    return goal_data


@app.put("/api/goals/{goal_id}")
async def update_goal(goal_id: str, goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    col = get_goals_collection()
    await col.update_one(
        {"_id": ObjectId(goal_id), "user_id": current_user.id},
        {"$set": goal_data},
    )
    return {"message": "Goal updated"}


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: str, current_user: UserOut = Depends(get_current_user)):
    col = get_goals_collection()
    await col.delete_one({"_id": ObjectId(goal_id), "user_id": current_user.id})
    return {"message": "Goal deleted"}


# ── Frontend SPA (only when dist folder present) ──────────────────────────────
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        fp = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
