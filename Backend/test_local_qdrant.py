import sys
import os
# Add the current directory to sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.vector_store import QdrantStore
from app.core.config import settings
import uuid

def test_local_qdrant():
    print(f"Testing local Qdrant at path: {settings.qdrant_path}")
    print(f"Qdrant URL: {settings.qdrant_url}")
    
    collection_name = "test_collection_" + str(uuid.uuid4())
    store = QdrantStore(collection=collection_name)
    
    print(f"Creating collection: {collection_name}")
    # help(store.client.query_points)
    store.ensure_collection(vector_size=4)
    
    print("Upserting point...")
    store.upsert_points(
        ids=[str(uuid.uuid4())],
        vectors=[[0.1, 0.2, 0.3, 0.4]],
        payloads=[{"test": "data"}]
    )
    
    print("Searching...")
    results = store.search([0.1, 0.2, 0.3, 0.4], top_k=1)
    
    if results:
        print("Success! Found point:", results[0])
    else:
        print("Failed! No results found.")

    # Cleanup
    store.client.delete_collection(collection_name)
    print("Cleanup done.")

if __name__ == "__main__":
    test_local_qdrant()
