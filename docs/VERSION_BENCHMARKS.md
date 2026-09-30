# Benchmarking future model versions

The offline workflow prepares blind typed-decision tasks, imports saved provider receipts and compares a candidate with a versioned baseline. It supports binary probabilities, ordinal and categorical distributions, and independent label probabilities. The comparison uses exact shared task IDs and keeps failed, invalid and missing outcomes in the requested denominator.

## Registered targets

| Target | State | Next step |
|---|---|---|
| Jev 1.13.0 | Published stored baseline | Import the released numeric responses |
| Next Jev version | `exact_version_required` | Record its confirmed serving ID and version |
| Gemini4 | `exact_version_required` | Confirm the requested Gemini endpoint and exact version |

Gemini4 is the requested future Gemini target. The earlier Gemma 4 experiments retain their own identities and results. On September 30, 2026, the official [Google model catalog](https://ai.google.dev/gemini-api/docs/models) was checked for preparation; a Gemini4 serving identifier remains to be confirmed. Google's [Models API](https://ai.google.dev/api/models) supplies available model names, version metadata and supported functionality. Record that evidence when pinning a target.

The registry is [version_targets.json](../examples/version_targets.json), with a [JSON Schema](../examples/version_targets.schema.json) and runtime validation. Each served version gets a distinct `target_id`, its declared `model_id`, `exact_version`, provider and family. A planned entry becomes `pinned` after endpoint confirmation. The preparation command requires that identity before it writes a bundle. A registry entry records the operator's declaration; provider-returned model IDs and versions supply separate evidence. An alias alone leaves the underlying serving revision dependent on the provider.

## Reproduce the stored baseline

From the release checkout:

```bash
python tools/version_benchmarks.py registry
python tools/version_benchmarks.py baseline \
  --target jev-1.13.0-baseline \
  --responses results/jev_crossborder_responses.jsonl \
  --out local-runs/jev-1.13.0-baseline.json
```

This imports the 937-task suite's saved responses. The older export includes task IDs, reported model identity and numeric decisions. Original transport-request hashes and decoding configuration are unavailable in that export, so their provenance stays explicit and the corresponding fields remain null. Import hashes identify the exact stored records used in the comparison.

## Prepare a candidate

Copy the target registry and [configuration example](../examples/version_configuration.json) into `local-runs/`, then record the confirmed model identity and actual adapter settings there. The configuration should cover prompt/adapter version, decoding, tool access and serving controls. Keep credentials in the provider's existing credential store.

For example, after pinning the `gemini4-planned` entry in your local registry:

```bash
python tools/version_benchmarks.py prepare \
  --registry local-runs/version_targets.json \
  --target gemini4-planned \
  --configuration local-runs/version_configuration.json \
  --out local-runs/gemini4-bundle
```

`blind_tasks.jsonl` contains the model-visible task and response contract. `manifest.json` stays with the evaluator. It records each reference-task hash and a request hash binding the blind task, pinned identity and public configuration. The manifest also hashes the task set and its own contents. An external adapter sends the blind task using those recorded settings and preserves the original provider output in its authorized storage.

The tool performs local preparation and import. Provider execution belongs to the selected adapter and its authorized run budget. Each output path is new, preserving earlier runs.

## Receipt contract

An adapter writes one JSON object per requested task outcome:

| Field | Value |
|---|---|
| `task_id` | Exact ID from the bundle |
| `status` | `completed`, or a recorded failure status such as `timeout`, `quota`, `provider_error` or `ungradeable` |
| `decision` | Typed numeric decision for completed outputs; null for failures |
| `model_reported` | Exact pinned model ID for completed outputs; reported ID or null for failures |
| `model_version_reported` | Provider-returned exact version when available; otherwise null or omitted |
| `request_sha256` | Canonical request digest copied from the manifest for this task |
| `transport_request_sha256` | Digest of the actual serialized provider request when recorded; otherwise null |
| `error_code` | Null for completed outputs; a short machine-readable failure code otherwise |

Use `ungradeable` with an appropriate code for a refusal or extraction failure. Keep raw exception text and private provider details in authorized logs. Record `model_version_reported` whenever the provider supplies it; the importer checks it against the declared version. The run reports observed versions and counts receipts where that metadata is unavailable. Every retry keeps its original receipt; select the analyzed attempt under a declared rule before import. The importer accepts one selected receipt per task and rejects duplicate IDs, foreign tasks, model mismatches and mismatched request hashes.

Malformed numeric decisions become `invalid_decision` outcomes with their source-receipt digests retained. Provider-completed, usable, missing and independently validated counts have separate meanings. Independent validation remains null until its evidence exists. Hashes provide reproducible linkage; authenticity and faithful adapter execution require the original receipt trail.

```bash
python tools/version_benchmarks.py import \
  --bundle local-runs/gemini4-bundle \
  --responses local-runs/gemini4-receipts.jsonl \
  --out local-runs/gemini4-imported.json

python tools/version_benchmarks.py compare \
  --baseline local-runs/jev-1.13.0-baseline.json \
  --candidate local-runs/gemini4-imported.json \
  --out local-runs/gemini4-vs-jev-1.13.0.json
```

## Read a version comparison

Every model's coverage uses the full task population. Paired metrics use the exact shared usable IDs, with the candidate listed first; a positive accuracy difference means candidate minus baseline on that subset. The report also gives family-specific results, probability metrics and ambiguous maxima. The deterministic 500-replicate interval resamples declared scenario groups and requires at least ten matched groups. Smaller comparisons retain their measured difference and a null interval.

Every reference task must declare a nonempty `group_id`, and all members of a group must use the same split. Choose source/scenario clusters that keep related variants together. Group IDs are declared sampling units; shared templates can leave dependence across groups and constrain broader inference. Preparation and import validate these group requirements before accepting a run.

Every imported run records a scoring signature containing the exact `comparison_analysis.py` and `version_benchmarks.py` file hashes. It also records the 0.5 thresholds, independent-label treatment, positive-mass distribution normalization, declared-order tie rule and bootstrap settings. Validation checks the signature's digest and supported conventions. Prior implementation hashes remain visible alongside the current release signature.

Task hashes must match exactly. A comparison reports whether the two recorded scoring signatures agree, then rescores both stored decision sets with the current released implementation. A changed threshold or scoring convention requires its own supported protocol version. File hashes support reproduction with the corresponding release files; provenance authentication requires the original receipts and release record.

Differences in serving configuration remain visible through `configuration_match`; a legacy baseline returns null because its original settings are unavailable. Interpret changes jointly with task coverage, settings and uncertainty. Claims about improvement across versions need the same declared interface, observed version evidence and suitable controls. Independent domain review, multilingual transfer and live agent behavior have separate evaluation tracks.
