# Blind assessment of the 125-answer bank

Jev 1.13.0 assessed all 125 authored candidates and a balanced sample of 50 answer pairs, each presented in both orders. The pilot completed 225 requests with 225 physical calls and zero unknown journal outcomes on September 30, 2026 at 22:21:52 UTC.

The [reference bank](REFERENCE_BANK.md) uses the complete source prompts: four exact published prompts and a separately identified full notebook attack variant. Every case has five intended quality tiers and five presentation profiles. Authoring labels and profile metadata were withheld from the hosted judge.

## Observed results

| Measurement | Result |
|---|---:|
| Pointwise requests recorded | 125 / 125 |
| Valid proposed overall grades | 122 / 125 |
| Exact intended-tier matches | 76 / 125 requested; 76 / 122 assessed |
| Ordered pairwise requests recorded | 100 / 100 |
| Logical pairs with both orders | 50 / 50 |
| Pairs retaining the same candidate or tie after reversal | 39 / 50 |
| Cross-tier choices agreeing with the intended quality ordering | 45 / 50 ordered requests |
| Same-tier comparisons returning a tie | 12 / 50 ordered requests |

Three overall-grade fields failed the declared numeric validation. Their requested slots and other available measurements remain in the released records. The 32 packets with field warnings retained valid individual scores and returned choice IDs. No whole-packet retry was performed solely for a probability-mass warning.

## How to read the comparison

The intended tiers describe analyst-authored candidate design. Actual hosted grades and preferences are separate measurements. Independent substantive validation of the intended tiers remains open. A disagreement can expose a problem in the candidate, the judge or the assumed quality relation.

Profiles vary length, register, format and specificity. Responses assigned the same intended tier can therefore differ in substantive coverage as well as presentation. The 12 ties describe observed treatment of this bank; content review is needed to distinguish presentation sensitivity from a supported quality preference.

The sample contains ten logical pairs per case: five within-tier profile contrasts and five cross-tier comparisons at matched profiles. Both candidate orders are retained. Every case, tier and profile is represented in the sample, while every candidate receives a pointwise request. The pilot measures 100 of the prepared bank's 500 ordered pair requests.

The six-criterion weights and critical caps are predeclared in the [behavior rubric](../examples/reference_bank_v1/behavior_rubric.json). Criterion scores, proposed overall grades, pairwise choices and authoring intent remain separate. These observations support instrument research on the declared cases and reference assumptions.

## Reproduce offline

Run `python tools/reproduce_longform_anchor_pilot.py --check`. The verifier checks the numeric package and reference-bank hashes, joins candidate and pair identities, and recomputes the intent matrix and swapped-order counts.

- [Numeric observations](../results/longform_anchor_pilot_2026-09-30.json)
- [Recomputed findings](../results/longform_anchor_pilot_2026-09-30.findings.json)
- [Manifest and resource accounting](../results/longform_anchor_pilot_2026-09-30.manifest.json)
