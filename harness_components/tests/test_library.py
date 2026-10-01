"""Library integrity, data-only lookup and executable-contract checks."""

import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import harness_components.library as api
from harness_components.__main__ import main


PUBLIC_ROOT = Path(api.__file__).parent


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def mutate_catalog(root, mutate):
    path = root / "catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    mutate(catalog)
    write_json(path, catalog)


@pytest.fixture
def library_root(tmp_path):
    root = tmp_path / "reviewed-library"
    root.mkdir()
    selected = [
        "__init__.py", "library.py", "components/__init__.py",
        "components/text/__init__.py", "components/text/_shared.py", "components/text/_lexicon.py",
        "components/text/email_normalize.py", "components/text/slang_matches.py",
        "components/text/find_literal_spans.py", "components/text/mask_spans.py",
        "components/search/__init__.py", "components/search/_common.py",
        "components/search/bm25_rank.py", "components/search/grep_lines.py",
    ]
    for relative in selected:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC_ROOT / relative, destination)
    query = {"id": "query-test", "type": "query_preset", "title": "Mailbox guidance search",
             "query": 'site:example.org "email"', "scope": "Unexecuted search preset.",
             "tags": ["mailbox", "sample"], "source_refs": [{"artifact": "example-query-source.jsonl"}]}
    payload = root / "search_queries/items/te/query-test.json"
    write_json(payload, query)
    query_row = {**query, "payload_path": "items/te/query-test.json",
                 "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}
    write_json(root / "search_queries/catalog.jsonl", query_row)
    skill = root / "skills/example-skill/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text('---\nname: example-skill\ndescription: "Example mailbox review instructions."\n---\n\n# Example\nRead the supplied sample.\n', encoding="utf-8")
    api.build_catalog(root)
    return root


def test_build_counts_distinguish_operations_data_and_helpers(library_root):
    library = api.Library(library_root)
    assert library.counts == {"function": 6, "query_preset": 1, "skill": 1, "upstream_reference": 0}
    assert library.search("")["total_matches"] == 8
    function = library.get("text.slang_matches")
    assert {"library.py", "__init__.py", "components/__init__.py", "components/text/__init__.py",
            "components/text/_shared.py", "components/text/_lexicon.py", "components/text/slang_matches.py"} == set(function["dependencies"])
    assert "text._shared" not in library._by_id
    assert "search._common" not in library._by_id
    inventory = json.loads((library_root / "inventory.json").read_text())
    assert inventory["catalog_sha256"] == library.catalog_sha256
    assert len(inventory["function_ids"]) == 6


def test_build_is_deterministic_and_dry_build_writes_nothing(library_root):
    original = (library_root / "catalog.json").read_bytes()
    inventory = (library_root / "inventory.json").read_bytes()
    api.build_catalog(library_root, write=False)
    assert (library_root / "catalog.json").read_bytes() == original
    api.build_catalog(library_root)
    assert (library_root / "catalog.json").read_bytes() == original
    assert (library_root / "inventory.json").read_bytes() == inventory


def test_lookup_search_and_skill_query_get_import_no_components(library_root, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("lookup attempted to execute component code")
    monkeypatch.setattr(api, "_with_module", forbidden)
    library = api.Library(library_root)
    assert library.search("email", kind="function")["total_matches"] == 1
    assert library.get("text.email_normalize")["effects"] == ["pure"]
    assert library.get("query-test")["payload"]["query"] == 'site:example.org "email"'
    assert "# Example" in library.get("skill.example-skill")["content"]
    summary = library.summary()
    assert summary["counts"] == library.counts
    assert summary["catalog_sha256"] == library.catalog_sha256
    assert summary["search_method"] == api.SEARCH_METHOD
    summary["counts"]["function"] = 0
    assert library.counts["function"] == 6


def test_lookup_does_not_require_function_source_reads(library_root, monkeypatch):
    library = api.Library(library_root)
    (library_root / "components/text/email_normalize.py").unlink()
    assert library.get("text.email_normalize")["id"] == "text.email_normalize"
    assert library.search("email", kind="function")["total_matches"] == 1
    with pytest.raises(api.IntegrityError):
        library.run("text.email_normalize", {"email": "A@example.org"})


def test_search_paginates_complete_population_and_uses_stable_ties(library_root):
    library = api.Library(library_root)
    all_results = library.search("", limit=1000)
    pages = [library.search("", limit=3, offset=offset) for offset in (0, 3, 6)]
    assert [page["next_offset"] for page in pages] == [3, 6, None]
    assert all(page["total_matches"] == 8 for page in pages)
    assert [entry["id"] for page in pages for entry in page["results"]] == [entry["id"] for entry in all_results["results"]]
    assert library.search("", limit=5, offset=100)["next_offset"] is None
    assert library.search("nonexistent-term-zqx")["results"] == []
    assert library.search("email_normalize")["results"][0]["id"] == "text.email_normalize"
    assert library.search("example-query-source", kind="query_preset")["total_matches"] == 1
    assert library.search("mailbox", kind="skill")["total_matches"] == 1
    for card in all_results["results"]:
        assert not {"input_schema", "output_schema", "examples", "dependencies", "source_refs", "payload", "payload_path"} & card.keys()
    assert library.search("", kind="query_preset")["results"][0]["query"] == 'site:example.org "email"'


@pytest.mark.parametrize("kwargs,error", [
    ({"query": 1}, TypeError), ({"query": "", "limit": True}, TypeError),
    ({"query": "", "offset": 1.0}, TypeError), ({"query": "", "limit": 0}, ValueError),
    ({"query": "", "offset": -1}, ValueError), ({"query": "", "kind": "tool"}, ValueError),
])
def test_search_rejects_bad_requests(library_root, kwargs, error):
    with pytest.raises(error):
        api.Library(library_root).search(**kwargs)


def test_run_text_and_search_contracts(library_root):
    library = api.Library(library_root)
    response = library.run("text.email_normalize", {"email": "A+Tag@EXAMPLE.ORG"})
    assert response == {"id": "text.email_normalize", "version": "1.0.0",
                        "sha256": library.get("text.email_normalize")["sha256"],
                        "result": {"status": "supported", "reason": "", "local": "A+Tag",
                                   "domain": "example.org", "normalized": "A+Tag@example.org"}}
    example = library.get("search.bm25_rank")["examples"][0]
    assert library.run("search.bm25_rank", example["input"])["result"] == example["output"]
    assert not any(name.startswith("_duecare_verified_") for name in sys.modules)


def test_run_unicode_original_offsets_and_no_input_mutation(library_root):
    payload = {"text": "ß SS İ", "lexicon": [{"term": "SS", "meanings": ["double"]}, {"term": "İ", "meanings": ["dotted"]}]}
    before = copy.deepcopy(payload)
    result = api.Library(library_root).run("text.slang_matches", payload)["result"]
    assert [(match["start"], match["end"]) for match in result["matches"]] == [(0, 1), (2, 4), (5, 6)]
    assert payload == before


@pytest.mark.parametrize("payload,error", [
    ({"email": 1}, TypeError), ({"email": "a@example.org", "extra": True}, ValueError),
    ({}, ValueError), ([], TypeError), ({"email": float("nan")}, ValueError),
    ({"email": b"bytes"}, TypeError), ({1: "value"}, TypeError),
])
def test_run_rejects_non_json_and_malformed_payloads(library_root, payload, error):
    with pytest.raises(error):
        api.Library(library_root).run("text.email_normalize", payload)


@pytest.mark.parametrize("identifier", ["query-test", "skill.example-skill"])
def test_data_records_are_never_executed(library_root, identifier):
    with pytest.raises(ValueError, match="only catalogued functions"):
        api.Library(library_root).run(identifier, {})


@pytest.mark.parametrize("identifier", ["os.system", "../text.email_normalize", "text._shared", "missing"])
def test_unknown_ids_cannot_become_code_paths(library_root, identifier):
    library = api.Library(library_root)
    with pytest.raises(KeyError):
        library.get(identifier)
    with pytest.raises(KeyError):
        library.run(identifier, {})


@pytest.mark.parametrize("relative", ["components/text/email_normalize.py", "components/text/_shared.py", "components/text/__init__.py", "__init__.py", "library.py"])
def test_tampered_source_or_helper_rejected_even_after_prior_run(library_root, relative):
    library = api.Library(library_root)
    assert library.run("text.email_normalize", {"email": "a@example.org"})["result"]["status"] == "supported"
    source = library_root / relative
    source.write_bytes(source.read_bytes() + b"\nraise RuntimeError('must never execute')\n")
    with pytest.raises(api.IntegrityError):
        library.run("text.email_normalize", {"email": "a@example.org"})


def test_missing_dependency_in_catalog_cannot_escape_closure(library_root):
    def mutate(catalog):
        item = next(entry for entry in catalog["entries"] if entry["id"] == "text.email_normalize")
        item["dependencies"].remove("components/text/_shared.py")
    mutate_catalog(library_root, mutate)
    with pytest.raises(api.IntegrityError, match="closure"):
        api.Library(library_root).run("text.email_normalize", {"email": "a@example.org"})


def test_catalog_metadata_tamper_is_detected_before_invocation(library_root):
    def mutate(catalog):
        next(entry for entry in catalog["entries"] if entry["id"] == "text.email_normalize")["description"] = "changed"
    mutate_catalog(library_root, mutate)
    with pytest.raises(api.IntegrityError, match="SPEC"):
        api.Library(library_root).run("text.email_normalize", {"email": "a@example.org"})


@pytest.mark.parametrize("bad_path", ["../outside.py", "/tmp/outside.py", "components/../outside.py", "components\\outside.py"])
def test_catalog_path_escape_is_rejected(library_root, bad_path):
    mutate_catalog(library_root, lambda catalog: catalog["files"].update({bad_path: "0" * 64}))
    with pytest.raises(api.IntegrityError):
        api.Library(library_root)


def test_symlink_source_and_root_are_rejected(library_root, tmp_path):
    source = library_root / "components/text/email_normalize.py"
    outside = tmp_path / "outside.py"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    with pytest.raises(api.IntegrityError, match="symlink"):
        api.Library(library_root).run("text.email_normalize", {"email": "a@example.org"})
    with pytest.raises(api.IntegrityError, match="symlink"):
        api.build_catalog(library_root)
    link = tmp_path / "library-link"
    link.symlink_to(library_root, target_is_directory=True)
    with pytest.raises(api.IntegrityError, match="symlink"):
        api.Library(link)


def test_payload_hashes_checked_on_get_and_full_check(library_root):
    library = api.Library(library_root)
    default = library.check()
    full = library.check(full=True)
    assert default["files_skipped"] == 1
    assert full["files_skipped"] == 0
    assert full["files_checked"] == default["files_checked"] + 1
    payload = library_root / "search_queries/items/te/query-test.json"
    payload.write_text('{"id":"query-test","query":"changed"}\n', encoding="utf-8")
    assert library.search("mailbox")["total_matches"] >= 1
    assert library.check()["ok"] is True
    with pytest.raises(api.IntegrityError):
        library.get("query-test")
    with pytest.raises(api.IntegrityError):
        library.check(full=True)


def test_skill_hash_checked_before_returning_content(library_root):
    skill = library_root / "skills/example-skill/SKILL.md"
    skill.write_text("changed", encoding="utf-8")
    with pytest.raises(api.IntegrityError):
        api.Library(library_root).get("skill.example-skill")


def test_upstream_discovery_is_hashed_searchable_metadata_never_code(library_root, monkeypatch):
    row = {"id": "upstream.example", "type": "upstream_reference", "title": "Example instruction file",
           "repository": "example/repository", "upstream_kind": "instructions", "path": "review/AGENTS.md",
           "source_url": "https://github.com/example/repository/blob/0000000000000000000000000000000000000000/review/AGENTS.md",
           "status": "discovered_unreviewed", "installed": False, "verified": False, "license_scope": "unreviewed"}
    payload = library_root / "discovery/upstream/items/example.json"
    write_json(payload, row)
    write_json(library_root / "discovery/upstream/catalog.jsonl", {**row, "payload_path": "items/example.json", "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest()})
    api.build_catalog(library_root)
    monkeypatch.setattr(api, "_with_module", lambda *args: pytest.fail("upstream metadata must not execute"))
    library = api.Library(library_root)
    assert library.summary()["counts"]["upstream_reference"] == 1
    result = library.search("instructions", kind="upstream_reference")
    assert result["total_matches"] == 1
    assert result["results"][0]["installed"] is False
    assert library.get("upstream.example")["payload"] == row
    with pytest.raises(ValueError, match="only catalogued functions"):
        library.run("upstream.example", {})
    assert library.check()["files_skipped"] == 2
    assert library.check(full=True)["files_skipped"] == 0
    payload.write_text("{}\n", encoding="utf-8")
    with pytest.raises(api.IntegrityError):
        library.get("upstream.example")


def test_result_contract_rejects_nonfinite_and_wrong_type(tmp_path):
    root = tmp_path / "minimal"
    group = root / "components/demo"
    group.mkdir(parents=True)
    module = group / "bad_result.py"
    specification = {"id": "demo.bad_result", "version": "1.0.0", "description": "Output contract fixture.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_schema": {"type": "object", "properties": {"value": {"type": "number"}}, "required": ["value"], "additionalProperties": False},
        "effects": ["pure"], "examples": [{"input": {}, "output": {"value": 1}}]}
    for returned in ("float('nan')", "True", "set()"):
        module.write_text("SPEC = " + repr(specification) + "\ndef run(payload):\n    return {'value': " + returned + "}\n", encoding="utf-8")
        api.build_catalog(root)
        with pytest.raises((TypeError, ValueError)):
            api.Library(root).run("demo.bad_result", {})


@pytest.mark.parametrize("value,schema,error", [
    (True, {"type": "integer"}, TypeError),
    (1, {"type": "boolean"}, TypeError),
    (True, {"enum": [1]}, ValueError),
    (float("inf"), {"type": "number"}, ValueError),
    ([1, 1], {"type": "array", "uniqueItems": True}, ValueError),
    ("x", {"type": "string", "minLength": 2}, ValueError),
    ([1, 2], {"type": "array", "maxItems": 1}, ValueError),
    ({"unknown": 1}, {"type": "object", "additionalProperties": False}, ValueError),
])
def test_stdlib_schema_validation_strictness(value, schema, error):
    with pytest.raises(error):
        api.validate(value, schema)


def test_cli_commands_emit_json_and_return_error_codes(library_root, capsys):
    prefix = ["--root", str(library_root)]
    assert main(prefix + ["list", "--limit", "2"]) == 0
    assert json.loads(capsys.readouterr().out)["total_matches"] == 8
    assert main(prefix + ["run", "text.email_normalize", "--input", '{"email":"A@EXAMPLE.ORG"}']) == 0
    assert json.loads(capsys.readouterr().out)["result"]["normalized"] == "A@example.org"
    assert main(prefix + ["get", "missing"]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["type"] == "KeyError"
    assert main(prefix + ["run", "text.email_normalize", "--input", '{"email":NaN}']) == 2
    assert json.loads(capsys.readouterr().out)["error"]["type"] == "ValueError"
    assert main(prefix + ["nonsense"]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["type"] == "ValueError"
    assert main(prefix + ["check", "--full"]) == 0
    assert json.loads(capsys.readouterr().out)["files_skipped"] == 0
    assert main(prefix + ["build"]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["function"] == 6


def test_python_module_entrypoint_reads_json_from_stdin(library_root):
    process = subprocess.run([sys.executable, "-m", "harness_components", "--root", str(library_root),
                              "run", "text.find_literal_spans"],
                             input='{"text":"ababa","needle":"aba","overlap":true}',
                             text=True, capture_output=True, cwd=PUBLIC_ROOT.parent, check=False)
    assert process.returncode == 0
    assert process.stderr == ""
    assert json.loads(process.stdout)["result"] == {"spans": [[0, 3], [2, 5]]}


def test_every_public_function_spec_and_example_crosses_registry_contract():
    catalog = api.build_catalog(PUBLIC_ROOT, write=False)
    functions = [entry for entry in catalog["entries"] if entry["kind"] == "function"]
    assert len(functions) >= 110
    for entry in functions:
        module = importlib.import_module("harness_components.components." + entry["id"])
        for example in entry["examples"]:
            api.validate(example["input"], entry["input_schema"])
            result = module.run(copy.deepcopy(example["input"]))
            api.validate(result, entry["output_schema"], "result")
            assert result == example["output"], entry["id"]
