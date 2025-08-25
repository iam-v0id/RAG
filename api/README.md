# RAG API - Vercel Serverless Functions

This directory contains the serverless functions for the RAG (Retrieval-Augmented Generation) API, structured for Vercel deployment.

## Structure

- `search.py` - Vercel serverless function for search endpoint (`/api/search`)
- `upload.py` - Vercel serverless function for upload endpoint (`/api/upload`)
- `docs.py` - Vercel serverless function for document listing (`/api/docs`)
- `core/` - Core logic shared between functions
  - `core/search.py` - Main search logic and handler
  - `core/upload.py` - Main upload logic and handler
- `requirements.txt` - Python dependencies

## API Endpoints

### `/api/search`

- **GET**: Health check and service info
- **POST**: Search documents and generate answers using RAG
  - Body: `{"query": "search term", "filters": {...}, "topK": 12, "returnK": 6}`

### `/api/upload`

- **GET**: Health check
- **POST**: Upload and process documents
  - Body: `{"id": "doc_id", "title": "...", "department": "...", "category": "...", "year": 2024, "content": "..."}`

### `/api/docs`

- **GET**: List all uploaded documents
- Returns: `{"items": [{"id": "...", "title": "...", "department": "...", "category": "...", "year": "...", "chunk_count": 0, "uploaded_at": "...", "processing_status": "completed"}]}`

## Environment Variables

Required environment variables:

- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_INDEX_NAME` - Pinecone index name (default: "company-docs")
- `HUGGINGFACE_API_KEY` - Hugging Face API key for embeddings

Optional:

- `PINECONE_CLOUD` - Pinecone cloud provider (default: "aws")
- `PINECONE_REGION` - Pinecone region (default: "us-east-1")
- `RAG_INDEX_NAMESPACE` - Namespace for RAG documents
- `DOCS_NAMESPACE` - Namespace for document registry (default: "docs_registry")
- `HF_EMBED_MODEL` - Embedding model (default: "BAAI/bge-small-en-v1.5")
- `OPENAI_API_KEY` - OpenAI API key for generation
- `GROQ_API_KEY` - Groq API key for generation (preferred over OpenAI)

## Features

- **Vector Search**: Uses Pinecone for semantic document retrieval
- **Embeddings**: BAAI/bge-small-en-v1.5 model via Hugging Face API
- **Document Processing**: Automatic chunking and metadata extraction
- **LLM Integration**: Support for OpenAI and Groq APIs
- **CORS Support**: Full CORS headers for frontend integration
