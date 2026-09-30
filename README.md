# DueCare: a benchmark for decisions, responses and agent workflows

[![Offline checks](https://github.com/alisonjieli-png/duecare-eval/actions/workflows/tests.yml/badge.svg)](https://github.com/alisonjieli-png/duecare-eval/actions/workflows/tests.yml)
[Paper](output/pdf/duecare_preliminary_report.pdf) · [Readable manuscript](docs/PAPER.md) · [Original cases and observed responses](docs/ORIGINAL_CASES_AND_OBSERVED_RESULTS.md) · [Versioned release](https://github.com/alisonjieli-png/duecare-eval/releases/tag/v0.1.0-rc.3)

DueCare measures how AI systems reason about evidence, choose actions and respond to people. Its first domain is migrant-worker protection: exploitation indicators, recruitment and referral arrangements, financial pressure, cross-border relationships and practical next steps. The benchmark builds on Taylor S. Amarel's [original GPT-OSS investigation](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind) and [DueCare research](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1779103293133).

The benchmark joins source research cases, adapted scenarios and controlled comparisons with recorded model responses. Each task keeps its provenance, visible evidence and scoring assumptions. Public examples contain reviewed research text; their first-person wording belongs to the source material. Human, legal and worker-safety validation are separate research milestones.

## What DueCare measures

| Part of the benchmark | Questions it addresses |
|---|---|
| Typed decisions | How well does a system estimate probabilities, select categories, assign multiple indicators or choose an ordinal grade? |
| Roles and scenarios | How do actor roles, evidence gaps, adversarial framing and practical constraints affect the response? |
| Rankings and action choices | Which next step does the system prefer, and how stable is that choice when candidate order changes? |
| Source questions | How does the system assess control, consent, coordination, arithmetic and evidence sufficiency in the original research context? |
| Five-tier response arrays | Do generated answers meet the requested quality tier, and which errors separate neighboring tiers? |
| Hybrid judging and style controls | How do evidence checks, explicit rules and model judgments agree? How much do formatting, length and register affect the grade? |
| Agents, languages and time | How do complete tool-using workflows perform, how do results transfer across languages, and what changes between model versions? |

The public package contains the offline scoring core, decision tasks, controlled judge comparisons and dated observations. The broader research program develops the response arrays, agent evaluation, multilingual assessment and recurring version comparisons. [The roadmap](docs/ROADMAP.md) gives the evidence and next step for each arm.

## Findings in this release

Jev's core and attack suites have usable observations for every requested task after a separately recorded recovery supplement: **12,000/12,000 core tasks** and **7,200/7,200 attack tasks**. Reference agreement is 10,067/12,000 (83.9%) and 5,341/7,200 (74.2%), respectively. The [completion overlay](results/jev_recovery_2026-09-30.json) preserves original failures, supplemental observations and their timestamps.

The model comparison uses six served configurations and the exact task IDs completed by all six within each suite. The table reports correct decisions on those shared populations.

| Configuration | Core /391 | Attacks /386 | Cross-border /117 | Reference tasks /186 |
|---|---:|---:|---:|---:|
| Jev 1.13.0 | 320 (81.8%) | 252 (65.3%) | 109 (93.2%) | 143 (76.9%) |
| Gemma 4 31B | 323 (82.6%) | 272 (70.5%) | 112 (95.7%) | 102 (54.8%) |
| Kimi K3 | 304 (77.7%) | 254 (65.8%) | 115 (98.3%) | 104 (55.9%) |
| Tactical Gemma | 292 (74.7%) | 208 (53.9%) | 103 (88.0%) | 117 (62.9%) |
| DeepSeek Flash | 288 (73.7%) | 203 (52.6%) | 111 (94.9%) | 102 (54.8%) |
| GPT-OSS 20B | 263 (67.3%) | 153 (39.6%) | 112 (95.7%) | 105 (56.5%) |

![Model results on shared tasks](docs/figures/matched_model_comparisons.png)

The [comparison evidence](results/comparison_2026-09-30/findings.json) includes full requested denominators, missing and invalid outcomes, per-role and per-indicator results, and pairwise scenario-group intervals. Shared subsets follow campaign collection order. Each column therefore describes its own captured task population and reference contract.

Jev's full core shows a useful distinction: 1,990/2,000 single-indicator decisions match their references, while 368/1,000 composite-indicator outputs match the entire reference set. The [384-case follow-up](results/indicator_followup_design.json) tests six explicitly defined conditions across worker/employer perspectives and three presentations. Jev matched all 384 sets, including all 288 held-out cases, with zero added or missed labels. The [recorded follow-up](results/indicator_followup_findings.json) points toward the importance of definitions and task context when interpreting the broader indicator result.

**Repeated answers can be stable while question variants produce different assessments.** Across 312 complete groups covering 78 original source prompts, Jev's mean absolute probability change on repeat calls was 0.008. The mean range across four question variants was 0.314. Both use the same complete groups. The statistics measure different forms of variation. Some variants change scope or emphasis, so classifying a difference as an error requires semantic review.

![Question sensitivity on matched source groups](docs/figures/question_sensitivity.png)

**Judges detected changed conclusions more consistently than equivalent assessments.** Both completed the same 1,728 controlled comparisons, including both candidate orders.

| Judge | Changed conclusions | Equivalent assessments | Same outcome after order reversal |
|---|---:|---:|---:|
| DeepSeek Flash | 811/864 (93.9%) | 493/864 (57.1%) | 645/864 (74.7%) |
| Kimi K3 | 850/864 (98.4%) | 532/864 (61.6%) | 706/864 (81.7%) |

These scores measure agreement with the declared screening policy. The cases share scenario and presentation families, so interpretation stays at that level. The current comparisons use blind inputs; the earlier prompt that disclosed pair equivalence remains a separate diagnostic.

**The source examples show useful distinctions as well as limits.** In one related-provider case, Jev assigned 0.09 to whether family ties alone established common control and 0.66 to whether the described decisions showed coordination. Those questions ask different things. The [case gallery](docs/ORIGINAL_CASES_AND_OBSERVED_RESULTS.md) includes unchanged prompts, exact request payloads, numeric outputs and separately marked interpretation.

The [arithmetic diagnostic](docs/ARITHMETIC_FINDING.md) separates ranking from threshold behavior: all seven false claims exceeded the declared 0.5 decision threshold, while every true claim ranked above every false one. Those two observations motivate held-out calibration and threshold testing.

## Evidence and coverage

The six-model [comparison snapshot](results/comparison_2026-09-30/snapshot.json) is dated **20:05 UTC on September 30, 2026**. It contains 20,338 task references, 35,927 typed receipt records and 17,007 tier-assessment records. Its explicit task-identity and numeric checks classify 220 transport-completed outputs as invalid decisions and retain them in the requested denominators. Original journals preserve the earlier transport outcomes.

The source-question and style findings use a separate snapshot captured between **17:15 and 17:21 UTC**. Its [manifest](results/release_snapshot.json) gives each capture time and hash. The paper labels both evidence dates, while ongoing collection remains visible in the captured operational coverage.

| Study | Released completed observations | Planned requests |
|---|---:|---:|
| Jev original-case and perspective study | 16,637 | 56,358 |
| Jev referral and control study | 11,271 | 16,800 |
| DeepSeek corrected style controls | 1,728 | 1,728 |
| Kimi corrected style controls | 1,728 | 1,728 |

The 27,908 Jev observations are completed assessments. The general study has 105 question templates; the referral study has 40. Repeated questions and information views share source material, so the analysis groups related assessments. The perspective extension was awaiting its first completed observations at this snapshot.

The recovered reference bank contains 251 normalized prompts and 3,622 five-tier candidate answers. The historical baseline contains 300 saved GPT-OSS outputs from 100 source test IDs and 94 exact prompt texts. Source ratings, requested tiers and model-assessed grades have separate fields. An embedding-similarity ensemble produced the historical grades; independent human review remains an additional validation step.

## Reproduce the findings

Python 3.11 or later is required. The tested environment is Linux; the journal module uses POSIX file locking.

```bash
git clone https://github.com/alisonjieli-png/duecare-eval.git
cd duecare-eval
git checkout v0.1.0-rc.3
sha256sum --check SHA256SUMS
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,vault]'
python tools/reproduce_findings.py --check
python tools/reproduce_comparisons.py --check
python tools/reproduce_indicator_followup.py --check
python tools/reproduce_jev_recovery.py --check
python tools/check_grading_rubrics.py
duecare-eval doctor
duecare-eval findings
duecare-eval comparisons
pytest -q
```

The reproduction command validates the released numeric records and regenerates the exact [findings](results/release_findings.json) using local files. `doctor` checks that the required files are present. Commands print a readable summary by default; add `--json` for structured output in a script. The complete score written by `score --out` is always JSON.

For the earlier 937-task decision suite:

```bash
duecare-eval verify
duecare-eval score --responses results/jev_crossborder_responses.jsonl --out local-runs/reproduced_jev.json
```

`duecare-eval self-check` tests the scoring code against explicit reference answers. Model performance comes from the saved model-response files and their coverage.

## Read and inspect

- [Paper and methods](docs/PAPER.md): design, findings, interpretation and limitations.
- [Benchmark scope](docs/BENCHMARK_SCOPE.md): roles, scenarios, indicator families, rankings and the complete advanced-question inventory.
- [Grading methods](docs/GRADING_METHODS.md): worked rubrics, component metrics and response-quality examples.
- [Version benchmarks](docs/VERSION_BENCHMARKS.md): blind bundles and comparisons across served model versions.
- [Original cases](docs/ORIGINAL_CASES_AND_OBSERVED_RESULTS.md): three reviewed source examples with 27 exact model observations.
- [Numeric evidence](results/release_snapshot.json): source assessments, referral assessments and judge decisions, with provenance.
- [Full-text evaluation](docs/FULL_TEXT_EVALUATION.md): text fidelity and the optional encrypted-storage helper.
- [Roadmap](docs/ROADMAP.md): priorities, retained scope and evidence needed for each claim.
- [Contributing](docs/CONTRIBUTING.md): how to reproduce, report a discrepancy or propose a benchmark change.

All published aggregates can be recomputed from the released numeric observations. Three reviewed examples also include full source context for close reading. The remaining source bank stays in the private research archive. Aggregate reproduction and independent review of case meaning each have their own evidence requirements.

The 20,080-candidate Tactical campaign and 4,320-candidate presentation supplement have separate requested, generated, usable and assessed counts. The comparison snapshot includes observed tier matrices and generation summaries for both designs. Future Jev versions and the requested Gemini 4 target use the version-benchmark workflow with recorded provider and model identifiers.

## Build the paper

```bash
python -m pip install -e '.[report]'
python tools/build_report.py
```

The builder derives the manuscript, charts and PDF from the dated findings. PDF rendering can vary with dependency versions; SHA256SUMS verifies the exact files distributed in this release.

Interpret each result within its task population, model configuration and reference policy. Legal conclusions, worker-safety assessment and model-version comparisons require the additional evidence described in [disclosures](docs/DISCLOSURES.md) and [the roadmap](docs/ROADMAP.md). See [data handling](DATA_GOVERNANCE.md) for the public/private boundary and [rights](NOTICE.md) for reuse terms. Licence selection remains with the rights holder.
