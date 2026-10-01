# Small tools for research harnesses

Use these components to clean a string, find a passage, assemble retrieval context, compare rankings or check a record. Each function has its own Python file, a version, JSON input/output schemas and executable examples. The library runs offline with Python's standard library.

The catalogue keeps four useful kinds of material separate:

| Kind | Count | What you can do with it |
|---|---:|---|
| Callable functions | 158 | Run 60 text, 50 search/retrieval and 48 structured-data operations. |
| Workflow skills | 11 | Follow focused instructions for authoring, evaluating, finding and combining components. |
| Search presets | 13,888 | Retrieve exact saved queries, with source-file and line provenance, for a search you choose to run. |
| Upstream references | 1,393 | Inspect commit-pinned links to external skills, instructions, agents, prompts and helpers. Review status is `discovered_unreviewed`. |

These are 15,450 catalogue entries. A query preset counts as a query; an upstream link counts as a discovery reference. The [inventory](inventory.json) records machine-readable counts and the catalogue digest. Each preset and upstream reference also has its own JSON file.

## Find one thing and use it

From the repository root:

```bash
python3 -m harness_components search "email" --kind function --limit 5
python3 -m harness_components get text.email_normalize
python3 -m harness_components run text.email_normalize --input '{"email":"Case+tag@EXAMPLE.ORG"}'
```

The result preserves `Case+tag` and changes the domain to `example.org`. Email handling uses an explicit ASCII dot-atom/DNS profile and reports unsupported forms. Delivery checks, quoted local parts and internationalized mailboxes need a separately chosen implementation.

Slang matching uses a lexicon supplied by the caller:

```bash
python3 -m harness_components run text.slang_matches --input '{"text":"IDK, can someone help?","lexicon":[{"term":"idk","meanings":["I do not know"]}]}'
```

The returned match includes the original spelling and character offsets. Multiple meanings stay visible. A lexical match supplies a reading aid; interpreting the person or situation requires context.

## Useful building blocks

- Text: Unicode normalization, original-span tracking, whitespace, email normalization/masking, literal and escaped-regex matching, caller-supplied slang lexicons and redaction.
- Retrieval: literal grep and surrounding lines, keyword-in-context, token and character chunks, inverted indexes, TF-IDF, BM25, reciprocal-rank fusion, diversity selection and context assembly.
- Database queries: quoted identifiers, parameterized SQL builders and escaped SQLite FTS5 expressions. These return query strings and parameters; database execution belongs to the caller.
- Structured data: strict JSON/JSONL, JSON Pointer, record projection, CSV, URLs and query pairs, Base64, hex, UTF-8 and hashes.
- Evaluation: precision, recall, reciprocal rank, average precision and discounted cumulative gain over supplied reference judgments.

Inspect the exact contract before composing functions:

```python
from harness_components import Library

library = Library()
documents = [
    {"id": "a", "text": "Example record: a recruiter keeps the worker's passport."},
    {"id": "b", "text": "Example record: the worker keeps their own passport."},
]
result = library.run("search.bm25_rank", {
    "documents": documents, "query": "passport", "k1": 1.2, "b": 0.75, "limit": 2,
})
print(result["result"])
```

Both example records can rank highly because both mention a passport. Retrieval finds candidate passages; the opposite facts still require interpretation. Preserve original records alongside transformed views, document IDs and source offsets. The retrieval layer can feed a RAG workflow using your chosen hosted model or a human reader.

## Search skills and research queries

```bash
python3 -m harness_components search "retrieval" --kind skill
python3 -m harness_components search "recruitment fees" --kind query_preset --limit 10
python3 -m harness_components search "search" --kind upstream_reference --limit 10
```

Results give `total_matches` and `next_offset`. Pass `--offset` to continue through the full population. Catalogue ordering uses documented weighted token overlap; its score measures matching metadata, separately from source quality or trust.

Search presets retain their exact query text from five project research-spider files. The [query inventory](search_queries/inventory.json) records deduplication and provenance. Their donor-authored query text carries the [original MIT licence](search_queries/SOURCE_LICENSE.txt); third-party search results carry their own terms. Executing searches and validating their findings are subsequent work.

The [upstream inventory](discovery/upstream/inventory.json) records four repository commits and discovery coverage. References contain paths and identifiers, with `installed=false`, `verified=false` and `license_scope=unreviewed`. Read the source and its licence before deciding whether to adapt or install it. External text stays data during discovery.

## Connect through MCP

Install the optional SDK in your environment with `python3 -m pip install -e '.[mcp]'`, then start:

```bash
harness-components-mcp --library-root /absolute/path/to/harness_components
```

The stdio server offers `harness_summary`, `harness_search`, `harness_get` and `harness_run`. Set the library root in the server's launch configuration. Tool calls use component IDs and JSON values. The existing `duecare-mcp` service continues to provide DueCare's nine source, case and evaluation operations.

## Add and check a component

Place a small module at `components/<group>/<name>.py`, exporting `SPEC` and `run(payload)`. Copy the contract shape from a nearby component, add normal and corner-case tests, and keep external effects explicit. This library's callable profile accepts pure, JSON-compatible transformations over supplied values. Provider calls, file writes and external actions belong in separately permissioned adapters.

```bash
python3 -m harness_components build
python3 -m harness_components check --full
pytest -q harness_components/tests
```

`build` imports trusted local component metadata and creates a deterministic catalogue. Search and inspection read catalogue data. Each execution verifies the component and its local dependency bytes before importing a fresh copy, then validates the input and output. Integrity hashes bind the reviewed files; code review and the operator's trust in the catalogue remain essential.

Tests cover examples and independent edge cases: Unicode expansion and offsets, ambiguous abbreviations, malformed email/JSON/CSV, duplicate keys, empty retrieval results, ranking ties, SQL values containing quotes and FTS syntax. Software tests establish those behaviors; model capability and worker-safety claims have their own evidence requirements.

All eleven skills live in [skills/](skills/). The five original DueCare skills retain their contents at the new path. The focused six add component discovery, text cleanup, local retrieval, research queries, corner-case checks and structured-data workflows. The compact Baltor candidate continues to carry the five domain skills; the complete library is distributed with this repository and its source release.
