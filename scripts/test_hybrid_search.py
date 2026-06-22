import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector
import asyncio
# Ensure imports work from project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from retrieval.search import HybridRetriever

async def test_hybrid_search():
    try:
        print(f"Testing hybrid search against: {settings.QDRANT_HOST}")
        
        # Initialize your custom retriever
        retriever = HybridRetriever()
        
        # Define a sample test query
        query_text = "how to implement backward pass"
        
        print(f"Executing query: '{query_text}'")
        
        # Execute the search
        results = await retriever.query(query_text, top_k=3)
        
        if not results:
            print("Search successful, but no results found in collection.")
        else:
            print(f"Successfully retrieved {len(results)} results:")
            for i, hit in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"Score: {hit.get('score')}")
                print(f"Path: {hit.get('path')}")
                print(f"Body snippet: {hit.get('body', '')[:100]}...")

    except Exception as e:
        print(f"Hybrid search test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
