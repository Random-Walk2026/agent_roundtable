# Local Knowledge Corpora

This directory is reserved for local book-level corpora used by RAG-backed domain experts.

The corpus files themselves are intentionally ignored by Git because they are local/private source material. Keep only lightweight placeholders and documentation in the public repository.

Expected expert folders:

- `ai_researcher/`
- `history_strategist/`
- `investing_master/`
- `macro_economist/`
- `philosophy_expert/`

Put complete books, papers, letters, or collected long-form works under the matching expert folder on your local machine, then rebuild indexes with:

```bash
python -m rag.ingest --embedding-provider keyword
```
