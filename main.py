# Root entry point — Render runs: uvicorn main:app --host 0.0.0.0 --port $PORT
# This simply re-exports the FastAPI app from backend/main.py
from backend.main import app  # noqa: F401
