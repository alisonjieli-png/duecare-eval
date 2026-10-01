"""Offline metadata discovery tests; gh and HTTP are replaced by fixtures."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("upstream_discovery_test", ROOT / "harness_components/tools/harvest_upstream_references.py")
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
COMMIT, TREE, BLOB, SUBTREE = "a" * 40, "b" * 40, "c" * 40, "d" * 40


def blob(path, *, sha=BLOB, size=12, mode="100644"):
    return {"path": path, "type": "blob", "mode": mode, "sha": sha, "size": size, "url": "https://api.github.com/unused/blob"}


def tree(path, sha=SUBTREE):
    return {"path": path, "type": "tree", "mode": "040000", "sha": sha}


class FakeApi:
    def __init__(self, responses): self.responses, self.calls = responses, []
    def __call__(self, endpoint):
        self.calls.append({"endpoint": endpoint, "method": "GET", "status": "fixture"})
        result = self.responses[endpoint]
        if isinstance(result, Exception): raise result
        return deepcopy(result)


def fixture_api(entries=None, *, repository="owner/repo", truncated=False):
    return FakeApi({f"repos/{repository}/commits/main": {"sha": COMMIT, "commit": {"tree": {"sha": TREE}, "message": "PRIVATE COMMIT TEXT"}, "author": {"email": "person@example.org"}},
        f"repos/{repository}/git/trees/{TREE}?recursive=1": {"sha": TREE, "truncated": truncated, "tree": entries or [blob("skills/example/SKILL.md"), blob("skills/example/scripts/helper.py")]}})


def test_commit_and_tree_identities_remain_distinct_and_blobs_are_never_fetched():
    api = fixture_api()
    rows, receipt = M.discover_repository("OWNER/REPO", api)
    assert api.calls[0]["endpoint"] == "repos/owner/repo/commits/main"
    assert api.calls[1]["endpoint"] == f"repos/owner/repo/git/trees/{TREE}?recursive=1"
    assert receipt["commit"] == COMMIT and receipt["tree_sha"] == TREE and receipt["tree_complete"]
    assert all(f"/blob/{COMMIT}/" in row["source_url"] and f"/blob/{TREE}/" not in row["source_url"] for row in rows)
    assert all("/git/blobs/" not in call["endpoint"] and "/contents/" not in call["endpoint"] for call in api.calls)
    assert "PRIVATE COMMIT TEXT" not in json.dumps([rows, receipt]) and "person@example.org" not in json.dumps([rows, receipt])


def test_useful_file_classes_and_skill_scoped_helpers_only():
    entries = [blob("skills/review/SKILL.md"), blob("skills/review/scripts/a.py"), blob("skills/review/a.js"), blob("skills/review/a.ts"),
        blob("skills/review/a.d.ts"), blob("skills/review/node_modules/pkg/index.js"), blob("skills/review/vendor/thing.py"),
        blob("src/arbitrary.py"), blob("instructions/check.instructions.md"), blob("agents/doctor.agent.md"), blob("prompts/review.prompt.md"),
        blob("README.md"), blob("skills/linked/SKILL.md", mode="120000"),
        {"path": "submodule", "type": "commit", "mode": "160000", "sha": SUBTREE}]
    rows, receipt = M.discover_repository("owner/repo", fixture_api(entries))
    assert len(rows) == 7 and receipt["symlinks_excluded"] == receipt["submodules_excluded"] == 1
    assert receipt["counts_by_kind"] == {"agent": 1, "helper_script": 3, "instructions": 1, "prompt": 1, "skill": 1}
    assert {row["path"] for row in rows}.isdisjoint({"src/arbitrary.py", "README.md", "skills/review/a.d.ts"})


def test_paths_with_special_characters_are_url_quoted_without_local_paths():
    rows, _ = M.discover_repository("owner/repo", fixture_api([blob("skills/café #1/SKILL.md")]))
    assert rows[0]["source_url"].endswith("skills/caf%C3%A9%20%231/SKILL.md")
    assert rows[0]["title"] == "café #1" and rows[0]["path"] == "skills/café #1/SKILL.md"


@pytest.mark.parametrize("path", ["../secret", "/absolute", "a/../b", "a\\b", "a//b", "a/./b", "a\x00b"])
def test_unsafe_upstream_paths_rejected(path):
    rows, receipt = M.discover_repository("owner/repo", fixture_api([blob(path)]))
    assert not rows and receipt["status"] == "invalid_metadata" and not receipt["tree_complete"]


def test_tree_sha_mismatch_and_invalid_commit_never_become_complete():
    api = fixture_api(); api.responses[f"repos/owner/repo/git/trees/{TREE}?recursive=1"]["sha"] = COMMIT
    rows, receipt = M.discover_repository("owner/repo", api)
    assert rows == [] and receipt["status"] == "invalid_metadata"
    api = fixture_api(); api.responses["repos/owner/repo/commits/main"]["sha"] = "main"
    rows, receipt = M.discover_repository("owner/repo", api)
    assert rows == [] and len(api.calls) == 1 and receipt["status"] == "invalid_metadata"


def test_complete_subtree_recovery_has_no_silent_count_cap():
    api = fixture_api([tree("skills")], truncated=True)
    leaf = "e" * 40
    api.responses[f"repos/owner/repo/git/trees/{TREE}"] = {"sha": TREE, "truncated": False, "tree": [tree("skills")]}
    api.responses[f"repos/owner/repo/git/trees/{SUBTREE}"] = {"sha": SUBTREE, "truncated": False, "tree": [tree("sample", leaf)]}
    api.responses[f"repos/owner/repo/git/trees/{leaf}"] = {"sha": leaf, "truncated": False, "tree": [blob("SKILL.md")] + [blob(f"helper-{i}.py") for i in range(1500)]}
    rows, receipt = M.discover_repository("owner/repo", api)
    assert len(rows) == 1501 and receipt["root_recursive_truncated"] and receipt["tree_complete"]
    assert receipt["status"] == "complete_metadata" and len(api.calls) == 5
    assert len({row["id"] for row in rows}) == 1501


def test_failed_or_truncated_recovery_preserves_partial_coverage():
    api = fixture_api([tree("skills"), blob("known.agent.md")], truncated=True)
    api.responses[f"repos/owner/repo/git/trees/{TREE}"] = {"sha": TREE, "truncated": False, "tree": [tree("skills"), blob("known.agent.md")]}
    api.responses[f"repos/owner/repo/git/trees/{SUBTREE}"] = M.ApiFailure("api_cli_error", http_status=403)
    rows, receipt = M.discover_repository("owner/repo", api)
    assert len(rows) == 1 and receipt["status"] == "partial_metadata" and not receipt["tree_complete"]
    assert receipt["coverage_errors"][0]["http_status"] == 403
    api.responses[f"repos/owner/repo/git/trees/{SUBTREE}"] = {"sha": SUBTREE, "truncated": True, "tree": []}
    assert not M.discover_repository("owner/repo", api)[1]["tree_complete"]


def test_tree_cycle_refused_without_infinite_traversal():
    api = fixture_api([tree("again", TREE)], truncated=True)
    api.responses[f"repos/owner/repo/git/trees/{TREE}"] = {"sha": TREE, "truncated": False, "tree": [tree("again", TREE)]}
    rows, receipt = M.discover_repository("owner/repo", api)
    assert not receipt["tree_complete"] and receipt["coverage_errors"][0]["code"] == "tree_cycle_detected"
    assert len(api.calls) == 3


def test_identical_duplicate_entries_deduplicate_but_conflicts_fail():
    entry = blob("example.agent.md")
    rows, _ = M.discover_repository("owner/repo", fixture_api([entry, entry]))
    assert len(rows) == 1
    rows, receipt = M.discover_repository("owner/repo", fixture_api([entry, {**entry, "sha": SUBTREE}]))
    assert not rows and receipt["status"] == "invalid_metadata"


def test_transport_is_get_only_fixed_host_and_sanitizes_errors():
    calls = []
    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=1, stdout='{"token":"SECRET"}', stderr="HTTP 403 /home/private SECRET token=SECRET")
    api = M.GhApi(runner=runner)
    with pytest.raises(M.ApiFailure) as caught: api("repos/owner/repo/commits/main")
    assert caught.value.details["http_status"] == 403
    assert "SECRET" not in json.dumps(api.calls) and "/home/private" not in json.dumps(api.calls)
    assert calls[0][0][:7] == ["gh", "api", "--hostname", "github.com", "--method", "GET", "-H"]
    assert "shell" not in calls[0][1] and calls[0][1]["capture_output"]
    with pytest.raises(ValueError): api("https://evil.example/endpoint")
    with pytest.raises(ValueError): api("repos/owner/repo/contents/SKILL.md")
    assert len(calls) == 1


@pytest.mark.parametrize("failure,code", [(FileNotFoundError("/secret/path"), "api_cli_unavailable"), (subprocess.TimeoutExpired(["secret"], 10), "api_cli_timeout")])
def test_transport_exceptions_do_not_copy_local_paths(failure, code):
    def runner(*args, **kwargs): raise failure
    api = M.GhApi(runner=runner)
    with pytest.raises(M.ApiFailure) as caught: api("repos/owner/repo/commits/main")
    assert caught.value.details["error_code"] == code and "secret" not in json.dumps(api.calls)


def test_harvest_and_offline_check_preserve_metadata_only_payloads(tmp_path):
    output = tmp_path / "snapshot"
    inventory = M.harvest(output, ["owner/repo"], api=fixture_api())
    checked = M.check(output)
    assert checked["metadata_integrity"] == "passed" and checked["references_discovered"] == 2
    assert checked["verified"] is checked["installed"] is False and checked["license_scope"] == "unreviewed"
    assert inventory["third_party_file_bodies_fetched"] == inventory["upstream_code_executed"] == inventory["model_calls"] == 0
    catalog = [json.loads(line) for line in (output / "catalog.jsonl").read_text().splitlines()]
    for row in catalog:
        data = (output / row["payload_path"]).read_bytes()
        assert sha256(data).hexdigest() == row["payload_sha256"]
        assert set(json.loads(data)) == M.ITEM_FIELDS
        assert f"/blob/{COMMIT}/" in row["source_url"]
    assert "PRIVATE COMMIT TEXT" not in "".join(p.read_text() for p in output.rglob("*") if p.is_file())


def test_nonempty_output_refused_before_network_and_existing_bytes_preserved(tmp_path):
    output = tmp_path / "snapshot"; output.mkdir(); existing = output / "old.json"; existing.write_text("preserve")
    api = fixture_api()
    with pytest.raises(ValueError, match="fresh_empty"): M.harvest(output, ["owner/repo"], api=api)
    assert api.calls == [] and existing.read_text() == "preserve"


def test_api_errors_are_source_coverage_outcomes(tmp_path):
    api = FakeApi({"repos/owner/repo/commits/main": M.ApiFailure("api_cli_error", http_status=404)})
    inventory = M.harvest(tmp_path / "missing", ["owner/repo"], api=api)
    assert inventory["references_discovered"] == 0 and inventory["repositories_complete"] == 0
    assert inventory["repositories"][0]["status"] == "api_error"
    assert M.check(tmp_path / "missing")["references_discovered"] == 0


def test_record_identity_changes_with_commit_and_metadata_tamper_is_rejected(tmp_path):
    output = tmp_path / "snapshot"; M.harvest(output, ["owner/repo"], api=fixture_api())
    row = json.loads((output / "catalog.jsonl").read_text().splitlines()[0])
    item = json.loads((output / row["payload_path"]).read_text())
    original = deepcopy(item); item["installed"] = True
    with pytest.raises(ValueError): M.validate_reference(item)
    item = deepcopy(original); item["commit"] = SUBTREE
    with pytest.raises(ValueError): M.validate_reference(item)
    item = deepcopy(original); item["description"] = "Third-party body"
    with pytest.raises(ValueError): M.validate_reference(item)
    (output / row["payload_path"]).write_text(json.dumps(item))
    with pytest.raises(ValueError): M.check(output)


def test_item_symlink_escape_and_catalog_path_tampering_refused(tmp_path):
    output = tmp_path / "snapshot"; M.harvest(output, ["owner/repo"], api=fixture_api())
    row = json.loads((output / "catalog.jsonl").read_text().splitlines()[0])
    item_path = output / row["payload_path"]; outside = tmp_path / "outside.json"; outside.write_bytes(item_path.read_bytes())
    item_path.unlink(); item_path.symlink_to(outside)
    with pytest.raises(ValueError, match="item_path_escape"): M.check(output)


def test_discovery_ids_are_deterministic_for_the_same_pinned_inputs():
    first, _ = M.discover_repository("owner/repo", fixture_api())
    second, _ = M.discover_repository("owner/repo", fixture_api())
    assert first == second


@pytest.mark.parametrize("field,value", [("repositories_complete", 99), ("references_discovered", 99), ("model_calls", 1), ("api_cli_invocations", 99)])
def test_false_inventory_coverage_or_execution_claims_rejected(tmp_path, field, value):
    output = tmp_path / "snapshot"; M.harvest(output, ["owner/repo"], api=fixture_api())
    path = output / "inventory.json"; inventory = json.loads(path.read_text()); inventory[field] = value
    path.write_text(json.dumps(inventory))
    with pytest.raises(ValueError): M.check(output)


def test_extra_body_file_is_outside_metadata_snapshot_contract(tmp_path):
    output = tmp_path / "snapshot"; M.harvest(output, ["owner/repo"], api=fixture_api())
    (output / "copied-third-party-body.md").write_text("Outside the metadata-only contract")
    with pytest.raises(ValueError, match="unexpected_snapshot_file"): M.check(output)


def test_mismatched_repository_commit_receipt_rejected(tmp_path):
    output = tmp_path / "snapshot"; M.harvest(output, ["owner/repo"], api=fixture_api())
    path = output / "inventory.json"; inventory = json.loads(path.read_text()); inventory["repositories"][0]["commit"] = SUBTREE
    path.write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match="repository_commit_tree_binding"): M.check(output)
