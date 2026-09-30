import json
from pathlib import Path

import pytest

from duecare_eval.rubric_examples import score_instances, score_one, validate_bank


def bank():
    return json.loads((Path(__file__).resolve().parents[1] / "examples/grading_rubrics.json").read_text())


def task(name):
    return next(row for row in bank()["worked_instances"] if row["instance_id"] == name)


def response(name, answer, status="completed"):
    return {"instance_id": name, "status": status, "answer": answer}


def test_catalog_counts_and_arithmetic_references():
    summary = validate_bank(bank())
    assert summary["rubrics"] == 12
    assert summary["worked_instances"] == 19
    assert summary["illustrative_responses"] == 15


def test_component_detection_penalizes_extra_and_missing_labels():
    result = score_one(task("indicator-composite"), ["document_control", "threat"])
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["correct"] is False


def test_empty_benign_control_has_an_exact_empty_answer():
    assert score_one(task("indicator-benign-control"), [])["exact_set"] is True
    assert score_one(task("indicator-benign-control"), ["threat"])["correct"] is False


@pytest.mark.parametrize("answer", [float("nan"), float("inf"), True, -0.1, 1.1, "0.8"])
def test_probability_contract_rejects_invalid_values(answer):
    with pytest.raises(ValueError):
        score_one(task("sufficiency-full-total"), answer)


def test_false_confidence_has_a_brier_penalty():
    result = score_one(task("sufficiency-missing-total"), 0.9)
    assert result["correct"] is False and result["brier"] == pytest.approx(0.81)


def test_numeric_error_is_preserved():
    result = score_one(task("arithmetic-total"), "1250.01")
    assert result == {"correct": False, "absolute_error": "0.01"}


def test_arithmetic_reference_is_independently_recomputed():
    value = bank()
    row = next(row for row in value["worked_instances"] if row["instance_id"] == "arithmetic-total")
    row["expected"] = "1200"
    with pytest.raises(ValueError, match="declared calculation"):
        validate_bank(value)


def test_unadjudicated_reference_stays_out_of_scored_accuracy():
    value = bank()
    value["worked_instances"][0]["reference_basis"] = "unadjudicated"
    with pytest.raises(ValueError, match="supported reference basis"):
        score_instances(value, [])


def test_missing_invalid_and_failed_remain_in_denominator():
    result = score_instances(bank(), [response("arithmetic-total", "1250"),
                                     response("arithmetic-paid", "bad"),
                                     response("arithmetic-extra-cost", None, "quota")])
    assert result["requested"] == 19 and result["assessed"] == result["correct"] == 1
    assert result["statuses"] == {"missing": 16, "assessed": 1, "invalid": 1, "unavailable": 1}
    assert result["accuracy_requested"] == pytest.approx(1 / 19)


def test_pair_consistency_maps_positions_back_to_actions():
    result = score_instances(bank(), [response("action-pair-forward", "A"), response("action-pair-reverse", "B")])
    assert result["both_order_pairs"] == {"complete": 1, "consistent": 1}
    result = score_instances(bank(), [response("action-pair-forward", "A"), response("action-pair-reverse", "A")])
    assert result["both_order_pairs"] == {"complete": 1, "consistent": 0}


def test_duplicate_ids_are_rejected():
    item = response("arithmetic-total", "1250")
    with pytest.raises(ValueError, match="unique"):
        score_instances(bank(), [item, item])


def test_ranking_reports_partial_pairwise_credit():
    result = score_one(task("ranking-authorized-workflow"), ["retrieve_authorized_case", "obtain_permission", "draft_options"])
    assert result["correct"] is False
    assert result["pairwise_order_correct"] == 2 and result["pairwise_order_total"] == 3


def test_teaching_examples_keep_authorship_separate_from_model_outputs():
    value = bank()
    value["five_tier_examples"][0]["model_execution"] = "completed"
    with pytest.raises(ValueError, match="authorship"):
        validate_bank(value)
