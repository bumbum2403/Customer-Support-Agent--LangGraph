# scripts/kb_ingest.py
import json
import os
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions

DATA_PATH = "data/kb_faq.json"
DB_PATH = "data/chroma"
COLLECTION_NAME = "faq"

def load_faq(path: str):
    """Load FAQ JSON file into a list of dicts with 'question' and 'answer'."""
    with open(path, "r") as f:
        return json.load(f)

def ingest():
    # Init Chroma client (persistent)
    client = chromadb.PersistentClient(path=DB_PATH)

    # Use a SentenceTransformer wrapper (works offline too)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"  # downloaded once, then cached locally
    )

    # Create or load collection with the embedding function
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )

    # Load FAQ data
    faqs = load_faq(DATA_PATH)

    ids, texts, metadatas = [], [], []
    for i, item in enumerate(faqs):
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()

        ids.append(f"faq-{i}")
        texts.append(f"Q: {q}\nA: {a}")  # embed both Q & A
        metadatas.append({"question": q, "answer": a})

    # Clean old data (safe refresh)
    if ids:
        collection.delete(ids=ids)
        collection.add(ids=ids, documents=texts, metadatas=metadatas)

    print(f"✅ Ingested {len(faqs)} FAQ entries into ChromaDB at {DB_PATH}")

if __name__ == "__main__":
    ingest()
