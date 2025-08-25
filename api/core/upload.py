from __future__ import annotations

import json
import time
import os
from typing import Any, Dict

from core.search import (
    init_clients,
    simple_chunks,
    make_chunk_records,
    embed_and_upsert,
)  # reuse from core.search

try:
    from pinecone import Pinecone, ServerlessSpec
except Exception:  # pragma: no cover
    Pinecone = None


def _json(headers: Dict[str, str] | None, status: int, body: Dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            **(headers or {}),
        },
        "body": json.dumps(body),
    }


def handler(request):
    try:
        method = (request.get("method") or "GET").upper()

        if method == "OPTIONS":
            return {
                "statusCode": 204,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
                "body": "",
            }

        if method == "GET":
            return _json(None, 200, {"ok": True})

        if method != "POST":
            return _json(None, 405, {"error": "Method not allowed"})

        init_clients()
        raw = request.get("body") or b"{}"
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        data = json.loads(raw.decode("utf-8")) if raw else {}

        doc_id = (data.get("id") or f"doc_{int(time.time()*1000)}").strip()
        title = (data.get("title") or "").strip()
        department = (data.get("department") or "").strip()
        category = (data.get("category") or "").strip()
        year = int(data.get("year") or 0)
        content = (data.get("content") or "").strip()
        chunk_count = int(data.get("chunk_count") or 0)

        if not title or not department or not category or not year or not content:
            return _json(
                None,
                400,
                {
                    "error": "Missing required fields: title, department, category, year, content"
                },
            )

        # Create document object for chunking
        doc = {
            "id": doc_id,
            "title": title,
            "department": department,
            "category": category,
            "year": year,
            "content": content,
        }

        # Chunk and store the document using the same logic as search.py
        chunk_records = make_chunk_records(doc)
        print(f"DEBUG: Created {len(chunk_records)} chunks for document {doc_id}")

        if Pinecone is None:
            return _json(None, 500, {"error": "Pinecone SDK not installed"})
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME") or "company-docs"
        if not api_key:
            return _json(None, 500, {"error": "Missing PINECONE_API_KEY"})
        _pc = Pinecone(api_key=api_key)
        # Ensure index exists (384 dims to match MiniLM embeddings)
        try:
            existing = [idx.name for idx in _pc.list_indexes().indexes]
        except Exception:
            existing = []
        if index_name not in existing:
            cloud = os.getenv("PINECONE_CLOUD", "aws")
            region = os.getenv("PINECONE_REGION", "us-east-1")
            _pc.create_index(
                name=index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud=cloud, region=region),
            )
        index = _pc.Index(index_name)

        # Store chunks in the main RAG namespace (same as search.py uses)
        rag_namespace = os.getenv("RAG_INDEX_NAMESPACE")
        embed_and_upsert(chunk_records)
        print(
            f"DEBUG: Stored {len(chunk_records)} chunks in namespace: {rag_namespace}"
        )

        # Also store a registry entry for document listing
        registry_namespace = os.getenv("DOCS_NAMESPACE", "docs_registry")
        # Use neutral vector for registry - we don't need embeddings for document listing
        neutral_vector = [0.0] * 384
        index.upsert(
            vectors=[
                {
                    "id": f"doc::{doc_id}",
                    "values": neutral_vector,
                    "metadata": {
                        "doc_id": doc_id,
                        "title": title,
                        "department": department,
                        "category": category,
                        "year": year,
                        "chunk_count": len(chunk_records),
                        "uploaded_at": __import__("datetime")
                        .datetime.utcnow()
                        .isoformat()
                        + "Z",
                    },
                }
            ],
            namespace=registry_namespace,
        )

        return _json(None, 200, {"ok": True, "id": doc_id})

    except Exception as e:
        return _json(None, 500, {"error": str(e)})
