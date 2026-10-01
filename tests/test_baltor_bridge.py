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


def read(path):
    return json.loads(path.read_text())


def request(name, **arguments):
    return {"schema": B.REQUEST_VERSION, "operation": name, "arguments": arguments}


def test_fresh_export_hashes_rights_and_clean_source_identity(checkout, tmp_path):
    destination = tmp_path / "candidate"
    receipt = B.export_candidate(checkout, destination, captured_at="2026-10-01T17:00:00Z")
    assert receipt["files_verified"] == len(B.EXPORT_PATHS)
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
        assert roles["skills/" + name + "/SKILL.md"] == "skill_definition"
        assert roles["skills/" + name + "/agents/openai.yaml"] == "configuration"
    assert roles["docs/KNOWLEDGE_TRANSFER.md"] == "skill_reference"
    candidate["distinct_file_digests"] += 1
    (destination / "candidate.json").write_text(canonical(candidate))
    with pytest.raises(B.BridgeError, match="package_file_counts_mismatch"):
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
