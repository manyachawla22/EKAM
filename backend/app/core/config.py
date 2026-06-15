from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str 
    VERSION: str 
    API_V1_STR: str 
    
    POSTGRES_SERVER: str 
    POSTGRES_USER: str 
    POSTGRES_PASSWORD: str 
    POSTGRES_DB: str 
    POSTGRES_PORT: str 
    DATABASE_URL: str
    
    FIREBASE_CREDENTIALS_PATH: str
    MOCK_AUTH: bool
    DEBUG: bool
     
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ----- Task-3 Event-OS agent LLM seam (llm_client.py) -----
    # Which provider answers the Task-3 blueprint/critic calls. "groq" (default)
    # uses GROQ_* above; "gemini" uses GEMINI_API_KEY; "anthropic" uses
    # ANTHROPIC_API_KEY. Everything else in the app keeps calling Groq directly.
    LLM_PROVIDER: str = "gemini"  # "groq" | "gemini" | "anthropic"
    # Optional explicit model id for the seam. Empty ⇒ the provider's default
    # (gemini-2.5-flash / claude-sonnet-4-6 / GROQ_MODEL). NOTE: free-tier keys
    # created in a NEW AI Studio project have quota for gemini-2.5-flash but often
    # ZERO for gemini-2.0-flash — use 2.5-flash.
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""
    # Optional pool of Gemini keys (comma-separated) to multiply the free-tier
    # daily quota (20 req/day/key). On a 429 RESOURCE_EXHAUSTED / 503 the client
    # rotates to the next key before falling back to Groq. Keys MUST come from
    # SEPARATE Google Cloud projects — keys in the same project share one quota.
    GEMINI_API_KEYS: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ----- JWT Configuration -----
    JWT_SECRET_KEY: str 
    JWT_ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    REFRESH_TOKEN_EXPIRE_DAYS: int 

    # ----- Email Configuration (placeholders for Phase 5) -----
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str

    EMAIL_FROM: str

    # ----- Frontend URL for magic links -----
    FRONTEND_URL: str = "http://localhost:3000"

    # ----- Captcha (public registration page, Task 6) -----
    # Cloudflare Turnstile secret. When empty, captcha verification is DISABLED
    # (dev/demo without keys still works); set it in prod to enforce.
    TURNSTILE_SECRET_KEY: str = ""
    TURNSTILE_VERIFY_URL: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    # ----- File storage / submissions -----
    # Local directory (relative to the backend working dir) where uploaded
    # submission files (PDFs) are stored.
    UPLOAD_DIR: str = "uploads"
    # Public base URL used to build absolute links to uploaded files. Set this
    # to your ngrok URL (e.g. https://abc123.ngrok-free.app) so remote judges
    # can open submissions. When empty, links fall back to the request host.
    PUBLIC_BASE_URL: str = ""

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings
