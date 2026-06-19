import os
from pathlib import Path 

BASE_DIR = Path(__file__).resolve().parent.parent 
STORAGE_ROOT = Path("/home/RYVEN/workspace/mirrored_repos").resolve()
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "local_development_server")

MAX_WORKERS = os.cpu_count() or 4
MAX_FILE_SIZE_BYTES = 1_000_000 #1MB 


# Qdrant config
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "codebase_chunks"
EMBEDDING_DIMENSION = 1536
