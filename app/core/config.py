import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Video Link Detector API"
    API_V1_STR: str = "/api/v1"
    
    # Playwright Settings
    DEFAULT_TIMEOUT_MS: int = 15000  # 15 seconds
    DEFAULT_WAIT_TIME_MS: int = 3000   # 3 seconds after page loads
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Default User Agent
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    class Config:
        case_sensitive = True

settings = Settings()
