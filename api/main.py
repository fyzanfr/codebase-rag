from fastapi import FastAPI
from api.webhook import router as webhook_router

app = FastAPI(title="Codebase RAG Web Gateway")

app.include_router(webhook_router, prefix="/api", tags=["ingestion"])

@app.get("/health")
def health_check():
    return {"status": "operational"}
