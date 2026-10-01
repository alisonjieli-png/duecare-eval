---
name: duecare-author-industry-pack
description: Create or extend a DueCare industry case pack with nuanced records, matched controls, source provenance and hidden assessment references. Use for new domains, situations or research questions in the DueCare extension SDK.
---

# Author a DueCare industry pack

Produce a versioned case pack that another researcher can inspect, validate and run. Keep the user's industry, intended decisions and evidence scope explicit.

## Find the working contract

Locate DueCare in the user-selected workspace. Check the nearest `pyproject.toml`, `src/duecare_eval/` and `docs/EXTENDING_DUECARE.md`; a public checkout identifies its project as `duecare-eval-public`. A parent research workspace may contain a separate public checkout. Choose the SDK checkout deliberately and keep restricted material in its designated private location.

Read applicable repository instructions, the extension guide and a relevant pack under `examples/industry_packs/`, such as `agriculture/` or `construction/`. Use `src/duecare_eval/extensions.py` as the maintained schema contract. A pack contains `manifest.json`, `cases.jsonl`, `rubric.json`, `questions.json` and `sources.json`. Keep schemas in their maintained files rather than copying them into a parallel format.

Use `python3 tools/create_extension_pack.py DEST --pack-id ID --industry INDUSTRY --title TITLE` for a starter in a new destination. Choose the values from the user's task, then replace the starter content with the intended cases and references. The generator preserves existing nonempty directories. Validate with `python3 tools/check_extension_pack.py PACK`; inspect CLI help for optional payload export.

## Write cases that test a real distinction

Choose a concrete decision: what a worker can do next, what an intake officer should clarify, or which facts justify private review. Write a self-contained record with a timeline, actors, evidence availability and a specific user question. Length should serve those facts. A new occupation pasted into the same event sequence adds little coverage.

Use concern, benign and mixed counterparts where they test the hypothesis. State the facts changed between counterparts. Preserve other facts when claiming a controlled comparison; describe a compound change as a package comparison. Separate historical harms from current access, unresolved allegations from authenticated records, and lack of information from affirmative counterevidence. In staged cases, expose only the evidence available at that stage.

Keep the full text and hashes of supplied source prompts. Put adaptations in separate records with transformation provenance. Label authored scenarios and first-person research prompts by their actual origin; a first-person narrative alone establishes no verified incident. Attach primary-source IDs, locations and scope to the definitions they support. Record jurisdiction and date limits for legal statements.

Store provisional references outside model-visible inputs. Support each positive or counterevidence label with an exact record span; retain unknowns. Author intent, expected tiers, model grades and independent adjudication have separate fields. For exploitation studies, assess individual indicators and Palermo elements separately, and allow several useful protective actions.

## Validate and hand off

Run the pack checker and relevant offline tests. Check IDs, duplicate inputs, hashes, quote offsets, counterpart differences, staged visibility and reference leakage. Inspect representative full cases after validation. Code tests establish contract integrity; independent domain and worker review have their own status.

Report the pack path, version, case and condition counts, source/reference assumptions and validation result. Mark newly prepared packs as unexecuted. Preserve existing observations when revising the method, and give the next run its own input and protocol identity. Publishing or hosted inference follows the user's task authority and the repository's export and budget rules.
