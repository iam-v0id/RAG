# api/search.py
from typing import List, Dict, Any, Optional
import json
import os
import re
import time

# Optionally load env vars in development
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    import pathlib

    # 1) Try auto-discovery upwards from this file
    loaded = False
    try:
        found = find_dotenv(usecwd=False)
        if found:
            load_dotenv(found)
            loaded = True
    except Exception:
        pass

    # 2) If not found, try explicit parent: RAG/.env when running from RAG/api/
    if not loaded:
        api_dir = pathlib.Path(__file__).resolve().parent
        rag_dir = api_dir.parent
        candidate = rag_dir / ".env"
        if candidate.exists():
            load_dotenv(candidate.as_posix())
            loaded = True
except Exception:
    pass

# Core deps (optional)
try:
    import numpy as np  # noqa: F401
except ImportError as e:
    print(f"Warning: numpy not available: {e}")
    np = None  # type: ignore

# Note: sentence-transformers removed to reduce bundle size
# Using Hugging Face API for embeddings instead
SentenceTransformer = None

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError as e:
    print(f"Warning: pinecone-client not available: {e}")
    Pinecone = None  # type: ignore


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
    if Pinecone is None:
        raise RuntimeError(
            "Missing Pinecone client. Add 'pinecone-client' to requirements."
        )
    if not os.getenv("PINECONE_API_KEY"):
        raise RuntimeError("Missing PINECONE_API_KEY in environment.")
    if _pc is None:
        try:
            _pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
            try:
                existing = [idx.name for idx in _pc.list_indexes().indexes]
            except Exception as e:
                print(f"Warning: Could not list existing indexes: {e}")
                existing = []
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

    # Note: Using Hugging Face API for embeddings instead of local models
    # This reduces bundle size and works better in serverless environments
    _hf_model = None


# ---------------- Embeddings ----------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    # Prefer local model if available
    if _hf_model is not None:
        vecs = _hf_model.encode(texts, show_progress_bar=False)
        return vecs.tolist() if hasattr(vecs, "tolist") else vecs  # type: ignore

    # Fallback: use Hugging Face Inference API for embeddings (free tier available)
    hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    model_id = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    api_url = (
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
    )

    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    import httpx  # type: ignore

    # HF API accepts a single string or list of strings. We'll send list to get batched output.
    resp = httpx.post(
        api_url,
        headers=headers,
        json={"inputs": texts, "options": {"wait_for_model": True}},
        timeout=60.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Hugging Face embedding request failed: {resp.status_code} {resp.text}"
        )

    data = resp.json()

    # Response can be list[list[float]] for single input or list[list[list[float]]] when batching token vectors.
    # For sentence-transformers feature-extraction pipeline, output is token-level; we need to pool to sentence.
    # We'll mean-pool across tokens per input.
    def mean_pool(token_vectors: List[List[float]]) -> List[float]:
        if not token_vectors:
            return []
        dim = len(token_vectors[0]) if token_vectors[0] else 0
        sums = [0.0] * dim
        for tv in token_vectors:
            for i in range(dim):
                sums[i] += float(tv[i])
        return [s / max(1, len(token_vectors)) for s in sums]

    # If the API returns a list for single input, normalize to batch
    if (
        texts
        and isinstance(data, list)
        and data
        and isinstance(data[0], list)
        and data
        and isinstance(data[0][0], (int, float))
    ):
        # Single input, token-level vectors
        return [mean_pool(data)]

    # Otherwise, expect list of inputs each with token-level vectors
    out: List[List[float]] = []
    for item in data:
        out.append(mean_pool(item))
    return out


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
    print(f"DEBUG: pinecone_search called")
    print(f"DEBUG: Query: '{query}'")
    print(f"DEBUG: k: {k}")
    print(f"DEBUG: filter_meta: {filter_meta}")
    print(f"DEBUG: _pinecone_index: {_pinecone_index}")
    print(f"DEBUG: _hf_model: {_hf_model}")

    if _pinecone_index is None:
        print(f"DEBUG: Missing Pinecone index")
        return []

    print(f"DEBUG: Embedding query...")
    qvec = embed_texts([query])[0]
    print(f"DEBUG: Query vector length: {len(qvec)}")

    print(f"DEBUG: Querying Pinecone...")
    res = _pinecone_index.query(
        vector=qvec,
        top_k=k,
        include_metadata=True,
        filter=filter_meta or {},
        namespace=RAG_INDEX_NAMESPACE,
    )
    print(f"DEBUG: Pinecone query completed")
    print(f"DEBUG: Number of matches: {len(res.matches or [])}")
    hits: List[Dict[str, Any]] = []
    for i, m in enumerate(res.matches or []):
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
        print(f"DEBUG: Hit {i+1}:")
        print(f"  - ID: {hit['id']}")
        print(f"  - Doc ID: {hit['doc_id']}")
        print(f"  - Title: {hit['title']}")
        print(f"  - Score: {hit['score']}")
        print(
            f"  - Content preview: {hit['content'][:100] if hit['content'] else 'None'}..."
        )
        hits.append(hit)
    print(f"DEBUG: Returning {len(hits)} hits")
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
    Returns {} on failure (caller will fallback).
    """
    print(
        f"DEBUG: call_llm_rerank_and_generate called with prompt length: {len(prompt)}"
    )
    print(f"DEBUG: Prompt preview: {prompt[:300]}...")

    # Prefer Groq if configured
    try:
        if GROQ_API_KEY:
            print(f"DEBUG: Using Groq API")
            print(f"DEBUG: GROQ_API_KEY: {GROQ_API_KEY[:10]}...")
            print(f"DEBUG: GROQ_BASE_URL: {GROQ_BASE_URL}")
            print(f"DEBUG: GROQ_MODEL: {GROQ_MODEL}")

            # Try using OpenAI library with minimal configuration
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000,
            )
            text = (resp.choices[0].message.content or "").strip()
            print(f"DEBUG: Groq response received, length: {len(text)}")
        else:
            if not OPENAI_API_KEY:
                print(f"DEBUG: No API keys configured")
                return {}
            print(f"DEBUG: Using OpenAI API")
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=GEN_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            text = (resp.choices[0].message.content or "").strip()
            print(f"DEBUG: OpenAI response received, length: {len(text)}")
        print(f"DEBUG: Raw LLM response: {text}")

        # Defensive JSON extraction if any stray tokens appear
        m = re.search(r"\{.*\}", text, flags=re.S)
        json_text = m.group(0) if m else text
        print(f"DEBUG: Extracted JSON text: {json_text}")

        obj = json.loads(json_text)
        print(f"DEBUG: Parsed JSON object: {obj}")

        if not isinstance(obj, dict):
            print(f"DEBUG: Object is not a dict")
            return {}
        if "ranked_indices" not in obj or "answer" not in obj:
            print(f"DEBUG: Missing required keys in JSON")
            return {}
        if not isinstance(obj["ranked_indices"], list) or not isinstance(
            obj["answer"], str
        ):
            print(f"DEBUG: Invalid types in JSON")
            return {}
        # validate indices are ints
        if not all(isinstance(x, int) for x in obj["ranked_indices"]):
            print(f"DEBUG: Invalid indices in JSON")
            return {}

        print(f"DEBUG: Successfully parsed LLM response")
        return obj
    except Exception as e:
        print(f"DEBUG: Exception in LLM call: {e}")
        return {"_error": str(e)}


def single_call_rerank_and_generate(
    query: str, hits: List[Dict[str, Any]], return_k: int
) -> Dict[str, Any]:
    print(f"DEBUG: single_call_rerank_and_generate called")
    print(f"DEBUG: Query: '{query}'")
    print(f"DEBUG: Number of hits: {len(hits)}")
    print(f"DEBUG: return_k: {return_k}")

    if not hits:
        print(f"DEBUG: No hits, returning empty result")
        return {"ranked": [], "answer": "No relevant sources found."}

    prompt = build_single_call_prompt(query, hits, return_k)
    print(f"DEBUG: Built prompt, length: {len(prompt)}")

    obj = call_llm_rerank_and_generate(prompt)
    print(f"DEBUG: LLM returned object: {obj}")

    if not obj:
        # Fallback: no LLM or parsing failed
        print(f"DEBUG: LLM failed, using fallback")
        ranked = hits[:return_k]
        answer = f"Found {len(ranked)} relevant source chunk(s). No generator configured; returning sources only."
        return {"ranked": ranked, "answer": answer}

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
    print(f"DEBUG: Handler called with method: {request.get('method')}")
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
            print(f"DEBUG: POST request received")
            init_clients()

            raw = request.get("body") or b"{}"
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            data = json.loads(raw.decode("utf-8")) if raw else {}
            print(f"DEBUG: Parsed POST data: {data}")

            action = (data.get("action") or "query").lower()
            print(f"DEBUG: Action: {action}")

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
            print(f"DEBUG: Query: '{query}'")
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
            print(f"DEBUG: Filters: {filters}")
            top_k = clamp(int(data.get("topK") or RAG_TOP_K), 1, 50)
            return_k = clamp(int(data.get("returnK") or RAG_RETURN_K), 1, top_k)
            print(f"DEBUG: top_k={top_k}, return_k={return_k}")

            pc_filter = to_pc_filter(filters)
            print(f"DEBUG: Pinecone filter: {pc_filter}")

            # 1) Retrieve candidates
            print(f"DEBUG: Searching Pinecone...")
            hits = pinecone_search(query, k=top_k, filter_meta=pc_filter)
            print(f"DEBUG: Pinecone returned {len(hits)} hits")
            if hits:
                print(f"DEBUG: First hit score: {hits[0].get('score')}")
                print(
                    f"DEBUG: First hit content preview: {hits[0].get('content', '')[:100]}"
                )
                print(f"DEBUG: First hit metadata: {dict(hits[0])}")

            # 2) Single LLM call: rerank + generate
            print(f"DEBUG: Calling LLM for rerank and generation...")
            outcome = single_call_rerank_and_generate(query, hits, return_k=return_k)
            print(f"DEBUG: LLM outcome: {outcome}")
            selected = outcome.get("ranked", [])
            answer = outcome.get("answer", "")
            print(f"DEBUG: Final answer: '{answer}'")
            print(f"DEBUG: Selected sources count: {len(selected)}")

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
