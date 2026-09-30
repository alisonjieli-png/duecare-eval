"""Reproduce the captured comparative analysis offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.comparison_analysis import reproduce


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "results/comparison_2026-09-30")
    args = parser.parse_args()
    result = reproduce(args.snapshot)
    if args.check:
        expected = json.loads((args.snapshot / "findings.json").read_text())
        if result != expected:
            raise SystemExit("Comparative findings differ from the frozen expected result.")
        print("Comparative findings reproduce exactly from captured numeric observations.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
