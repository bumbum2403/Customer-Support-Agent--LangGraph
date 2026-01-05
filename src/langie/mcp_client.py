# src/langie/mcp_client.py
import logging
from typing import Any, Dict

from .retriever import Retriever
from . import abilities  # <— use the local ability implementations

logger = logging.getLogger(__name__)
kb_retriever = Retriever()

class MCPClientError(RuntimeError):
    pass

# -------- COMMON SERVER ABILITIES --------
COMMON_ABILITY_MAP = {
    "parse_request_text": abilities.parse_request_text,
    "normalize_fields": abilities.normalize_fields,
    "add_flags_calculations": abilities.add_flags_calculations,
    "solution_evaluation": abilities.solution_evaluation,
    "response_generation": abilities.response_generation,
    "update_payload": abilities.update_payload,
    # alias
    "generate_customer_response": abilities.response_generation,
}

# -------- ATLAS SERVER ABILITIES --------
ATLAS_ABILITY_MAP = {
    "extract_entities": abilities.extract_entities,
    "enrich_records": abilities.enrich_records,
    "clarify_question": abilities.clarify_question,
    "extract_answer": abilities.extract_answer,
    "store_answer": abilities.store_answer,
    "store_data": abilities.store_data,
    "update_ticket": abilities.update_ticket,
    "close_ticket": abilities.close_ticket,
    "execute_api_calls": abilities.execute_api_calls,
    "trigger_notifications": abilities.trigger_notifications,
    # NOTE: knowledge_base_search handled via retriever fallback
}

# ----------------- HELPERS -----------------
def _kb_search(user_query: str, channel: str) -> Dict[str, Any]:
    """Shared knowledge base search logic."""
    if not user_query:
        logger.warning("%s: KB called with empty query", channel)
        return {"kb_results": []}
    logger.info("%s: KB search for %s", channel, user_query)
    results = kb_retriever.search(user_query)
    return {
        "kb_results": results,
        "kb_match_confidence": 0.85 if results else 0.0,  # fake confidence
        "kb_answer": results[0]["answer"] if results else "No match found.",
    }

# ----------------- COMMON -----------------
def call_common(ability_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if ability_name in ("faq_query", "knowledge_base_search"):
            return _kb_search(state.get("user_query") or state.get("query") or "", "COMMON")

        fn = COMMON_ABILITY_MAP.get(ability_name)
        if not fn:
            raise MCPClientError(f"COMMON ability '{ability_name}' is not implemented.")

        output = fn(state)
        if not isinstance(output, dict):
            logger.warning("COMMON ability '%s' returned non-dict, wrapping", ability_name)
            return {"result": output}
        return output
    except Exception as e:
        logger.exception("Error in call_common(%s): %s", ability_name, e)
        raise

# ----------------- ATLAS -----------------
def call_atlas(ability_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if ability_name in ("faq_query", "knowledge_base_search"):
            return _kb_search(state.get("user_query") or state.get("query") or "", "ATLAS")

        fn = ATLAS_ABILITY_MAP.get(ability_name)
        if not fn:
            raise MCPClientError(f"ATLAS ability '{ability_name}' is not implemented.")

        output = fn(state)
        if not isinstance(output, dict):
            logger.warning("ATLAS ability '%s' returned non-dict, wrapping", ability_name)
            return {"result": output}
        return output
    except Exception as e:
        logger.exception("Error in call_atlas(%s): %s", ability_name, e)
        raise
