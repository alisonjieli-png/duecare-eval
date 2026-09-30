"""Check source identity, tier/profile balance and blind packets offline."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.reference_bank import validate_bank

if __name__ == "__main__":
    print(json.dumps(validate_bank(ROOT / "examples/reference_bank_v1"), indent=2))
