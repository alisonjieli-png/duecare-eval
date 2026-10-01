"""Offline adapter fixtures verify integrity; they measure no model performance."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

import pytest

from duecare_eval import extensions as E
from duecare_eval.contracts import canonical, text_hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pack():
    value = E.starter_pack("fixture", "Example industry", "Evidence and worker choice")
    value["sources"]["sources"] = [{"id": "SRC", "title": "Illustrative source", "url": "https://example.org/research", "accessed_on": "2026-10-01",
        "summary": "A scoped fixture source entry.", "scope": "Illustration for integrity tests; no independently established legal finding."}]
    for case in value["cases"]:
        case["provenance"]["source_ids"] = ["SRC"]
    return value


def save_pack(path, pack):
    path.mkdir(parents=True, exist_ok=True)
    for role, name in E.FILES.items():
        data = ("".join(canonical(case) + "\n" for case in pack["cases"]) if role == "cases" else canonical(pack[role]) + "\n").encode()
        (path / name).write_bytes(data)
        pack["manifest"]["file_sha256"][role] = sha256(data).hexdigest()
    (path / "manifest.json").write_text(canonical(pack["manifest"]) + "\n")


def add_multilabel(pack):
    question = {"id": "indicators", "type": "multi_label", "prompt": "Which facts are supported independently?", "options": [
        {"id": "documents", "label": "Document access", "description": "Assess access to personal documents."},
        {"id": "wages", "label": "Wage withholding", "description": "Assess withheld wages independently."}]}
    pack["questions"]["questions"].append(question)
    for case in pack["cases"]:
        case["question_ids"].append("indicators")
        case["reference"]["answers"]["indicators"] = {"value": {"documents": "supported", "wages": "unknown"}, "evidence": []}


def test_starter_creation_load_hashes_counts_and_zero_model_calls(tmp_path):
    path = tmp_path / "new"
    summary = E.create_pack(path, "example", "Example industry", "A starter pair")
    assert summary["case_variants"] == 2 and summary["scenario_groups"] == 1 and summary["paired_groups"] == 1
    assert summary["model_calls_executed"] == summary["assessed_model_responses"] == 0
    assert summary["independent_human_validation"] is False
    assert set(p.name for p in path.iterdir()) == set(E.FILES.values()) | {"manifest.json"}
    loaded = E.load_pack(path)
    for role, name in E.FILES.items(): assert loaded["manifest"]["file_sha256"][role] == sha256((path / name).read_bytes()).hexdigest()


def test_nonempty_generator_destination_is_preserved(tmp_path):
    path = tmp_path / "existing"; path.mkdir(); original = path / "keep.txt"; original.write_text("User material")
    with pytest.raises(E.ExtensionError, match="nonempty_destination"): E.create_pack(path, "example", "Industry", "Title")
    assert original.read_text() == "User material" and len(list(path.iterdir())) == 1


def test_hidden_reference_tiers_and_source_labels_never_enter_any_payload(pack):
    pack["cases"][0]["evaluator"] = {"requested_tier": 5, "source_labels": {"private_marker": "SECRET_LABEL_ONLY"}, "reference_validation": "author_assigned"}
    # References differ from the visible content but remain evaluator-side.
    pack["cases"][0]["reference"]["answers"]["document_access"]["value"] = "unknown"
    for plugin in E.PLUGINS:
        before = deepcopy(pack)
        payload = E.build_payload(pack, "fixture-concern", plugin)
        serialized = canonical(payload)
        assert "SECRET_LABEL_ONLY" not in serialized and '"requested_tier"' not in serialized
        assert '"reference"' not in serialized and '"evaluator"' not in serialized and '"group_id"' not in serialized and '"provenance"' not in serialized
        assert pack == before
        other = deepcopy(pack); other["cases"][0]["evaluator"]["requested_tier"] = 1
        assert E.build_payload(other, "fixture-concern", plugin) == payload


def test_nested_allowlists_reject_unknown_fields_in_visible_catalog(pack):
    pack["questions"]["questions"][0]["options"][0]["hidden_reference"] = "ANSWER"
    with pytest.raises(E.ExtensionError, match="option_fields"): E.build_payload(pack, "fixture-concern")


def test_sources_are_explicit_and_case_scoped(pack):
    pack["sources"]["sources"].append({**pack["sources"]["sources"][0], "id": "UNUSED", "summary": "SHOULD_NOT_APPEAR"})
    bare = E.build_payload(pack, "fixture-concern")
    source_on = E.build_payload(pack, "fixture-concern", include_sources=True)
    assert "sources" not in json.loads(bare["messages"][1]["content"])
    view = json.loads(source_on["messages"][1]["content"])
    assert [s["id"] for s in view["sources"]] == ["SRC"] and "SHOULD_NOT_APPEAR" not in canonical(source_on)


def test_multilabel_jev_decomposition_and_native_values_are_distinct(pack):
    add_multilabel(pack)
    summary = E.validate_pack(pack)
    assert summary["case_question_slots"] == 4 and summary["semantic_judgment_slots"] == 6
    payload = E.build_payload(pack, "fixture-concern", "jev-typed")
    assert set(payload["questions"]) == {"document_access", "indicators__documents", "indicators__wages"}
    for key in ("indicators__documents", "indicators__wages"):
        assert payload["questions"][key]["type"] == "choice"
        assert set(payload["questions"][key]["criteria"]) == {"supported", "counterevidence", "unknown"}
    native = E.build_payload(pack, "fixture-concern", "chat-messages")
    assert "categorical answers, not probability estimates" in native["messages"][0]["content"]
    assert json.loads(native["messages"][1]["content"])["questions"][1]["type"] == "multi_label"


def test_ordinal_maps_to_jev_score_with_order_preserved(pack):
    question = deepcopy(pack["questions"]["questions"][0]); question.update(id="priority", type="ordinal")
    pack["questions"]["questions"].append(question)
    for case in pack["cases"]: case["question_ids"].append("priority")
    pack["cases"][0]["reference"]["answers"]["priority"] = {"value": 2, "evidence": []}
    value = E.build_payload(pack, "fixture-concern", "jev-typed")["questions"]["priority"]
    assert value["type"] == "score" and value["criteria"][2].startswith(question["options"][2]["label"])


def test_unknown_questions_can_remain_unscored_without_fabricating_gold(pack):
    for case in pack["cases"]: case["reference"]["answers"] = {}
    assert E.validate_pack(pack)["reference_entries"] == 0
    assert E.build_payload(pack, "fixture-concern")


@pytest.mark.parametrize("change,reason", [
    (lambda p: p["cases"].append(deepcopy(p["cases"][0])), "duplicate_case_id"),
    (lambda p: p["cases"][0]["question_ids"].append("missing"), "unknown_case_question"),
    (lambda p: p["cases"][0]["provenance"]["source_ids"].append("missing"), "unknown_provenance_source"),
    (lambda p: p["cases"][0]["reference"]["answers"].update(missing={"value": "unknown", "evidence": []}), "unknown_reference_question"),
    (lambda p: p["cases"][0]["reference"]["answers"]["document_access"].update(value="missing"), "reference_choice_unknown_option"),
    (lambda p: p["cases"][0]["reference"]["answers"]["document_access"]["evidence"][0].update(start=1), "evidence_quote_offset"),
    (lambda p: p["cases"][0].update(measured_grade=5), "case_fields"),
    (lambda p: p["cases"][0]["evaluator"].update(measured_grade=5), "evaluator_fields"),
    (lambda p: p["manifest"]["privacy"].update(contains_personal_data=True), "nonidentifying"),
    (lambda p: p["cases"][0].update(narrative=p["cases"][0]["narrative"] + " Changed."), "hash_mismatch"),
    (lambda p: p["manifest"]["groups"][0]["variant_ids"].append("missing"), "group_population"),
])
def test_integrity_and_unknown_ids_rejected(pack, change, reason):
    change(pack)
    with pytest.raises(E.ExtensionError, match=reason): E.validate_pack(pack)


def test_unicode_hashes_and_quote_offsets_preserved_exactly(pack):
    case = pack["cases"][0]; case["language"] = "tl"
    case["narrative"] = "Nasa manggagawa ang pasaporte. Café 🧭"
    case["narrative_sha256"] = text_hash(case["narrative"])
    quote = "pasaporte"; start = case["narrative"].index(quote)
    case["reference"]["answers"]["document_access"]["evidence"] = [{"field": "narrative", "quote": quote, "start": start, "end": start + len(quote), "source_ids": []}]
    E.validate_pack(pack)
    assert json.loads(E.build_payload(pack, case["case_id"])["messages"][1]["content"])["case"]["narrative"] == case["narrative"]


def test_source_verbatim_and_adapted_provenance_are_distinct(pack):
    source = pack["cases"][0]
    source["kind"] = "source_research"
    source["provenance"].update(origin="verbatim_source", original_text_sha256=source["narrative_sha256"], transformations=[])
    E.validate_pack(pack)
    source["provenance"]["transformations"] = ["Paraphrased"]
    with pytest.raises(E.ExtensionError, match="verbatim_source_binding"): E.validate_pack(pack)
    source["kind"] = "adapted_scenario"; source["provenance"]["origin"] = "adapted"
    E.validate_pack(pack)


def test_file_tamper_hash_and_path_traversal_and_symlink_rejected(tmp_path, pack):
    root = tmp_path / "pack"; save_pack(root, pack)
    (root / "cases.jsonl").write_text((root / "cases.jsonl").read_text() + "\n")
    with pytest.raises(E.ExtensionError, match="file_hash_mismatch"): E.load_pack(root)
    save_pack(root, pack)
    manifest = pack["manifest"]; manifest["files"]["cases"] = "../outside.jsonl"
    (root / "manifest.json").write_text(canonical(manifest))
    with pytest.raises(E.ExtensionError, match="fixed_pack_file_roles"): E.load_pack(root)
    manifest["files"] = E.FILES.copy(); save_pack(root, pack)
    external = tmp_path / "external.json"; external.write_bytes((root / "sources.json").read_bytes())
    (root / "sources.json").unlink(); (root / "sources.json").symlink_to(external)
    with pytest.raises(E.ExtensionError, match="escapes_root"): E.load_pack(root)


def test_duplicate_json_keys_are_rejected(tmp_path, pack):
    root = tmp_path / "pack"; save_pack(root, pack)
    raw = (root / "manifest.json").read_text().replace('"pack_id":"fixture"', '"pack_id":"fixture","pack_id":"other"')
    (root / "manifest.json").write_text(raw)
    with pytest.raises(ValueError, match="duplicate_json_key"): E.load_pack(root)


def test_manifest_symlink_cannot_escape_pack(tmp_path, pack):
    root = tmp_path / "pack"; save_pack(root, pack)
    outside = tmp_path / "outside.json"; outside.write_bytes((root / "manifest.json").read_bytes())
    (root / "manifest.json").unlink(); (root / "manifest.json").symlink_to(outside)
    with pytest.raises(E.ExtensionError, match="escapes_root"): E.load_pack(root)


def test_declared_plugins_are_data_only_with_no_untrusted_execution(pack, monkeypatch):
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network forbidden")))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("execution forbidden")))
    for name in E.PLUGINS:
        profile = E.load_plugin(ROOT / "plugins" / (name + ".json"))
        assert E.build_payload(pack, "fixture-concern", profile)
        hostile = {**profile, "entrypoint": "os.system", "command": "touch unauthorized"}
        with pytest.raises(E.ExtensionError, match="plugin_fields"): E.build_payload(pack, "fixture-concern", hostile)
    with pytest.raises(E.ExtensionError, match="unknown_plugin"): E.build_payload(pack, "fixture-concern", "../untrusted.py")


def test_batch_is_deterministic_opaque_and_preserves_exact_body_hash(pack):
    first = E.batch_payloads(pack); second = E.batch_payloads(pack)
    assert first == second and len({r["custom_id"] for r in first}) == 2
    assert all(r["custom_id"].startswith("EXT-") and "concern" not in r["custom_id"] for r in first)
    assert all(r["body_sha256"] == text_hash(canonical(r["body"])) for r in first)


@pytest.mark.parametrize("text", ["Contact actual.person@example.org.", "Call +1 202 555 0123."])
def test_obvious_contact_identifiers_rejected_without_claiming_full_privacy_validation(pack, text):
    case = pack["cases"][0]; case["narrative"] = text; case["narrative_sha256"] = text_hash(text)
    with pytest.raises(E.ExtensionError, match="identifier"): E.validate_pack(pack)


def test_cli_creation_check_and_exclusive_output(tmp_path, capsys):
    def tool(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
    create = tool("create_extension_pack"); check = tool("check_extension_pack")
    directory = tmp_path / "industry"; output = tmp_path / "blind.jsonl"
    created = create.main([str(directory), "--pack-id", "my-industry", "--industry", "Example", "--title", "My fixture"])
    checked = check.main([str(directory), "--plugin", str(ROOT / "plugins/jev-typed.json"), "--output", str(output)])
    assert created["case_variants"] == checked["prepared_payloads"] == 2
    assert checked["projected_typed_question_slots"] == 2
    assert len(output.read_text().splitlines()) == 2
    with pytest.raises(FileExistsError): check.main([str(directory), "--output", str(output)])


@pytest.mark.parametrize("change,reason", [
    (lambda p: p["questions"]["questions"].append(deepcopy(p["questions"]["questions"][0])), "duplicate_question_id"),
    (lambda p: p["sources"]["sources"].append(deepcopy(p["sources"]["sources"][0])), "duplicate_source_id"),
    (lambda p: p["questions"]["questions"][0]["options"].append(deepcopy(p["questions"]["questions"][0]["options"][0])), "duplicate_option_id"),
    (lambda p: p["rubric"]["dimensions"][0].update(weight=float("nan")), "positive_finite_dimension_weight"),
    (lambda p: p["rubric"]["dimensions"][0].update(weight=0.8), "weights_must_sum"),
    (lambda p: p["rubric"]["critical_flags"][0].update(maximum_tier=5), "critical_cap_tier"),
    (lambda p: p["sources"]["sources"][0].update(url="file:///etc/passwd"), "public_https_source_url"),
    (lambda p: p["sources"]["sources"][0].update(url="https://user:secret@example.org/source"), "public_https_source_url"),
    (lambda p: p["cases"][0]["evaluator"]["source_labels"].update(measured_grade="5"), "separate_observation_records"),
])
def test_catalog_rubric_and_source_edge_cases(pack, change, reason):
    change(pack)
    with pytest.raises(E.ExtensionError, match=reason): E.validate_pack(pack)


def test_incomplete_or_unknown_multilabel_population_rejected(pack):
    add_multilabel(pack)
    value = pack["cases"][0]["reference"]["answers"]["indicators"]["value"]
    value.pop("wages")
    with pytest.raises(E.ExtensionError, match="multilabel_population"): E.validate_pack(pack)
    value["wages"] = "legally_proven"
    with pytest.raises(E.ExtensionError, match="multilabel_population"): E.validate_pack(pack)


def test_projected_jev_question_collision_rejected(pack):
    add_multilabel(pack)
    question = deepcopy(pack["questions"]["questions"][0]); question["id"] = "indicators__documents"
    pack["questions"]["questions"].append(question)
    with pytest.raises(E.ExtensionError, match="question_id_collision"): E.validate_pack(pack)


def test_ordinal_boolean_is_not_a_valid_reference(pack):
    pack["questions"]["questions"][0]["type"] = "ordinal"
    pack["cases"][0]["reference"]["answers"]["document_access"]["value"] = True
    with pytest.raises(E.ExtensionError, match="ordinal_range"): E.validate_pack(pack)


@pytest.mark.parametrize("industry", ["agriculture", "construction", "manufacturing", "hospitality", "maritime", "platform_delivery"])
def test_substantive_industry_packs_all_three_adapters(industry):
    pack = E.load_pack(ROOT / "examples/industry_packs" / industry)
    summary = E.validate_pack(pack)
    assert summary["case_variants"] == 2 and summary["paired_groups"] == 1
    assert summary["case_question_slots"] == 4 and summary["semantic_judgment_slots"] == 24
    assert summary["reference_entries"] == 2 and summary["model_calls_executed"] == 0
    for case in pack["cases"]:
        assert len(case["narrative"].split()) >= 300
        for profile in E.PLUGINS:
            bare = E.build_payload(pack, case["case_id"], profile)
            contextual = E.build_payload(pack, case["case_id"], profile, include_sources=True)
            assert bare != contextual
            assert '"reference"' not in canonical(bare) and '"requested_tier"' not in canonical(contextual)
        jev = E.build_payload(pack, case["case_id"], "jev-typed")
        assert len(jev["questions"]) == 12
