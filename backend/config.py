from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str
    jwt_secret: str = "gymsense-change-this-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    gemini_api_key: str = ""
    # Comma-separated list of allowed CORS origins.
    # Set ALLOWED_ORIGINS in your Render / Vercel environment variables
    # to override the defaults baked into main.py
    allowed_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,"
        "https://gym-sense-orcin.vercel.app,https://gymsense-j.onrender.com"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()