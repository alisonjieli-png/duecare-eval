"""Discover pinned public GitHub file metadata without fetching file bodies.

Only the explicit harvest command uses the network. Discovered references are
unreviewed and uninstalled; local integrity checks preserve those distinctions.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote

VERSION = "harness-upstream-discovery/1.0.0"
DEFAULT_REPOSITORIES = ("github/awesome-copilot", "openai/skills", "anthropics/skills", "microsoft/skills")
KINDS = {"skill", "instructions", "agent", "prompt", "helper_script"}
GIT_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
ITEM_FIELDS = {"type", "id", "title", "upstream_kind", "repository", "commit", "tree_sha", "blob_git_sha", "size", "path", "source_url", "status", "installed", "verified", "license_scope"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def repository_name(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value) is not None, "invalid_repository_name")
    require(all(part not in {".", ".."} for part in value.split("/")), "invalid_repository_name")
    return value.lower()


def git_sha(value):
    require(isinstance(value, str) and GIT_SHA.fullmatch(value) is not None, "invalid_git_object_sha")
    return value


def git_path(value, *, immediate=False):
    require(isinstance(value, str) and value and "\\" not in value and not any(ord(char) < 32 or ord(char) == 127 for char in value), "invalid_git_path")
    parsed = PurePosixPath(value)
    require(not parsed.is_absolute() and parsed.as_posix() == value and all(part not in {".", ".."} for part in parsed.parts), "unsafe_git_path")
    require(not immediate or len(parsed.parts) == 1, "nonrecursive_tree_entry_requires_basename")
    return value


class ApiFailure(RuntimeError):
    def __init__(self, code, *, http_status=None, returncode=None, stderr_sha256=None):
        super().__init__(code)
        self.details = {"error_code": code, "http_status": http_status, "returncode": returncode}
        if stderr_sha256 is not None:
            self.details["stderr_sha256"] = stderr_sha256


class GhApi:
    """Read-only fixed-host transport. Raw stderr and API error bodies stay out."""
    def __init__(self, runner=subprocess.run, timeout=120):
        self.runner, self.timeout = runner, timeout
        self.calls = []

    def __call__(self, endpoint):
        require(re.fullmatch(r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:commits/main|git/trees/[0-9a-f]+(?:\?recursive=1)?)", endpoint) is not None, "metadata_endpoint_allowlist")
        command = ["gh", "api", "--hostname", "github.com", "--method", "GET", "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2026-03-10", endpoint]
        call = {"endpoint": endpoint, "started_at": now(), "method": "GET"}
        self.calls.append(call)
        try:
            result = self.runner(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired:
            failure = ApiFailure("api_cli_timeout")
            call.update(status="error", **failure.details); raise failure from None
        except OSError:
            failure = ApiFailure("api_cli_unavailable")
            call.update(status="error", **failure.details); raise failure from None
        call["finished_at"] = now()
        if result.returncode:
            # Extract only the three-digit status; never return command stderr.
            match = re.search(r"\bHTTP\s+(\d{3})\b", result.stderr or "")
            failure = ApiFailure("api_cli_error", http_status=int(match.group(1)) if match else None,
                                 returncode=result.returncode, stderr_sha256=sha256((result.stderr or "").encode()).hexdigest())
            call.update(status="error", **failure.details); raise failure
        try:
            value = json.loads(result.stdout)
            require(isinstance(value, dict), "api_object_required")
        except (ValueError, TypeError):
            failure = ApiFailure("invalid_api_json")
            call.update(status="error", **failure.details); raise failure from None
        call.update(status="completed", response_json_sha256=sha256(result.stdout.encode()).hexdigest())
        return value


def parse_commit(body):
    require(isinstance(body, dict), "commit_object_required")
    try:
        commit, tree = git_sha(body["sha"]), git_sha(body["commit"]["tree"]["sha"])
    except (KeyError, TypeError):
        raise ValueError("commit_tree_binding_missing") from None
    return commit, tree


def parse_tree(body, expected_sha, *, immediate=False):
    require(isinstance(body, dict) and body.get("sha") == expected_sha, "tree_sha_binding_mismatch")
    require(type(body.get("truncated")) is bool and isinstance(body.get("tree"), list), "tree_population_contract")
    entries = {}
    for value in body["tree"]:
        require(isinstance(value, dict), "tree_entry_object_required")
        path = git_path(value.get("path"), immediate=immediate)
        kind, mode = value.get("type"), value.get("mode")
        require(kind in {"blob", "tree", "commit"} and mode in {"100644", "100755", "040000", "160000", "120000"}, "tree_entry_kind_or_mode")
        require((kind == "tree" and mode == "040000") or (kind == "commit" and mode == "160000") or (kind == "blob" and mode in {"100644", "100755", "120000"}), "inconsistent_tree_kind_and_mode")
        entry = {"path": path, "type": kind, "mode": mode, "sha": git_sha(value.get("sha"))}
        if kind == "blob":
            require(type(value.get("size")) is int and value["size"] >= 0, "blob_size_required")
            entry["size"] = value["size"]
        require(path not in entries or entries[path] == entry, "conflicting_tree_entry")
        entries[path] = entry
    return entries, body["truncated"]


def collect_tree(api, repository, tree_sha):
    """Use a full recursive response, recovering truncated trees by subtrees.

    Every subtree is pinned by its Git tree SHA. Incomplete or failed branches
    remain coverage errors; already observed metadata stays a partial inventory.
    """
    endpoint = f"repos/{repository}/git/trees/{tree_sha}"
    entries, truncated = parse_tree(api(endpoint + "?recursive=1"), tree_sha)
    coverage = {"root_recursive_truncated": truncated, "tree_complete": not truncated,
                "traversal": "recursive", "coverage_errors": []}
    if not truncated:
        return entries, coverage
    coverage["traversal"] = "recursive_then_pinned_subtree_recovery"
    queue, cache = [("", tree_sha, ())], {}
    while queue:
        prefix, current_sha, ancestors = queue.pop()
        if current_sha in ancestors:
            coverage["coverage_errors"].append({"code": "tree_cycle_detected", "tree_sha": current_sha}); continue
        try:
            if current_sha not in cache:
                cache[current_sha] = parse_tree(api(f"repos/{repository}/git/trees/{current_sha}"), current_sha, immediate=True)
            children, partial = cache[current_sha]
            if partial:
                coverage["coverage_errors"].append({"code": "nonrecursive_tree_truncated", "tree_sha": current_sha})
            for name, child in children.items():
                path = prefix + name
                item = {**child, "path": path}
                require(path not in entries or entries[path] == item, "conflicting_pinned_tree_metadata")
                entries[path] = item
                if child["type"] == "tree":
                    queue.append((path + "/", child["sha"], ancestors + (current_sha,)))
        except ApiFailure as error:
            coverage["coverage_errors"].append({"code": "subtree_api_error", "tree_sha": current_sha, **error.details})
        except (ValueError, KeyError, TypeError):
            coverage["coverage_errors"].append({"code": "invalid_subtree_metadata", "tree_sha": current_sha})
    coverage["tree_complete"] = not coverage["coverage_errors"]
    return entries, coverage


def classify_files(entries):
    regular = {path: row for path, row in entries.items() if row["type"] == "blob" and row["mode"] in {"100644", "100755"}}
    roots = [PurePosixPath(path).parent for path in regular if PurePosixPath(path).name == "SKILL.md"]
    selected = []
    for path, row in sorted(regular.items()):
        parsed = PurePosixPath(path); name = parsed.name; kind = None
        if name == "SKILL.md": kind = "skill"
        elif name.endswith(".instructions.md"): kind = "instructions"
        elif name.endswith(".agent.md"): kind = "agent"
        elif name.endswith(".prompt.md"): kind = "prompt"
        elif parsed.suffix in {".py", ".js", ".ts"} and not name.endswith(".d.ts"):
            if not {"node_modules", ".git", "vendor"} & set(parsed.parts) and any(root == PurePosixPath(".") or root in parsed.parents for root in roots):
                kind = "helper_script"
        if kind:
            selected.append((kind, row))
    return selected


def make_reference(repository, commit, tree_sha, kind, entry):
    path = entry["path"]; parsed = PurePosixPath(path)
    if kind == "skill": title = parsed.parent.name or repository.split("/")[-1]
    elif kind == "helper_script": title = parsed.stem
    else:
        suffix = {"instructions": ".instructions.md", "agent": ".agent.md", "prompt": ".prompt.md"}[kind]
        title = parsed.name[:-len(suffix)]
    digest = sha256(canonical({"repository": repository, "path": path, "commit": commit}).encode()).hexdigest()
    return {"type": "upstream_reference", "id": "upstream." + digest, "title": title,
        "upstream_kind": kind, "repository": repository, "commit": commit, "tree_sha": tree_sha,
        "blob_git_sha": entry["sha"], "size": entry["size"], "path": path,
        "source_url": f"https://github.com/{repository}/blob/{commit}/{quote(path, safe='/')}",
        "status": "discovered_unreviewed", "installed": False, "verified": False, "license_scope": "unreviewed"}


def discover_repository(repository, api):
    repository = repository_name(repository)
    before = len(getattr(api, "calls", []))
    record = {"repository": repository, "requested_ref": "main", "commit": None, "tree_sha": None,
              "status": "unattempted", "tree_complete": False, "selected_references": 0, "counts_by_kind": {}, "coverage_errors": []}
    try:
        commit, tree_sha = parse_commit(api(f"repos/{repository}/commits/main"))
        record.update(commit=commit, tree_sha=tree_sha)
        entries, coverage = collect_tree(api, repository, tree_sha)
        selected = classify_files(entries)
        references = [make_reference(repository, commit, tree_sha, kind, entry) for kind, entry in selected]
        record.update(coverage, status="complete_metadata" if coverage["tree_complete"] else "partial_metadata",
                      tree_entries_observed=len(entries), regular_blobs_observed=sum(row["type"] == "blob" and row["mode"] in {"100644", "100755"} for row in entries.values()),
                      symlinks_excluded=sum(row["mode"] == "120000" for row in entries.values()),
                      submodules_excluded=sum(row["type"] == "commit" for row in entries.values()),
                      selected_references=len(references), counts_by_kind=dict(sorted(Counter(row["upstream_kind"] for row in references).items())))
    except ApiFailure as error:
        record.update(status="api_error", coverage_errors=[error.details]); references = []
    except (ValueError, KeyError, TypeError):
        record.update(status="invalid_metadata", coverage_errors=[{"error_code": "metadata_contract_failed"}]); references = []
    record["api_calls"] = list(getattr(api, "calls", []))[before:]
    return references, record


def fresh_directory(path):
    path = Path(path)
    require(not path.is_symlink() and (not path.exists() or path.is_dir() and not any(path.iterdir())), "fresh_empty_output_directory_required")
    return path


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def harvest(output, repositories=DEFAULT_REPOSITORIES, *, api=None):
    output = fresh_directory(output)
    repositories = [repository_name(value) for value in repositories]
    require(repositories and len(repositories) == len(set(repositories)), "distinct_repository_population_required")
    api = api if api is not None else GhApi()
    started = now(); references, coverage = [], []
    for repository in repositories:
        rows, receipt = discover_repository(repository, api)
        references.extend(rows); coverage.append(receipt)
    references.sort(key=lambda row: (row["repository"], row["path"]))
    require(len({row["id"] for row in references}) == len(references), "duplicate_reference_identity")
    # Recheck before writing after potentially long metadata retrieval. Existing
    # snapshots remain unchanged even if another process created this directory.
    fresh_directory(output); output.mkdir(parents=True, exist_ok=True)
    (output / "items").mkdir()
    catalog = []
    for item in references:
        name = "items/" + item["id"].split(".", 1)[1] + ".json"
        data = (canonical(item) + "\n").encode()
        write_new(output / name, data)
        catalog.append({**item, "payload_path": name, "payload_sha256": sha256(data).hexdigest()})
    catalog_bytes = "".join(canonical(row) + "\n" for row in catalog).encode()
    write_new(output / "catalog.jsonl", catalog_bytes)
    inventory = {"schema": VERSION, "started_at": started, "captured_at": now(), "repositories_requested": repositories,
        "repositories": coverage, "repositories_complete": sum(row["tree_complete"] for row in coverage),
        "references_discovered": len(catalog), "counts_by_kind": dict(sorted(Counter(row["upstream_kind"] for row in catalog).items())),
        "catalog_sha256": sha256(catalog_bytes).hexdigest(), "item_files": len(catalog),
        "api_cli_invocations": len(getattr(api, "calls", [])),
        "api_request_scope": "Recorded gh api invocations; internal HTTP redirects or retries are not independently counted.",
        "third_party_file_bodies_fetched": 0, "upstream_code_executed": 0, "skills_installed": 0, "model_calls": 0,
        "rights_status": "File-level rights and reuse permission remain unreviewed. Repository visibility supplies discovery metadata only.",
        "selection_scope": "SKILL.md, instruction/agent/prompt Markdown and .py/.js/.ts helpers beneath an observed skill folder; declaration-only .d.ts files, vendored dependencies, symlinks and submodules are excluded.",
        "coverage_scope": "Counts refer to distinct pinned file references, not reviewed capabilities. Any failed or truncated unrecovered tree remains explicitly incomplete.",
        "api_documentation": ["https://docs.github.com/en/rest/commits/commits#get-a-commit", "https://docs.github.com/en/rest/git/trees#get-a-tree"]}
    write_new(output / "inventory.json", (canonical(inventory) + "\n").encode())
    return inventory


def validate_reference(item):
    require(isinstance(item, dict) and set(item) == ITEM_FIELDS, "reference_metadata_allowlist")
    repository = repository_name(item["repository"]); path = git_path(item["path"])
    require(repository == item["repository"], "repository_canonical_case")
    for field in ("commit", "tree_sha", "blob_git_sha"): git_sha(item[field])
    require(item["type"] == "upstream_reference" and item["upstream_kind"] in KINDS, "reference_kind")
    require(type(item["size"]) is int and item["size"] >= 0 and isinstance(item["title"], str), "reference_size_or_title")
    require(item["status"] == "discovered_unreviewed" and item["installed"] is False and item["verified"] is False and item["license_scope"] == "unreviewed", "discovery_cannot_claim_installation_validation_or_rights")
    expected = sha256(canonical({"repository": repository, "path": path, "commit": item["commit"]}).encode()).hexdigest()
    require(item["id"] == "upstream." + expected, "reference_identity_binding")
    require(item["source_url"] == f"https://github.com/{repository}/blob/{item['commit']}/{quote(path, safe='/')}", "commit_pinned_source_url_required")


def check(output):
    output = Path(output).resolve()
    inventory_path, catalog_path = output / "inventory.json", output / "catalog.jsonl"
    require(not inventory_path.is_symlink() and not catalog_path.is_symlink(), "metadata_symlinks_refused")
    inventory = json.loads(inventory_path.read_text()); raw = catalog_path.read_bytes()
    require(inventory["schema"] == VERSION and sha256(raw).hexdigest() == inventory["catalog_sha256"], "catalog_hash_binding")
    require({p.name for p in output.iterdir()} == {"catalog.jsonl", "inventory.json", "items"}, "unexpected_snapshot_file")
    require((output / "items").is_dir() and not (output / "items").is_symlink(), "items_directory_required")
    require(all(type(inventory.get(field)) is int and inventory[field] == 0 for field in ("third_party_file_bodies_fetched", "upstream_code_executed", "skills_installed", "model_calls")), "metadata_only_capture_required")
    require(not raw or raw.endswith(b"\n"), "catalog_complete_lines_required")
    catalog = [json.loads(line) for line in raw.splitlines() if line.strip()]
    seen = set()
    for row in catalog:
        require(set(row) == ITEM_FIELDS | {"payload_path", "payload_sha256"}, "catalog_row_allowlist")
        item = {key: row[key] for key in ITEM_FIELDS}; validate_reference(item)
        require(row["id"] not in seen, "duplicate_catalog_id"); seen.add(row["id"])
        expected_path = "items/" + row["id"].split(".", 1)[1] + ".json"
        require(row["payload_path"] == expected_path, "item_path_binding")
        path = output / expected_path
        require(not path.is_symlink() and path.resolve().is_relative_to(output), "item_path_escape")
        data = path.read_bytes()
        require(sha256(data).hexdigest() == row["payload_sha256"] and json.loads(data) == item, "item_hash_or_metadata_binding")
    require(len(catalog) == inventory["references_discovered"] == inventory["item_files"], "inventory_population")
    require(dict(sorted(Counter(row["upstream_kind"] for row in catalog).items())) == inventory["counts_by_kind"], "inventory_kind_counts")
    require({p.name for p in (output / "items").iterdir()} == {row["payload_path"].split("/", 1)[1] for row in catalog}, "item_directory_population")
    repositories = inventory["repositories"]
    require(isinstance(repositories, list) and [row["repository"] for row in repositories] == inventory["repositories_requested"] and len({row["repository"] for row in repositories}) == len(repositories), "repository_population_binding")
    require(set(row["repository"] for row in catalog) <= set(inventory["repositories_requested"]), "unknown_catalog_repository")
    for repository in repositories:
        selected = [row for row in catalog if row["repository"] == repository["repository"]]
        require(type(repository["tree_complete"]) is bool and repository["status"] in {"complete_metadata", "partial_metadata", "api_error", "invalid_metadata"}, "repository_coverage_status")
        require(repository["tree_complete"] == (repository["status"] == "complete_metadata"), "repository_completion_claim")
        require(not repository["tree_complete"] or not repository["coverage_errors"], "complete_tree_has_coverage_error")
        require(len(selected) == repository["selected_references"] and dict(sorted(Counter(row["upstream_kind"] for row in selected).items())) == repository["counts_by_kind"], "repository_selected_counts")
        require(all(row["commit"] == repository["commit"] and row["tree_sha"] == repository["tree_sha"] for row in selected), "repository_commit_tree_binding")
    require(inventory["repositories_complete"] == sum(row["tree_complete"] for row in repositories), "complete_repository_count")
    require(inventory["api_cli_invocations"] == sum(len(row["api_calls"]) for row in repositories), "api_invocation_count")
    return {"schema": VERSION, "metadata_integrity": "passed", "references_discovered": len(catalog),
            "repositories_complete": inventory["repositories_complete"], "repositories_requested": len(inventory["repositories_requested"]),
            "counts_by_kind": inventory["counts_by_kind"], "installed": False, "verified": False, "license_scope": "unreviewed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("harvest", "check"))
    parser.add_argument("--output", type=Path, required=True, help="Fresh discovery directory for harvest; existing snapshot for offline check.")
    parser.add_argument("--repo", action="append", help="Explicit public owner/repository; defaults to the four documented source repositories.")
    args = parser.parse_args(argv)
    result = harvest(args.output, args.repo or DEFAULT_REPOSITORIES) if args.mode == "harvest" else check(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
