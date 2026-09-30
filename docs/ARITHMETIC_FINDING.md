# Ranked correctly but accepted at the declared threshold

The released arithmetic fixture contains six true claims and seven false claims. Each task supplies the assumptions for simple annualization or adding monthly components. The reference labels follow from those explicit calculations; statutory APR interpretation is a separate research question.

At the predeclared 0.5 decision threshold, Jev accepted all 13 claims: 6 true positives, 7 false positives, no true negatives and no false negatives. Accuracy was 6/13, balanced accuracy 0.50 and Brier score 0.244369.

The true-claim probabilities ranged from 0.86 to 0.95; false-claim probabilities ranged from 0.51 to 0.80. Every true claim ranked above every false claim, giving AUROC 1.00 within this set. Ranking succeeded within these examples while the declared decision threshold accepted every false claim. Evaluating a revised cutoff requires separate calibration and held-out cases.

This diagnostic measures behavior on 13 related arithmetic examples. A follow-up should preregister balanced numeric claims, vary phrasing and context, separate calibration and held-out sets, and report both probability quality and decisions. Broader financial-reasoning and version-comparison claims require those additional measurements.

Recompute without an API account:

```python
from duecare_eval.public_cli import ROOT, load_rows
from duecare_eval.decisioning import score_decisions

tasks = [r for r in load_rows(ROOT / "examples/crossborder_references.jsonl")
         if r["family"] == "financial_arithmetic"]
responses = {r["task_id"]: r["decision"] for r in
             load_rows(ROOT / "results/jev_crossborder_responses.jsonl")}
print(score_decisions(tasks, responses)["binary"])
```
