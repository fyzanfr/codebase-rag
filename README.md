# Codebase RAG

AST-based code chunking, hybrid vector search (dense + sparse), and LLM-powered Q&A over your codebase.

## Features

- **AST chunking** — parses code by functions, classes, and symbols (not line windows)
- **Hybrid search** — combines dense embeddings (`BAAI/bge-small-en-v1.5`) with sparse vectors (`Splade_PP_en_v1`) via Qdrant RRF fusion
- **LLM agnostic** — swap between Groq, OpenAI, Gemini, or Anthropic via `LLMFactory`
- **Incremental sync** — GitHub webhook receiver for real-time re-indexing

## Quick Start

### 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
QDRANT_HOST=http://localhost:6333
QDRANT_API_KEY=
COLLECTION_NAME=codebase_chunks
```

### 2. Ingest a repository

```bash
python cli.py index -r my-repo -p /path/to/my-repo
```

### 3. Ask questions

```bash
export GROQ_API_KEY="your-key"
python cli.py query "How does authentication work?"
```

## Commands

| Command | Description |
|---------|-------------|
| `index -r <name> -p <path>` | Scan a local repo, AST chunk, and seed Qdrant |
| `query <question>` | Retrieve relevant chunks and answer via LLM |

Optional flags for `query`: `--top-k`, `--provider`, `--model`, `--api-key`.

## Architecture

```
Local repo → ASTChunker → CodeChunks → Embed (dense + sparse) → Qdrant Cloud
User query → HybridRetriever (RRF fusion) → context → LLM → answer
```

## LLM Providers

| Provider | Default model | Env var |
|----------|---------------|---------|
| groq | llama-3.3-70b-versatile | `GROQ_API_KEY` |
| openai | gpt-4o-mini | `OPENAI_API_KEY` |
| gemini | gemini-1.5-flash | `GEMINI_API_KEY` |
| anthropic | claude-3-5-sonnet-latest | `ANTHROPIC_API_KEY` |

## API

Run `uvicorn api.main:app` for the webhook receiver (GitHub push events → auto re-index).
