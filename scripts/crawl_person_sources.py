#!/usr/bin/env python3
"""Crawl X and Weibo for configured people and import into knowledge/people/."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from person_crawl_agent.config import load_person_crawl_config
from person_crawl_agent.pipeline import run_person_crawl_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl X/Weibo via spider and import Markdown into knowledge/people/<person_id>/.",
    )
    parser.add_argument("person_id", nargs="?", help="Person folder name, e.g. example_person")
    parser.add_argument("--list", action="store_true", help="List configured person IDs.")
    parser.add_argument("--platform", choices=["x", "weibo"], action="append", help="Limit platforms.")
    parser.add_argument("--dry-run", action="store_true", help="Validate spider targets only.")
    parser.add_argument("--skip-crawl", action="store_true", help="Import from existing spider outputs.")
    parser.add_argument("--skip-import", action="store_true", help="Crawl only; do not import Markdown.")
    parser.add_argument("--ingest-rag", action="store_true", help="Rebuild RAG index after import.")
    parser.add_argument(
        "--embedding-provider",
        default="keyword",
        help="RAG embedding provider when --ingest-rag is set.",
    )
    parser.add_argument("--include-retweets", action="store_true", help="Keep retweets during import.")
    parser.add_argument("--min-length-x", type=int, default=300)
    parser.add_argument("--min-length-weibo", type=int, default=80)
    parser.add_argument("--lang", default="zh", help="Language filter for X export; empty disables.")
    parser.add_argument(
        "--config",
        default="",
        help="Path to person crawl registry YAML. Defaults to config/person_crawl.yaml or the example file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = args.config or None
    config = load_person_crawl_config(config_path, root_dir=PROJECT_ROOT)

    if args.list:
        for person_id in config.list_person_ids():
            person = config.get_person(person_id)
            platforms = []
            if person.x is not None:
                platforms.append(f"x=@{person.x.payload.get('user')}")
            if person.weibo is not None:
                platforms.append(f"weibo={person.weibo.payload.get('id')}")
            print(f"{person_id}: {', '.join(platforms) or '(no targets)'}")
        return 0

    if not args.person_id:
        parser.print_help()
        print("\nConfigured people:")
        for person_id in config.list_person_ids():
            print(f"  - {person_id}")
        return 0

    platforms = set(args.platform) if args.platform else None
    lang = args.lang or None

    try:
        result = run_person_crawl_pipeline(
            args.person_id,
            config=config,
            root_dir=PROJECT_ROOT,
            platforms=platforms,
            dry_run=args.dry_run,
            skip_crawl=args.skip_crawl,
            skip_import=args.skip_import,
            ingest_rag=args.ingest_rag,
            embedding_provider=args.embedding_provider,
            originals_only=not args.include_retweets,
            min_length_x=args.min_length_x,
            min_length_weibo=args.min_length_weibo,
            lang=lang,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Import subprocess failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1

    for spider_result in result.spider_results:
        status = "ok" if spider_result.ok else "failed"
        print(f"[{status}] {spider_result.platform}: {spider_result.message}")
        print(f"  output_dir: {spider_result.output_dir}")

    for path in result.imported_files[:10]:
        print(f"imported: {path}")
    if len(result.imported_files) > 10:
        print(f"... and {len(result.imported_files) - 10} more files")

    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if result.rag_ingest:
        print("rag ingest:")
        for kind, stats in result.rag_ingest.items():
            print(f"  {kind}: {stats.get('chunks_written', 0)} chunks")

    if args.dry_run:
        return 0 if all(item.ok for item in result.spider_results) else 1
    if result.warnings and not result.imported_files:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())