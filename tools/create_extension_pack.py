"""Create a new two-case starter pack for offline industry-extension checks."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.extensions import create_pack


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--industry", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args(argv)
    summary = create_pack(args.destination, args.pack_id, args.industry, args.title)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
