import asyncio
import logging
from pathlib import Path 
import sys

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Prefetch, SparseVector
from fastembed.embedding import TextEmbedding

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))


from config.settings import settings
from index.dense import DenseIndex
from index.sparse import SparseIndex

logging.basicConfig(level=logging.INFO)

class HybridRetriever:
    def __init__(self):
        self.client = AsyncQdrantClient(
                url=settings.QDRANT_HOST,
                api_key=settings.QDRANT_API_KEY,
                check_compatibility=False
            )
        self.dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.sparse_engine = SparseIndex()

    async def query(self, query_text:str, top_k:int = 10) -> list[dict]:
        dense_vector = list(self.dense_model.embed([query_text]))[0].tolist()
        
        sparse_res = self.sparse_engine.generate_sparse_vector(query_text)
        sparse_vector = SparseVector(
            indices=sparse_res["indices"],
            values=sparse_res["values"]
        )

        logging.info(f"Executing hybrid search for: '{query_text}'")

        results = await self.client.query_points(
            collection_name=settings.COLLECTION_NAME,
            prefetch=[
                # Dense semantic lane
                models.Prefetch(
                    query=dense_vector,
                    using="dense", # Vector name identifier
                    limit=top_k * 2
                ),
                # Sparse keyword stream
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=top_k * 2
                )
            ],
            # Use RRF (Reciprocal Rank Fusion) to cleanly combine keyword matches with concept matches
            query=models.FusionQuery(fusion=models.Fusion.RRF), 
            limit=top_k
        )

        hits = []
        for point in results.points:
            hits.append({
                "score": point.score,
                "repo": point.payload.get("repo"),
                "path": point.payload.get("path"),
                "symbol": point.payload.get("symbol"),
                "start_line": point.payload.get("start_line"),
                "end_line": point.payload.get("end_line"),
                "body": point.payload.get("body")
            })
        return hits 


