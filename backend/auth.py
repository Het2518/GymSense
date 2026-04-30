from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from bson import ObjectId

from backend.config import settings
from backend.models import UserCreate, UserLogin, UserOut, Token, UserProfileUpdate
from backend.database import get_users_collection

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/auth", tags=["auth"])

def verify_password(plain_password: str, hashed_password: str):
    # Try to verify the password using bcrypt directly
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str):
    # Hash the password using bcrypt directly, ensuring it's safely decoded to string for storage
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
        
    import logging
    logger = logging.getLogger('gymsense')
    logger.info(f"Fetched user data for {user_id}")
    
    return UserOut(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        age=user.get("age"),
        gender=user.get("gender"),
        weight=user.get("weight"),
        height=user.get("height"),
        target_weight=user.get("target_weight"),
        experience_level=user.get("experience_level"),
        primary_goal=user.get("primary_goal"),
        workout_frequency=user.get("workout_frequency"),
        preferred_workout_duration=user.get("preferred_workout_duration"),
        dietary_preference=user.get("dietary_preference"),
        sleep_quality=user.get("sleep_quality"),
        medical_conditions=user.get("medical_conditions"),
    )


@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    users = get_users_collection()
    if users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    user_dict = {
        "name": user.name,
        "email": user.email,
        "hashed_password": hashed_password
    }
    
    result = users.insert_one(user_dict)
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(result.inserted_id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = get_users_collection()
    user = users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: UserOut = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserOut)
async def update_profile(profile_data: UserProfileUpdate, current_user: UserOut = Depends(get_current_user)):
    import logging
    logger = logging.getLogger('gymsense')
    logger.info(f"Updating profile for user {current_user.id} with data: {profile_data.dict(exclude_unset=True)}")
    
    users = get_users_collection()
    update_data = profile_data.dict(exclude_unset=True)
    
    if update_data:
        users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data}
        )
        logger.info(f"Profile updated successfully for user {current_user.id}")
    
    # Fetch updated user
    updated_user = users.find_one({"_id": ObjectId(current_user.id)})
    logger.info(f"Profile fetch after update for user {current_user.id}: {updated_user.get('primary_goal')} / {updated_user.get('experience_level')}")
    return UserOut(
        id=str(updated_user["_id"]),
        name=updated_user["name"],
        email=updated_user["email"],
        age=updated_user.get("age"),
        gender=updated_user.get("gender"),
        weight=updated_user.get("weight"),
        height=updated_user.get("height"),
        target_weight=updated_user.get("target_weight"),
        experience_level=updated_user.get("experience_level"),
        primary_goal=updated_user.get("primary_goal"),
        workout_frequency=updated_user.get("workout_frequency"),
        preferred_workout_duration=updated_user.get("preferred_workout_duration"),
        dietary_preference=updated_user.get("dietary_preference"),
        sleep_quality=updated_user.get("sleep_quality"),
        medical_conditions=updated_user.get("medical_conditions"),
    )
