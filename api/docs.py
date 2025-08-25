# Vercel serverless function for docs endpoint
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Ensure this directory is on sys.path so we can import core.search
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from core.search import init_clients
    import core.search
except ImportError as e:
    print(f"Import error: {e}")
    core = None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            # Check if required environment variables are set
            if not os.getenv("PINECONE_API_KEY"):
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                error_response = {
                    "error": "Missing PINECONE_API_KEY environment variable"
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Initialize clients
            try:
                init_clients()
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                error_response = {"error": f"Failed to initialize clients: {str(e)}"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Use registry namespace
            ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
            # Query with a neutral vector - no need for real embeddings to list documents
            v = [0.0] * 384

            res = core.search._pinecone_index.query(
                vector=v, top_k=500, include_metadata=True, namespace=ns
            )

            items = []
            for i, m in enumerate(res.matches or []):
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

            response = {"items": items}

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"Error in docs endpoint: {e}")
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            error_response = {"error": f"Internal server error: {str(e)}"}
            self.wfile.write(json.dumps(error_response).encode())
