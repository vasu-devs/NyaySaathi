from app.services.vector_store import QdrantStore
from app.core.config import settings

def verify_data():
    print(f"Checking collection: {settings.qdrant_corpus_collection}")
    store = QdrantStore()
    try:
        info = store.client.get_collection(settings.qdrant_corpus_collection)
        print(f"Collection exists. Status: {info.status}")
        print(f"Points count: {info.points_count}")
        
        if info.points_count > 0:
            print("SUCCESS: Vectors found in collection.")
        else:
            print("WARNING: Collection exists but is empty.")
            
    except Exception as e:
        print(f"Error checking collection: {e}")

if __name__ == "__main__":
    verify_data()
