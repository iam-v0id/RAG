#!/usr/bin/env python3
"""
Test script to verify search functionality
"""

import os
import sys
from typing import List, Dict, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_search():
    print("=== Testing Search Functionality ===\n")

    try:
        from core.search import init_clients, pinecone_search

        # Initialize clients
        print("1. Initializing clients...")
        init_clients()
        print("   ✅ Clients initialized successfully")

        # Test search with a simple query
        print("\n2. Testing search...")
        test_query = "test"
        print(f"   Query: '{test_query}'")

        hits = pinecone_search(test_query, k=5)
        print(f"   ✅ Search completed successfully")
        print(f"   📊 Number of hits: {len(hits)}")

        if hits:
            print(f"   📊 First hit score: {hits[0].get('score', 'N/A')}")
            print(f"   📊 First hit title: {hits[0].get('title', 'N/A')}")
            print(
                f"   📊 First hit content preview: {hits[0].get('content', '')[:100]}..."
            )
        else:
            print("   ⚠️  No hits found - this might indicate:")
            print("      - No documents in the index")
            print("      - Query doesn't match any content")
            print("      - Embedding/model issues")

        # Test with a more specific query
        print("\n3. Testing with specific query...")
        specific_query = "document"
        print(f"   Query: '{specific_query}'")

        hits2 = pinecone_search(specific_query, k=3)
        print(f"   📊 Number of hits: {len(hits2)}")

        if hits2:
            for i, hit in enumerate(hits2[:2]):
                print(f"   Hit {i+1}:")
                print(f"     - Score: {hit.get('score', 'N/A')}")
                print(f"     - Title: {hit.get('title', 'N/A')}")
                print(f"     - Content: {hit.get('content', '')[:80]}...")

        return True

    except Exception as e:
        print(f"   ❌ Search test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_index_contents():
    print("\n=== Testing Index Contents ===\n")

    try:
        from core.search import init_clients
        import core.search

        init_clients()

        # Get index stats
        stats = core.search._pinecone_index.describe_index_stats()
        print(f"Index stats: {stats}")

        # Try to get some vectors from the main namespace
        namespace = core.search.RAG_INDEX_NAMESPACE or "main"
        print(f"\nFetching vectors from namespace: '{namespace}'")

        # Use a dummy vector to query
        dummy_vector = [0.0] * 384
        result = core.search._pinecone_index.query(
            vector=dummy_vector, top_k=10, include_metadata=True, namespace=namespace
        )

        print(f"Found {len(result.matches or [])} vectors")

        if result.matches:
            print("\nSample vectors:")
            for i, match in enumerate(result.matches[:3]):
                print(f"  Vector {i+1}:")
                print(f"    ID: {match.id}")
                print(f"    Score: {match.score}")
                print(f"    Metadata: {match.metadata}")

        return True

    except Exception as e:
        print(f"❌ Index test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Starting search tests...\n")

    success1 = test_search()
    success2 = test_index_contents()

    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
