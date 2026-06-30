from pathlib import Path

import pytest
import yaml

from roundtable.graph import run_roundtable
from roundtable.loader import load_persona
from llm import MockLLM, OpenRouterLLM, create_llm


def test_graph_runs_two_rounds_and_generates_final_summary(tmp_path: Path):
    result = run_roundtable(
        topic="AI 会不会取代程序员？",
        council_name="experts",
        rounds=2,
        llm=MockLLM(),
        output_dir=tmp_path,
    )

    assert result["round"] == 2
    assert result["final_summary"]
    assert len(result["round_summaries"]) == 2
    assert any(message["speaker"] == "Moderator" for message in result["messages"])
    assert any(message.get("type") == "agent" for message in result["messages"])
    assert result["log_path"]
    assert Path(result["log_path"]).exists()


def test_openrouter_llm_accepts_comma_separated_model_candidates(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "model-a:free, model-b:free")

    llm = create_llm(provider="openrouter")

    assert isinstance(llm, OpenRouterLLM)
    assert llm.models == ["model-a:free", "model-b:free"]


def test_openrouter_llm_uses_numbered_api_key_by_default(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "test-key-1")
    monkeypatch.setenv("OPENROUTER_MODEL", "model-a:free")

    llm = create_llm(provider="openrouter")

    assert isinstance(llm, OpenRouterLLM)
    assert llm.api_key_env == "OPENROUTER_API_KEY_1"
    assert llm.api_key == "test-key-1"


def test_persona_llm_config_is_logged_per_agent(tmp_path: Path):
    (tmp_path / "config" / "domain_experts").mkdir(parents=True)
    (tmp_path / "config" / "councils").mkdir()
    (tmp_path / "config" / "domain_experts" / "analyst.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Test Analyst",
                "role": "测试分析师",
                "worldview": "关注可验证行为",
                "speaking_style": "直接",
                "strengths": ["测试"],
                "weaknesses": ["保守"],
                "catchphrases": ["先验证"],
                "llm": {"provider": "mock", "model": "agent-mock-model"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "councils" / "test.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "test",
                "description": "测试圆桌",
                "members": ["analyst"],
                "moderator_llm": {"provider": "mock", "model": "moderator-mock-model"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = run_roundtable(
        topic="测试不同角色模型",
        council_name="test",
        rounds=1,
        root_dir=tmp_path,
        output_dir=tmp_path / "logs",
    )

    agent_message = next(message for message in result["messages"] if message["type"] == "agent")
    moderator_message = next(message for message in result["messages"] if message["type"] == "question")
    assert agent_message["llm_provider"] == "mock"
    assert agent_message["llm_model"] == "agent-mock-model"
    assert moderator_message["llm_model"] == "moderator-mock-model"
    assert "LLM: mock / agent-mock-model" in Path(result["log_path"]).read_text(encoding="utf-8")


def test_agent_llm_json_overrides_agent_yaml_config(tmp_path: Path):
    (tmp_path / "config" / "domain_experts").mkdir(parents=True)
    (tmp_path / "config" / "councils").mkdir()
    (tmp_path / "config" / "domain_experts" / "analyst.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Test Analyst",
                "role": "测试分析师",
                "worldview": "关注可验证行为",
                "speaking_style": "直接",
                "strengths": ["测试"],
                "weaknesses": ["保守"],
                "catchphrases": ["先验证"],
                "llm": {"provider": "mock", "model": "yaml-agent-model"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "councils" / "test.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "test",
                "description": "测试圆桌",
                "members": ["analyst"],
                "moderator_llm": {"provider": "mock", "model": "moderator-mock-model"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "agent_llms.json").write_text(
        """{
  "agents": {
    "analyst": {
      "provider": "mock",
      "model": "json-agent-model"
    }
  }
}
""",
        encoding="utf-8",
    )

    result = run_roundtable(
        topic="测试集中 JSON 模型配置",
        council_name="test",
        rounds=1,
        root_dir=tmp_path,
        output_dir=tmp_path / "logs",
    )

    agent_message = next(message for message in result["messages"] if message["type"] == "agent")
    assert agent_message["llm_provider"] == "mock"
    assert agent_message["llm_model"] == "json-agent-model"
    assert "LLM: mock / json-agent-model" in Path(result["log_path"]).read_text(encoding="utf-8")


def test_roundtable_emits_progress_events(tmp_path: Path):
    (tmp_path / "config" / "domain_experts").mkdir(parents=True)
    (tmp_path / "config" / "councils").mkdir()
    (tmp_path / "config" / "domain_experts" / "analyst.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Test Analyst",
                "role": "测试分析师",
                "worldview": "关注可验证行为",
                "speaking_style": "直接",
                "strengths": ["测试"],
                "weaknesses": ["保守"],
                "catchphrases": ["先验证"],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "councils" / "test.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "test",
                "description": "测试圆桌",
                "members": ["analyst"],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    events: list[dict] = []

    run_roundtable(
        topic="测试进度事件",
        council_name="test",
        rounds=1,
        root_dir=tmp_path,
        llm=MockLLM(),
        output_dir=tmp_path / "logs",
        progress_callback=events.append,
    )

    done_stages = [event["stage"] for event in events if event["event"] == "done"]
    assert done_stages == [
        "moderator_question",
        "agent",
        "round_summary",
        "final_summary",
        "save_log",
    ]
    assert any(event["event"] == "start" and "Test Analyst" in event["label"] for event in events)


def test_loader_does_not_fall_back_to_legacy_personas_directory(tmp_path: Path):
    (tmp_path / "personas").mkdir()
    (tmp_path / "personas" / "legacy.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Legacy Persona",
                "role": "旧人格",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        load_persona("legacy", root_dir=tmp_path)


class CapturingLLM(MockLLM):
    def __init__(self) -> None:
        super().__init__()
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return super().generate(prompt)


def test_agent_uses_rag_retrieved_context_before_speaking(tmp_path: Path):
    (tmp_path / "config" / "domain_experts").mkdir(parents=True)
    (tmp_path / "config" / "councils").mkdir()
    (tmp_path / "knowledge" / "macro_economist" / "keynes").mkdir(parents=True)
    (tmp_path / "knowledge" / "macro_economist" / "keynes" / "demand.md").write_text(
        "# Keynesian Demand\n\n"
        "## Fiscal Policy\n\n"
        "Aggregate demand and employment can be supported by countercyclical fiscal policy.",
        encoding="utf-8",
    )
    (tmp_path / "config" / "domain_experts" / "macro_economist.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Macro Economist",
                "role": "宏观经济主题专家",
                "worldview": "用总需求、通胀、就业和政策反馈分析问题",
                "speaking_style": "结构化、克制",
                "strengths": ["宏观框架"],
                "weaknesses": ["可能低估个体差异"],
                "catchphrases": ["先看总需求"],
                "rag_expert_name": "macro_economist",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "councils" / "macro.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "macro",
                "description": "宏观圆桌",
                "members": ["macro_economist"],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    llm = CapturingLLM()

    result = run_roundtable(
        topic="财政政策能否稳定就业？",
        council_name="macro",
        rounds=1,
        root_dir=tmp_path,
        llm=llm,
        output_dir=tmp_path / "logs",
    )

    agent_prompt = next(prompt for prompt in llm.prompts if "[ROUND_TABLE_AGENT]" in prompt)
    agent_message = next(message for message in result["messages"] if message["type"] == "agent")
    assert "retrieved_context" in agent_prompt
    assert "countercyclical fiscal policy" in agent_prompt
    assert agent_message["references"] == ["knowledge/macro_economist/keynes/demand.md"]
    assert "引用来源：knowledge/macro_economist/keynes/demand.md" in agent_message["content"]
