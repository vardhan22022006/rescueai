from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./rescueai.db"
    environment: str = "development"
    openweather_api_key: Optional[str] = None

    # Translation backend for non-English reports.
    # "argos"  (default) — argos-translate, fully offline, no API key required.
    # "google"           — deep-translator GoogleTranslator, free tier, no key required.
    translate_backend: str = "argos"

    class Config:
        env_file = ".env"


settings = Settings()
