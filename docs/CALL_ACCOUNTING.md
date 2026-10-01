# How much testing was actually run?

The audited campaign subtotal is **204,248 recorded attempts or reservations**: 119,889 Jev API attempts and 84,359 native hosted language-model attempt reservations. There are 204,238 recorded outcomes and ten without a completion record at capture. Failed, truncated and invalid results remain in those counts. Six CLI invocations are separate because their internal provider-call counts are unknown.

The Jev receipt was captured at 02:31:16 UTC on October 1, 2026; native journals were captured from 02:38:18 to 02:38:22 UTC. Older bulk/variation jobs were still running. These dated snapshots retain their exact included journal prefixes while research continues.

## What the 32-answer figure describes

Thirty-two answers belong to one controlled experiment: two model configurations each answered sixteen context/scaffold conditions, based on two scenario packages. That study isolates specific changes in worker-choice advice, factual qualification and action ordering. The broader project includes thousands of decisions, generated response variants and grading requests.

The newest rc.4 expansion used 274 native hosted calls: 82 for the six-model source expansion and its probes/retries, 136 for the common-question bridge, 22 for adapter follow-ups, two for GLM's low-thinking control and 32 for the context/scaffold trial. Its one new Jev request returned HTTP402. Eight earlier Jev panels were reused in the bridge, adding zero calls. Two OpenCode CLI diagnostics are recorded separately.

## Jev campaign accounting

| Study family | Physical API attempts |
| --- | ---: |
| Source/perspective questions and supplements | 56,780 |
| Referral/control questions and recovery | 16,917 |
| Core decisions | 12,058 |
| Attack decisions | 7,239 |
| Judge calibration | 2,816 |
| Reference decisions | 202 |
| Main prose grading | 4,686 |
| Cross-border decisions and grading | 2,351 |
| Bulk response grading | 11,591 |
| Variation grading | 4,491 |
| Explicit-indicator follow-up | 384 |
| Original full-context panels and response grading | 110 |
| Five-tier anchor pilot | 225 |
| Transport pilot | 38 |
| New ILO/menu request, HTTP402 | 1 |
| Total | 119,889 |

Requested and usable logical outcomes answer a different question. The source/perspective study has 56,348 usable outcomes among 56,358 requested; referral/control has 16,798 among 16,800; the core and attack decision suites have 12,000/12,000 and 7,200/7,200. Jev assessed 122 usable overall grades among 125 anchor candidates. Repeated attempts and several fields in one request explain why call counts differ from these denominators.

## Breadth and validation

The source-context study uses 251 normalized source prompt texts, each asked 105 questions twice: 52,710 requested observations. A separate perspective expansion adds 3,648 requests. These repeat related source material. The close-reading source study has five complete prompts; its four advice-seeking cases and one explicit-analysis notebook variant retain separate strata. The 125 authored responses also share those five scenarios.

Call volume measures execution. Distinct source families, information stages, languages, question forms, benign controls and independent reviewers measure other parts of study breadth. This release claims zero independent human, legal or worker-informed validation of the fifty original long-form replies.

## Audit method

The accounting unions reservation identities using timestamp, provider, model, journal key and request hash. It removes 1,590 copied Jev reservations and 840 copied native reservations while retaining deliberate later attempts. Cached/reused observations and exported copies add zero calls. Earlier smoke/probe journals outside the declared campaign scope are excluded, making this an exact scoped subtotal rather than a lifetime total.

Public [Jev accounting](../results/jev_call_accounting_2026-10-01.json) and [native accounting](../results/native_call_accounting_2026-10-01.json) expose campaign totals, outcome coverage and provenance. Native source-prefix hashes identify the captured evidence; the Jev summary includes frozen audit hashes. Raw journals remain restricted. Offline checks reproduce public arithmetic; the private audit additionally verifies journal prefixes and deduplication.

```sh
python -c 'from duecare_eval.call_accounting import summarize; import json; print(json.dumps(summarize("."), indent=2))'
```
