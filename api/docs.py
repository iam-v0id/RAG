"""
Vercel serverless function for docs endpoint
Lists all documents in the Pinecone index and supports deletion
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Ensure this directory is on sys.path so we can import core.search
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from core.search import init_clients, RAG_INDEX_NAMESPACE
    import core.search
except ImportError as e:
    core = None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _write_json(self, status: int, payload: dict):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_GET(self):
        try:
            # Check if required environment variables are set
            if not os.getenv("PINECONE_API_KEY"):
                self._write_json(
                    500, {"error": "Missing PINECONE_API_KEY environment variable"}
                )
                return

            # Initialize clients
            try:
                init_clients()
            except Exception as e:
                self._write_json(
                    500, {"error": f"Failed to initialize clients: {str(e)}"}
                )
                return

            # Use registry namespace
            ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
            # Query with a neutral vector - no need for real embeddings to list documents
            v = [0.0] * 384

            # Check if core.search module is available and _pinecone_index is initialized
            if core is None or core.search._pinecone_index is None:
                self._write_json(
                    500,
                    {
                        "error": "Pinecone index not initialized",
                        "details": {
                            "core_available": core is not None,
                            "pinecone_index_available": (
                                core.search._pinecone_index is not None
                                if core
                                else False
                            ),
                        },
                    },
                )
                return

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

            self._write_json(200, {"items": items})

        except Exception as e:
            print(f"Error in docs endpoint GET: {e}")
            self._write_json(500, {"error": f"Internal server error: {str(e)}"})

    def do_DELETE(self):
        print(f"DELETE request received: {self.path}")
        try:
            if not os.getenv("PINECONE_API_KEY"):
                print("ERROR: Missing PINECONE_API_KEY")
                self._write_json(
                    500, {"error": "Missing PINECONE_API_KEY environment variable"}
                )
                return

            try:
                print("Initializing clients...")
                init_clients()
                print("Clients initialized successfully")
            except Exception as e:
                print(f"ERROR: Failed to initialize clients: {e}")
                self._write_json(
                    500, {"error": f"Failed to initialize clients: {str(e)}"}
                )
                return

            if core is None or core.search._pinecone_index is None:
                print("ERROR: Pinecone index not initialized")
                self._write_json(500, {"error": "Pinecone index not initialized"})
                return

            # Read doc id from query string
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            doc_id = (qs.get("id", [""])[0] or "").strip()
            print(f"Extracted doc_id from query: '{doc_id}'")

            if not doc_id:
                print("ERROR: Missing doc_id parameter")
                self._write_json(
                    400, {"error": "Missing required 'id' query parameter"}
                )
                return

            registry_namespace = os.getenv("DOCS_NAMESPACE", "docs_registry")
            print(f"Using registry namespace: {registry_namespace}")

            # 1) Delete the registry entry
            try:
                print(f"Deleting registry entry: doc::{doc_id}")
                core.search._pinecone_index.delete(
                    ids=[f"doc::{doc_id}"],
                    namespace=registry_namespace,
                )
                print(
                    f"Deleted registry entry: doc::{doc_id} from {registry_namespace}"
                )
            except Exception as e:
                print(f"Warning: Failed to delete registry entry: {e}")

            # 2) Delete all chunks for the document in the RAG namespace, by metadata filter
            rag_ns = RAG_INDEX_NAMESPACE
            if rag_ns:  # Only delete chunks if namespace is specified
                try:
                    print(f"Deleting chunks for doc_id: {doc_id} from {rag_ns}")
                    core.search._pinecone_index.delete(
                        filter={"doc_id": {"$eq": doc_id}},
                        namespace=rag_ns,
                    )
                    print(f"Deleted chunks for doc_id: {doc_id} from {rag_ns}")
                except Exception as e:
                    print(f"Warning: Failed to delete chunks: {e}")
            else:
                print(f"No RAG namespace specified, skipping chunk deletion")

            print(f"Delete operation completed successfully for doc_id: {doc_id}")
            self._write_json(200, {"ok": True, "deleted": doc_id})

        except Exception as e:
            print(f"Error in docs endpoint DELETE: {e}")
            self._write_json(500, {"error": f"Failed to delete document: {str(e)}"})
