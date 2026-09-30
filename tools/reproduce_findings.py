"""Recompute this release's descriptive findings without network access."""
import argparse
import json
from pathlib import Path
from duecare_eval.source_analysis import reproduce

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Require exact agreement with the frozen findings")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        expected = json.loads((ROOT / "results/release_findings.json").read_text())
        if result != expected:
            raise SystemExit("Frozen findings do not reproduce")
        print("All source and style findings reproduce exactly from released observations.")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
