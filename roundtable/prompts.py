from __future__ import annotations

from roundtable.state import Persona, RoundtableMessage


def _format_recent_messages(messages: list[RoundtableMessage], limit: int = 8) -> str:
    if not messages:
        return "暂无历史发言。"
    recent = messages[-limit:]
    return "\n".join(
        f"- Round {message.get('round', '-')}, {message.get('speaker', 'Unknown')}: {message.get('content', '')}"
        for message in recent
    )


def _format_profile(profile: dict | None) -> str:
    if not profile:
        return "无额外设定。"
    lines: list[str] = []
    for key, value in profile.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(str(item) for item in value)}")
        elif isinstance(value, dict):
            nested = "; ".join(f"{nested_key}={nested_value}" for nested_key, nested_value in value.items())
            lines.append(f"- {key}: {nested}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_moderator_question_prompt(
    *,
    topic: str,
    round_number: int,
    max_rounds: int,
    council_description: str,
    messages: list[RoundtableMessage],
) -> str:
    return f"""[ROUND_TABLE_MODERATOR_QUESTION]
你是圆桌会议主持人。你的任务是控制节奏、点名发言、总结分歧，不要偏袒任何一方。

话题：{topic}
专家组：{council_description}
当前轮次：{round_number}/{max_rounds}
最近发言：
{_format_recent_messages(messages, limit=6)}

请提出本轮的一个聚焦问题，要求简洁、有推进感，并提醒大家可以回应或反驳前面的观点。
"""


def build_agent_prompt(
    *,
    topic: str,
    round_number: int,
    max_rounds: int,
    persona: Persona,
    previous_message: RoundtableMessage | None,
    messages: list[RoundtableMessage],
    retrieved_context: str = "暂无可用参考资料。",
) -> str:
    previous = (
        f"{previous_message.get('speaker', '上一位')}: {previous_message.get('content', '')}"
        if previous_message
        else "暂无上一位发言。"
    )
    return f"""[ROUND_TABLE_AGENT]
你正在参加一个人格化多 Agent 圆桌讨论。

话题：{topic}
当前轮次：{round_number}/{max_rounds}

你的人格卡：
- 名称：{persona.name}
- 角色：{persona.role}
- 世界观：{persona.worldview}
- 说话风格：{persona.speaking_style}
- 优势：{", ".join(persona.strengths)}
- 弱点：{", ".join(persona.weaknesses)}
- 口头禅：{", ".join(persona.catchphrases)}
- Agent 类型：{persona.agent_type}

扩展设定：
{_format_profile(persona.profile)}

上一位发言：
{previous}

最近上下文：
{_format_recent_messages(messages, limit=8)}

retrieved_context:
{retrieved_context}

发言要求：
1. 保持自己的人格设定。
2. 回应当前话题。
3. 明确引用或反驳上一位 Agent 或主持人的观点。
4. 不要长篇大论，每次发言 120-250 字。
5. 可以有个性，但不要胡编具体数据。
6. 如果涉及现实经济数据，要提醒“需要联网核实”。
7. 如果使用了 retrieved_context，请自然提到其观点，但不要逐字照搬。
8. 使用资料时在句末标注来源，格式为（来源：source_file）。

请直接输出你的发言，不要加额外标题。
"""


def build_round_summary_prompt(
    *,
    topic: str,
    round_number: int,
    messages: list[RoundtableMessage],
) -> str:
    return f"""[ROUND_TABLE_ROUND_SUMMARY]
你是圆桌会议主持人。请为第 {round_number} 轮做一个中立小结。

话题：{topic}
本轮和最近发言：
{_format_recent_messages(messages, limit=12)}

输出 2-4 点，说明本轮推进了什么、争议在哪里、下一轮应该追问什么。
"""


def build_final_summary_prompt(
    *,
    topic: str,
    round_summaries: list[str],
    messages: list[RoundtableMessage],
) -> str:
    summaries = "\n".join(
        f"第 {index + 1} 轮：{summary}" for index, summary in enumerate(round_summaries)
    )
    return f"""[ROUND_TABLE_FINAL_SUMMARY]
你是圆桌会议主持人。请基于完整讨论输出结构化最终总结。

话题：{topic}
轮次小结：
{summaries}

最近完整发言：
{_format_recent_messages(messages, limit=20)}

必须使用以下结构：
## 主要共识
## 主要分歧
## 最有价值观点
## 风险提示
## 最终总结

保持中立，不要编造具体数据；如涉及现实经济数据，提醒需要联网核实。
"""
