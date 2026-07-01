from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from person_crawl_agent.config import PersonCrawlConfig, PersonTarget, load_person_crawl_config
from person_crawl_agent.locate import find_tweets_jsonl, find_weibo_json
from person_crawl_agent.spider_bridge import SpiderRunResult, run_spider_for_person

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CrawlImportResult:
    person_id: str
    dry_run: bool
    spider_results: list[SpiderRunResult] = field(default_factory=list)
    imported_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rag_ingest: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        if self.dry_run:
            return bool(self.spider_results)
        return bool(self.imported_files) or bool(self.warnings)


def _person_knowledge_dir(root_dir: Path, person_id: str, kind: str) -> Path:
    return root_dir / "knowledge" / "people" / person_id / kind


def _import_x_corpus(
    *,
    tweets_jsonl: Path,
    person: PersonTarget,
    root_dir: Path,
    originals_only: bool,
    min_length: int,
    lang: str | None,
) -> list[Path]:
    output_dir = _person_knowledge_dir(root_dir, person.person_id, "x")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "parse_twitter_jsonl.py"),
        str(tweets_jsonl),
        "--command",
        "export-md",
        "--person-name",
        person.person_id,
        "--display-name",
        person.display_name,
        "--output-dir",
        str(output_dir),
        "--min-length",
        str(min_length),
    ]
    if originals_only:
        cmd.append("--originals-only")
    if lang:
        cmd.extend(["--lang", lang])

    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    return sorted(path for path in output_dir.rglob("*.md") if path.is_file())


def _import_weibo_corpus(
    *,
    weibo_json: Path,
    person: PersonTarget,
    root_dir: Path,
    originals_only: bool,
    min_length: int,
) -> list[Path]:
    output_dir = _person_knowledge_dir(root_dir, person.person_id, "weibo")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "parse_weibo_json.py"),
        str(weibo_json),
        "--command",
        "export-md",
        "--person-name",
        person.person_id,
        "--display-name",
        person.display_name,
        "--output-dir",
        str(output_dir),
        "--min-length",
        str(min_length),
    ]
    if originals_only:
        cmd.append("--originals-only")

    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    return sorted(path for path in output_dir.rglob("*.md") if path.is_file())


def _maybe_ingest_rag(
    *,
    person_id: str,
    root_dir: Path,
    source_kinds: set[str],
    embedding_provider: str,
) -> dict[str, Any]:
    from rag.ingest import ingest_corpus

    stats: dict[str, Any] = {}
    for kind in sorted(source_kinds):
        stats[kind] = ingest_corpus(
            person_id,
            knowledge_scope="people",
            root_dir=root_dir,
            embedding_provider=embedding_provider,
            reset=False,
            source_kinds={kind},
        )
    return stats


def run_person_crawl_pipeline(
    person_id: str,
    *,
    config: PersonCrawlConfig | None = None,
    root_dir: Path | str | None = None,
    platforms: set[str] | None = None,
    dry_run: bool = False,
    skip_crawl: bool = False,
    skip_import: bool = False,
    ingest_rag: bool = False,
    embedding_provider: str = "keyword",
    originals_only: bool = True,
    min_length_x: int = 300,
    min_length_weibo: int = 80,
    lang: str | None = "zh",
) -> CrawlImportResult:
    root = Path(root_dir or PROJECT_ROOT).expanduser().resolve()
    crawl_config = config or load_person_crawl_config(root_dir=root)
    person = crawl_config.get_person(person_id)
    result = CrawlImportResult(person_id=person_id, dry_run=dry_run)

    search_roots = [
        item.output_dir
        for item in (result.spider_results if skip_crawl else [])
    ]

    if not skip_crawl:
        result.spider_results = run_spider_for_person(
            crawl_config,
            person,
            platforms=platforms,
            dry_run=dry_run,
        )
        search_roots = [item.output_dir for item in result.spider_results]

    if dry_run or skip_import:
        return result

    imported_kinds: set[str] = set()

    if (platforms is None or "x" in platforms) and person.x is not None:
        handle = str(person.x.payload.get("user") or "")
        tweets_jsonl = find_tweets_jsonl(
            spider_base_path=crawl_config.spider_base_path,
            handle=handle,
            search_roots=search_roots,
        )
        if tweets_jsonl is None:
            result.warnings.append(f"X tweets.jsonl not found for @{handle}")
        else:
            result.imported_files.extend(
                _import_x_corpus(
                    tweets_jsonl=tweets_jsonl,
                    person=person,
                    root_dir=root,
                    originals_only=originals_only,
                    min_length=min_length_x,
                    lang=lang,
                )
            )
            imported_kinds.add("x")

    if (platforms is None or "weibo" in platforms) and person.weibo is not None:
        user_id = str(person.weibo.payload.get("id") or "")
        display_name = str(person.weibo.payload.get("name") or person.display_name)
        weibo_json = find_weibo_json(
            spider_base_path=crawl_config.spider_base_path,
            user_id=user_id,
            display_name=display_name,
            search_roots=search_roots,
        )
        if weibo_json is None:
            result.warnings.append(f"Weibo JSON not found for uid={user_id}")
        else:
            result.imported_files.extend(
                _import_weibo_corpus(
                    weibo_json=weibo_json,
                    person=person,
                    root_dir=root,
                    originals_only=originals_only,
                    min_length=min_length_weibo,
                )
            )
            imported_kinds.add("weibo")

    if ingest_rag and imported_kinds:
        result.rag_ingest = _maybe_ingest_rag(
            person_id=person_id,
            root_dir=root,
            source_kinds=imported_kinds,
            embedding_provider=embedding_provider,
        )

    return result