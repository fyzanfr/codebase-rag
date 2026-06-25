import logging
import os
from qdrant_client import QdrantClient, models 
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding

from config.settings import settings
from models.chunk import CodeChunk

logging.basicConfig(level=logging.INFO)

class DenseIndex:
    def __init__(self):
        self.client = QdrantClient(
                url=settings.QDRANT_HOST, 
                api_key=settings.QDRANT_API_KEY
            )
        
        logging.info("loading local FastEmbed model (BAAI/bge-small-en-v1.5)...")
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.dimension = 384
        self._ensure_collection()

    def _ensure_collection(self):
        """ Qdrant codebase collection if it isn't initialized """

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == settings.COLLECTION_NAME for c in collections)
        except Exception:
            exists = False

        if not exists:
            logging.info(f"creating new local Qdrant collection: '{settings.COLLECTION_NAME}' ({self.dimension})")
            self.client.create_collection(
                    collection_name=settings.COLLECTION_NAME,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=settings.EMBEDDING_DIMENSION,
                            distance=models.Distance.COSINE
                            )
                        },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams()
                        }
                )

        self.client.create_payload_index(
                collection_name = settings.COLLECTION_NAME,
                field_name="repo_name",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        self.client.create_payload_index(
                collection_name=settings.COLLECTION_NAME,
                field_name="path",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )


    def index_chunks(self, chunks: list[CodeChunk]):
        if not chunks:
            return

        body_to_embed = [
                f"File: {c.path}\nSymbol: {c.symbol}\nCode: {c.body}" 
                for c in chunks
            ]

        embeddings_generator = self.embedding_model.embed(body_to_embed)
        vectors = list(embeddings_generator)

        points = []
        for i, chunk in enumerate(chunks):
            chunk.dense_vector = [float(x) for x in vectors[i]]
            unique_anchor_str = f"{chunk.repo}/{chunk.path}:{chunk.symbol}:{chunk.start_line}"

            sparse_data = getattr(chunk, "sparse_vector", None) or {}

            sparse_indices = sparse_data.get("indices", []) if isinstance(sparse_data, dict) else []
            sparse_values = sparse_data.get("values", []) if isinstance(sparse_data, dict) else []


            points.append(
                    PointStruct(
                        id=hash(unique_anchor_str) & 0xFFFFFFFFFFFFFFFF,
                        vector={
                            "dense": chunk.dense_vector,
                            "sparse": models.SparseVector(
                                indices=sparse_indices,
                                values=sparse_values
                                )
                            },
                        payload={
                            "repo": chunk.repo,
                            "path": chunk.path,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "symbol": chunk.symbol,
                            "kind": chunk.kind,
                            "body": chunk.body,
                            "language": chunk.language,
                        #"summary": chunk.summary
                    }

            )   )

        logging.info(f"uploading {len(points)} points to local Qdrant...")
        self.client.upsert(
                collection_name=settings.COLLECTION_NAME,
                wait=True,
                points=points 
            )
        logging.info("local vector database syncronization complete.")




