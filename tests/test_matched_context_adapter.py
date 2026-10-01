from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import matched_context_adapter as A

ROOT = Path(__file__).resolve().parents[1]


def package():
    def read(name):
        return json.loads((ROOT / "results" / name).read_text())
    def rows(name):
        return [json.loads(line) for line in (ROOT / "results" / name).read_text().splitlines()]
    return (rows("matched_context_adapter_2026-10-01.jsonl"), read("matched_context_adapter_2026-10-01.manifest.json"),
            rows("matched_context_2026-09-30.jsonl"), read("longform_cases_2026-09-30.json"),
            read("longform_jev_questions_2026-09-30.json"), read("longform_primary_sources_2026-09-30.json"))


def test_frozen_conditions_reproduce_without_merging_baseline():
    result = A.reproduce(ROOT)
    assert result == json.loads((ROOT / "results/matched_context_adapter_2026-10-01.findings.json").read_text())
    assert result["requested"] == 24 and result["physical_calls"] == 22
    assert result["conditions"]["gpt-oss-20b"]["followup"]["strict_outcomes"] == {"malformed_json": 1, "unattempted": 7}
    assert result["conditions"]["glm-5-3"]["followup"]["analysis_complete"] == 6
    assert result["conditions"]["glm-5-3-flash"]["followup"]["analysis_complete"] == 7
    assert all(c["baseline"]["analysis_complete"] == 0 for c in result["conditions"].values())
    assert all(c["same_model_matched_numeric_fields"] == [] for c in result["conditions"].values())


def test_exact_deployment_payload_is_reconstructed_from_public_sources():
    values = package()
    values[1]["formatting_instruction"] += " Changed instruction."
    with pytest.raises(ValueError, match="baseline_payload_reconstruction"):
        A.summarize(*values)


def test_followup_condition_and_request_hash_drift_are_rejected():
    values = package(); values[0][0]["condition_id"] = "changed_questions"
    with pytest.raises(ValueError, match="condition_or_context"):
        A.summarize(*values)
    values = package(); values[0][0]["prepared_request_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="intervention_payload"):
        A.summarize(*values)


def test_raw_prose_remains_outside_numeric_projection():
    values = package(); values[0][0]["response"] = "private response"
    with pytest.raises(ValueError, match="allowlist"):
        A.summarize(*values)
