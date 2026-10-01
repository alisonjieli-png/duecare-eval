"""Offline knowledge-edge checks use fixtures and make zero model calls."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from duecare_eval.contracts import canonical, text_hash
from duecare_eval.extensions import PLUGINS
from duecare_eval.knowledge import KnowledgeLibrary, KnowledgeError, describe_operations

ROOT = Path(__file__).resolve().parents[1]
PACK_IDS = ["duecare-" + industry + "-starter" for industry in
            ("agriculture", "construction", "manufacturing", "hospitality", "maritime", "platform-delivery")]


@pytest.fixture(scope="module")
def library():
    return KnowledgeLibrary(ROOT)


@pytest.fixture
def copied_root(tmp_path):
    target = tmp_path / "public"
    for relative in ("examples/industry_packs", "examples/narrative_indicators_v2"):
        if relative.endswith("narrative_indicators_v2"):
            folder = target / relative; folder.mkdir(parents=True)
            for name in ("catalog.json", "manifest.json"):
                shutil.copyfile(ROOT / relative / name, folder / name)
        else:
            shutil.copytree(ROOT / relative, target / relative)
    (target / "results").mkdir()
    name = "results/documented_indicator_sources_2026-10-01.json"
    shutil.copyfile(ROOT / name, target / name)
    return target


def save_cases(root, cases):
    folder = root / "examples/industry_packs/agriculture"
    raw = "".join(canonical(case) + "\n" for case in cases).encode()
    (folder / "cases.jsonl").write_bytes(raw)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["file_sha256"]["cases"] = sha256(raw).hexdigest()
    (folder / "manifest.json").write_text(canonical(manifest))


def test_catalog_is_scoped_and_zero_call(library):
    value = library.catalog()
    assert len(value["packs"]) == 6 and len(value["sources"]) == 9
    assert len(value["indicator_ids"]) == 11 and len(value["action_ids"]) == 8
    assert len(value["followup_ids"]) == 11
    assert value["model_calls_executed"] == 0 and value["independent_human_validation"] is False
    assert not {"reference", "groups", "evaluator"} & set(value)


@pytest.mark.parametrize("pack_id", PACK_IDS)
@pytest.mark.parametrize("profile", sorted(PLUGINS))
@pytest.mark.parametrize("include_sources", [False, True])
def test_preparation_is_deterministic_and_preserves_visible_content(library, pack_id, profile, include_sources):
    prepared = library.prepare_benchmark(pack_id, profile, include_sources)
    assert prepared == library.prepare_benchmark(pack_id, profile, include_sources)
    assert prepared["prepared_requests"] == 2 and prepared["model_calls_executed"] == 0
    assert prepared["prepared_sha256"] == text_hash(canonical(prepared["records"]))
    forbidden = {"reference", "evaluator", "group_id", "variant_id", "requested_tier", "source_labels", "provenance"}
    def walk(value):
        if isinstance(value, dict):
            assert not set(value) & forbidden
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    for record in prepared["records"]:
        assert record["case_id"].startswith("case-") and len(record["case_id"]) == 69
        assert record["payload_sha256"] == text_hash(canonical(record["payload"]))
        payload = record["payload"]
        if profile == "jev-typed":
            view = payload["state"]
        else:
            body = payload["body"] if profile == "jsonl-batch" else payload
            view = json.loads(body["messages"][1]["content"])
        assert len(view["case"]["narrative"].split()) > 400
        assert ("sources" in view) is include_sources
        walk(view)


def test_hidden_reference_and_source_identity_changes_do_not_change_edge(copied_root):
    before = KnowledgeLibrary(copied_root)
    pack = "duecare-agriculture-starter"
    cases = [json.loads(line) for line in (copied_root / "examples/industry_packs/agriculture/cases.jsonl").read_text().splitlines()]
    for index, case in enumerate(cases):
        case["case_id"] = "renamed-" + str(index)
        case["title"] = "EVALUATOR_TITLE_SENTINEL"
        case["reference"]["answers"] = {}
        case["evaluator"]["requested_tier"] = 5
        case["evaluator"]["source_labels"] = {"private_marker": "EVALUATOR_LABEL_SENTINEL"}
    save_cases(copied_root, cases)
    after = KnowledgeLibrary(copied_root)
    assert before.catalog() == after.catalog()
    assert before.list_cases(pack) == after.list_cases(pack)
    for profile in PLUGINS:
        for sources in (False, True):
            assert before.prepare_benchmark(pack, profile, sources) == after.prepare_benchmark(pack, profile, sources)


@pytest.mark.parametrize("operation,arguments", [
    ("__dict__", {}), ("_read_public", {"relative": "NOTICE"}),
    ("catalog", {"root": "/tmp"}), ("list_cases", {}),
    ("list_cases", {"pack_id": "../private"}), ("list_cases", {"pack_id": "/etc/passwd"}),
    ("get_source", {"source_id": "file:///etc/passwd"}),
    ("get_source", {"source_id": "UNKNOWN"}),
    ("get_case_payload", {"pack_id": PACK_IDS[0], "case_id": "agriculture-concern"}),
    ("prepare_benchmark", {"pack_id": PACK_IDS[0], "include_sources": "false"}),
    ("prepare_benchmark", {"pack_id": PACK_IDS[0], "include_sources": 1}),
    ("prepare_benchmark", {"pack_id": PACK_IDS[0], "profile": "run_shell"}),
    ("get_action_template", {"action_id": "contact_police"}),
])
def test_unknown_inputs_paths_and_coercions_rejected(library, operation, arguments):
    with pytest.raises(KnowledgeError): library.dispatch(operation, arguments)


def test_generic_templates_rubric_and_source_provenance(library):
    source = library.get_source("PALERMO_PROTOCOL_2000")
    assert "Article 3" in source["source"]["location"]
    assert source["provenance"]["reviewed_on"] == "2026-10-01"
    assert len(source["provenance"]["sha256"]) == 64
    indicator = library.get_indicator("debt_bondage")
    assert indicator["source_ids"] == ["ILO_INDICATORS_2025_FULL"]
    assert "worker" in indicator["indicator"]["definition"]
    assert "privat" in library.get_action_template("private_safety_check")["text"]
    assert "safe" in library.get_followup_template("safe_contact")["text"]
    rubric = library.get_rubric(PACK_IDS[0])
    assert len(rubric["rubric"]["dimensions"]) == 6
    assert sum(d["weight"] for d in rubric["rubric"]["dimensions"]) == pytest.approx(1)


def test_returned_values_cannot_mutate_snapshot(library):
    catalog = library.catalog(); catalog["packs"].clear()
    rubric = library.get_rubric(PACK_IDS[0]); rubric["rubric"]["dimensions"].clear()
    source = library.get_source("PALERMO_PROTOCOL_2000"); source["source"]["summary"] = "CHANGED"
    assert len(library.catalog()["packs"]) == 6
    assert len(library.get_rubric(PACK_IDS[0])["rubric"]["dimensions"]) == 6
    assert library.get_source("PALERMO_PROTOCOL_2000")["source"]["summary"] != "CHANGED"


def test_operation_contract_is_isolated_and_pure(copied_root, monkeypatch):
    contract = describe_operations(); contract["operations"].clear()
    assert len(describe_operations()["operations"]) == 9
    def forbidden(*args, **kwargs): raise AssertionError("network or process use forbidden")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    before = {p.relative_to(copied_root): sha256(p.read_bytes()).hexdigest() for p in copied_root.rglob("*") if p.is_file()}
    library = KnowledgeLibrary(copied_root)
    library.prepare_benchmark(PACK_IDS[0])
    after = {p.relative_to(copied_root): sha256(p.read_bytes()).hexdigest() for p in copied_root.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize("member", ["manifest.json", "cases.jsonl", "questions.json", "rubric.json", "sources.json"])
def test_symlinks_inside_pack_rejected(copied_root, tmp_path, member):
    target = copied_root / "examples/industry_packs/agriculture" / member
    external = tmp_path / member; external.write_bytes(target.read_bytes())
    target.unlink(); target.symlink_to(external)
    with pytest.raises(KnowledgeError, match="symlink"): KnowledgeLibrary(copied_root)


def test_symlink_root_and_directory_rejected(copied_root, tmp_path):
    link = tmp_path / "alias"; link.symlink_to(copied_root, target_is_directory=True)
    with pytest.raises(KnowledgeError, match="symlink"): KnowledgeLibrary(link)
    original = copied_root / "examples/industry_packs/agriculture"
    moved = tmp_path / "moved"; original.rename(moved); original.symlink_to(moved, target_is_directory=True)
    with pytest.raises(KnowledgeError, match="symlink"): KnowledgeLibrary(copied_root)


def test_catalog_path_escape_and_tamper_rejected(copied_root):
    path = copied_root / "examples/industry_packs/library.json"
    original = path.read_text(); data = json.loads(original)
    data["packs"][0]["path"] = "../../private"
    path.write_text(canonical(data))
    with pytest.raises(KnowledgeError, match="allowlist"): KnowledgeLibrary(copied_root)
    path.write_text(original)
    target = copied_root / "examples/industry_packs/agriculture/cases.jsonl"
    target.write_text(target.read_text() + "\n")
    with pytest.raises(KnowledgeError, match="hash_mismatch"): KnowledgeLibrary(copied_root)


@pytest.mark.parametrize("relative,reason", [
    ("results/documented_indicator_sources_2026-10-01.json", "source_packet_hash_mismatch"),
    ("examples/narrative_indicators_v2/catalog.json", "narrative_catalog_hash_mismatch"),
])
def test_source_and_template_tamper_rejected(copied_root, relative, reason):
    target = copied_root / relative; target.write_text(target.read_text() + "\n")
    with pytest.raises(KnowledgeError, match=reason): KnowledgeLibrary(copied_root)


def test_private_and_reference_files_are_never_read(copied_root, monkeypatch):
    called = []
    original = KnowledgeLibrary._read_public
    def observed(self, path):
        called.append(path)
        assert "references.jsonl" not in path and "runs/" not in path
        return original(self, path)
    monkeypatch.setattr(KnowledgeLibrary, "_read_public", observed)
    KnowledgeLibrary(copied_root)
    assert len(called) == 34
