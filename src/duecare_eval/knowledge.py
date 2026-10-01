"""Read-only, target-safe knowledge projections for harnesses and MCP hosts.

The library takes a trusted checkout root at construction. Its operation edge
accepts catalog IDs and primitive choices, and reads no caller-selected paths.
Snapshots retain full visible narratives while keeping assessment keys private.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .contracts import canonical, loads_strict, text_hash
from .extensions import FILES, PLUGINS, build_payload, validate_pack

VERSION = "duecare-knowledge/1.0.0"
CATALOG_PATH = "examples/industry_packs/library.json"
SOURCE_PATH = "results/documented_indicator_sources_2026-10-01.json"
NARRATIVE_ROOT = "examples/narrative_indicators_v2"
MAX_PUBLIC_FILE_BYTES = 64 * 1024 * 1024


class KnowledgeError(ValueError):
    """A public operation fails its fixed ID, data or integrity contract."""


def _schema(properties=None, required=()):
    return {"type": "object", "properties": properties or {},
            "required": list(required), "additionalProperties": False}


_ID = {"type": "string", "minLength": 1}
_PROFILE = {"type": "string", "enum": sorted(PLUGINS), "default": "chat-messages"}
_SOURCES = {"type": "boolean", "default": False}
OPERATION_SCHEMAS = {
    "catalog": _schema(),
    "list_cases": _schema({"pack_id": _ID}, ["pack_id"]),
    "get_case_payload": _schema({"pack_id": _ID, "case_id": _ID,
        "profile": _PROFILE, "include_sources": _SOURCES}, ["pack_id", "case_id"]),
    "prepare_benchmark": _schema({"pack_id": _ID, "profile": _PROFILE,
        "include_sources": _SOURCES}, ["pack_id"]),
    "get_source": _schema({"source_id": _ID}, ["source_id"]),
    "get_rubric": _schema({"pack_id": _ID}, ["pack_id"]),
    "get_indicator": _schema({"indicator_id": _ID}, ["indicator_id"]),
    "get_action_template": _schema({"action_id": _ID}, ["action_id"]),
    "get_followup_template": _schema({"question_id": _ID}, ["question_id"]),
}


def describe_operations():
    """Return independent copies of the fixed typed edge for other engines."""
    return {"schema": VERSION, "operations": deepcopy(OPERATION_SCHEMAS),
            "effects": {"read_only": True, "network": False, "model_calls": 0,
                        "external_actions": False, "filesystem_writes": False}}


def _require(condition, message):
    if not condition:
        raise KnowledgeError(message)


def _safe_id(value, name):
    _require(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,119}", value),
             "invalid_" + name)
    return value


def validate_operation(operation, arguments=None):
    """Validate raw edge arguments before a transport can coerce their types."""
    _require(isinstance(operation, str) and operation in OPERATION_SCHEMAS, "unknown_operation")
    arguments = {} if arguments is None else arguments
    schema = OPERATION_SCHEMAS[operation]
    _require(type(arguments) is dict and set(schema["required"]) <= set(arguments)
             <= set(schema["properties"]), "operation_argument_fields")
    for key, value in arguments.items():
        rule = schema["properties"][key]
        expected = bool if rule["type"] == "boolean" else str
        _require(type(value) is expected, "operation_argument_type:" + key)
        if "enum" in rule:
            _require(value in rule["enum"], "operation_argument_choice:" + key)
        if expected is str:
            _require(bool(value), "operation_argument_empty:" + key)
    return arguments.copy()


class KnowledgeLibrary:
    """A verified, in-memory view of a reviewed public checkout.

    The construction path belongs to the local operator. Tool clients receive
    opaque record handles, visible-input digests and source provenance. Loading
    a new checkout creates a new snapshot; operations never mutate its files.
    """

    def __init__(self, public_root):
        supplied = Path(public_root).absolute()
        _require(supplied.is_dir(), "public_root_directory_required")
        # Reject symlinks even when they happen to point back inside the root.
        for part in (supplied, *supplied.parents):
            _require(not part.is_symlink(), "symlink_public_root_refused")
        self._root = supplied.resolve()
        self._packs = {}
        self._cases = {}
        index = self._json(CATALOG_PATH)
        _require(index.get("schema") == "duecare-industry-library/1.0.0", "library_schema")
        _require(isinstance(index.get("packs"), list) and index["packs"], "library_packs")
        for entry in index["packs"]:
            relative = entry.get("path") if isinstance(entry, dict) else None
            _require(isinstance(relative, str) and re.fullmatch(
                r"examples/industry_packs/[a-z][a-z0-9_-]*", relative), "pack_path_allowlist")
            manifest = self._json(relative + "/manifest.json")
            _require(manifest.get("files") == FILES, "fixed_pack_file_roles_required")
            pack = {"manifest": manifest}
            for role, name in FILES.items():
                raw = self._read_public(relative + "/" + name)
                _require(sha256(raw).hexdigest() == manifest.get("file_sha256", {}).get(role),
                         "pack_file_hash_mismatch:" + role)
                if role == "cases":
                    _require(raw.endswith(b"\n"), "cases_complete_line_required")
                    pack[role] = [loads_strict(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
                else:
                    pack[role] = loads_strict(raw.decode("utf-8"))
            validate_pack(pack)
            pack_id = manifest["pack_id"]
            _require(pack_id not in self._packs, "duplicate_pack_id")
            self._packs[pack_id] = pack
            handles = {}
            for case in pack["cases"]:
                visible = {key: case[key] for key in ("narrative", "user_question", "language")}
                handle = "case-" + text_hash(canonical(visible))
                _require(handle not in handles, "duplicate_visible_case")
                handles[handle] = case
            self._cases[pack_id] = handles

        # These hashes bind the previously released source packet and generic
        # templates. No reference file or private execution journal is loaded.
        narrative_manifest = self._json(NARRATIVE_ROOT + "/manifest.json")
        catalog_raw = self._read_public(NARRATIVE_ROOT + "/catalog.json")
        sources_raw = self._read_public(SOURCE_PATH)
        _require(sha256(catalog_raw).hexdigest() == narrative_manifest["files"]["catalog.json"]["sha256"],
                 "narrative_catalog_hash_mismatch")
        _require(sha256(sources_raw).hexdigest() == narrative_manifest["source_files"][SOURCE_PATH],
                 "source_packet_hash_mismatch")
        self._templates = loads_strict(catalog_raw.decode("utf-8"))
        crosswalk = loads_strict(sources_raw.decode("utf-8"))
        _require(crosswalk.get("schema") == "duecare-documented-indicator-crosswalk/1.0.0", "source_packet_schema")
        self._source_provenance = {"artifact": SOURCE_PATH, "sha256": sha256(sources_raw).hexdigest(),
            "schema": crosswalk["schema"], "reviewed_on": crosswalk["reviewed_on"],
            "relationship_to_benchmarks": crosswalk["relationship_to_benchmarks"]}
        self._template_provenance = {"artifact": NARRATIVE_ROOT + "/catalog.json",
            "sha256": sha256(catalog_raw).hexdigest(), "protocol": narrative_manifest["protocol"],
            "status": "authored_research_templates", "independent_human_validation": False}
        source_keys = ("id", "title", "date", "url", "location", "summary", "scope", "access_note")
        self._sources = {}
        for source in crosswalk["sources"]:
            identifier = _safe_id(source["id"], "source_id")
            _require(identifier not in self._sources, "duplicate_source_id")
            self._sources[identifier] = {key: source[key] for key in source_keys if key in source}

    def _read_public(self, relative):
        """Open allowlisted members without following intermediate or leaf links."""
        path = PurePosixPath(relative)
        _require(not path.is_absolute() and path.parts and all(p not in {".", ".."} for p in path.parts)
                 and "\\" not in relative and "\x00" not in relative, "invalid_public_member")
        allowed = (relative == CATALOG_PATH or relative == SOURCE_PATH
                   or relative in {NARRATIVE_ROOT + "/manifest.json", NARRATIVE_ROOT + "/catalog.json"}
                   or re.fullmatch(r"examples/industry_packs/[a-z][a-z0-9_-]*/(?:manifest\.json|cases\.jsonl|rubric\.json|questions\.json|sources\.json)", relative))
        _require(allowed, "public_member_not_allowlisted")
        for prefix in range(1, len(path.parts) + 1):
            _require(not self._root.joinpath(*path.parts[:prefix]).is_symlink(), "symlink_public_member_refused")
        file_path = self._root.joinpath(*path.parts)
        _require(file_path.resolve().is_relative_to(self._root), "public_member_escapes_root")
        descriptors = []
        try:
            if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
                descriptor = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                descriptors.append(descriptor)
                for part in path.parts[:-1]:
                    descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    descriptors.append(descriptor)
                fd = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            else:
                fd = os.open(file_path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
            descriptors.append(fd)
            info = os.fstat(fd)
            _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_PUBLIC_FILE_BYTES,
                     "public_member_regular_bounded_file_required")
            with os.fdopen(os.dup(fd), "rb") as stream:
                raw = stream.read(MAX_PUBLIC_FILE_BYTES + 1)
            _require(len(raw) <= MAX_PUBLIC_FILE_BYTES, "oversized_public_member")
            return raw
        except OSError as exc:
            raise KnowledgeError("public_member_unavailable") from exc
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _json(self, relative):
        return loads_strict(self._read_public(relative).decode("utf-8"))

    def _pack(self, pack_id):
        _safe_id(pack_id, "pack_id")
        _require(pack_id in self._packs, "unknown_pack_id")
        return self._packs[pack_id]

    def catalog(self):
        """Discover public materials with reference answers and labels withheld."""
        packs = []
        for pack_id, pack in sorted(self._packs.items()):
            manifest = pack["manifest"]
            packs.append({key: manifest[key] for key in ("pack_id", "version", "industry", "title")}
                         | {"case_count": len(pack["cases"]), "status": "prepared_research_inputs"})
        return {"schema": VERSION, "packs": packs, "profiles": sorted(PLUGINS),
            "sources": [{"id": s["id"], "title": s["title"]} for _, s in sorted(self._sources.items())],
            "indicator_ids": sorted(self._templates["indicators"]),
            "action_ids": sorted(self._templates["actions"]),
            "followup_ids": sorted(self._templates["followups"]),
            "scope": "Published research materials and offline input preparation. Model observations and assessments belong to separately recorded studies.",
            "model_calls_executed": 0, "independent_human_validation": False}

    def list_cases(self, pack_id):
        self._pack(pack_id)
        return {"schema": VERSION, "cases": [{"case_id": handle, "language": case["language"],
            "narrative_words": len(case["narrative"].split()), "question_count": len(case["question_ids"])}
            for handle, case in sorted(self._cases[pack_id].items())]}

    def get_case_payload(self, pack_id, case_id, profile="chat-messages", include_sources=False):
        pack = self._pack(pack_id)
        _safe_id(case_id, "case_id")
        _require(case_id in self._cases[pack_id], "unknown_case_id")
        _require(profile in PLUGINS, "unknown_profile")
        _require(type(include_sources) is bool, "include_sources_boolean")
        case = self._cases[pack_id][case_id]
        payload = build_payload(pack, case["case_id"], profile, include_sources=include_sources)
        if profile == "jsonl-batch":
            # The extension adapter binds its coordinator source ID into custom_id.
            # Replace that digest with one derived solely from the visible body.
            payload["custom_id"] = "DC-" + text_hash(canonical(payload["body"]))
        return {"schema": VERSION, "case_id": case_id, "profile": profile,
            "include_sources": include_sources, "payload": payload,
            "payload_sha256": text_hash(canonical(payload)), "model_calls_executed": 0}

    def prepare_benchmark(self, pack_id, profile="chat-messages", include_sources=False):
        """Prepare exact requests in memory; a caller separately owns execution."""
        self._pack(pack_id)
        records = [self.get_case_payload(pack_id, key, profile, include_sources)
                   for key in sorted(self._cases[pack_id])]
        return {"schema": VERSION, "status": "prepared", "prepared_requests": len(records),
            "model_calls_executed": 0, "records": records,
            "prepared_sha256": text_hash(canonical(records))}

    def get_source(self, source_id):
        _safe_id(source_id, "source_id")
        _require(source_id in self._sources, "unknown_source_id")
        return {"schema": VERSION, "source": deepcopy(self._sources[source_id]),
                "provenance": deepcopy(self._source_provenance)}

    def get_rubric(self, pack_id):
        rubric = self._pack(pack_id)["rubric"]
        return {"schema": VERSION, "rubric": deepcopy(rubric),
            "rubric_sha256": text_hash(canonical(rubric)),
            "scope": "Generic response-quality criteria; references and measured grades stay in the assessment layer.",
            "independent_human_validation": False}

    def _template(self, group, identifier):
        _safe_id(identifier, "template_id")
        _require(identifier in self._templates[group], "unknown_template_id")
        return deepcopy(self._templates[group][identifier])

    def get_indicator(self, indicator_id):
        indicator = self._template("indicators", indicator_id)
        return {"schema": VERSION, "indicator_id": indicator_id,
            "indicator": {key: indicator[key] for key in ("label", "definition", "ilo_section")},
            "source_ids": ["ILO_INDICATORS_2025_FULL"],
            "provenance": deepcopy(self._template_provenance),
            "scope": "A research indicator definition supports inquiry; an individual finding requires case-specific evidence and review."}

    def get_action_template(self, action_id):
        return {"schema": VERSION, "action_id": action_id,
            "text": self._template("actions", action_id),
            "provenance": deepcopy(self._template_provenance),
            "execution": "Suggested language only; the template performs zero external actions."}

    def get_followup_template(self, question_id):
        return {"schema": VERSION, "question_id": question_id,
            "text": self._template("followups", question_id),
            "provenance": deepcopy(self._template_provenance)}

    def dispatch(self, operation, arguments=None):
        """Use the fixed typed edge from an engine wrapper, with strict primitives."""
        arguments = validate_operation(operation, arguments)
        return getattr(self, operation)(**arguments)
