#!/usr/bin/env python3
"""
Test script to check environment variables and dependencies for the RAG API.
Run this to diagnose deployment issues.
"""

import os
import sys


def check_env_vars():
    """Check if required environment variables are set."""
    required_vars = [
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        "PINECONE_CLOUD",
        "PINECONE_REGION",
    ]

    optional_vars = [
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "HUGGINGFACE_API_KEY",
        "DOCS_NAMESPACE",
        "RAG_INDEX_NAMESPACE",
    ]

    print("=== Environment Variables Check ===")

    print("\nRequired variables:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(
                f"✓ {var}: {value[:10]}..." if len(value) > 10 else f"✓ {var}: {value}"
            )
        else:
            print(f"✗ {var}: NOT SET")
            missing_required.append(var)

    print("\nOptional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(
                f"✓ {var}: {value[:10]}..." if len(value) > 10 else f"✓ {var}: {value}"
            )
        else:
            print(f"- {var}: not set (optional)")

    return len(missing_required) == 0


def check_dependencies():
    """Check if required Python packages are available."""
    print("\n=== Dependencies Check ===")

    dependencies = [
        ("pinecone-client", "pinecone"),
        ("sentence-transformers", "sentence_transformers"),
        ("numpy", "numpy"),
        ("openai", "openai"),
        ("httpx", "httpx"),
        ("python-dotenv", "dotenv"),
    ]

    missing_deps = []
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError as e:
            print(f"✗ {package_name}: {e}")
            missing_deps.append(package_name)

    return len(missing_deps) == 0


def test_pinecone_connection():
    """Test Pinecone connection if API key is available."""
    print("\n=== Pinecone Connection Test ===")

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("✗ PINECONE_API_KEY not set, skipping connection test")
        return False

    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=api_key)

        # Try to list indexes
        indexes = pc.list_indexes()
        print(f"✓ Successfully connected to Pinecone")
        print(f"  Available indexes: {[idx.name for idx in indexes.indexes]}")

        # Check if our index exists
        index_name = os.getenv("PINECONE_INDEX_NAME", "company-docs")
        index_exists = any(idx.name == index_name for idx in indexes.indexes)
        if index_exists:
            print(f"✓ Index '{index_name}' exists")
        else:
            print(
                f"- Index '{index_name}' does not exist (will be created on first use)"
            )

        return True

    except Exception as e:
        print(f"✗ Failed to connect to Pinecone: {e}")
        return False


def main():
    """Run all checks."""
    print("RAG API Environment and Dependencies Check")
    print("=" * 50)

    env_ok = check_env_vars()
    deps_ok = check_dependencies()
    pinecone_ok = test_pinecone_connection()

    print("\n=== Summary ===")
    if env_ok and deps_ok and pinecone_ok:
        print("✓ All checks passed! Your environment is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
