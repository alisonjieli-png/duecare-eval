# Benchmark scope and question inventory

DueCare evaluates how language models, decision engines and agent workflows handle migrant-worker protection tasks. It combines source research questions, adapted scenarios, controlled comparisons and recorded model outputs. Its reporting separates target capability, judge calibration and response generation so each result has a clear reference basis.

This inventory describes the September 30, 2026 evidence package. The [paper](PAPER.md) combines six-model comparisons, source studies, the completed composite-indicator follow-up and a Jev completion supplement. The [comparison findings](../results/comparison_2026-09-30/findings.json) expose exact shared samples and all captured facets. [The roadmap](ROADMAP.md) describes continuing work. A question catalog establishes implemented coverage; measured coverage requires a recorded outcome for that question, case, target and protocol.

## Questions readers can inspect

The [general question catalog](../examples/source_question_catalog.json) contains 105 exact questions across 41 families: 72 binary-probability questions, 29 categorical distributions and four ordinal distributions. The [referral catalog](../examples/referral_question_catalog.json) adds 40 exact questions: 32 binary-probability questions and eight categorical distributions. These 145 questions carry stable probe IDs and their reference status. Their current source-study reference status is `unadjudicated`; the reported findings describe observed judgments, repetition, sensitivity and choice consistency.

Three [source cases](../examples/reviewed_source_cases.jsonl), 27 [exact model payloads](../examples/observed_source_inputs.jsonl) and their [observed outputs](../results/observed_source_examples.jsonl) show how source text, the review question and a numeric response fit together. [The worked examples](ORIGINAL_CASES_AND_OBSERVED_RESULTS.md) explain their interpretation. The larger historical prompt and response banks remain in the research workspace under their recorded access classifications.

The adapted cross-border suite contains 937 tasks: 288 screening decisions, 576 safe-action boundary decisions, 48 sequential-evidence updates, 12 source-scope entailment decisions and 13 arithmetic diagnostics. Both [execution inputs](../examples/crossborder_blind_inputs.jsonl) and [scoring references](../examples/crossborder_references.jsonl) are available. The scoring references state the policy or structural expectation used for each task.

The corrected style-control suite contains 1,728 requests, split evenly between equivalent-assessment references and changed-conclusion references. Both candidate positions are represented. Its [execution inputs](../examples/style_comparison_blind_inputs.jsonl), [references](../examples/style_comparison_references.jsonl) and [presentation protocol](VARIATION.md) support inspection of format, register, length and conclusion effects.

## Facets and evidence

| Facet | Implemented questions or suite | Evidence and continuing work |
|---|---|---|
| Worker and employer perspectives | `worker_next`, `employer_next`, `employer_check_first`, `referral_worker_next`, `referral_employer_next` | Role-framed questions have recorded original-context observations. The separate information-projection arm has 3,648 planned assessments across 16 source cases, two roles, three reveal stages, 19 questions and two repeats; its measured coverage must be read separately. |
| Role-play and situational testing | Role metadata in the typed suites; worker/employer questions; before-signing and first-payment situations | The implementation includes role-framed decisions and case roles such as worker, employer, family, inspector, NGO and union. Live multi-turn role-play and autonomous agent runs remain follow-up work. |
| Direct, indirect and everyday questions | Four wording variants for each baseline concept; `is_this_okay`, `warning_sign`, `implied_dependency`, `off_record` | The source snapshot contains matched repetition and question-variant measurements. Semantic review distinguishes changes of wording from changes of the question being asked. |
| Actor, place, timing and purpose | `who_sets_terms`, `who_controls_access`, `where_decisive_action`, `when_terms_known`, `what_cost_difference`, `why_next_evidence` | Categorical outputs retain uncertainty options. The question catalog and released payloads make the requested distinction explicit. |
| Exploitation indicators and practical control | `baseline_worker_control_0` through `_3`, `warning_sign`, `can_say_no`, `revocable_financial_access`, `indicator_not_verdict`; typed `indicator_detection` and `indicator_composite` families | Source observations describe screening judgments. Typed decisions can also be checked against their declared structural references. Independent domain assessment remains a separate evidence task. |
| Financial exploitation and opaque arrangements | `baseline_financial_exploitation_0` through `_3`, cost-disclosure variants, `fee_or_interest`, `numbers_add_up`, `price_cashflow_match`, `documentation_conflict`, `off_record` | The package contains actual source-case judgments and a 13-question arithmetic diagnostic. Source-grounded arithmetic replication and held-out calibration are continuing experiments. |
| Cross-border substance and legal scope | `baseline_cross_border_evidence_0` through `_3`, `assignment_changes_cost`, `approval_scope`, `origin_approval_suffices`, `allowed_here`, `enough_for_illegal` | The study measures how models use the supplied record and distinguish the scope of an approval. Corridor-specific legal validation remains open. |
| Palermo and debt-bondage analysis | Six `palermo_*` probes and four `debt_*` probes, with [supplied frameworks](../examples/assessment_frameworks.json) | Models assess elements, combinations and missing evidence under a supplied framework. A verified legal conclusion requires the relevant facts, jurisdiction and qualified legal review. |
| Consent, timing and incomplete information | `signature_informed`, `optional_in_practice`, `provider_choice`, `cost_before_commitment`, `terms_changed_after_travel`, `worker_hidden_information`, `worker_knows_terms` | Original-context questions have partial observed coverage. The prepared perspective arm uses verbatim spans revealed in document order; that order is an experimental information condition. |
| Linked stages and compound reasoning | `downstream_enforcement`, `exit_new_charge`, `logic_documents`, `logic_earnings`, `logic_exit`, `logic_all`, `logic_any`, `logic_not_documents` | Compound and component outputs support consistency checks. Semantic review is required when assessing a possible logical disagreement. |
| Practical next steps and improvements | `worker_next`, `employer_next`, `before_signing`, `after_first_pay`, `improve_arrangement`, `private_before_confronting`, `preserve_worker_choice` | The outputs are model assessments of proposed actions under the supplied case. Worker-informed assessment of action quality and real service availability remains open. |
| Ranking and probability | Four `rank_score_*` probes, `rank_first_step`, twelve `rank_pair_*` probes | Four actions receive ordinal distributions; a separate question selects the first step; six pairs are presented in both orders. The dated source snapshot reports 815 stable outcomes among 943 resolved swaps and six ambiguous pairs. |
| Referrals, shared interests and decision control | The 40-question referral catalog, including `referral_coordination_evidence`, `referral_family_vs_control`, `referral_collection_vs_ownership`, `referral_control_hypothesis` | The design separates payment collection, ownership, decision authority and shared incentives. It also tests unrelated-context controls and benign interpretations. Source-reference adjudication remains open. |
| Reasoning and evidence audit | `purpose_not_outcome`, `reasoning_assumptions`, `decision_changing_fact`, `why_next_evidence`; tool-trace and source-scope tasks | The benchmark examines observable claims, evidence choices, decisions and tool events. Full premise-entailment review and live agent evaluation are continuing work. |
| Five-tier response comparison | Worst, bad, neutral, good and best arrays; 120 calibration anchors; bulk and presentation candidate protocols | The implementation records requested tiers, generated candidates and measured grades separately. Candidate acceptance, tier adherence and judge agreement require their own counts. |
| Hybrid judging and judge quality | Retrieval, keyword/fuzzy matching, propositions, rule checks, analogy, tools and cross-provider model judgments; 2,790 judge challenges | Corrected style judgments have complete released coverage for two judges. Full cross-provider coverage and independent calibration remain continuing work. |
| Attacks, evidence changes and refusal quality | 7,200 paired attack tasks across 18 transformations; benign controls; evidence and action-boundary tasks | Typed robustness results use paired clean/attack tasks. Helpful responses, over-refusal, harmful assistance and invalid responses retain separate outcomes. |
| Languages, agent workflows and time comparisons | Versioned domain packs, language metadata, observable traces and repeatable run manifests | Native-language assessment, live agent workflows, the Migrasia evidence binder and monthly/version comparisons remain explicit parts of the research program. |

The broader typed-decision program uses a 12,000-task core, a 7,200-task attack suite and a 201-task reference suite alongside the cross-border suite. The [comparison snapshot](../results/comparison_2026-09-30/snapshot.json), [coverage](../results/comparison_2026-09-30/coverage.json) and [findings](../results/comparison_2026-09-30/findings.json) record the later evidence capture. Suite sizes describe task inventories. Each model table supplies its requested, completed, usable and scored counts. Case-role facets describe the supplied case; role-framed questions describe the request made to the target; a live role-play experiment adds an interactive history and observed actions. Each belongs in its own coverage row.

## General question families

The IDs below resolve to exact question strings in the general catalog. The four baseline variants retain their individual strings and digests. The `rank_pair_*` IDs encode the two action indices and their presentation order.

| Family | Questions | Probe IDs |
|---|---:|---|
| actor_power | 3 | `change_obligation`, `concentrated_control`, `related_party_independence` |
| allowed_not_allowed | 1 | `allowed_by_contract` |
| conflict_of_interest | 1 | `affiliated_referral` |
| consent_and_choice | 3 | `signature_informed`, `optional_in_practice`, `provider_choice` |
| cost_disclosure | 4 | `baseline_cost_disclosure_0` through `_3` |
| cross_border_evidence | 4 | `baseline_cross_border_evidence_0` through `_3` |
| cross_border_substance | 3 | `assignment_changes_cost`, `approval_scope`, `origin_approval_suffices` |
| debt_bondage | 4 | `debt_services_pledged`, `debt_repayment_credit`, `debt_end_defined`, `debt_definition_scope` |
| employer_next_steps | 2 | `employer_check_first`, `employer_next` |
| ethical_scope | 1 | `acceptable_vs_legal` |
| everyday_baseline | 1 | `is_this_okay` |
| evidence_quality | 2 | `claimed_fact_verification`, `material_unknown` |
| financial_exploitation | 4 | `baseline_financial_exploitation_0` through `_3` |
| financial_substance | 3 | `dont_call_it_a_loan`, `numbers_add_up`, `fee_or_interest` |
| implicit_indicators | 1 | `implied_dependency` |
| improvement_options | 1 | `improve_arrangement` |
| incentive_analysis | 1 | `who_gets_more` |
| indicator_screening | 1 | `warning_sign` |
| indicator_vs_finding | 1 | `indicator_not_verdict` |
| information_asymmetry | 2 | `worker_hidden_information`, `worker_knows_terms` |
| legal_scope | 2 | `allowed_here`, `enough_for_illegal` |
| logical_composition | 6 | `logic_documents`, `logic_earnings`, `logic_exit`, `logic_all`, `logic_any`, `logic_not_documents` |
| multi_step_dependency | 2 | `downstream_enforcement`, `exit_new_charge` |
| nontransparent_behavior | 1 | `off_record` |
| opaque_payments | 3 | `payment_reconciliation`, `price_cashflow_match`, `documentation_conflict` |
| palermo_elements | 6 | `palermo_act`, `palermo_means`, `palermo_purpose`, `palermo_combination`, `palermo_consent`, `palermo_gap` |
| practical_choice | 1 | `can_say_no` |
| practical_control | 1 | `revocable_financial_access` |
| purpose_and_effect | 3 | `purpose_matches_practice`, `necessary_repeat_service`, `benefit_resolves_control` |
| ranked_next_steps | 17 | `rank_score_clarify_terms`, `rank_score_private_support`, `rank_score_check_actual_payments`, `rank_score_check_exit_and_access`, `rank_first_step`; `rank_pair_0_1_0`, `rank_pair_0_1_1`, `rank_pair_0_2_0`, `rank_pair_0_2_1`, `rank_pair_0_3_0`, `rank_pair_0_3_1`, `rank_pair_1_2_0`, `rank_pair_1_2_1`, `rank_pair_1_3_0`, `rank_pair_1_3_1`, `rank_pair_2_3_0`, `rank_pair_2_3_1` |
| reasoning_audit | 3 | `purpose_not_outcome`, `reasoning_assumptions`, `decision_changing_fact` |
| safe_next_steps | 2 | `private_before_confronting`, `preserve_worker_choice` |
| stage_next_steps | 2 | `before_signing`, `after_first_pay` |
| timing_and_disclosure | 2 | `cost_before_commitment`, `terms_changed_after_travel` |
| what | 1 | `what_cost_difference` |
| when | 1 | `when_terms_known` |
| where | 1 | `where_decisive_action` |
| who | 2 | `who_sets_terms`, `who_controls_access` |
| why_and_verification | 1 | `why_next_evidence` |
| worker_control | 4 | `baseline_worker_control_0` through `_3` |
| worker_next_steps | 1 | `worker_next` |

## Referral question families

The 32 binary probes cover disclosure, optionality, tied purchases, repeated services, independent pricing, shared collection, decision authority, fragmented obligations, timing, records and benign alternatives. Their exact wording and IDs are in the [referral catalog](../examples/referral_question_catalog.json).

| Categorical family | Probe ID | Requested distinction |
|---|---|---|
| referral_roles | `referral_who_benefits` | Who receives the financial benefit |
| control_hypotheses | `referral_control_hypothesis` | Independence, shared incentives, reported coordination, contradictory evidence or insufficient information |
| referral_next_steps | `referral_worker_next`, `referral_employer_next` | What the worker should clarify and what an employer should verify |
| control_evidence | `referral_evidence_priority` | Which record would resolve uncertainty about control |
| non_choice | `referral_nonchoice_mechanism` | The practical condition limiting a worker's choices |
| timing | `referral_when_to_intervene` | When checking obligations could prevent an uninformed commitment |
| improvements | `referral_improvement` | The change best supported by the described arrangement |

## Reading a result

Every finding should be read with its case population, protocol, model configuration, evidence available to the model, reference basis and requested denominator. Repeated calls and question variants share a source case. The release analysis preserves that relationship and requires complete matched groups for the question-sensitivity comparison.

The dated source snapshot contains 16,637 of 56,358 general/perspective assessments and 11,271 of 16,800 referral/control assessments. Both corrected style judges completed 1,728 requests. [Released analysis records](../results/release_findings.json) support these fixed figures while current research continues to collect evidence.

Independent worker, domain, legal and native-language review will extend the basis for interpreting deployment use. The present package supports reproducible analysis of the declared tasks, their references and observed API responses.

The [384-case indicator follow-up](../results/indicator_followup_findings.json) adds completed Jev observations under six explicit condition definitions. The [grading guide](GRADING_METHODS.md) and [rubric bank](../examples/grading_rubrics.json) provide 12 methods, 19 worked instances and 15 analyst-authored five-tier examples. [Version benchmarks](VERSION_BENCHMARKS.md) prepares the same task contracts for future Jev versions and the requested Gemini 4 target, with confirmed serving identities recorded for each run.
