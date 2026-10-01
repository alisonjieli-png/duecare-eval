---
name: harness-test-corner-cases
description: Test harness-component contracts and meaningful boundary behavior with independent fixtures. Use for regressions, integration checks or verifying a proposed component transformation.
---

# Test component boundaries

Locate the reviewed `harness_components` package and inspect the requested component with `get`. Choose fixtures from the caller's requirements, including expected values or refusal behavior written independently of the implementation.

Start with a valid case and one deliberate contract violation:

```bash
python3 -m harness_components get data.json_parse
python3 -m harness_components run data.json_parse --input '{"text":"{\"x\":1}"}'
python3 -m harness_components run data.json_parse --input '{"text":"{\"x\":1,\"x\":2}"}'
```

The first run returns `result.value`. The duplicate-key run should return a JSON error and exit status 2. Treat that refusal as the expected outcome of this fixture.

Select boundaries that can change meaning: boolean versus integer fields; missing versus empty values; duplicate keys or record IDs; composed versus decomposed Unicode; literal quotes and query operators; percent-escape errors; CSV embedded newlines or leading BOM; exact span boundaries. Test only the relevant categories.

Check that inputs remain unchanged, output types match the declared schema, and errors retain a useful explanation. Round-trip tests are useful where the contract promises reversibility; avoid treating lossy normalization as reversible. A component's examples are smoke checks, so add at least one independently chosen case when investigating a regression.

For CLI integration, copy the reviewed library to an isolated temporary directory and run `python3 -m harness_components --root /temporary/library build` there. Build imports reviewed modules and refreshes the copied catalog. Exercise `search`, `get` and `run` against that root; keep generated fixtures outside recorded benchmark inputs.

Report tested IDs/versions, fixture outcomes and unresolved failures. Software checks establish the tested behavior; they do not establish model quality, domain validity or privacy completeness.
