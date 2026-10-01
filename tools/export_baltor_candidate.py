#!/usr/bin/env python3
"""Export a fresh, candidate-only Baltor package from this public checkout."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.baltor_bridge import BridgeError, export_candidate, validate_candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory outside the source checkout; existing paths are preserved.")
    parser.add_argument("--verify", action="store_true", help="Verify an existing candidate instead of exporting.")
    args = parser.parse_args(argv)
    try:
        result = validate_candidate(args.destination) if args.verify else export_candidate(ROOT, args.destination)
    except (BridgeError, ValueError, OSError) as exc:
        parser.exit(2, "Candidate refused: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
