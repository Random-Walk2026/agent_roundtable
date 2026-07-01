from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_spider_settings(spider_base_path: Path) -> dict[str, Any]:
    settings_path = spider_base_path / "settings.json"
    if not settings_path.exists():
        return {}
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _platform_output_dir(spider_base_path: Path, platform: str) -> Path:
    settings = _read_spider_settings(spider_base_path)
    section = settings.get(platform, {})
    if isinstance(section, dict):
        configured = section.get("output_dir")
        if configured:
            return Path(str(configured)).expanduser().resolve()
    return (spider_base_path / "downloads" / platform).resolve()


def find_tweets_jsonl(
    *,
    spider_base_path: Path,
    handle: str,
    search_roots: list[Path] | None = None,
) -> Path | None:
    handle = handle.lstrip("@")
    candidates = [
        _platform_output_dir(spider_base_path, "x") / "twitter" / handle / "tweets.jsonl",
        _platform_output_dir(spider_base_path, "x") / handle / "tweets.jsonl",
    ]
    if search_roots:
        for root in search_roots:
            candidates.extend(
                [
                    root / "twitter" / handle / "tweets.jsonl",
                    root / handle / "tweets.jsonl",
                ]
            )

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    for root in [_platform_output_dir(spider_base_path, "x"), *(search_roots or [])]:
        if not root.exists():
            continue
        matches = sorted(root.rglob("tweets.jsonl"))
        for match in matches:
            if handle.lower() in {part.lower() for part in match.parts}:
                return match.resolve()
    return None


def find_weibo_json(
    *,
    spider_base_path: Path,
    user_id: str,
    display_name: str | None = None,
    search_roots: list[Path] | None = None,
) -> Path | None:
    output_dir = _platform_output_dir(spider_base_path, "weibo")
    candidates: list[Path] = [output_dir / f"{user_id}.json"]
    if display_name:
        candidates.append(output_dir / display_name / f"{user_id}.json")

    if search_roots:
        for root in search_roots:
            candidates.append(root / f"{user_id}.json")
            if display_name:
                candidates.append(root / display_name / f"{user_id}.json")

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    search_bases = [output_dir, *(search_roots or [])]
    for root in search_bases:
        if not root.exists():
            continue
        for match in sorted(root.rglob(f"{user_id}.json")):
            return match.resolve()
    return None