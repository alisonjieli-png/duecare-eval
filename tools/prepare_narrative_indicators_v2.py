"""Build or verify the prepared narrative/social-post bank without inference."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.contracts import canonical
from duecare_eval.narrative_indicators_v2 import build_bank


def outputs():
    def load(name):
        return json.loads((ROOT / "results" / name).read_text())
    source_names = ["longform_cases_2026-09-30.json", "documented_indicator_sources_2026-10-01.json", "longform_jev_questions_2026-09-30.json"]
    bank = build_bank(*(load(name) for name in source_names))
    def lines(rows):
        return "".join(canonical(row) + "\n" for row in rows)
    def document(value):
        return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    data = {"contexts.jsonl": lines(bank["contexts"]), "specifications.jsonl": lines(bank["specifications"]),
            "blind_inputs.jsonl": lines([{k: r[k] for k in ("specification_id", "model_input", "model_input_sha256")} for r in bank["specifications"]]),
            "references.jsonl": lines([{"context_id": c["context_id"], "reference": c["reference"]} for c in bank["contexts"]]),
            "catalog.json": document(bank["catalog"]), "archived_menu_v1.json": document(bank["archived_menu"])}
    manifest = {**bank["manifest"], "source_files": {"results/" + name: sha256((ROOT / "results" / name).read_bytes()).hexdigest() for name in source_names},
                "files": {name: {"sha256": sha256(value.encode()).hexdigest(), "bytes": len(value.encode())} for name, value in data.items()},
                "execution": "Pass only a specification's model_input to a reviewed hosted adapter. Add the exact served model binding at dispatch. This tool performs zero provider calls."}
    data["manifest.json"] = document(manifest)
    return data, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-prepared", action="store_true")
    parser.add_argument("--archive-dir", type=Path)
    args = parser.parse_args()
    data, manifest = outputs()
    folder = ROOT / "examples/narrative_indicators_v2"
    if args.check:
        if any(not (folder / name).exists() or (folder / name).read_text() != text for name, text in data.items()):
            raise SystemExit("Prepared narrative bank differs from deterministic source reconstruction.")
        print("Narrative indicator bank reproduces exactly: 156 specifications, 39 contexts, 37 questions each, 0 model calls.")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        changed = any((folder / name).exists() and (folder / name).read_text() != text for name, text in data.items())
        if changed:
            if not args.refresh_prepared or args.archive_dir is None:
                raise SystemExit("Prepared artifact differs; use an explicit archive directory to preserve the earlier unexecuted preparation.")
            old = json.loads((folder / "manifest.json").read_text())
            if old.get("status") != "prepared_no_inference" or old.get("model_calls_executed") != 0:
                raise SystemExit("An executed bank requires a separate output directory and protocol.")
            archive = args.archive_dir / sha256((folder / "manifest.json").read_bytes()).hexdigest()[:16]
            archive.mkdir(parents=True, exist_ok=True)
            for name in data:
                previous = folder / name
                if previous.exists():
                    target = archive / name
                    if target.exists() and target.read_bytes() != previous.read_bytes():
                        raise SystemExit("Existing preparation archive differs.")
                    target.write_bytes(previous.read_bytes())
        for name, text in data.items():
            path = folder / name
            path.write_text(text)
        print(json.dumps({k: manifest[k] for k in ("protocol", "status", "contexts", "specifications", "questions_per_panel", "logical_question_slots", "model_calls_executed")}, indent=2))
