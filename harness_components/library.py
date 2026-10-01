"""Data-only discovery and hash-verified execution of reviewed local components.

``build_catalog`` is an explicit trusted-source import boundary. It must only
be used on reviewed local source. A catalog and its hashes provide integrity,
not a signature or a sandbox for untrusted Python. Search/get never import
component code. Run rechecks the exact source closure on every invocation and
executes the verified bytes in a fresh private package, avoiding stale modules
and unverified bytecode caches. Query presets and skills are data, never tools.
"""

import ast
from collections import Counter
import copy
import hashlib
import importlib.abc
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import threading
import uuid


SCHEMA_VERSION = "1.0.0"
SEARCH_METHOD = "weighted_token_overlap_v1"
KINDS = ("function", "query_preset", "skill", "upstream_reference")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_IMPORT_LOCK = threading.RLock()
_FUNCTION_FIELDS = {"kind", "path", "sha256", "dependencies"}


class IntegrityError(ValueError):
    """A catalog path, source dependency or stored payload failed verification."""


def _json_value(value):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    raise TypeError("plain JSON values with string object keys are required")


def _canonical(value):
    _json_value(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _load_json(data):
    def invalid_constant(value):
        raise ValueError("nonfinite JSON number")
    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=invalid_constant)
    _json_value(value)
    return value


def _root(value=None):
    path = Path(__file__).parent if value is None else Path(value)
    path = path.absolute()
    for current in (path, *path.parents):
        if current.is_symlink():
            raise IntegrityError("library root must not contain symlink components")
    if not path.is_dir():
        raise ValueError("library root must be an existing directory")
    return path


def _relative(value):
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise IntegrityError("invalid catalog relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value or ":" in value:
        raise IntegrityError("catalog path must stay within the library root")
    return path


def _path(root, relative):
    result = root
    for part in _relative(relative).parts:
        result = result / part
        if result.is_symlink():
            raise IntegrityError("symlink catalog paths are forbidden")
    return result


def _read(root, relative):
    path = _path(root, relative)
    if not path.is_file():
        raise IntegrityError("catalog file is missing: " + relative)
    return path.read_bytes()


def _verified(root, relative, expected):
    if type(expected) is not str or not _SHA.fullmatch(expected):
        raise IntegrityError("invalid SHA-256 record")
    data = _read(root, relative)
    if _sha(data) != expected:
        raise IntegrityError("file hash mismatch: " + relative)
    return data


def validate(value, schema, path="payload"):
    """Validate the supported JSON Schema subset, preserving Python JSON types."""
    _json_value(value)
    if schema is True:
        return
    if schema is False:
        raise ValueError(path + ": forbidden value")
    if type(schema) is not dict:
        raise ValueError("invalid JSON schema")
    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword in schema:
            successes = 0
            for branch in schema[keyword]:
                try:
                    validate(value, branch, path)
                except (TypeError, ValueError):
                    pass
                else:
                    successes += 1
            if (keyword == "allOf" and successes != len(schema[keyword])) or (keyword == "anyOf" and not successes) or (keyword == "oneOf" and successes != 1):
                raise ValueError(path + ": schema alternatives did not match")
    if "not" in schema:
        try:
            validate(value, schema["not"], path)
        except (TypeError, ValueError):
            pass
        else:
            raise ValueError(path + ": excluded by schema")
    kinds = schema.get("type", [])
    kinds = [kinds] if type(kinds) is str else kinds
    matches = {"null": value is None, "boolean": type(value) is bool,
               "integer": type(value) is int, "number": type(value) in (int, float),
               "string": type(value) is str, "array": type(value) is list, "object": type(value) is dict}
    if kinds and not any(matches.get(kind, False) for kind in kinds):
        raise TypeError(path + ": wrong JSON type")
    if "enum" in schema and not any(_canonical(value) == _canonical(item) for item in schema["enum"]):
        raise ValueError(path + ": unknown enum value")
    if "const" in schema and _canonical(value) != _canonical(schema["const"]):
        raise ValueError(path + ": wrong constant")
    if type(value) in (int, float):
        for key, invalid in (("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b),
                             ("exclusiveMinimum", lambda a, b: a <= b), ("exclusiveMaximum", lambda a, b: a >= b)):
            if key in schema and invalid(value, schema[key]):
                raise ValueError(path + ": numeric bound exceeded")
    if type(value) is str:
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            raise ValueError(path + ": invalid string length")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(path + ": string does not match pattern")
    if type(value) is list:
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            raise ValueError(path + ": invalid array length")
        if schema.get("uniqueItems") and len({_canonical(item) for item in value}) != len(value):
            raise ValueError(path + ": duplicate array items")
        for index, item in enumerate(value):
            validate(item, schema.get("items", True), path + "/" + str(index))
    if type(value) is dict:
        if not set(schema.get("required", [])) <= value.keys():
            raise ValueError(path + ": missing required fields")
        properties = schema.get("properties", {})
        for key, item in value.items():
            validate(item, properties.get(key, schema.get("additionalProperties", True)), path + "/" + key)


def _schema_supported(schema):
    if type(schema) is bool:
        return
    if type(schema) is not dict:
        raise ValueError("schema must be an object or boolean")
    allowed = {"type", "properties", "required", "additionalProperties", "items", "minLength", "maxLength",
               "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
               "enum", "const", "description", "title", "default", "examples", "pattern", "anyOf", "oneOf", "allOf", "not", "$schema"}
    if set(schema) - allowed:
        raise ValueError("unsupported schema keywords: " + ", ".join(sorted(set(schema) - allowed)))
    for child in schema.get("properties", {}).values():
        _schema_supported(child)
    for key in ("items", "additionalProperties", "not"):
        if key in schema:
            _schema_supported(schema[key])
    for key in ("allOf", "anyOf", "oneOf"):
        for child in schema.get(key, []):
            _schema_supported(child)


def _module_name(relative):
    parts = list(PurePosixPath(relative).parts)
    if parts[-1] == "__init__.py":
        return ".".join(parts[:-1])
    parts[-1] = parts[-1][:-3]
    return ".".join(parts)


def _dependency_closure(root, entrypoint, expected=None):
    """Resolve static relative imports plus every existing package initializer."""
    pending, sources = [entrypoint], {}
    while pending:
        relative = pending.pop()
        if relative in sources:
            continue
        data = _read(root, relative)
        if expected is not None and _sha(data) != expected.get(relative):
            raise IntegrityError("uncatalogued or changed source dependency: " + relative)
        sources[relative] = data
        path = PurePosixPath(relative)
        for parent in (path.parent, *path.parent.parents):
            initializer = (parent / "__init__.py").as_posix()
            if _path(root, initializer).is_file() and initializer not in sources:
                pending.append(initializer)
        tree = ast.parse(data, filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "harness_components":
                        raise ValueError("component-local imports must be relative")
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            parent = path.parent
            for _ in range(node.level - 1):
                if parent == PurePosixPath("."):
                    raise IntegrityError("relative import escapes library root")
                parent = parent.parent
            targets = [node.module.replace(".", "/")] if node.module else [alias.name for alias in node.names]
            for target in targets:
                stem = parent / target
                candidate = stem.as_posix() + ".py"
                package = (stem / "__init__.py").as_posix()
                if _path(root, candidate).is_file():
                    pending.append(candidate)
                elif _path(root, package).is_file():
                    pending.append(package)
                elif not _path(root, stem.as_posix()).is_dir():
                    raise IntegrityError("unresolved local import: " + stem.as_posix())
    return dict(sorted(sources.items()))


class _VerifiedImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, root, prefix, sources):
        self.root, self.prefix = root, prefix
        self.modules = {_module_name(path): (path, data) for path, data in sources.items()}
        self.packages = {""}
        for name in self.modules:
            pieces = name.split(".")
            self.packages.update(".".join(pieces[:i]) for i in range(1, len(pieces)))
        self.packages.update(name for name, (path, _) in self.modules.items() if path.endswith("/__init__.py") or path == "__init__.py")

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.prefix and not fullname.startswith(self.prefix + "."):
            return None
        name = fullname[len(self.prefix):].lstrip(".")
        if name not in self.modules and name not in self.packages:
            raise ImportError("module is outside the verified source closure")
        return importlib.util.spec_from_loader(fullname, self, is_package=name in self.packages)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        name = module.__name__[len(self.prefix):].lstrip(".")
        if name in self.packages:
            module.__path__ = []
        if name in self.modules:
            relative, source = self.modules[name]
            module.__file__ = str(self.root / relative)
            exec(compile(source, module.__file__, "exec", dont_inherit=True), module.__dict__)


def _with_module(root, entrypoint, sources, action):
    prefix = "_duecare_verified_" + uuid.uuid4().hex
    importer = _VerifiedImporter(root, prefix, sources)
    with _IMPORT_LOCK:
        sys.meta_path.insert(0, importer)
        try:
            module = __import__(prefix + "." + _module_name(entrypoint), fromlist=["run"])
            return action(module)
        finally:
            sys.meta_path.remove(importer)
            for name in list(sys.modules):
                if name == prefix or name.startswith(prefix + "."):
                    del sys.modules[name]


def _check_spec(specification, expected_id):
    _json_value(specification)
    required = {"id", "version", "description", "input_schema", "output_schema", "effects", "examples"}
    if type(specification) is not dict or not required <= specification.keys() or set(specification) & _FUNCTION_FIELDS:
        raise ValueError("component SPEC is incomplete or uses reserved catalog fields")
    if specification["id"] != expected_id or specification["effects"] != ["pure"]:
        raise ValueError("component ID/path or pure-effect contract mismatch")
    if not all(type(specification[key]) is str and specification[key] for key in ("id", "version", "description")):
        raise ValueError("component string metadata is malformed")
    _schema_supported(specification["input_schema"])
    _schema_supported(specification["output_schema"])
    if type(specification["examples"]) is not list or not specification["examples"]:
        raise ValueError("component must declare examples")
    for example in specification["examples"]:
        validate(example["input"], specification["input_schema"])
        validate(example["output"], specification["output_schema"], "result")


def _skill_metadata(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("skill requires YAML frontmatter")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError("unterminated skill frontmatter") from exc
    values = {}
    for line in lines[1:end]:
        match = re.fullmatch(r"(name|description):\s*(.+)", line)
        if match:
            key, value = match.groups()
            if key in values or value in ("|", ">", "|-", ">-"):
                raise ValueError("skill metadata requires unique one-line scalars")
            if value.startswith('"'):
                value = _load_json(value)
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("''", "'")
            values[key] = value
    if set(values) != {"name", "description"} or not all(type(value) is str and value for value in values.values()):
        raise ValueError("skill requires one-line name and description")
    return values


def _atomic_json(root, relative, value):
    destination = _path(root, relative)
    data = _canonical(value) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".catalog-", dir=root)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return _sha(data)


def build_catalog(root=None, *, write=True):
    """Explicitly import reviewed local modules and build a deterministic catalog.

    Query and upstream-reference payload hashes come from their existing JSONL
    manifests; payloads are checked on get or check(full=True). Upstream records
    are unreviewed metadata only and never become installed or runnable code.
    """
    if type(write) is not bool:
        raise TypeError("write must be boolean")
    root = _root(root)
    entries, files = [], {}
    components = _path(root, "components")
    if components.is_dir():
        for group in sorted(components.iterdir()):
            _path(root, group.relative_to(root).as_posix())
            if not group.is_dir() or not _NAME.fullmatch(group.name):
                continue
            for source in sorted(group.glob("*.py")):
                if source.name.startswith("_"):
                    continue
                if not _NAME.fullmatch(source.stem):
                    raise ValueError("invalid component module filename")
                relative = source.relative_to(root).as_posix()
                closure = _dependency_closure(root, relative)
                expected_id = group.name + "." + source.stem
                def describe(module):
                    specification = copy.deepcopy(module.SPEC)
                    _check_spec(specification, expected_id)
                    if not callable(getattr(module, "run", None)):
                        raise ValueError("component must export run")
                    return specification
                specification = _with_module(root, relative, closure, describe)
                for path, data in closure.items():
                    digest = _sha(data)
                    if path in files and files[path] != digest:
                        raise IntegrityError("source changed during catalog construction")
                    files[path] = digest
                entries.append({**specification, "kind": "function", "path": relative,
                                "sha256": files[relative], "dependencies": sorted(closure)})
    query_index = _path(root, "search_queries/catalog.jsonl")
    if query_index.is_file():
        index_bytes = _read(root, "search_queries/catalog.jsonl")
        files["search_queries/catalog.jsonl"] = _sha(index_bytes)
        for line in index_bytes.splitlines():
            if not line.strip():
                continue
            row = _load_json(line)
            if type(row) is not dict or row.get("type") != "query_preset" or not all(type(row.get(key)) is str for key in ("id", "query", "payload_path", "payload_sha256")):
                raise ValueError("malformed query-preset index row")
            if not row["payload_path"].startswith("items/") or not _SHA.fullmatch(row["payload_sha256"]):
                raise IntegrityError("invalid query-preset payload reference")
            relative = "search_queries/" + _relative(row["payload_path"]).as_posix()
            _path(root, relative)
            if relative in files and files[relative] != row["payload_sha256"]:
                raise IntegrityError("conflicting query-preset payload hashes")
            files[relative] = row["payload_sha256"]
            entries.append({**row, "kind": "query_preset", "description": row.get("scope", "Unexecuted search query preset."), "payload_path": relative})
    upstream_index = _path(root, "discovery/upstream/catalog.jsonl")
    if upstream_index.is_file():
        index_bytes = _read(root, "discovery/upstream/catalog.jsonl")
        files["discovery/upstream/catalog.jsonl"] = _sha(index_bytes)
        for line in index_bytes.splitlines():
            if not line.strip():
                continue
            row = _load_json(line)
            required = ("id", "title", "repository", "upstream_kind", "path", "source_url", "payload_path", "payload_sha256")
            if type(row) is not dict or row.get("type") != "upstream_reference" or not all(type(row.get(key)) is str for key in required):
                raise ValueError("malformed upstream-reference index row")
            if row.get("status") != "discovered_unreviewed" or row.get("installed") is not False or row.get("verified") is not False or row.get("license_scope") != "unreviewed":
                raise ValueError("upstream-reference review status must remain explicit")
            if not row["payload_path"].startswith("items/") or not _SHA.fullmatch(row["payload_sha256"]):
                raise IntegrityError("invalid upstream-reference payload reference")
            relative = "discovery/upstream/" + _relative(row["payload_path"]).as_posix()
            _path(root, relative)
            if relative in files and files[relative] != row["payload_sha256"]:
                raise IntegrityError("conflicting upstream-reference payload hashes")
            files[relative] = row["payload_sha256"]
            entries.append({**row, "kind": "upstream_reference", "payload_path": relative,
                            "description": "Unreviewed upstream " + row["upstream_kind"] + " metadata from " + row["repository"] + "."})
    skills = _path(root, "skills")
    if skills.is_dir():
        for source in sorted(skills.glob("*/SKILL.md")):
            relative = source.relative_to(root).as_posix()
            data = _read(root, relative)
            metadata = _skill_metadata(data.decode("utf-8"))
            files[relative] = _sha(data)
            entries.append({"id": "skill." + metadata["name"], "kind": "skill", **metadata,
                            "path": relative, "sha256": files[relative], "effects": ["data_only"]})
    entries.sort(key=lambda entry: entry["id"])
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("duplicate catalog ID")
    counts = {kind: sum(entry["kind"] == kind for entry in entries) for kind in KINDS}
    catalog = {"schema_version": SCHEMA_VERSION, "search_method": SEARCH_METHOD,
               "counts": counts, "entries": entries, "files": dict(sorted(files.items()))}
    if write:
        digest = _atomic_json(root, "catalog.json", catalog)
        _atomic_json(root, "inventory.json", {"schema_version": SCHEMA_VERSION, "catalog_sha256": digest,
                     "counts": counts, "total_entries": len(entries), "file_count": len(files),
                     "function_ids": [entry["id"] for entry in entries if entry["kind"] == "function"],
                     "skill_ids": [entry["id"] for entry in entries if entry["kind"] == "skill"],
                     "data_payload_hashes": "declared by local query/upstream JSONL indexes; verified on get or check --full"})
    return catalog


def _words(value):
    return set(re.findall(r"[^\W_]+", value.casefold()))


def _search_text(value):
    if type(value) is str:
        return value
    if type(value) is list:
        return " ".join(_search_text(item) for item in value)
    if type(value) is dict:
        return " ".join(_search_text(item) for item in value.values())
    return ""


def _card(entry, score):
    fields = ("id", "kind", "title", "description", "version", "tags", "query", "source_url", "path",
              "repository", "upstream_kind", "status", "installed", "verified", "license_scope")
    return {**{key: copy.deepcopy(entry[key]) for key in fields if key in entry}, "score": score}


class Library:
    """Read a prebuilt local catalog without importing any component modules."""

    def __init__(self, root=None):
        self.root = _root(root)
        data = _read(self.root, "catalog.json")
        self.catalog_sha256 = _sha(data)
        self._catalog = _load_json(data)
        if type(self._catalog) is not dict or self._catalog.get("schema_version") != SCHEMA_VERSION or self._catalog.get("search_method") != SEARCH_METHOD:
            raise ValueError("unsupported catalog format")
        self._entries = self._catalog.get("entries")
        self._files = self._catalog.get("files")
        if type(self._entries) is not list or type(self._files) is not dict:
            raise ValueError("malformed catalog collections")
        for path, digest in self._files.items():
            _relative(path)
            if type(digest) is not str or not _SHA.fullmatch(digest):
                raise IntegrityError("malformed file hash record")
        self._by_id = {}
        for entry in self._entries:
            if type(entry) is not dict or type(entry.get("id")) is not str or not entry["id"] or entry.get("kind") not in KINDS or entry["id"] in self._by_id:
                raise ValueError("invalid or duplicate catalog entry")
            kind = entry["kind"]
            if kind == "function":
                path = _relative(entry["path"])
                if len(path.parts) != 3 or path.parts[0] != "components" or not path.name.endswith(".py") or path.name.startswith("_") or entry["id"] != path.parts[1] + "." + path.stem:
                    raise IntegrityError("function entrypoint does not match its ID")
                if type(entry.get("dependencies")) is not list or entry["path"] not in entry["dependencies"]:
                    raise IntegrityError("function source closure is missing")
                for dependency in entry["dependencies"]:
                    if dependency not in self._files or not dependency.endswith(".py"):
                        raise IntegrityError("uncatalogued source dependency")
                if entry.get("sha256") != self._files.get(entry["path"]):
                    raise IntegrityError("entrypoint digest mismatch")
            elif kind in ("query_preset", "upstream_reference"):
                path = _relative(entry["payload_path"])
                prefix = ("search_queries", "items") if kind == "query_preset" else ("discovery", "upstream", "items")
                if path.parts[:len(prefix)] != prefix or entry.get("payload_sha256") != self._files.get(entry["payload_path"]):
                    raise IntegrityError("invalid data-only payload record")
                if kind == "upstream_reference" and (entry.get("status") != "discovered_unreviewed" or entry.get("installed") is not False or entry.get("verified") is not False or entry.get("license_scope") != "unreviewed"):
                    raise IntegrityError("upstream-reference review status changed")
            else:
                path = _relative(entry["path"])
                if len(path.parts) != 3 or path.parts[0] != "skills" or path.name != "SKILL.md" or entry.get("sha256") != self._files.get(entry["path"]):
                    raise IntegrityError("invalid skill payload record")
            self._by_id[entry["id"]] = entry
        self.counts = {kind: sum(entry["kind"] == kind for entry in self._entries) for kind in KINDS}
        if self.counts != self._catalog.get("counts") or any(type(value) is not int for value in self._catalog["counts"].values()):
            raise IntegrityError("catalog counts do not reconcile")

    def summary(self):
        """Return data-only catalog counts and method/digest metadata for adapters."""
        return {"schema_version": SCHEMA_VERSION, "catalog_sha256": self.catalog_sha256,
                "search_method": SEARCH_METHOD, "counts": dict(self.counts),
                "total_entries": len(self._entries), "file_count": len(self._files)}

    def search(self, query, kind=None, limit=20, offset=0):
        if type(query) is not str or type(limit) is not int or type(offset) is not int:
            raise TypeError("query must be a string; limit and offset must be integers")
        if limit < 1 or offset < 0 or (kind is not None and kind not in KINDS):
            raise ValueError("invalid search pagination or kind")
        wanted = _words(query)
        matches = []
        for entry in self._entries:
            if kind is not None and entry["kind"] != kind:
                continue
            identifier = _words(entry["id"])
            title = _words(str(entry.get("title", entry.get("name", ""))))
            description = _words(entry.get("description", "") + " " + entry.get("query", ""))
            tags = _words(_search_text(entry.get("tags", [])))
            source_fields = {key: entry.get(key, "") for key in ("sources", "source_refs", "source_url", "repository", "upstream_kind", "path")}
            sources = _words(_search_text(source_fields))
            score = 8 * len(wanted & identifier) + 4 * len(wanted & title) + 3 * len(wanted & tags) + 2 * len(wanted & description) + len(wanted & sources)
            if wanted and not score:
                continue
            matches.append((score, entry["id"], entry))
        matches.sort(key=lambda match: (-match[0], match[1]))
        page = [_card(entry, score) for score, _, entry in matches[offset:offset + limit]]
        next_offset = offset + len(page) if offset + len(page) < len(matches) else None
        return {"query": query, "kind": kind, "method": SEARCH_METHOD, "total_matches": len(matches),
                "offset": offset, "limit": limit, "next_offset": next_offset, "results": page}

    def _entry(self, identifier):
        if type(identifier) is not str:
            raise TypeError("component ID must be a string")
        if identifier not in self._by_id:
            raise KeyError("unknown component ID: " + identifier)
        return self._by_id[identifier]

    def get(self, identifier):
        entry = self._entry(identifier)
        result = copy.deepcopy(entry)
        if entry["kind"] in ("query_preset", "upstream_reference"):
            result["payload"] = _load_json(_verified(self.root, entry["payload_path"], entry["payload_sha256"]))
            if type(result["payload"]) is not dict or result["payload"].get("id") != identifier:
                raise IntegrityError("data payload ID mismatch")
            if entry["kind"] == "upstream_reference" and any(result["payload"].get(key) != entry.get(key) or type(result["payload"].get(key)) is not type(entry.get(key)) for key in ("status", "installed", "verified", "license_scope")):
                raise IntegrityError("upstream payload review status differs from catalog")
        elif entry["kind"] == "skill":
            result["content"] = _verified(self.root, entry["path"], entry["sha256"]).decode("utf-8")
        return result

    def run(self, identifier, payload):
        entry = self._entry(identifier)
        if entry["kind"] != "function":
            raise ValueError("only catalogued functions can be run; skills, query presets and upstream references are data")
        _json_value(payload)
        sources = _dependency_closure(self.root, entry["path"], self._files)
        if set(sources) != set(entry["dependencies"]):
            raise IntegrityError("source dependency closure differs from catalog")
        recorded_spec = {key: value for key, value in entry.items() if key not in _FUNCTION_FIELDS}
        def invoke(component):
            if _canonical(component.SPEC) != _canonical(recorded_spec):
                raise IntegrityError("runtime SPEC differs from catalog metadata")
            validate(payload, recorded_spec["input_schema"])
            result = component.run(copy.deepcopy(payload))
            validate(result, recorded_spec["output_schema"], "result")
            return result
        result = _with_module(self.root, entry["path"], sources, invoke)
        return {"id": identifier, "version": entry["version"], "sha256": entry["sha256"], "result": result}

    def check(self, *, full=False):
        if type(full) is not bool:
            raise TypeError("full must be boolean")
        _verified(self.root, "catalog.json", self.catalog_sha256)
        paths = sorted(self._files)
        checked = []
        for path in paths:
            if not full and path.startswith(("search_queries/items/", "discovery/upstream/items/")):
                continue
            _verified(self.root, path, self._files[path])
            checked.append(path)
        return {"ok": True, "catalog_sha256": self.catalog_sha256, "counts": dict(self.counts),
                "files_checked": len(checked), "files_total": len(paths), "files_skipped": len(paths) - len(checked), "full": full}
