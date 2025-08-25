# RAG Play - Retrieval-Augmented Generation System

A modern RAG (Retrieval-Augmented Generation) system built with React frontend and Python backend, deployed on Vercel.

## Features

- **Document Upload**: Upload PDF, TXT, and DOCX files with metadata
- **Semantic Search**: Advanced vector search using Pinecone and BAAI embeddings
- **AI-Powered Answers**: Generate contextual answers using OpenAI or Groq
- **Modern UI**: Clean React interface with real-time search
- **Serverless**: Fully deployed on Vercel with Python serverless functions

## Tech Stack

### Frontend

- React 19 with Vite
- Modern CSS with responsive design
- PDF.js for document processing

### Backend

- Python serverless functions (Vercel)
- Pinecone vector database
- Hugging Face Inference API for embeddings
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
   PINECONE_API_KEY=your_pinecone_key
   HUGGINGFACE_API_KEY=your_hf_key
   OPENAI_API_KEY=your_openai_key
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

## Environment Variables

See `api/README.md` for detailed environment variable configuration.

## License

MIT License
