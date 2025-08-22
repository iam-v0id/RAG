# Vercel serverless function for docs endpoint
import json
import os
from core.search import init_clients, embed_texts, _pinecone_index

def handler(request):
    """
    Vercel serverless function handler for docs endpoint
    """
    try:
        method = (request.get("method") or "GET").upper()
        
        if method == "OPTIONS":
            return {
                "statusCode": 204,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
                "body": "",
            }
        
        if method != "GET":
            return {
                "statusCode": 405,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Method not allowed"}),
            }
        
        # Initialize clients
        init_clients()
        
        # Use registry namespace
        ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
        # Query with a neutral vector
        v = [0.0] * 384
        # If embedding model available, create a real vector
        try:
            v = embed_texts(["documents"])[0]
        except Exception:
            pass
        
        res = _pinecone_index.query(
            vector=v, top_k=500, include_metadata=True, namespace=ns
        )
        print(
            f"DEBUG: Found {len(res.matches or [])} documents in registry namespace '{ns}'"
        )
        
        items = []
        for i, m in enumerate(res.matches or []):
            print(f"DEBUG: Document {i+1}: ID={m.id}, metadata={m.metadata}")
            md = m.metadata or {}
            doc_id = (md.get("doc_id") or md.get("id") or m.id).replace("doc::", "")
            chunk_count = md.get("chunk_count", 0)

            # Ensure chunk_count is a valid number
            try:
                chunk_count = int(chunk_count) if chunk_count is not None else 0
            except (ValueError, TypeError):
                chunk_count = 0

            items.append(
                {
                    "id": doc_id,
                    "title": md.get("title", ""),
                    "department": md.get("department", ""),
                    "category": md.get("category", ""),
                    "year": md.get("year", ""),
                    "chunk_count": chunk_count,
                    "uploaded_at": md.get("uploaded_at", ""),
                    "processing_status": "completed",  # Add missing field
                }
            )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"items": items}),
        }
        
    except Exception as e:
        print(f"Error in docs handler: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error"}),
        }
