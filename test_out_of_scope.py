from src.langie.retriever import Retriever

def test_out_of_scope():
    retriever = Retriever()
    queries = [
        "What is your hiring process?",
        "Tell me about stock market trends",
        "Who is the CEO of the company?"
    ]

    for query in queries:
        print(f"\n❓ Query: {query}")
        results = retriever.retrieve(query, top_k=1)
        if results:
            print(f"   ➡️ Closest match: {results[0]['answer']} (Q: {results[0]['question']})")
        else:
            print("   🚫 No relevant match found.")

if __name__ == "__main__":
    test_out_of_scope()
