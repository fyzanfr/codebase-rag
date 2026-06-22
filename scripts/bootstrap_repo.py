import asyncio
import os
import shutil
import sys
from git import Repo
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index.dense import DenseIndex
from index.sparse import SparseIndex
from ingestion.parser import ASTChunker
from ingestion import queries
from config import settings

TMP_DIR = Path("./tmp/bootstrap_sandbox")

async def bootstrap_repository(repo_url: str, repo_name: str):
    indexer = DenseIndex()
    sparse_indexer = SparseIndex()
    chunker = ASTChunker(
            languages=queries.LANG_CAPSULES,
            queries=queries.CHUNK_QUERIES,
            ext_map=queries.EXTENSION_MAP
            ) 
    
    if TMP_DIR.exists():
        print(f" Cleaning up old workspace...")
        shutil.rmtree(TMP_DIR)
        
    print(f"Cloning repository: {repo_url}...")
    Repo.clone_from(repo_url, TMP_DIR, depth=1)
    
    all_new_chunks = []
    
    for fpath in TMP_DIR.rglob("*"):
        if fpath.is_file() and fpath.suffix.lower() in chunker.ext_map:
            rel_path_str = str(fpath.relative_to(TMP_DIR))
            try:
                content = fpath.read_bytes()
                file_chunks = chunker.chunk_file(repo_name, rel_path_str, content)
                all_new_chunks.extend(file_chunks)
            except Exception as e:
                print(f"Failed extraction on file {rel_path_str}: {e}")

    print(f"Successfully generated {len(all_new_chunks)} code chunks.")
    
    if all_new_chunks:
        print("Computing dense vectors and syncing to Qdrant...")
        
        for chunk in all_new_chunks:
            body_text = f"File: {chunk.path}\nSymbol:{chunk.symbol}\nCode:{chunk.body}"
            chunk.sparse_vector = sparse_indexer.generate_sparse_vector(body_text)
        indexer.index_chunks(all_new_chunks)
        print("Complete!")

if __name__ == "__main__":
    TARGET_URL = "https://github.com/karpathy/micrograd.git"
    TARGET_NAME = "micrograd"
    asyncio.run(bootstrap_repository(TARGET_URL, TARGET_NAME))
