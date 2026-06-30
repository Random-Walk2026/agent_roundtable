from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


_EFFORT_SUFFIXES = ("low", "medium", "high", "thinking")
_MODEL_VARIANTS: dict[str, dict[str, str]] = {
    "gemini-3.5-flash": {
        "low": "gemini-3.5-flash-low",
        "extra-low": "gemini-3.5-flash-extra-low",
    },
    "gemini-3.1-pro": {"low": "gemini-3.1-pro-low"},
    "claude-opus-4-6": {
        "low": "claude-opus-4-6-thinking",
        "medium": "claude-opus-4-6-thinking",
        "high": "claude-opus-4-6-thinking",
        "thinking": "claude-opus-4-6-thinking",
    },
}
_DEFAULT_HTTP_MODELS = {
    "claude": "claude-sonnet-4-6",
    "antigravity": "gemini-3.1-pro-low",
    "codex": "gpt-oss-120b-medium",
    "grok": "grok-4.3",
    "copilot": "gpt-oss-120b-medium",
}
_MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5",
    "claude": "claude-sonnet-4-6",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
}
_OPENAI_EFFORTS = ("minimal", "low", "medium", "high")


def antigravity_model_variant(model: str, effort: str) -> str:
    chosen = (model or "").strip()
    if not chosen or not effort:
        return chosen
    lower = chosen.lower()
    if any(lower.endswith(f"-{suffix}") for suffix in _EFFORT_SUFFIXES):
        return chosen
    variants = _MODEL_VARIANTS.get(lower)
    if not variants:
        return chosen
    return variants.get(effort.strip().lower(), chosen)


def _base_url() -> str:
    url = (
        os.environ.get("CLI_PROXY_BASE_URL")
        or os.environ.get("CLIPROXY_BASE_URL")
        or "http://127.0.0.1:8317"
    ).strip()
    return url.rstrip("/")


def _api_key() -> str:
    key = (
        os.environ.get("CLI_PROXY_API_KEY")
        or os.environ.get("CLIPROXY_API_KEY")
        or "local"
    ).strip()
    return key or "local"


def _timeout() -> float:
    raw = os.environ.get("CLI_PROXY_TIMEOUT", "").strip()
    try:
        return float(raw) if raw else 600.0
    except ValueError:
        return 600.0


def run_cli(
    backend: str,
    text: str,
    model: str = "",
    effort: str = "",
    *,
    env_override: Optional[dict[str, str]] = None,
) -> str:
    base = (model or "").strip() or _DEFAULT_HTTP_MODELS.get(backend, "")
    base = _MODEL_ALIASES.get(base.lower(), base)
    if not base:
        raise RuntimeError(f"CLIProxyAPI: backend {backend!r} has no configured model.")
    model_id = antigravity_model_variant(base, effort) if effort else base
    payload: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
    }
    if effort and model_id == base:
        normalized_effort = {"middle": "medium", "mid": "medium"}.get(effort.lower(), effort.lower())
        if normalized_effort in _OPENAI_EFFORTS:
            payload["reasoning_effort"] = normalized_effort

    url = f"{_base_url()}/v1/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_timeout()) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CLIProxyAPI returned {exc.code} for model={model_id}: {body[:500]}") from exc
    except OSError as exc:
        raise RuntimeError(
            f"CLIProxyAPI connection failed ({url}): {exc}. Start the local CLIProxyAPI service first."
        ) from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"CLIProxyAPI response parse failed for model={model_id}: {data}") from exc
    return (content or "").strip()
