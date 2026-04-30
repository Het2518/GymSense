"""
auth.py — Async JWT authentication with Motor (non-blocking bcrypt).

Key improvements vs. the old version:
- All MongoDB calls are `await`-ed (Motor async) → event loop never blocked.
- bcrypt hashing/verification offloaded to a thread pool via
  `asyncio.get_event_loop().run_in_executor()` so the async worker isn't
  stalled during the expensive hash computation.
- logger imported at module level (no per-call import).
- Email index enforced in database.py so the duplicate-email check is O(log n).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Optional

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from backend.config import settings
from backend.database import get_users_collection
from backend.models import Token, UserCreate, UserLogin, UserOut, UserProfileUpdate

logger = logging.getLogger("gymsense")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Password helpers (CPU-bound → thread pool) ────────────────────────────────

def _hash_password_sync(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password_sync(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


async def hash_password(plain: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _hash_password_sync, plain)


async def verify_password(plain: str, hashed: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _verify_password_sync, plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Current-user dependency ───────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    users = get_users_collection()
    user = await users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception

    return _doc_to_user_out(user)


# ── Utility ───────────────────────────────────────────────────────────────────

def _doc_to_user_out(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        age=doc.get("age"),
        gender=doc.get("gender"),
        weight=doc.get("weight"),
        height=doc.get("height"),
        target_weight=doc.get("target_weight"),
        experience_level=doc.get("experience_level"),
        primary_goal=doc.get("primary_goal"),
        workout_frequency=doc.get("workout_frequency"),
        preferred_workout_duration=doc.get("preferred_workout_duration"),
        dietary_preference=doc.get("dietary_preference"),
        sleep_quality=doc.get("sleep_quality"),
        medical_conditions=doc.get("medical_conditions"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=201)
async def register(user: UserCreate):
    users = get_users_collection()

    # Leverage the unique index — catch DuplicateKeyError instead of a
    # blocking find_one (one round-trip instead of two).
    from pymongo.errors import DuplicateKeyError  # motor re-exports this

    hashed = await hash_password(user.password)
    user_dict = {
        "name": user.name,
        "email": user.email.lower().strip(),
        "hashed_password": hashed,
    }
    try:
        result = await users.insert_one(user_dict)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")

    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token({"sub": str(result.inserted_id)}, expires)
    logger.info(f"New user registered: {user.email!r}")
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = get_users_collection()
    email = form_data.username.lower().strip()
    user = await users.find_one({"email": email})

    if not user or not await verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token({"sub": str(user["_id"])}, expires)
    logger.info(f"User logged in: {email!r}")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: UserOut = Depends(get_current_user),
):
    users = get_users_collection()
    update_data = profile_data.dict(exclude_unset=True)

    if update_data:
        await users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data},
        )
        logger.info(f"Profile updated for user {current_user.id}")

    updated = await users.find_one({"_id": ObjectId(current_user.id)})
    return _doc_to_user_out(updated)
