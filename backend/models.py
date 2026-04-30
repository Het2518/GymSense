from pydantic import BaseModel
from typing import Optional, List

# --- AUTH MODELS ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    # Basic body stats
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None          # kg
    height: Optional[float] = None          # cm
    target_weight: Optional[float] = None   # kg
    # Fitness profile
    experience_level: Optional[str] = None           # Beginner / Intermediate / Advanced / Elite
    primary_goal: Optional[str] = None               # Hypertrophy / Strength / Weight Loss / Endurance / General Health
    workout_frequency: Optional[int] = None          # days per week
    preferred_workout_duration: Optional[int] = None # minutes per session
    # Lifestyle
    dietary_preference: Optional[str] = None  # Standard / Vegetarian / Vegan / Keto / Paleo
    sleep_quality: Optional[str] = None       # Poor / Fair / Good / Excellent
    # Medical / free text
    medical_conditions: Optional[str] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    target_weight: Optional[float] = None
    experience_level: Optional[str] = None
    primary_goal: Optional[str] = None
    workout_frequency: Optional[int] = None
    preferred_workout_duration: Optional[int] = None
    dietary_preference: Optional[str] = None
    sleep_quality: Optional[str] = None
    medical_conditions: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

# --- SESSION MODELS ---
class SessionOut(BaseModel):
    session_id: str
    session_date: str
    total_duration_min: float
    total_exercises: int
    total_reps: int
    avg_tempo_score: float
