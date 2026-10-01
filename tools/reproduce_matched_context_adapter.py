"""Reproduce the separate matched-context adapter conditions offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.matched_context_adapter import reproduce


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/matched_context_adapter_2026-10-01.findings.json").read_text())
        if result != expected:
            raise SystemExit("Adapter findings differ from the frozen expected result.")
        print("Matched-context adapter conditions reproduce exactly; baseline and follow-up stay separate.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
