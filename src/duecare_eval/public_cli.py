"""Offline validation and scoring. No providers, credentials or live calls."""
import argparse
import json
from pathlib import Path

from .decisioning import decision_input, score_decisions, validate_decision_tasks


ROOT = Path(__file__).resolve().parents[2]


def load_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def oracle(task):
    kind, expected = task["decision_type"], task["expected"]
    if kind == "binary_probability":
        return {"probability": float(expected)}
    if kind == "ordinal_distribution":
        return {"probabilities": {str(i): float(i == expected) for i in range(1, 6)}}
    if kind == "categorical_distribution":
        return {"probabilities": {c: float(c == expected) for c in task["choices"]}}
    return {"probabilities": {c: float(c in expected) for c in task["labels"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "self-check", "score"])
    parser.add_argument("--references", type=Path, default=ROOT / "examples/crossborder_references.jsonl")
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    tasks = load_rows(args.references)
    validation = validate_decision_tasks(tasks)
    if args.command == "verify":
        hidden = {"expected", "oracle", "metadata", "pair_id", "split", "group_id", "leakage_group_id"}
        assert all(not hidden.intersection(decision_input(t)) for t in tasks)
        print(json.dumps({"fixture_validation": validation, "hidden_fields_removed": True}))
        return
    if args.command == "self-check":
        responses = {t["task_id"]: oracle(t) for t in tasks}
    else:
        if args.responses is None or args.out is None:
            parser.error("score requires --responses and --out")
        rows = load_rows(args.responses)
        ids = [r["task_id"] for r in rows]
        if len(ids) != len(set(ids)) or not set(ids) <= {t["task_id"] for t in tasks}:
            raise ValueError("duplicate_or_unknown_response_id")
        responses = {r["task_id"]: r["decision"] for r in rows}
    result = score_decisions(tasks, responses)
    if args.command == "self-check":
        print(json.dumps({"kind": "SIMULATED_ORACLE_NOT_MODEL_PERFORMANCE", "requested": result["tasks"],
                          "completed": result["completed"], "invalid": result["invalid"], "coverage": result["coverage"]}))
        if result["completed"] != len(tasks) or not all(r["correct"] for r in result["per_item"]):
            raise RuntimeError("oracle_self_check_failed")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps({"out": str(args.out), "requested": result["tasks"], "completed": result["completed"]}))


if __name__ == "__main__":
    main()
