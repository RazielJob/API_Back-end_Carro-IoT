import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str = "3306"
    DB_NAME: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 5500
    # SECRET_API_KEY removed — API key authentication disabled for this demo

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
