# Customer Support LangGraph

A modular, extensible Python pipeline for handling customer support queries. It validates input, extracts entities, retrieves answers from a knowledge base (ChromaDB + SentenceTransformers), makes decisions (resolve vs escalate), and produces a final response. It offers both a CLI workflow and a FastAPI web server.

- Built with: Pydantic, ChromaDB, SentenceTransformers, FastAPI
- Orchestrated via: YAML-defined stages executed by a pipeline agent
- Knowledge base: Embedding-based retrieval from a persisted ChromaDB collection

---

## Table of Contents

1. Features
2. Architecture Overview
3. Project Structure
4. Installation
5. Quick Start
6. Running the CLI
7. Running the FastAPI Server
8. Configuration (stages.yaml)
9. Knowledge Base and Ingestion
10. Pipeline Internals
11. API Endpoints
12. Tests
13. Troubleshooting
14. Development Tips
15. License

---

## 1) Features

- Modular pipeline with deterministic, conditional, and non-deterministic stages
- Knowledge base retrieval with ChromaDB and SentenceTransformers
- Pydantic validation of input payloads
- Simple decision logic with escalation
- Structured logging to console and file
- CLI and FastAPI integration
- Easily extendable “abilities” for each stage

---

## 2) Architecture Overview

- Input is validated with Pydantic (`InputPayload`).
- The pipeline (`LangGraphAgent`) reads stage definitions from `config/stages.yaml`.
- Each stage runs one or more “abilities” via an MCP-style router (`mcp_client.py`), which calls local functions in `src/langie/abilities.py`.
- Knowledge base retrieval uses `Retriever` backed by ChromaDB + SentenceTransformers.
- Non-deterministic stage (DECIDE) evaluates and possibly escalates.
- Final output is a structured payload including entities, scores, flags, and response.

---

## 3) Project Structure

```
.
├── app.py                         # FastAPI app with / and /chat endpoints
├── config/
│   └── stages.yaml                # Pipeline stages configuration
├── data/
│   ├── kb_faq.json                # FAQ seed data for ingestion
│   ├── tickets.json               # Ticket history (updated by FastAPI)
│   └── chroma/                    # Persisted ChromaDB store (created after ingest)
├── logs/
│   ├── pipeline.log               # Runtime logs
│   └── pipeline_test.log          # Test logs
├── pipeline/
│   └── abilities/
│       └── knowledge_base_search.py  # (legacy path used by the FastAPI app)
├── scripts/
│   ├── kb_ingest.py               # Ingest FAQ JSON into ChromaDB
|   └── run.sh                     # Convenience script to start the FastAPI server
├── src/langie/
│   ├── __main__.py                # python -m src.langie entrypoint
│   ├── abilities.py               # Ability implementations
│   ├── cli.py                     # CLI wrapper to run the pipeline
│   ├── logger.py                  # Logger configuration (console + file)
│   ├── mcp_client.py              # Ability router: COMMON/ATLAS + KB fallback
│   ├── models.py                  # Pydantic models (InputPayload)
│   ├── pipeline.py                # LangGraphAgent: loads YAML, executes stages
│   └── retriever.py               # ChromaDB + SentenceTransformers retriever
├── static/
│   └── index.html                 # Simple UI page (served under /static)
├── test_insertDB.py               # Add FAQ and rebuild ChromaDB demo
├── test_out_of_scope.py           # OOD retrieval test (uses legacy method name)
├── test_pipeline.py               # Pipeline smoke test
├── test_retriever.py              # Retrieval test (uses legacy method name)
├── pyproject.toml                 # Build metadata
├── requirements.txt               # Runtime dependencies
└── README.md                      # This document
```

Note: Some tests call `Retriever.retrieve(...)` while the current implementation exposes `search(...)`. If you run those tests as-is, adjust accordingly or add a small adapter.

---

## 4) Installation

1) Create a clean virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2) Install dependencies:
```bash
pip install -r requirements.txt
```

3) Verify Python version:
- Requires Python 3.10+ (see `pyproject.toml`). Recommended: Python 3.11.

---

## 5) Quick Start

1) Ingest the knowledge base (creates `data/chroma` with embeddings):
```bash
python scripts/kb_ingest.py
```

2) Run the CLI with default sample:
```bash
python -m src.langie run --config config/stages.yaml
```

3) Start the FastAPI server:
```bash
uvicorn app:app --reload --port 8000
```
Open http://localhost:8000/static/index.html

---

## 6) Running the CLI

Command:
```bash
python -m src.langie run --config config/stages.yaml [--input path/to/input.json] [--debug]
```

- `--config`: Path to pipeline YAML.
- `--input`: Optional JSON payload file. If omitted, a built-in sample is used.
- `--debug`: Enable verbose logging.

Example input JSON:
```json
{
  "customer_name": "Alice",
  "email": "alice@example.com",
  "query": "My order #123 hasn’t arrived",
  "priority": "High",
  "ticket_id": "TKT-5678"
}
```

What happens:
- Loads `stages.yaml`
- Validates payload with `InputPayload`
- Runs abilities per stage
- Prints final state JSON to stdout

---

## 7) Running the FastAPI Server

Start:
```bash
uvicorn app:app --reload --port 8000
```

Endpoints:
- GET `/` → Serves `static/index.html`
- POST `/chat` → Accepts name/email/query, runs KB search, returns ticket with response

Example `curl`:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
        "customer_name": "Bob",
        "email": "bob@example.com",
        "query": "What is your refund policy?"
      }'
```

Response will include:
- `ticket_id`
- `response`
- `alternatives`
- `status` (resolved/pending)
- `timestamp`

Tickets are stored in `data/tickets.json`.

---

## 8) Configuration (stages.yaml)

`config/stages.yaml` defines the pipeline stages and abilities. Modes:
- deterministic: run abilities in order
- non-deterministic: perform evaluation then branch (e.g., escalate)

Excerpt:
```yaml
stages:
  - name: INTAKE
    mode: deterministic
    abilities:
      - { name: accept_payload, server: COMMON }

  - name: UNDERSTAND
    mode: deterministic
    abilities:
      - { name: parse_request_text, server: COMMON }
      - { name: extract_entities,   server: ATLAS }

  - name: RETRIEVE
    mode: deterministic
    abilities:
      - { name: knowledge_base_search, server: ATLAS }
      - { name: store_data,            server: COMMON }

  - name: DECIDE
    mode: non-deterministic
    abilities:
      - { name: solution_evaluation, server: COMMON }
      - { name: escalation_decision, server: ATLAS }
      - { name: update_payload,      server: COMMON }

  - name: CREATE
    mode: deterministic
    abilities:
      - { name: response_generation, server: COMMON }
```

- Abilities are routed to `COMMON` or `ATLAS` via `mcp_client.py`.
- `knowledge_base_search` is handled via a retriever shortcut in `pipeline.py`.

---

## 9) Knowledge Base and Ingestion

- Source FAQ: `data/kb_faq.json`
- Ingestion: `scripts/kb_ingest.py` reads the JSON and indexes it into ChromaDB with SentenceTransformers embeddings.

Run ingestion:
```bash
python scripts/kb_ingest.py
```

Add an FAQ and rebuild (example script):
```bash
python test_insertDB.py
```

Retriever implementation (simplified):
```python
# Python example showing how the retriever works
from src.langie.retriever import Retriever

# Create retriever (persisted DB)
retriever = Retriever(db_path="data/chroma", collection_name="faq")

# Search top-3 results for a query
hits = retriever.search("How do I get a refund?", top_k=3)

# Each hit contains question, answer, doc, and a distance-based score
for h in hits:
    print(h["answer"])  # comment: prints the retrieved answer text
```

Notes:
- Initial download of "all-MiniLM-L6-v2" happens once and is cached.
- Ensure `data/chroma/` is writable and present (created by ingestion).

---

## 10) Pipeline Internals

Core class: `src/langie/pipeline.py` → `LangGraphAgent`

- Loads YAML config
- Validates payload via `InputPayload`
- Executes stages and abilities
- Merges results into a shared `state`
- Provides structured logs and summary

Key ability highlights (`src/langie/abilities.py`):

- `accept_payload`: Ensures required keys and default structures exist.
- `parse_request_text`: Tokenizes query, extracts simple patterns (e.g., order ID).
- `extract_entities`: Heuristic intent/issue/product extraction.
- `normalize_fields`: Normalizes email, priority, and cleans order ID format.
- `enrich_records`: Adds SLA/historical metadata.
- `clarify_question` / `extract_answer` / `store_answer`: Simulated Q&A loop for missing details.
- `knowledge_base_search`: No-op in abilities (the pipeline itself already injects KB results).
- `store_data`: Derives `kb_hits` and `kb_top_answer` from retrieval results.
- `solution_evaluation`: Assigns a 0–100 score based on KB hits.
- `escalation_decision`: Escalates to human if score < 90.
- `response_generation`: Selects the best response (KB top answer or a fallback).
- `update_ticket` / `close_ticket`: Simulated CRM updates.
- `output_payload`: Final structured output for downstream usage.

Ability routing (`src/langie/mcp_client.py`):
- `call_common` and `call_atlas` map `ability_name` to the function in `abilities.py`.
- Special-cases `knowledge_base_search` to call the shared retriever for KB results.

Input validation (`src/langie/models.py`):
```python
# Python: Pydantic schema with comments
from pydantic import BaseModel, Field
from typing import Optional

class InputPayload(BaseModel):
    # comment: schema for the incoming ticket/request
    customer_name: str
    email: str
    query: str
    priority: Optional[str] = Field(default="Normal")
    ticket_id: Optional[str] = None
```

---

## 11) API Endpoints

Defined in `app.py` (FastAPI):

- GET `/`:
  - Serves `static/index.html`.
- POST `/chat`:
  - Request body:
    ```json
    {
      "customer_name": "Alice",
      "email": "alice@example.com",
      "query": "Where is my order?"
    }
    ```
  - Flow:
    1. Runs knowledge base search through `KnowledgeBaseSearch` (legacy pipeline component in `pipeline/abilities/knowledge_base_search.py`).
    2. Picks top answer, marks ticket status as resolved if score >= threshold.
    3. Persists the ticket to `data/tickets.json`.
  - Response:
    ```json
    {
      "ticket_id": "TKT-00X",
      "customer_name": "Alice",
      "email": "alice@example.com",
      "query": "Where is my order?",
      "response": "KB answer...",
      "alternatives": [{"answer": "...", "score": 0.12}],
      "status": "resolved",
      "timestamp": "2025-..."
    }
    ```

Note: The web flow uses a simplified ability class under `pipeline/abilities/knowledge_base_search.py` and not the full `LangGraphAgent` pipeline. The CLI uses the YAML-based pipeline.

---

## 12) Tests

- `test_pipeline.py`:
  - Smoke test for `LangGraphAgent` reading `config/stages.yaml` and executing end-to-end.
  - Prints final output and asserts basics.

- `test_retriever.py` and `test_out_of_scope.py`:
  - Demonstrations for searching the knowledge base.
  - These invoke `retriever.retrieve(...)`, but current `Retriever` exposes `search(...)`.
  - You can either:
    - Replace `retrieve(...)` with `search(...)` in tests, or
    - Add a small adapter method to `Retriever`:
      ```python
      # Python: Optional adapter for backward compatibility
      class Retriever(...):
          def retrieve(self, query: str, top_k: int = 3):
              # comment: call the new search method for legacy tests
              return self.search(query, top_k=top_k)
      ```

Run tests:
```bash
pytest
```

---

## 13) Troubleshooting

- SentenceTransformers model download is slow:
  - First-time download of "all-MiniLM-L6-v2" can take time. It is cached afterward.
- ChromaDB directory missing:
  - Run `python scripts/kb_ingest.py` to create/populate `data/chroma/`.
- No results from KB search:
  - Verify `data/kb_faq.json` is valid and ingestion ran successfully.
- Tests failing due to `retrieve` vs `search`:
  - Update tests to use `search`, or add the adapter method shown above.
- Logging not visible:
  - Use `--debug` in CLI or tail `logs/pipeline.log`.

---

## 14) Development Tips

- Where to add new abilities:
  - Implement in `src/langie/abilities.py` as a function:
    ```python
    # Python: new ability example with comments
    def my_new_ability(state: dict) -> dict:
        # comment: read from state
        text = state.get("query", "")

        # comment: do something simple
        if "coupon" in text.lower():
            state.setdefault("entities", {})["has_coupon"] = True

        # comment: return full state dict
        return state
    ```
  - Register in `src/langie/mcp_client.py` under `COMMON_ABILITY_MAP` or `ATLAS_ABILITY_MAP`.
  - Reference in `config/stages.yaml`:
    ```yaml
    - name: CUSTOM
      mode: deterministic
      abilities:
        - { name: my_new_ability, server: COMMON }
    ```

- How to change the decision logic:
  - Modify `solution_evaluation` in `abilities.py` to reflect your scoring strategy.

- How to customize the response:
  - Edit `response_generation` to format the reply or use templates.

---

## 15) License

This project is licensed under the MIT License. See the LICENSE file for details.