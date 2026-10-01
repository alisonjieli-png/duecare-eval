---
name: harness-build-local-retrieval
description: Build and test lexical retrieval or context assembly over supplied document values using pure harness components. Use for local RAG preparation, passage ranking and retrieval diagnostics.
---

# Build retrieval over supplied documents

Locate the reviewed `harness_components` package and run the CLI from its parent directory. The components operate on provided JSON values; a caller supplies any document reading, storage or separately authorized model access.

Inspect the actual contracts and try a small ranking fixture:

```bash
python3 -m harness_components get search.bm25_rank
python3 -m harness_components run search.bm25_rank --input '{"documents":[{"id":"a","text":"passport access"},{"id":"b","text":"wage records"}],"query":"passport","k1":1.2,"b":0.75,"limit":2}'
python3 -m harness_components get search.assemble_context
```

Keep exact source documents and stable source IDs. When chunking with `search.chunk_characters`, `search.chunk_tokens` or `search.paragraph_spans`, retain source IDs and original offsets in a sidecar mapping. Namespace chunk IDs across documents. Pass the contract's `id`/`text` records to rankers without adding unsupported fields.

Choose the simplest suitable method: `search.build_inverted_index` for positional token lookup, `search.tfidf_rank` or `search.bm25_rank` for lexical ranking. Keep ranking scores distinct from probabilities or evidence strength. Preserve ties and empty/no-match outcomes.

Use `search.retrieve_context` on passages from the same source when neighboring text is needed. Give `search.assemble_context` an explicit caller-chosen character budget; retain included IDs, omitted IDs and citation offsets. Relevance ranking and factual/source review remain separate tasks.

Evaluate with a few queries whose relevant document IDs are independently specified, including an empty query, an absent term and a competing near-match. Use `search.precision_at_k`, `search.recall_at_k` or rank metrics with their documented denominators. In evaluation workflows, keep hidden answer keys out of the retrieval corpus.

Read returned values from the CLI's `result` envelope. Deliver the corpus mapping, component choices/settings, representative retrieval results and measured limitations. Report retrieval preparation separately from any model run.
