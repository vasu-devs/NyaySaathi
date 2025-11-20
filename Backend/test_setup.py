import sys
import time
from app.services.vector_store import QdrantStore
from app.services.embedding import get_embedder

def test_qdrant():
    print("Testing Qdrant connection...")
    try:
        store = QdrantStore()
        info = store.client.get_collections()
        print(f"Success! Collections: {info}")
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        sys.exit(1)

def test_embedding():
    print("Testing embedding model...")
    try:
        model = get_embedder()
        vec = model.encode("test query")
        print(f"Success! Vector dimension: {len(vec)}")
    except Exception as e:
        print(f"Failed to generate embedding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_qdrant()
    test_embedding()
