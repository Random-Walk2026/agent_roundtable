from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_llm_config import (  # noqa: E402
    DEFAULT_DESCRIPTION,
    load_agent_llm_config_document,
    save_agent_llm_config_document,
)
from src.graph import run_roundtable  # noqa: E402
from src.llm import MockLLM  # noqa: E402
from src.loader import load_council_personas  # noqa: E402
from src.model_catalog import (  # noqa: E402
    ModelCatalogResult,
    fallback_model_options,
    fetch_model_options,
    list_api_key_env_names,
)


PROVIDERS = ["openrouter", "gemini", "openai", "deepseek"]
DEFAULT_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY_1",
    "gemini": "GEMINI_API_KEY_1",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


st.set_page_config(
    page_title="Agent Roundtable",
    page_icon="",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        background: rgba(15, 23, 42, 0.38);
    }
    .agent-row {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 8px;
        padding: 0.85rem 0.9rem 0.35rem 0.9rem;
        margin-bottom: 0.75rem;
        background: rgba(15, 23, 42, 0.24);
    }
    .muted { color: rgba(226, 232, 240, 0.72); font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _council_names() -> list[str]:
    names = sorted(path.stem for path in (PROJECT_ROOT / "councils").glob("*.yaml"))
    return names or ["experts"]


def _select_index(options: list[str], value: str | None) -> int:
    if value in options:
        return options.index(value or "")
    return 0


def _provider_options(current_provider: str | None) -> list[str]:
    options = list(PROVIDERS)
    if current_provider and current_provider not in options:
        options.insert(0, current_provider)
    return options


def _key_env_options(provider: str, current_key_env: str | None) -> list[str]:
    options = list_api_key_env_names(provider, root_dir=PROJECT_ROOT)
    fallback = current_key_env or DEFAULT_KEY_ENV.get(provider, "")
    if fallback and fallback not in options:
        options.insert(0, fallback)
    return options or [""]


@st.cache_data(ttl=600, show_spinner=False)
def _cached_model_options(
    provider: str,
    api_key_env: str,
    current_model: str,
    fetch_online: bool,
) -> ModelCatalogResult:
    if fetch_online:
        return fetch_model_options(
            provider,
            api_key_env=api_key_env or None,
            current_model=current_model,
            root_dir=PROJECT_ROOT,
        )
    return ModelCatalogResult(
        fallback_model_options(provider, current_model=current_model, root_dir=PROJECT_ROOT),
        "official" if provider == "deepseek" else "env",
        None,
    )


def _model_options(
    provider: str,
    api_key_env: str,
    current_model: str,
    fetch_online: bool,
) -> tuple[list[str], ModelCatalogResult]:
    result = _cached_model_options(provider, api_key_env, current_model, fetch_online)
    options = list(result.models)
    if current_model and current_model not in options:
        options.insert(0, current_model)
    return options or [current_model or ""], result


def _render_agent_llm_row(
    agent_id: str,
    display_name: str,
    role: str,
    initial_config: dict[str, Any],
    *,
    fetch_online: bool,
) -> dict[str, str]:
    st.markdown('<div class="agent-row">', unsafe_allow_html=True)
    heading, provider_col, key_col, model_col = st.columns([1.4, 1.05, 1.15, 1.8])
    with heading:
        st.markdown(f"**{display_name}**")
        st.markdown(f'<span class="muted">{agent_id} · {role}</span>', unsafe_allow_html=True)

    current_provider = str(initial_config.get("provider") or "openrouter")
    provider_options = _provider_options(current_provider)
    with provider_col:
        provider = st.selectbox(
            "Provider",
            provider_options,
            index=_select_index(provider_options, current_provider),
            key=f"{agent_id}_provider",
        )

    current_key_env = str(initial_config.get("api_key_env") or DEFAULT_KEY_ENV.get(provider, ""))
    key_options = _key_env_options(provider, current_key_env)
    with key_col:
        api_key_env = st.selectbox(
            "API key env",
            key_options,
            index=_select_index(key_options, current_key_env),
            key=f"{agent_id}_{provider}_api_key_env",
        )

    initial_provider = str(initial_config.get("provider") or "openrouter")
    initial_model = str(initial_config.get("model") or "")
    current_model = initial_model if provider == initial_provider else ""
    model_options, model_result = _model_options(
        provider,
        api_key_env,
        current_model,
        fetch_online,
    )
    with model_col:
        model_choice = st.selectbox(
            "Model",
            model_options,
            index=_select_index(model_options, current_model),
            key=f"{agent_id}_{provider}_model_select",
        )
        model = st.text_input(
            "Actual request model",
            value=model_choice,
            key=f"{agent_id}_{provider}_model",
            label_visibility="collapsed",
        )
        if model_result.error:
            st.caption(f"Model list fallback: {model_result.error}")
        else:
            st.caption(f"Model source: {model_result.source}")

    st.markdown("</div>", unsafe_allow_html=True)
    return {
        "provider": provider,
        "model": model,
        "api_key_env": api_key_env,
    }


def _merge_agent_configs(
    current_agents: dict[str, dict[str, Any]],
    updates: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    merged = {agent_id: dict(config) for agent_id, config in current_agents.items()}
    for agent_id, config in updates.items():
        merged[agent_id] = {
            key: value
            for key, value in config.items()
            if value is not None and value != ""
        }
    return merged


def _save_configs(agents: dict[str, dict[str, Any]], description: str) -> Path:
    return save_agent_llm_config_document(
        PROJECT_ROOT,
        agents,
        description=description or DEFAULT_DESCRIPTION,
    )


def _progress_event_line(event: dict[str, Any]) -> str:
    event_name = str(event.get("event", "event")).upper()
    stage = str(event.get("stage", ""))
    label = str(event.get("label", ""))
    return f"{event_name} [{stage}] {label}".strip()


st.title("Agent Roundtable")
st.caption("Configure per-agent LLM routing, run a real roundtable, and read the generated Markdown report.")

config_document = load_agent_llm_config_document(PROJECT_ROOT)
saved_agent_configs: dict[str, dict[str, Any]] = config_document["agents"]

with st.sidebar:
    st.header("Run Setup")
    council_names = _council_names()
    council_name = st.selectbox(
        "Council",
        council_names,
        index=_select_index(council_names, "experts"),
    )
    rounds = st.number_input("Rounds", min_value=1, max_value=5, value=1, step=1)
    fetch_online = st.toggle("Fetch model lists with API keys", value=False)
    use_mock = st.toggle("Mock mode", value=False)
    st.caption("Mock mode is off by default. Real LLM calls use configs/agent_llms.json and .env.")

council, personas = load_council_personas(council_name, PROJECT_ROOT)

metric_cols = st.columns(3)
metric_cols[0].metric("Council", council.name)
metric_cols[1].metric("Agents", len(personas))
metric_cols[2].metric("Mode", "Mock" if use_mock else "Real LLM")

st.subheader("Agent LLM Routing")
st.caption("The UI saves provider, model, and api_key_env only. API key values stay in .env.")

updates: dict[str, dict[str, str]] = {}
for persona in personas:
    initial = {**persona.llm_config, **saved_agent_configs.get(persona.id, {})}
    updates[persona.id] = _render_agent_llm_row(
        persona.id,
        persona.name,
        persona.role,
        initial,
        fetch_online=fetch_online,
    )

merged_agent_configs = _merge_agent_configs(saved_agent_configs, updates)

save_col, json_col = st.columns([1, 3])
with save_col:
    if st.button("Save LLM JSON", type="primary", use_container_width=True):
        path = _save_configs(merged_agent_configs, str(config_document.get("description", "")))
        st.success(f"Saved: {path.relative_to(PROJECT_ROOT)}")
with json_col:
    with st.expander("Preview configs/agent_llms.json"):
        st.json(
            {
                "description": str(config_document.get("description", DEFAULT_DESCRIPTION)),
                "agents": merged_agent_configs,
            },
            expanded=False,
        )

st.divider()
st.subheader("Run Roundtable")

default_topic = "AI 对投资和就业的长期影响"
topic = st.text_area("Topic", value=default_topic, height=90)

run_disabled = not topic.strip()
if st.button("Run With Current Config", type="primary", disabled=run_disabled):
    total_steps = 1 + int(rounds) * (len(personas) + 2) + 2
    progress_state = {"completed": 0}
    progress_events: list[dict[str, Any]] = []
    progress_bar = st.progress(0.0, text="Preparing roundtable run...")
    status_slot = st.empty()
    event_log_slot = st.empty()

    def render_progress_log() -> None:
        if not progress_events:
            return
        event_log_slot.code(
            "\n".join(_progress_event_line(event) for event in progress_events[-12:]),
            language="text",
        )

    def mark_step_done(label: str) -> None:
        progress_state["completed"] = min(progress_state["completed"] + 1, total_steps)
        progress_bar.progress(
            min(progress_state["completed"] / total_steps, 1.0),
            text=label,
        )
        status_slot.success(label)

    def handle_progress(event: dict[str, Any]) -> None:
        progress_events.append(event)
        label = str(event.get("label") or event.get("stage") or "Running")
        if event.get("event") == "done":
            mark_step_done(label)
        else:
            progress_bar.progress(
                min(progress_state["completed"] / total_steps, 0.99),
                text=label,
            )
            status_slot.info(label)
        render_progress_log()

    try:
        saved_path = _save_configs(
            merged_agent_configs,
            str(config_document.get("description", "")),
        )
        save_label = f"Saved current LLM routing to {saved_path.relative_to(PROJECT_ROOT)}"
        progress_events.append(
            {
                "event": "done",
                "stage": "save_config",
                "label": save_label,
            }
        )
        mark_step_done(save_label)
        render_progress_log()

        result = run_roundtable(
            topic=topic,
            council_name=council_name,
            rounds=int(rounds),
            llm=MockLLM() if use_mock else None,
            root_dir=PROJECT_ROOT,
            output_dir=PROJECT_ROOT / "logs",
            progress_callback=handle_progress,
        )
    except Exception as exc:
        progress_events.append(
            {
                "event": "error",
                "stage": "run_roundtable",
                "label": str(exc),
            }
        )
        progress_bar.progress(
            min(progress_state["completed"] / total_steps, 1.0),
            text="Run failed",
        )
        status_slot.error(f"Run failed: {exc}")
        render_progress_log()
        st.exception(exc)
        st.stop()

    progress_bar.progress(1.0, text="Run complete")
    status_slot.success("Run complete")
    st.success(f"Log saved to {Path(result['log_path']).relative_to(PROJECT_ROOT)}")
    st.markdown("### Final Summary")
    st.markdown(result.get("final_summary", ""))
    with st.expander("Progress Events"):
        st.json(progress_events)
    with st.expander("Transcript Messages"):
        for message in result.get("messages", []):
            speaker = message.get("speaker", "Unknown")
            llm_provider = message.get("llm_provider", "unknown")
            llm_model = message.get("llm_model", "unknown")
            st.markdown(f"**{speaker}** · `{llm_provider}` / `{llm_model}`")
            st.markdown(str(message.get("content", "")))
            st.divider()
