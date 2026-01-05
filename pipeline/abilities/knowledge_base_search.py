# pipeline/abilities/knowledge_base_search.py
from src.langie.retriever import Retriever

class KnowledgeBaseSearch:
    def __init__(self, config=None):
        # Config may hold db path, collection name, top-k, etc.
        db_path = config.get("db_path", "data/chroma") if config else "data/chroma"
        collection = config.get("collection", "faq") if config else "faq"
        self.top_k = config.get("top_k", 3) if config else 3

        self.retriever = Retriever(db_path=db_path, collection_name=collection)

    def run(self, state: dict):
        query = state.get("input", {}).get("text", "")
        if not query:
            state["knowledge_base"] = []
            state["response"] = "No response generated"
            return state

        results = self.retriever.search(query, top_k=self.top_k)

        # Normalize into pipeline output
        kb_results = []
        for r in results:
            kb_results.append({
                "id": r.get("id"),
                "question": r.get("question"),
                "answer": r.get("answer"),
                "score": r.get("score", 1.0),
                "metadata": r.get("metadata", {})
            })

        state["knowledge_base"] = kb_results

        # Pick top answer as main response
        if kb_results:
            state["response"] = kb_results[0]["answer"]
        else:
            state["response"] = "No response generated"

        return state

