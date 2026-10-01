"""Validate an industry pack and optionally export deterministic input JSONL."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.extensions import batch_payloads, load_pack, load_plugin, validate_pack
from duecare_eval.contracts import canonical, text_hash


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--plugin", type=Path)
    parser.add_argument("--include-sources", action="store_true")
    parser.add_argument("--output", type=Path, help="New JSONL file; existing targets are preserved.")
    args = parser.parse_args(argv)
    pack = load_pack(args.pack); summary = validate_pack(pack)
    profile = load_plugin(args.plugin) if args.plugin else "jsonl-batch"
    if args.plugin or args.output:
        payloads = batch_payloads(pack, profile, include_sources=args.include_sources)
        lines = "".join(canonical(payload) + "\n" for payload in payloads)
        summary.update(adapter=profile["adapter"] if isinstance(profile, dict) else profile,
                       source_context_included=args.include_sources, prepared_payloads=len(payloads),
                       payload_jsonl_sha256=text_hash(lines))
        if summary["adapter"] == "jev-typed":
            summary["projected_typed_question_slots"] = sum(len(payload["questions"]) for payload in payloads)
        if args.output:
            # No overwrite and no inference. The author chooses the destination.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(lines)
            summary["output"] = str(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
