"""
auth.py — Async JWT authentication with Motor.
All DB calls are awaited. bcrypt runs in thread pool.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pymongo.errors import DuplicateKeyError

from backend.config import settings
from backend.database import get_users_collection
from backend.models import Token, UserCreate, UserOut, UserProfileUpdate

logger = logging.getLogger("gymsense")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Password (CPU-bound → thread pool) ───────────────────────────────────────

def _hash_sync(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_sync(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


async def _hash_password(plain: str) -> str:
    return await asyncio.get_running_loop().run_in_executor(None, _hash_sync, plain)


async def _verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.get_running_loop().run_in_executor(None, _verify_sync, plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Current user dependency ───────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise exc
    return _to_user_out(user)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_user_out(doc: dict) -> UserOut:
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
    hashed = await _hash_password(user.password)
    user_dict = {
        "name":            user.name,
        "email":           user.email.lower().strip(),
        "hashed_password": hashed,
    }
    try:
        result = await get_users_collection().insert_one(user_dict)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = create_access_token(
        {"sub": str(result.inserted_id)},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info(f"Registered: {user.email!r}")
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.lower().strip()
    user  = await get_users_collection().find_one({"email": email})

    if not user or not await _verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {"sub": str(user["_id"])},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info(f"Login: {email!r}")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: UserOut = Depends(get_current_user),
):
    # Pydantic v2: model_dump(); v1 fallback: dict()
    try:
        update_data = profile_data.model_dump(exclude_unset=True)
    except AttributeError:
        update_data = profile_data.dict(exclude_unset=True)

    if update_data:
        await get_users_collection().update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data},
        )
        logger.info(f"Profile updated: {current_user.id}")

    updated = await get_users_collection().find_one({"_id": ObjectId(current_user.id)})
    return _to_user_out(updated)
