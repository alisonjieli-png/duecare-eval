"""Validate a numeric recovery supplement and reproduce its coverage overlay."""
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re

from . import comparison_analysis as C

SCHEMA = "duecare-jev-recovery-export/1.0.0"
COUNTS = {"core": 12000, "attacks": 7200, "judge": 2790, "referral": 16800}
TOP = {"schema", "snapshot_at", "original_comparison_snapshot_at", "model", "provenance", "original", "observations", "findings"}
ROW = {"lane", "task_id", "model", "status", "decision", "request_sha256", "original_attempts",
       "supplement_attempt", "recorded_at", "original_receipt_sha256", "supplement_receipt_sha256"}
PROVENANCE = {"supplement_manifest_sha256", "supplement_responses_sha256", "supplement_summary_sha256",
              "comparison_snapshot_sha256", "comparison_tasks_sha256", "comparison_observations_sha256"}


def valid_time(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def validate_decision(lane, decision):
    if not isinstance(decision, dict):
        raise ValueError("A completed recovery needs a numeric decision.")
    if set(decision) == {"probability"}:
        valid = C.probability(decision["probability"])
    elif set(decision) == {"probabilities"}:
        probs = decision["probabilities"]
        valid = (isinstance(probs, dict) and bool(probs) and
                 all(isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9_]+", k) and C.probability(v)
                     for k, v in probs.items()) and sum(probs.values()) > 0)
    elif lane == "judge" and set(decision) == {"winner", "confidence"}:
        valid = decision["winner"] in {"A", "B", "tie"} and C.probability(decision["confidence"])
    elif lane == "judge" and set(decision) == {"grade", "critical_failure", "abstain", "insufficient_evidence_probability"}:
        valid = (type(decision["grade"]) is int and 1 <= decision["grade"] <= 5 and
                 type(decision["critical_failure"]) is bool and type(decision["abstain"]) is bool and
                 C.probability(decision["insufficient_evidence_probability"]))
    else:
        valid = False
    if not valid:
        raise ValueError("The recovery decision must use the numeric allowlist.")


def validate(data):
    if set(data) != TOP or data["schema"] != SCHEMA or data["model"] != "jev-1.13.0":
        raise ValueError("Select the supported recovery export schema and model.")
    if not valid_time(data["snapshot_at"]) or not valid_time(data["original_comparison_snapshot_at"]):
        raise ValueError("Recovery snapshots need dated timestamps with timezones.")
    if set(data["provenance"]) != PROVENANCE or not all(C.digest(x) for x in data["provenance"].values()):
        raise ValueError("Every provenance field must be a SHA-256 digest.")
    if set(data["original"]) != set(COUNTS):
        raise ValueError("The export must retain all four original populations.")
    lookup = {}
    for lane, original in data["original"].items():
        required = {"requested", "ids_by_status", "responses_sha256", "calls_sha256"}
        if set(original) != required or original["requested"] != COUNTS[lane]:
            raise ValueError("The original requested denominator changed.")
        if not C.digest(original["responses_sha256"]) or not C.digest(original["calls_sha256"]):
            raise ValueError("Original journals need source digests.")
        status_map = {}
        if set(original["ids_by_status"]) - {"completed", "provider_error", "unavailable"}:
            raise ValueError("Unexpected original status in the terminal population.")
        for status, ids in original["ids_by_status"].items():
            if not isinstance(ids, list):
                raise ValueError("Original ID inventories must be arrays.")
            for item in ids:
                if not isinstance(item, str) or not re.fullmatch(r"(?:DEC2|ATK2|JCH|REFQ)-[a-f0-9]+", item) or item in status_map:
                    raise ValueError("Original IDs must be distinct, valid task identifiers.")
                status_map[item] = status
        if len(status_map) != original["requested"]:
            raise ValueError("Every original requested ID must stay in the inventory.")
        lookup[lane] = status_map
    seen = set()
    for row in data["observations"]:
        if set(row) != ROW or row["lane"] not in lookup or row["model"] != data["model"]:
            raise ValueError("Recovery rows must use the public field allowlist.")
        key = row["lane"], row["task_id"]
        if key in seen or row["task_id"] not in lookup[row["lane"]]:
            raise ValueError("Recovery IDs must be distinct members of the original population.")
        if lookup[row["lane"]][row["task_id"]] == "completed":
            raise ValueError("Recovery can supplement only an originally unsuccessful ID.")
        if row["status"] not in {"completed", "provider_error", "unavailable"}:
            raise ValueError("Unexpected supplemental status.")
        if row["original_attempts"] != 2 or row["supplement_attempt"] != 1 or not valid_time(row["recorded_at"]):
            raise ValueError("Recovery attempt accounting or timestamp changed.")
        for field in ("request_sha256", "original_receipt_sha256", "supplement_receipt_sha256"):
            if not C.digest(row[field]):
                raise ValueError("Recovery observations need valid payload and receipt digests.")
        if row["status"] == "completed":
            validate_decision(row["lane"], row["decision"])
        elif row["decision"] is not None:
            raise ValueError("An unsuccessful recovery retains an empty decision field.")
        seen.add(key)
    if len(seen) != 17:
        raise ValueError("This supplement contains exactly 17 selected original IDs.")
    return lookup


def analyze(data, tasks, original_observations):
    baseline = validate(data)
    result = {"snapshot_at": data["snapshot_at"], "original_comparison_snapshot_at": data["original_comparison_snapshot_at"],
              "supplement": {"requested": len(data["observations"]),
                             "statuses": dict(sorted(Counter(r["status"] for r in data["observations"]).items()))},
              "coverage": {}, "typed_metrics": {}, "recovered_item_scores": []}
    for lane, statuses in baseline.items():
        recovered = {r["task_id"] for r in data["observations"] if r["lane"] == lane and r["status"] == "completed"}
        completed = {item for item, status in statuses.items() if status == "completed"}
        overlay = completed | recovered
        result["coverage"][lane] = {"requested": len(statuses), "original_completed": len(completed),
            "original_unsuccessful": len(statuses) - len(completed), "recovered_distinct_ids": len(recovered),
            "overlay_completed": len(overlay), "overlay_unresolved": len(statuses) - len(overlay),
            "overlay_coverage": len(overlay) / len(statuses)}
    for lane in ("core", "attacks"):
        population = {task["task_id"]: task for task in tasks if task["suite"] == lane}
        if set(population) != set(baseline[lane]):
            raise ValueError("Released task IDs differ from the recovery population.")
        records = [row for row in original_observations if row["suite"] == lane and row["model_id"] == "jev"]
        if len(records) != len({row["task_id"] for row in records}) or {row["task_id"] for row in records} != set(population):
            raise ValueError("Original Jev observations must cover each requested ID exactly once.")
        if any(row["status"] != baseline[lane][row["task_id"]] for row in records):
            raise ValueError("Original projected status differs from the terminal inventory.")
        scored = {row["task_id"]: C.score(population[row["task_id"]], row["decision"])
                  for row in records if row["status"] == "completed"}
        original_metrics = C.metrics(list(scored.values()), len(population))
        for row in data["observations"]:
            if row["lane"] == lane and row["status"] == "completed":
                item_score = C.score(population[row["task_id"]], row["decision"])
                scored[row["task_id"]] = item_score
                result["recovered_item_scores"].append({"lane": lane, "task_id": row["task_id"],
                    "correct": item_score["correct"], "decision_type": item_score["decision_type"],
                    "expected_grade_mae": item_score.get("expected_grade_mae"),
                    "ranked_probability_score": item_score.get("ranked_probability_score")})
        result["typed_metrics"][lane] = {"original": original_metrics,
                                          "overlay": C.metrics(list(scored.values()), len(population))}
    return result


def reproduce(root):
    root = Path(root)
    data = json.loads((root / "results/jev_recovery_2026-09-30.json").read_text())
    files = {"comparison_snapshot_sha256": "snapshot.json", "comparison_tasks_sha256": "tasks.jsonl",
             "comparison_observations_sha256": "observations.jsonl"}
    comparison = root / "results/comparison_2026-09-30"
    for key, name in files.items():
        if sha256((comparison / name).read_bytes()).hexdigest() != data["provenance"][key]:
            raise ValueError("The original comparison artifact digest changed.")
    return analyze(data, C.rows(comparison / "tasks.jsonl"), C.rows(comparison / "observations.jsonl"))
