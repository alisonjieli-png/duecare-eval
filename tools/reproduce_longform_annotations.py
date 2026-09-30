"""Verify and reproduce source-centered numeric model annotations offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.longform_annotations import reproduce


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/longform_annotations_2026-09-30.findings.json").read_text())
        if result != expected:
            raise SystemExit("Long-form numeric findings differ from the captured result.")
        print("Long-form annotations reproduce exactly from hashed numeric fields.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
