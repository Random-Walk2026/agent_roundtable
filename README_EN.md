# agent_roundtable

A local multi-agent roundtable project.

You give the system a topic. Several expert agents take turns discussing it, a moderator asks follow-up questions and writes summaries, and the whole session is saved as a Markdown report.

This project is useful if you want to:

- Let multiple agents discuss one question from different perspectives.
- Give different experts their own books, papers, or long-form Markdown files for RAG.
- Configure which model each agent uses through a small local UI instead of editing code.

You do not need to understand LangGraph to use this project. Think of it as a configurable expert roundtable that runs on your own machine.

## What It Can Do

- Run a roundtable from the command line or from a local web UI.
- Set a separate provider, model, and API key environment variable for each agent.
- Keep real API keys in `.env` only. They are not written into JSON files or reports.
- Let domain experts read their own local long-form knowledge folders.
- Save every run to `logs/`.
- Show the provider and model used for each message in the report.
- Run in `--mock` mode when you do not have API keys yet.

The project currently includes two built-in councils:

- `experts`: macroeconomics, investing, AI research, philosophy, and historical strategy experts.
- `persona_inspired`: Buffett-, Munger-, Dalio-, and Hayek-inspired style agents. This side mode is style-only for now and does not use RAG yet.

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

If the terminal prints a final summary and a line like this, the project is working:

```text
Log saved to: logs/How_will_AI_affect_investing_and_employment_20260621_123456.md
```

## Start The Local UI

For most users, the UI is the easiest entry point:

```bash
python -m streamlit run ui/app.py
```

Your browser should open a local page, usually:

```text
http://localhost:8501
```

In the UI you can:

- Choose a council: `experts` or `persona_inspired`.
- Set the provider for each agent.
- Set the model for each agent.
- Choose which `.env` API key variable each agent should use.
- Save changes to `configs/agent_llms.json`.
- Enter a topic and run a real LLM roundtable.
- Watch a progress bar, current stage, recent events, and error details if a run fails.
- Preview the final summary and transcript.

The UI `Mock mode` toggle is off by default. Leave it off when you want to test real LLM calls.

## Configure Real LLMs

Put real API keys in `.env`. Do not put real keys in JSON, YAML, README files, logs, screenshots, or issue comments.

Recommended OpenRouter naming:

```env
OPENROUTER_API_KEY_1=your_first_key
OPENROUTER_API_KEY_2=your_second_key
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free,poolside/laguna-m.1:free,nvidia/nemotron-3-super-120b-a12b:free,openai/gpt-oss-120b:free
OPENROUTER_TIMEOUT=60
```

Gemini:

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
- `deepseek-chat`: legacy compatibility name, scheduled by DeepSeek for deprecation on 2026-07-24 23:59 Beijing time.
- `deepseek-reasoner`: legacy compatibility name, scheduled by DeepSeek for deprecation on 2026-07-24 23:59 Beijing time.

## Which Model Does Each Agent Use?

The central configuration file is:

```text
configs/agent_llms.json
```

This file has one job: define which LLM each agent calls.

Example:

```json
{
  "agents": {
    "macro_economist": {
      "provider": "openrouter",
      "model": "nvidia/nemotron-3-super-120b-a12b:free",
      "api_key_env": "OPENROUTER_API_KEY_1"
    },
    "ai_researcher": {
      "provider": "openrouter",
      "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
      "api_key_env": "OPENROUTER_API_KEY_1"
    }
  }
}
```

`api_key_env` is not the API key itself. It is the name of the variable the program should read from `.env`.

If you change models in the UI, the UI writes the result back to this JSON file.

## Configuration Priority

When you run a roundtable, model configuration is resolved in this order:

1. Command-line `--mock` or `--provider`: temporarily overrides all agents.
2. `configs/agent_llms.json`: per-agent model routing.
3. The `llm` field inside an agent YAML file: fallback configuration.
4. Default models from `.env`, such as `OPENROUTER_MODEL` or `GEMINI_MODEL`.
5. If no usable key is found, `auto` falls back to the local mock model.

Recommended use:

- First demo: use `--mock`.
- Normal use: edit `.env` and `configs/agent_llms.json`, or use the UI.
- Temporary provider test: use `--provider openrouter` or `--provider gemini`.

## Project Structure

```text
agent_roundtable/
├── main.py                  # Command-line entry point
├── ui/
│   └── app.py               # Streamlit local UI
├── src/
│   ├── graph.py             # Roundtable flow: moderator, agents, summaries
│   ├── agents.py            # What each agent does during a turn
│   ├── llm.py               # OpenRouter / Gemini / OpenAI / DeepSeek / Mock clients
│   ├── model_catalog.py     # Reads .env key names and fetches model lists for the UI
│   ├── agent_llm_config.py  # Reads and writes configs/agent_llms.json
│   ├── loader.py            # Loads YAML files from agents/ and councils/
│   ├── logger.py            # Saves Markdown reports
│   ├── prompts.py           # Prompt templates
│   └── state.py             # Runtime state data structures
├── agents/
│   ├── domain_experts/      # Main experts with RAG
│   └── persona_inspired/    # Style-inspired agents, no RAG for now
├── councils/                # Council member lists
├── configs/
│   └── agent_llms.json      # Per-agent model routing
├── knowledge/               # Your local books, papers, and long-form Markdown
├── rag/                     # Document chunking, indexing, and retrieval
├── vector_db/chroma/        # Generated local RAG indexes
├── logs/                    # Generated Markdown reports
├── tests/                   # Automated tests
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variable template
```

## What The Main Folders Mean

### `agents/`

This folder contains agent "profile cards".

An agent YAML file describes:

- name
- role
- worldview
- speaking style
- strengths and blind spots
- the matching RAG knowledge folder

For example, `agents/domain_experts/macro_economist.yaml` defines the macroeconomics and institutions expert.

### `councils/`

This folder defines who joins a roundtable.

For example, `councils/experts.yaml` includes:

```yaml
members:
  - macro_economist
  - investing_master
  - ai_researcher
  - philosophy_expert
  - history_strategist
```

These five agents speak in that order.

### `configs/`

This folder contains runtime configuration. The most important file is `configs/agent_llms.json`, which controls the model used by each agent.

### `knowledge/`

This folder is where you place your local knowledge files.

Actual books, papers, and long-form Markdown files are ignored by Git by default. This helps avoid accidentally uploading copyrighted material, private notes, or large files.

### `logs/`

This folder stores generated reports from each run.

Log files are local run results and are ignored by Git.

## Add Your Own Markdown Knowledge

Suppose you want to give the macroeconomics expert more material.

1. Find the matching folder:

```text
knowledge/macro_economist/
```

2. Create a subfolder:

```text
knowledge/macro_economist/keynes/
```

3. Add your `.md` long-form file:

```text
knowledge/macro_economist/keynes/general_theory.md
```

4. Rebuild the local RAG index:

```bash
python -m rag.ingest --expert-name macro_economist --embedding-provider keyword
```

5. Run the roundtable again:

```bash
python main.py --topic "Can fiscal policy stabilize employment?" --council experts --rounds 1
```

At runtime, `macro_economist` retrieves from its own knowledge folder. If relevant material is found, the report shows source references.

## What Is RAG?

You can think of RAG as an open-book exam.

A normal LLM answers from the model's internal knowledge. With RAG, the system first searches your local `knowledge/` files, then gives relevant passages to the agent as reference material.

For this project, start with `keyword`:

```bash
python -m rag.ingest --embedding-provider keyword
```

`keyword` does not require an embedding API key, so it is the easiest path for local testing.

If you later want stronger semantic retrieval, you can connect an embedding model. The project already has entry points for `mock`, `openai`, and `openrouter` embedding providers, but beginners do not need them first.

## Built-In Agents

Main `experts` council:

| Agent ID | Role | RAG |
| --- | --- | --- |
| `macro_economist` | Macroeconomics and institutions expert | Yes |
| `investing_master` | Long-term investing and business analysis expert | Yes |
| `ai_researcher` | AI and computational thinking expert | Yes |
| `philosophy_expert` | Philosophy and intellectual history expert | Yes |
| `history_strategist` | History and strategy expert | Yes |

Side `persona_inspired` council:

| Agent ID | Style | RAG |
| --- | --- | --- |
| `buffett_inspired` | Buffett-inspired style | No |
| `munger_inspired` | Munger-inspired style | No |
| `dalio_inspired` | Dalio-inspired style | No |
| `hayek_inspired` | Hayek-inspired style | No |

"Inspired" means the agent uses a similar reasoning style. It does not impersonate the person or claim to represent their views.

## Add A New Expert

Suppose you want to add an energy expert.

1. Create a new agent file:

```text
agents/domain_experts/energy_expert.yaml
```

2. Write the profile card:

```yaml
name: "Energy Expert"
role: "Energy and industrial policy expert"
worldview: "Analyzes questions through energy supply, infrastructure, geopolitics, and technology substitution"
speaking_style: "Clear and careful; explains constraints before conclusions"
strengths:
  - "Energy supply and demand analysis"
  - "Industrial chain breakdown"
weaknesses:
  - "May underestimate short-term financial market volatility"
catchphrases:
  - "Start with the energy constraint"
rag_expert_name: "energy_expert"
agent_type: "domain_expert"
profile:
  focus:
    - "Energy security"
    - "Power systems"
    - "Oil, gas, and renewables"
```

3. Create the matching knowledge folder:

```text
knowledge/energy_expert/
```

4. Add the new agent to `councils/experts.yaml` or to a new council:

```yaml
members:
  - energy_expert
```

5. Add model routing in `configs/agent_llms.json`:

```json
{
  "provider": "openrouter",
  "model": "nvidia/nemotron-3-super-120b-a12b:free",
  "api_key_env": "OPENROUTER_API_KEY_1"
}
```

6. Add Markdown files and rebuild the index:

```bash
python -m rag.ingest --expert-name energy_expert --embedding-provider keyword
```

Note: the current tests intentionally lock the built-in expert list. If you fork the project and permanently add new experts, update `tests/test_structure.py` as well.

## Common Command-Line Usage

Mock run, no API key needed:

```bash
python main.py --topic "How will AI affect investing and employment?" --council experts --rounds 1 --mock
```

Real LLM run using `configs/agent_llms.json`:

```bash
python main.py --topic "How will AI affect investing and employment?" --council experts --rounds 1
```

Temporarily force all agents to use OpenRouter:

```bash
python main.py --topic "Gold, USD, or Bitcoin: which is better for hedging?" --council experts --rounds 2 --provider openrouter
```

Temporarily force all agents to use one model:

```bash
python main.py --topic "Will AI replace programmers?" --council experts --rounds 1 --provider openrouter --model "openai/gpt-oss-120b:free"
```

Choose an output directory:

```bash
python main.py --topic "AI and employment" --council experts --rounds 1 --output-dir logs
```

## Where Reports Are Saved

Reports are saved under `logs/`.

The filename is generated from the topic and timestamp:

```text
logs/How_will_AI_affect_investing_and_employment_20260621_123456.md
```

Each report can include:

- moderator questions
- each agent's answer
- provider / model used by each message
- RAG source references
- round summaries
- final summary

## Open Source Safety Notes

The default `.gitignore` helps keep sensitive or local files out of Git:

- `.env`: real API keys
- `knowledge/**/*.md`: local books, papers, and long-form corpora
- `logs/**`: generated reports
- `vector_db/chroma/**`: generated local indexes
- `__pycache__/`, `.pytest_cache/`, and other temporary files

Usually safe to commit:

- source code
- README files
- `agents/*.yaml`
- `councils/*.yaml`
- `configs/agent_llms.json`
- `knowledge/README.md`
- `.gitkeep` placeholder files

Do not commit copyrighted books, private notes, or real API keys.

## Troubleshooting

### I do not have an API key yet. Can I try it?

Yes. Use `--mock`:

```bash
python main.py --topic "Test run" --council experts --rounds 1 --mock
```

### Why does the UI not show a model list?

Check:

- Does `.env` contain the selected API key variable?
- Does the UI `api_key_env` value match the variable name in `.env`?
- Did you enable `Fetch model lists with API keys`?

If model fetching fails, you can still type the model name manually.

### Why did a real LLM run fail?

Common causes:

- API key is empty.
- `api_key_env` is wrong.
- model name is unavailable.
- provider rate limits or network failures.
- a free model is temporarily unavailable.

First run with `--mock` to confirm the project flow works, then check the real LLM configuration.

### I added Markdown. Why are there no references?

Common causes:

- You did not run `python -m rag.ingest` after adding files.
- The Markdown file is in the wrong expert folder.
- The agent YAML `rag_expert_name` does not match the folder under `knowledge/`.
- The discussion topic is not related to the material.

### Why does the test suite require long-form knowledge files?

This project is designed around book-level, long-form expert corpora.

Short notes, temporary summaries, and scraped snippets are not meant to be formal `knowledge/` sources in the current design.

If you fork the project and want short-note support, update the tests and knowledge rules accordingly.

## Developer Checks

Run tests:

```bash
python -m pytest -q
```

Check the JSON config:

```bash
python -m json.tool configs/agent_llms.json >/dev/null
```

Start the UI:

```bash
python -m streamlit run ui/app.py
```

## Design Principles

- Long-term agent identity lives in YAML.
- Actual model routing lives in JSON.
- Real API keys live only in `.env`.
- Local corpora and generated reports stay out of Git.
- Start with `keyword` RAG before using more complex embeddings.
- CLI and UI share the same runtime path so behavior stays consistent.
