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
    
    FIREBASE_CREDENTIALS_PATH:str = "ekam-aaa95-firebase-adminsdk-fbsvc-7f4e06ba47.json"
    MOCK_AUTH: bool = False
    GROQ_API_KEY: str = ""
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
