"""Recompute the released six-condition follow-up from hashed numeric receipts."""
from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.comparison_analysis import digest, STATUSES
from duecare_eval.indicator_followup import PROTOCOL, assess, blind_tasks

FIELDS = {"task_id", "status", "decision", "attempt", "model", "model_reported",
          "request_sha256", "receipt_sha256"}


def reproduce(root=ROOT):
    root = Path(root)
    results = root / "results"
    manifest = json.loads((results / "indicator_followup_manifest.json").read_text())
    if manifest["protocol"] != PROTOCOL:
        raise ValueError("followup_protocol_mismatch")
    names = {"indicator_followup_observations.jsonl", "../examples/indicator_followup_references.jsonl"}
    if set(manifest["files"]) != names:
        raise ValueError("unexpected_followup_files")
    for name, expected in manifest["files"].items():
        if not digest(expected) or sha256((results / name).read_bytes()).hexdigest() != expected:
            raise ValueError("followup_file_digest_mismatch")
    tasks = [json.loads(line) for line in (root / "examples/indicator_followup_references.jsonl").read_text().splitlines() if line.strip()]
    blind_path = root / "examples/indicator_followup_blind_inputs.jsonl"
    if sha256(blind_path.read_bytes()).hexdigest() != manifest["source_design"]["files"][blind_path.name]:
        raise ValueError("followup_blind_input_digest_mismatch")
    if [json.loads(line) for line in blind_path.read_text().splitlines() if line.strip()] != blind_tasks(tasks):
        raise ValueError("followup_blind_reference_mismatch")
    observations = [json.loads(line) for line in (results / "indicator_followup_observations.jsonl").read_text().splitlines() if line.strip()]
    if len(tasks) != manifest["requested"]:
        raise ValueError("followup_requested_count_mismatch")
    ids = {t["task_id"] for t in tasks}
    seen, decisions = set(), {}
    for row in observations:
        if set(row) != FIELDS or row["task_id"] not in ids or row["task_id"] in seen:
            raise ValueError("unknown_duplicate_or_unexpected_followup_fields")
        if row["model"] != manifest["model"] or row["status"] not in STATUSES or type(row["attempt"]) is not int or row["attempt"] not in (1, 2):
            raise ValueError("invalid_followup_model_status_or_attempt")
        if not digest(row["receipt_sha256"]) or (row["request_sha256"] is not None and not digest(row["request_sha256"])):
            raise ValueError("invalid_followup_receipt_digest")
        if row["model_reported"] is not None and row["model_reported"] != manifest["model"]:
            raise ValueError("invalid_reported_model")
        if row["status"] == "completed":
            decisions[row["task_id"]] = row["decision"]
        elif row["decision"] is not None:
            raise ValueError("unsuccessful_followup_has_decision")
        seen.add(row["task_id"])
    assessment = assess(tasks, decisions)
    if assessment["invalid"]:
        raise ValueError("invalid_completed_followup_decision")
    return {"snapshot_at": manifest["snapshot_at"], "model": manifest["model"],
        "assessment": assessment, "outcomes": dict(Counter(r["status"] for r in observations)),
        "requested": len(tasks), "recorded": len(observations), "coverage": len(decisions) / len(tasks),
        "protocol": manifest["protocol"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce()
    if args.check:
        expected = json.loads((ROOT / "results/indicator_followup_findings.json").read_text())
        if result != expected:
            raise SystemExit("Follow-up findings differ from the captured expected result.")
        print("Follow-up findings reproduce exactly from hashed numeric observations.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
