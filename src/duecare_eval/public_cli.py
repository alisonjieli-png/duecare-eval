"""Validate DueCare tasks, reproduce findings and score saved responses offline."""
import argparse
import json
from pathlib import Path

from .decisioning import decision_input, score_decisions, validate_decision_tasks
from .console import comparisons_text, explain_error, findings_text


ROOT = Path(__file__).resolve().parents[2]


def load_rows(path):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Read {path}, line {number}: {error.msg}. Each line must contain one JSON object.") from error
            if not isinstance(row, dict):
                raise ValueError(f"Read {path}, line {number}: each record must be a JSON object.")
            rows.append(row)
    return rows


def doctor():
    """Check the local files needed by the public commands."""
    required = (
        "examples/crossborder_references.jsonl",
        "examples/crossborder_blind_inputs.jsonl",
        "examples/source_question_catalog.json",
        "examples/referral_question_catalog.json",
        "examples/style_comparison_references.jsonl",
        "results/release_findings.json",
        "results/release_snapshot.json",
        "results/source_questions_observations.jsonl",
        "results/referral_control_observations.jsonl",
        "results/style_deepseek_observations.jsonl",
        "results/style_kimi_observations.jsonl",
        "tools/reproduce_findings.py",
        "results/comparison_2026-09-30/snapshot.json",
        "results/comparison_2026-09-30/findings.json",
        "results/comparison_2026-09-30/tasks.jsonl",
        "results/comparison_2026-09-30/observations.jsonl",
        "results/comparison_2026-09-30/tier_requests.jsonl",
        "results/comparison_2026-09-30/tier_observations.jsonl",
        "results/comparison_2026-09-30/coverage.json",
        "examples/version_targets.json",
        "examples/version_targets.schema.json",
        "examples/version_configuration.json",
        "tools/version_benchmarks.py",
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    return {"ready": not missing, "network_used": False, "root": str(ROOT),
            "checked_files": len(required), "missing": missing}


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
    parser.add_argument("command", choices=["verify", "self-check", "score", "findings", "comparisons", "doctor"],
                        help="validate tasks, check the scorer, score outputs, reproduce findings/comparisons, or check local files")
    parser.add_argument("--references", type=Path, default=ROOT / "examples/crossborder_references.jsonl",
                        help="JSONL task references with local answer keys")
    parser.add_argument("--responses", type=Path, help="JSONL saved responses for score")
    parser.add_argument("--out", type=Path, help="write the complete score as JSON to this path")
    parser.add_argument("--json", action="store_true", help="print structured JSON for scripts")
    args = parser.parse_args()
    if args.command == "score" and (args.responses is None or args.out is None):
        parser.error("score requires --responses and --out")
    try:
        run_command(args)
    except (OSError, UnicodeError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(2, f"duecare-eval: {explain_error(error)}\n")


def emit(args, result, description):
    print(json.dumps(result, indent=2) if args.json else description)


def run_command(args):
    if args.command == "doctor":
        result = doctor()
        description = (f"DueCare checkout ready: {result['checked_files']} required files are present.\n"
                       "The public commands use local files and run offline.")
        if result["missing"]:
            description = "DueCare checkout has missing files:\n" + "\n".join(f"  {p}" for p in result["missing"])
            description += "\nUse a complete release checkout to run the public commands."
        emit(args, result, description)
        if not result["ready"]:
            raise SystemExit(2)
        return
    if args.command == "findings":
        from .source_analysis import reproduce
        result = reproduce(ROOT)
        emit(args, result, findings_text(result))
        return
    if args.command == "comparisons":
        from .comparison_analysis import reproduce
        result = reproduce(ROOT / "results/comparison_2026-09-30")
        emit(args, result, comparisons_text(result))
        return
    tasks = load_rows(args.references)
    validation = validate_decision_tasks(tasks)
    if args.command == "verify":
        hidden = {"expected", "oracle", "metadata", "pair_id", "split", "group_id", "leakage_group_id"}
        if any(hidden.intersection(decision_input(t)) for t in tasks):
            raise ValueError("hidden_reference_fields_in_input")
        emit(args, {"fixture_validation": validation, "hidden_fields_removed": True},
             f"Validated {len(tasks):,} decision tasks.\n"
             "Answer keys stay in local reference files; model inputs contain the task and its response contract.")
        return
    if args.command == "self-check":
        responses = {t["task_id"]: oracle(t) for t in tasks}
    else:
        rows = load_rows(args.responses)
        if any(not isinstance(r.get("task_id"), str) or "decision" not in r for r in rows):
            raise ValueError("invalid_response_record")
        ids = [r["task_id"] for r in rows]
        if len(ids) != len(set(ids)) or not set(ids) <= {t["task_id"] for t in tasks}:
            raise ValueError("duplicate_or_unknown_response_id")
        responses = {r["task_id"]: r["decision"] for r in rows}
    result = score_decisions(tasks, responses)
    if args.command == "self-check":
        if result["completed"] != len(tasks) or not all(r["correct"] for r in result["per_item"]):
            raise RuntimeError("oracle_self_check_failed")
        emit(args, {"kind": "SIMULATED_ORACLE_NOT_MODEL_PERFORMANCE", "requested": result["tasks"],
                    "completed": result["completed"], "invalid": result["invalid"], "coverage": result["coverage"]},
             f"Scorer self-check passed: {result['completed']:,} of {result['tasks']:,} answer keys recovered.\n"
             "This checks the scoring code using explicit reference answers.")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        emit(args, {"out": str(args.out), "requested": result["tasks"], "completed": result["completed"]},
             f"Scored {result['completed']:,} of {result['tasks']:,} requested tasks.\n"
             f"Full results, including invalid and missing outputs: {args.out}")


if __name__ == "__main__":
    main()
