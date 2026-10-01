"""Reproduce locked context/scaffold paired findings offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.context_scaffold import reproduce

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/context_scaffold_findings_2026-10-01.json").read_text())
        if result != expected:
            raise SystemExit("Context/scaffold findings differ from the frozen expected result.")
        print("Context/scaffold findings reproduce exactly: 32 reviews and 8 paired comparisons per model and axis.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
