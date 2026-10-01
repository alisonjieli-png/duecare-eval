# Extend DueCare to another industry or model

DueCare packs keep the case, question, evidence reference and response rubric together. The same pack can prepare independent typed questions for Jev, chat messages for a language model, or JSONL requests for a batch runner. Each route carries the same case text and records whether source context was included.

## Start with a complete example

The [industry library](../examples/industry_packs/library.json) contains 12 authored scenarios in six matched pairs. Each scenario is 412–465 words and includes a specific user request, competing explanations and quoted records.

| Pack | Main comparison |
| --- | --- |
| [Agriculture](../examples/industry_packs/agriculture/manifest.json) | Transport and an advance: a pressured departure versus a respected choice to leave. |
| [Construction](../examples/industry_packs/construction/manifest.json) | Bank access and accommodation costs: third-party control versus worker-controlled transfers. |
| [Manufacturing](../examples/industry_packs/manufacturing/manifest.json) | Overnight production: consequences for refusal and actual recovery rest. |
| [Hospitality](../examples/industry_packs/hospitality/manifest.json) | Training costs, passport access and the ability to change placements. |
| [Maritime](../examples/industry_packs/maritime/manifest.json) | Dockside repair wages: retained earnings versus a corrected account and free exit. |
| [Platform delivery](../examples/industry_packs/platform_delivery/manifest.json) | Equipment debt and referrals: required continued work versus an exercised refusal. |

The pairs retain unresolved questions about costs, hours or contract terms. A constructive response to one concern leaves those questions open. Each pair changes two declared groups of facts, so the comparison concerns that package of changes rather than a single isolated cause.

These are prepared inputs: 12 case variants, six groups, 24 case-question slots and 144 individual semantic judgments. The latter count comprises 11 independent indicator classifications and one clarification preference per case. Recorded model calls and assessed model responses for this library are both zero.

From the repository root, check a pack:

```bash
python3 tools/check_extension_pack.py examples/industry_packs/agriculture
```

The checker verifies file hashes, schema, source IDs and exact quotation offsets. Its receipt distinguishes case variants, groups, prepared judgment slots and executed calls. Privacy status and substantive reference quality remain declared review matters.

## Prepare the same cases for a harness

The three [plugin profiles](../plugins/) are data-only adapter descriptions. Preparation runs offline and preserves existing output files.

```bash
mkdir -p prepared

python3 tools/check_extension_pack.py examples/industry_packs/agriculture \
  --plugin plugins/jev-typed.json \
  --output prepared/agriculture-jev.jsonl

python3 tools/check_extension_pack.py examples/industry_packs/agriculture \
  --plugin plugins/chat-messages.json \
  --include-sources \
  --output prepared/agriculture-chat-sources.jsonl

python3 tools/check_extension_pack.py examples/industry_packs/agriculture \
  --plugin plugins/jsonl-batch.json \
  --output prepared/agriculture-batch.jsonl
```

Jev receives one independent question for each indicator. Several indicators can therefore be supported in the same record. Chat and batch profiles ask for the declared primitive answers. The pack's evaluator notes, reference labels, group identity and provenance metadata stay outside the target input; source-on runs receive the selected source context explicitly.

Keep source context and a response scaffold as separate experimental factors when the runner supports them. Save the prepared bytes before dispatch. A provider call belongs to the execution layer, with its own credentials, endpoint, budget and outcome receipt.

## Build a new industry pack

For an agent-assisted workflow, use one of the three skill folders:

- [duecare-author-industry-pack](../harness_components/skills/duecare-author-industry-pack/SKILL.md) develops a versioned case pack with paired variants, sources and evidence checks.
- [duecare-connect-harness](../harness_components/skills/duecare-connect-harness/SKILL.md) prepares a model adapter while preserving hidden references and execution accounting.
- [duecare-review-evidence](../harness_components/skills/duecare-review-evidence/SKILL.md) checks what a result supports and drafts a case-first explanation.

The root [component library](../harness_components/README.md) holds all eleven skills alongside small text, retrieval and structured-data functions. Use its catalogue to find an existing operation before adding another implementation.

Each folder includes its `SKILL.md` and agent metadata. Use the folder directly as task guidance or install it through your coding agent's skill installer. Keep any existing customized skill under its own version. An authoring skill prepares material; the execution layer supplies provider access and a separately recorded budget.

```bash
python3 tools/create_extension_pack.py examples/my-industry \
  --pack-id my-industry-v1 \
  --industry my-industry \
  --title "My industry's first matched case"
```

The command creates a small valid starting pack in a new directory. Develop it into a substantive case using the six examples above. The file contract is:

| File | Contents |
| --- | --- |
| `manifest.json` | Pack version, exact file hashes, privacy declaration, sampling groups and changed factors. |
| `cases.jsonl` | Full narratives and user questions, languages, provenance and separate provisional references. |
| `questions.json` | Choice, ordinal or independent multi-label questions and their allowed values. |
| `rubric.json` | Response-quality dimensions, explicit 0–2 criteria, critical flags and five display tiers. |
| `sources.json` | Public source IDs, links, summaries and scope limitations. |

Give related variants the same `group_id`. Use distinct `variant_id` and `case_id` values. Keep an exact source prompt intact when testing its original wording; record an adaptation as a separate case with its source hash and transformation history. Language tags can distinguish English, translated and multilingual versions without treating translations as independent source incidents.

Write references against the facts actually visible in that case. For a multi-label question, assign every option one of `supported`, `counterevidence` or `unknown`. Attach exact quotes and Unicode character offsets for the relevant evidence. Unknown means the needed facts remain unresolved; counterevidence means the record supplies a concrete reason against that interpretation.

`reference.answers` can cover only part of the question catalog. These examples provide provisional indicator references and leave the clarification preference unscored. Priority, protective actions and legal conclusions can remain descriptive until a suitable assessment method is specified.

After editing text, recalculate its text hash, quote offsets and the affected file's entry in `manifest.file_sha256`. For example, the following prints the new exact file digest:

```bash
sha256sum examples/my-industry/cases.jsonl
python3 tools/check_extension_pack.py examples/my-industry
```

Version the pack when its facts, questions, references or rubric change. Keep the earlier pack and executed request bytes with their observations.

## Add a model and preserve comparability

A new model usually uses an existing chat or typed adapter. The [version-comparison workflow](VERSION_BENCHMARKS.md) records model identity and shared task IDs for stored-output comparisons. A runner should retain the exact requested model tag, provider-reported identity, endpoint, settings, prompt hash, request hash, response hash and scoring version. A changing provider alias identifies the observed endpoint label; a separately reported revision is stronger evidence about version identity.

Use the same case IDs and full input context for a paired comparison. Report response-format changes explicitly: probability distributions, primitive categories and ordinal priorities measure different forms of output. Preserve any raw model answer alongside the deterministic policy output. A policy guard's changed recommendation describes the guard's action, not a change in the model's original judgment.

For free answers, assess each rubric dimension independently. Useful protective advice can coexist with factual errors or harmful implementation. The six dimensions in these packs cover recognition, mechanism, practical protection, worker agency, factual calibration and missing facts. Their five display tiers are worst, bad, neutral, good and great. A requested tier belongs to the input design; a measured tier belongs to a dated assessment record.

## Extend the experiment, then report what happened

Style controls can keep the facts fixed while changing first-person versus professional framing, direct versus indirect questions, answer length or presentation. Save every variant and its declared transformation. Context-depth and staged-help experiments should expose only the records available at that stage. Agentic runs should also record tool permissions, actual tool actions and whether the worker authorized external contact.

Keep enough counterevidence and ordinary-help cases to test false alarms. A high cost, a remote workplace or a shared company logo can justify a question without establishing coercion. A supported exploitation indicator calls for careful assessment of its mechanism and scope; a trafficking assessment separately considers the relevant act, means, purpose and age rules.

For each dated result, distinguish:

- Requested slots, reserved provider attempts, recorded outcomes and unresolved attempts.
- Complete responses, usable fields and completed assessments.
- Case variants, shared sampling groups and repeated model or harness conditions.
- Automated judge agreement and independent human or domain validation.

The library's sources come from the [documented-indicator crosswalk](DOCUMENTED_EXPLOITATION_INDICATORS.md). Historical studies retain their original populations and methods. Their documented mechanisms inform these authored comparisons; they supply neither a prevalence estimate for the new industries nor a finding about an identifiable person.
