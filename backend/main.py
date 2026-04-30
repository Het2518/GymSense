# === FILE: backend/main.py ===
# GymSense AI — FastAPI backend (production-grade, Render root=backend/)

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

# ── All paths resolved relative to THIS file — never depends on CWD ───────────
BACKEND_DIR  = Path(__file__).resolve().parent   # .../backend/
PROJECT_ROOT = str(BACKEND_DIR.parent)           # .../  (project root)

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(Path(PROJECT_ROOT) / ".env", override=False)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.auth import get_current_user, router as auth_router
from backend.database import (
    create_indexes, get_goals_collection, get_sessions_collection, ping_db
)
from backend.models import UserOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gymsense")

# ── Absolute directories ───────────────────────────────────────────────────────
MODELS_DIR    = str(BACKEND_DIR / "models")
SESSIONS_DIR  = str(BACKEND_DIR / "sessions")
REPORTS_DIR   = str(BACKEND_DIR / "reports")
FRONTEND_DIST = str(BACKEND_DIR.parent / "frontend" / "dist")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR,  exist_ok=True)

logger.info(f"BACKEND_DIR={BACKEND_DIR}  MODELS_DIR={MODELS_DIR}")

# ── ML state ──────────────────────────────────────────────────────────────────
state: dict = {
    "model":         None,
    "scaler":        None,
    "le":            None,
    "model_loaded":  False,
    "gpu_available": False,
    "gpu_name":      "N/A",
}

_model_lock: asyncio.Lock | None = None

def _get_lock() -> asyncio.Lock:
    global _model_lock
    if _model_lock is None:
        _model_lock = asyncio.Lock()
    return _model_lock


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ping_db()
        logger.info("MongoDB reachable ✓")
    except Exception as exc:
        logger.error(f"MongoDB ping failed: {exc}")
    try:
        await create_indexes()
    except Exception as exc:
        logger.warning(f"Index creation skipped: {exc}")
    logger.info("GymSense startup complete ✓")
    yield
    logger.info("GymSense shutting down.")


# ── Model architecture (inline — no import train needed) ──────────────────────
def _build_model(n_classes: int):
    """
    Builds the Hybrid CNN-Dilated Self-Attention skeleton.
    Architecture exactly matches train.py so load_weights(.h5) works.
    Lambda layers replaced with direct tensor ops — no serialization issues.
    """
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, regularizers, constraints

    def conv_block(x, in_chans, F1=32, D=4, pfx=''):
        x = layers.Conv2D(F1, (20, 1), padding='same', use_bias=True,
                          kernel_regularizer=regularizers.L2(0.009),
                          kernel_constraint=constraints.max_norm(0.8),
                          name=f'{pfx}_conv1')(x)
        x = layers.LayerNormalization(name=f'{pfx}_ln1')(x)
        x = layers.Activation('elu', name=f'{pfx}_elu1')(x)
        x = layers.DepthwiseConv2D((1, in_chans), depth_multiplier=D, use_bias=True,
                                    depthwise_regularizer=regularizers.L2(0.009),
                                    depthwise_constraint=constraints.max_norm(0.8),
                                    name=f'{pfx}_dwconv')(x)
        x = layers.LayerNormalization(name=f'{pfx}_ln2')(x)
        x = layers.Activation('elu', name=f'{pfx}_elu2')(x)
        x = layers.Dropout(0.1, name=f'{pfx}_drop1')(x)
        F2 = F1 * D
        x = layers.Conv2D(F2, (10, 1), padding='same', use_bias=True,
                          kernel_regularizer=regularizers.L2(0.009),
                          kernel_constraint=constraints.max_norm(0.8),
                          name=f'{pfx}_conv2')(x)
        x = layers.LayerNormalization(name=f'{pfx}_ln3')(x)
        x = layers.Activation('elu', name=f'{pfx}_elu3')(x)
        x = layers.Dropout(0.1, name=f'{pfx}_drop2')(x)
        return x

    def mha_block(x, pfx=''):
        skip = x
        x = layers.LayerNormalization(epsilon=1e-6, name=f'{pfx}_mha_ln')(x)
        x = layers.MultiHeadAttention(num_heads=4, key_dim=8, dropout=0.1,
                                       name=f'{pfx}_mha')(x, x)
        x = layers.Dropout(0.3, name=f'{pfx}_mha_drop')(x)
        x = layers.Add(name=f'{pfx}_mha_add')([skip, x])
        return x

    def dilated_stage(x, rate, sname):
        res = x
        x = layers.Conv1D(32, 3, dilation_rate=rate, padding='causal',
                          activation='linear',
                          kernel_regularizer=regularizers.L2(0.009),
                          kernel_constraint=constraints.max_norm(0.6),
                          kernel_initializer='he_uniform',
                          name=f'{sname}_conv1')(x)
        x = layers.BatchNormalization(name=f'{sname}_bn1')(x)
        x = layers.Activation('elu', name=f'{sname}_elu1')(x)
        x = layers.Dropout(0.1, name=f'{sname}_drop1')(x)
        x = layers.Conv1D(32, 3, dilation_rate=rate, padding='causal',
                          activation='linear',
                          kernel_regularizer=regularizers.L2(0.009),
                          kernel_constraint=constraints.max_norm(0.6),
                          kernel_initializer='he_uniform',
                          name=f'{sname}_conv2')(x)
        x = layers.BatchNormalization(name=f'{sname}_bn2')(x)
        x = layers.Activation('elu', name=f'{sname}_elu2')(x)
        x = layers.Dropout(0.1, name=f'{sname}_drop2')(x)
        if res.shape[-1] != 32:
            res = layers.Conv1D(32, 1, name=f'{sname}_res_conv')(res)
        x = layers.Add(name=f'{sname}_add')([res, x])
        x = layers.Activation('elu', name=f'{sname}_elu_out')(x)
        return x

    # Input: (batch, 1, 80, 7)
    inp = layers.Input(shape=(1, 80, 7), name='input')

    # Slice channels — direct tensor ops, no Lambda layers
    imu = inp[:, :, :, 0:6]
    cap = tf.expand_dims(inp[:, :, :, -1], -1)

    imu = layers.Permute((2, 3, 1), name='permute_imu')(imu)
    cap = layers.Permute((2, 3, 1), name='permute_cap')(cap)

    imu_out = conv_block(imu, in_chans=6, pfx='imu')
    cap_out = conv_block(cap, in_chans=1, pfx='cap')

    fused  = layers.Concatenate(axis=-1, name='concat_branches')([imu_out, cap_out])
    # squeeze spatial dim: (batch,80,1,256) → (batch,80,256)
    block1 = fused[:, :, -1, :]

    n_windows = 4
    window_outputs = []
    for i in range(n_windows):
        s, e = i, 80 - n_windows + i + 1
        win = block1[:, s:e, :]
        win = mha_block(win, pfx=f'w{i}')
        win = dilated_stage(win, 1,           f'w{i}_di_s1')
        win = dilated_stage(win, 2 ** (i+1),  f'w{i}_di_s2')
        win = win[:, -1, :]
        win = layers.Dense(n_classes, kernel_regularizer=regularizers.L2(0.5),
                           name=f'w{i}_dense')(win)
        window_outputs.append(win)

    avg    = layers.Average(name='avg_windows')(window_outputs)
    output = layers.Activation('softmax', name='softmax')(avg)
    return keras.Model(inputs=inp, outputs=output, name='HybridCNN_DilatedSA')


# ── Lazy ML loader ────────────────────────────────────────────────────────────
async def _ensure_model_loaded() -> None:
    if state["model_loaded"]:
        return
    async with _get_lock():
        if state["model_loaded"]:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _load_model_sync)


def _load_model_sync() -> None:
    """
    Load saved model artifacts from backend/models/.
    Uses pre-trained weights directly — no training, no import train.
    """
    def _abs(env_key: str, default_name: str) -> str:
        val = os.environ.get(env_key, "")
        if val:
            p = Path(val)
            return str(p if p.is_absolute() else BACKEND_DIR / p)
        return str(BACKEND_DIR / "models" / default_name)

    mp = _abs("MODEL_WEIGHTS_PATH", "best_model.weights.h5")
    sp = _abs("SCALER_PATH",        "scaler.pkl")
    lp = _abs("LABEL_ENCODER_PATH", "label_encoder.pkl")

    logger.info(f"ML loader — weights:{mp} exists={os.path.exists(mp)}")
    logger.info(f"            scaler :{sp} exists={os.path.exists(sp)}")
    logger.info(f"            encoder:{lp} exists={os.path.exists(lp)}")

    try:
        import joblib
    except ImportError:
        logger.error("joblib not installed"); return

    try:
        import tensorflow as tf
        logger.info(f"TensorFlow {tf.__version__} ✓")
    except Exception as exc:
        logger.error(f"TF import failed: {exc}"); return

    try:
        if not os.path.exists(sp):
            logger.error(f"Scaler missing: {sp}"); return
        state["scaler"] = joblib.load(sp)
        logger.info("scaler.pkl loaded ✓")

        if not os.path.exists(lp):
            logger.error(f"Label encoder missing: {lp}"); return
        state["le"] = joblib.load(lp)
        logger.info(f"label_encoder.pkl loaded ✓  classes={list(state['le'].classes_)}")

        if not os.path.exists(mp):
            logger.error(f"Weights missing: {mp}"); return

        n_classes = len(state["le"].classes_)
        logger.info(f"Building model skeleton (n_classes={n_classes}) ...")
        model = _build_model(n_classes)
        model.load_weights(mp)
        state["model"] = model
        state["model_loaded"] = True
        logger.info("model_loaded=True ✓  /api/analyze is ready")

    except Exception as exc:
        logger.error(f"ML load failed: {exc}", exc_info=True)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="GymSense AI",
    version="2.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=86400,
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.include_router(auth_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    ms = (time.monotonic() - t0) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({ms:.0f}ms)")
    return response


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status":        "ok",
        "model_loaded":  state["model_loaded"],
        "gpu":           state["gpu_available"],
        "models_dir":    MODELS_DIR,
        "models_exist":  os.path.isdir(MODELS_DIR),
    }


# ── Analyze ───────────────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_session(
    file: UploadFile = File(...),
    coach_focus: str = Form(default="general"),
    current_user: UserOut = Depends(get_current_user),
):
    await _ensure_model_loaded()

    if not state["model_loaded"]:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ML model not loaded. "
                f"weights={os.path.exists(str(BACKEND_DIR/'models'/'best_model.weights.h5'))}, "
                f"scaler={os.path.exists(str(BACKEND_DIR/'models'/'scaler.pkl'))}, "
                f"encoder={os.path.exists(str(BACKEND_DIR/'models'/'label_encoder.pkl'))}, "
                f"models_dir={MODELS_DIR}"
            )
        )

    session_id = str(uuid.uuid4())
    temp_csv   = os.path.join(SESSIONS_DIR, f"{session_id}_input.csv")

    try:
        content = await file.read()
        with open(temp_csv, "wb") as fh:
            fh.write(content)
        logger.info(f"[{session_id}] {len(content)} bytes from {current_user.id}")

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

        await get_sessions_collection().insert_one(session_json)
        logger.info(f"[{session_id}] complete ✓")

        return {
            "session_id": session_id,
            "pdf_url":    f"/api/report/{session_id}",
            "coaching":   coaching,
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


# ── Report ────────────────────────────────────────────────────────────────────
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
        projection={"session_id":1,"session_date":1,"total_duration_min":1,
                    "total_exercises":1,"total_reps":1,"avg_tempo_score":1,"coaching":1},
    ).sort("session_date", -1)
    result = []
    async for doc in cursor:
        result.append({
            "session_id":         doc.get("session_id"),
            "session_date":       doc.get("session_date", "Unknown"),
            "total_duration_min": doc.get("total_duration_min", 0),
            "total_exercises":    doc.get("total_exercises", 0),
            "total_reps":         doc.get("total_reps", 0),
            "avg_tempo_score":    doc.get("avg_tempo_score", 0),
            "coaching":           doc.get("coaching", {}),
        })
    return result


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str, current_user: UserOut = Depends(get_current_user)):
    doc = await get_sessions_collection().find_one(
        {"session_id": session_id, "user_id": current_user.id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc["_id"] = str(doc["_id"])
    return doc


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def dashboard_stats(current_user: UserOut = Depends(get_current_user)):
    col = get_sessions_collection()
    pipeline = [
        {"$match": {"user_id": current_user.id}},
        {"$group": {"_id": None,
                    "total_workouts": {"$sum": 1},
                    "total_duration": {"$sum": "$total_duration_min"},
                    "total_reps":     {"$sum": "$total_reps"},
                    "muscle_groups":  {"$push": "$muscle_groups_trained"}}},
    ]
    rows = await col.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {"total_workouts":0,"total_duration_min":0,"total_reps":0,"muscle_distribution":{}}
    row = rows[0]
    mc: dict = {}
    for lst in row.get("muscle_groups", []):
        for m in (lst or []):
            mc[m] = mc.get(m, 0) + 1
    return {
        "total_workouts":     row["total_workouts"],
        "total_duration_min": round(row["total_duration"], 1),
        "total_reps":         row["total_reps"],
        "muscle_distribution": mc,
    }


# ── Goals ─────────────────────────────────────────────────────────────────────
from bson import ObjectId


@app.get("/api/goals")
async def list_goals(current_user: UserOut = Depends(get_current_user)):
    col = get_goals_collection()
    cursor = col.find({"user_id": current_user.id}).sort("created_at", -1)
    goals = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        goals.append(doc)
    return goals


@app.post("/api/goals", status_code=201)
async def create_goal(goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    col = get_goals_collection()
    goal_data.update({"user_id": current_user.id,
                      "created_at": datetime.utcnow().isoformat(),
                      "completed": False})
    result = await col.insert_one(goal_data)
    goal_data["_id"] = str(result.inserted_id)
    return goal_data


@app.put("/api/goals/{goal_id}")
async def update_goal(goal_id: str, goal_data: dict, current_user: UserOut = Depends(get_current_user)):
    await get_goals_collection().update_one(
        {"_id": ObjectId(goal_id), "user_id": current_user.id}, {"$set": goal_data})
    return {"message": "Goal updated"}


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: str, current_user: UserOut = Depends(get_current_user)):
    await get_goals_collection().delete_one(
        {"_id": ObjectId(goal_id), "user_id": current_user.id})
    return {"message": "Goal deleted"}


# ── Frontend SPA (only if built dist exists on server) ────────────────────────
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        fp = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
