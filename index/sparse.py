import logging
from fastembed.sparse import SparseTextEmbedding
from config.settings import settings

class SparseIndex:
    def __init__(self):
        logging.info("loading local FastEmbed sparse model...")
        self.model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")

    def generate_sparse_vector(self, text:str) -> dict:
        embeddings = list(self.model.embed([text]))
        sparse_val = embeddings[0]

        return {
            "indices" : sparse_val.indices.tolist(),
            "values" : sparse_val.values.tolist()
            }
