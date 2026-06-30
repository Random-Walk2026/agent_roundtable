from __future__ import annotations

from pathlib import Path

import yaml

from roundtable.graph import run_roundtable
from llm import MockLLM
from roundtable.state import RoundtableMessage


class CapturingLLM(MockLLM):
    def __init__(self) -> None:
        super().__init__()
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return super().generate(prompt)


def _write_single_agent_council(root: Path) -> None:
    (root / "config" / "domain_experts").mkdir(parents=True)
    (root / "config" / "councils").mkdir()
    (root / "config" / "domain_experts" / "analyst.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Test Analyst",
                "role": "测试分析师",
                "worldview": "关注延续上下文",
                "speaking_style": "直接",
                "strengths": ["追问"],
                "weaknesses": ["保守"],
                "catchphrases": ["接着看"],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (root / "config" / "councils" / "test.yaml").write_text(
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


def test_roundtable_can_continue_from_existing_messages(tmp_path: Path):
    _write_single_agent_council(tmp_path)
    llm = CapturingLLM()
    previous_messages: list[RoundtableMessage] = [
        {
            "round": 1,
            "speaker": "Moderator",
            "speaker_id": "moderator",
            "role": "主持人",
            "type": "round_summary",
            "content": "第一轮已经确认核心分歧是短期效率与长期适应能力。",
        }
    ]

    result = run_roundtable(
        topic="继续讨论 AI 对就业的影响",
        council_name="test",
        rounds=1,
        root_dir=tmp_path,
        llm=llm,
        output_dir=tmp_path / "logs",
        initial_messages=previous_messages,
        initial_round_summaries=["第一轮小结"],
    )

    assert result["round"] == 2
    assert result["max_rounds"] == 2
    assert result["messages"][0]["content"] == previous_messages[0]["content"]
    assert any("第一轮已经确认核心分歧" in prompt for prompt in llm.prompts)
