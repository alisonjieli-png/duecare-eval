"""Reproduce the Jev-inclusive visual evidence using public local files."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.jev_visuals import reproduce


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    path = ROOT / "results/jev_visuals_2026-09-30.json"
    if args.check:
        if result != json.loads(path.read_text()):
            raise SystemExit("Jev visual evidence differs from the frozen expected result.")
        print("Jev visual evidence reproduces exactly: six-model matched tasks and ten full-context panels.")
    elif args.write:
        path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        print(path.relative_to(ROOT))
    else:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
