"""Clean JSON command-line interface for the offline component library."""

import argparse
import json
import sys

from .library import KINDS, Library, _load_json, build_catalog


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _Parser(description="Offline catalog discovery and verified pure functions")
    parser.add_argument("--root", help="Explicit reviewed local library root (defaults to this package)")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "search"):
        command = commands.add_parser(name)
        if name == "search":
            command.add_argument("query")
        command.add_argument("--kind", choices=KINDS)
        command.add_argument("--limit", type=int, default=20)
        command.add_argument("--offset", type=int, default=0)
    get = commands.add_parser("get")
    get.add_argument("id")
    run = commands.add_parser("run")
    run.add_argument("id")
    run.add_argument("--input", default="-", help="JSON object, or '-' to read JSON from stdin")
    commands.add_parser("build", help="Import reviewed local component metadata and atomically rebuild catalog/inventory")
    check = commands.add_parser("check")
    check.add_argument("--full", action="store_true", help="Also read and hash every query-preset payload")
    try:
        args = parser.parse_args(argv)
        if args.command == "build":
            catalog = build_catalog(args.root)
            output = {"ok": True, "counts": catalog["counts"], "files": len(catalog["files"]), "schema_version": catalog["schema_version"]}
        else:
            library = Library(args.root)
            if args.command in ("list", "search"):
                output = library.search(args.query if args.command == "search" else "", args.kind, args.limit, args.offset)
            elif args.command == "get":
                output = library.get(args.id)
            elif args.command == "run":
                output = library.run(args.id, _load_json(sys.stdin.read() if args.input == "-" else args.input))
            else:
                output = library.check(full=args.full)
        print(json.dumps(output, ensure_ascii=True, sort_keys=True, allow_nan=False))
        return 0
    except (KeyError, ValueError, TypeError, OSError, ImportError) as exc:
        print(json.dumps({"error": {"type": type(exc).__name__, "message": str(exc)}}, ensure_ascii=True, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
