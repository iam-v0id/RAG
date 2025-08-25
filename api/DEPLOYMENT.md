# RAG API Deployment Guide

This guide helps you deploy the RAG API to Vercel and troubleshoot common issues.

## Environment Variables

You need to set the following environment variables in your Vercel project:

### Required Variables

1. **PINECONE_API_KEY** - Your Pinecone API key

   - Get this from your Pinecone console at https://app.pinecone.io/
   - This is required for vector database operations

2. **PINECONE_INDEX_NAME** - Name of your Pinecone index (default: "company-docs")

   - The index will be created automatically if it doesn't exist

3. **PINECONE_CLOUD** - Cloud provider (default: "aws")

   - Options: "aws", "gcp", "azure"

4. **PINECONE_REGION** - Region for your Pinecone index (default: "us-east-1")
   - Choose a region close to your users

### Optional Variables

5. **OPENAI_API_KEY** - OpenAI API key for text generation

   - Required if you want to use GPT models for answer generation

6. **GROQ_API_KEY** - Groq API key (alternative to OpenAI)

   - Faster and often cheaper than OpenAI

7. **HUGGINGFACE_API_KEY** - Hugging Face API key

   - Used for embeddings (recommended for serverless environments)

8. **DOCS_NAMESPACE** - Namespace for document registry (default: "docs_registry")

   - Used by the `/api/docs` endpoint

9. **RAG_INDEX_NAMESPACE** - Namespace for RAG index
   - Leave empty to use default namespace

## Setting Environment Variables in Vercel

1. Go to your Vercel dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add each variable with the appropriate value
5. Redeploy your project

## Testing Your Deployment

After setting up environment variables, you can test your deployment:

1. **Test the docs endpoint**: `https://your-domain.vercel.app/api/docs`
2. **Test the search endpoint**: `https://your-domain.vercel.app/api/search`
3. **Test the upload endpoint**: `https://your-domain.vercel.app/api/upload`

## Common Issues and Solutions

### 500 Error on `/api/docs`

**Cause**: Missing environment variables or dependencies

**Solution**:

1. Check that `PINECONE_API_KEY` is set in Vercel
2. Verify all required environment variables are configured
3. Check Vercel logs for specific error messages

### Import Errors

**Cause**: Missing Python dependencies

**Solution**:

1. Ensure `requirements.txt` includes all necessary packages
2. Redeploy after updating requirements
3. Check that package versions are compatible

### Pinecone Connection Issues

**Cause**: Invalid API key or network issues

**Solution**:

1. Verify your Pinecone API key is correct
2. Check that your Pinecone account is active
3. Ensure the region matches your Pinecone index

### Build Failures

**Cause**: Large dependencies causing timeout or memory issues

**Solution**:

1. The current setup uses lightweight dependencies
2. Uses Hugging Face API for embeddings instead of local models
3. If you still have issues, consider using a different deployment platform

## Architecture Notes

This deployment is optimized for Vercel's serverless environment:

- **Lightweight Dependencies**: Removed heavy ML libraries like `sentence-transformers`
- **API-based Embeddings**: Uses Hugging Face API instead of local models
- **Minimal Bundle Size**: Only essential packages included
- **Better Error Handling**: More descriptive error messages

## Local Testing

You can test locally before deploying:

1. Create a `.env` file in the `api/` directory
2. Add your environment variables
3. Run the test script: `python test_env.py`
4. Start the local server: `python dev_server.py`

## Monitoring

Check Vercel logs for errors:

1. Go to your Vercel dashboard
2. Select your project
3. Go to Functions → View Function Logs
4. Look for error messages related to your API endpoints

## Support

If you're still having issues:

1. Run the test script to diagnose problems
2. Check Vercel function logs for detailed error messages
3. Verify all environment variables are set correctly
4. Ensure your Pinecone account and API key are valid
5. Consider the lightweight architecture if you need to reduce bundle size
