"""Offline reconstruction and corruption checks for the dated model extension."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket

import pytest

from duecare_eval import model_expansion as M

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "results/model_expansion_2026-10-01.json",
    "results/model_inventory_2026-10-01.json",
    "examples/reference_bank_v1/cases.json",
    "examples/reference_bank_v1/evidence_review.json",
)


@pytest.fixture
def records():
    return [json.loads((ROOT / name).read_text()) for name in FILES]


def test_counts_reproduce_from_public_records(records):
    result = M.analyze(*records)
    assert result["coverage"]["requested_answer_slots"] == 60
    assert result["coverage"]["complete_identity_matched_answers"] == 46
    assert result["coverage"]["truncated_answer_slots"] == 14
    assert result["coverage"]["behavior_assessed_answers"] == 0
    assert result["reconstructed_payloads"] == {"original_answers": 60, "access_canaries": 6, "changed_control_canaries": 2}
    assert result["physical_calls"] == {"original_study_including_access_checks": 82, "separate_low_control": 2, "native_total": 84, "unknown_native_outcomes": 0}
    assert result["attempts"]["retry_attempts"] == 16
    assert result["inventory"]["catalog_routes"] == 62
    assert result["inventory"]["cli_invocations"] == 2
    assert result["inventory"]["cli_provider_calls"] is None


def test_portable_public_only_copy_and_no_network(tmp_path, monkeypatch):
    for name in FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline reproduction attempted network access")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert M.reproduce(tmp_path)["coverage"]["complete_identity_matched_answers"] == 46


@pytest.mark.parametrize("mutation", [
    lambda s: s["observations"].pop(),
    lambda s: s["observations"].__setitem__(-1, deepcopy(s["observations"][0])),
    lambda s: s["observations"][0].update(request_id="MEX-" + "0" * 26),
    lambda s: s["observations"][0].update(request_sha256="0" * 64),
    lambda s: s["observations"][0].update(prompt_sha256="0" * 64),
    lambda s: s["observations"][0].update(response_sha256="0" * 64),
    lambda s: s["observations"][0].update(model_reported="some-other-model"),
    lambda s: s["observations"][0].update(status="completed"),
    lambda s: s["observations"][0].update(attempt=3),
    lambda s: s["observations"][0].update(recorded_response_characters=0),
    lambda s: s["observations"][0].update(elapsed_seconds=float("nan")),
    lambda s: s["observations"][0].update(response="raw private content"),
    lambda s: s["observations"][0].update(behavior_assessment_status="assessed"),
    lambda s: s["coverage"].update(complete_identity_matched_answers=48),
    lambda s: s["coverage"].update(behavior_assessed_answers=False),
    lambda s: s["coverage_by_model"]["glm-5-3"].update(requested_answer_slots=9),
    lambda s: s["prior_attempt_history"].append(deepcopy(s["prior_attempt_history"][0])),
    lambda s: s["prior_attempt_history"][0].update(request_id="unknown-slot"),
    lambda s: s["prior_attempt_history"].pop(0),
    lambda s: s["canaries"].pop(),
    lambda s: s["canaries"][0].update(request_sha256="a" * 64),
    lambda s: s["separate_glm_low_control_canary"]["observations"][0]["changed_fields"]["think"].update(after="max"),
    lambda s: s["separate_glm_low_control_canary"]["observations"][0].update(model_reported="glm-5.3-flash"),
    lambda s: s["separate_glm_low_control_canary"]["observations"][0].update(baseline_response_sha256="b" * 64),
    lambda s: s["separate_glm_low_control_canary"].update(requested_slots=1),
    lambda s: s["source_provenance"]["request_prefix"].update(unread_tail_bytes=1),
    lambda s: s["execution_receipt"].update(physical_calls_reserved=83),
    lambda s: s["glm_serving_condition_review"].update(effective_provider_reasoning_level="max"),
], ids=["missing-slot", "duplicate-cell", "slot-id", "payload-digest", "prompt-digest", "response-link", "served-identity", "status-finish", "attempt-cap", "empty-text", "nan-time", "raw-output-field", "later-review-backfill", "coverage-overlay", "bool-count", "model-denominator", "duplicate-attempt", "unplanned-attempt", "lost-history", "missing-canary", "canary-payload", "changed-effort", "low-served-model", "low-baseline-link", "low-denominator", "torn-prefix", "physical-call-count", "inferred-effective-effort"])
def test_snapshot_corruption_is_rejected(records, mutation):
    mutation(records[0])
    with pytest.raises(ValueError):
        M.analyze(*records)


@pytest.mark.parametrize("mutation", [
    lambda i: i.update(catalog_routes=63),
    lambda i: i["models"].append(deepcopy(i["models"][0])),
    lambda i: i["models"][0].update(native_hosted_canary_status="completed_exact_model_tag"),
    lambda i: i["opencode_deployment_canary"].update(cli_invocations=2),
    lambda i: i["opencode_deployment_diagnostic_v2"].update(provider_call_count_verified=True),
    lambda i: i["opencode_deployment_diagnostic_v2"].update(served_model_id="qwen3.8-flash"),
    lambda i: i["opencode_deployment_diagnostic_v2"].update(status="completed"),
    lambda i: i["opencode_deployment_diagnostic_v2"]["safe_errors"][0].update(error_name="QuotaError"),
    lambda i: i["hosted_control_audit"]["models"]["glm-5.3"].update(requested_value_advertised=True),
], ids=["catalog-total", "duplicate-route", "catalog-as-access", "cli-invocations", "invented-provider-count", "invented-served-identity", "cli-as-completion", "invented-cause", "unsupported-control"])
def test_inventory_and_cli_uncertainty_are_checked(records, mutation):
    mutation(records[1])
    with pytest.raises(ValueError):
        M.analyze(*records)


def test_original_source_string_change_is_rejected(records):
    records[2][0]["task"] += " "
    with pytest.raises(ValueError, match="prompt bytes"):
        M.analyze(*records)


def test_grounding_evidence_change_breaks_actual_payload_digest(records):
    records[3]["sources"][0]["summary"] += " Changed."
    with pytest.raises(ValueError, match="request digest"):
        M.analyze(*records)


def test_full_cartesian_design_and_separate_low_condition(records):
    result = M.analyze(*records)
    assert all(v["requested_answer_slots"] == 10 for v in result["coverage_by_model"].values())
    assert result["low_control"]["complete"] == 2
    assert result["coverage"]["complete_identity_matched_answers"] == 46


def test_boolean_usage_and_incorrect_totals_are_rejected(records):
    records[0]["observations"][0]["usage"]["input_tokens"] = True
    with pytest.raises(ValueError, match="usage counts"):
        M.analyze(*records)


def test_shared_ready_response_hashes_are_valid(records):
    canaries = records[0]["canaries"]
    assert len({r["response_sha256"] for r in canaries}) < len(canaries)
    assert M.analyze(*records)["inventory"]["native_models_with_completed_canaries"] == 6
