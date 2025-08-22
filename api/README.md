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
- `OPENAI_API_KEY` or `GROQ_API_KEY` - LLM API key for generation

Optional:

- `PINECONE_CLOUD` - Pinecone cloud provider (default: "aws")
- `PINECONE_REGION` - Pinecone region (default: "us-east-1")
- `RAG_INDEX_NAMESPACE` - Namespace for RAG documents
- `DOCS_NAMESPACE` - Namespace for document registry (default: "docs_registry")
- `RAG_MODEL_NAME` - Embedding model (default: "all-MiniLM-L6-v2")
- `GEN_LLM_MODEL` - OpenAI model (default: "gpt-4o-mini")
- `GROQ_MODEL` - Groq model (default: "llama-3.3-70b-versatile")

## Deployment

This is configured for Vercel deployment with the following setup:

- Python serverless functions for API endpoints
- Static build for React frontend
- Proper routing configuration in `vercel.json`
