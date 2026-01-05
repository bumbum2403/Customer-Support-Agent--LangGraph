# app.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pipeline.abilities.knowledge_base_search import KnowledgeBaseSearch
from datetime import datetime
import json
import os

app = FastAPI()

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load pipeline components
kb_search = KnowledgeBaseSearch(config={"db_path": "data/chroma", "collection": "faq", "top_k": 3})

# File to store tickets
TICKETS_FILE = "data/tickets.json"

# Ticket counter (for TKT-XXX IDs)
def get_next_ticket_id():
    if not os.path.exists(TICKETS_FILE):
        return "TKT-001"
    with open(TICKETS_FILE, "r") as f:
        try:
            tickets = json.load(f)
            if not tickets:
                return "TKT-001"
            last_id = tickets[-1]["ticket_id"]
            num = int(last_id.split("-")[1])
            return f"TKT-{num + 1:03d}"
        except Exception:
            return "TKT-001"

# Save ticket
def save_ticket(ticket):
    tickets = []
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "r") as f:
            try:
                tickets = json.load(f)
            except json.JSONDecodeError:
                tickets = []
    tickets.append(ticket)
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)

# Threshold score to mark as resolved
SCORE_THRESHOLD = 0.25

class ChatPayload(BaseModel):
    customer_name: str
    email: str
    query: str

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return f.read()

@app.post("/chat")
async def chat(payload: ChatPayload):
    state = {
        "input": {"text": payload.query},
        "customer_name": payload.customer_name,
        "email": payload.email
    }

    # Run KB search
    state = kb_search.run(state)
    knowledge_base = state.get("knowledge_base", [])

    # Determine main response and status
    if knowledge_base:
        top_answer_data = knowledge_base[0]
        top_answer = top_answer_data.get("answer", "No response generated")
        status = "resolved" if top_answer_data.get("score", 0) >= SCORE_THRESHOLD else "pending"
    else:
        top_answer = "No response generated"
        status = "pending"

    ticket_id = get_next_ticket_id()

    ticket = {
        "ticket_id": ticket_id,
        "customer_name": payload.customer_name,
        "email": payload.email,
        "query": payload.query,
        "response": top_answer,
        "alternatives": [
            {"answer": r.get("answer", ""), "score": r.get("score", 0)} for r in knowledge_base
        ],
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Save ticket to JSON file
    save_ticket(ticket)

    return JSONResponse(ticket)
