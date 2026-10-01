"""Offline candidate packages for Baltor's existing code and file contracts.

Export is an explicit filesystem operation. Discovery cards confer no rights,
admission, model access or execution authority. The optional Baltor probe checks
these wire records against the installed implementation, without importing
Baltor as a dependency of DueCare.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

from .contracts import canonical, loads_strict
from .knowledge import KnowledgeLibrary, OPERATION_SCHEMAS, VERSION as KNOWLEDGE_VERSION

VERSION = "duecare-baltor-candidate/1.0.0"
REQUEST_VERSION = "duecare-baltor-request/1.0.0"
RESULT_VERSION = "duecare-baltor-result/1.0.0"
PUBLIC_ORIGIN = "https://github.com/alisonjieli-png/duecare-eval.git"
PACK_NAMES = ("agriculture", "construction", "manufacturing", "hospitality", "maritime", "platform_delivery")
PACK_FILES = ("manifest.json", "cases.jsonl", "questions.json", "rubric.json", "sources.json")
SKILL_NAMES = ("duecare-author-industry-pack", "duecare-connect-harness", "duecare-review-evidence",
               "duecare-package-knowledge", "duecare-design-agent-evaluation")
# The dependency closure is explicit. In particular, neither runs/ nor full
# narrative cases/reference banks nor model output files are selected.
EXPORT_PATHS = tuple(sorted((
    "NOTICE.md", "src/duecare_eval/__init__.py", "src/duecare_eval/contracts.py",
    "src/duecare_eval/extensions.py", "src/duecare_eval/knowledge.py",
    "src/duecare_eval/mcp_server.py", "src/duecare_eval/baltor_bridge.py",
    "tools/run_duecare_mcp.py", "tools/export_baltor_candidate.py",
    "tools/check_extension_pack.py", "tools/create_extension_pack.py",
    "docs/EXTENDING_DUECARE.md", "docs/KNOWLEDGE_TRANSFER.md",
    "examples/industry_packs/library.json",
    "examples/narrative_indicators_v2/manifest.json",
    "examples/narrative_indicators_v2/catalog.json",
    "results/documented_indicator_sources_2026-10-01.json",
    "plugins/mcp-stdio.json",
    *("plugins/" + name + ".json" for name in ("jev-typed", "chat-messages", "jsonl-batch")),
    *("examples/industry_packs/" + name + "/" + member for name in PACK_NAMES for member in PACK_FILES),
    *("skills/" + name + "/" + member for name in SKILL_NAMES for member in ("SKILL.md", "agents/openai.yaml")),
)))
# These are the receiving CataloguePackage implementation's limits, not limits
# on DueCare research or the number of generated/admitted knowledge items.
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PACKAGE_BYTES = 32 * 1024 * 1024
RECEIVING_CONSTRAINTS = {
    "contract": "catalogue_package/v1",
    "implementation": "loop_engine.core.service_runtime.catalogue_packages",
    "symbols": {"MAXIMUM_FILE_BYTES": MAX_FILE_BYTES, "MAXIMUM_PACKAGE_BYTES": MAX_PACKAGE_BYTES,
                "MAXIMUM_PATH_DEPTH": 8, "MAXIMUM_PATH_CHARACTERS": 200},
    "scope": "Receiving Baltor file-package compatibility only; not research generation or daily usage limits."}
ROOT_DOCUMENTS = ("candidate.json", "package.json", "code-assets.json", "operation-contracts.json")


class BridgeError(ValueError):
    """A candidate export or typed operation does not meet its contract."""


def _require(condition, reason):
    if not condition:
        raise BridgeError(reason)


def _digest(raw):
    return sha256(raw).hexdigest()


def _json_bytes(value):
    return canonical(value).encode("utf-8")


def _member(value):
    _require(isinstance(value, str) and value and len(value) <= 200 and "\\" not in value, "unsafe_member")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and str(path) == value and len(path.parts) <= 8
             and all(re.fullmatch(r"[A-Za-z0-9._@+-]{1,100}", part)
                     and part not in {".", ".."} and part.casefold() != ".git" for part in path.parts),
             "unsafe_member")
    return path.parts


def _root(value):
    path = Path(value).absolute()
    _require(path.is_dir() and path == path.resolve(), "root_requires_existing_unlinked_directory")
    _require(all(not member.is_symlink() for member in (path, *path.parents)), "symlink_root_refused")
    return path


def _read(root, relative):
    """Bounded regular-file read with no followed links, including directories."""
    parts = _member(relative)
    _require(all(not root.joinpath(*parts[:n]).is_symlink() for n in range(1, len(parts) + 1)),
             "symlink_member_refused")
    descriptors = []
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptors.append(descriptor)
            for part in parts[:-1]:
                descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                descriptors.append(descriptor)
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
        else:
            fd = os.open(root.joinpath(*parts), os.O_RDONLY)
        descriptors.append(fd)
        info = os.fstat(fd)
        _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES, "regular_bounded_file_required")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        _require(len(raw) <= MAX_FILE_BYTES, "oversized_member")
        return raw
    except OSError as exc:
        raise BridgeError("export_member_unavailable:" + relative) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _git(root, *arguments):
    result = subprocess.run(["git", "-C", str(root), *arguments], check=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    _require(result.returncode == 0, "public_git_identity_required")
    return result.stdout.decode("utf-8").strip()


def _canonical_public_origin(value):
    """Recognize only ordinary clone URLs for the one public repository.

    HTTPS and SSH may name their default port explicitly. No other host,
    repository, userinfo, port, query, fragment or encoded path is accepted.
    Refusal messages deliberately omit the supplied URL, which may be secret.
    """
    _require(type(value) is str and re.fullmatch(
        r"(?:https://github\.com(?::443)?/|ssh://git@github\.com(?::22)?/|git@github\.com:)"
        r"alisonjieli-png/duecare-eval(?:\.git)?", value) is not None,
        "public_origin_required")
    return PUBLIC_ORIGIN


def _source_state(root):
    _require(Path(_git(root, "rev-parse", "--show-toplevel")).resolve() == root,
             "independent_public_checkout_required")
    origin = _canonical_public_origin(_git(root, "remote", "get-url", "origin"))
    project = _read(root, "pyproject.toml").decode("utf-8")
    _require(re.search(r'^name\s*=\s*"duecare-eval-public"\s*$', project, re.M), "public_project_required")
    revision = _git(root, "rev-parse", "HEAD")
    _require(re.fullmatch(r"[0-9a-f]{40,64}", revision), "source_revision_required")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {"repository": origin, "base_commit": revision,
            "worktree_dirty": bool(status), "worktree_status_sha256": _digest(status.encode()),
            "content_binding": "exact_exported_file_hashes"}


def _matches_commit(root, revision, blobs):
    # A clean porcelain status can hide ignored or assume-unchanged files.
    # Compare the exact allowlisted blobs rather than inferring this claim.
    for name, raw in blobs.items():
        result = subprocess.run(["git", "-C", str(root), "cat-file", "blob", revision + ":" + name],
                                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode != 0 or result.stdout != raw:
            return False
    return True


def operation_contracts():
    """Versioned edges for the same preloaded operations exposed through MCP."""
    operations = []
    for name, arguments in sorted(OPERATION_SCHEMAS.items()):
        operations.append({"name": name, "version": "1.0.0", "effects": ["pure"],
            "entrypoint": "duecare_eval.baltor_bridge.PreloadedOperations.invoke",
            "input_contract": REQUEST_VERSION + "#" + name,
            "output_contract": RESULT_VERSION + "#" + name,
            "input_schema": {"type": "object", "properties": {
                "schema": {"const": REQUEST_VERSION}, "operation": {"const": name},
                "arguments": deepcopy(arguments)},
                "required": ["schema", "operation", "arguments"], "additionalProperties": False},
            "output_schema": {"type": "object", "properties": {
                "schema": {"const": RESULT_VERSION}, "operation": {"const": name},
                "request_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "result_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "result": {"type": "object", "properties": {"schema": {"const": KNOWLEDGE_VERSION}},
                           "required": ["schema"]}},
                "required": ["schema", "operation", "request_sha256", "result_sha256", "result"],
                "additionalProperties": False}})
    return {"schema": "duecare-baltor-operation-contracts/1.0.0", "operations": operations,
            "preload_effects": ["reads_fs"], "stdio_launch_effects": ["spawns_process"],
            "admission": "candidate_only", "model_calls_executed": 0}


class PreloadedOperations:
    """Pure operation calls over an explicitly loaded, fixed public snapshot."""

    def __init__(self, library):
        _require(isinstance(library, KnowledgeLibrary), "preloaded_knowledge_library_required")
        self._library = library

    @classmethod
    def from_public_root(cls, root):
        """Explicit local reads; this constructor is not a pure tool operation."""
        return cls(KnowledgeLibrary(root))

    def invoke(self, request):
        _require(type(request) is dict and set(request) == {"schema", "operation", "arguments"},
                 "operation_envelope_fields")
        _require(request["schema"] == REQUEST_VERSION, "unsupported_operation_version")
        _require(type(request["arguments"]) is dict, "operation_arguments_object")
        # JSON round trip prevents a caller's nested objects being retained.
        frozen = loads_strict(canonical(request))
        result = self._library.dispatch(frozen["operation"], frozen["arguments"])
        return {"schema": RESULT_VERSION, "operation": frozen["operation"],
                "request_sha256": _digest(_json_bytes(frozen)),
                "result_sha256": _digest(_json_bytes(result)), "result": result}


def _file_record(name, raw):
    role = "executable_tool" if name.endswith(".py") else "configuration" if name.startswith("plugins/") else "other"
    if name.startswith("skills/"):
        role = "skill_definition" if name.endswith("/SKILL.md") else "configuration"
    elif name.startswith("docs/"):
        role = "skill_reference"
    if name == "plugins/mcp-stdio.json":
        role = "protocol_server_configuration"
    media = "text/x-python" if name.endswith(".py") else "text/markdown" if name.endswith(".md") else "application/x-ndjson" if name.endswith(".jsonl") else "application/yaml" if name.endswith(".yaml") else "application/json"
    return {"path": name, "digest": _digest(raw), "size_bytes": len(raw), "media_type": media, "role": role}


def _file_counts(files):
    return {"file_placements": len(files),
            "distinct_file_digests": len({entry["digest"] for entry in files}),
            "file_count_scope": "Package file inventory only; candidate metadata documents are excluded."}


def _asset(package, source, notice_digest):
    """CodeAssetSpec/v2 projection; its actual reader is checked separately."""
    package_raw = _json_bytes({"record_type": "catalogue_package/v1", "files": package["files"]})
    body_ref = {"uri": "duecare-candidate:sha256/" + _digest(package_raw), "digest": _digest(package_raw),
                "size_bytes": len(package_raw), "media_type": "application/json", "storage": "external", "immutable": True}
    value = {"record_type": "code_asset_spec/v2", "asset_id": "duecare.knowledge.operations",
        "name": "DueCare research knowledge operations",
        "description": "Prepare research inputs and retrieve scoped source material from a fixed public snapshot.",
        "asset_kind": "module", "source_kind": "git", "body_ref": body_ref,
        "entrypoints": ["duecare_eval.baltor_bridge.PreloadedOperations.invoke"],
        "modes": ["deterministic"], "input_contract": REQUEST_VERSION, "output_contract": RESULT_VERSION,
        "effects": ["pure"], "dependencies": ["python>=3.11", "duecare_eval.knowledge.KnowledgeLibrary"],
        "data_refs": [], "file_count": len(package["files"]), "line_count": 0,
        "load_strategy": "manifest_then_select", "template_id": "multi_file_module", "version": "1.0.0",
        "license": "unknown", "lifecycle": "candidate", "admission_ref": "",
        "metadata": {"source": source, "notice_sha256": notice_digest,
                     "rights_state": "permission_required", "preload_effects": ["reads_fs"],
                     "entrypoint_requires_preloaded_snapshot": True,
                     "validation_scope": "Compatibility candidate; no independent admission or semantic validation."},
        "qualification_version": "code_asset_qualification/v2"}
    stable = {"asset_id": value["asset_id"], "version": value["version"], "body_digest": body_ref["digest"],
        "entrypoints": value["entrypoints"], "modes": value["modes"],
        "dependency_digest": _digest(_json_bytes(value["dependencies"])),
        "contract_digest": _digest(_json_bytes({"input_contract": value["input_contract"], "output_contract": value["output_contract"]})),
        "effect_digest": _digest(_json_bytes(value["effects"])), "load_strategy": value["load_strategy"],
        "qualification_version": value["qualification_version"], "data_refs": value["data_refs"]}
    card = {key: item for key, item in value.items() if key not in {"record_type", "input_contract", "output_contract"}}
    card["contracts"] = [value["input_contract"], value["output_contract"]]
    # Baltor's card digest intentionally uses its existing spaced JSON form.
    value["card_digest"] = _digest(json.dumps(card, sort_keys=True).encode())
    value["qualification_digest"] = _digest(_json_bytes(stable))
    return value


def export_candidate(source_root, destination, *, captured_at=None):
    """Write one fresh candidate directory from the independent public checkout.

    No file outside EXPORT_PATHS is copied. Git metadata and pyproject.toml
    establish identity only. Source changes during capture refuse the export.
    The output is not a catalogue release bundle and contains no approval.
    """
    root = _root(source_root)
    output = Path(destination).absolute()
    _require(not output.exists() and not output.is_symlink(), "destination_already_exists")
    _require(".." not in output.parts, "destination_path_traversal")
    parent = _root(output.parent)
    _require(not output.is_relative_to(root) and not root.is_relative_to(output), "destination_overlaps_source")
    before = _source_state(root)
    blobs = {name: _read(root, name) for name in EXPORT_PATHS}
    _require(sum(map(len, blobs.values())) <= MAX_PACKAGE_BYTES, "package_too_large")
    matches_base = _matches_commit(root, before["base_commit"], blobs)
    # Load only the knowledge closure and verify its existing manifest hashes.
    KnowledgeLibrary(root)
    _require(before == _source_state(root) and all(_read(root, name) == raw for name, raw in blobs.items()),
             "source_changed_during_capture")
    timestamp = captured_at or datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BridgeError("capture_time_requires_utc") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "capture_time_requires_utc")
    package = {"body_form": "package", "files": [_file_record(name, raw) for name, raw in blobs.items()]}
    package_document = _json_bytes({"record_type": "catalogue_package/v1", "files": package["files"]})
    snapshot_digest = _digest(package_document)
    source = {**before, "captured_at": timestamp, "exported_files_sha256": snapshot_digest,
              "base_commit_is_exported_tree": matches_base}
    contracts = operation_contracts()
    assets = [_asset(package, source, _digest(blobs["NOTICE.md"]))]
    candidate = {"schema": VERSION, "lifecycle": "candidate", "admitted": False, "served": False,
        "source": source, "rights": {"license": "unknown", "reuse_permission": "unresolved",
            "notice_path": "NOTICE.md", "notice_sha256": _digest(blobs["NOTICE.md"]),
            "third_party_rights": "Each cited source retains its own rights and terms."},
        "package": package, "package_sha256": snapshot_digest, **_file_counts(package["files"]),
        "code_assets_sha256": _digest(_json_bytes(assets)), "operation_contracts_sha256": _digest(_json_bytes(contracts)),
        "dependency_profile": {"core": ["python>=3.11"], "optional_stdio": ["mcp==2.2.0"],
            "bootstrap": "Set PYTHONPATH to files/src and load KnowledgeLibrary from files/.",
            "stdio_bootstrap": "From the candidate root, install mcp==2.2.0 into an operator-chosen Python environment, then run python3 files/tools/run_duecare_mcp.py --public-root files.",
            "guide": "files/docs/KNOWLEDGE_TRANSFER.md",
            "effects": {"preload": ["reads_fs"], "operations": ["pure"],
                        "stdio_launch": ["spawns_process"], "export_cli": ["reads_fs", "writes_fs", "spawns_process"]}},
        "receiving_constraints": deepcopy(RECEIVING_CONSTRAINTS),
        "full_bundle_contains_evaluator_references": True,
        "coordinator_only_fixture_files": ["examples/industry_packs/" + name + "/cases.jsonl" for name in PACK_NAMES],
        "target_input": "payload_only",
        "assessment_boundary": "The full candidate contains public evaluator references. Target-model access uses only the operation projections, never the candidate file tree.",
        "model_calls_executed": 0, "independent_human_validation": False,
        "validation_scope": "Exact public file capture and offline interoperability. Not a grant of rights, independent admission, hosted publication or benchmark performance."}
    # Parent is resolved and link-free; exclusive mkdir preserves an existing
    # destination if a competing exporter wins this name.
    try:
        (parent / output.name).mkdir(mode=0o700)
    except FileExistsError as exc:
        raise BridgeError("destination_already_exists") from exc
    for name, raw in blobs.items():
        target = output / "files" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
    for name, value in (("candidate.json", candidate), ("package.json", package),
                        ("code-assets.json", assets), ("operation-contracts.json", contracts)):
        with (output / name).open("xb") as stream:
            stream.write(_json_bytes(value))
    return validate_candidate(output)


def validate_candidate(directory):
    """Rehash an exported allowlisted closure without executing its code."""
    root = _root(directory)
    candidate = loads_strict(_read(root, "candidate.json").decode())
    _require(candidate.get("schema") == VERSION and candidate.get("lifecycle") == "candidate"
             and candidate.get("admitted") is False and candidate.get("served") is False, "candidate_only_required")
    _require(candidate.get("full_bundle_contains_evaluator_references") is True
             and candidate.get("target_input") == "payload_only"
             and candidate.get("coordinator_only_fixture_files") == ["examples/industry_packs/" + name + "/cases.jsonl" for name in PACK_NAMES],
             "evaluator_reference_boundary_required")
    _require(candidate.get("receiving_constraints") == RECEIVING_CONSTRAINTS, "receiving_constraints_mismatch")
    _require(set(candidate.get("rights", {})) == {"license", "reuse_permission", "notice_path", "notice_sha256", "third_party_rights"}
             and candidate["rights"]["license"] == "unknown"
             and candidate["rights"]["reuse_permission"] == "unresolved", "rights_state_required")
    package = loads_strict(_read(root, "package.json").decode())
    _require(package == candidate.get("package") and set(package) == {"body_form", "files"}
             and package["body_form"] == "package", "package_manifest_mismatch")
    files = package["files"]
    _require(type(files) is list and all(type(entry) is dict for entry in files)
             and [entry.get("path") for entry in files] == list(EXPORT_PATHS), "exact_allowlist_required")
    expected_paths = set(ROOT_DOCUMENTS) | {"files/" + name for name in EXPORT_PATHS}
    actual_paths = set()
    for parent, directories, members in os.walk(root, followlinks=False):
        for name in directories + members:
            path = Path(parent) / name
            _require(not path.is_symlink(), "symlink_member_refused")
        actual_paths.update((Path(parent) / name).relative_to(root).as_posix() for name in members)
    _require(actual_paths == expected_paths, "unexpected_candidate_files")
    for entry in files:
        raw = _read(root, "files/" + entry["path"])
        _require(entry == _file_record(entry["path"], raw), "package_file_identity_mismatch")
    counts = _file_counts(files)
    _require(all(candidate.get(key) == value for key, value in counts.items()), "package_file_counts_mismatch")
    package_digest = _digest(_json_bytes({"record_type": "catalogue_package/v1", "files": files}))
    _require(package_digest == candidate["package_sha256"] == candidate["source"]["exported_files_sha256"], "package_digest_mismatch")
    _require(candidate["rights"]["notice_path"] == "NOTICE.md"
             and candidate["rights"]["notice_sha256"] == _digest(_read(root, "files/NOTICE.md")), "notice_fingerprint_mismatch")
    assets = loads_strict(_read(root, "code-assets.json").decode())
    _require(assets == [_asset(package, candidate["source"], candidate["rights"]["notice_sha256"])], "code_asset_projection_mismatch")
    _require(_digest(_json_bytes(assets)) == candidate["code_assets_sha256"], "code_asset_digest_mismatch")
    contracts = loads_strict(_read(root, "operation-contracts.json").decode())
    _require(contracts == operation_contracts() and _digest(_json_bytes(contracts)) == candidate["operation_contracts_sha256"], "operation_contract_mismatch")
    return {"schema": VERSION, "lifecycle": "candidate", "files_verified": len(files), **counts,
            "package_sha256": package_digest, "source": candidate["source"],
            "rights": candidate["rights"], "model_calls_executed": 0, "admitted": False, "served": False}
