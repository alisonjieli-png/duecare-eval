"""Reproduce the separate anchored-object and fieldwise numeric interpretation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.structured_extraction import reproduce

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/structured_extraction_2026-10-01.findings.json").read_text())
        if result != expected:
            raise SystemExit("Structured-extraction findings differ from the frozen result.")
        print("Structured extraction reproduces exactly; original snapshots remain distinct.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
