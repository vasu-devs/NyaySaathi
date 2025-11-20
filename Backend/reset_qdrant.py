from app.services.vector_store import QdrantStore
from app.core.config import settings

def reset_collection():
    print(f"Deleting collection: {settings.qdrant_corpus_collection}")
    store = QdrantStore()
    try:
        store.client.delete_collection(settings.qdrant_corpus_collection)
        print("Collection deleted successfully.")
    except Exception as e:
        print(f"Error deleting collection: {e}")

if __name__ == "__main__":
    reset_collection()
