import json
from pathlib import Path
import subprocess

KB_JSON = Path("data/kb_faq.json")

def add_faq_to_json(question: str, answer: str):
    """Append a new Q&A entry to kb_faq.json."""
    if not KB_JSON.exists():
        kb = []
    else:
        kb = json.loads(KB_JSON.read_text())

    new_id = f"faq_{len(kb)+1:03d}"
    kb.append({"id": new_id, "question": question, "answer": answer})

    KB_JSON.write_text(json.dumps(kb, indent=2))
    print(f"✅ Added new FAQ to JSON: Q='{question}' | A='{answer}'")

def rebuild_chroma_db():
    """Call kb_ingest.py to rebuild ChromaDB."""
    subprocess.run(["python", "scripts/kb_ingest.py"], check=True)
    print("✅ ChromaDB rebuilt with updated FAQs.")

if __name__ == "__main__":
    # Example FAQ to add
    add_faq_to_json(
        "Do you provide 24/7 customer support?",
        "Yes, our customer support is available 24/7 via chat and email."
    )
    rebuild_chroma_db()
