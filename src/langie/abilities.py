# src/langie/abilities.py
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# -------------------------------
# STAGE 1: INTAKE
# -------------------------------
def accept_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Capture/normalize incoming request fields.
    Idempotent: ensures required keys exist so subsequent stages don't blow up.
    """
    required = ["customer_name", "email", "query", "priority", "ticket_id"]
    for f in required:
        state[f] = state.get(f, "")
    state.setdefault("entities", {})
    state.setdefault("flags", {})
    state.setdefault("meta", {})
    return state


# -------------------------------
# STAGE 2: UNDERSTAND (COMMON + ATLAS)
# -------------------------------
def parse_request_text(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    COMMON: Convert unstructured query into simple structure.
    Extract obvious patterns deterministically (fast-path).
    """
    text = state.get("query", "") or ""
    order_id_match = re.search(r"#\d+", text)
    if order_id_match:
        state["entities"]["order_id"] = order_id_match.group()
    state["raw_query"] = text
    state["parsed_query_tokens"] = text.split()
    return state


def extract_entities(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Identify product/issue/intent (simulate external system).
    Pragmatic heuristic so the pipeline is fully functional out-of-the-box.
    """
    text = (state.get("raw_query") or state.get("query") or "").lower()
    intent = None
    issue = None
    product = None

    if "refund" in text:
        intent = "refund_request"
    if any(k in text for k in ["delay", "late", "haven't arrived", "hasn’t arrived"]):
        issue = "delivery_delay"
    if "invoice" in text:
        product = "invoice_service"

    # Merge into existing entities (non-destructive)
    ents = state.get("entities", {})
    if intent: ents["intent"] = intent
    if issue: ents["issue"] = issue
    if product: ents["product"] = product
    state["entities"] = ents

    # Lightweight confidence for conditional stages
    state["confidence"] = 0.9 if any([intent, issue, product]) else 0.5
    return state


# -------------------------------
# STAGE 3: PREPARE (COMMON + ATLAS + COMMON)
# -------------------------------
def normalize_fields(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    COMMON: Standardize fields (emails lowercased, priority normalized, etc.)
    """
    email = (state.get("email") or "").strip()
    state["email"] = email.lower()

    priority = (state.get("priority") or "Normal").strip().title()
    if priority not in {"Low", "Normal", "High", "Urgent"}:
        priority = "Normal"
    state["priority"] = priority

    # standardize order_id shape if present (strip '#')
    oid = state.get("entities", {}).get("order_id")
    if oid and oid.startswith("#"):
        state["entities"]["order_id"] = oid[1:]

    return state


def enrich_records(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Simulate pulling SLA / historical data from an external system.
    """
    # Mock SLA policy and historical ticket count
    state["meta"]["sla_policy"] = "Standard-48h"
    state["meta"]["historical_tickets"] = state["meta"].get("historical_tickets", 0) + 1
    state["meta"]["received_utc"] = datetime.utcnow().isoformat()
    return state


def add_flags_calculations(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    COMMON: Compute SLA risk/priority flags.
    """
    flags = state.get("flags", {})
    p = state.get("priority", "Normal")
    flags["is_high_priority"] = p in ("High", "Urgent")
    # naive SLA risk if delivery delay mentioned
    flags["sla_risk"] = state.get("entities", {}).get("issue") == "delivery_delay"
    state["flags"] = flags
    return state


# -------------------------------
# STAGE 4: ASK (ATLAS)
# -------------------------------
def clarify_question(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Ask for missing critical fields (simulating human/CRM channel).
    """
    ents = state.get("entities", {})
    missing = []
    if not ents.get("order_id"): missing.append("order_id")
    if not ents.get("intent"):   missing.append("intent")

    if missing:
        state["clarifying_question"] = f"Please share missing details: {', '.join(missing)}."
    return state


# -------------------------------
# STAGE 5: WAIT (ATLAS + STATE MGMT)
# -------------------------------
def extract_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Simulate capturing a concise answer from a user/human channel.
    If you already have 'clarification_answer' in state, keep it.
    """
    if "clarification_answer" not in state:
        # stub a response so the demo can run deterministically
        state["clarification_answer"] = "Order id is #12345"
    return state


def store_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    STATE MGMT: Fold the answer back into entities.
    """
    ans = state.get("clarification_answer", "")
    m = re.search(r"#?\d+", ans)
    if m:
        state.setdefault("entities", {})["order_id"] = m.group().lstrip("#")
    state.setdefault("answers", []).append(ans)
    return state


# -------------------------------
# STAGE 6: RETRIEVE (ATLAS + STATE MGMT)
# -------------------------------
def knowledge_base_search(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: In practice pipeline handles this via Retriever shortcut,
    but we keep an ability with the same schema for completeness.
    """
    # no-op here; pipeline already injects kb_results
    return state


def store_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    STATE MGMT: Attach retrieved info into payload.
    Useful if you want to transform kb_results → kb_context, etc.
    """
    kb = state.get("kb_results", [])
    if kb:
        state["kb_hits"] = len(kb)
        # simple derived field for later scoring
        state["kb_top_answer"] = kb[0].get("answer")
    return state


# -------------------------------
# STAGE 7: DECIDE (NON-DETERMINISTIC)
# -------------------------------
def solution_evaluation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    COMMON: Score potential solutions 1-100.
    Deterministic heuristic: more KB hits → higher score.
    """
    hits = int(state.get("kb_hits") or len(state.get("kb_results", []) or []))
    # cap at 100, simple linear heuristic
    score = max(0, min(100, 60 + 10 * min(hits, 4)))
    state["solution_score"] = score
    state["decision"] = "resolve" if score >= 90 else "consider_escalation"
    return state


def escalation_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Assign to human if score < 90.
    """
    score = int(state.get("solution_score", 0))
    if score < 90:
        state["escalate_to"] = "human_agent"
        state["ticket_status"] = "needs_escalation"
    else:
        state["ticket_status"] = "resolved"
    return state


def update_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    STATE MGMT: Record decision outcomes in a stable structure.
    """
    state.setdefault("decision_log", []).append({
        "score": state.get("solution_score"),
        "decision": state.get("decision"),
        "ticket_status": state.get("ticket_status"),
        "ts": datetime.utcnow().isoformat(),
    })
    return state


# -------------------------------
# STAGE 8: UPDATE (ATLAS)
# -------------------------------
def update_ticket(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Simulate CRM status update.
    """
    state["ticket_id"] = state.get("ticket_id") or "TKT-0001"
    state["meta"]["last_update_utc"] = datetime.utcnow().isoformat()
    return state


def close_ticket(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Close ticket if resolved.
    """
    if state.get("ticket_status") == "resolved":
        state["ticket_closed"] = True
    return state


# -------------------------------
# STAGE 9: CREATE (COMMON)
# -------------------------------
def response_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    COMMON: Draft customer reply.
    Prefer KB answer if present; otherwise human-escalation message.
    """
    if state.get("ticket_status") == "resolved" and state.get("kb_top_answer"):
        msg = state["kb_top_answer"]
    elif state.get("kb_results"):
        msg = state["kb_results"][0].get("answer", "We found a solution for your request.")
    else:
        msg = "Thanks for the details. Your query has been assigned to a support specialist."
    state["response"] = msg
    return state


# -------------------------------
# STAGE 10: DO (ATLAS)
# -------------------------------
def execute_api_calls(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Trigger side effects (shipments, refunds, etc.). Mocked for demo.
    """
    state.setdefault("actions", []).append({
        "type": "noop_demo",
        "ts": datetime.utcnow().isoformat()
    })
    return state


def trigger_notifications(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ATLAS: Notify customer via outbox (mock).
    """
    logger.info("Notify: Ticket %s status %s → customer %s",
                state.get("ticket_id"), state.get("ticket_status"), state.get("email"))
    state["notified"] = True
    return state


# -------------------------------
# STAGE 11: COMPLETE
# -------------------------------
def output_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return final structured payload. The pipeline prints this.
    """
    return {
        "ticket_id": state.get("ticket_id"),
        "customer_name": state.get("customer_name"),
        "status": state.get("ticket_status"),
        "escalate_to": state.get("escalate_to"),
        "confidence": state.get("confidence"),
        "solution_score": state.get("solution_score"),
        "entities": state.get("entities"),
        "flags": state.get("flags"),
        "response": state.get("response"),
        "kb_hits": state.get("kb_hits", 0),
        "notified": state.get("notified", False),
    }


# ---------- OPTIONAL: Backward-compatibility aliases ----------
# If your YAML or old code ever references these older names,
# keep these thin wrappers so nothing breaks.
def ask_clarifying_question(state: Dict[str, Any]) -> Dict[str, Any]:
    return clarify_question(state)

def generate_customer_response(state: Dict[str, Any]) -> Dict[str, Any]:
    return response_generation(state)
