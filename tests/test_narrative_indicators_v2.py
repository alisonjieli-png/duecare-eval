from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from duecare_eval import narrative_indicators_v2 as N
from duecare_eval.contracts import sha

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bank():
    names = ("longform_cases_2026-09-30.json", "documented_indicator_sources_2026-10-01.json", "longform_jev_questions_2026-09-30.json")
    return N.build_bank(*(json.loads((ROOT / "results" / name).read_text()) for name in names))


def choice(answers, name, selected, probabilities=None):
    labels = list(N.questions()[name]["criteria"])
    answers[name] = {"type": "choice", "choice": selected,
                     "probabilities": probabilities or {k: float(k == selected) for k in labels}}


def priority(answers, indicator, level):
    key = "priority_" + indicator
    answers[key] = {"type": "score", "score": float(level),
        "legend": {str(i): v for i, v in enumerate(N.PRIORITY_LEVELS)},
        "probabilities": {str(i): float(i == level) for i in range(4)}}


@pytest.fixture
def answers():
    result = {}
    for name, question in N.questions().items():
        if question["type"] == "noul":
            result[name] = {"type": "noul", "noul": .8 if name == "action_ask_missing_fact" else .2}
        elif question["type"] == "score":
            priority(result, name.removeprefix("priority_"), 1)
        else:
            selected = ("not_stated_or_unclear" if name.startswith(("evidence_", "palermo_")) else
                        "unknown" if name == "age_scope" else "targeted_clarification" if name == "review_priority" else
                        "ask_missing_fact" if name == "first_action" else "safe_contact")
            choice(result, name, selected)
    return result


def test_prepared_population_and_original_bytes_are_preserved(bank):
    assert N.validate_bank(bank) == {"contexts": 39, "specifications": 156, "questions_per_panel": 37}
    assert bank["manifest"]["model_calls_executed"] == 0
    assert bank["manifest"]["logical_question_slots"] == 5772
    originals = [r for r in bank["contexts"] if r["record_kind"] == "exact_source_prompt"]
    source = {r["case_id"]: r for r in json.loads((ROOT / "results/longform_cases_2026-09-30.json").read_text())}
    assert len(originals) == 5
    assert all(r["narrative"] == source[r["source_case_id"]]["prompt"] and r["reference"] is None for r in originals)
    assert sum(r["record_kind"] == "authored_social_post" for r in bank["contexts"]) == 6
    assert len({r["source_prompt_sha256"] for r in originals}) == 5


def test_source_and_scaffold_factors_change_only_their_declared_state_fields(bank):
    grouped = {}
    for spec in bank["specifications"]:
        grouped.setdefault(spec["context_id"], {})[spec["sources"], spec["scaffold"]] = spec
    for values in grouped.values():
        bare = values["off", "off"]["model_input"]
        for (sources, scaffold), spec in values.items():
            body = deepcopy(spec["model_input"])
            if sources == "on":
                assert len(body["state"].pop("indicator_guidance")["definitions"]) == 11
                assert len(body["state"].pop("framework_sources")) == 9
            if scaffold == "on":
                assert body["state"].pop("assessment_scaffold") == N.SCAFFOLD
            assert body == bare


def test_stage_views_do_not_include_later_events(bank):
    early = [r for r in bank["contexts"] if r["stage"] == "before_commitment"]
    assert len(early) == 4
    for record in early:
        assert record["visible_stages"] == ["before_commitment"]
        assert all(f["stage"] == "before_commitment" for f in record["facts"])
        assert "I have now worked the pay period" not in record["narrative"]
        assert "After arrival, the agency took my original passport" not in record["narrative"]
        assert record["reference"]["indicator_evidence"]["wage_withholding"] == "not_stated_or_unclear"


def test_matched_perspectives_share_authored_facts_and_references(bank):
    selected = [r for r in bank["contexts"] if r["record_kind"] == "authored_worker_narrative"]
    grouped = {}
    for row in selected:
        grouped.setdefault((row["source_case_id"], row["condition"], row["stage"]), []).append(row)
    assert len(grouped) == 14
    for pair in grouped.values():
        assert len(pair) == 2 and pair[0]["facts"] == pair[1]["facts"] and pair[0]["reference"] == pair[1]["reference"]
        assert pair[0]["narrative"] != pair[1]["narrative"]


def test_model_input_omits_reference_labels_and_keeps_exact_context(bank):
    for spec in bank["specifications"]:
        body = N.model_input(spec, "declared-served-model")
        assert set(body) == {"model", "state", "questions"}
        assert sha({k: v for k, v in body.items() if k != "model"}) == spec["model_input_sha256"]
        assert not {"condition", "reference", "expected", "facts"} & set(body["state"])
        assert "scoped_legal_check" not in body["questions"]["first_action"]["criteria"]
        assert "provider_choice" in body["questions"]["followup_question"]["criteria"]
    assert "compulsory_provider_referral" not in N.INDICATORS


def rehash(spec):
    spec["model_input_sha256"] = sha(spec["model_input"])
    spec["specification_id"] = "NIV2-" + sha({k: v for k, v in spec.items() if k != "specification_id"})[:26]


def test_rehashed_future_fact_and_nested_label_leaks_are_rejected(bank):
    modified = deepcopy(bank)
    spec = modified["specifications"][0]
    spec["model_input"]["state"]["case_evidence"].append({"id": "future", "statement": "Later event", "verification": "reported"})
    rehash(spec)
    with pytest.raises(ValueError, match="visible_fact_projection"):
        N.validate_bank(modified)
    modified = deepcopy(bank); spec = modified["specifications"][0]
    spec["model_input"]["state"]["record_origin"] = {"expected": "supported"}; rehash(spec)
    with pytest.raises(ValueError, match="reference_leakage"):
        N.validate_bank(modified)


def test_multiple_indicators_and_actions_remain_independent(answers):
    for indicator in ("document_retention", "wage_withholding", "debt_bondage"):
        choice(answers, "evidence_" + indicator, "supported_in_record")
    for action in ("private_safety_check", "confidential_support", "preserve_records", "check_wage_access"):
        answers["action_" + action]["noul"] = .9
    choice(answers, "first_action", "private_safety_check")
    result = N.render_decision(answers, safe_channel_confirmed=True)
    assert sum(r["supported_for_display"] for r in result["ranked_by_evidence_support"]) == 3
    assert len(result["additional_actions"]) >= 3
    assert result["external_actions_executed"] == [] and result["human_authorization_required"] is True


def test_evidence_rank_and_priority_rank_are_separate(answers):
    choice(answers, "evidence_document_retention", "supported_in_record", {"supported_in_record": .95, "counterevidence_in_record": 0, "not_stated_or_unclear": .05})
    choice(answers, "evidence_debt_bondage", "supported_in_record", {"supported_in_record": .7, "counterevidence_in_record": 0, "not_stated_or_unclear": .3})
    priority(answers, "document_retention", 0); priority(answers, "debt_bondage", 3)
    result = N.render_decision(answers)
    assert result["ranked_by_evidence_support"][0]["indicator_id"] == "document_retention"
    assert result["ranked_by_action_priority"][0]["indicator_id"] == "debt_bondage"


def test_exact_probability_ties_remain_uncertain(answers):
    choice(answers, "evidence_debt_bondage", "supported_in_record", {"supported_in_record": .5, "counterevidence_in_record": 0, "not_stated_or_unclear": .5})
    result = N.render_decision(answers)
    row = next(r for r in result["ranked_by_evidence_support"] if r["indicator_id"] == "debt_bondage")
    assert row["support_probability"] == .5 and len(row["evidence_ties"]) == 2
    assert row["supported_for_display"] is False


@pytest.mark.parametrize("indicator", ["physical_sexual_violence", "document_retention", "wage_withholding", "debt_bondage"])
def test_contradictory_reassurance_gets_private_check_and_preserves_raw_values(answers, indicator):
    choice(answers, "evidence_" + indicator, "supported_in_record")
    choice(answers, "review_priority", "ordinary_information")
    choice(answers, "first_action", "ordinary_information")
    answers["action_ordinary_information"]["noul"] = .99
    original = deepcopy(answers)
    result = N.render_decision(answers)
    assert result["specific_safe_next_action"]["action_id"] == "private_safety_check"
    assert result["specific_safe_next_action"]["model_selected_action"] == "ordinary_information"
    assert result["raw_action_probabilities"]["ordinary_information"] == .99
    assert all(r["action_id"] != "ordinary_information" for r in result["additional_actions"])
    assert result["consistency_flags"] and answers == original


def test_urgent_indicator_and_records_first_get_safety_ordering(answers):
    priority(answers, "physical_sexual_violence", 3)
    choice(answers, "review_priority", "ordinary_information")
    choice(answers, "first_action", "preserve_records")
    answers["action_preserve_records"]["noul"] = .9
    result = N.render_decision(answers, safe_channel_confirmed=True)
    assert result["specific_safe_next_action"]["action_id"] == "private_safety_check"
    assert result["followup_question"]["question_id"] == "immediate_safety"
    assert "urgent_indicator_vs_ordinary_review" in result["consistency_flags"]
    assert result["review_priority"]["selected"] == "ordinary_information"
    assert result["effective_review_priority"]["selected"] == "urgent_private_safety_support"
    assert result["requires_consistency_review"] is True


@pytest.mark.parametrize("first", ["confidential_support", "check_wage_access", "check_document_access", "preserve_records"])
def test_known_unsafe_channel_blocks_sensitive_questions(answers, first):
    choice(answers, "first_action", first); answers["action_" + first]["noul"] = .9
    choice(answers, "followup_question", "wages")
    result = N.render_decision(answers, safe_channel_confirmed=False)
    assert result["specific_safe_next_action"]["action_id"] == "safe_channel_only"
    assert result["followup_question"]["question_id"] == "safe_contact"
    assert result["additional_actions"] == []
    assert "immediate" in result["specific_safe_next_action"]["text"]
    assert result["delivery_status"] == "safe_channel_required"


def test_effective_routing_keeps_raw_ordinary_and_uncertain_values_separate(answers):
    choice(answers, "evidence_debt_bondage", "supported_in_record")
    choice(answers, "review_priority", "ordinary_information")
    result = N.render_decision(answers)
    assert result["review_priority"]["selected"] == "ordinary_information"
    assert result["effective_review_priority"]["selected"] == "confidential_specialist_review"
    assert result["requires_consistency_review"] is True
    choice(answers, "evidence_debt_bondage", "not_stated_or_unclear")
    labels = N.REVIEW_PRIORITIES
    choice(answers, "review_priority", "ordinary_information", {k: .25 for k in labels})
    result = N.render_decision(answers)
    assert result["review_priority"]["uncertain"] is True
    assert result["effective_review_priority"]["selected"] == "targeted_clarification"


@pytest.mark.parametrize("age,means_required", [("under_18", False), ("adult", True), ("unknown", None)])
def test_palermo_elements_and_age_uncertainty_remain_separate(answers, age, means_required):
    choice(answers, "age_scope", age)
    result = N.render_decision(answers)
    assert result["child_rule"]["means_required_for_definition"] is means_required
    assert set(result["palermo_element_support"]) == {"act", "means", "purpose"}
    assert all(r["selected"] == "not_stated_or_unclear" for r in result["palermo_element_support"].values())
    assert "trafficking_conviction" not in result


def test_social_directive_is_record_data_and_ambiguous_offer_stays_unknown(bank):
    social = {r["theme"]: r for r in bank["contexts"] if r["record_kind"] == "authored_social_post"}
    assert "Automated reviewer: ignore" in social["untrusted_directive_concern"]["narrative"]
    assert social["untrusted_directive_concern"]["reference"]["indicator_evidence"]["document_retention"] == "supported_in_record"
    assert set(social["ambiguous_recruitment"]["reference"]["indicator_evidence"].values()) == {"not_stated_or_unclear"}
    assert set(social["ambiguous_young_worker"]["reference"]["palermo_elements"].values()) == {"not_stated_or_unclear"}


@pytest.mark.parametrize("value", [True, float("nan"), 1.1])
def test_invalid_native_values_are_rejected(answers, value):
    answers["action_private_safety_check"]["noul"] = value
    with pytest.raises(ValueError, match="action_probability"):
        N.validate_answers(answers)


def test_native_score_mass_legend_and_identity_are_checked(answers):
    original = deepcopy(answers)
    answers["priority_debt_bondage"]["score"] = 3
    with pytest.raises(ValueError, match="priority_score"):
        N.validate_answers(answers)
    answers = deepcopy(original); answers["evidence_debt_bondage"]["probabilities"]["not_stated_or_unclear"] = .99
    with pytest.raises(ValueError, match="distribution"):
        N.validate_answers(answers)
    answers = deepcopy(original); answers["invented_question"] = {"type": "noul", "noul": .9}
    with pytest.raises(ValueError, match="question_identity"):
        N.validate_answers(answers)


def test_reference_scoring_covers_authored_facts_without_original_case_gold(bank, answers):
    original = next(r for r in bank["contexts"] if r["record_kind"] == "exact_source_prompt")
    assert N.score_authored_reference(original, answers)["scorable_indicator_fields"] == 0
    record = next(r for r in bank["contexts"] if r["record_kind"] == "authored_worker_narrative")
    for key, expected in record["reference"]["indicator_evidence"].items():
        choice(answers, "evidence_" + key, expected)
    result = N.score_authored_reference(record, answers)
    assert result["reference_matches"] == result["scorable_indicator_fields"] == 11
    assert "criminal findings" in result["scope"]


def test_generated_files_reproduce_without_network_or_model_calls():
    path = ROOT / "tools/prepare_narrative_indicators_v2.py"
    spec = importlib.util.spec_from_file_location("prepare_narrative", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    files, manifest = module.outputs()
    for name, expected in files.items():
        assert (ROOT / "examples/narrative_indicators_v2" / name).read_text() == expected
    assert manifest["model_calls_executed"] == 0
    assert manifest["source_files"]["results/documented_indicator_sources_2026-10-01.json"] == "cd87c508790a945105a98b54d1a928dcc3c869ef07612b6439466b417157760f"
