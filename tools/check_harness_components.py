"""Reproduce the local component catalogue and run every declared example offline."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness_components import Library, build_catalog


def verify(root=ROOT / "harness_components"):
    library = Library(root)
    check = library.check(full=True)
    recorded = json.loads((Path(root) / "catalog.json").read_text(encoding="utf-8"))
    if build_catalog(root, write=False) != recorded:
        raise ValueError("catalog differs from current source metadata")
    examples = 0
    for entry in recorded["entries"]:
        if entry["kind"] != "function":
            continue
        for example in entry["examples"]:
            actual = library.run(entry["id"], example["input"])["result"]
            if actual != example["output"]:
                raise ValueError("declared example mismatch: " + entry["id"])
            examples += 1
    return {**check, "catalog_reproduced": True, "declared_examples_passed": examples,
            "project_provider_model_calls": 0,
            "scope": "Offline artifact integrity and declared examples; independent edge tests run in pytest."}


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
