from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "EKAM Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "ekam"
    POSTGRES_PORT: str = "5432"
    
    FIREBASE_CREDENTIALS_PATH:str = "ekam-aaa95-firebase-adminsdk-fbsvc-7f4e06ba47.json"
    MOCK_AUTH: bool = False
    
    GROQ_API_KEY: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""
    SENDER_NAME: str = "EKAM"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
