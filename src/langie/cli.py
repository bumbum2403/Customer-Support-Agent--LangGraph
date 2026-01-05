import argparse
import json
from .logger import get_logger
from pathlib import Path
from .pipeline import LangGraphAgent

logging = get_logger(__name__)

def run(args):
    """Run the Langie bot with either sample or provided JSON input."""
    sample = {
        "customer_name": "Alice",
        "email": "alice@example.com",
        "query": "My order #123 hasn’t arrived",
        "priority": "High",
        "ticket_id": "TKT-5678",
    }
    if args.input:
        sample = json.loads(Path(args.input).read_text())

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    agent = LangGraphAgent(config_path=args.config)
    final = agent.run(sample)

    print("\n--- Final payload ---")
    print(json.dumps(final, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="langie", description="Langie CLI - Customer Support Bot"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the Langie bot")
    run_parser.add_argument(
        "--config", "-c", default="config/stages.yaml", help="Path to stages YAML"
    )
    run_parser.add_argument(
        "--input", "-i", default=None, help="Path to JSON file with input payload (optional)"
    )
    run_parser.add_argument(
        "--debug", action="store_true", default=False, help="Enable debug logging"
    )
    run_parser.set_defaults(func=run)

    args = parser.parse_args()
    args.func(args)
