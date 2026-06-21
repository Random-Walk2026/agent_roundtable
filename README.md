# agent_roundtable

一个本地运行的多 Agent 圆桌项目。

你给一个话题，系统会请几位“专家 Agent”轮流发言，主持人负责追问、总结，最后把整场讨论保存成一份 Markdown 报告。

这个项目适合做三类事：

- 想让多个不同视角的 Agent 一起讨论一个问题。
- 想给不同专家接入不同书籍、论文、长文资料，再做 RAG 检索。
- 想用一个简单 UI 配置每个 Agent 用什么模型，而不是每次改代码。

你不需要懂 LangGraph 才能用它。把它理解成一个“可配置的专家圆桌工具”就可以。

## 现在能做什么

- 用命令行或本地网页 UI 启动圆桌。
- 每个 Agent 可以单独设置 provider、模型、API key 环境变量名。
- API key 只放在 `.env`，不会写进 JSON 或日志。
- 主线专家可以读取各自的本地长文资料。
- 运行结果自动写入 `logs/`。
- 报告里会标明每条发言使用的 provider / model。
- 没有 API key 时可以用 `--mock` 先跑通流程。

当前项目有两条内置圆桌：

- `experts`：宏观、投资、AI、哲学、历史战略五位主题专家。
- `persona_inspired`：巴菲特、芒格、达利欧、哈耶克风格启发的副线。它目前只使用风格设定，不接 RAG。

## 3 分钟快速开始

先安装依赖：

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

没有 API key，也可以先跑一个模拟版本：

```bash
python main.py --topic "AI 对投资和就业的长期影响" --council experts --rounds 1 --mock
```

如果看到终端输出总结，并出现类似下面的提示，就说明项目已经跑通：

```text
Log saved to: logs/AI对投资和就业的长期影响_20260621_123456.md
```

## 用本地 UI 启动

更推荐普通用户从 UI 开始：

```bash
python -m streamlit run ui/app.py
```

浏览器会打开一个本地页面，通常是：

```text
http://localhost:8501
```

在 UI 里你可以做这些事：

- 选择圆桌：`experts` 或 `persona_inspired`。
- 设置每个 Agent 使用哪个 provider。
- 设置每个 Agent 使用哪个模型。
- 选择每个 Agent 使用 `.env` 里的哪个 API key。
- 点击按钮保存到 `configs/agent_llms.json`。
- 输入一个话题，直接调用真实 LLM 运行。
- 运行时查看进度条、当前阶段、最近事件；失败时直接看到错误详情。
- 在页面里预览最终总结和对话记录。

UI 里的 `Mock mode` 默认关闭。
如果你要测试真实 LLM，请保持它关闭。

## 配置真实 LLM

真实 API key 放在 `.env` 文件里。不要把真实 key 写到 JSON、YAML、README、日志或截图里。

OpenRouter 推荐这样命名：

```env
OPENROUTER_API_KEY_1=你的第一个_key
OPENROUTER_API_KEY_2=你的第二个_key
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free,poolside/laguna-m.1:free,nvidia/nemotron-3-super-120b-a12b:free,openai/gpt-oss-120b:free
OPENROUTER_TIMEOUT=60
```

Gemini 可以这样配置：

```env
GEMINI_API_KEY_1=你的第一个_key
GEMINI_API_KEY_2=你的第二个_key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MAX_OUTPUT_TOKENS=4096
```

OpenAI 和 DeepSeek 也预留了配置：

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

DeepSeek 使用 OpenAI 兼容接口，`base_url` 是 `https://api.deepseek.com`。UI 不会去请求 DeepSeek 的模型列表接口，而是内置官方模型名：

- `deepseek-v4-flash`
- `deepseek-v4-pro`
- `deepseek-chat`：兼容旧名，DeepSeek 文档说明将于北京时间 2026-07-24 23:59 弃用。
- `deepseek-reasoner`：兼容旧名，DeepSeek 文档说明将于北京时间 2026-07-24 23:59 弃用。

## 每个 Agent 用什么模型

集中配置文件是：

```text
configs/agent_llms.json
```

它只负责一件事：说明每个 Agent 背后调用什么 LLM。

例子：

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

这里的 `api_key_env` 不是 API key 本身。它只是告诉程序：“去 `.env` 里找这个名字对应的 key”。

如果你用 UI 修改模型，UI 会自动写回这个 JSON。

## 配置优先级

当你运行圆桌时，模型配置按下面的顺序生效：

1. 命令行 `--mock` 或 `--provider`：临时覆盖所有 Agent。
2. `configs/agent_llms.json`：每个 Agent 的集中模型配置。
3. Agent YAML 里的 `llm` 字段：后备配置。
4. `.env` 中的默认模型：比如 `OPENROUTER_MODEL`、`GEMINI_MODEL`。
5. 如果没有可用 key，`auto` 会退回本地 mock。

普通使用建议：

- 想快速体验：用 `--mock`。
- 想认真使用：改 `.env` 和 `configs/agent_llms.json`。
- 想临时测试某个 provider：用 `--provider openrouter` 或 `--provider gemini`。

## 项目结构

```text
agent_roundtable/
├── main.py                  # 命令行入口
├── ui/
│   └── app.py               # Streamlit 本地 UI
├── src/
│   ├── graph.py             # 圆桌流程：主持人、Agent、总结如何串起来
│   ├── agents.py            # 每个 Agent 发言时做什么
│   ├── llm.py               # OpenRouter / Gemini / OpenAI / DeepSeek / Mock 调用
│   ├── model_catalog.py     # UI 拉取模型列表、读取 .env key 名称
│   ├── agent_llm_config.py  # 读写 configs/agent_llms.json
│   ├── loader.py            # 读取 agents/ 和 councils/ 的 YAML
│   ├── logger.py            # 保存 Markdown 报告
│   ├── prompts.py           # 提示词模板
│   └── state.py             # 圆桌运行时的数据结构
├── agents/
│   ├── domain_experts/      # 主线专家：接 RAG
│   └── persona_inspired/    # 人物风格启发：当前不接 RAG
├── councils/                # 圆桌名单：哪些 Agent 一起上桌
├── configs/
│   └── agent_llms.json      # 每个 Agent 使用什么模型
├── knowledge/               # 你的本地书籍、论文、长文资料
├── rag/                     # 切分文档、建立索引、检索资料
├── vector_db/chroma/        # 本地生成的 RAG 索引
├── logs/                    # 每次运行生成的 Markdown 报告
├── tests/                   # 自动测试
├── requirements.txt         # Python 依赖
└── .env.example             # 环境变量模板
```

## 几个关键文件夹是什么意思

### `agents/`

这里放 Agent 的“角色卡”。

一个 Agent YAML 会描述：

- 名称
- 角色
- 世界观
- 说话风格
- 优点和盲点
- RAG 对应的知识目录

例如 `agents/domain_experts/macro_economist.yaml` 代表“宏观经济与制度专家”。

### `councils/`

这里放“哪几个人一起开会”。

例如 `councils/experts.yaml`：

```yaml
members:
  - macro_economist
  - investing_master
  - ai_researcher
  - philosophy_expert
  - history_strategist
```

这表示这五个 Agent 会按顺序发言。

### `configs/`

这里放运行配置。
目前最重要的是 `configs/agent_llms.json`，它负责每个 Agent 用什么模型。

### `knowledge/`

这里放你自己的本地知识资料。

注意：真正的书籍、论文、长文文件默认不会提交到 GitHub。
这是为了避免误传版权内容、私人资料或太大的文件。

### `logs/`

这里放每次圆桌生成的报告。

日志文件也不会提交到 GitHub。
它们是你的本地运行结果。

## 如何加入自己的 Markdown 资料

假设你想给“宏观经济专家”加入资料：

1. 找到对应目录：

```text
knowledge/macro_economist/
```

2. 建一个子文件夹，比如：

```text
knowledge/macro_economist/keynes/
```

3. 把你的 `.md` 长文放进去：

```text
knowledge/macro_economist/keynes/general_theory.md
```

4. 重建本地 RAG 索引：

```bash
python -m rag.ingest --expert-name macro_economist --embedding-provider keyword
```

5. 再运行圆桌：

```bash
python main.py --topic "财政政策是否能稳定就业？" --council experts --rounds 1
```

运行时，`macro_economist` 会优先从自己的目录检索相关资料。
如果检索到资料，报告里会显示引用来源。

## RAG 是什么

你可以把 RAG 理解成“开卷考试”。

普通 LLM 只靠模型自己记得的东西回答。
RAG 会先从你放进 `knowledge/` 的资料里找相关段落，再把这些段落交给 Agent 参考。

这个项目当前推荐先用 `keyword`：

```bash
python -m rag.ingest --embedding-provider keyword
```

`keyword` 不需要额外 API key，适合入门和本地测试。

如果你以后要做更强的语义检索，可以再接 embedding 模型。项目里已经预留了 `mock`、`openai`、`openrouter` 等 embedding provider 的入口，但入门不需要先碰这些。

## 当前内置专家

主线 `experts`：

| Agent ID | 角色 | RAG |
| --- | --- | --- |
| `macro_economist` | 宏观经济与制度专家 | 是 |
| `investing_master` | 长期投资与商业分析专家 | 是 |
| `ai_researcher` | 人工智能与计算思想专家 | 是 |
| `philosophy_expert` | 哲学与思想史专家 | 是 |
| `history_strategist` | 历史与战略专家 | 是 |

副线 `persona_inspired`：

| Agent ID | 风格 | RAG |
| --- | --- | --- |
| `buffett_inspired` | 巴菲特风格启发 | 否 |
| `munger_inspired` | 芒格风格启发 | 否 |
| `dalio_inspired` | 达利欧风格启发 | 否 |
| `hayek_inspired` | 哈耶克风格启发 | 否 |

这里的“风格启发”不是冒充本人，也不代表本人观点。它只是用类似的思考风格组织回答。

## 如何新增一个专家

假设你要新增一个“能源专家”：

1. 新建 Agent 文件：

```text
agents/domain_experts/energy_expert.yaml
```

2. 写入角色卡：

```yaml
name: "Energy Expert"
role: "能源与产业政策专家"
worldview: "从能源供需、基础设施、地缘政治和技术替代分析问题"
speaking_style: "清晰、谨慎，先讲约束再讲判断"
strengths:
  - "能源供需分析"
  - "产业链拆解"
weaknesses:
  - "可能低估金融市场短期波动"
catchphrases:
  - "先看能源约束"
rag_expert_name: "energy_expert"
agent_type: "domain_expert"
profile:
  focus:
    - "能源安全"
    - "电力系统"
    - "油气与新能源"
```

3. 新建知识目录：

```text
knowledge/energy_expert/
```

4. 在 `councils/experts.yaml` 或新 council 里加入：

```yaml
members:
  - energy_expert
```

5. 在 `configs/agent_llms.json` 里给它配置模型：

```json
{
  "provider": "openrouter",
  "model": "nvidia/nemotron-3-super-120b-a12b:free",
  "api_key_env": "OPENROUTER_API_KEY_1"
}
```

6. 放入资料并重建索引：

```bash
python -m rag.ingest --expert-name energy_expert --embedding-provider keyword
```

提示：当前测试固定约束了内置专家列表。如果你 fork 后要长期加入新专家，需要同步更新 `tests/test_structure.py`。

## 命令行常用方式

模拟运行，不需要 API key：

```bash
python main.py --topic "AI 对投资和就业的长期影响" --council experts --rounds 1 --mock
```

真实 LLM 运行，按 `configs/agent_llms.json` 为每个 Agent 分配模型：

```bash
python main.py --topic "AI 对投资和就业的长期影响" --council experts --rounds 1
```

临时强制所有 Agent 使用 OpenRouter：

```bash
python main.py --topic "黄金、美元、比特币哪个更适合避险？" --council experts --rounds 2 --provider openrouter
```

临时强制所有 Agent 使用某个模型：

```bash
python main.py --topic "AI 会不会取代程序员？" --council experts --rounds 1 --provider openrouter --model "openai/gpt-oss-120b:free"
```

指定输出目录：

```bash
python main.py --topic "AI 对就业的影响" --council experts --rounds 1 --output-dir logs
```

## 生成的报告在哪里

报告保存在 `logs/`。

文件名会根据话题和时间自动生成，例如：

```text
logs/AI对投资和就业的长期影响_20260621_123456.md
```

报告内容包括：

- 每轮主持人的问题
- 每个 Agent 的发言
- 每条发言使用的 provider / model
- RAG 引用来源
- 每轮小结
- 最终总结

## 开源时要注意什么

默认 `.gitignore` 已经帮你避开几类不适合上传的内容：

- `.env`：真实 API key
- `knowledge/**/*.md`：本地书籍、论文、长文
- `logs/**`：运行报告
- `vector_db/chroma/**`：本地索引
- `__pycache__/`、`.pytest_cache/` 等临时文件

可以提交的通常是：

- 代码
- README
- `agents/*.yaml`
- `councils/*.yaml`
- `configs/agent_llms.json`
- `knowledge/README.md`
- `.gitkeep` 占位文件

如果你的 `knowledge/` 里有版权书籍或私人资料，不要提交。

## 常见问题

### 我不会配置 API key，能不能先试？

可以。用 `--mock`：

```bash
python main.py --topic "测试一下" --council experts --rounds 1 --mock
```

### UI 里为什么看不到模型列表？

先检查：

- `.env` 里有没有对应 key。
- UI 里选的 `api_key_env` 是否和 `.env` 变量名一致。
- 是否打开了 `Fetch model lists with API keys`。

如果模型列表拉不到，仍然可以手动输入模型名。

### 为什么真实 LLM 运行失败？

常见原因：

- API key 没填。
- `api_key_env` 写错。
- 模型名不可用。
- provider 限流或网络失败。
- 免费模型暂时不可用。

先用 `--mock` 确认项目流程没问题，再检查真实 LLM 配置。

### 我放了 Markdown，为什么没有引用？

可能是：

- 没有运行 `python -m rag.ingest` 重建索引。
- Markdown 放错专家目录。
- Agent YAML 里的 `rag_expert_name` 和 `knowledge/` 目录名不一致。
- 话题和资料内容相关性不高。

### 为什么测试要求知识库是长文？

这个项目的定位是“书籍级长文驱动的专家圆桌”。
短笔记、临时摘要、抓取片段不适合放进 `knowledge/` 作为正式语料。

当前测试会保护这个约定。你自己 fork 后如果要支持短资料，可以调整测试和知识库规则。

## 开发者验证

运行测试：

```bash
python -m pytest -q
```

检查 JSON 是否合法：

```bash
python -m json.tool configs/agent_llms.json >/dev/null
```

启动 UI：

```bash
python -m streamlit run ui/app.py
```

## 项目设计原则

- Agent 的长期人设放在 YAML。
- 每次实际调用什么模型放在 JSON。
- 真实 API key 只放 `.env`。
- 本地书籍和运行日志不进 Git。
- 先用 `keyword` RAG 跑通，再考虑更复杂的 embedding。
- CLI 和 UI 共用同一条运行链路，避免两套逻辑不一致。
