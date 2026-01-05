# src/langie/retriever.py
import chromadb
from chromadb.api.types import EmbeddingFunction
from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def __call__(self, input):
        # input is a list[str]
        return self.model.encode(input).tolist()


class Retriever:
    def __init__(self, db_path: str = "data/chroma", collection_name: str = "faq"):
        """
        Retriever for ChromaDB-based FAQ Knowledge Base.
        
        Args:
            db_path (str): Path where ChromaDB is persisted.
            collection_name (str): Name of the collection to use.
        """
        self.db_path = db_path
        self.collection_name = collection_name

        # Load persisted Chroma
        self.client = chromadb.PersistentClient(path=self.db_path)

        # Pass in wrapper embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction()
        )
    def search(self, query: str, top_k: int = 3):
        """Search FAQ KB using local embeddings + ChromaDB."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        hits = []
        for doc, meta, distance in zip(
                results["documents"][0], 
                results["metadatas"][0], 
                results["distances"][0]
            ):
            hits.append({
                "question": meta.get("question"),
                "answer": meta.get("answer"),
                "doc": doc,
                # "score": 1 - distance  # if distance is 0=perfect match, convert to similarity
                "score": distance  # use distance directly
            })
        return hits

