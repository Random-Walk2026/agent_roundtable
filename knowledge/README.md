# Local Knowledge Corpora

This directory stores local source material for RAG-backed agents. It is split into two top-level scopes:

## `experts/`

Book-level corpora for domain experts. Config IDs are short domain words (1-2 words), for example `macroeconomics`, `investing`, `computing`.

Expected folders:

- `experts/macroeconomics/`
- `experts/investing/`
- `experts/computing/`
- `experts/philosophy/`
- `experts/history/`

Example:

```text
knowledge/experts/macroeconomics/general_theory.md
```

## `people/`

Multi-source corpora for specific people used by `persona_inspired` agents. Config IDs use person names only, for example `desmond_shum`, `buffett`.

Source-type subfolders:

- `book/` — books and memoirs
- `x/` — X/Twitter posts exported from `tweets.jsonl`
- `weibo/` — Weibo posts exported from spider_weibo JSON
- `news/` — news articles and interviews
- `report/` — public reports, speeches, filings

Example:

```text
knowledge/people/desmond_shum/book/red_roulette.md
knowledge/people/desmond_shum/x/corpus.md
```

## Import helpers

```bash
python scripts/crawl_person_sources.py desmond_shum --dry-run
python scripts/crawl_person_sources.py desmond_shum --skip-crawl --ingest-rag
python scripts/parse_twitter_jsonl.py ~/path/to/tweets.jsonl --command export-md --originals-only --min-length 300 --lang zh
python scripts/parse_weibo_json.py ~/path/to/uid.json --command export-md --person-name desmond_shum
python scripts/import_person_source.py desmond_shum book "/path/to/book.md"
python -m rag.ingest --expert-name macroeconomics --embedding-provider keyword
python -m rag.ingest --person-name desmond_shum --embedding-provider keyword
python -m rag.ingest --person-name desmond_shum --source-kind x
```

Mixed councils can combine experts and people, for example `config/councils/china_debt.yaml`.

Corpus files are intentionally ignored by Git because they are local/private source material.