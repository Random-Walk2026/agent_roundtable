from __future__ import annotations

import json
from pathlib import Path

import yaml

from person_crawl_agent.config import load_person_crawl_config
from person_crawl_agent.locate import find_tweets_jsonl, find_weibo_json
from person_crawl_agent.pipeline import run_person_crawl_pipeline


def _write_person_crawl_config(path: Path, *, spider_base_path: Path) -> None:
    payload = {
        "spider_base_path": str(spider_base_path),
        "defaults": {
            "x": {"mode": "with_replies"},
            "weibo": {"since_date": 7, "modes": ["posts"]},
        },
        "people": {
            "desmond_shum": {
                "display_name": "Desmond Shum",
                "x": {"user": "DesmondShum"},
                "weibo": None,
            },
            "guaxichan": {
                "display_name": "瓜希酱",
                "x": None,
                "weibo": {"id": "1842707505", "name": "瓜希酱"},
            },
        },
    }
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


def test_load_person_crawl_config_merges_defaults(tmp_path: Path):
    spider_base = tmp_path / "spider"
    spider_base.mkdir()
    config_path = tmp_path / "person_crawl.yaml"
    _write_person_crawl_config(config_path, spider_base_path=spider_base)

    config = load_person_crawl_config(config_path, root_dir=tmp_path)
    person = config.get_person("desmond_shum")

    assert person.x is not None
    assert person.x.payload["user"] == "DesmondShum"
    assert person.x.payload["mode"] == "with_replies"
    assert person.weibo is None


def test_find_tweets_jsonl_under_twitter_subdir(tmp_path: Path):
    spider_base = tmp_path / "spider"
    spider_base.mkdir()
    output_dir = tmp_path / "drive"
    tweets = output_dir / "twitter" / "DesmondShum" / "tweets.jsonl"
    tweets.parent.mkdir(parents=True)
    tweets.write_text('{"tweet_id": 1, "content": "hello"}\n', encoding="utf-8")
    (spider_base / "settings.json").write_text(
        json.dumps({"x": {"output_dir": str(output_dir)}}),
        encoding="utf-8",
    )

    found = find_tweets_jsonl(spider_base_path=spider_base, handle="DesmondShum")
    assert found == tweets.resolve()


def test_find_weibo_json_under_name_subdir(tmp_path: Path):
    spider_base = tmp_path / "spider"
    spider_base.mkdir()
    output_dir = tmp_path / "character"
    weibo_json = output_dir / "瓜希酱" / "1842707505.json"
    weibo_json.parent.mkdir(parents=True)
    weibo_json.write_text('{"weibo": [{"id": "abc", "content": "测试"}]}', encoding="utf-8")
    (spider_base / "settings.json").write_text(
        json.dumps({"weibo": {"output_dir": str(output_dir)}}),
        encoding="utf-8",
    )

    found = find_weibo_json(
        spider_base_path=spider_base,
        user_id="1842707505",
        display_name="瓜希酱",
    )
    assert found == weibo_json.resolve()


def test_skip_crawl_imports_existing_x_corpus(tmp_path: Path, monkeypatch):
    project_root = tmp_path / "agent_roundtable"
    project_root.mkdir()
    (project_root / "scripts").mkdir()
    (project_root / "knowledge" / "people").mkdir(parents=True)

    spider_base = tmp_path / "spider"
    spider_base.mkdir()
    output_dir = tmp_path / "drive"
    tweets = output_dir / "twitter" / "DesmondShum" / "tweets.jsonl"
    tweets.parent.mkdir(parents=True)
    tweets.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "tweet_id": 1,
                        "date": "2026-01-01 12:00:00",
                        "content": "这是一段足够长的中文原创推文，用于测试导入流水线。",
                        "lang": "zh",
                        "favorite_count": 1,
                        "retweet_count": 0,
                        "reply_count": 0,
                        "view_count": 10,
                        "user": {"name": "DesmondShum", "nick": "Desmond Shum"},
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (spider_base / "settings.json").write_text(
        json.dumps({"x": {"output_dir": str(output_dir)}}),
        encoding="utf-8",
    )

    config_path = project_root / "config"
    config_path.mkdir()
    _write_person_crawl_config(config_path / "person_crawl.yaml", spider_base_path=spider_base)

    real_root = Path(__file__).resolve().parent.parent
    for relative in (
        "scripts/parse_twitter_jsonl.py",
        "scripts/parse_weibo_json.py",
        "person_crawl_agent",
        "rag",
    ):
        source = real_root / relative
        target = project_root / relative
        if source.is_dir():
            import shutil

            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    config = load_person_crawl_config(config_path / "person_crawl.yaml", root_dir=project_root)
    result = run_person_crawl_pipeline(
        "desmond_shum",
        config=config,
        root_dir=project_root,
        skip_crawl=True,
        min_length_x=10,
        lang=None,
    )

    corpus = project_root / "knowledge" / "people" / "desmond_shum" / "x" / "corpus.md"
    assert corpus.exists()
    assert result.imported_files
    assert "中文原创推文" in corpus.read_text(encoding="utf-8")