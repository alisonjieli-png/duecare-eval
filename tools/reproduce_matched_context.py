"""Reproduce matched full-context numeric findings without provider access."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.matched_context import reproduce


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/matched_context_2026-09-30.findings.json").read_text())
        if result != expected:
            raise SystemExit("Matched-context findings differ from the frozen expected result.")
        print("Matched-context findings reproduce exactly from the public numeric projection.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
