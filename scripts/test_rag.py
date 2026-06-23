import asyncio
import os
import sys
from pathlib import Path 

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR)) 

from config.settings import settings
from retrieval.search import HybridRetriever
from generation.llm import LLMFactory 

def execute_chat_turn(user_input: str, system_ctx: str, provider: str, token_key: str, model: str = None) -> str:

    llm_model = LLMFactory.get_provider(
            provider_name = provider,
            api_key = token_key,
            model_name = model
            )

    reply = llm_model.generate(
            system_prompt = system_ctx,
            user_prompt = user_input,
            temperature = 0.1
            )

    return reply


async def run_rag(query_text: str, provider: str, api_key: str, model: str = None):
    if not api_key or "YOUR_ACTUAL" in api_key:
        print(f"Error: Missing or invalid API key for provider '{provider}'. Check your setup.")
        return

    print(f"1. Querying Qdrant via Hybrid Retreiver (Semantic + Sparse Splade)...")
    retriever = HybridRetriever()
    search_hits = await retriever.query(query_text, top_k=4)

    if not search_hits:
        print("Zero code chunks matched this query in the vector database.")
        return

    context_segments = []
    for hit in search_hits:
        segment = f"--- File: {hit['path']} ({hit['symbol']}) ---\n{hit['body']}"
        context_segments.append(segment)

    codebase_context = "\n\n".join(context_segments)

    system_prompt = f"""You are an elite AI pair-programmer. Use the following codebase context snippets to accurately resolve the user request.

Codebase Context:
    {codebase_context}"""

    print(f"2. Forwarding unified context blocks to {provider.upper()} engine...")
    try:
        # Utilizing your wrapper execution method 
        response = execute_chat_turn(
                user_input=query_text,
                system_ctx=system_prompt,
                provider=provider,
                token_key=api_key,
                model=model
                )


        print("\n" + "="*40 + " RAG ANSWER " + "="*40)
        print(response)
        print("="*92 + "\n")

    except Exception as e:
        print(f"Generation Stage Crashed: {e}")



if __name__ == "__main__":
    # The testing question matching the karpathy/micrograd repository we bootstrapped
    TEST_QUERY = "How is the backward pass handled inside the Value class?"
    
    # Target configurations
    PROVIDER_SELECTION = "groq"
    MODEL_SELECTION = "llama-3.3-70b-versatile"
    
    # Automatically extracts from your environment shell or falls back to a string variable
    TARGET_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_ACTUAL_GROQ_API_KEY")
    
    # Fire up the loop
    asyncio.run(run_rag(
        query_text=TEST_QUERY,
        provider=PROVIDER_SELECTION,
        api_key=TARGET_API_KEY,
        model=MODEL_SELECTION
    ))
