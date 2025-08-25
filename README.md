# RAG Play - Retrieval-Augmented Generation System

A modern RAG (Retrieval-Augmented Generation) system built with React frontend and Python backend, deployed on Vercel.

## Ideal Flow

The system follows this exact flow:

1. **Document Upload** → Upload documents with metadata
2. **BAAI Embeddings** → Generate embeddings using Hugging Face API (BAAI/bge-small-en-v1.5)
3. **Pinecone Storage** → Store vectors in Pinecone for semantic search
4. **RAG Search** → Search with filters and generate answers using LLM

## Features

- **Document Upload**: Upload PDF, TXT, and DOCX files with metadata
- **Semantic Search**: Advanced vector search using Pinecone and BAAI embeddings
- **AI-Powered Answers**: Generate contextual answers using OpenAI or Groq
- **Modern UI**: Clean React interface with real-time search
- **Serverless**: Fully deployed on Vercel with Python serverless functions
- **No Fallbacks**: Clear error messages with proper dependency management

## Tech Stack

### Frontend

- React 19 with Vite
- Modern CSS with responsive design
- PDF.js for document processing

### Backend

- Python serverless functions (Vercel)
- Pinecone vector database
- Hugging Face Inference API for BAAI embeddings
- OpenAI/Groq for text generation

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd RAG-Play
   ```

2. **Set up environment variables**
   Create a `.env` file in the root directory:

   ```
   # Required for all operations
   PINECONE_API_KEY=your_pinecone_key
   HUGGINGFACE_API_KEY=your_hf_key

   # Required for search/answer generation
   OPENAI_API_KEY=your_openai_key
   # OR
   GROQ_API_KEY=your_groq_key
   ```

3. **Install dependencies**

   ```bash
   npm install
   ```

4. **Run development server**

   ```bash
   npm run dev
   ```

5. **Deploy to Vercel**

   ```bash
   vercel --prod
   ```

## API Endpoints

- `/api/search` - Document search and answer generation
- `/api/upload` - Document upload and processing
- `/api/docs` - List all uploaded documents

## Required Environment Variables

**Required for all operations:**

- `PINECONE_API_KEY` - Pinecone API key
- `HUGGINGFACE_API_KEY` - Hugging Face API key for BAAI embeddings

**Required for search/answer generation:**

- `OPENAI_API_KEY` or `GROQ_API_KEY` - LLM API key

See `api/README.md` for detailed environment variable configuration.

## Error Handling

The system provides clear error messages for:

- Missing environment variables
- Failed API connections
- Invalid document formats
- Network timeouts

No fallbacks are provided - all dependencies must be properly configured.

## License

MIT License
