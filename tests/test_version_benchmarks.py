"""Offline tests for version identity, provenance and matched comparisons."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import version_benchmarks as versions
from duecare_eval.contracts import canonical, sha

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def registry():
    return json.loads((ROOT / "examples/version_targets.json").read_text())


@pytest.fixture
def tasks():
    source = json.loads((ROOT / "examples/crossborder_references.jsonl").read_text().splitlines()[0])
    result = []
    for index in range(12):
        task = deepcopy(source)
        task.update(task_id=f"version-test-{index}", group_id=f"group-{index}",
                    leakage_group_id=f"group-{index}", expected=False)
        task["task_sha256"] = sha([canonical({k: v for k, v in task.items() if k != "task_sha256"})])
        result.append(task)
    return result


@pytest.fixture
def target(registry):
    target = deepcopy(registry["targets"][0])
    target.update(target_id="test-version", model_id="test-model-v2", exact_version="v2", status="pinned")
    return target


def receipts(bundle, probability=.1):
    return [{"task_id": row["task_id"], "status": "completed", "decision": {"probability": probability},
             "model_reported": bundle["manifest"]["target"]["model_id"],
             "request_sha256": row["request_sha256"], "transport_request_sha256": None, "error_code": None}
            for row in bundle["manifest"]["requests"]]


def test_planned_targets_require_exact_versions(registry):
    versions.validate_registry(registry)
    assert registry["targets"][2]["requested_name"] == "Gemini4"
    assert registry["targets"][2]["family"] == "Gemini"
    for target_id in ("jev-next-version", "gemini4-planned"):
        with pytest.raises(ValueError, match="confirmed model_id and exact_version"):
            versions.select_target(registry, target_id)


def test_registry_rejects_duplicate_ids_and_partial_pinning(registry):
    registry["targets"].append(deepcopy(registry["targets"][0]))
    with pytest.raises(ValueError, match="unique"):
        versions.validate_registry(registry)
    registry["targets"].pop()
    registry["targets"][2]["model_id"] = "unconfirmed"
    with pytest.raises(ValueError, match="null"):
        versions.validate_registry(registry)


def test_bundle_is_blind_and_hashes_configuration(tasks, target):
    first = versions.prepare(tasks, target, {"temperature": 0})
    second = versions.prepare(tasks, target, {"temperature": .1})
    for row in first["blind_tasks"]:
        assert not {"expected", "metadata", "split", "group_id", "task_sha256", "label_basis"} & set(row)
    assert first["manifest"]["task_set_sha256"] == second["manifest"]["task_set_sha256"]
    assert first["manifest"]["requests"][0]["request_sha256"] != second["manifest"]["requests"][0]["request_sha256"]


def test_configuration_rejects_credentials(tasks, target):
    with pytest.raises(ValueError, match="credential"):
        versions.prepare(tasks, target, {"transport": {"api_key": "example-secret"}})


def test_import_preserves_missing_failed_and_invalid_counts(tasks, target):
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    rows = receipts(bundle)[:3]
    rows[1].update(status="timeout", decision=None, model_reported=None, error_code="request_timeout")
    rows[2]["decision"] = {"probability": 2}
    result = versions.import_receipts(tasks, bundle["manifest"], rows)
    assert result["coverage"] == {"requested": 12, "recorded": 3, "usable": 1, "missing": 9,
                                  "independently_validated": None,
                                  "outcomes": {"completed": 1, "invalid_decision": 1, "timeout": 1}}
    assert result["provenance"]["provider_completed"] == 2
    assert result["provenance"]["failures"][0]["error_code"] == "request_timeout"
    assert result["observations"][2]["decision"] is None
    assert versions.validate_run(tasks, result) == result


@pytest.mark.parametrize("change", ["request", "model", "duplicate", "unknown"])
def test_import_rejects_mismatched_receipts(tasks, target, change):
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    rows = receipts(bundle)
    if change == "request":
        rows[0]["request_sha256"] = "0" * 64
    elif change == "model":
        rows[0]["model_reported"] = "another-version"
    elif change == "duplicate":
        rows.append(deepcopy(rows[0]))
    else:
        rows[0]["task_id"] = "outside-the-bundle"
    with pytest.raises(ValueError):
        versions.import_receipts(tasks, bundle["manifest"], rows)


def test_legacy_baseline_keeps_unavailable_provenance_explicit(tasks, registry):
    target = registry["targets"][0]
    rows = [{"task_id": task["task_id"], "model": target["model_id"], "decision": {"probability": .1}}
            for task in tasks]
    result = versions.import_legacy_baseline(tasks, target, rows)
    assert result["configuration_sha256"] is None and result["manifest"] is None
    assert all(row["request_sha256"] is None for row in result["observations"])
    assert result["coverage"]["usable"] == 12


def test_paired_comparison_reports_shared_ids_and_group_uncertainty(tasks, target, registry):
    baseline_target = registry["targets"][0]
    baseline = versions.import_legacy_baseline(tasks, baseline_target,
        [{"task_id": task["task_id"], "model": baseline_target["model_id"], "decision": {"probability": .9}}
         for task in tasks])
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    candidate = versions.import_receipts(tasks, bundle["manifest"], receipts(bundle)[:-1])
    report = versions.compare_versions(tasks, baseline, candidate)
    pair = report["suites"]["crossborder-v1"]["pairwise"][0]
    assert pair["matched_tasks"] == pair["scenario_groups"] == 11
    assert pair["accuracy_difference_left_minus_right"] == 1
    assert pair["cluster_bootstrap_95_interval"] == [1, 1]
    assert report["configuration_match"] is None
    assert report["suites"]["crossborder-v1"]["models"]["test-version"]["requested"] == 12


def test_comparison_rejects_changed_reference_and_tampered_receipt(tasks, target):
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    run = versions.import_receipts(tasks, bundle["manifest"], receipts(bundle))
    changed = deepcopy(tasks)
    changed[0]["expected"] = True
    changed[0]["task_sha256"] = sha([canonical({k: v for k, v in changed[0].items() if k != "task_sha256"})])
    with pytest.raises(ValueError, match="exact reference"):
        versions.validate_run(changed, run)
    run["observations"][0]["decision"]["probability"] = .99
    with pytest.raises(ValueError, match="digest"):
        versions.validate_run(tasks, run)


def resign(value, field):
    value[field] = versions.digest({k: v for k, v in value.items() if k != field})


@pytest.mark.parametrize("change, message", [("signature", "signature differs"),
                                            ("settings", "settings differ"),
                                            ("schema", "signature schema")])
def test_run_validation_checks_scoring_signature(tasks, target, change, message):
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    run = versions.import_receipts(tasks, bundle["manifest"], receipts(bundle))
    if change == "signature":
        run["scoring"]["implementation_sha256"]["comparison_analysis.py"] = "0" * 64
    elif change == "settings":
        run["scoring"]["settings"]["binary_threshold"] = .7
        resign(run["scoring"], "signature_sha256")
    else:
        run["scoring"]["schema"] = "unrecognized-scoring-version"
        resign(run["scoring"], "signature_sha256")
    resign(run, "run_sha256")
    with pytest.raises(ValueError, match=message):
        versions.validate_run(tasks, run)


def test_comparison_exposes_changed_implementation_and_rescores(tasks, target, registry):
    baseline_target = registry["targets"][0]
    baseline = versions.import_legacy_baseline(tasks, baseline_target,
        [{"task_id": task["task_id"], "model": baseline_target["model_id"], "decision": {"probability": .9}}
         for task in tasks])
    baseline["scoring"]["implementation_sha256"]["comparison_analysis.py"] = "0" * 64
    resign(baseline["scoring"], "signature_sha256")
    resign(baseline, "run_sha256")
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    candidate = versions.import_receipts(tasks, bundle["manifest"], receipts(bundle))
    report = versions.compare_versions(tasks, baseline, candidate)
    assert report["scoring"]["recorded_signatures_match"] is False
    assert report["scoring"]["current"] == versions.scoring_signature()
    assert report["suites"]["crossborder-v1"]["pairwise"][0]["accuracy_difference_left_minus_right"] == 1


def test_provider_version_is_separate_observed_evidence(tasks, target):
    bundle = versions.prepare(tasks, target, {"temperature": 0})
    rows = receipts(bundle)
    for row in rows[:5]:
        row["model_version_reported"] = target["exact_version"]
    result = versions.import_receipts(tasks, bundle["manifest"], rows)
    evidence = result["version_evidence"]
    assert evidence["registry_declared_exact_version"] == "v2"
    assert evidence["provider_reported_versions"] == {"v2": 5}
    assert evidence["receipts_without_provider_version"] == 7
    rows[0]["model_version_reported"] = "v3"
    with pytest.raises(ValueError, match="provider-reported version"):
        versions.import_receipts(tasks, bundle["manifest"], rows)


@pytest.mark.parametrize("group", [None, "", "   "])
def test_version_tasks_require_explicit_sampling_groups(tasks, target, registry, group):
    tasks[0]["group_id"] = group
    tasks[0]["task_sha256"] = sha([canonical({k: v for k, v in tasks[0].items() if k != "task_sha256"})])
    with pytest.raises(ValueError, match="explicit nonempty"):
        versions.prepare(tasks, target, {"temperature": 0})
    with pytest.raises(ValueError, match="explicit nonempty"):
        versions.import_legacy_baseline(tasks, registry["targets"][0], [])


def test_version_groups_keep_one_split_even_with_different_leakage_ids(tasks, target):
    tasks[1]["group_id"] = tasks[0]["group_id"]
    tasks[1]["split"] = "held_out"
    tasks[1]["task_sha256"] = sha([canonical({k: v for k, v in tasks[1].items() if k != "task_sha256"})])
    with pytest.raises(ValueError, match="same split"):
        versions.prepare(tasks, target, {"temperature": 0})
