# Vercel serverless function for docs endpoint
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from typing import Optional
import pathlib
from urllib.parse import urlparse, parse_qs
import datetime

# Load .env from repo root (or nearest) for local/dev runs
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore

    loaded = False
    try:
        found = find_dotenv(usecwd=False)
        if found:
            load_dotenv(found)
            loaded = True
    except Exception:
        pass

    if not loaded:
        api_dir = pathlib.Path(__file__).resolve().parent
        rag_dir = api_dir.parent
        candidate = rag_dir / ".env"
        if candidate.exists():
            load_dotenv(candidate.as_posix())
            loaded = True
except Exception:
    pass

# Ensure this directory is on sys.path so we can import core.search
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from core.search import init_clients, _pinecone_index
except ImportError as e:
    print(f"Import error: {e}")
    _pinecone_index = None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            # Check for test parameter
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            # If ?test=true, return a simple connection test
            if query_params.get("test") == ["true"]:
                return self._handle_test_request()

            # Diagnostic: check env vars first and short-circuit with a clear response
            required_vars = [
                "PINECONE_API_KEY",
                "PINECONE_INDEX_NAME",
                "PINECONE_CLOUD",
                "PINECONE_REGION",
            ]
            missing = [v for v in required_vars if not os.getenv(v)]

            # If any required envs are missing, return a 200 diagnostic so it is visible in Vercel quickly
            if missing:
                mask = lambda v: (
                    (v[:6] + "...") if (v and len(v) > 6) else v
                )  # noqa: E731
                payload = {
                    "ok": False,
                    "reason": "missing_env",
                    "missing": missing,
                    "env": {
                        "PINECONE_API_KEY": mask(os.getenv("PINECONE_API_KEY")),
                        "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME"),
                        "PINECONE_CLOUD": os.getenv("PINECONE_CLOUD"),
                        "PINECONE_REGION": os.getenv("PINECONE_REGION"),
                        "DOCS_NAMESPACE": os.getenv("DOCS_NAMESPACE"),
                    },
                }
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
                return

            # Initialize clients
            try:
                init_clients()
                # Check if _pinecone_index was actually initialized
                if _pinecone_index is None:
                    raise RuntimeError(
                        "Pinecone index initialization failed - index is None"
                    )
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                error_response = {
                    "error": f"Failed to initialize clients: {str(e)}",
                    "message": "Check your Pinecone configuration and API key. The index may not exist yet.",
                    "details": {
                        "index_name": os.getenv("PINECONE_INDEX_NAME", "company-docs"),
                        "region": os.getenv("PINECONE_REGION", "us-east-1"),
                        "cloud": os.getenv("PINECONE_CLOUD", "aws"),
                        "pinecone_index_initialized": _pinecone_index is not None,
                    },
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Use registry namespace
            ns = os.getenv("DOCS_NAMESPACE", "docs_registry")

            # Create a simple query vector (all zeros) to list documents
            # This is a lightweight approach that doesn't require embedding models
            v = [0.0] * 384

            try:
                res = _pinecone_index.query(
                    vector=v, top_k=500, include_metadata=True, namespace=ns
                )
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                error_response = {
                    "error": f"Failed to query Pinecone: {str(e)}",
                    "message": "Check your Pinecone index configuration. The index may be empty or the namespace may not exist.",
                    "details": {
                        "index_name": os.getenv("PINECONE_INDEX_NAME", "company-docs"),
                        "namespace": ns,
                        "error_type": type(e).__name__,
                    },
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

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
                        "processing_status": "completed",
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
            import traceback

            traceback.print_exc()

            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            error_response = {
                "error": f"Internal server error: {str(e)}",
                "message": "An unexpected error occurred. Check the server logs for details.",
                "type": type(e).__name__,
                "details": str(e),
            }
            self.wfile.write(json.dumps(error_response).encode())

    def _handle_test_request(self):
        """Handle test requests to verify Pinecone connection"""
        try:
            # Test 1: Check environment variables
            env_status = {
                "PINECONE_API_KEY": bool(os.getenv("PINECONE_API_KEY")),
                "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME", "company-docs"),
                "PINECONE_CLOUD": os.getenv("PINECONE_CLOUD", "aws"),
                "PINECONE_REGION": os.getenv("PINECONE_REGION", "us-east-1"),
            }

            # Test 2: Try to initialize Pinecone client
            pinecone_status = {
                "client_initialized": False,
                "index_exists": False,
                "error": None,
            }
            try:
                from pinecone import Pinecone

                pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
                pinecone_status["client_initialized"] = True

                # Test 3: List indexes
                indexes = pc.list_indexes()
                index_names = [idx.name for idx in indexes.indexes]
                pinecone_status["available_indexes"] = index_names
                pinecone_status["index_exists"] = (
                    os.getenv("PINECONE_INDEX_NAME", "company-docs") in index_names
                )

            except Exception as e:
                pinecone_status["error"] = str(e)

            payload = {
                "ok": True,
                "test": True,
                "timestamp": str(datetime.datetime.now()),
                "environment": env_status,
                "pinecone": pinecone_status,
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        except Exception as e:
            error_response = {
                "ok": False,
                "test": True,
                "error": str(e),
                "timestamp": str(datetime.datetime.now()),
            }
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
