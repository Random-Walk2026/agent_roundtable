from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "person_crawl.yaml"


@dataclass(frozen=True)
class PlatformTarget:
    platform: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PersonTarget:
    person_id: str
    display_name: str
    x: PlatformTarget | None = None
    weibo: PlatformTarget | None = None


@dataclass(frozen=True)
class PersonCrawlConfig:
    spider_base_path: Path
    defaults: dict[str, dict[str, Any]]
    people: dict[str, PersonTarget]

    def get_person(self, person_id: str) -> PersonTarget:
        target = self.people.get(person_id)
        if target is None:
            known = ", ".join(sorted(self.people))
            raise KeyError(f"Unknown person_id '{person_id}'. Configured: {known or '(none)'}")
        return target

    def list_person_ids(self) -> list[str]:
        return sorted(self.people)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key == "options" and isinstance(value, dict):
            options = dict(merged.get("options", {}))
            options.update(value)
            merged["options"] = options
        else:
            merged[key] = value
    return merged


def _normalize_platform_target(
    platform: str,
    raw: Any,
    defaults: dict[str, Any],
) -> PlatformTarget | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{platform} target must be a mapping or null")

    payload = _deep_merge(defaults, raw)
    if platform == "x":
        user = str(payload.get("user") or payload.get("handle") or "").strip()
        if not user:
            raise ValueError(f"{platform} target requires 'user'")
        payload["user"] = user
    elif platform == "weibo":
        user_id = str(payload.get("id") or payload.get("user_id") or "").strip()
        if not user_id:
            raise ValueError(f"{platform} target requires 'id'")
        payload["id"] = user_id
    return PlatformTarget(platform=platform, payload=payload)


def load_person_crawl_config(
    path: Path | str | None = None,
    *,
    root_dir: Path | str | None = None,
) -> PersonCrawlConfig:
    config_path = Path(path or DEFAULT_CONFIG_PATH).expanduser()
    if not config_path.is_absolute():
        root = Path(root_dir or PROJECT_ROOT).expanduser().resolve()
        config_path = (root / config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Person crawl config not found: {config_path}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Person crawl config must be a mapping: {config_path}")

    env_spider_path = os.getenv("SPIDER_BASE_PATH", "").strip()
    spider_base_path = Path(
        env_spider_path or data.get("spider_base_path") or "~/GitHub/spider"
    ).expanduser().resolve()

    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping")

    x_defaults = defaults.get("x", {})
    weibo_defaults = defaults.get("weibo", {})
    if not isinstance(x_defaults, dict):
        raise ValueError("defaults.x must be a mapping")
    if not isinstance(weibo_defaults, dict):
        raise ValueError("defaults.weibo must be a mapping")

    people_raw = data.get("people", {})
    if not isinstance(people_raw, dict):
        raise ValueError("people must be a mapping")

    people: dict[str, PersonTarget] = {}
    for person_id, entry in people_raw.items():
        if not isinstance(entry, dict):
            raise ValueError(f"people.{person_id} must be a mapping")
        display_name = str(entry.get("display_name") or person_id)
        people[person_id] = PersonTarget(
            person_id=str(person_id),
            display_name=display_name,
            x=_normalize_platform_target("x", entry.get("x"), x_defaults),
            weibo=_normalize_platform_target("weibo", entry.get("weibo"), weibo_defaults),
        )

    return PersonCrawlConfig(
        spider_base_path=spider_base_path,
        defaults={"x": x_defaults, "weibo": weibo_defaults},
        people=people,
    )