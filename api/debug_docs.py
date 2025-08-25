#!/usr/bin/env python3
"""
Debug script for the docs endpoint
Run this to test the endpoint locally and identify issues
"""

import os
import sys
import json
import pathlib

# Load nearest .env for local/dev runs, falling back to RAG/.env
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

# Add current directory to path
sys.path.append(os.path.dirname(__file__))


def test_environment():
    """Test environment variables and basic setup"""
    print("=== Environment Test ===")

    # Check required environment variables
    pinecone_key = os.getenv("PINECONE_API_KEY")
    print(f"PINECONE_API_KEY: {'✓ Set' if pinecone_key else '✗ Missing'}")

    # Check optional variables
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    print(f"HUGGINGFACE_API_KEY: {'✓ Set' if hf_key else '- Not set (optional)'}")

    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY: {'✓ Set' if openai_key else '- Not set (optional)'}")

    # Check other Pinecone settings
    index_name = os.getenv("PINECONE_INDEX_NAME", "company-docs")
    print(f"PINECONE_INDEX_NAME: {index_name}")

    region = os.getenv("PINECONE_REGION", "us-east-1")
    print(f"PINECONE_REGION: {region}")

    cloud = os.getenv("PINECONE_CLOUD", "aws")
    print(f"PINECONE_CLOUD: {cloud}")

    return bool(pinecone_key)


def test_imports():
    """Test if all required modules can be imported"""
    print("\n=== Import Test ===")

    try:
        import pinecone

        print("✓ pinecone-client imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import pinecone-client: {e}")
        return False

    try:
        import httpx

        print("✓ httpx imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import httpx: {e}")
        return False

    try:
        from core.search import init_clients, _pinecone_index

        print("✓ core.search imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import core.search: {e}")
        return False

    return True


def test_pinecone_connection():
    """Test Pinecone connection"""
    print("\n=== Pinecone Connection Test ===")

    try:
        from pinecone import Pinecone

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("✗ PINECONE_API_KEY not set")
            return False

        print("Attempting to connect to Pinecone...")
        pc = Pinecone(api_key=api_key)

        print("Listing indexes...")
        indexes = pc.list_indexes()
        print(f"✓ Successfully connected to Pinecone")
        print(f"  Available indexes: {[idx.name for idx in indexes.indexes]}")

        # Check if our index exists
        index_name = os.getenv("PINECONE_INDEX_NAME", "company-docs")
        index_exists = any(idx.name == index_name for idx in indexes.indexes)

        if index_exists:
            print(f"✓ Index '{index_name}' exists")

            # Try to get the index
            index = pc.Index(index_name)
            print(f"✓ Successfully got index '{index_name}'")

            # Try a simple query
            try:
                print("Testing simple query...")
                result = index.query(
                    vector=[0.0] * 384,
                    top_k=1,
                    include_metadata=True,
                    namespace=os.getenv("DOCS_NAMESPACE", "docs_registry"),
                )
                print(f"✓ Query successful, found {len(result.matches or [])} matches")
                return True
            except Exception as e:
                print(f"✗ Query failed: {e}")
                return False
        else:
            print(
                f"- Index '{index_name}' does not exist (will be created on first use)"
            )
            return True

    except Exception as e:
        print(f"✗ Failed to connect to Pinecone: {e}")
        return False


def test_docs_endpoint():
    """Test the docs endpoint logic"""
    print("\n=== Docs Endpoint Test ===")

    try:
        from core.search import init_clients, _pinecone_index

        print("Initializing clients...")
        init_clients()
        print("✓ Clients initialized successfully")

        if _pinecone_index is None:
            print("✗ _pinecone_index is None after initialization")
            return False

        print("✓ _pinecone_index is available")

        # Test the query logic
        ns = os.getenv("DOCS_NAMESPACE", "docs_registry")
        print(f"Using namespace: {ns}")

        v = [0.0] * 384
        print("Executing query...")

        res = _pinecone_index.query(
            vector=v, top_k=500, include_metadata=True, namespace=ns
        )

        print(f"✓ Query executed successfully")
        print(f"  Found {len(res.matches or [])} matches")

        # Process results
        items = []
        for i, m in enumerate(res.matches or []):
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

        print(f"✓ Processed {len(items)} items")
        return True

    except Exception as e:
        print(f"✗ Docs endpoint test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("RAG API Docs Endpoint Debug")
    print("=" * 50)

    env_ok = test_environment()
    if not env_ok:
        print("\n❌ Environment test failed - missing required variables")
        return 1

    imports_ok = test_imports()
    if not imports_ok:
        print("\n❌ Import test failed - missing dependencies")
        return 1

    pinecone_ok = test_pinecone_connection()
    if not pinecone_ok:
        print("\n❌ Pinecone connection test failed")
        return 1

    docs_ok = test_docs_endpoint()
    if not docs_ok:
        print("\n❌ Docs endpoint test failed")
        return 1

    print("\n✅ All tests passed! The docs endpoint should work correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
