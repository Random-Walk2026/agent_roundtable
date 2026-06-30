from __future__ import annotations

from llm import (
    MockLLM,
    TextGenerationRequest,
    create_llm_from_config,
    generate_text,
    parse_provider_chain,
    split_model_effort,
)


def test_parse_provider_chain_accepts_workflow_style_model_tokens():
    assert parse_provider_chain(
        "antigravity:gemini-3.1-pro-low, claude:sonnet@high, codex@medium"
    ) == [
        ("antigravity", "gemini-3.1-pro-low"),
        ("claude", "sonnet@high"),
        ("codex", "@medium"),
    ]
    assert split_model_effort("sonnet@high") == ("sonnet", "high")
    assert split_model_effort("@medium") == ("", "medium")


def test_generate_text_uses_provider_chain_fallback(monkeypatch):
    calls: list[tuple[str, str, str, str]] = []

    def fake_call_provider(
        instruction: str,
        provider: str,
        model: str = "",
        *,
        workflow: str,
        **_: object,
    ) -> str:
        calls.append((instruction, provider, model, workflow))
        if provider == "claude":
            raise RuntimeError("quota exhausted")
        return f"{provider}:{model}:{instruction}"

    monkeypatch.setattr("llm.router.call_provider", fake_call_provider)

    text, provider = generate_text(
        TextGenerationRequest(
            workflow="agent_roundtable",
            provider_chain="claude:sonnet@high, gemini:gemini-2.5-flash",
            label="test-chain",
        ),
        "hello",
    )

    assert provider == "gemini"
    assert text == "gemini:gemini-2.5-flash:hello"
    assert calls == [
        ("hello", "claude", "sonnet@high", "agent_roundtable"),
        ("hello", "gemini", "gemini-2.5-flash", "agent_roundtable"),
    ]


def test_create_llm_from_provider_chain_config_uses_facade_client():
    llm = create_llm_from_config(
        {
            "provider_chain": "mock:chain-model",
            "temperature": 0.2,
            "max_output_tokens": 2048,
        },
        fallback=MockLLM(model="fallback"),
    )

    assert llm.generate("[ROUND_TABLE_FINAL_SUMMARY]\n话题：测试") != ""
    assert getattr(llm, "provider_name") == "mock"
    assert getattr(llm, "model") == "chain-model"
