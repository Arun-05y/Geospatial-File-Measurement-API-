import os
from pathlib import Path
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Upload and storage settings
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    
    # Supported file extensions
    ALLOWED_EXTENSIONS: set[str] = {".zip", ".kml"}
    
    # Default Coordinate Reference System when unspecified
    DEFAULT_CRS: str = "EPSG:4326"

settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
