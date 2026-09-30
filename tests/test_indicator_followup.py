import math
import pytest
from duecare_eval.indicator_followup import tasks, blind_tasks, assess, CONDITIONS


def test_balanced_fact_sets_and_shared_split():
    rows = tasks()
    assert len(rows) == 384
    assert sum(r["split"] == "held_out" for r in rows) == 288
    assert all(sum(k in r["expected"] for r in rows) == 192 for k in CONDITIONS)
    groups = {}
    for row in rows:
        groups.setdefault(row["group_id"], set()).add(row["split"])
    assert len(groups) == 64 and all(len(v) == 1 for v in groups.values())


def test_blind_views_retain_facts_and_hide_references():
    rows = tasks()
    assert rows == tasks()
    blind = blind_tasks(rows)
    assert all(not {"expected", "metadata", "split", "group_id"} & set(r) for r in blind)
    assert len({r["input_sha256"] for r in blind}) == 384


def test_component_errors_and_missing_stay_visible():
    rows = tasks()
    row = next(r for r in rows if len(r["expected"]) == 2)
    p = {k: float(k in row["expected"]) for k in CONDITIONS}
    p[row["expected"][0]] = 0
    result = assess(rows, {row["task_id"]: {"probabilities": p}})
    assert result["requested"] == 384 and result["usable"] == 1 and result["missing"] == 383
    assert result["exact_sets"] == 0 and result["false_negatives"] == 1
    assert result["micro_precision"] == 1 and result["micro_recall"] == .5


@pytest.mark.parametrize("bad", [float("nan"), 1.1, -0.1, True])
def test_invalid_probabilities_preserve_denominator(bad):
    rows = tasks()[:1]
    p = {k: .5 for k in CONDITIONS}
    p[next(iter(p))] = bad
    result = assess(rows, {rows[0]["task_id"]: {"probabilities": p}})
    assert result["invalid"] == 1 and result["requested"] == 1 and result["usable"] == 0


def test_oracle_checks_invariance_and_heldout_counts():
    rows = tasks()
    responses = {r["task_id"]: {"probabilities": {k: float(k in r["expected"]) for k in CONDITIONS}} for r in rows}
    result = assess(rows, responses)
    assert result["exact_sets"] == 384 and result["micro_f1"] == 1
    assert result["by_split"]["held_out"]["usable"] == 288
    assert result["invariance"] == {"complete_fact_groups": 64, "stable_predicted_sets": 64}


def test_unknown_ids_rejected():
    with pytest.raises(ValueError, match="unknown_followup_task"):
        assess(tasks(), {"wrong": {"probabilities": {}}})


@pytest.mark.parametrize("bad", [None, list(CONDITIONS)])
def test_malformed_distribution_counts_as_invalid(bad):
    rows = tasks()[:1]
    result = assess(rows, {rows[0]["task_id"]: {"probabilities": bad}})
    assert result["requested"] == 1 and result["invalid"] == 1 and result["usable"] == 0
