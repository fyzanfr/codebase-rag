# Codebase RAG Pipeline (with Incremental Synchronization)

A high-performance, event-driven Retrieval-Augmented Generation (RAG) pipeline designed to index, parse, and query complex codebases. Unlike naive character-splitting RAG setups, this system utilizes Abstract Syntax Tree (AST) structural chunking and handles dynamic repository changes via live GitHub webhooks to perform real-time vector synchronization.

## Key Features

* **AST-Based Code Chunking:** Breaks down source code by logical blocks (functions, classes, symbols) rather than static character limits to maintain strict semantic context.
* **Hybrid Vector Indexing:** Employs a dense vector layout using `FastEmbed` (`BAAI/bge-small-en-v1.5`) mapped directly alongside an optimized sparse vector configuration inside Qdrant Cloud.
* **Event-Driven Sync (Webhook Worker):** Processes real-time incoming GitHub push payloads through an asynchronous FastAPI pipeline.
* **Surgical Database Updates:** Parses `git diff` boundaries to dynamically isolate modified or deleted files, executing precise metadata vector purges and upserts without rebuilding the entire index.
* **Decoupled LLM Layer:** Hot-swappable LLM factory architecture integrating high-throughput Groq processing nodes for lightning-fast RAG generation.

## System Architecture

* **Backend Framework:** FastAPI (Async Task Runner Engine)
* **Vector Engine:** Qdrant Cloud (Managed Cluster Schema)
* **Embeddings Layer:** FastEmbed (Dense Vector Transformers)
* **Tunnel Integration:** Ngrok Secure Payload Relay Agent

## ⚙️ Quick Start

### 1. Environment Configuration
Create a `.env` file in the root folder:
```env
QDRANT_HOST="your-qdrant-cloud-cluster-url"
QDRANT_API_KEY="your-qdrant-secret-key"
COLLECTION_NAME="codebase_chunks"
EMBEDDING_DIMENSION=384
GITHUB_WEBHOOK_SECRET="your-configured-payload-secret"
