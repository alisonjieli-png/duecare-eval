"""Reconcile every requested source ID and its final numeric observation offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.source_completion import reproduce

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    print("Final source-request counts and supplemental provenance reproduce exactly." if args.check else json.dumps(result, indent=2, sort_keys=True))
