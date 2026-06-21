from __future__ import annotations

import argparse

from src.graph import run_roundtable
from src.llm import create_llm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a persona-based agent roundtable.")
    parser.add_argument("--topic", required=True, help="Discussion topic")
    parser.add_argument("--council", default="experts", help="Council config name")
    parser.add_argument("--rounds", type=int, default=2, help="Number of discussion rounds")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "mock", "gemini", "openai", "openrouter", "deepseek"],
        help="LLM provider. auto uses persona/council config or falls back to mock.",
    )
    parser.add_argument("--model", default=None, help="Provider model override")
    parser.add_argument("--mock", action="store_true", help="Force deterministic mock LLM")
    parser.add_argument("--output-dir", default="logs", help="Markdown log output directory")
    parser.add_argument(
        "--agent-llm-config",
        default=None,
        help="JSON file for per-agent LLM config. Defaults to configs/agent_llms.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mock:
        llm = create_llm(provider="mock", model=args.model)
    elif args.provider == "auto":
        llm = None
    else:
        llm = create_llm(provider=args.provider, model=args.model)
    result = run_roundtable(
        topic=args.topic,
        council_name=args.council,
        rounds=args.rounds,
        llm=llm,
        output_dir=args.output_dir,
        agent_llm_config_path=args.agent_llm_config,
    )
    print(result["final_summary"])
    print(f"\nLog saved to: {result['log_path']}")


if __name__ == "__main__":
    main()
