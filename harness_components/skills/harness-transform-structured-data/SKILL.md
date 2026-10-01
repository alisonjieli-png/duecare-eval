---
name: harness-transform-structured-data
description: Transform supplied JSON, records, CSV, URLs or encoded bytes with explicit harness contracts and preserved source values. Use for deterministic data preparation, conversion and validation.
---

# Transform structured data

Locate the reviewed `harness_components` package and run the CLI from its parent directory. Inspect the relevant schema, then apply the smallest operation that produces the requested view:

```bash
python3 -m harness_components get data.pointer_set
python3 -m harness_components run data.pointer_set --input '{"value":{"items":[{"count":2}]},"pointer":"/items/0/count","replacement":3}'
python3 -m harness_components run data.query_parse --input '{"query":"tag=one&tag=two&empty="}'
```

Keep the source value or file and its provenance separate from the transformed result. The CLI returns the value under `result`, with component ID/version/hash alongside it. Preserve that receipt when transformation reproducibility matters.

Use `data.json_parse` for strict JSON; it refuses duplicate keys and nonfinite numbers. JSON Pointers use escaped path tokens, exact Unicode keys and existing array indices. `data.pointer_set` returns a copy and requires the addressed target to exist. Object renames refuse collisions; record grouping and filtering retain type distinctions.

For CSV, `data.csv_records` requires unique nonempty headers and matching row widths. Cell values remain strings. `data.csv_formula_flags` reports common spreadsheet-sensitive prefixes without rewriting cells. Choose any display or export policy deliberately.

For URLs, keep path case, duplicate query keys and parameter order when meaningful. `data.url_normalize_http` normalizes scheme/host/default port and refuses userinfo; it does not verify the host or fetch a page. Percent decoding and form-query decoding have different plus-sign semantics. Byte helpers expose strict UTF-8, Base64 and hexadecimal contracts.

Check a representative value and an edge case that could lose information. Retain malformed or unsupported records with their error/status rather than silently coercing them. Write final artifacts only to the user's requested destination; the component calls themselves use supplied values and perform no file, network or model operations.
