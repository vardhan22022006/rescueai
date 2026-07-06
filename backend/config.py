from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./rescueai.db"
    environment: str = "development"
    openweather_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()
