from src.langie.retriever import Retriever

def run_tests():
    retriever = Retriever()
    queries = [
        "How do I return a product?",
        "What should I do if my order is delayed?",
        "How do I track my order?",
        "Tell me about refund policy",
        "Do you offer international shipping?"
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        results = retriever.retrieve(query, top_k=2)
        for idx, res in enumerate(results, start=1):
            print(f"   {idx}. {res['answer']} (Q: {res['question']})")

if __name__ == "__main__":
    run_tests()
