# Ranked correctly but accepted at the declared threshold

The released arithmetic fixture contains six true claims and seven false claims. It supplies explicit assumptions about simple annualization or adding monthly components; it makes no statutory APR claim. The labels can be recomputed from those numbers.

At the predeclared 0.5 decision threshold, Jev accepted all 13 claims: 6 true positives, 7 false positives, no true negatives and no false negatives. Accuracy was 6/13, balanced accuracy 0.50 and Brier score 0.244369.

However, the true-claim probabilities ranged from 0.86 to 0.95; false-claim probabilities ranged from 0.51 to 0.80. Every true claim ranked above every false claim, giving AUROC 1.00 within this tiny set. The observation is not evidence of absent discrimination. It exposes a decision-threshold problem and motivates calibration testing. An apparent separating cutoff chosen after seeing these 13 outcomes is not a validated solution.

This is a small, constructed diagnostic with related examples, not a population estimate. The report does not establish that the model improved, regressed or is generally unable to reason about finance. A follow-up should preregister balanced numeric claims, vary phrasing and context, separate calibration and held-out sets, and report both probability quality and decisions.

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
