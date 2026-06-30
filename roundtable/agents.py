from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rag.retriever import format_retrieved_context, get_retriever, source_files
from llm import LLMClient, describe_llm
from roundtable.prompts import (
    build_agent_prompt,
    build_final_summary_prompt,
    build_moderator_question_prompt,
    build_round_summary_prompt,
)
from roundtable.state import Persona, RoundtableMessage, RoundtableState


Node = Callable[[RoundtableState], dict]
ProgressCallback = Callable[[dict], None]


def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    event: str,
    stage: str,
    label: str,
    **payload: object,
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        {
            "event": event,
            "stage": stage,
            "label": label,
            **payload,
        }
    )


def _messages(state: RoundtableState) -> list[RoundtableMessage]:
    return list(state.get("messages", []))


def _unique_sources(sources: list[str]) -> list[str]:
    return list(dict.fromkeys(sources))


def _recent_messages_query(topic: str, messages: list[RoundtableMessage], limit: int = 6) -> str:
    recent = messages[-limit:]
    message_text = " ".join(str(message.get("content", "")) for message in recent)
    return f"{topic} {message_text}".strip()


def _rag_expert_name(persona: Persona, root_dir: Path) -> str | None:
    if persona.rag_expert_name:
        return persona.rag_expert_name
    return None


def _with_reference_footer(content: str, references: list[str]) -> str:
    missing_references = [reference for reference in references if reference not in content]
    if not missing_references:
        return content
    return f"{content.rstrip()}\n\n引用来源：{', '.join(missing_references)}"


def create_moderator_question_node(
    llm: LLMClient,
    progress_callback: ProgressCallback | None = None,
) -> Node:
    def moderator_question(state: RoundtableState) -> dict:
        round_number = int(state.get("round", 0)) + 1
        label = f"Round {round_number}: Moderator question"
        _emit_progress(
            progress_callback,
            event="start",
            stage="moderator_question",
            label=label,
            round=round_number,
        )
        prompt = build_moderator_question_prompt(
            topic=state["topic"],
            round_number=round_number,
            max_rounds=int(state["max_rounds"]),
            council_description=state.get("council_description", ""),
            messages=_messages(state),
        )
        content = llm.generate(prompt)
        message: RoundtableMessage = {
            "round": round_number,
            "speaker": "Moderator",
            "speaker_id": "moderator",
            "role": "主持人",
            "type": "question",
            "content": content,
            "llm_provider": describe_llm(llm)["provider"],
            "llm_model": describe_llm(llm)["model"],
        }
        _emit_progress(
            progress_callback,
            event="done",
            stage="moderator_question",
            label=label,
            round=round_number,
            speaker="Moderator",
        )
        return {
            "round": round_number,
            "current_speaker": "moderator",
            "messages": _messages(state) + [message],
        }

    return moderator_question


def create_agent_node(
    persona: Persona,
    llm: LLMClient,
    *,
    root_dir: Path,
    progress_callback: ProgressCallback | None = None,
) -> Node:
    def agent_turn(state: RoundtableState) -> dict:
        messages = _messages(state)
        round_number = int(state["round"])
        label = f"Round {round_number}: {persona.name} speaking"
        _emit_progress(
            progress_callback,
            event="start",
            stage="agent",
            label=label,
            round=round_number,
            speaker=persona.name,
            speaker_id=persona.id,
        )
        previous_message = messages[-1] if messages else None
        retrieval_query = _recent_messages_query(state["topic"], messages)
        rag_chunks = []
        expert_name = _rag_expert_name(persona, root_dir)
        if expert_name:
            rag_chunks = get_retriever(
                expert_name,
                top_k=5,
                root_dir=root_dir,
            ).invoke(retrieval_query)
        retrieved_context = (
            format_retrieved_context(rag_chunks)
            if rag_chunks
            else "暂无可用参考资料。"
        )
        prompt = build_agent_prompt(
            topic=state["topic"],
            round_number=round_number,
            max_rounds=int(state["max_rounds"]),
            persona=persona,
            previous_message=previous_message,
            messages=messages,
            retrieved_context=retrieved_context,
        )
        references = _unique_sources(source_files(rag_chunks))
        content = _with_reference_footer(llm.generate(prompt), references)
        llm_info = describe_llm(llm)
        message: RoundtableMessage = {
            "round": round_number,
            "speaker": persona.name,
            "speaker_id": persona.id,
            "role": persona.role,
            "type": "agent",
            "content": content,
            "references": references,
            "llm_provider": llm_info["provider"],
            "llm_model": llm_info["model"],
        }
        _emit_progress(
            progress_callback,
            event="done",
            stage="agent",
            label=label,
            round=round_number,
            speaker=persona.name,
            speaker_id=persona.id,
        )
        return {
            "current_speaker": persona.id,
            "messages": messages + [message],
        }

    return agent_turn


def create_round_summary_node(
    llm: LLMClient,
    progress_callback: ProgressCallback | None = None,
) -> Node:
    def round_summary(state: RoundtableState) -> dict:
        messages = _messages(state)
        round_number = int(state["round"])
        label = f"Round {round_number}: Round summary"
        _emit_progress(
            progress_callback,
            event="start",
            stage="round_summary",
            label=label,
            round=round_number,
        )
        prompt = build_round_summary_prompt(
            topic=state["topic"],
            round_number=round_number,
            messages=messages,
        )
        content = llm.generate(prompt)
        llm_info = describe_llm(llm)
        message: RoundtableMessage = {
            "round": round_number,
            "speaker": "Moderator",
            "speaker_id": "moderator",
            "role": "主持人",
            "type": "round_summary",
            "content": content,
            "llm_provider": llm_info["provider"],
            "llm_model": llm_info["model"],
        }
        _emit_progress(
            progress_callback,
            event="done",
            stage="round_summary",
            label=label,
            round=round_number,
            speaker="Moderator",
        )
        return {
            "current_speaker": "moderator",
            "messages": messages + [message],
            "round_summaries": list(state.get("round_summaries", [])) + [content],
        }

    return round_summary


def create_final_summary_node(
    llm: LLMClient,
    progress_callback: ProgressCallback | None = None,
) -> Node:
    def final_summary(state: RoundtableState) -> dict:
        messages = _messages(state)
        label = "Final summary"
        _emit_progress(
            progress_callback,
            event="start",
            stage="final_summary",
            label=label,
            round=int(state["round"]),
        )
        content = llm.generate(
            build_final_summary_prompt(
                topic=state["topic"],
                round_summaries=list(state.get("round_summaries", [])),
                messages=messages,
            )
        )
        llm_info = describe_llm(llm)
        message: RoundtableMessage = {
            "round": int(state["round"]),
            "speaker": "Moderator",
            "speaker_id": "moderator",
            "role": "主持人",
            "type": "final_summary",
            "content": content,
            "llm_provider": llm_info["provider"],
            "llm_model": llm_info["model"],
        }
        _emit_progress(
            progress_callback,
            event="done",
            stage="final_summary",
            label=label,
            round=int(state["round"]),
            speaker="Moderator",
        )
        return {
            "current_speaker": "moderator",
            "messages": messages + [message],
            "final_summary": content,
        }

    return final_summary
