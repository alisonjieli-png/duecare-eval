---
name: duecare-connect-harness
description: Connect a model, agent harness or saved response stream to DueCare through a Jev-typed, chat-messages or JSONL profile. Use for adapter design, payload checks and response-contract validation.
---

# Connect a harness to DueCare

Build an adapter whose recorded request and response explain exactly what the model saw and returned.

## Locate the SDK and choose a profile

Start in the user-selected workspace. Find the DueCare checkout through `pyproject.toml`, `src/duecare_eval/` and `docs/EXTENDING_DUECARE.md`; the public project's name is `duecare-eval-public`. Read the repository instructions and extension guide. Inspect the declarative profiles and `src/duecare_eval/extensions.py` before choosing `jev-typed`, `chat-messages` or `jsonl-batch`.

A profile describes a data exchange. Check which transport or importer actually exists. State separately whether the work delivers a profile, an offline adapter, verified access or a completed benchmark. For example, `python3 tools/check_extension_pack.py PACK --plugin plugins/chat-messages.json --output OUTPUT.jsonl` validates and exports a new payload file offline. Use a fresh output path. The library provides `load_pack`, `validate_pack`, `build_payload` and `batch_payloads` for integration; read their signatures and tests before adapting a caller.

## Preserve the task across interfaces

Record the complete visible state, user question, source/scaffold arm and response instructions. Keep hidden references and intended tiers outside the payload. Preserve the executed input bytes and hashes. If an adapter adds a system message, action menu, evidence briefing or tool observation, register that as a distinct condition.

Use the provider's actual contract. Jev typed distributions, native categorical selections and free prose are different measures. A returned category remains a category; a parser must never invent a calibrated distribution from it. Preserve returned probabilities, ties, missing fields and invalid values. Retain strict validation beside any separately versioned extraction of unchanged returned values.

Bind request IDs, protocol and pack versions, requested and reported model identities, serving parameters, attempt numbers, usage and response hashes. Imported JSONL needs source provenance and explicit missing metadata. Match comparisons by case, visible context and elicited question, and disclose remaining interface differences.

For agent harnesses, retain the ordered tool trace and the distinction between proposed action, tool execution and observed postcondition. A helpful-sounding final message does not establish that the requested action succeeded.

## Test within the requested scope

Start with offline fixtures that exercise valid outputs, unknown IDs, malformed JSON, truncation, partial answers, identity mismatch and duplicate outcomes. Label fixtures as fixtures. A network canary requires task authority and a declared attempt/output budget; schema checks consume no inference budget.

Use the project's configured credential resolver and fixed permitted endpoint. Keep secrets out of profiles, fixtures, logs and exported artifacts. Preserve provider-wide stops and observed retry constraints. An unknown in-flight outcome needs reconciliation before replay. Run only the execution route authorized for this project and request.

Hand off the profile and adapter paths, contract tests, exact payload differences and coverage accounting. Separate logical requests from physical attempts, transport completion from usable answers, and raw choices from any policy guard. List the remaining execution or validation work without presenting a prepared connector as measured model performance.
