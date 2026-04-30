"""
database.py — Async Motor client, production-tuned for Render free tier.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.config import settings

logger = logging.getLogger("gymsense")

_client: Optional[AsyncIOMotorClient] = None
_db:     Optional[AsyncIOMotorDatabase] = None


def _build_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=8_000,   # fail-fast on bad URI
        socketTimeoutMS=30_000,
        connectTimeoutMS=10_000,
        maxPoolSize=10,
        minPoolSize=2,
        maxIdleTimeMS=45_000,
        retryWrites=True,
        retryReads=True,
        # zstd removed — requires extra native lib not on Render free tier
        compressors=["zlib"],
    )


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()["gymsense"]
    return _db


def get_users_collection():
    return get_db()["users"]

def get_sessions_collection():
    return get_db()["sessions"]

def get_goals_collection():
    return get_db()["goals"]


async def create_indexes() -> None:
    """Idempotent — safe to call every startup."""
    db = get_db()
    # unique email index (enables DuplicateKeyError on duplicate registration)
    await db["users"].create_index("email", unique=True)
    # compound indexes for fast per-user queries
    await db["sessions"].create_index([("user_id", 1), ("session_date", -1)])
    await db["goals"].create_index([("user_id", 1), ("created_at", -1)])
    logger.info("MongoDB indexes ensured ✓")


async def ping_db() -> None:
    """Raises if Atlas unreachable."""
    await get_client().admin.command("ping")
