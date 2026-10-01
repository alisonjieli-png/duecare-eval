---
name: harness-find-component
description: Find a suitable reusable harness function, query preset, workflow skill or upstream reference and inspect its contract. Use for component discovery and choosing a small implementation before writing new code.
---

# Find a harness component

Locate the user-selected checkout containing `harness_components/__main__.py` and `library.py`. Run the CLI from its parent directory. An explicit library directory goes before the subcommand: `python3 -m harness_components --root /path/to/harness_components search "CSV"`.

Search by the needed operation and inspect promising IDs:

```bash
python3 -m harness_components search "CSV duplicate header" --kind function --limit 5
python3 -m harness_components get data.csv_records
python3 -m harness_components run data.csv_records --input '{"text":"name,score\nAda,7\n"}'
```

Match the input/output schema, failure behavior, source references and version to the user's actual data. A search score measures catalog-word overlap. Read the full entry before choosing; use its example as a starting point and check a representative user case.

Keep catalog kinds explicit. Functions expose `run`; query presets are unexecuted query text; skills supply workflows; upstream references are discovery records whose installed, verified and license status travels with them. Preserve these distinctions in the handoff.

The `run` response contains `result` plus the component ID, version and source hash. Feed only the expected result fields into another function, while retaining the envelope as a receipt. For long or untrusted strings, pass JSON on stdin rather than interpolating shell text.

`python3 -m harness_components build` intentionally imports reviewed local modules and refreshes derived catalog/inventory files. Use it when preparing or refreshing the chosen library. Resolve an integrity mismatch against the reviewed source before rebuilding.

Return the selected ID, a minimal working invocation, the result and any relevant contract limitation. Count functions, presets, skills and references separately.
