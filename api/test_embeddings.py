#!/usr/bin/env python3
"""
Test script to check embedding functionality
"""

import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# Add current directory to path
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from core.search import init_clients, embed_texts
    print("✅ Successfully imported core.search")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_embeddings():
    print("\n=== Testing Embedding Functionality ===\n")
    
    # Test 1: Check environment variables
    print("1. Environment Variables:")
    hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
    print(f"   HUGGINGFACE_API_KEY: {'✅ Set' if hf_token else '❌ Missing'}")
    print(f"   HF_TOKEN: {'✅ Set' if os.getenv("HF_TOKEN") else '❌ Missing'}")
    print(f"   HF_EMBED_MODEL: {os.getenv('HF_EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')}")
    
    # Test 2: Initialize clients
    print("\n2. Initializing clients...")
    try:
        init_clients()
        print("   ✅ Clients initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize clients: {e}")
        return
    
    # Test 3: Test embedding with a simple text
    print("\n3. Testing embeddings...")
    test_texts = ["This is a test document for embedding generation."]
    
    try:
        embeddings = embed_texts(test_texts)
        print(f"   ✅ Embeddings generated successfully")
        print(f"   📊 Number of embeddings: {len(embeddings)}")
        print(f"   📊 Embedding dimensions: {len(embeddings[0]) if embeddings else 0}")
        print(f"   📊 First embedding preview: {embeddings[0][:5] if embeddings else 'None'}...")
        
        # Check if embeddings look like real embeddings (not random)
        if embeddings and len(embeddings[0]) > 0:
            first_embedding = embeddings[0]
            # Check if values are reasonable (not all the same, not all zeros)
            unique_values = len(set(round(x, 3) for x in first_embedding))
            max_val = max(abs(x) for x in first_embedding)
            min_val = min(abs(x) for x in first_embedding)
            
            print(f"   📊 Unique values (rounded): {unique_values}")
            print(f"   📊 Value range: [{min_val:.3f}, {max_val:.3f}]")
            
            if unique_values > 10 and max_val > 0.1:
                print("   ✅ Embeddings look like real embeddings (not random)")
            else:
                print("   ⚠️  Embeddings might be random fallback")
        
    except Exception as e:
        print(f"   ❌ Failed to generate embeddings: {e}")
        return
    
    # Test 4: Test with multiple texts
    print("\n4. Testing with multiple texts...")
    test_texts_multi = [
        "First document about machine learning.",
        "Second document about artificial intelligence.",
        "Third document about data science."
    ]
    
    try:
        embeddings_multi = embed_texts(test_texts_multi)
        print(f"   ✅ Multiple embeddings generated successfully")
        print(f"   📊 Number of embeddings: {len(embeddings_multi)}")
        
        # Check if embeddings are different (not all the same)
        if len(embeddings_multi) >= 2:
            first = embeddings_multi[0]
            second = embeddings_multi[1]
            similarity = sum(a * b for a, b in zip(first, second)) / (sum(a*a for a in first) ** 0.5 * sum(b*b for b in second) ** 0.5)
            print(f"   📊 Cosine similarity between first two: {similarity:.3f}")
            
            if similarity < 0.99:
                print("   ✅ Embeddings are different (good)")
            else:
                print("   ⚠️  Embeddings are very similar (might be random)")
        
    except Exception as e:
        print(f"   ❌ Failed to generate multiple embeddings: {e}")
        return
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_embeddings()
