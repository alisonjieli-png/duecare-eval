"""Check rubric examples or score a supplied file of structured responses offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.rubric_examples import score_instances, validate_bank


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", type=Path, help="JSONL with instance_id, status and answer fields")
    args = parser.parse_args()
    bank = json.loads((ROOT / "examples/grading_rubrics.json").read_text())
    result = {"kind": "rubric_definition_check", **validate_bank(bank), "network_used": False}
    if args.responses:
        responses = [json.loads(line) for line in args.responses.read_text().splitlines() if line.strip()]
        result = score_instances(bank, responses)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
