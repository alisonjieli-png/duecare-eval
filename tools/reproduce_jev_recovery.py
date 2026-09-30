"""Recompute the dated Jev recovery overlay from public numeric evidence."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.recovery_analysis import reproduce


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    expected = json.loads((ROOT / "results/jev_recovery_2026-09-30.json").read_text())["findings"]
    if args.check:
        if result != expected:
            raise SystemExit("The recovery findings differ from the released numeric evidence.")
        print("Jev recovery findings reproduce exactly from public records.")
    else:
        print(json.dumps(result, indent=2))
