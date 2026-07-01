---
name: person-crawl-agent
description: >
  MUST USE when the user wants to crawl/import X(Twitter) or Weibo posts for a
  persona agent in agent_roundtable, refresh knowledge/people/<person_id>/x or
  weibo corpora, or run the person_crawl_agent. Triggers: 爬人物/抓推文/
  更新语料/同步X/同步微博/crawl person/import corpus/person_crawl_agent/
  crawl_person_sources. Uses the local spider project (SPIDER_BASE_PATH) and
  writes Markdown into knowledge/people/<person_id>/{x,weibo}/.
metadata:
  scope: project
---

# person_crawl_agent — 人物 X/微博语料采集 Agent

这个 skill 负责把 **spider 项目** 的爬取结果，导入到 **agent_roundtable** 的 `knowledge/people/<person_id>/` 目录，供人物 Agent RAG 使用。

## 常驻规则

1. **先查注册表**：真实人物与账号映射在本地 `config/person_crawl.yaml`（不进 Git）。仓库里只有 `config/person_crawl.example.yaml` 占位示例。执行前用 `--list` 确认 `person_id`、X handle、微博 UID。
2. **先 dry-run 再真跑**：`python scripts/crawl_person_sources.py <person_id> --dry-run`
3. **不要泄露 cookie**：spider 的 `settings.json` 含登录态，只在本地使用，不要回显到日志。
4. **只爬用户明确指定的人物**，不要凭空猜测账号。
5. **声明你在用什么**：例如「调用 spider x runner → parse_twitter_jsonl → knowledge/people/<person_id>/x/」。

## 环境

```bash
cp config/person_crawl.example.yaml config/person_crawl.yaml
```

`.env` 或 `config/person_crawl.yaml` 中配置 spider 仓库路径：

```env
SPIDER_BASE_PATH=~/GitHub/spider
```

## 命令速查

| 目的 | 命令 |
|------|------|
| 列出已配置人物 | `python scripts/crawl_person_sources.py --list` |
| 预览 spider 目标 | `python scripts/crawl_person_sources.py <person_id> --dry-run` |
| 爬取并导入 X+微博 | `python scripts/crawl_person_sources.py <person_id>` |
| 只爬 X | `python scripts/crawl_person_sources.py <person_id> --platform x` |
| 只爬微博 | `python scripts/crawl_person_sources.py <person_id> --platform weibo` |
| 已有爬取结果，只导入 | `python scripts/crawl_person_sources.py <person_id> --skip-crawl` |
| 导入后重建 RAG | 加 `--ingest-rag` |

## 新增人物

1. 编辑本地 `config/person_crawl.yaml` 的 `people`（不要提交到 Git）：

```yaml
people:
  your_person_id:
    display_name: 显示名
    x:
      user: XHandle
      mode: with_replies
      options:
        file-filter: "False"
    weibo:
      id: "1234567890"
      name: 微博昵称
      since_date: 7
      modes: [posts]
```

2. 确保 `knowledge/people/your_person_id/{x,weibo}/` 存在（脚本会自动创建）。
3. 若需圆桌 Agent，另在 `config/persona_inspired/` 添加 YAML 并在 council 中引用。

## 输出位置

- X：`knowledge/people/<person_id>/x/corpus.md` + `long_posts/`
- 微博：`knowledge/people/<person_id>/weibo/corpus.md` + `long_posts/`

原始 spider 输出仍在 spider 的 `settings.json` 配置的 `output_dir`（通常 Google Drive 或 `downloads/`）。

## 手动分步（调试时）

```bash
# X
python -m spider_core.cli x --base-path "$SPIDER_BASE_PATH" --dry-run
python scripts/parse_twitter_jsonl.py /path/to/tweets.jsonl \
  --command export-md --person-name <person_id> --display-name "Display Name" \
  --originals-only --min-length 300 --lang zh

# 微博
python -m spider_core.cli weibo --base-path "$SPIDER_BASE_PATH" --dry-run
python scripts/parse_weibo_json.py /path/to/uid.json \
  --command export-md --person-name <person_id> --display-name "Display Name" \
  --originals-only --min-length 80

# RAG
python -m rag.ingest --person-name <person_id> --source-kind x --embedding-provider keyword
python -m rag.ingest --person-name <person_id> --source-kind weibo --embedding-provider keyword
```

## 相关文件

- `person_crawl_agent/` — 配置加载、spider 桥接、定位输出、导入流水线
- `config/person_crawl.example.yaml` — 公开示例；真实映射放 `config/person_crawl.yaml`
- `scripts/crawl_person_sources.py` — CLI 入口
- `scripts/parse_twitter_jsonl.py` / `scripts/parse_weibo_json.py` — 原始 JSON/JSONL → Markdown