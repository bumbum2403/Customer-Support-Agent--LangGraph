import yaml
from pathlib import Path
from typing import Dict, Any
from .logger import get_logger
from .mcp_client import call_common, call_atlas
from .models import InputPayload
from .retriever import Retriever

logger = get_logger(__name__)

# Global KB retriever instance
kb_retriever = Retriever()

class LangGraphAgent:
    """
    Orchestrates customer-support pipeline execution based on stages.yaml.
    Each stage defines abilities executed either deterministically,
    conditionally, or non-deterministically (decision-making).
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = yaml.safe_load(Path(config_path).read_text())
        self.state: Dict[str, Any] = {"logs": []}
        logger.info("⚙️ Loaded pipeline config from %s", config_path)

    def validate_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input payload against schema."""
        validated = InputPayload.model_validate(payload)
        return validated.model_dump()

    def run(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run the end-to-end pipeline for a given payload."""
        try:
            validated = self.validate_input(input_payload)
        except Exception as e:
            logger.error("❌ Input validation failed: %s", e)
            raise
        self.state.update(validated)
        self._log("run_started", {
            "input_summary": {k: self.state.get(k) for k in ['ticket_id', 'customer_name']}
        })

        for stage in self.config.get("stages", []):
            name = stage["name"]
            mode = stage.get("mode", "deterministic")
            self._log("stage_start", {"stage": name, "mode": mode})

            if mode == "deterministic":
                for ability in stage.get("abilities", []):
                    self._execute_ability(name, ability)

            elif mode == "conditional":
                cond = stage.get("condition", "")
                if self._eval_condition(cond):
                    for ability in stage.get("abilities", []):
                        self._execute_ability(name, ability)
                else:
                    logger.info("⏩ Skipping conditional stage %s (cond=%s)", name, cond)

            elif mode == "non-deterministic":
                # Run evaluation first
                for ability in stage.get("abilities", []):
                    if ability["name"] == "solution_evaluation":
                        self._execute_ability(name, ability)
                        break
                score = self.state.get("solution_score", 0)

                # Escalation if score < threshold
                if score < 90:
                    for ability in stage.get("abilities", []):
                        if ability["name"] == "escalation_decision":
                            self._execute_ability(name, ability)

                # Always update payload if configured
                for ability in stage.get("abilities", []):
                    if ability["name"] == "update_payload":
                        self._execute_ability(name, ability)

            else:
                logger.warning("⚠️ Unknown stage mode %s for stage %s", mode, name)

            self._log("stage_end", {"stage": name})

        self._log("run_completed", {"final_keys": list(self.state.keys())})
        return self.state

    def _execute_ability(self, stage_name: str, ability: Dict[str, Any]) -> Any:
        """Execute an ability via MCP client (COMMON or ATLAS)."""
        name = ability["name"]
        server = ability.get("server", "COMMON")
        self._log("ability_start", {"stage": stage_name, "ability": name, "server": server})

        try:
            if name == "knowledge_base_search":
                query = self.state.get("query", "")
                kb_results = kb_retriever.search(query)
                self.state["kb_results"] = kb_results
                result = kb_results
            else:
                if server.upper() == "ATLAS":
                    result = call_atlas(name, self.state)
                else:
                    result = call_common(name, self.state)
        except Exception as e:
            logger.exception("❌ Ability %s failed in stage %s", name, stage_name)
            result = {"error": str(e)}

        # merge results into state
        if isinstance(result, dict):
            for k, v in result.items():
                if k in self.state and isinstance(self.state[k], dict) and isinstance(v, dict):
                    self.state[k].update(v)  # deep merge
                else:
                    self.state[k] = v
        else:
            self.state[f"{stage_name}_{name}"] = result or "done"

        self._log("ability_end", {
            "stage": stage_name,
            "ability": name,
            "result_summary": self._summarize(result)
        })
        return result

    def _eval_condition(self, cond: str) -> bool:
        """Evaluate conditional stage execution rules."""
        if not cond:
            return True
        cond = cond.lower()
        try:
            if cond == "missing_entities":
                return not self.state.get("entities")
            if cond == "low_confidence":
                return self.state.get("solution_score", 100) < 80
        except Exception:
            return False
        return False

    def _log(self, event: str, payload: Dict[str, Any]):
        """Log structured event to both state and logger."""
        logger.info("%s %s", event, payload)
        self.state.setdefault("logs", []).append({"event": event, "payload": payload})

    def _summarize(self, result: Any):
        """Summarize results to avoid bloating logs."""
        if isinstance(result, dict):
            return {k: (v if isinstance(v, (int, str, bool)) else str(type(v)))
                    for k, v in list(result.items())[:5]}
        return result
