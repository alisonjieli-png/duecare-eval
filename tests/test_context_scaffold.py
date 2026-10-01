from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import context_scaffold as C

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package():
    return (json.loads((ROOT / "results/context_scaffold_review_2026-10-01.json").read_text()),
            json.loads((ROOT / "results/context_scaffold_observations_2026-10-01.json").read_text()),
            [json.loads(line) for line in (ROOT / "examples/breadth_depth_v1/breadth_canary_v2_requests.jsonl").read_text().splitlines()])


def test_locked_results_reproduce_with_full_coverage_and_scoped_counts(package):
    result = C.reproduce(ROOT)
    assert result == json.loads((ROOT / "results/context_scaffold_findings_2026-10-01.json").read_text())
    assert result["requested"] == result["completed"] == result["usable"] == result["assessed"] == 32
    assert result["independently_human_validated"] == 0
    assert package[0]["private_verification"]["exact_quote_spans_checked"] == 268
    for model in C.MODELS:
        for axis in ("harness", "context"):
            assert result["pair_summaries"][axis][model]["pairs"] == 8
        for level in ("off", "on"):
            assert result["aggregate_by_model"][model]["by_harness"][level]["requested"] == 8
    assert result["worker_control_checks"]["all"] == {"requested": 16, "assessed": 16,
        "unwarranted_alarm_or_escalation": 0, "without_unwarranted_alarm": 16, "benign_over_refusal": 0}
    assert set(result["theme_question_packages"]) == {"salary_deduction", "worker_guilt"}


def test_scaffold_gains_and_regressions_are_counted_independently():
    result = C.reproduce(ROOT)
    deep = result["aggregate_by_model"]["deepseek-flash"]["by_harness"]
    gemma = result["aggregate_by_model"]["gemma4-31b"]["by_harness"]
    assert [deep[k]["criterion_full_credit"]["worker_agency"] for k in ("off", "on")] == [3, 8]
    assert [gemma[k]["criterion_full_credit"]["worker_agency"] for k in ("off", "on")] == [4, 6]
    assert [deep[k]["criterion_full_credit"]["factual_legal_calibration"] for k in ("off", "on")] == [3, 5]
    assert [gemma[k]["criterion_full_credit"]["factual_legal_calibration"] for k in ("off", "on")] == [0, 5]
    assert result["pair_summaries"]["harness"]["deepseek-flash"]["safe_action_ordering"] == {"improved": 4, "tied": 3, "regressed": 1}
    assert result["pair_summaries"]["harness"]["gemma4-31b"]["safe_action_ordering"] == {"improved": 2, "tied": 6, "regressed": 0}
    assert result["pair_summaries"]["harness"]["gemma4-31b"]["criteria"]["factual_legal_calibration"] == {"improved": 8, "tied": 0, "regressed": 0}
    assert result["pair_summaries"]["context"]["deepseek-flash"]["criteria"]["factual_legal_calibration"] == {"improved": 0, "tied": 4, "regressed": 4}


def test_public_row_allowlist_excludes_full_response_and_private_paths(package):
    package[0]["rows"][0]["response"] = "private full response"
    with pytest.raises(ValueError, match="allowlist"):
        C.validate(*package)


def test_response_hash_and_returned_model_must_match_observation(package):
    changed = deepcopy(package); changed[0]["rows"][0]["response_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="response_review_join"):
        C.validate(*changed)
    changed = deepcopy(package); changed[0]["rows"][0]["model_reported"] = "another-model"
    with pytest.raises(ValueError, match="model_identity"):
        C.validate(*changed)


def test_instrument_bytes_and_executed_request_contract_are_verified(package):
    changed = deepcopy(package); changed[2][0]["state"]["case_text"] += " Changed fact."
    with pytest.raises(ValueError, match="instrument_hash"):
        C.validate(*changed)
    changed = deepcopy(package)
    row = changed[0]["rows"][0]
    row["request_sha256"] = "0" * 64
    next(r for r in changed[1]["observations"] if r["request_id"] == row["request_id"])["request_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="executed_payload"):
        C.validate(*changed)


@pytest.mark.parametrize("score", [True, -1, 3, 1.5])
def test_scores_use_exact_predeclared_integer_scale(package, score):
    package[0]["rows"][0]["criterion_scores"]["worker_agency"] = score
    with pytest.raises(ValueError, match="criterion_score"):
        C.validate(*package)


def test_flags_remain_independent_boolean_observations(package):
    package[0]["rows"][0]["flags"]["privacy_or_retaliation_risk"] = 1
    with pytest.raises(ValueError, match="behavior_flag"):
        C.validate(*package)


def test_short_quote_hash_span_and_omission_status_are_verified(package):
    evidence = next(e for r in package[0]["rows"] for e in r["criterion_evidence"].values() if e["excerpt_status"] == "included")
    evidence["quote"] += " added"
    with pytest.raises(ValueError, match="short_excerpt"):
        C.validate(*package)


def test_withheld_quote_is_distinct_from_absence_after_full_read(package):
    evidence = next(e for r in package[0]["rows"] for e in r["criterion_evidence"].values() if e["excerpt_status"] == "hash_reference_only")
    assert evidence["quote"] is None and not evidence["absence_after_full_read"]
    assert C.digest(evidence["quote_sha256"])
    evidence["absence_after_full_read"] = True
    with pytest.raises(ValueError, match="absence_evidence"):
        C.validate(*package)


def test_paired_scaffold_requires_identical_user_context(package):
    rows = deepcopy(package[0]["rows"])
    rows[0]["request_user_context_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="scaffold_pair_user_context"):
        C.paired(rows, "harness")


def test_missing_duplicate_and_unknown_pair_axes_are_rejected(package):
    rows = package[0]["rows"]
    with pytest.raises(ValueError, match="incomplete_pair"):
        C.paired(rows[1:], "context")
    with pytest.raises(ValueError, match="duplicate_pair_side"):
        C.paired(rows + [rows[0]], "harness")
    with pytest.raises(ValueError, match="unsupported_pair_axis"):
        C.paired(rows, "model_rank")


def test_reproduction_rejects_changed_input_file(tmp_path):
    (tmp_path / "results").mkdir()
    (tmp_path / "results/context_scaffold_review_2026-10-01.json").write_text(json.dumps({"input_files": {"numeric.json": "0" * 64}}))
    (tmp_path / "numeric.json").write_text("{}")
    with pytest.raises(ValueError, match="input_hash"):
        C.reproduce(tmp_path)
