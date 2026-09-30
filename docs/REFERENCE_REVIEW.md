# Composite-indicator reference review

The original core suite includes 1,000 composite-indicator tasks across 500 declared pairs and 156 distinct situation strings. Jev returned usable independent probabilities for all 13 indicator labels in every task. At the declared 0.5 threshold, its selected label set matches the generator-assigned reference in 368 tasks: 36.8% exact-set agreement.

That result describes agreement with the existing references. The reference review examines how those assigned sets correspond to the facts in each task. Model observations, task strings, reference sets and the published score retain their original versions.

## What the model received

All 13 short label names were supplied in `indicator_catalog`, alongside the situation, corridor, role and stage. The catalog values are names such as "Restriction of movement or communication" and "Isolation from support networks". The original composite payloads use this catalog directly; full taxonomy criteria and supporting evidence have separate review work ahead.

The instruction asks for an independent probability for each listed indicator and explicitly distinguishes indicators from criminal findings. The payload uses 13 independent probability questions. Their values can therefore sum above one.

The frozen generator combines two selected example fragments. Its structural reference lists the two seed indicator IDs, or the first ID when the second fragment is replaced with a lookalike. This reproduces the generator's intended reference exactly. Establishing every indicator supported by the combined facts also requires semantic review across labels.

## Two cases that need reference review

### Monitored door

Task ID: `DEC2-7f2d0d3a4283af3959098a5a`

Exact supplied situation:

> door monitored; additionally, an accommodation charge was itemised and deducted with a signed agreement, for a facility the worker chose to use.

The assigned set is `{IND-H-06}`. The supplied label name is "Restriction of movement or communication". Jev returned `P(IND-H-06) = 0.39`, below the declared threshold.

The fact describes monitoring. Whether that monitoring constrains the worker's ability to leave or communicate requires an explicit condition. This is a reference-interpretation question alongside the measured disagreement.

Reconstructing the request with the frozen adapter produces SHA-256 `92ab97421be97b575f00d74690eebba7648f273a381acdde59ed04f49bcc162a`, matching the recorded request digest. The payload's evidence array is empty.

### Contact with one migrant centre

Task ID: `DEC2-0c592f4e35dc6f8accd62c68`

Exact supplied situation:

> no contact with a migrant centre; additionally, the contract was provided in the worker's preferred language and an interpreter attended the signing.

The assigned set is `{IND-S-05}`. The supplied label name is "Isolation from support networks". Jev returned `P(IND-S-05) = 0.12`.

The situation establishes absence of contact with one centre. The broader question concerns independent access to support. Review should distinguish contact, access, choice and an imposed restriction before assigning a complete label set.

The reconstructed payload SHA-256 is `b5b23d5c3bef9b5296c28fad74bdd19ec6b7b4094ae8bb0f6b1678b10a209699`, matching the recorded request digest. Its evidence array is also empty.

The numeric observations and original task IDs are retained in the [comparison evidence](../results/comparison_2026-09-30/observations.jsonl) and [task references](../results/comparison_2026-09-30/tasks.jsonl).

## Component agreement

Across 13,000 task-label comparisons, the existing references yield 1,395 true positives, 1,080 false positives, 105 false negatives and 10,420 true negatives at threshold 0.5. Here these are score categories relative to the assigned references.

| Measure | Result |
|---|---:|
| Exact-set agreement | 368/1,000 = 36.8% |
| Micro precision | 56.36% |
| Micro recall | 93.00% |
| Micro F1 | 70.19% |
| Hamming disagreement | 1,185/13,000 = 9.12% |

[Label-level component counts](../results/composite_indicator_components_2026-09-30.json) preserve precision, recall, F1, Hamming disagreement and the source hashes for all 13 labels. The audit reconstructed all 1,000 provider payloads; every digest matches its recorded observation.

Most label-level disagreements are additional selected labels: 1,080 of 1,185. This pattern deserves inspection of overlapping concepts, the specificity of the supplied names and the completeness of the assigned sets. It supports a narrower interpretation than treating every disagreement as an established detection error.

## Methodology to continue

The follow-up explicit-condition probes make the required facts and the intended distinction visible. Their outcomes should retain their own protocol and comparison table. The 384-task follow-up is a separate instrument from the original 13-label family.

Review each ambiguous original reference against an explicit definition, recording supported, absent and unresolved conditions. Then assess all labels against the combined facts, including implications introduced by either fragment. Give any revised reference set its own version and preserve both scores. Matched comparisons can then separate effects of clearer definitions, fuller facts and the model's response to those changes.

Independent domain and worker-informed assessment can extend this semantic review. The current evidence supports reproducible measurements of agreement, probability outputs and sensitivity under the declared task designs.
