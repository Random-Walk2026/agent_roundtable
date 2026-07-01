#!/usr/bin/env python3
"""Parse Twitter/X tweets.jsonl exports for viewing, filtering, and RAG corpus export."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PERSON_ID = "example_person"
DEFAULT_DISPLAY_NAME = "Example Person"

RT_PREFIX_RE = re.compile(r"^RT @\w+:\s*", re.MULTILINE)


@dataclass(frozen=True)
class Tweet:
    tweet_id: int
    date: str
    content: str
    lang: str
    favorite_count: int
    retweet_count: int
    reply_count: int
    view_count: int
    is_retweet: bool
    is_reply: bool
    is_quote: bool
    author_handle: str
    author_name: str
    user_handle: str
    user_name: str
    raw: dict[str, Any]

    @property
    def engagement(self) -> int:
        return self.favorite_count + self.retweet_count * 2 + self.reply_count

    @property
    def clean_content(self) -> str:
        text = self.content.strip()
        text = RT_PREFIX_RE.sub("", text)
        return text.strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _user_field(record: dict[str, Any], field: str, fallback: str = "") -> str:
    user = record.get("user") or {}
    if not isinstance(user, dict):
        return fallback
    return str(user.get(field) or fallback)


def _author_field(record: dict[str, Any], field: str, fallback: str = "") -> str:
    author = record.get("author") or {}
    if not isinstance(author, dict):
        return fallback
    return str(author.get(field) or fallback)


def load_tweets(path: Path) -> list[Tweet]:
    tweets: list[Tweet] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_number} in {path} must be a JSON object.")

            content = str(record.get("content") or "")
            retweet_id = _safe_int(record.get("retweet_id"))
            reply_id = _safe_int(record.get("reply_id"))
            quote_id = _safe_int(record.get("quote_id"))
            is_retweet = retweet_id > 0 or content.startswith("RT @")

            tweets.append(
                Tweet(
                    tweet_id=_safe_int(record.get("tweet_id")),
                    date=str(record.get("date") or ""),
                    content=content,
                    lang=str(record.get("lang") or ""),
                    favorite_count=_safe_int(record.get("favorite_count")),
                    retweet_count=_safe_int(record.get("retweet_count")),
                    reply_count=_safe_int(record.get("reply_count")),
                    view_count=_safe_int(record.get("view_count")),
                    is_retweet=is_retweet,
                    is_reply=reply_id > 0,
                    is_quote=quote_id > 0,
                    author_handle=_author_field(record, "name"),
                    author_name=_author_field(record, "nick"),
                    user_handle=_user_field(record, "name"),
                    user_name=_user_field(record, "nick"),
                    raw=record,
                )
            )
    return tweets


def filter_tweets(
    tweets: Iterable[Tweet],
    *,
    originals_only: bool = False,
    min_length: int = 0,
    langs: set[str] | None = None,
    handles: set[str] | None = None,
    query: str | None = None,
) -> list[Tweet]:
    results: list[Tweet] = []
    query_lower = query.lower() if query else None
    for tweet in tweets:
        if originals_only and tweet.is_retweet:
            continue
        if len(tweet.clean_content) < min_length:
            continue
        if langs and tweet.lang not in langs:
            continue
        if handles:
            if tweet.user_handle not in handles and tweet.author_handle not in handles:
                continue
        if query_lower and query_lower not in tweet.clean_content.lower():
            continue
        results.append(tweet)
    return results


def tweet_stats(tweets: list[Tweet]) -> dict[str, Any]:
    langs = Counter(tweet.lang for tweet in tweets)
    lengths = [len(tweet.clean_content) for tweet in tweets]
    dates = [tweet.date for tweet in tweets if tweet.date]
    return {
        "total": len(tweets),
        "originals": sum(1 for tweet in tweets if not tweet.is_retweet),
        "retweets": sum(1 for tweet in tweets if tweet.is_retweet),
        "replies": sum(1 for tweet in tweets if tweet.is_reply),
        "langs": langs.most_common(),
        "avg_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "date_range": (min(dates), max(dates)) if dates else ("", ""),
        "user_handles": Counter(tweet.user_handle for tweet in tweets).most_common(3),
    }


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text.strip().lower())
    slug = slug.strip("_")
    if not slug:
        slug = "tweet"
    return slug[:max_len].rstrip("_")


def _format_tweet_markdown(tweet: Tweet) -> str:
    title = tweet.clean_content.splitlines()[0][:80]
    lines = [
        f"# {title}",
        "",
        f"- tweet_id: {tweet.tweet_id}",
        f"- date: {tweet.date}",
        f"- lang: {tweet.lang}",
        f"- user: @{tweet.user_handle} ({tweet.user_name})",
        f"- favorites: {tweet.favorite_count}",
        f"- retweets: {tweet.retweet_count}",
        f"- replies: {tweet.reply_count}",
        f"- views: {tweet.view_count}",
        "",
        tweet.clean_content,
        "",
    ]
    return "\n".join(lines)


def export_markdown(
    tweets: list[Tweet],
    output_dir: Path,
    *,
    person_id: str = DEFAULT_PERSON_ID,
    display_name: str = DEFAULT_DISPLAY_NAME,
    combined: bool = True,
    split_long_posts: bool = True,
    long_post_min_length: int = 800,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files: list[str] = []

    if combined:
        combined_path = output_dir / "corpus.md"
        sections = [
            f"# {display_name} X/Twitter Corpus",
            "",
            f"Exported at: {datetime.now().isoformat(timespec='seconds')}",
            f"Total tweets: {len(tweets)}",
            "",
        ]
        for index, tweet in enumerate(tweets, start=1):
            sections.append(f"## Post {index}")
            sections.append("")
            sections.append(_format_tweet_markdown(tweet).removeprefix(f"# {tweet.clean_content.splitlines()[0][:80]}\n\n"))
        combined_path.write_text("\n".join(sections).strip() + "\n", encoding="utf-8")
        exported_files.append(str(combined_path))

    if split_long_posts:
        long_dir = output_dir / "long_posts"
        long_dir.mkdir(parents=True, exist_ok=True)
        long_posts = [tweet for tweet in tweets if len(tweet.clean_content) >= long_post_min_length]
        for tweet in long_posts:
            first_line = tweet.clean_content.splitlines()[0][:80]
            filename = f"{tweet.date[:10]}_{tweet.tweet_id}_{_slugify(first_line)}.md"
            path = long_dir / filename
            path.write_text(_format_tweet_markdown(tweet) + "\n", encoding="utf-8")
            exported_files.append(str(path))

    return {
        "output_dir": str(output_dir),
        "files_written": len(exported_files),
        "files": exported_files,
    }


def export_csv(tweets: list[Tweet], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tweet_id",
                "date",
                "lang",
                "user_handle",
                "favorite_count",
                "retweet_count",
                "reply_count",
                "view_count",
                "is_retweet",
                "content",
            ],
        )
        writer.writeheader()
        for tweet in tweets:
            writer.writerow(
                {
                    "tweet_id": tweet.tweet_id,
                    "date": tweet.date,
                    "lang": tweet.lang,
                    "user_handle": tweet.user_handle,
                    "favorite_count": tweet.favorite_count,
                    "retweet_count": tweet.retweet_count,
                    "reply_count": tweet.reply_count,
                    "view_count": tweet.view_count,
                    "is_retweet": tweet.is_retweet,
                    "content": tweet.clean_content,
                }
            )


def print_stats(tweets: list[Tweet]) -> None:
    stats = tweet_stats(tweets)
    print(f"Total tweets:      {stats['total']}")
    print(f"Original posts:    {stats['originals']}")
    print(f"Retweets:          {stats['retweets']}")
    print(f"Replies:           {stats['replies']}")
    print(f"Date range:        {stats['date_range'][0]} -> {stats['date_range'][1]}")
    print(f"Avg content length:{stats['avg_length']}")
    print(f"Max content length:{stats['max_length']}")
    print("Languages:")
    for lang, count in stats["langs"]:
        print(f"  {lang}: {count}")
    print("Account handles:")
    for handle, count in stats["user_handles"]:
        print(f"  @{handle}: {count}")


def print_preview(tweets: list[Tweet], *, limit: int = 10) -> None:
    for index, tweet in enumerate(tweets[:limit], start=1):
        preview = tweet.clean_content.replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:220] + "..."
        print(f"[{index}] {tweet.date} @{tweet.user_handle} ({tweet.lang})")
        print(f"    fav={tweet.favorite_count} rt={tweet.retweet_count} len={len(tweet.clean_content)}")
        print(f"    {preview}")
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse tweets.jsonl from X/Twitter scrapes for viewing and corpus export.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to tweets.jsonl. If omitted, prints usage hints.",
    )
    parser.add_argument(
        "--command",
        choices=["stats", "preview", "search", "export-md", "export-csv"],
        default="stats",
        help="What to do with the file.",
    )
    parser.add_argument("--originals-only", action="store_true", help="Drop retweets.")
    parser.add_argument("--min-length", type=int, default=0, help="Minimum cleaned content length.")
    parser.add_argument("--lang", action="append", help="Keep only these language codes, e.g. zh or en.")
    parser.add_argument("--handle", action="append", help="Keep tweets from these handles.")
    parser.add_argument("--query", help="Case-insensitive substring filter.")
    parser.add_argument("--limit", type=int, default=10, help="Preview/search result limit.")
    parser.add_argument(
        "--person-name",
        default=DEFAULT_PERSON_ID,
        help="Person folder name under knowledge/people/, e.g. example_person.",
    )
    parser.add_argument(
        "--display-name",
        default="",
        help="Display name for corpus.md title. Defaults to --person-name.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for export-md output. Defaults to knowledge/people/<person-name>/x/.",
    )
    parser.add_argument(
        "--csv-output",
        default="",
        help="CSV output path for export-csv. Defaults to <output-dir>/tweets.csv",
    )
    parser.add_argument(
        "--no-combined",
        action="store_true",
        help="Skip writing corpus.md during export-md.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        print(
            "\nExample:\n"
            "  python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl --command stats\n"
            "  python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl --command preview "
            "--originals-only --min-length 500 --lang zh --limit 5\n"
            "  python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl --command export-md "
            "--originals-only --min-length 300 --lang zh\n"
            "  python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl --command export-csv "
            "--originals-only\n"
        )
        return 0

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"File not found: {input_path}", file=sys.stderr)
        return 1

    tweets = load_tweets(input_path)
    langs = set(args.lang) if args.lang else None
    handles = set(args.handle) if args.handle else None
    filtered = filter_tweets(
        tweets,
        originals_only=args.originals_only,
        min_length=args.min_length,
        langs=langs,
        handles=handles,
        query=args.query,
    )

    if args.command == "stats":
        print_stats(tweets)
        if filtered is not tweets:
            print("\nFiltered subset:")
            print_stats(filtered)
        return 0

    if args.command == "preview":
        print_preview(filtered, limit=args.limit)
        print(f"Showing {min(args.limit, len(filtered))} of {len(filtered)} tweets.")
        return 0

    if args.command == "search":
        print_preview(filtered, limit=args.limit)
        print(f"Matched {len(filtered)} tweets.")
        return 0

    if args.command == "export-md":
        person_id = args.person_name
        display_name = args.display_name or person_id
        output_dir = (
            Path(args.output_dir).expanduser()
            if args.output_dir
            else PROJECT_ROOT / "knowledge" / "people" / person_id / "x"
        )
        result = export_markdown(
            filtered,
            output_dir,
            person_id=person_id,
            display_name=display_name,
            combined=not args.no_combined,
        )
        print(f"Exported {result['files_written']} files to {result['output_dir']}")
        for path in result["files"][:5]:
            print(f"  - {path}")
        if result["files_written"] > 5:
            print(f"  ... and {result['files_written'] - 5} more")
        print(
            "\nNext step for RAG:\n"
            f"  python -m rag.ingest --person-name {person_id} --embedding-provider keyword"
        )
        return 0

    if args.command == "export-csv":
        output_dir = Path(args.output_dir).expanduser()
        csv_path = Path(args.csv_output).expanduser() if args.csv_output else output_dir / "tweets.csv"
        export_csv(filtered, csv_path)
        print(f"Wrote {len(filtered)} rows to {csv_path}")
        print("Open this CSV in Excel, Numbers, or Google Sheets.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())