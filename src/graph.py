from __future__ import annotations

from pathlib import Path
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.agent_llm_config import load_agent_llm_configs
from src.agents import (
    ProgressCallback,
    create_agent_node,
    create_final_summary_node,
    create_moderator_question_node,
    create_round_summary_node,
)
from src.llm import LLMClient, create_llm, create_llm_from_config
from src.loader import PROJECT_ROOT, load_council_personas
from src.logger import save_markdown_log
from src.state import Council, Persona, RoundtableState


def build_roundtable_graph(
    council: Council,
    personas: list[Persona],
    llm: LLMClient,
    *,
    root_dir: Path | str | None = None,
    agent_llms: dict[str, LLMClient] | None = None,
    progress_callback: ProgressCallback | None = None,
):
    if not personas:
        raise ValueError("At least one persona is required to build a roundtable graph")

    builder = StateGraph(RoundtableState)
    builder.add_node(
        "moderator_question",
        create_moderator_question_node(llm, progress_callback),
    )

    previous_node = "moderator_question"
    graph_root = Path(root_dir) if root_dir else PROJECT_ROOT
    for persona in personas:
        node_name = f"agent_{persona.id}"
        builder.add_node(
            node_name,
            create_agent_node(
                persona,
                (agent_llms or {}).get(persona.id, llm),
                root_dir=graph_root,
                progress_callback=progress_callback,
            ),
        )
        builder.add_edge(previous_node, node_name)
        previous_node = node_name

    builder.add_node("round_summary", create_round_summary_node(llm, progress_callback))
    builder.add_node("final_summary", create_final_summary_node(llm, progress_callback))
    builder.add_edge(START, "moderator_question")
    builder.add_edge(previous_node, "round_summary")

    def should_continue(state: RoundtableState) -> Literal["continue", "finish"]:
        return "continue" if int(state["round"]) < int(state["max_rounds"]) else "finish"

    builder.add_conditional_edges(
        "round_summary",
        should_continue,
        {"continue": "moderator_question", "finish": "final_summary"},
    )
    builder.add_edge("final_summary", END)
    return builder.compile()


def run_roundtable(
    *,
    topic: str,
    council_name: str,
    rounds: int,
    llm: LLMClient | None = None,
    root_dir: Path | str | None = None,
    output_dir: Path | str = "logs",
    agent_llm_config_path: Path | str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> RoundtableState:
    if not topic.strip():
        raise ValueError("topic must not be empty")
    if rounds < 1:
        raise ValueError("rounds must be at least 1")

    root = Path(root_dir) if root_dir else PROJECT_ROOT
    council, personas = load_council_personas(council_name, root)
    if llm is not None:
        selected_llm = llm
        agent_llms: dict[str, LLMClient] = {persona.id: llm for persona in personas}
    else:
        selected_llm = create_llm_from_config(council.moderator_llm_config, create_llm("auto"))
        agent_llm_configs = load_agent_llm_configs(root, agent_llm_config_path)
        agent_llms = {
            persona.id: create_llm_from_config(
                {**persona.llm_config, **agent_llm_configs.get(persona.id, {})},
                selected_llm,
            )
            for persona in personas
        }

    app = build_roundtable_graph(
        council,
        personas,
        selected_llm,
        root_dir=root,
        agent_llms=agent_llms,
        progress_callback=progress_callback,
    )
    initial_state: RoundtableState = {
        "topic": topic,
        "round": 0,
        "max_rounds": rounds,
        "council_name": council.name,
        "council_description": council.description,
        "current_speaker": "",
        "personas": [persona.to_dict() for persona in personas],
        "messages": [],
        "round_summaries": [],
        "final_summary": "",
    }
    result: RoundtableState = app.invoke(initial_state)
    if progress_callback is not None:
        progress_callback(
            {
                "event": "start",
                "stage": "save_log",
                "label": "Saving Markdown report",
            }
        )
    log_path = save_markdown_log(result, output_dir=output_dir)
    if progress_callback is not None:
        progress_callback(
            {
                "event": "done",
                "stage": "save_log",
                "label": "Saved Markdown report",
                "log_path": log_path,
            }
        )
    result["log_path"] = log_path
    return result
