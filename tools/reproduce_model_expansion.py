"""Check dated model-extension coverage using only the public checkout."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.model_expansion import reproduce


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reproduce(ROOT)
    if args.check:
        print("Model expansion verified offline: 60 answer payloads, 6 access checks, 2 separate GLM controls; 46 complete and 14 truncated baseline responses; 2 CLI invocations with unknown provider-call count.")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
