"""Prepare versioned task bundles, import saved responses and compare runs offline."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval import version_benchmarks as versions
from duecare_eval.public_cli import load_rows


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["registry", "prepare", "import", "baseline", "compare"])
    parser.add_argument("--registry", type=Path, default=ROOT / "examples/version_targets.json")
    parser.add_argument("--references", type=Path, default=ROOT / "examples/crossborder_references.jsonl")
    parser.add_argument("--target", help="registered target_id with a pinned model version")
    parser.add_argument("--configuration", type=Path, help="public JSON adapter and decoding settings")
    parser.add_argument("--bundle", type=Path, help="prepared bundle directory")
    parser.add_argument("--responses", type=Path, help="saved JSONL receipts or published baseline responses")
    parser.add_argument("--baseline", type=Path, help="imported baseline run JSON")
    parser.add_argument("--candidate", type=Path, help="imported candidate run JSON")
    parser.add_argument("--suite", default="crossborder-v1")
    parser.add_argument("--out", type=Path, help="new output file, or a new directory for prepare")
    args = parser.parse_args()
    required = {"registry": [], "prepare": ["target", "configuration", "out"],
                "import": ["bundle", "responses", "out"], "baseline": ["target", "responses", "out"],
                "compare": ["baseline", "candidate", "out"]}
    for field in required[args.command]:
        if getattr(args, field) is None:
            parser.error(f"{args.command} requires --{field}")
    try:
        if args.command == "registry":
            registry = versions.validate_registry(read_json(args.registry))
            print(json.dumps(registry, indent=2))
            return
        tasks = load_rows(args.references)
        if args.command in {"prepare", "baseline"}:
            target = versions.select_target(read_json(args.registry), args.target)
        if args.command == "prepare":
            bundle = versions.prepare(tasks, target, read_json(args.configuration), args.suite)
            args.out.mkdir(parents=True, exist_ok=False)
            write_new(args.out / "manifest.json", bundle["manifest"])
            with (args.out / "blind_tasks.jsonl").open("x", encoding="utf-8") as stream:
                for row in bundle["blind_tasks"]:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            print(f"Prepared {len(tasks):,} blind tasks for {target['model_id']}: {args.out}")
            return
        if args.command == "import":
            result = versions.import_receipts(tasks, read_json(args.bundle / "manifest.json"), load_rows(args.responses))
        elif args.command == "baseline":
            result = versions.import_legacy_baseline(tasks, target, load_rows(args.responses), args.suite)
        else:
            result = versions.compare_versions(tasks, read_json(args.baseline), read_json(args.candidate))
        write_new(args.out, result)
        print(f"Wrote {args.command} result: {args.out}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"version-benchmarks: {error}\n")


if __name__ == "__main__":
    main()
