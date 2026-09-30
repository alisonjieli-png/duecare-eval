# DueCare: evidence, decisions and model behavior

Release `v0.1.0-rc.3` brings together six served model configurations, role and scenario comparisons, indicator subgroups, action rankings, advanced source questions and graded response examples.

## Recorded results

- Jev has usable observations for all 12,000 core tasks and all 7,200 attack tasks after a separately recorded recovery supplement. Agreement with the declared references is 10,067/12,000 (83.9%) and 5,341/7,200 (74.2%). Original outcomes and recovery records remain distinct.
- The six-model comparisons use exact shared task IDs within each suite: 391 core, 386 attack/control, 117 cross-border and 186 reference tasks. The report includes full coverage, errors, per-role and per-indicator metrics, probability quality and paired scenario-group intervals.
- Jev matched all 384 exact indicator sets in the new six-condition follow-up, including 288 held-out cases. These hold out combinations of the same definitions and fact sentences. All 64 fact groups retained their predicted set across six role/presentation views.
- The source study retains 27,908 recorded Jev assessments and 3,456 corrected style-judge decisions in its earlier dated snapshot. The report includes all 105 advanced/general and 40 referral questions with their observed coverage and descriptive outputs.

## Methods and use

The package adds 12 grading methods, 19 worked instances and three five-tier teaching arrays containing 15 analyst-authored responses. Component precision/recall/F1, exact-set agreement, arithmetic error, probability scores, ranking and order consistency preserve the distinctions needed to interpret a grade.

The version workflow prepares blind bundles, records model/configuration/scoring identities, imports receipts and compares exact shared tasks. Future Jev versions and Gemini 4 have distinct target records. Each future run requires a confirmed served model identifier and version.

The CLI provides readable summaries, `--json`, `doctor` and `comparisons`. The README, current guides and explanatory code comments describe the benchmark's purpose, behavior and evidence directly. Original prompts, executed inputs and recorded observations preserve their exact text.

## Evidence dates and validation

The comparison snapshot is dated September 30, 2026 at 20:05:37 UTC. Source/style prefixes were captured between 17:15 and 17:21 UTC. The indicator follow-up is dated 20:29:56 UTC and the terminal recovery supplement 20:30:13 UTC. Continuing campaigns produce later evidence under their recorded protocols.

The comparison projection explicitly checks nested task identities and numeric schemas. It retains 220 transport-completed records as invalid decisions in requested denominators. Earlier journals preserve the original transport outcomes, and the stricter projection has its own versioned analysis.

Public evidence consists of reviewed research examples and allowlisted numeric records. Independent worker, domain, legal and native-language review are additional validation milestones. The research program retains live agents, Migrasia evidence integration, multilingual assessment and recurring model-version comparisons.

## Reproduce offline

```bash
python tools/reproduce_comparisons.py --check
python tools/reproduce_findings.py --check
python tools/reproduce_indicator_followup.py --check
python tools/reproduce_jev_recovery.py --check
python tools/check_grading_rubrics.py
duecare-eval doctor
pytest -q
```

The source repository, matching manuscript, PDF and evidence manifests accompany this release. `SHA256SUMS` records the distributed file bytes. Rights information is in `NOTICE.md`.
