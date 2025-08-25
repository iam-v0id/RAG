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
            if not os.getenv("PINECONE_API_KEY"):
                self._write_json(
                    500, {"error": "Missing PINECONE_API_KEY environment variable"}
                )
                return

            try:
                init_clients()
            except Exception as e:
                self._write_json(
                    500, {"error": f"Failed to initialize clients: {str(e)}"}
                )
                return

            ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
            v = [0.0] * 384

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
            for m in res.matches or []:
                md = m.metadata or {}
                doc_id = (md.get("doc_id") or md.get("id") or m.id).replace("doc::", "")
                chunk_count = md.get("chunk_count", 0)
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
                        "processing_status": "completed",
                    }
                )

            self._write_json(200, {"items": items})

        except Exception as e:
            print(f"Error in docs endpoint GET: {e}")
            self._write_json(500, {"error": f"Internal server error: {str(e)}"})

    def do_DELETE(self):
        try:
            if not os.getenv("PINECONE_API_KEY"):
                self._write_json(
                    500, {"error": "Missing PINECONE_API_KEY environment variable"}
                )
                return

            try:
                init_clients()
            except Exception as e:
                self._write_json(
                    500, {"error": f"Failed to initialize clients: {str(e)}"}
                )
                return

            if core is None or core.search._pinecone_index is None:
                self._write_json(500, {"error": "Pinecone index not initialized"})
                return

            # Read doc id from query string
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            doc_id = (qs.get("id", [""])[0] or "").strip()

            if not doc_id:
                self._write_json(
                    400, {"error": "Missing required 'id' query parameter"}
                )
                return

            registry_namespace = os.getenv("DOCS_NAMESPACE", "docs_registry")

            # 1) Delete the registry entry
            core.search._pinecone_index.delete(
                ids=[f"doc::{doc_id}"],
                namespace=registry_namespace,
            )

            # 2) Delete all chunks for the document in the RAG namespace, by metadata filter
            rag_ns = RAG_INDEX_NAMESPACE
            delete_kwargs = {"namespace": rag_ns} if rag_ns else {}
            core.search._pinecone_index.delete(
                filter={"doc_id": {"$eq": doc_id}},
                **delete_kwargs,
            )

            self._write_json(200, {"ok": True, "deleted": doc_id})

        except Exception as e:
            print(f"Error in docs endpoint DELETE: {e}")
            self._write_json(500, {"error": f"Failed to delete document: {str(e)}"})
