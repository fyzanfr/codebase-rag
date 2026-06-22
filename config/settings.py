import os
from pathlib import Path 
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    BASE_DIR: Path = Path(__file__).resolve().parent.parent 
    STORAGE_ROOT: Path = Path("/home/RYVEN/workspace/mirrored_repos").resolve()

    GITHUB_WEBHOOK_SECRET: str = "local_development_server"

    MAX_WORKERS: int = os.cpu_count() or 4
    MAX_FILE_SIZE_BYTES: int = 1_000_000 #1MB 


# Qdrant config
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None 
    COLLECTION_NAME: str = "codebase_chunks"
    EMBEDDING_DIMENSION: int = 384

    model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )


settings = Settings()
settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

