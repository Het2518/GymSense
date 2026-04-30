"""
database.py — Production-grade async MongoDB client using Motor.

Key improvements:
- Motor (async) instead of PyMongo (sync) so the event loop is never blocked.
- Connection-pool tuned for Render's free tier (1 CPU, ~512 MB RAM).
- Automatic index creation at startup for fast email/user_id lookups.
- Explicit serverSelectionTimeoutMS so bad connections fail-fast instead
  of hanging and causing Render to return ERR_CONNECTION_RESET.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings

logger = logging.getLogger("gymsense")

# ── Singleton async client ────────────────────────────────────────────────────
_client: AsyncIOMotorClient | None = None
_db = None


def _build_client() -> AsyncIOMotorClient:
    """Build a Motor client with production-safe settings."""
    return AsyncIOMotorClient(
        settings.mongodb_uri,
        # Fail fast if Atlas is unreachable (prevents 30-s hang on cold start)
        serverSelectionTimeoutMS=8_000,
        # Keep connections alive through Render's TCP idle-timeout (90 s)
        socketTimeoutMS=30_000,
        connectTimeoutMS=10_000,
        # Pool tuned for a single-CPU Render instance
        maxPoolSize=10,
        minPoolSize=2,
        maxIdleTimeMS=45_000,
        # Retry transient network errors once automatically
        retryWrites=True,
        retryReads=True,
        # Compress wire traffic (saves bandwidth on free tier)
        compressors=["zstd", "zlib"],
    )


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def get_db():
    global _db
    if _db is None:
        _db = get_client()["gymsense"]
    return _db


# Convenience collection accessors (sync-style wrappers that return Motor collections)
def get_users_collection():
    return get_db()["users"]


def get_sessions_collection():
    return get_db()["sessions"]


def get_goals_collection():
    return get_db()["goals"]


# ── Index bootstrap (called once at startup) ──────────────────────────────────
async def create_indexes():
    """Ensure all performance-critical indexes exist.

    This is idempotent — safe to call on every startup.
    Atlas free-tier supports at most 3 collections and sparse indexes,
    so we keep these minimal but impactful.
    """
    db = get_db()
    try:
        # users: email uniqueness + fast login lookup
        await db["users"].create_index("email", unique=True, background=True)

        # sessions: user's session listing (sorted by date)
        await db["sessions"].create_index(
            [("user_id", 1), ("session_date", -1)], background=True
        )

        # goals: user's goal listing
        await db["goals"].create_index(
            [("user_id", 1), ("created_at", -1)], background=True
        )

        logger.info("MongoDB indexes ensured ✓")
    except Exception as exc:
        logger.warning(f"Index creation warning (non-fatal): {exc}")


async def ping_db():
    """Verify Atlas is reachable. Raises on failure."""
    await get_client().admin.command("ping")
