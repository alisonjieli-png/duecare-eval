from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import matched_context as M

ROOT = Path(__file__).resolve().parents[1]


def small_questions():
    return {"risk": {"type": "noul"}, "action": {"type": "choice", "criteria": {"a": None, "b": None}}}


def small_response(probability=.8):
    return json.dumps({"answers": {"risk": {"type": "noul", "noul": probability},
        "action": {"type": "choice", "choice": "b", "probabilities": {"a": .5, "b": .5}}}})


def test_earliest_valid_fence_is_selected_independently_of_probability():
    attempts = [{"attempt": i, "status": "malformed_json", "transport_status": "completed",
                 "response": "```json\n" + small_response(p) + "\n```"} for i, p in ((1, .1), (2, .9))]
    selected, method, values, invalid = M.select_attempt(attempts, small_questions())
    assert selected["attempt"] == 1 and method == M.FENCE_METHOD
    assert values["risk"]["probability"] == .1 and not invalid
    assert values["action"]["selected"] == "b"
    assert values["action"]["maxima"] == ["a", "b"]


def test_strict_completion_takes_precedence_over_earlier_fence():
    attempts = [{"attempt": 1, "status": "malformed_json", "transport_status": "completed", "response": "```\n" + small_response(.1) + "\n```"},
                {"attempt": 2, "status": "completed", "transport_status": "completed", "response": small_response(.9)}]
    selected, method, values, _ = M.select_attempt(attempts, small_questions())
    assert selected["attempt"] == 2 and method == "strict_plain_json"
    assert values["risk"]["probability"] == .9


@pytest.mark.parametrize("text", [small_response()[:-1], "Explanation\n```json\n" + small_response() + "\n```",
    "```json\n" + small_response() + "\n```\nExtra", "```json\n" + small_response()[:-1] + "\n```"])
def test_missing_syntax_and_partial_wrappers_remain_unavailable(text):
    candidate = {"attempt": 1, "status": "malformed_json", "transport_status": "completed", "response": text}
    _, method, values, _ = M.select_attempt([candidate], small_questions())
    assert method == "unavailable" and values == {}


def test_truncated_or_wrong_identity_transport_is_not_recovered():
    candidate = {"attempt": 1, "status": "truncated", "transport_status": "truncated",
                 "response": "```json\n" + small_response() + "\n```"}
    assert M.select_attempt([candidate], small_questions())[1] == "unavailable"
    candidate.update(status="identity_mismatch", transport_status="identity_mismatch")
    assert M.select_attempt([candidate], small_questions())[1] == "unavailable"


def test_probability_mass_is_retained_and_invalid_values_are_never_normalized():
    body = json.loads(small_response())
    body["answers"]["action"]["probabilities"]["a"] = .49
    valid, invalid = M.validate_raw(body["answers"], small_questions())
    assert "action" not in valid and invalid == {"action": "choice_probability_mass"}
    assert body["answers"]["action"]["probabilities"] == {"a": .49, "b": .5}


@pytest.fixture
def package():
    def read(name):
        return json.loads((ROOT / "results" / name).read_text())
    cases = read("longform_cases_2026-09-30.json")
    questions = read("longform_jev_questions_2026-09-30.json")
    evidence = read("longform_primary_sources_2026-09-30.json")
    targets = {name: {"model": name, "provider": "jev" if name == "jev" else "ollama"}
               for name in ["jev"] + [f"target-{i}" for i in range(11)]}
    records = []
    for target in targets:
        for case in cases:
            if case["stratum"] != "original_advice":
                continue
            for arm in ("bare", "grounded"):
                raw = {}
                for name, q in questions.items():
                    raw[name] = ({"type": "noul", "noul": .8} if q["type"] == "noul" else
                        {"type": "choice", "choice": next(iter(q["criteria"])), "probabilities": {k: 1 / len(q["criteria"]) for k in q["criteria"]}})
                values, invalid = M.validate_raw(raw, questions)
                semantic = M.sha(M.context(case, arm, questions, evidence))
                records.append({"target_id": target, "model_requested": target, "model_reported": target,
                    "context_id": "MFC-" + semantic[:26], "case_id": case["case_id"], "arm": arm,
                    "prompt_sha256": case["prompt_sha256"], "semantic_payload_sha256": semantic,
                    "strict_status": "completed", "analysis_status": "completed",
                    "selection_method": "archived_native_actual_choice/1.0.0" if target == "jev" else "strict_plain_json",
                    "selected_attempt": 1, "answers": values, "invalid_answers": invalid,
                    "attempts": [{"attempt": 1, "status": "completed", "transport_status": "completed", "recorded_at": "2026-09-30T23:00:00Z",
                        "receipt_sha256": "1" * 64, "request_sha256": "2" * 64, "response_sha256": "3" * 64}],
                    "reused_archived_jev": target == "jev", "legacy_tie_resolution_differences": {}})
    manifest = {"targets": targets, "snapshot_at": "2026-09-30T23:00:00Z", "new_physical_calls": 88}
    return records, manifest, cases, questions, evidence


def test_all_requested_panels_and_matched_fields_have_distinct_denominators(package):
    result = M.summarize(*package)
    assert result["requested_panels"] == 96
    assert result["new_panels_requested"] == 88 and result["archived_jev_panels"] == 8
    assert result["models"]["target-0"]["typed_fields_available"] == 96
    assert len(result["all_model_intersection"]["bare"]["complete_panel_case_ids"]) == 4
    records, manifest, cases, questions, evidence = package
    row = next(r for r in records if r["target_id"] == "target-0" and r["arm"] == "bare")
    row.update(strict_status="invalid_response", analysis_status="partial", selection_method="strict_fieldwise")
    row["attempts"][0]["status"] = "invalid_response"
    del row["answers"]["financial_pressure"]
    row["invalid_answers"] = {"financial_pressure": "invalid_binary_probability"}
    result = M.summarize(*package)
    assert result["models"]["target-0"]["requested_panels"] == 8
    assert result["models"]["target-0"]["typed_fields_available"] == 95
    assert result["models"]["target-0"]["probes"]["bare"]["financial_pressure"]["available_cases"] == 3
    assert result["paired_jev_probability_differences"]["target-0"]["matched_binary_fields"] == 79
    assert len(result["all_model_intersection"]["bare"]["complete_panel_case_ids"]) == 3


def test_extra_text_unknown_ids_and_context_drift_fail(package):
    altered = deepcopy(package); altered[0][0]["raw_prose"] = "private"
    with pytest.raises(ValueError, match="allowlist"):
        M.validate(*altered)
    altered = deepcopy(package); altered[0][0]["case_id"] = "unknown"
    with pytest.raises(ValueError, match="unknown_or_duplicate"):
        M.validate(*altered)
    altered = deepcopy(package); altered[0][0]["semantic_payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="shared_context"):
        M.validate(*altered)


@pytest.mark.parametrize("value", [True, None, float("nan"), 1.1])
def test_public_numeric_projection_rejects_invalid_probabilities(package, value):
    package[0][0]["answers"]["financial_pressure"]["probability"] = value
    with pytest.raises(ValueError, match="exported_probability"):
        M.validate(*package)


def test_public_selection_cannot_silently_relabel_a_strict_failure(package):
    row = package[0][0]
    row["strict_status"] = "malformed_json"
    with pytest.raises(ValueError, match="strict_latest"):
        M.validate(*package)


def test_reproduction_rejects_a_changed_hashed_file(tmp_path):
    folder = tmp_path / "results"
    folder.mkdir()
    (folder / "matched_context_2026-09-30.manifest.json").write_text(json.dumps({"files": {"numeric.jsonl": "0" * 64}}))
    (tmp_path / "numeric.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="file_hash_mismatch"):
        M.reproduce(tmp_path)


def test_captured_bridge_reproduces_full_requested_and_extraction_counts():
    result = M.reproduce(ROOT)
    assert result == json.loads((ROOT / "results/matched_context_2026-09-30.findings.json").read_text())
    assert result["requested_panels"] == 96
    assert result["new_physical_calls"] == 136
    assert sum(m["analysis_complete_panels"] for m in result["models"].values()) == 67
    assert sum(m["fence_extracted_panels"] for m in result["models"].values()) == 22
    assert sum(m["typed_fields_available"] for m in result["models"].values()) == 837
    assert result["models"]["gpt-oss-20b"]["analysis_complete_panels"] == 0
    assert result["models"]["gpt-oss-20b"]["requested_panels"] == 8
    assert all(not r["complete_panel_case_ids"] for r in result["all_model_intersection"].values())
