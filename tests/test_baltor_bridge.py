"""Candidate interoperability fixtures; no admission or model-quality claims."""
from hashlib import sha256
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from duecare_eval import baltor_bridge as B
from duecare_eval.contracts import canonical
from duecare_eval.knowledge import KnowledgeError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("network is outside an offline candidate check")
    monkeypatch.setattr(socket, "socket", refused)
    monkeypatch.setattr(socket, "create_connection", refused)


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "public"
    root.mkdir()
    for name in B.EXPORT_PATHS:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (root / "pyproject.toml").write_text('[project]\nname = "duecare-eval-public"\n')
    for args in (("init", "-q"), ("remote", "add", "origin", B.PUBLIC_ORIGIN), ("add", "."),
                 ("-c", "user.name=Offline fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "-qm", "Offline fixture")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


@pytest.fixture
def legacy_checkout(checkout):
    """An exact legacy-path source fixture, with the same five skill bytes."""
    (checkout / "skills").mkdir()
    for name in B.SKILL_NAMES:
        (checkout / "harness_components/skills" / name).rename(checkout / "skills" / name)
    for args in (("add", "-A"), ("-c", "user.name=Offline fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Legacy layout fixture")):
        subprocess.run(["git", "-C", str(checkout), *args], check=True, capture_output=True)
    return checkout


def read(path):
    return json.loads(path.read_text())


def request(name, **arguments):
    return {"schema": B.REQUEST_VERSION, "operation": name, "arguments": arguments}


def test_fresh_export_hashes_rights_and_clean_source_identity(checkout, tmp_path):
    destination = tmp_path / "candidate"
    receipt = B.export_candidate(checkout, destination, captured_at="2026-10-01T17:00:00Z")
    assert receipt["files_verified"] == len(B.EXPORT_PATHS)
    assert receipt["layout_profile"] == B.CURRENT_LAYOUT
    assert receipt["source"]["worktree_dirty"] is False
    assert receipt["source"]["base_commit_is_exported_tree"] is True
    assert receipt["rights"]["license"] == "unknown"
    assert receipt["rights"]["notice_sha256"] == sha256((checkout / "NOTICE.md").read_bytes()).hexdigest()
    assert receipt["admitted"] is receipt["served"] is False
    assert receipt == B.validate_candidate(destination)
    for row in read(destination / "package.json")["files"]:
        raw = (destination / "files" / row["path"]).read_bytes()
        assert row["digest"] == sha256(raw).hexdigest() and row["size_bytes"] == len(raw)
    asset = read(destination / "code-assets.json")[0]
    assert asset["lifecycle"] == "candidate" and asset["admission_ref"] == ""
    assert asset["body_ref"]["digest"] == receipt["package_sha256"]
    candidate = read(destination / "candidate.json")
    assert candidate["layout_profile"] == B.CURRENT_LAYOUT
    files = candidate["package"]["files"]
    assert candidate["file_placements"] == receipt["file_placements"] == len(files)
    assert candidate["distinct_file_digests"] == receipt["distinct_file_digests"] == len({
        sha256((destination / "files" / row["path"]).read_bytes()).hexdigest() for row in files})
    assert candidate["file_count_scope"] == receipt["file_count_scope"]
    assert candidate["full_bundle_contains_evaluator_references"] is True
    assert candidate["target_input"] == "payload_only"
    assert len(candidate["coordinator_only_fixture_files"]) == 6
    assert candidate["receiving_constraints"] == B.RECEIVING_CONSTRAINTS
    roles = {entry["path"]: entry["role"] for entry in candidate["package"]["files"]}
    for name in B.SKILL_NAMES:
        assert roles["harness_components/skills/" + name + "/SKILL.md"] == "skill_definition"
        assert roles["harness_components/skills/" + name + "/agents/openai.yaml"] == "configuration"
    assert roles["docs/KNOWLEDGE_TRANSFER.md"] == "skill_reference"
    candidate["distinct_file_digests"] += 1
    (destination / "candidate.json").write_text(canonical(candidate))
    with pytest.raises(B.BridgeError, match="package_file_counts_mismatch"):
        B.validate_candidate(destination)


def test_layout_profiles_are_exact_closures_with_only_ten_relocated_files():
    legacy, current = set(B.LAYOUT_PATHS[B.LEGACY_LAYOUT]), set(B.LAYOUT_PATHS[B.CURRENT_LAYOUT])
    assert len(legacy) == len(current) == 61
    assert legacy & current == set(B.COMMON_EXPORT_PATHS) and len(legacy & current) == 51
    old_skills, new_skills = legacy - current, current - legacy
    assert len(old_skills) == len(new_skills) == 10
    assert new_skills == {"harness_components/" + path for path in old_skills}
    assert "plugins/mcp-stdio.json" in legacy & current
    assert "src/duecare_eval/mcp_server.py" in legacy & current
    assert not any(path.startswith("harness_components/") and not path.startswith("harness_components/skills/") for path in current)


def test_named_legacy_and_undeclared_published_layout_keep_asset_digests(legacy_checkout, tmp_path):
    destination = tmp_path / "legacy-candidate"
    named = B.export_candidate(legacy_checkout, destination, layout_profile=B.LEGACY_LAYOUT)
    assert named["layout_profile"] == B.LEGACY_LAYOUT and named["files_verified"] == 61
    candidate_path = destination / "candidate.json"
    candidate = read(candidate_path)
    assert candidate.pop("layout_profile") == B.LEGACY_LAYOUT
    candidate_path.write_text(canonical(candidate))
    assets_before = (destination / "code-assets.json").read_bytes()
    assets = read(destination / "code-assets.json")
    qualification = assets[0]["qualification_digest"]
    package_digest = candidate["package_sha256"]
    receipt = B.validate_candidate(destination)
    assert receipt["layout_profile"] == B.LEGACY_LAYOUT and receipt["package_sha256"] == package_digest
    assert (destination / "code-assets.json").read_bytes() == assets_before
    assert read(destination / "code-assets.json")[0]["qualification_digest"] == qualification
    assert "layout_profile" not in read(candidate_path)
    roles = {row["path"]: row["role"] for row in candidate["package"]["files"]}
    assert all(roles["skills/" + name + "/SKILL.md"] == "skill_definition" for name in B.SKILL_NAMES)


@pytest.mark.parametrize("declaration,error", [(None, "unsupported_layout_profile"), ("unknown/v1", "unsupported_layout_profile"),
    (1, "unsupported_layout_profile"), (B.LEGACY_LAYOUT, "exact_allowlist_required"), ("missing", "exact_allowlist_required")])
def test_new_layout_requires_its_own_explicit_supported_declaration(checkout, tmp_path, declaration, error):
    destination = tmp_path / "candidate"; B.export_candidate(checkout, destination)
    path = destination / "candidate.json"; candidate = read(path)
    if declaration == "missing": candidate.pop("layout_profile")
    else: candidate["layout_profile"] = declaration
    path.write_text(canonical(candidate))
    with pytest.raises(B.BridgeError, match=error): B.validate_candidate(destination)


def rewrite_candidate_paths(destination, changes):
    """Keep every digest consistent so rejection tests isolate layout closure."""
    candidate = read(destination / "candidate.json")
    package = candidate["package"]
    for index, entry in enumerate(package["files"]):
        if entry["path"] not in changes:
            continue
        old = destination / "files" / entry["path"]
        new_name = changes[entry["path"]]; new = destination / "files" / new_name
        new.parent.mkdir(parents=True, exist_ok=True); old.rename(new)
        package["files"][index] = B._file_record(new_name, new.read_bytes())
    package["files"].sort(key=lambda entry: entry["path"])
    digest = sha256(canonical({"record_type": "catalogue_package/v1", "files": package["files"]}).encode()).hexdigest()
    candidate["package_sha256"] = candidate["source"]["exported_files_sha256"] = digest
    candidate.update(B._file_counts(package["files"]))
    assets = [B._asset(package, candidate["source"], candidate["rights"]["notice_sha256"])]
    candidate["code_assets_sha256"] = sha256(canonical(assets).encode()).hexdigest()
    for name, value in (("candidate.json", candidate), ("package.json", package), ("code-assets.json", assets)):
        (destination / name).write_text(canonical(value))


@pytest.mark.parametrize("replacement", ["skills/duecare-author-industry-pack/SKILL.md", "harness_components/skills/unlisted-skill/SKILL.md",
    "harness_components/components/search/unknown.py"])
def test_mixed_and_unknown_layouts_fail_even_with_consistent_file_and_asset_hashes(checkout, tmp_path, replacement):
    destination = tmp_path / "candidate"; B.export_candidate(checkout, destination)
    original = "harness_components/skills/duecare-author-industry-pack/SKILL.md"
    rewrite_candidate_paths(destination, {original: replacement})
    with pytest.raises(B.BridgeError, match="exact_allowlist_required"): B.validate_candidate(destination)


def test_new_library_and_additional_skills_stay_outside_default_core(checkout, tmp_path):
    extras = ("harness_components/skills/new-workflow/SKILL.md", "harness_components/catalog.json", "harness_components/mcp/server.py")
    for name in extras:
        path = checkout / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("UNSELECTED_LIBRARY_CONTENT")
    destination = tmp_path / "candidate"
    assert B.export_candidate(checkout, destination)["files_verified"] == 61
    assert all(not (destination / "files" / name).exists() for name in extras)


def test_unknown_export_layout_is_refused_before_writing(checkout, tmp_path):
    destination = tmp_path / "candidate"
    with pytest.raises(B.BridgeError, match="unsupported_layout_profile"):
        B.export_candidate(checkout, destination, layout_profile="copy-everything")
    assert not destination.exists()


def test_validation_enforces_actual_aggregate_bytes_inclusive_boundary(checkout, tmp_path, monkeypatch):
    destination = tmp_path / "candidate"
    B.export_candidate(checkout, destination)
    files = read(destination / "package.json")["files"]
    total = sum((destination / "files" / entry["path"]).stat().st_size for entry in files)
    assert all(entry["size_bytes"] <= B.MAX_FILE_BYTES for entry in files)
    monkeypatch.setattr(B, "MAX_PACKAGE_BYTES", total)
    assert B.validate_candidate(destination)["files_verified"] == 61
    monkeypatch.setattr(B, "MAX_PACKAGE_BYTES", total - 1)
    with pytest.raises(B.BridgeError, match="package_too_large"):
        B.validate_candidate(destination)


def test_dirty_source_is_bound_to_exact_bytes_and_base_commit(checkout, tmp_path):
    path = checkout / "NOTICE.md"
    path.write_text(path.read_text() + "\nOffline fixture change.\n")
    receipt = B.export_candidate(checkout, tmp_path / "candidate")
    assert receipt["source"]["worktree_dirty"] is True
    assert receipt["source"]["base_commit_is_exported_tree"] is False
    assert receipt["source"]["content_binding"] == "exact_exported_file_hashes"
    assert receipt["rights"]["notice_sha256"] == sha256(path.read_bytes()).hexdigest()


def test_clean_git_status_cannot_claim_changed_assume_unchanged_bytes(checkout, tmp_path):
    subprocess.run(["git", "-C", str(checkout), "update-index", "--assume-unchanged", "NOTICE.md"], check=True)
    path = checkout / "NOTICE.md"
    path.write_text(path.read_text() + "\nIgnored local fixture difference.\n")
    receipt = B.export_candidate(checkout, tmp_path / "candidate")
    assert receipt["source"]["worktree_dirty"] is False
    assert receipt["source"]["base_commit_is_exported_tree"] is False


def test_private_and_unlisted_inputs_are_never_copied(checkout, tmp_path):
    private = checkout / "runs" / "private"
    private.mkdir(parents=True)
    (private / "responses.jsonl").write_text("DO_NOT_EXPORT_THIS_PRIVATE_RESPONSE")
    destination = tmp_path / "candidate"
    B.export_candidate(checkout, destination)
    assert not (destination / "files/runs").exists()
    assert all("DO_NOT_EXPORT_THIS_PRIVATE_RESPONSE" not in path.read_text()
               for path in destination.rglob("*") if path.is_file())
    assert read(destination / "candidate.json")["source"]["worktree_dirty"] is True


def test_private_parent_or_wrong_remote_is_not_a_source(checkout, tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    with pytest.raises(B.BridgeError, match="public_git_identity_required"):
        B.export_candidate(private, tmp_path / "candidate")
    subprocess.run(["git", "-C", str(checkout), "remote", "set-url", "origin", "https://example.invalid/private.git"], check=True)
    with pytest.raises(B.BridgeError, match="public_origin_required"):
        B.export_candidate(checkout, tmp_path / "candidate")
    assert not (tmp_path / "candidate").exists()


@pytest.mark.parametrize("origin", [
    "https://github.com/alisonjieli-png/duecare-eval",
    "https://github.com/alisonjieli-png/duecare-eval.git",
    "https://github.com:443/alisonjieli-png/duecare-eval",
    "https://github.com:443/alisonjieli-png/duecare-eval.git",
    "git@github.com:alisonjieli-png/duecare-eval",
    "git@github.com:alisonjieli-png/duecare-eval.git",
    "ssh://git@github.com/alisonjieli-png/duecare-eval",
    "ssh://git@github.com/alisonjieli-png/duecare-eval.git",
    "ssh://git@github.com:22/alisonjieli-png/duecare-eval",
    "ssh://git@github.com:22/alisonjieli-png/duecare-eval.git",
])
def test_same_repository_clone_urls_export_with_canonical_identity(checkout, tmp_path, origin):
    subprocess.run(["git", "-C", str(checkout), "remote", "set-url", "origin", origin], check=True)
    receipt = B.export_candidate(checkout, tmp_path / "candidate")
    assert receipt["source"]["repository"] == B.PUBLIC_ORIGIN
    assert receipt["source"]["base_commit_is_exported_tree"] is True


@pytest.mark.parametrize("origin", [
    "https://example.invalid/alisonjieli-png/duecare-eval.git",
    "https://github.com.evil.invalid/alisonjieli-png/duecare-eval.git",
    "https://github.com/another-owner/duecare-eval.git",
    "https://github.com/alisonjieli-png/another-repo.git",
    "https://github.com/alisonjieli-png/duecare-eval.git/extra",
    "https://github.com/alisonjieli-png/duecare-eval.git?query=secret-value",
    "https://github.com/alisonjieli-png/duecare-eval.git#fragment",
    "https://secret-value@github.com/alisonjieli-png/duecare-eval.git",
    "https://user:secret-value@github.com/alisonjieli-png/duecare-eval.git",
    "https://github.com:8443/alisonjieli-png/duecare-eval.git",
    "http://github.com/alisonjieli-png/duecare-eval.git",
    "git://github.com/alisonjieli-png/duecare-eval.git",
    "git@evil.invalid:alisonjieli-png/duecare-eval.git",
    "secret-value@github.com:alisonjieli-png/duecare-eval.git",
    "ssh://user@github.com/alisonjieli-png/duecare-eval.git",
    "ssh://git:secret-value@github.com/alisonjieli-png/duecare-eval.git",
    "ssh://git@github.com:2222/alisonjieli-png/duecare-eval.git",
    "https://github.com/alisonjieli-png/%64uecare-eval.git",
    "https://github.com/alisonjieli-png/../alisonjieli-png/duecare-eval.git",
    "https://github.com\\@evil.invalid/alisonjieli-png/duecare-eval.git",
])
def test_noncanonical_or_secret_bearing_origins_are_refused_without_echo(checkout, tmp_path, origin):
    subprocess.run(["git", "-C", str(checkout), "remote", "set-url", "origin", origin], check=True)
    with pytest.raises(B.BridgeError, match="^public_origin_required$") as error:
        B.export_candidate(checkout, tmp_path / "candidate")
    assert "secret-value" not in str(error.value)
    assert not (tmp_path / "candidate").exists()


def test_existing_destination_is_preserved_and_overlap_refused(checkout, tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "user.txt"
    marker.write_text("preserve")
    with pytest.raises(B.BridgeError, match="destination_already_exists"):
        B.export_candidate(checkout, destination)
    assert marker.read_text() == "preserve"
    with pytest.raises(B.BridgeError, match="destination_overlaps_source"):
        B.export_candidate(checkout, checkout / "candidate")
    with pytest.raises(B.BridgeError, match="destination_path_traversal"):
        B.export_candidate(checkout, tmp_path / "existing" / ".." / "escaped")


def test_symlink_member_and_output_parent_are_refused(checkout, tmp_path):
    source = checkout / "NOTICE.md"
    original = source.read_bytes()
    source.unlink()
    external = tmp_path / "notice"
    external.write_bytes(original)
    source.symlink_to(external)
    with pytest.raises(B.BridgeError, match="symlink_member_refused"):
        B.export_candidate(checkout, tmp_path / "candidate")
    linked = tmp_path / "link"
    linked.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(B.BridgeError, match="root_requires_existing_unlinked_directory"):
        B.export_candidate(checkout, linked / "candidate")


@pytest.mark.parametrize("mutation,error", [
    (lambda p: (p / "files/NOTICE.md").write_text("changed"), "package_file_identity_mismatch"),
    (lambda p: (p / "extra.json").write_text("{}"), "unexpected_candidate_files"),
    (lambda p: (p / "code-assets.json").write_text("[]"), "code_asset_projection_mismatch"),
    (lambda p: (p / "operation-contracts.json").write_text("{}"), "operation_contract_mismatch"),
])
def test_export_verification_refuses_changed_or_extra_content(checkout, tmp_path, mutation, error):
    destination = tmp_path / "candidate"
    B.export_candidate(checkout, destination)
    mutation(destination)
    with pytest.raises(B.BridgeError, match=error):
        B.validate_candidate(destination)


def test_forged_admission_and_rights_are_refused(checkout, tmp_path):
    destination = tmp_path / "candidate"
    B.export_candidate(checkout, destination)
    path = destination / "candidate.json"
    value = read(path)
    value["admitted"] = True
    path.write_text(canonical(value))
    with pytest.raises(B.BridgeError, match="candidate_only_required"):
        B.validate_candidate(destination)
    value["admitted"] = False
    value["rights"]["license"] = "MIT"
    path.write_text(canonical(value))
    with pytest.raises(B.BridgeError, match="rights_state_required"):
        B.validate_candidate(destination)


def test_preloaded_operations_cover_packs_profiles_arms_and_do_no_later_reads(monkeypatch):
    operations = B.PreloadedOperations.from_public_root(ROOT)
    catalog = operations.invoke(request("catalog"))["result"]
    def refused(*args, **kwargs):
        raise AssertionError("preloaded operation attempted a filesystem read")
    monkeypatch.setattr(Path, "open", refused)
    prepared = 0
    for pack in catalog["packs"]:
        for profile in catalog["profiles"]:
            for source_on in (False, True):
                result = operations.invoke(request("prepare_benchmark", pack_id=pack["pack_id"],
                    profile=profile, include_sources=source_on))
                assert result["result"]["model_calls_executed"] == 0
                assert result["result_sha256"] == sha256(canonical(result["result"]).encode()).hexdigest()
                prepared += result["result"]["prepared_requests"]
    assert prepared == 72  # 12 case variants, three adapters, two source arms.


@pytest.mark.parametrize("value,error", [
    ({"schema": "old", "operation": "catalog", "arguments": {}}, "unsupported_operation_version"),
    ({"schema": B.REQUEST_VERSION, "operation": "missing", "arguments": {}}, "unknown_operation"),
    ({"schema": B.REQUEST_VERSION, "operation": "catalog", "arguments": {"path": "/private"}}, "operation_argument_fields"),
    ({"schema": B.REQUEST_VERSION, "operation": "catalog", "arguments": {}, "extra": True}, "operation_envelope_fields"),
])
def test_typed_operation_refuses_unknown_or_path_arguments(value, error):
    operations = B.PreloadedOperations.from_public_root(ROOT)
    with pytest.raises((B.BridgeError, KnowledgeError), match=error):
        operations.invoke(value)


def test_hidden_reference_changes_leave_prepared_payloads_unchanged():
    operations = B.PreloadedOperations.from_public_root(ROOT)
    catalog = operations.invoke(request("catalog"))["result"]
    for item in catalog["packs"]:
        pack_id = item["pack_id"]
        before = operations.invoke(request("prepare_benchmark", pack_id=pack_id))
        # In-memory mutation is an adversarial fixture, not an editing API.
        for case in operations._library._packs[pack_id]["cases"]:
            case["evaluator"]["requested_tier"] = 1
            case["evaluator"]["source_labels"]["private_marker"] = "DO_NOT_DISCLOSE"
        assert operations.invoke(request("prepare_benchmark", pack_id=pack_id)) == before


def test_exported_dependency_closure_bootstraps_in_clean_process(checkout, tmp_path):
    destination = tmp_path / "candidate"
    B.export_candidate(checkout, destination)
    program = "import sys; sys.path.insert(0, sys.argv[1]); from duecare_eval.baltor_bridge import PreloadedOperations; print(len(PreloadedOperations.from_public_root(sys.argv[2])._library.catalog()['packs']))"
    process = subprocess.run([sys.executable, "-B", "-I", "-c", program,
                              str(destination / "files/src"), str(destination / "files")],
                             check=True, capture_output=True, text=True)
    assert process.stdout.strip() == "6"


def test_operation_cards_are_independent_copies():
    cards = B.operation_contracts()
    assert len(cards["operations"]) == 9
    cards["operations"][0]["input_schema"]["properties"]["arguments"]["additionalProperties"] = True
    assert B.operation_contracts()["operations"][0]["input_schema"]["properties"]["arguments"]["additionalProperties"] is False
