# Narrative and social-post instrument

This prepared instrument asks what a narrative supports, which concerns deserve attention and what useful step could come next. The [manifest](../examples/narrative_indicators_v2/manifest.json) records 39 context views, 156 specifications, 37 typed questions per panel and zero model calls. The resulting 5,772 question slots describe prepared work; API execution and model observations remain separate counts.

Each record has four prepared variants: source guidance off/on crossed with scaffold off/on. The record and questions stay fixed across that comparison. The current input protocol is `duecare-narrative-indicators/2.1.0`; the deterministic renderer is `duecare-narrative-renderer/1.2.0`.

## Records, controls and information stages

Five views preserve full source prompts unchanged: four published advice questions and the separately documented full notebook variant. Another 28 contain authored worker narratives, with concern and worker-control conditions in first-person and intake-report formats. Six authored social posts cover benign, concerning and ambiguous situations, a quoted instruction aimed at an automated reviewer, and a young applicant whose work circumstances are unclear.

These views share source themes and fact templates. They are controlled comparisons, with no claim that 39 views represent 39 independent incidents. First-person wording, intake formatting and social-post presentation retain their research provenance; they establish no verified person's history.

The worker-guilt theme includes views before commitment, after arrival and at a payment demand. Each view contains only events available by that stage. For example, a record before the first payday leaves actual wage withholding unstated. The generator and validator check this boundary rather than importing later events into an earlier assessment.

## Evidence, priority and legal elements

Each of eleven ILO indicators receives two questions. One distinguishes support in the record, explicit counterevidence and facts that are unstated or unclear. The other asks for action priority on a four-level scale. Several indicators can be supported together. Evidence confidence and urgency have separate distributions and rankings; a high confidence value supplies no automatic measure of severity.

The source-on variant includes short definitions of all eleven indicators and the dated nine-source briefing. Matched worker-control narratives supply affirmative protective facts, while ambiguous records preserve missing information. Compulsory lender, clinic and training-centre arrangements appear as mechanisms and follow-up topics, separately from the eleven-indicator taxonomy.

Three Palermo fields assess act, means and exploitation purpose separately. An age field distinguishes adult, under-18 and unknown. The renderer's child-rule flag removes the means requirement for an assessed child while retaining act and purpose assessment. Uncertain age remains unknown. These fields describe evidence support and leave a legal finding to qualified review.

## Concrete actions and fixed follow-ups

Eight independently rated actions allow more than one useful response: a private safety check, confidential support, preserving records, checking document access, checking wage access, a specific missing-fact question, ordinary information and scoped legal review. Seven first-action choices cover practical next steps. Scoped legal review remains an additional action after immediate safety and practical needs.

A separate choice selects one of eleven fixed follow-up questions. These ask about safe contact, threats, documents, usable wages, leaving, costs, changed terms, age, working conditions, support preferences or provider choice. The renderer combines the selected action and follow-up templates into readable text. It makes no additional LLM call and performs no external contact.

## Transparent routing and privacy guards

The renderer validates question IDs, answer types, probability values, distributions and score legends. It keeps ties visible and uses declared 0.6 support/action thresholds and a 0.1 choice margin. These are uncalibrated research settings.

Raw `review_priority`, the model's first-action selection and action probabilities remain available. The separate `effective_review_priority` records a rule-derived route with reason codes. Uncertain review labels lead to targeted clarification; urgent indicator priority leads to urgent private safety support. Supported coercion combined with an ordinary-information route leads to confidential specialist review. Consistency conflicts set `requires_consistency_review` and can replace an incompatible first action with a private safety check. A rule-derived route has no invented probability.

Known unsafe channels restrict the output to `safe_channel_only` and the safe-contact question, with no additional sensitive actions and an emergency-route caveat. Unknown channel safety is marked as requiring confirmation. Human permission, context-specific safeguarding and suitable local support remain necessary. Threshold calibration and independent worker-informed validation are open; the guards are a research prototype.

## References, files and verification

Automatic scoring compares only the eleven evidence classifications against authored visible-fact references. The five unchanged source contexts have no imposed answer key. Palermo interpretations, urgency and action quality receive no automatic correctness score or action gold label.

The [bank directory](../examples/narrative_indicators_v2/) contains full contexts, specifications, blind inputs, separate references, a catalog with indicator definitions and fixed action/question templates, and the archived earlier menu. Hidden authoring keys stay outside `model_input`; the validator rejects reference leakage. A future adapter should receive only that input plus its declared model binding and record the returned identity.

```sh
python3 tools/prepare_narrative_indicators_v2.py --check
```

This check reproduces the files without network access. Hosted measurements remain pending after the previously recorded Jev HTTP402. Preparation includes no fresh availability probe or new model result. Earlier executed inputs and observations retain their original versions.
