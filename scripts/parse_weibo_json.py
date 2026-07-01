#!/usr/bin/env python3
"""Parse spider_weibo JSON exports for viewing, filtering, and RAG corpus export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class WeiboPost:
    post_id: str
    publish_time: str
    content: str
    is_retweet: bool
    user_id: str
    raw: dict[str, Any]

    @property
    def clean_content(self) -> str:
        text = self.content.strip()
        if self.is_retweet and "转发内容:" in text:
            text = text.split("转发内容:", 1)[-1].strip()
        return text


def _load_posts(path: Path) -> tuple[dict[str, Any], list[WeiboPost]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")

    posts_raw = data.get("weibo", [])
    if not isinstance(posts_raw, list):
        raise ValueError(f"{path} must contain a 'weibo' array")

    posts: list[WeiboPost] = []
    for item in posts_raw:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "")
        posts.append(
            WeiboPost(
                post_id=str(item.get("id") or ""),
                publish_time=str(item.get("publish_time") or ""),
                content=content,
                is_retweet=bool(item.get("original") is False or content.startswith("转发理由:")),
                user_id=str(item.get("user_id") or ""),
                raw=item,
            )
        )
    return data, posts


def filter_posts(
    posts: Iterable[WeiboPost],
    *,
    originals_only: bool = False,
    min_length: int = 0,
    query: str | None = None,
) -> list[WeiboPost]:
    results: list[WeiboPost] = []
    query_lower = query.lower() if query else None
    for post in posts:
        if originals_only and post.is_retweet:
            continue
        if len(post.clean_content) < min_length:
            continue
        if query_lower and query_lower not in post.clean_content.lower():
            continue
        results.append(post)
    return results


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text.strip().lower())
    slug = slug.strip("_")
    return (slug or "post")[:max_len].rstrip("_")


def _format_post_markdown(post: WeiboPost) -> str:
    title = post.clean_content.splitlines()[0][:80]
    lines = [
        f"# {title}",
        "",
        f"- post_id: {post.post_id}",
        f"- publish_time: {post.publish_time}",
        f"- is_retweet: {post.is_retweet}",
        "",
        post.clean_content,
        "",
    ]
    return "\n".join(lines)


def export_markdown(
    posts: list[WeiboPost],
    output_dir: Path,
    *,
    person_name: str,
    combined: bool = True,
    split_long_posts: bool = True,
    long_post_min_length: int = 300,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files: list[str] = []

    if combined:
        combined_path = output_dir / "corpus.md"
        sections = [
            f"# {person_name} Weibo Corpus",
            "",
            f"Exported at: {datetime.now().isoformat(timespec='seconds')}",
            f"Total posts: {len(posts)}",
            "",
        ]
        for index, post in enumerate(posts, start=1):
            sections.append(f"## Post {index}")
            sections.append("")
            sections.append(
                _format_post_markdown(post).removeprefix(
                    f"# {post.clean_content.splitlines()[0][:80]}\n\n"
                )
            )
        combined_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")
        exported_files.append(str(combined_path))

    if split_long_posts:
        long_dir = output_dir / "long_posts"
        long_dir.mkdir(parents=True, exist_ok=True)
        for post in [item for item in posts if len(item.clean_content) >= long_post_min_length]:
            date_prefix = post.publish_time[:10] if post.publish_time else "unknown"
            filename = f"{date_prefix}_{post.post_id}_{_slugify(post.clean_content.splitlines()[0])}.md"
            path = long_dir / filename
            path.write_text(_format_post_markdown(post) + "\n", encoding="utf-8")
            exported_files.append(str(path))

    return {
        "output_dir": str(output_dir),
        "files_written": len(exported_files),
        "files": exported_files,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse spider_weibo JSON for corpus export.")
    parser.add_argument("input", nargs="?", help="Path to <uid>.json from spider_weibo.")
    parser.add_argument(
        "--command",
        choices=["stats", "preview", "export-md"],
        default="stats",
    )
    parser.add_argument("--person-name", default="person", help="Person folder name under knowledge/people/.")
    parser.add_argument("--display-name", default="", help="Display name for corpus.md title.")
    parser.add_argument("--originals-only", action="store_true")
    parser.add_argument("--min-length", type=int, default=0)
    parser.add_argument("--query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--no-combined", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 0

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"File not found: {input_path}", file=sys.stderr)
        return 1

    _, posts = _load_posts(input_path)
    filtered = filter_posts(
        posts,
        originals_only=args.originals_only,
        min_length=args.min_length,
        query=args.query,
    )

    if args.command == "stats":
        print(f"Total posts: {len(posts)}")
        print(f"Filtered posts: {len(filtered)}")
        return 0

    if args.command == "preview":
        for index, post in enumerate(filtered[: args.limit], start=1):
            preview = post.clean_content.replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:220] + "..."
            print(f"[{index}] {post.publish_time} id={post.post_id}")
            print(f"    {preview}")
            print()
        return 0

    person_id = args.person_name
    display_name = args.display_name or person_id
    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else PROJECT_ROOT / "knowledge" / "people" / person_id / "weibo"
    )
    result = export_markdown(
        filtered,
        output_dir,
        person_name=display_name,
        combined=not args.no_combined,
    )
    print(f"Exported {result['files_written']} files to {result['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())