# Preliminary research preview

This educational red-teaming release publishes the reviewed offline evaluation core, 937 constructed decision fixtures, 1,728 style comparisons with non-tie controls, Jev's numeric outputs for the 937-task fixture, aggregate campaign results, and a rebuilt PDF.

The aggregate snapshot is dated 2026-09-30 15:02 UTC. Background campaigns continued after that time; this release does not update itself or claim that queued work completed. The requested Tactical volumes are 20,080 plus a separate 4,320-register-variation supplement.

The report distinguishes requested tiers, source labels, constructed policy references and model assessments. It does not establish human agreement, legal validity, deployment safety or a model-class ranking.

Before publication, a pair-equivalence cue was found in the private style comparison prompt. The public version removes that cue and adds non-tie controls. Earlier cued results are not used as validity evidence. This correction affects the comparison protocol, not the ongoing candidate-generation text.

The public repository starts with new history. The restricted archive, raw model-response journals, private notebooks, operator configuration, and original Git history were not exported. Licence selection is pending; see NOTICE.md.

To reproduce the released Jev fixture score without an API account:

```bash
duecare-eval score --responses results/jev_crossborder_responses.jsonl --out local-runs/reproduced_jev.json
```
