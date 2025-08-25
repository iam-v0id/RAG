from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from flask import Flask, Response, request

# Ensure this directory is on sys.path so we can import core modules
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from core.search import handler as vercel_handler  # type: ignore
from core.upload import handler as upload_handler  # type: ignore


app = Flask(__name__)


def _to_flask_response(api_resp: Dict[str, Any]) -> Response:
    status = int(api_resp.get("statusCode", 200))
    headers = api_resp.get("headers", {}) or {}
    body = api_resp.get("body", "") or ""
    if not isinstance(body, (bytes, bytearray)):
        body = body.encode("utf-8")
    return Response(response=body, status=status, headers=headers)


@app.route("/api/search", methods=["GET", "POST", "OPTIONS"])
def api_search() -> Response:
    req_dict = {
        "method": request.method,
        "headers": {k: v for k, v in request.headers.items()},
        "query": request.args.to_dict(flat=True),
        "body": request.get_data(),
    }
    api_resp = vercel_handler(req_dict)
    return _to_flask_response(api_resp)


@app.route("/api/docs", methods=["GET", "OPTIONS"])
def api_docs() -> Response:
    # Import the module so we can see updated globals after init
    import core.search as core_search  # type: ignore

    try:
        core_search.init_clients()
    except Exception as e:
        return _to_flask_response(
            {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": f"init_clients failed: {e}"}),
            }
        )

    # Use registry namespace
    ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
    # Query with a neutral vector
    v = [0.0] * 384
    # If embedding model available, create a real vector
    try:
        v = core_search.embed_texts(["documents"])[0]
    except Exception:
        pass

    index = getattr(core_search, "_pinecone_index", None)
    if index is None:
        return _to_flask_response(
            {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Pinecone index is not initialized"}),
            }
        )

    res = index.query(vector=v, top_k=500, include_metadata=True, namespace=ns)
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
    return _to_flask_response(
        {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"items": items}),
        }
    )


@app.route("/api/upload", methods=["GET", "POST", "OPTIONS"])
def api_upload() -> Response:
    req_dict = {
        "method": request.method,
        "headers": {k: v for k, v in request.headers.items()},
        "query": request.args.to_dict(flat=True),
        "body": request.get_data(),
    }
    api_resp = upload_handler(req_dict)
    return _to_flask_response(api_resp)


@app.route("/")
def root() -> str:
    return "Dev API running. Try POST /api/search"


if __name__ == "__main__":
    # Run on port 3000 to match Vite proxy target
    app.run(host="127.0.0.1", port=3000, debug=True)
