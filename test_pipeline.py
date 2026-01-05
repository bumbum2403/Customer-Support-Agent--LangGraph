# test_pipeline.py
import json
from pathlib import Path
import importlib
import logging
from src.langie.pipeline import LangGraphAgent
import src.langie.abilities as abilities

# -------------------------------
# Setup logging
# -------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "pipeline_test.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------------
# Helper to patch only missing abilities
# -------------------------------
def mock_missing_abilities():
    """Patch only missing abilities so existing ones are preserved."""
    def dummy_fn(state):
        logger.info("Dummy ability called")
        return state

    missing = []
    for fname in ["store_data", "output_payload"]:
        if not hasattr(abilities, fname):
            setattr(abilities, fname, dummy_fn)
            missing.append(fname)
    if missing:
        logger.warning(f"Patched missing abilities: {missing}")

# -------------------------------
# Smoke Test Function
# -------------------------------
def test_pipeline_smoke(sample_path="sample.json", config_path="config/stages.yaml"):
    # Reload abilities to ensure latest code is loaded
    importlib.reload(abilities)

    # Patch only missing abilities
    mock_missing_abilities()

    # Load sample input
    if not Path(sample_path).exists():
        raise FileNotFoundError(f"Sample file not found: {sample_path}")
    sample = json.loads(Path(sample_path).read_text())

    # Initialize pipeline agent
    agent = LangGraphAgent(config_path=config_path)

    # Ensure state defaults to prevent KeyErrors
    agent.state.setdefault("entities", {})
    agent.state.setdefault("meta", {})
    agent.state.setdefault("flags", {})

    # Run pipeline
    logger.info("Starting pipeline run for ticket_id=%s", sample.get("ticket_id"))
    output = agent.run(sample)
    logger.info("Pipeline run completed: %s", output)

    # Debug output
    print("\n===== PIPELINE OUTPUT =====")
    for k, v in output.items():
        print(f"{k}: {v}")
    print("==========================\n")

    # Basic assertions
    assert output.get("ticket_id") == sample.get("ticket_id"), "Ticket ID mismatch"
    assert "response" in output, "Response missing"
    assert "solution_score" in output, "Solution score missing"

    logger.info("✅ Pipeline smoke test passed for ticket_id=%s", sample.get("ticket_id"))
    return output

# -------------------------------
# CLI Execution
# -------------------------------
if __name__ == "__main__":
    result = test_pipeline_smoke()
