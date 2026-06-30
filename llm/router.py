from __future__ import annotations

import os
from typing import Any, Callable, Optional

from . import transport_cli, transport_http
from .providers_api import MockLLM, create_llm
from .transport_http import antigravity_model_variant


CLI_BACKENDS = ("claude", "codex", "grok", "antigravity", "copilot")
CLI_EFFORT_BACKENDS = CLI_BACKENDS
CLI_EFFORT_CHOICES = {
    "claude": ("", "low", "medium", "high", "xhigh", "max"),
    "codex": ("", "low", "medium", "high", "xhigh"),
    "grok": ("", "low", "medium", "high", "xhigh", "max"),
    "antigravity": ("", "low", "medium", "high", "thinking"),
    "copilot": ("", "none", "low", "medium", "high", "xhigh", "max"),
}
API_PROVIDERS = ("mock", "auto", "gemini", "openai", "openrouter", "deepseek")
_DEFAULT_TRANSPORTS = {
    "claude": "subprocess",
    "codex": "subprocess",
    "grok": "http",
    "antigravity": "http",
    "copilot": "http",
}


def _alias(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ("claude", "claude_cli", "claude-cli", "anthropic"):
        return "claude"
    if v in ("codex", "codex_cli", "codex-cli", "chatgpt", "openai_cli"):
        return "codex"
    if v in ("grok", "grok_cli", "grok-cli", "xai"):
        return "grok"
    if v in ("antigravity", "antigravity_cli", "antigravity-cli", "agy"):
        return "antigravity"
    if v in ("copilot", "copilot_cli", "copilot-cli", "github_copilot", "github-copilot"):
        return "copilot"
    return v or "auto"


def _normalize_effort(value: str) -> str:
    effort = (value or "").strip().lower()
    if effort in ("middle", "mid"):
        return "medium"
    return effort


def _normalize_transport(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ("subprocess", "cli", "local"):
        return "subprocess"
    if v in ("http", "cliproxy", "cliproxyapi"):
        return "http"
    return ""


def backend_transport(backend: str) -> str:
    normalized = _alias(backend)
    for env in (f"{normalized.upper()}_TRANSPORT", "CLI_TRANSPORT", "AGY_TRANSPORT"):
        transport = _normalize_transport(os.environ.get(env, ""))
        if transport:
            return transport
    return _DEFAULT_TRANSPORTS.get(normalized, "http")


def supports_effort(backend: str) -> bool:
    return _alias(backend) in CLI_EFFORT_BACKENDS


def run_cli(
    backend: str,
    text: str,
    model: str = "",
    effort: str = "",
    *,
    env_override: Optional[dict[str, str]] = None,
) -> str:
    normalized = _alias(backend)
    if backend_transport(normalized) == "subprocess":
        return transport_cli.run_cli(normalized, text, model, effort, env_override=env_override)
    return transport_http.run_cli(normalized, text, model, effort, env_override=env_override)


def split_model_effort(token: str) -> tuple[str, str]:
    model, _, effort = str(token or "").partition("@")
    return model.strip(), _normalize_effort(effort)


def parse_provider_chain(provider_string: str, *, default: str = "gemini") -> list[tuple[str, str]]:
    chain: list[tuple[str, str]] = []
    for segment in str(provider_string or "").split(","):
        segment = segment.strip()
        if not segment:
            continue
        provider, _, model = segment.partition(":")
        provider = _alias(provider.strip())
        if not model and "@" in provider:
            provider, _, effort = provider.partition("@")
            provider = _alias(provider.strip())
            model = f"@{effort.strip()}"
        chain.append((provider, model.strip()))
    return chain or [(_alias(default), "")]


def cli_text(
    backend: str,
    prompt: Any,
    *,
    workflow: str = "",
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> str:
    normalized = _alias(backend)
    if normalized not in CLI_BACKENDS:
        raise ValueError(f"cli_text only supports {', '.join(CLI_BACKENDS)}, got {backend!r}.")
    chosen, inline_effort = split_model_effort(model or "")
    chosen_effort = _normalize_effort(effort or inline_effort or "")
    if not supports_effort(normalized):
        chosen_effort = ""
    text = prompt if isinstance(prompt, str) else str(prompt)
    return run_cli(normalized, text, chosen, chosen_effort)


def call_provider(
    instruction: str,
    provider: str,
    model: str = "",
    *,
    workflow: str,
    fallback_model: str = "",
    gemini_max_output_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    normalized = _alias(provider)
    chosen, inline_effort = split_model_effort(model or fallback_model)
    if normalized == "mock":
        return MockLLM(model=chosen or "mock").generate(instruction)
    if normalized in CLI_BACKENDS:
        return cli_text(
            normalized,
            instruction,
            workflow=workflow,
            model=chosen,
            effort=inline_effort or None,
        )
    llm = create_llm(
        normalized,
        model=chosen or None,
        temperature=temperature,
        max_output_tokens=gemini_max_output_tokens,
    )
    return llm.generate(instruction)


def run_provider_chain(
    instruction: str,
    provider_string: str,
    *,
    workflow: str,
    skip: tuple[str, ...] = (),
    label: str = "",
    validate: Optional[Callable[[str], Any]] = None,
    **call_kwargs: Any,
) -> tuple[str, str]:
    errors: list[str] = []
    tag = label or workflow
    skip_set = {_alias(item) for item in skip}
    for provider, model in parse_provider_chain(provider_string):
        if provider in skip_set:
            continue
        try:
            result = call_provider(
                instruction,
                provider,
                model,
                workflow=workflow,
                **call_kwargs,
            )
            if validate is not None:
                validate(result)
            return result, provider
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{provider}: {exc}")
            print(f"  [{tag}] provider={provider} failed, trying next provider... ({exc})", flush=True)
    raise RuntimeError("; ".join(errors) or "No usable provider in chain")


def model_for_provider(provider_chain: str, provider: str) -> str:
    normalized = _alias(provider)
    for chain_provider, model in parse_provider_chain(provider_chain):
        if chain_provider == normalized:
            chosen, _ = split_model_effort(model)
            return chosen or "default"
    return "unknown"
