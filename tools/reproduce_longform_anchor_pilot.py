"""Recompute blind authored-candidate and both-order pilot results offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.anchor_pilot import reproduce

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        if result != json.loads((ROOT / "results/longform_anchor_pilot_2026-09-30.findings.json").read_text()):
            raise SystemExit("Anchor pilot findings differ from the captured result.")
        print("Long-form anchor and both-order pilot findings reproduce exactly.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
