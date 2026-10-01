# Expanded questions, context and action choices

The expanded design separates the question asked, the facts available and the instructions used to answer it. Six frozen banks contain 200 stored rows representing 184 distinct request specifications. The 16-row prose canary is an exact subset of the 96-row prose bank; its typed counterpart has separate request IDs for the same case/context conditions.

## Prepared banks and observed coverage

| Bank | Prepared requests per model | Purpose |
| --- | ---: | --- |
| Action-menu comparison | 30 | Five preserved source texts, three menus, two submitted orders |
| ILO case application | 40 | Five texts, source absent/supplied, two assessment lenses, two orders |
| ILO standard knowledge | 2 | Eight propositions per request, four true and four false, source absent/supplied |
| Question/context/scaffold pilot | 96 | Eight question forms with matched concern/control conditions, three contexts and scaffold off/on |
| Prose canary | 16, included in the 96 | Two themes with realized minimal/whole-history differences |
| Typed canary | 16 | The same sixteen conditions with the common twelve-question panel |

The Jev allocation covered the first three banks: 72 requests. One was attempted and returned HTTP 402; zero were usable and 71 were unattempted. The [execution receipt](../results/ilo_menu_execution_2026-10-01.json) therefore supports no new ILO-knowledge or action-menu performance finding.

The separate context/scaffold trial produced 32 usable generations: sixteen canary conditions for each of two served configurations. [Generation receipts](../results/context_scaffold_observations_2026-10-01.json) and full-text assessments have separate roles. Preparation counts describe request specifications, while model behavior requires actual recorded answers and review.

## Exact source text and authored derivatives

The source arms preserve four complete published advice prompts and one separately documented full notebook variant, with five exact prompt hashes. The notebook variant has its own provenance; identity with the writeup's truncated fourth exhibit remains unproven.

Four source themes also motivate authored timelines: salary deductions, collection assignment, high-interest novation and worker guilt. Each has a concern condition and a worker-control counterpart. The paired conditions differ in explicit cost allocation, access to documents and wages, threats and freedom to decline or leave. This is a matched package of facts rather than a one-sentence causal change.

The timelines contain events before commitment, after arrival and at payment demand or payment-record review. They are research scenarios, with no claim of a verified person's history. All derivatives share one conservative source-family group and remain in an evaluation-only split.

## Context and scaffold are separate factors

Minimal context contains the current staged event. Whole-case context contains the history through that event. Evidence-enriched context adds the scoped v1 ILO source statements to the same available history. Future events remain withheld.

The 96-row design has 32 minimal/whole pairs. Twelve occur at the first stage, where those views necessarily contain the same information; twenty have different histories. The sixteen-condition canary uses later stages so all eight of its minimal/whole contrasts contain different information.

Scaffold off/on changes only a fixed instruction while keeping the prose user message byte-identical. The full pilot has 48 such pairs. The C trial tests this text scaffold. The [executable protection-first prototype](PROTECTION_HARNESS_PROTOTYPE.md) has additional source, fact, arithmetic and response-checking components and its own protocol.

The bounded canary covers salary advice after arrival and a worker-pressure question at payment demand. Theme, stage and question form therefore move together in that canary. Their independent effects need a broader allocation. Its authored stages measure available information within a case; calendar-time model improvement requires repeated versioned runs.

## Questions, menus and references

The eight forms are direct screening, indirect practical advice, worker-first-person help, professional advice, action ranking, missing-facts/uncertainty questions, a declared counterfactual and a three-step pressure vignette. The vignette receives one answer. Interactive multi-turn execution remains a separate design.

The action-menu comparison retains the original twelve question strings. Menus contain the original choices, those choices with the generic jurisdiction/financing fallback removed, or concrete protective choices. Every menu retains distinct options for insufficient information and several supported first steps. Removing a choice changes menu size; replacing wording changes the treatment. Both submitted orders and case-wise rotations are recorded, with provider-internal presentation remaining unknown.

The ILO application arm appends four explicitly standard-cued questions. Both assessment lenses receive the same added, unverified approval claim; the requested focus changes between domestic approval and international labour standards. The knowledge arm separately tests eight source statements. Original-case judgments remain descriptive. The typed authored canary has four declared fact-based references per condition and allows several proportionate first actions. Its menu includes ordinary explanation without escalation for the worker-control condition.

References stay outside model-facing `state` and `messages`. A prepared row contains both the model-facing fields and separate assessment metadata, so dispatch should use `model_input(row)` or equivalent explicit field selection. Declared cost/debt fields describe the authored requirement; legal enforceability needs its own assessment.

The dated v1 source packet remains attached to these frozen inputs. The later ILO scope addendum, including membership-based fundamental principles and the distinction between ratification and domestic implementation, belongs to its separately versioned evidence layer.

## Scalable design and offline checks

The [manifest](../examples/breadth_depth_v1/manifest.json) defines a full factorial of 1,152 conditions per model:

`4 themes × 2 conditions × 3 stages × 8 question forms × 3 contexts × 2 scaffold levels`

This is a prepared design, with no full-factorial execution attributed to it. The [definition fixture](../examples/breadth_depth_v1/design_definitions.json) contains the authored timelines, question strings, source hashes, scaffold and reference definitions needed to inspect the design.

From the repository root after package installation:

```sh
python tools/check_breadth_design.py --check
python tools/check_breadth_design.py --json
python -m pytest tests/test_breadth_design.py
```

The validator checks bank bytes, per-file uniqueness, documented overlap, the original sealing method, source fidelity, submitted action order, hidden reference keys, eight-form coverage, stage visibility, scaffold matching and the dated execution receipts. It makes zero provider calls. Software integrity checks and automated answer reviews retain their separate status from independent legal, domain and worker-informed validation.
