#!/usr/bin/env python3
"""Link or copy external Markdown sources into knowledge/people/<person_id>/<kind>/."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from rag.config import PERSON_SOURCE_KINDS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PEOPLE_DIR = PROJECT_ROOT / "knowledge" / "people"


def _target_dir(person_id: str, kind: str) -> Path:
    if kind not in PERSON_SOURCE_KINDS:
        supported = ", ".join(sorted(PERSON_SOURCE_KINDS))
        raise ValueError(f"Unsupported source kind '{kind}'. Use one of: {supported}")
    return DEFAULT_PEOPLE_DIR / person_id / kind


def _import_path(source: Path, target_dir: Path, *, mode: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source.name
    if destination.exists() or destination.is_symlink():
        destination.unlink()

    source = source.expanduser().resolve()
    if mode == "symlink":
        destination.symlink_to(source)
    elif mode == "copy":
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    else:
        raise ValueError(f"Unsupported import mode: {mode}")
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import external Markdown sources into a person's knowledge folder.",
    )
    parser.add_argument("person_id", help="Person folder name, e.g. desmond_shum")
    parser.add_argument(
        "kind",
        choices=sorted(PERSON_SOURCE_KINDS),
        help="Source category: book, x, news, report",
    )
    parser.add_argument("source", help="External file or directory to import")
    parser.add_argument(
        "--mode",
        choices=["symlink", "copy"],
        default="symlink",
        help="symlink keeps the original path; copy duplicates files locally.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1

    try:
        destination = _import_path(source, _target_dir(args.person_id, args.kind), mode=args.mode)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Imported {source} -> {destination}")
    print(
        "Rebuild RAG index:\n"
        f"  python -m rag.ingest --person-name {args.person_id} --embedding-provider keyword"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())