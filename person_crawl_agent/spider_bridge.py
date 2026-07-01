from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from person_crawl_agent.config import PersonCrawlConfig, PersonTarget, PlatformTarget


@dataclass(frozen=True)
class SpiderRunResult:
    platform: str
    ok: bool
    message: str
    output_dir: Path
    details: dict[str, Any]


def _ensure_spider_importable(spider_base_path: Path) -> None:
    base = str(spider_base_path.resolve())
    if base not in sys.path:
        sys.path.insert(0, base)


def _run_platform(
    *,
    spider_base_path: Path,
    platform: str,
    target: PlatformTarget,
    dry_run: bool,
) -> SpiderRunResult:
    _ensure_spider_importable(spider_base_path)
    from spider_core.api import SpiderClient, SpiderRequest

    client = SpiderClient(base_path=spider_base_path)
    runner = client.runners.get(platform)
    if runner is None:
        raise ValueError(f"Unsupported spider platform: {platform}")

    config = client.get_config(platform)
    request = SpiderRequest(
        platform=platform,
        config=config,
        targets=[target.payload],
        base_path=spider_base_path,
        dry_run=dry_run,
    )
    result = runner.run(request)
    output_key = "output_dir"
    output_dir = Path(str(result.details.get(output_key) or config.get(output_key) or spider_base_path))
    return SpiderRunResult(
        platform=platform,
        ok=result.ok,
        message=result.message,
        output_dir=output_dir.expanduser().resolve(),
        details=dict(result.details),
    )


def run_spider_for_person(
    config: PersonCrawlConfig,
    person: PersonTarget,
    *,
    platforms: set[str] | None = None,
    dry_run: bool = False,
) -> list[SpiderRunResult]:
    if not config.spider_base_path.exists():
        raise FileNotFoundError(
            f"Spider project not found at {config.spider_base_path}. "
            "Set SPIDER_BASE_PATH in .env or copy config/person_crawl.example.yaml to config/person_crawl.yaml."
        )

    selected = platforms or {"x", "weibo"}
    results: list[SpiderRunResult] = []

    if "x" in selected and person.x is not None:
        results.append(
            _run_platform(
                spider_base_path=config.spider_base_path,
                platform="x",
                target=person.x,
                dry_run=dry_run,
            )
        )
    if "weibo" in selected and person.weibo is not None:
        results.append(
            _run_platform(
                spider_base_path=config.spider_base_path,
                platform="weibo",
                target=person.weibo,
                dry_run=dry_run,
            )
        )

    if not results:
        raise ValueError(
            f"No crawl targets configured for {person.person_id} on platforms: {sorted(selected)}"
        )
    return results