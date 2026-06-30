from __future__ import annotations

import json
from pathlib import Path

from scripts.parse_twitter_jsonl import export_csv, export_markdown, filter_tweets, load_tweets, tweet_stats


def _write_sample_jsonl(path: Path) -> None:
    records = [
        {
            "tweet_id": 1,
            "retweet_id": 0,
            "reply_id": 0,
            "quote_id": 0,
            "date": "2026-01-01 10:00:00",
            "lang": "zh",
            "favorite_count": 12,
            "retweet_count": 3,
            "reply_count": 1,
            "view_count": 100,
            "user": {"name": "DesmondShum", "nick": "Desmond Shum"},
            "author": {"name": "DesmondShum", "nick": "Desmond Shum"},
            "content": "被推迟的清算：中国债务问题如何演变为资产负债表衰退。" + "机制分析。" * 120,
        },
        {
            "tweet_id": 2,
            "retweet_id": 99,
            "reply_id": 0,
            "quote_id": 0,
            "date": "2026-01-02 11:00:00",
            "lang": "en",
            "favorite_count": 1,
            "retweet_count": 0,
            "reply_count": 0,
            "view_count": 10,
            "user": {"name": "DesmondShum", "nick": "Desmond Shum"},
            "author": {"name": "OtherUser", "nick": "Other"},
            "content": "RT @OtherUser: short retweet",
        },
        {
            "tweet_id": 3,
            "retweet_id": 0,
            "reply_id": 0,
            "quote_id": 0,
            "date": "2026-01-03 12:00:00",
            "lang": "zh",
            "favorite_count": 5,
            "retweet_count": 0,
            "reply_count": 0,
            "view_count": 20,
            "user": {"name": "DesmondShum", "nick": "Desmond Shum"},
            "author": {"name": "DesmondShum", "nick": "Desmond Shum"},
            "content": "简短评论。",
        },
    ]
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


def test_load_and_filter_twitter_jsonl(tmp_path: Path):
    source = tmp_path / "tweets.jsonl"
    _write_sample_jsonl(source)

    tweets = load_tweets(source)
    assert len(tweets) == 3
    assert tweet_stats(tweets)["originals"] == 2

    filtered = filter_tweets(tweets, originals_only=True, min_length=100, langs={"zh"})
    assert len(filtered) == 1
    assert "资产负债表衰退" in filtered[0].clean_content


def test_export_markdown_and_csv(tmp_path: Path):
    source = tmp_path / "tweets.jsonl"
    _write_sample_jsonl(source)
    tweets = filter_tweets(load_tweets(source), originals_only=True, min_length=50)

    export_dir = tmp_path / "export"
    md_result = export_markdown(tweets, export_dir, split_long_posts=False)
    assert (export_dir / "corpus.md").exists()
    assert md_result["files_written"] == 1
    assert "资产负债表衰退" in (export_dir / "corpus.md").read_text(encoding="utf-8")

    csv_path = export_dir / "tweets.csv"
    export_csv(tweets, csv_path)
    assert csv_path.exists()
    assert "tweet_id" in csv_path.read_text(encoding="utf-8")