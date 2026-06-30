# agent_roundtable

A local multi-agent roundtable project.

You give the system a topic. Several expert agents take turns discussing it, a moderator asks follow-up questions and writes summaries, and the whole session is saved as a Markdown report.

This project is useful if you want to:

- Let multiple agents discuss one question from different perspectives.
- Give different experts their own books, papers, or long-form Markdown files for RAG.
- Give specific people multi-source corpora (books, posts, news, reports) for style + corpus driven roundtables.
- Configure which model each agent uses through a small local UI instead of editing code.

You do not need to understand LangGraph to use this project. Think of it as a configurable expert roundtable that runs on your own machine.

## What It Can Do

- Run a roundtable from the command line or from a local web UI.
- Set a separate `provider:model@effort` fallback chain for each agent.
- Keep real API keys in `.env` only. They are not written into JSON files or reports.
- Let domain experts read book-level corpora from `knowledge/experts/`; persona agents can read multi-source corpora from `knowledge/people/`.
- Show the provider and model used for each message, plus epistemic tags (local corpus hit, style-only, needs online verification).
- Rotate speaking order each round to reduce fixed-seat bias.
- Save every run to `logs/`.
- Run in `--mock` mode when you do not have API keys yet.

The project currently includes three built-in councils:

- `experts`: macroeconomics, investing, computing, philosophy, and history domain experts.
- `persona_inspired`: Buffett-, Munger-, Dalio-, Hayek-inspired style agents, plus Desmond Shum with multi-source corpus.
- `china_debt`: mixed council of macroeconomics + Desmond Shum + history for debt and balance-sheet discussions.

## 3-Minute Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Run a no-key mock demo:

```bash
python main.py --topic "How will AI affect investing and employment?" --council experts --rounds 1 --mock
```

Mixed council example:

```bash
python main.py --topic "How might China's debt problem evolve into balance-sheet recession?" --council china_debt --rounds 1 --mock
```

If the terminal prints a final summary and a line like this, the project is working:

```text
Log saved to: logs/How_will_AI_affect_investing_and_employment_20260701_123456.md
```

## Run the Local UI

For most users, the UI is the easiest entry point:

```bash
python -m streamlit run ui/app.py
```

Your browser should open a local page, usually:

```text
http://localhost:8501
```

In the UI you can:

- Choose a council: `experts`, `persona_inspired`, or `china_debt`.
- Set each agent's provider-chain.
- Copy common model chains from `config/model_example.json`.
- Continue a new session from a previous transcript.
- Save changes back to `config/agent_llms.json`.
- Enter a topic and run with real LLMs.
- Watch progress, current stage, and recent events during a run.
- Preview the final summary and transcript in the page.

`Mock mode` is off by default. Keep it off when testing real LLMs.

## Configure Real LLMs

Put real API keys in `.env`. Do not write real keys into JSON, YAML, README, logs, or screenshots.

OpenRouter example:

```env
OPENROUTER_API_KEY_1=your_first_key
OPENROUTER_API_KEY_2=your_second_key
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free,poolside/laguna-m.1:free,nvidia/nemotron-3-super-120b-a12b:free,openai/gpt-oss-120b:free
OPENROUTER_TIMEOUT=60
```

Gemini example:

```env
GEMINI_API_KEY_1=your_first_key
GEMINI_API_KEY_2=your_second_key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=4096
```

OpenAI and DeepSeek are also supported:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

DeepSeek uses an OpenAI-compatible API with `base_url=https://api.deepseek.com`. The UI does not try to fetch a model list endpoint for DeepSeek. It uses the official model names directly:

- `deepseek-v4-flash`
- `deepseek-v4-pro`
- `deepseek-chat` and `deepseek-reasoner` are legacy names scheduled for deprecation by DeepSeek on 2026-07-24 23:59 Beijing time.

Claude / Codex can use local CLI login state. Grok / Antigravity / Copilot can use a local CLIProxyAPI HTTP service. Chain syntax is documented in `config/model_example.json`:

```text
provider:model@effort
```

Example:

```text
claude:sonnet@high, codex:gpt-5.5@medium, gemini:gemini-2.5-flash
```

`@effort` only applies to CLI providers. Gemini / OpenRouter / DeepSeek ignore it.

### Optional: CLIProxyAPI

Provider-chain entries for `antigravity` / `grok` / `copilot` require a separate **CLIProxyAPI** service running locally. It is an independent open-source proxy that exposes your locally logged-in CLI accounts (Antigravity, Grok, Copilot, etc.) as OpenAI/Gemini/Claude-compatible HTTP endpoints.

- Project: <https://github.com/router-for-me/CLIProxyAPI>
- After starting it, the default listen address is `http://127.0.0.1:8317`.
- Point this project at it in `.env`:

```env
CLI_PROXY_BASE_URL=http://127.0.0.1:8317
CLI_PROXY_API_KEY=local        # must match an entry in CLIProxyAPI's api-keys
CLI_PROXY_TIMEOUT=600
```

If you do not use the `antigravity` / `grok` / `copilot` chains, CLIProxyAPI is **not** required — direct APIs (Gemini/OpenAI/OpenRouter/DeepSeek) and the local Claude/Codex CLIs do not depend on it.

## Per-Agent Model Config

The central config file is:

```text
config/agent_llms.json
```

It only answers one question: which LLM fallback chain each agent should use.

Example:

```json
{
  "agents": {
    "macroeconomics": {
      "provider_chain": "antigravity:gemini-3.1-pro-low, gemini:gemini-2.5-flash, claude:sonnet@high",
      "temperature": 0.3,
      "max_output_tokens": 4096
    },
    "computing": {
      "provider_chain": "codex:gpt-5.5@high, antigravity:gemini-3.5-flash-low, gemini:gemini-3.5-flash",
      "temperature": 0.25,
      "max_output_tokens": 4096
    }
  }
}
```

Real keys still come only from `.env`. `config/model_example.json` is a cheat sheet and is not loaded automatically at runtime.

If you edit models in the UI, the UI writes back to this JSON.

## Config Priority

When you run a roundtable, model config resolves in this order:

1. CLI `--mock`, `--provider`, or `--provider-chain`: temporary override for all agents.
2. `config/agent_llms.json`: per-agent model config.
3. The `llm` field in each agent YAML: fallback config.
4. Default models in `.env`, such as `OPENROUTER_MODEL` and `GEMINI_MODEL`.
5. If no key is available, `auto` falls back to local mock.

Practical advice:

- Quick demo: use `--mock`.
- Real use: edit `.env` and `config/agent_llms.json`.
- Temporary chain test: use `--provider-chain "claude:sonnet@high, gemini:gemini-2.5-flash"`.

## Project Layout

```text
agent_roundtable/
├── main.py                  # CLI entry point
├── ui/
│   └── app.py               # Streamlit local UI
├── roundtable/              # Business layer: how a roundtable runs
│   ├── graph.py             # Flow: moderator, agents, summaries
│   ├── agents.py            # What each agent does when speaking
│   ├── agent_llm_config.py  # Read/write config/agent_llms.json
│   ├── loader.py            # Load domain_experts / persona_inspired / councils
│   ├── discovery.py         # Auto-discover configured agents and knowledge dirs
│   ├── epistemics.py        # Epistemic tags: local corpus / style-only / verify online
│   ├── order.py             # Rotate speaking order across rounds
│   ├── logger.py            # Save Markdown reports
│   ├── prompts.py           # Prompt templates
│   └── state.py             # Runtime data structures
├── llm/                     # Model layer
├── config/
│   ├── domain_experts/      # Mainline experts: experts corpora
│   ├── persona_inspired/    # Persona agents: style-only or people corpora
│   ├── councils/            # Which agents sit at the table
│   ├── agent_llms.json
│   ├── model_example.json
│   └── model_catalog.json
├── knowledge/               # Local corpora (not committed to Git)
│   ├── experts/             # Book-level long-form texts by domain
│   └── people/              # Multi-source person corpora: book / x / news / report
├── scripts/
│   ├── parse_twitter_jsonl.py
│   └── import_person_source.py
├── rag/
├── vector_db/chroma/
├── logs/
├── tests/
├── requirements.txt
└── .env.example
```

## Key Folders

### `config/domain_experts/` and `config/persona_inspired/`

Agent "character cards" live here. Each YAML describes name, role, worldview, speaking style, strengths, weaknesses, and optional RAG corpus mapping.

Persona agents come in two flavors:

- **Style-only** (e.g. `buffett`, `munger`): persona-driven reasoning without local corpus.
- **Multi-source corpus** (e.g. `desmond_shum`): RAG over `knowledge/people/desmond_shum/`.

### `config/councils/`

Defines which agents sit at the table together.

Mixed councils like `china_debt` can combine domain experts and persona agents:

```yaml
members:
  - macroeconomics
  - desmond_shum
  - history
```

### `knowledge/`

Local corpora are split into two scopes:

**`knowledge/experts/`** — book-level texts for domain experts:

```text
knowledge/experts/macroeconomics/general_theory.md
```

**`knowledge/people/`** — multi-source person corpora:

```text
knowledge/people/desmond_shum/book/red_roulette.md
knowledge/people/desmond_shum/x/corpus.md
```

Real corpus files are not committed to GitHub. Only `.gitkeep` placeholders and `knowledge/README.md` are tracked.

## Add Your Own Markdown Sources

### For a domain expert

1. Put files under `knowledge/experts/macroeconomics/`.
2. Rebuild the index:

```bash
python -m rag.ingest --expert-name macroeconomics --embedding-provider keyword
```

### For a persona agent

1. Organize by source kind:

```text
knowledge/people/desmond_shum/book/
knowledge/people/desmond_shum/x/
knowledge/people/desmond_shum/news/
knowledge/people/desmond_shum/report/
```

2. Optional import helpers:

```bash
python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl \
  --command export-md --originals-only --min-length 300 --lang zh

python scripts/import_person_source.py desmond_shum book "/path/to/book.md"
```

3. Rebuild the index:

```bash
python -m rag.ingest --person-name desmond_shum --embedding-provider keyword
python -m rag.ingest --person-name desmond_shum --source-kind x --embedding-provider keyword
```

## RAG

RAG is "open-book" reasoning: the system retrieves relevant passages from your local corpora before the agent answers.

Recommended starting point:

```bash
python -m rag.ingest --embedding-provider keyword
```

`keyword` needs no extra API key. For person corpora, source kinds are weighted: `book` > `report` > `x` > `news`.

## Epistemic Tags

Each agent message in the report includes epistemic tags:

| Tag | Meaning |
| --- | --- |
| Local corpus | RAG retrieved relevant local material |
| No local hit | RAG configured but nothing relevant found |
| Style-only | No RAG; persona-driven reasoning |
| Verify online | Real-world data or current events; verify independently |

## Built-In Agents

Mainline `experts`:

| Agent ID | Role | RAG |
| --- | --- | --- |
| `macroeconomics` | Macroeconomics and institutions | Yes |
| `investing` | Long-term investing and business analysis | Yes |
| `computing` | AI and computing thought | Yes |
| `philosophy` | Philosophy and intellectual history | Yes |
| `history` | History and strategy | Yes |

`persona_inspired`:

| Agent ID | Style | RAG |
| --- | --- | --- |
| `buffett` | Buffett-inspired | No (corpus pending) |
| `munger` | Munger-inspired | No (corpus pending) |
| `dalio` | Dalio-inspired | No (corpus pending) |
| `hayek` | Hayek-inspired | No (corpus pending) |
| `desmond_shum` | Desmond Shum-inspired | Yes (multi-source) |

Mixed `china_debt`: `macroeconomics` + `desmond_shum` + `history`.

"Style-inspired" does not impersonate the real person or claim to represent their views.

## Common CLI Usage

```bash
python main.py --topic "How will AI affect investing?" --council experts --rounds 1 --mock
python main.py --topic "China debt and balance-sheet recession" --council china_debt --rounds 2 --mock
python main.py --topic "How will AI affect investing?" --council experts --rounds 1
python main.py --topic "Gold, USD, or Bitcoin?" --council experts --rounds 2 --provider openrouter
python main.py --topic "Will AI replace programmers?" --council experts --rounds 1 --provider-chain "claude:sonnet@high, gemini:gemini-2.5-flash"
```

## What Gets Committed to GitHub

`.gitignore` excludes:

- `.env` (real API keys)
- `knowledge/**/*.md`, `knowledge/**/*.txt`, `knowledge/**/*.pdf`, etc.
- `logs/**`
- `vector_db/chroma/**`, `indexes/**`

Safe to commit: code, README, config YAML/JSON, `knowledge/README.md`, and `knowledge/**/.gitkeep`.

## Developer Checks

```bash
python -m pytest -q
python -m json.tool config/agent_llms.json >/dev/null
python -m streamlit run ui/app.py
```

## Design Principles

- Long-term persona in YAML.
- Per-run model routing in JSON.
- Real API keys only in `.env`.
- Local corpora and run logs stay out of Git.
- Knowledge split into `experts/` (domain long-form) and `people/` (person multi-source).
- Start with `keyword` RAG before heavier embeddings.
- CLI and UI share the same runtime path.