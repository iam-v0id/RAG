# RAG API - Vercel Serverless Functions

This directory contains the serverless functions for the RAG (Retrieval-Augmented Generation) API, structured for Vercel deployment.

## Ideal Flow

The system follows this exact flow:

1. **Document Upload** → Upload documents with metadata
2. **BAAI Embeddings** → Generate embeddings using Hugging Face API (BAAI/bge-small-en-v1.5)
3. **Pinecone Storage** → Store vectors in Pinecone for semantic search
4. **RAG Search** → Search with filters and generate answers using LLM

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

## Required Environment Variables

**Required for all operations:**

- `PINECONE_API_KEY` - Pinecone API key
- `HUGGINGFACE_API_KEY` or `HF_TOKEN` - Hugging Face API key for BAAI embeddings

**Required for search/answer generation:**

- `OPENAI_API_KEY` or `GROQ_API_KEY` - LLM API key for answer generation

**Optional configuration:**

- `PINECONE_INDEX_NAME` - Pinecone index name (default: "company-docs")
- `PINECONE_CLOUD` - Pinecone cloud provider (default: "aws")
- `PINECONE_REGION` - Pinecone region (default: "us-east-1")
- `RAG_INDEX_NAMESPACE` - Namespace for RAG documents
- `DOCS_NAMESPACE` - Namespace for document registry (default: "docs_registry")
- `HF_EMBED_MODEL` - Embedding model (default: "BAAI/bge-small-en-v1.5")
- `GROQ_MODEL` - Groq model (default: "llama-3.3-70b-versatile")
- `GEN_LLM_MODEL` - OpenAI model (default: "gpt-4o-mini")

## Features

- **Vector Search**: Uses Pinecone for semantic document retrieval
- **BAAI Embeddings**: BAAI/bge-small-en-v1.5 model via Hugging Face API
- **Document Processing**: Automatic chunking and metadata extraction
- **LLM Integration**: Support for OpenAI and Groq APIs (no fallbacks)
- **CORS Support**: Full CORS headers for frontend integration
- **Error Handling**: Clear error messages with no fallbacks

## Error Handling

The API will return clear error messages for:

- Missing environment variables
- Failed API connections (Pinecone, Hugging Face, OpenAI/Groq)
- Invalid document formats
- Missing required fields
- Network timeouts

No fallbacks are provided - the system requires all dependencies to be properly configured.
