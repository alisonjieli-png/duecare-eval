from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import structured_extraction as X


Q = {"binary": {"type": "noul"}, "action": {"type": "choice", "criteria": {"a": None, "b": None}}}


def body(probability=.5):
    return {"answers": {"binary": {"type": "noul", "noul": probability},
                        "action": {"type": "choice", "choice": "b", "probabilities": {"a": .5, "b": .5}}}}


def attempt(text, index=1, status="malformed_json"):
    return {"attempt": index, "status": status, "transport_status": "completed", "response": text}


def test_complete_inner_object_is_read_without_adding_a_character():
    text = json.dumps(body())[:-1]
    obj, span = X.anchored_object(text)
    assert json.loads(text[span[0]:span[1]]) == obj == body()["answers"]
    assert text[span[1]:] == ""
    selected, method, valid, invalid = X.select_attempt([attempt(text)], Q)
    assert selected["response"] == text and method == X.INNER
    assert valid["binary"]["probability"] == .5 and not invalid
    assert valid["action"]["selected"] == "b" and valid["action"]["maxima"] == ["a", "b"]


@pytest.mark.parametrize("transform", [lambda t: t[:-1], lambda t: t + ',"extra":1}',
    lambda t: t + "{}", lambda t: 'prefix' + t,
    lambda t: t.replace('"answers":', '"unknown":0,"answers":')])
def test_missing_inner_brace_unknown_outer_keys_and_multiple_objects_fail(transform):
    text = transform(json.dumps(body())[:-1])
    with pytest.raises(ValueError):
        X.anchored_object(text)


def test_duplicate_inner_keys_and_nonfinite_values_fail():
    with pytest.raises(ValueError, match="duplicate"):
        X.anchored_object('{"answers":{"binary":{},"binary":{}}')
    with pytest.raises(ValueError, match="nonfinite"):
        X.anchored_object('{"answers":{"binary":{"noul":NaN}}')


def test_complete_object_can_have_only_partial_numeric_validity():
    value = body(); value["answers"]["action"]["probabilities"]["a"] = .49
    text = json.dumps(value)[:-1]
    _, method, valid, invalid = X.select_attempt([attempt(text)], Q)
    assert method == X.PARTIAL["anchored_object"]
    assert valid == {"binary": {"probability": .5}}
    assert invalid == {"action": "choice_probability_mass"}
    assert value["answers"]["action"]["probabilities"]["a"] == .49


def test_earliest_partial_selection_is_independent_of_probability():
    values = []
    for p in (.1, .9):
        b = body(p); b["answers"]["action"]["probabilities"]["a"] = .49
        values.append(json.dumps(b)[:-1])
    selected, _, valid, _ = X.select_attempt([attempt(values[0]), attempt(values[1], 2)], Q)
    assert selected["attempt"] == 1 and valid["binary"]["probability"] == .1


def test_whole_fence_complete_precedes_anchored_complete():
    first = attempt(json.dumps(body(.1))[:-1])
    second = attempt("```json\n" + json.dumps(body(.9)) + "\n```", 2)
    selected, method, valid, _ = X.select_attempt([first, second], Q)
    assert selected["attempt"] == 2 and method == X.M.FENCE_METHOD
    assert valid["binary"]["probability"] == .9


def test_missing_redundant_type_tags_use_exact_known_schema_and_are_recorded():
    value = body()
    for answer in value["answers"].values():
        del answer["type"]
    original = deepcopy(value)
    selected, method, valid, invalid = X.select_attempt([attempt(json.dumps(value), status="invalid_response")], Q)
    assert method == X.KNOWN + ":plain_json"
    assert valid["binary"]["probability"] == .5 and not invalid
    option = next(o for o in X.candidates(selected, Q) if o["kind"] == "question_schema/plain_json")
    assert option["missing_type_tags"] == ["action", "binary"]
    assert value == original


def test_wrong_type_extra_keys_and_unknown_ids_are_rejected_without_imputation():
    value = body(); value["answers"]["binary"]["type"] = "choice"
    valid, invalid, missing = X.known_schema_values(value["answers"], Q)
    assert "binary" not in valid and invalid["binary"] == "answer_type_mismatch" and missing == []
    value = body(); del value["answers"]["binary"]["type"]; value["answers"]["binary"]["reason"] = "extra"
    valid, invalid, missing = X.known_schema_values(value["answers"], Q)
    assert "binary" not in valid and missing == []
    value = body(); value["answers"]["unknown"] = {"noul": .9}
    with pytest.raises(ValueError, match="question_id"):
        X.known_schema_values(value["answers"], Q)


def test_frozen_working_view_preserves_baseline_and_marks_adapter_conditions():
    root = Path(__file__).resolve().parents[1]
    result = X.reproduce(root)
    assert result == json.loads((root / "results/structured_extraction_2026-10-01.findings.json").read_text())
    assert result["cohorts"]["baseline"]["totals"]["complete_panels"] == 75
    assert result["cohorts"]["baseline"]["totals"]["partial_panels"] == 5
    assert result["cohorts"]["adapter_v1_1"]["totals"]["complete_panels"] == 17
    working = result["working_configurations"]
    assert sum(m["typed_fields_available"] for m in working.values()) == 1147
    assert sum(m["complete_panels"] for m in working.values()) == 91
    assert working["gpt-oss-20b"]["binary_exact_half"] == 13
    assert working["glm-5-3"]["source_cohort"] == "adapter_v1_1"
    assert working["glm-5-3-flash"]["source_cohort"] == "adapter_v1_1"
    assert working["gpt-oss-20b"]["source_cohort"] == "baseline"
    for arm in ("bare", "grounded"):
        assert len(result["working_config_intersection"][arm]["by_question"]["financial_pressure"]) == 4


def test_recovered_missing_type_tags_are_explicit_in_numeric_records():
    root = Path(__file__).resolve().parents[1]
    rows = [json.loads(line) for line in (root / "results/structured_extraction_2026-10-01.jsonl").read_text().splitlines()]
    row = next(r for r in rows if r["cohort"] == "adapter_v1_1" and r["target_id"] == "glm-5-3-flash" and r["case_id"] == "WRITEUP-16674-CASE-3" and r["arm"] == "bare")
    assert row["strict_status"] == "invalid_response"
    assert row["analysis_status"] == "completed"
    assert len(row["missing_type_tags"]) == 12
    assert row["selection_method"] == X.KNOWN + ":plain_json"
