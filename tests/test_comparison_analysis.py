from copy import deepcopy
from hashlib import sha256
import json

import pytest

from duecare_eval.comparison_analysis import (decision_summary, normalized,
    paired_uncertainty, reproduce, score, tier_summary, validate)


def task(ident="a", expected=True, group="g"):
    return {"suite": "fixture", "task_id": ident, "task_sha256": "a" * 64,
            "decision_type": "binary_probability", "expected": expected,
            "choices": [], "labels": [], "family": "screening", "group_id": group,
            "split": "test", "facets": {"role": "worker"}}


def observation(ident="a", model="one", p=.8, status="completed"):
    return {"suite": "fixture", "model_id": model, "task_id": ident,
            "status": status, "decision": {"probability": p} if status == "completed" else None,
            "attempt": 1, "request_sha256": "b" * 64, "receipt_sha256": "c" * 64,
            "model_reported": model}


def test_requested_denominators_retain_failures_and_missing():
    tasks = [task("a"), task("b"), task("c")]
    result = decision_summary(tasks, [observation(), observation("b", status="provider_error")], ["one"])["fixture"]["models"]["one"]
    assert result["usable"] == result["missing"] == 1
    assert result["requested"] == 3
    assert result["outcomes"] == {"completed": 1, "provider_error": 1}
    assert result["accuracy_on_usable"] == 1
    assert result["correct_over_requested"] == result["coverage"] == 1 / 3


def test_comparisons_share_exact_task_ids_and_facet_denominators():
    tasks = [task("a"), task("b", False)]
    observed = [observation("a", "one"), observation("b", "one", .9), observation("b", "two", .1)]
    result = decision_summary(tasks, observed, ["one", "two"])["fixture"]
    matched = result["all_model_intersection"]
    assert matched["tasks"] == 1
    assert matched["models"]["one"]["correct"] == 0
    assert matched["models"]["two"]["correct"] == 1
    assert matched["models"]["one"]["by_facet"]["role"]["worker"]["requested"] == 1
    assert result["pairwise"][0]["accuracy_difference_left_minus_right"] == -1


@pytest.mark.parametrize("change", [lambda x: x.update(task_id="unknown"),
    lambda x: x.update(model_id="unknown"), lambda x: x.update(status="unrecognized"),
    lambda x: x.update(prompt="unexpected text"),
    lambda x: x.update(decision={"probability": float("nan")}),
    lambda x: x.update(decision={"probability": True}),
    lambda x: x.update(decision={"probability": 1.1})])
def test_rejects_unknown_and_invalid_observations(change):
    row = observation()
    change(row)
    with pytest.raises(ValueError):
        validate([task()], [row], ["one"])


def test_duplicate_task_and_observation_rejected():
    with pytest.raises(ValueError):
        validate([task(), task()], [], ["one"])
    with pytest.raises(ValueError):
        validate([task()], [observation(), observation()], ["one"])


def test_distribution_contract_and_tie_rule_are_explicit():
    t = task()
    t.update(decision_type="categorical_distribution", expected="B", choices=["B", "A"])
    value, mass = normalized(t, {"probabilities": {"A": .4, "B": .4}})
    assert mass == .8 and value["probabilities"] == {"B": .5, "A": .5}
    result = score(t, {"probabilities": {"A": .4, "B": .4}})
    assert result["correct"] and result["ambiguous_maximum"]
    with pytest.raises(ValueError):
        normalized(t, {"probabilities": {"A": 1}})
    with pytest.raises(ValueError):
        normalized(t, {"probabilities": {"A": 0, "B": 0}})


def test_bootstrap_resamples_groups_and_is_deterministic():
    left, right = {}, {}
    for index in range(20):
        key = str(index)
        group = str(index // 2)
        left[key] = {"group_id": group, "correct": True}
        right[key] = {"group_id": group, "correct": False}
    result = paired_uncertainty(left, right)
    assert result["scenario_groups"] == 10 and result["matched_tasks"] == 20
    assert result["cluster_bootstrap_95_interval"] == [1, 1]
    assert result == paired_uncertainty(left, right)
    right["0"]["group_id"] = "changed"
    with pytest.raises(ValueError):
        paired_uncertainty(left, right)


def test_tier_intent_assessment_and_abstention_are_distinct():
    base = {"campaign": "bulk", "producer": "tactical", "case_id": "d" * 64,
            "requested_tier": 5, "requested_band": "short", "style": "prose"}
    requests = [{**base, "request_id": str(i)} for i in range(3)]
    observed = [{"campaign": "bulk", "producer": "tactical", "judge": "jev",
                 "request_id": str(i), "status": "completed", "grade": grade,
                 "abstain": abstain, "critical_failure": False, "receipt_sha256": "e" * 64}
                for i, grade, abstain in [(0, 2, False), (1, 5, True)]]
    result = tier_summary(requests, observed)[0]
    assert result["requested"] == 3 and result["assessed"] == 1
    assert result["missing"] == 1 and result["exact_tier_matches"] == 0
    assert result["mean_absolute_tier_difference"] == 3
    assert result["requested_assessed_matrix"]["5"]["2"] == 1
    bad = deepcopy(observed)
    bad[0]["grade"] = 6
    with pytest.raises(ValueError):
        tier_summary(requests, bad)


def test_reproduction_requires_captured_file_digests(tmp_path):
    payload = b"[]\n"
    (tmp_path / "tasks.jsonl").write_bytes(payload)
    manifest = {"schema": "duecare-comparison-snapshot/1.0.0", "files": {
        "tasks.jsonl": {"sha256": sha256(payload).hexdigest()}}, "models": {}, "snapshot_at": "fixture"}
    (tmp_path / "snapshot.json").write_text(json.dumps(manifest))
    (tmp_path / "tasks.jsonl").write_bytes(b"modified\n")
    with pytest.raises(ValueError, match="digest_mismatch"):
        reproduce(tmp_path)
