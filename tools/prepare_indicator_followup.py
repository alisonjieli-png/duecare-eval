"""Create the reproducible composite-indicator follow-up and its blind inputs."""
import hashlib
import json
from pathlib import Path
from duecare_eval.indicator_followup import PROTOCOL, tasks, blind_tasks

ROOT = Path(__file__).resolve().parents[1]


def build():
    values = tasks()
    files = {}
    for name, rows in [("indicator_followup_references.jsonl", values), ("indicator_followup_blind_inputs.jsonl", blind_tasks(values))]:
        data = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        path = ROOT / "examples" / name
        if path.exists() and path.read_text() != data:
            raise ValueError("Use a new protocol and filename for a changed follow-up")
        path.write_text(data)
        files[name] = hashlib.sha256(data.encode()).hexdigest()
    manifest = {"protocol": PROTOCOL, "tasks": len(values), "fact_groups": 64,
                "calibration_tasks": 96, "held_out_tasks": 288, "roles": ["worker", "employer"],
                "presentations": ["forward", "reversed", "benign_context"], "labels": list(values[0]["labels"]),
                "files": files, "reference_basis": "Explicit fact composition", "domain_review": "pending"}
    (ROOT / "results/indicator_followup_design.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    build()
