"""Prepare blind tasks and compare pinned model versions from stored receipts."""

from collections import Counter
from hashlib import sha256
from pathlib import Path

from . import comparison_analysis as analysis
from .decisioning import decision_input, validate_decision_tasks


REGISTRY_SCHEMA = "duecare-version-targets/1.0.0"
BUNDLE_SCHEMA = "duecare-version-bundle/1.0.0"
RUN_SCHEMA = "duecare-version-run/1.0.0"
TARGET_FIELDS = {"target_id", "provider", "family", "requested_name", "model_id",
                 "exact_version", "status", "documentation_url"}
RECEIPT_FIELDS = {"task_id", "status", "decision", "model_reported",
                  "request_sha256", "transport_request_sha256", "error_code"}
FAILURES = analysis.STATUSES - {"completed"}
SCORING_SCHEMA = "duecare-version-scoring/1.0.0"
SCORING_SETTINGS = {
    "binary_threshold": 0.5,
    "multilabel_threshold": 0.5,
    "threshold_operator": "greater_than_or_equal",
    "categorical_ordinal_normalization": "divide each component by its positive total mass",
    "multilabel_normalization": "independent probabilities retained directly",
    "tie_policy": "first maximum in declared choice order; ordinal order 1 through 5",
    "multilabel_correctness": "exact predicted set equals expected set",
    "bootstrap_unit": "declared scenario group; task-weighted difference",
    "bootstrap_replicates": 500,
    "bootstrap_seed": 20260930,
    "bootstrap_minimum_groups": 10,
}


def digest(value):
    return sha256(analysis.canonical(value).encode("utf-8")).hexdigest()


def scoring_signature():
    """Bind the scoring conventions to the exact released implementation files."""
    result = {"schema": SCORING_SCHEMA, "settings": dict(SCORING_SETTINGS),
              "implementation_sha256": {
                  "comparison_analysis.py": sha256(Path(analysis.__file__).read_bytes()).hexdigest(),
                  "version_benchmarks.py": sha256(Path(__file__).read_bytes()).hexdigest()}}
    result["signature_sha256"] = digest(result)
    return result


def validate_scoring_signature(value):
    fields = {"schema", "settings", "implementation_sha256", "signature_sha256"}
    if not isinstance(value, dict) or set(value) != fields or value["schema"] != SCORING_SCHEMA:
        raise ValueError("Use a supported version-scoring signature schema.")
    if value["settings"] != SCORING_SETTINGS:
        raise ValueError("The recorded scoring settings differ from this scoring protocol's conventions.")
    hashes = value["implementation_sha256"]
    if (not isinstance(hashes, dict) or set(hashes) != {"comparison_analysis.py", "version_benchmarks.py"}
            or not all(analysis.digest(item) for item in hashes.values())):
        raise ValueError("Record SHA-256 values for both scoring implementation files.")
    if value["signature_sha256"] != digest({k: v for k, v in value.items() if k != "signature_sha256"}):
        raise ValueError("The scoring signature differs from its recorded digest.")
    return value


def validate_registry(registry):
    if set(registry) != {"schema", "targets"} or registry["schema"] != REGISTRY_SCHEMA:
        raise ValueError("Use the duecare-version-targets/1.0.0 registry schema.")
    if not isinstance(registry["targets"], list):
        raise ValueError("The registry targets field must be a list.")
    seen = set()
    for target in registry["targets"]:
        if not isinstance(target, dict) or set(target) != TARGET_FIELDS:
            raise ValueError("Each target must contain the documented model identity fields.")
        for field in ("target_id", "provider", "family", "requested_name", "documentation_url"):
            if not isinstance(target[field], str) or not target[field].strip():
                raise ValueError(f"A target needs a nonempty {field}.")
        if target["target_id"] in seen:
            raise ValueError("Give each version target a unique target_id.")
        seen.add(target["target_id"])
        if target["status"] == "exact_version_required":
            if target["model_id"] is not None or target["exact_version"] is not None:
                raise ValueError("A planned target keeps model_id and exact_version null until confirmed.")
        elif target["status"] in {"pinned", "recorded_baseline"}:
            if any(not isinstance(target[k], str) or not target[k].strip()
                   for k in ("model_id", "exact_version")):
                raise ValueError("A pinned target needs model_id and exact_version.")
        else:
            raise ValueError("Use pinned, recorded_baseline or exact_version_required target status.")
    return registry


def select_target(registry, target_id):
    validate_registry(registry)
    for target in registry["targets"]:
        if target["target_id"] == target_id:
            if target["status"] == "exact_version_required":
                raise ValueError(f"{target['requested_name']} needs a confirmed model_id and exact_version before preparing a run.")
            return target
    raise ValueError(f"Add target_id {target_id} to the model registry.")


def validate_configuration(value):
    """Accept public JSON settings and reject common credential-bearing fields."""
    if not isinstance(value, dict) or not value:
        raise ValueError("Supply an explicit, nonempty public configuration object.")
    sensitive = {"api_key", "apikey", "authorization", "password", "secret", "token", "cookies", "cookie", "headers"}

    def walk(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) or k.lower() in sensitive for k in item):
                raise ValueError("Keep credential and header fields outside the public benchmark configuration.")
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(value)
    analysis.canonical(value)
    return value


def validate_groups(tasks):
    """Require explicit sampling units and consistent split assignments."""
    splits = {}
    for task in tasks:
        group = task.get("group_id")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("Every task needs an explicit nonempty source/scenario group_id for clustered comparison.")
        split = task.get("split")
        if group in splits and splits[group] != split:
            raise ValueError("Keep every task in a source/scenario group in the same split.")
        splits[group] = split


def task_set_hash(tasks):
    validate_decision_tasks(tasks)
    validate_groups(tasks)
    if not tasks:
        raise ValueError("Select at least one reference task.")
    return digest(sorted((task["task_id"], task["task_sha256"]) for task in tasks))


def prepare(tasks, target, configuration, suite="crossborder-v1"):
    """Create a local manifest and the model-visible tasks for one pinned target."""
    validate_registry({"schema": REGISTRY_SCHEMA, "targets": [target]})
    if target["status"] == "exact_version_required":
        raise ValueError("Confirm the target's exact model ID and version before preparing requests.")
    if not isinstance(suite, str) or not suite.strip():
        raise ValueError("Give the task suite a nonempty name.")
    validate_configuration(configuration)
    model_hash, config_hash = digest(target), digest(configuration)
    blind, requests = [], []
    for task in tasks:
        view = decision_input(task)
        request_hash = digest({"task": view, "model_identity_sha256": model_hash,
                               "configuration_sha256": config_hash})
        blind.append(view)
        requests.append({"task_id": task["task_id"], "task_sha256": task["task_sha256"],
                         "request_sha256": request_hash})
    manifest = {"schema": BUNDLE_SCHEMA, "suite": suite, "target": target,
                "model_identity_sha256": model_hash, "configuration": configuration,
                "configuration_sha256": config_hash, "task_set_sha256": task_set_hash(tasks),
                "requests": requests, "blind_tasks_sha256": digest(blind)}
    manifest["manifest_sha256"] = digest(manifest)
    return {"manifest": manifest, "blind_tasks": blind}


def project_tasks(tasks, suite):
    validate_groups(tasks)
    return [{"suite": suite, "task_id": task["task_id"], "task_sha256": task["task_sha256"],
             "decision_type": task["decision_type"], "expected": task["expected"],
             "choices": task.get("choices", []), "labels": task.get("labels", []),
             "family": task["family"], "group_id": task["group_id"],
             "split": task.get("split"), "facets": {}} for task in tasks]


def finish_run(tasks, target, suite, observations, provenance, manifest=None, scoring=None):
    requested = len(tasks)
    statuses = Counter(row["status"] for row in observations)
    analysis.validate(project_tasks(tasks, suite), observations, [target["target_id"]])
    scoring = scoring_signature() if scoring is None else validate_scoring_signature(scoring)
    versions = provenance.get("provider_reported_versions", {})
    result = {"schema": RUN_SCHEMA, "suite": suite, "target": target,
              "model_identity_sha256": digest(target), "task_set_sha256": task_set_hash(tasks),
              "scoring": scoring,
              "version_evidence": {
                  "registry_declared_model_id": target["model_id"],
                  "registry_declared_exact_version": target["exact_version"],
                  "observed_model_ids": dict(sorted(Counter(r["model_reported"] for r in observations if r["model_reported"]).items())),
                  "provider_reported_versions": dict(sorted(Counter(v for v in versions.values() if v is not None).items())),
                  "receipts_without_provider_version": sum(versions.get(r["task_id"]) is None for r in observations)},
              "manifest": manifest, "configuration_sha256": manifest["configuration_sha256"] if manifest else None,
              "provenance": provenance, "observations": observations,
              "coverage": {"requested": requested, "recorded": len(observations),
                           "usable": statuses["completed"], "missing": requested - len(observations),
                           "independently_validated": None, "outcomes": dict(sorted(statuses.items()))}}
    result["run_sha256"] = digest(result)
    return result


def import_receipts(tasks, manifest, receipts):
    """Validate stored receipts against the exact planned task and model envelope."""
    expected_manifest = prepare(tasks, manifest["target"], manifest["configuration"], manifest["suite"])["manifest"]
    if manifest != expected_manifest:
        raise ValueError("The manifest differs from its tasks, model identity or configuration. Use the matching bundle.")
    lookup = {task["task_id"]: task for task in project_tasks(tasks, manifest["suite"])}
    planned = {row["task_id"]: row for row in manifest["requests"]}
    observations, seen, invalid, transport_hashes, failures, observed_versions = [], set(), [], {}, [], {}
    for row in receipts:
        if (not isinstance(row, dict) or not RECEIPT_FIELDS <= set(row)
                or set(row) - RECEIPT_FIELDS - {"model_version_reported"}):
            raise ValueError("Each receipt must follow the documented typed response schema.")
        task_id = row["task_id"]
        if task_id not in lookup or task_id in seen:
            raise ValueError("Each receipt needs one unique task_id from the prepared bundle.")
        seen.add(task_id)
        if row["request_sha256"] != planned[task_id]["request_sha256"]:
            raise ValueError(f"Request hash mismatch for {task_id}.")
        reported_version = row.get("model_version_reported")
        if reported_version is not None and reported_version != manifest["target"]["exact_version"]:
            raise ValueError("The provider-reported version differs from the registry-declared exact version.")
        observed_versions[task_id] = reported_version
        transport_hash = row["transport_request_sha256"]
        if transport_hash is not None and not analysis.digest(transport_hash):
            raise ValueError("A transport request digest must be a SHA-256 value or null.")
        status, decision = row["status"], row["decision"]
        if status == "completed":
            if row["model_reported"] != manifest["target"]["model_id"] or row["error_code"] is not None:
                raise ValueError("A completed receipt must report the pinned model ID and a null error_code.")
            try:
                analysis.normalized(lookup[task_id], decision)
            except ValueError as error:
                status, decision = "invalid_decision", None
                invalid.append({"task_id": task_id, "error_code": str(error)})
        elif status not in FAILURES or decision is not None or not isinstance(row["error_code"], str) or not row["error_code"]:
            raise ValueError("A failed receipt needs a supported status, null decision and an error_code.")
        if row["status"] != "completed":
            failures.append({"task_id": task_id, "status": row["status"], "error_code": row["error_code"]})
        if row["model_reported"] is not None and not isinstance(row["model_reported"], str):
            raise ValueError("model_reported must be a string or null.")
        observations.append({"suite": manifest["suite"], "model_id": manifest["target"]["target_id"],
                             "task_id": task_id, "status": status, "decision": decision, "attempt": 1,
                             "request_sha256": row["request_sha256"], "receipt_sha256": digest(row),
                             "model_reported": row["model_reported"]})
        transport_hashes[task_id] = transport_hash
    provenance = {"mode": "prepared_receipts", "provider_completed": sum(r["status"] == "completed" for r in receipts),
                  "request_hash_basis": "canonical task, pinned model identity and public configuration",
                  "transport_request_sha256": transport_hashes, "invalid_decisions": invalid,
                  "provider_reported_versions": observed_versions,
                  "failures": failures,
                  "source_receipts_sha256": digest(receipts)}
    return finish_run(tasks, manifest["target"], manifest["suite"], observations, provenance, manifest)


def import_legacy_baseline(tasks, target, rows, suite="crossborder-v1"):
    """Import the published Jev baseline with its original provenance gaps visible."""
    validate_registry({"schema": REGISTRY_SCHEMA, "targets": [target]})
    if target["status"] != "recorded_baseline":
        raise ValueError("Legacy import requires a recorded_baseline target.")
    lookup = {task["task_id"]: task for task in project_tasks(tasks, suite)}
    observations, seen, invalid = [], set(), []
    for row in rows:
        if set(row) != {"task_id", "model", "decision"} or row["model"] != target["model_id"]:
            raise ValueError("Use the published task_id, model and decision baseline records.")
        task_id = row["task_id"]
        if task_id not in lookup or task_id in seen:
            raise ValueError("Baseline records need unique IDs from the selected reference tasks.")
        seen.add(task_id)
        status, decision = "completed", row["decision"]
        try:
            analysis.normalized(lookup[task_id], decision)
        except ValueError as error:
            status, decision = "invalid_decision", None
            invalid.append({"task_id": task_id, "error_code": str(error)})
        observations.append({"suite": suite, "model_id": target["target_id"], "task_id": task_id,
                             "status": status, "decision": decision, "attempt": 1,
                             "request_sha256": None, "receipt_sha256": digest(row), "model_reported": row["model"]})
    return finish_run(tasks, target, suite, observations,
                      {"mode": "legacy_published_baseline", "source_receipts_sha256": digest(rows),
                       "original_request_hashes": "unavailable_in_this_export",
                       "original_configuration": "unavailable_in_this_export", "invalid_decisions": invalid})


def validate_run(tasks, run):
    if run.get("schema") != RUN_SCHEMA or run.get("run_sha256") != digest({k: v for k, v in run.items() if k != "run_sha256"}):
        raise ValueError("The stored run differs from its recorded digest.")
    validate_registry({"schema": REGISTRY_SCHEMA, "targets": [run["target"]]})
    if run["target"]["status"] == "exact_version_required":
        raise ValueError("A run needs a pinned model identity.")
    if run["task_set_sha256"] != task_set_hash(tasks) or run["model_identity_sha256"] != digest(run["target"]):
        raise ValueError("Use the exact reference tasks and model identity associated with the run.")
    validate_scoring_signature(run["scoring"])
    analysis.validate(project_tasks(tasks, run["suite"]), run["observations"], [run["target"]["target_id"]])
    if any(r["status"] == "completed" and r["model_reported"] != run["target"]["model_id"] for r in run["observations"]):
        raise ValueError("Completed observations must retain the declared served model ID.")
    manifest = run["manifest"]
    if manifest:
        expected = prepare(tasks, run["target"], manifest["configuration"], run["suite"])["manifest"]
        if manifest != expected or run["configuration_sha256"] != expected["configuration_sha256"]:
            raise ValueError("The run's configuration differs from its prepared manifest.")
        requests = {r["task_id"]: r["request_sha256"] for r in manifest["requests"]}
        if any(r["request_sha256"] != requests[r["task_id"]] for r in run["observations"]):
            raise ValueError("The run includes an observation from a different prepared request.")
    elif run["configuration_sha256"] is not None or run["provenance"].get("mode") != "legacy_published_baseline":
        raise ValueError("A prepared run needs its manifest; a legacy import records its provenance gaps explicitly.")
    reported_versions = run["provenance"].get("provider_reported_versions", {})
    if (not isinstance(reported_versions, dict)
            or not set(reported_versions) <= {r["task_id"] for r in run["observations"]}
            or any(v is not None and v != run["target"]["exact_version"] for v in reported_versions.values())):
        raise ValueError("Provider-reported version evidence must match the declared version and observed task IDs.")
    expected = finish_run(tasks, run["target"], run["suite"], run["observations"], run["provenance"], manifest, run["scoring"])
    if run != expected:
        raise ValueError("The run's coverage or schema differs from its recorded observations.")
    return run


def compare_versions(tasks, baseline, candidate):
    """Compare candidate and baseline on shared usable tasks with grouped uncertainty."""
    validate_run(tasks, baseline)
    validate_run(tasks, candidate)
    if baseline["suite"] != candidate["suite"] or baseline["target"]["target_id"] == candidate["target"]["target_id"]:
        raise ValueError("Use the same suite and distinct target IDs for the two model configurations.")
    target_ids = [candidate["target"]["target_id"], baseline["target"]["target_id"]]
    summary = analysis.decision_summary(project_tasks(tasks, baseline["suite"]),
                                        candidate["observations"] + baseline["observations"], target_ids)
    return {"schema": "duecare-version-comparison/1.0.0", "task_set_sha256": task_set_hash(tasks),
            "candidate": candidate["target"], "baseline": baseline["target"],
            "candidate_run_sha256": candidate["run_sha256"], "baseline_run_sha256": baseline["run_sha256"],
            "version_evidence": {"candidate": candidate["version_evidence"], "baseline": baseline["version_evidence"]},
            "scoring": {"candidate_recorded": candidate["scoring"], "baseline_recorded": baseline["scoring"],
                        "recorded_signatures_match": candidate["scoring"] == baseline["scoring"],
                        "current": scoring_signature(),
                        "comparison_policy": "Both stored decision sets are rescored with the current released implementation."},
            "configuration_match": (candidate["configuration_sha256"] == baseline["configuration_sha256"]
                                    if all(r["configuration_sha256"] for r in (candidate, baseline)) else None),
            "suites": summary,
            "interpretation": "Paired differences apply to shared usable tasks and the recorded model configurations. "
                              "Coverage uses the full requested population. Intervals resample declared scenario groups; "
                              "at least ten matched groups are required. Independent domain validation remains a separate study."}
