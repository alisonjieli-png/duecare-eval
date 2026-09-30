from copy import deepcopy
import json
from pathlib import Path
import pytest
from duecare_eval.source_analysis import source_summary, style_summary, reproduce

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    catalog = [{"probe_id": f"p{w}", "decision_type": "binary_probability", "variant_group": "x", "wording": w} for w in range(4)]
    observations = [{"request_id": f"r{w}{r}", "case_id": "case", "probe_id": f"p{w}",
        "view_id": "original_full", "repeat": r, "track": "source_context", "model": "jev-1.13.0",
        "decision": {"probability": [.1, .3, .7, .9][w]}, "request_sha256": "digest"}
        for w in range(4) for r in (0, 1)]
    return observations, catalog


def test_repeat_stability_does_not_imply_wording_stability():
    data, catalog = fixture()
    result = source_summary(data, catalog, 16)
    assert result["coverage"] == .5
    matched = result["matched_question_groups"]
    assert matched["complete_groups"] == matched["distinct_source_texts"] == 1
    assert matched["mean_absolute_repeat_change"] == 0
    assert matched["mean_within_repeat_wording_span"] == pytest.approx(.8)
    assert matched["by_concept"]["x"]["repeat_groups_with_mixed_threshold_decisions"] == 2
    assert "accuracy" not in result


def test_incomplete_groups_and_other_views_are_not_pooled():
    data, catalog = fixture()
    assert source_summary(data[:-1], catalog, 8)["matched_question_groups"]["complete_groups"] == 0
    for row in data:
        row["view_id"] = "worker_early_record"
        row["track"] = "perspective_expansion"
    assert source_summary(data, catalog, 8)["matched_question_groups"]["complete_groups"] == 0


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_numeric_outputs_fail(bad):
    data, catalog = fixture()
    data[0]["decision"]["probability"] = bad
    with pytest.raises(ValueError):
        source_summary(data, catalog, 8)


def test_duplicate_identity_and_extra_private_fields_fail():
    data, catalog = fixture()
    with pytest.raises(ValueError):
        source_summary(data + [data[0]], catalog, 16)
    copied = deepcopy(data[0]); copied["request_id"] = "different-id"
    with pytest.raises(ValueError):
        source_summary(data + [copied], catalog, 16)
    data[0]["response"] = "private prose"
    with pytest.raises(ValueError):
        source_summary(data, catalog, 8)


def test_style_swap_maps_positions_back_to_candidate_identity():
    refs = [{"request_id": f"s{i}", "order": i, "swap_group_id": "pair", "method": "altered_conclusion:plain:prose",
             "expected_winner": "A" if i == 0 else "B"} for i in (0, 1)]
    data = [{"request_id": r["request_id"], "model": "judge", "winner": r["expected_winner"], "request_sha256": "digest"} for r in refs]
    result = style_summary(data, refs)
    assert result["correct"] == 2 and result["stable_swapped_pairs"] == 1
    data[1]["winner"] = "A"
    assert style_summary(data, refs)["stable_swapped_pairs"] == 0


def test_release_findings_reproduce():
    assert reproduce(ROOT) == json.loads((ROOT / "results/release_findings.json").read_text())
