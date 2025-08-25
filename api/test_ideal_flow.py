#!/usr/bin/env python3
"""
Test script to verify the ideal RAG flow:
1. Document upload
2. BAAI embeddings using HF API
3. Store in Pinecone
4. List existing documents
5. RAG search with filters
"""

import os
import sys
import json
from typing import List, Dict, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_environment():
    """Test if all required environment variables are set"""
    print("=== Testing Environment Variables ===")

    required_vars = {
        "PINECONE_API_KEY": "Pinecone API key",
        "HUGGINGFACE_API_KEY": "Hugging Face API key for BAAI embeddings",
    }

    optional_vars = {
        "OPENAI_API_KEY": "OpenAI API key for answer generation",
        "GROQ_API_KEY": "Groq API key for answer generation",
    }

    missing_required = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {description} - Set")
        else:
            print(f"❌ {var}: {description} - Missing")
            missing_required.append(var)

    print("\nOptional variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {description} - Set")
        else:
            print(f"⚠️  {var}: {description} - Not set (will use fallback)")

    if missing_required:
        print(
            f"\n❌ Missing required environment variables: {', '.join(missing_required)}"
        )
        return False

    print("\n✅ All required environment variables are set")
    return True


def test_embeddings():
    """Test BAAI embeddings via Hugging Face API"""
    print("\n=== Testing BAAI Embeddings ===")

    try:
        from core.search import embed_texts

        test_texts = [
            "This is a test document for embedding generation.",
            "Another test document with different content.",
        ]

        embeddings = embed_texts(test_texts)

        if len(embeddings) == 2 and len(embeddings[0]) > 0:
            print(f"✅ Generated {len(embeddings)} embeddings")
            print(f"✅ Embedding dimensions: {len(embeddings[0])}")
            print(f"✅ First embedding preview: {embeddings[0][:5]}...")
            return True
        else:
            print("❌ Invalid embedding format")
            return False

    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False


def test_pinecone_connection():
    """Test Pinecone connection and index"""
    print("\n=== Testing Pinecone Connection ===")

    try:
        from core.search import init_clients, _pinecone_index

        init_clients()

        if _pinecone_index is not None:
            # Test index stats
            stats = _pinecone_index.describe_index_stats()
            print(f"✅ Connected to Pinecone index: {stats}")
            return True
        else:
            print("❌ Pinecone index not initialized")
            return False

    except Exception as e:
        print(f"❌ Pinecone connection test failed: {e}")
        return False


def test_document_upload():
    """Test document upload flow"""
    print("\n=== Testing Document Upload Flow ===")

    try:
        from core.upload import handler

        # Create a test document
        test_doc = {
            "id": "test_doc_001",
            "title": "Test Document",
            "department": "Engineering",
            "category": "Technical",
            "year": 2024,
            "content": "This is a test document content for the RAG system. It contains information about testing and validation.",
        }

        # Create mock request
        request = {
            "method": "POST",
            "body": json.dumps(test_doc).encode(),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(request)

        if response["statusCode"] == 200:
            print("✅ Document upload successful")
            return True
        else:
            print(f"❌ Document upload failed: {response}")
            return False

    except Exception as e:
        print(f"❌ Document upload test failed: {e}")
        return False


def test_document_listing():
    """Test listing existing documents"""
    print("\n=== Testing Document Listing ===")

    try:
        from core.search import init_clients, _pinecone_index
        import os

        init_clients()

        # Query documents from registry namespace
        namespace = os.getenv("DOCS_NAMESPACE", "docs_registry")
        dummy_vector = [0.0] * 384

        result = _pinecone_index.query(
            vector=dummy_vector, top_k=10, include_metadata=True, namespace=namespace
        )

        documents = result.matches or []
        print(f"✅ Found {len(documents)} documents in registry")

        for i, doc in enumerate(documents[:3]):
            metadata = doc.metadata or {}
            print(
                f"  Document {i+1}: {metadata.get('title', 'Untitled')} ({metadata.get('department', 'Unknown')})"
            )

        return True

    except Exception as e:
        print(f"❌ Document listing test failed: {e}")
        return False


def test_rag_search():
    """Test RAG search with filters"""
    print("\n=== Testing RAG Search ===")

    try:
        from core.search import handler

        # Test search request
        search_request = {
            "method": "POST",
            "body": json.dumps(
                {
                    "query": "test document",
                    "filters": {"department": "Engineering"},
                    "topK": 5,
                    "returnK": 3,
                }
            ).encode(),
            "headers": {"Content-Type": "application/json"},
        }

        response = handler(search_request)

        if response["statusCode"] == 200:
            data = json.loads(response["body"])
            print(f"✅ Search successful")
            print(f"✅ Found {len(data.get('sources', []))} sources")
            print(f"✅ Answer: {data.get('answer', 'No answer')[:100]}...")
            return True
        else:
            print(f"❌ Search failed: {response}")
            return False

    except Exception as e:
        print(f"❌ RAG search test failed: {e}")
        return False


def main():
    """Run all tests for the ideal flow"""
    print("🧪 Testing Ideal RAG Flow")
    print("=" * 50)

    tests = [
        ("Environment Variables", test_environment),
        ("BAAI Embeddings", test_embeddings),
        ("Pinecone Connection", test_pinecone_connection),
        ("Document Upload", test_document_upload),
        ("Document Listing", test_document_listing),
        ("RAG Search", test_rag_search),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! The ideal flow is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
