---
name: harness-compose-search-queries
description: Compose reusable web-search presets, literal search clauses, FTS5 expressions or parameterized SQL query data. Use when the user needs prepared queries for a specified search system.
---

# Compose queries for the chosen search system

Identify the intended dialect and requested search scope. Locate the reviewed `harness_components` package and run its CLI from the parent directory.

For web research, discover query presets and read their full provenance:

```bash
python3 -m harness_components search "recruitment fees official" --kind query_preset --limit 5
```

Use `python3 -m harness_components get ID` with an ID returned by discovery. Preserve the original query and source reference when making a task-specific variant. The preset is a prepared search string; record executed searches and retrieved evidence separately.

Choose builders that match the receiving engine:

```bash
python3 -m harness_components run search.parse_simple_query --input '{"query":"+passport \"wage records\" -advertisement"}'
python3 -m harness_components run search.fts5_boolean_query --input '{"phrases":["recruitment fees","worker control"],"operator":"AND"}'
python3 -m harness_components get search.build_select
```

`search.parse_simple_query` implements its documented required/optional/excluded grammar. `search.fts5_quote_phrase` and related FTS5 builders quote literal phrase data. Their output is specific to that dialect. For SQL, retain the builder's SQL string and separate `params` list, and pass values as bound parameters in an authorized caller.

Use `data.query_encode` or `data.url_query_append` for form-encoded URL parameters; preserve duplicate keys when meaningful. These functions prepare data and perform no searches or database actions.

Test embedded quotes, an operator-looking literal, empty input and duplicate query parameters where relevant. Pass untrusted JSON through stdin rather than shell interpolation. Report the query text, dialect, purpose, provenance and any adaptation. Keep private case identifiers out of public search strings; use the scoped public terms needed by the user's task.
