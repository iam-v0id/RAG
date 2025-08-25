# api/search.py
from typing import List, Dict, Any, Optional
import json
import os
import re
import time

# Optionally load env vars in development
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# Core deps (required)
try:
    import numpy as np  # noqa: F401
except ImportError as e:
    raise RuntimeError(f"numpy is required but not available: {e}")

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise RuntimeError(f"sentence-transformers is required but not available: {e}")

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError as e:
    raise RuntimeError(f"pinecone-client is required but not available: {e}")


# ---------------- Configuration ----------------
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "company-docs")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
RAG_INDEX_NAMESPACE = os.getenv("RAG_INDEX_NAMESPACE", None)

RAG_MODEL_NAME = os.getenv("RAG_MODEL_NAME", "all-MiniLM-L6-v2")  # 384-d vectors
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "12"))  # retrieve this many candidates
RAG_RETURN_K = int(os.getenv("RAG_RETURN_K", "6"))  # model may cite up to this many
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEN_LLM_MODEL = os.getenv("GEN_LLM_MODEL", "gpt-4o-mini")

# Groq API configuration (preferred if present)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# ---------------- Globals (lazy-initialized) ----------------
_pc = None
_pinecone_index = None
_hf_model = None


# ---------------- Utilities ----------------
def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------------- Initialization ----------------
def init_clients():
    global _pc, _pinecone_index, _hf_model

    # Check required environment variables
    if not os.getenv("PINECONE_API_KEY"):
        raise RuntimeError("Missing PINECONE_API_KEY in environment.")
    if not os.getenv("HUGGINGFACE_API_KEY") and not os.getenv("HF_TOKEN"):
        raise RuntimeError("Missing HUGGINGFACE_API_KEY or HF_TOKEN in environment.")

    # Initialize Pinecone client and index
    try:
        _pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        try:
            existing = [idx.name for idx in _pc.list_indexes().indexes]
        except Exception as e:
            raise RuntimeError(f"Failed to list Pinecone indexes: {e}")

        if PINECONE_INDEX_NAME not in existing:
            _pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
            )
        _pinecone_index = _pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Pinecone: {e}")

    # Always use Hugging Face API for embeddings (BAAI model)
    _hf_model = None  # We'll use HF API instead of local model


# ---------------- Embeddings ----------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using BAAI/bge-small-en-v1.5 via Hugging Face API"""
    if not texts:
        return []

    hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("Missing HUGGINGFACE_API_KEY or HF_TOKEN for embeddings")

    model_id = os.getenv("HF_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {hf_token}",
    }

    import httpx  # type: ignore

    try:
        resp = httpx.post(
            api_url,
            headers=headers,
            json={"inputs": texts},
            timeout=60.0,
        )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Hugging Face API failed ({resp.status_code}): {resp.text}"
            )

        data = resp.json()

        # Handle different response formats from BAAI model
        if isinstance(data, list) and len(data) > 0:
            if (
                isinstance(data[0], list)
                and len(data[0]) > 0
                and isinstance(data[0][0], (int, float))
            ):
                # Token-level vectors, need to mean pool
                def mean_pool(token_vectors: List[List[float]]) -> List[float]:
                    if not token_vectors:
                        return []
                    dim = len(token_vectors[0]) if token_vectors[0] else 0
                    sums = [0.0] * dim
                    for tv in token_vectors:
                        for i in range(dim):
                            sums[i] += float(tv[i])
                    return [s / max(1, len(token_vectors)) for s in sums]

                # Single input case
                if len(texts) == 1:
                    return [mean_pool(data)]
                # Multiple inputs case
                return [mean_pool(item) for item in data]
            elif isinstance(data[0], (int, float)):
                # Direct embedding vectors
                return [data] if len(texts) == 1 else data
            else:
                raise RuntimeError(
                    f"Unexpected response format from Hugging Face API: {type(data)}"
                )
        else:
            raise RuntimeError(
                f"Empty or invalid response from Hugging Face API: {data}"
            )

    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to Hugging Face API: {e}")
    except Exception as e:
        raise RuntimeError(f"Embedding generation failed: {e}")


# ---------------- Chunking & Ingestion ----------------
def simple_chunks(text: str, size: int, overlap: int) -> List[str]:
    if not text:
        return []
    t = text.strip()
    if not t:
        return []
    chunks: List[str] = []
    start = 0
    n = len(t)
    while start < n:
        end = min(n, start + size)
        chunks.append(t[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def make_chunk_records(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    doc: { id, title, department?, category?, year?, content }
    """
    content = (doc.get("content") or "").strip()
    base_meta = {
        "doc_id": doc["id"],
        "title": doc.get("title"),
        "department": doc.get("department"),
        "category": doc.get("category"),
        "year": (
            int(doc["year"])
            if str(doc.get("year") or "").strip().isdigit()
            else doc.get("year")
        ),
    }
    chunks = simple_chunks(content, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP)
    out: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        cid = f"{doc['id']}::chunk::{i:05d}"
        meta = {
            **base_meta,
            "chunk_id": cid,
            "content": ch,
            "chunk_ix": i,
            "chunk_count": len(chunks),
        }
        out.append({"id": cid, "metadata": meta})
    return out


def embed_and_upsert(records: List[Dict[str, Any]]):
    if not records:
        return
    texts = [r["metadata"]["content"] for r in records]
    vecs = embed_texts(texts)
    payload = []
    for r, v in zip(records, vecs):
        payload.append({"id": r["id"], "values": v, "metadata": r["metadata"]})
    _pinecone_index.upsert(vectors=payload, namespace=RAG_INDEX_NAMESPACE)


def ingest_documents(docs: List[Dict[str, Any]], batch_cap: int = 200):
    batch: List[Dict[str, Any]] = []
    for d in docs:
        if not d.get("id") or not isinstance(d.get("content"), str):
            continue
        chunk_records = make_chunk_records(d)
        for rec in chunk_records:
            batch.append(rec)
            if len(batch) >= batch_cap:
                embed_and_upsert(batch)
                batch = []
    if batch:
        embed_and_upsert(batch)


# ---------------- Filters ----------------
def to_pc_filter(flt: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not flt:
        return out
    if flt.get("department"):
        out["department"] = {"$eq": flt["department"]}
    if flt.get("category"):
        out["category"] = {"$eq": flt["category"]}
    if flt.get("year"):
        try:
            out["year"] = {"$eq": int(flt["year"])}
        except Exception:
            pass
    return out


# ---------------- Retrieval ----------------
def pinecone_search(
    query: str, k: int, filter_meta: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    if _pinecone_index is None:
        return []

    qvec = embed_texts([query])[0]
    res = _pinecone_index.query(
        vector=qvec,
        top_k=k,
        include_metadata=True,
        filter=filter_meta or {},
        namespace=RAG_INDEX_NAMESPACE,
    )

    hits: List[Dict[str, Any]] = []
    for m in res.matches or []:
        md = m.metadata or {}
        hit = {
            "id": md.get("chunk_id") or m.id,
            "doc_id": md.get("doc_id"),
            "title": md.get("title"),
            "department": md.get("department"),
            "category": md.get("category"),
            "year": md.get("year"),
            "content": md.get("content"),
            "chunk_ix": md.get("chunk_ix", 0),
            "chunk_count": md.get("chunk_count", 0),
            "score": float(m.score),
        }
        hits.append(hit)
    return hits


# ---------------- Single-call LLM: rerank + generate ----------------
def build_single_call_prompt(
    query: str, hits: List[Dict[str, Any]], return_k: int
) -> str:
    """
    The model must:
      1) Select and rerank the top `return_k` candidates.
      2) Produce a grounded answer using ONLY the selected candidates.
      3) Cite sources inline as [Source N], where N is the 1-based index in the provided candidates list.
    The model must output STRICT JSON with keys: ranked_indices (list[int]), answer (string).
    """
    # Prepare compact candidate previews (avoid large tokens)
    candidates = []
    for idx, h in enumerate(hits, start=1):
        preview = (h.get("content") or "").strip().replace("\n", " ")
        preview = preview[:600]  # keep prompt small
        candidates.append(
            {
                "index": idx,
                "id": h.get("id"),
                "doc_id": h.get("doc_id"),
                "title": h.get("title"),
                "preview": preview,
            }
        )

    instructions = (
        "You are a retrieval-augmented assistant. You will rerank candidate text snippets for a user query, "
        "then write a grounded answer using ONLY the selected snippets. Follow these rules strictly:\n"
        "- First select up to RETURN_K most relevant candidates and order them from best to worst.\n"
        "- Then compose an answer based ONLY on those selected candidates.\n"
        "- Cite sources inline as [Source N], where N matches the candidate's 'index' from the list below.\n"
        "- If the sources do not contain the answer, say you do not have enough information.\n"
        "- Output STRICT JSON with exactly two keys: "
        "`ranked_indices` (an array of integers) and `answer` (a single string). Do not include any extra text.\n"
    )

    payload = {
        "query": query,
        "return_k": return_k,
        "candidates": candidates,
    }

    return instructions + "\n" + json.dumps(payload, ensure_ascii=False)


def call_llm_rerank_and_generate(prompt: str) -> Dict[str, Any]:
    """
    Calls the LLM once to both rerank and generate.
    Expects STRICT JSON: {"ranked_indices":[...], "answer":"..."}
    Raises exception on failure.
    """
    # Check for required API keys
    if not GROQ_API_KEY and not OPENAI_API_KEY:
        raise RuntimeError(
            "No LLM API key configured. Set GROQ_API_KEY or OPENAI_API_KEY"
        )

    try:
        if GROQ_API_KEY:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000,
            )
            text = (resp.choices[0].message.content or "").strip()
        else:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=GEN_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            text = (resp.choices[0].message.content or "").strip()

        # Defensive JSON extraction if any stray tokens appear
        m = re.search(r"\{.*\}", text, flags=re.S)
        json_text = m.group(0) if m else text

        obj = json.loads(json_text)

        if not isinstance(obj, dict):
            raise RuntimeError("LLM response is not a valid JSON object")
        if "ranked_indices" not in obj or "answer" not in obj:
            raise RuntimeError(
                "LLM response missing required fields: ranked_indices, answer"
            )
        if not isinstance(obj["ranked_indices"], list) or not isinstance(
            obj["answer"], str
        ):
            raise RuntimeError("LLM response has invalid field types")
        if not all(isinstance(x, int) for x in obj["ranked_indices"]):
            raise RuntimeError("LLM response has invalid indices")

        return obj
    except Exception as e:
        raise RuntimeError(f"LLM generation failed: {e}")


def single_call_rerank_and_generate(
    query: str, hits: List[Dict[str, Any]], return_k: int
) -> Dict[str, Any]:
    if not hits:
        return {"ranked": [], "answer": "No relevant sources found."}

    prompt = build_single_call_prompt(query, hits, return_k)
    obj = call_llm_rerank_and_generate(prompt)

    order: List[int] = obj.get("ranked_indices", [])
    # Map 1-based indices to hits
    selected: List[Dict[str, Any]] = []
    for i in order:
        j = i - 1
        if 0 <= j < len(hits):
            selected.append(hits[j])
        if len(selected) >= return_k:
            break
    if not selected:
        selected = hits[:return_k]
    return {"ranked": selected, "answer": obj.get("answer", "").strip()}


# ---------------- Response shaping ----------------
def to_frontend_source(
    h: Dict[str, Any], citation_ix: Optional[int] = None
) -> Dict[str, Any]:
    return {
        "id": h.get("id"),
        "doc_id": h.get("doc_id"),
        "title": h.get("title"),
        "department": h.get("department"),
        "category": h.get("category"),
        "year": h.get("year"),
        "content_preview": (h.get("content") or "")[:600],
        "chunk_ix": h.get("chunk_ix", 0),
        "chunk_count": h.get("chunk_count", 0),
        "score": h.get("score"),
        "citation": f"[Source {citation_ix}]" if citation_ix is not None else None,
    }


# ---------------- HTTP Handler ----------------
def handler(request):
    """
    Vercel-style Python function entry.
    request: dict with keys:
      - method: 'GET' | 'POST' | 'OPTIONS'
      - body: bytes | str | None
      - headers: dict
      - query: dict (for GET query params)
    Returns dict with statusCode, headers, body (string).
    """
    try:
        method = (request.get("method") or "GET").upper()

        if method == "OPTIONS":
            return {
                "statusCode": 204,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Max-Age": "86400",
                },
                "body": "",
            }

        if method == "GET":
            body = {"ok": True, "service": "rag-api", "mode": "single-llm-call"}
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(body),
            }

        if method == "POST":
            t0 = now_ms()
            init_clients()

            raw = request.get("body") or b"{}"
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            data = json.loads(raw.decode("utf-8")) if raw else {}

            action = (data.get("action") or "query").lower()

            if action == "ingest":
                # Expect docs: List[Dict] with {id, title, department, category, year, content}
                docs = data.get("docs") or []
                if not isinstance(docs, list) or not docs:
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                        },
                        "body": json.dumps(
                            {"error": "Missing or invalid 'docs' for ingestion"}
                        ),
                    }
                ingest_documents(docs)
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"ok": True, "ingested_docs": len(docs)}),
                }

            # Default: query flow (single LLM call for rerank + generation)
            query = (data.get("query") or "").strip()
            if not query:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({"error": "Missing 'query'"}),
                }

            filters = data.get("filters") or {}
            top_k = clamp(int(data.get("topK") or RAG_TOP_K), 1, 50)
            return_k = clamp(int(data.get("returnK") or RAG_RETURN_K), 1, top_k)

            pc_filter = to_pc_filter(filters)

            # 1) Retrieve candidates
            hits = pinecone_search(query, k=top_k, filter_meta=pc_filter)

            # 2) Single LLM call: rerank + generate
            outcome = single_call_rerank_and_generate(query, hits, return_k=return_k)
            selected = outcome.get("ranked", [])
            answer = outcome.get("answer", "")

            # Build sources in displayed order, assign citations [Source N]
            sources = [
                to_frontend_source(h, citation_ix=i + 1) for i, h in enumerate(selected)
            ]

            t1 = now_ms()
            resp = {
                "answer": answer,
                "sources": sources,
                "responseTimeMs": t1 - t0,
                "chunksProcessed": sum((s.get("chunk_count") or 0) for s in sources),
                "retrieved": len(hits),
            }
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(resp),
            }

        # Method not allowed
        return {
            "statusCode": 405,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Method not allowed"}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
