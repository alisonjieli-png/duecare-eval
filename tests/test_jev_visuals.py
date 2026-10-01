from copy import deepcopy
import json
from pathlib import Path

import pytest

from duecare_eval import comparison_analysis as CA
from duecare_eval.jev_visuals import context_panels, reproduce, shared_tasks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def comparison_data():
    directory = ROOT / "results/comparison_2026-09-30"
    return ([t for t in CA.rows(directory / "tasks.jsonl") if t["suite"] == "crossborder"],
            [r for r in CA.rows(directory / "observations.jsonl") if r["suite"] == "crossborder"],
            CA.rows(ROOT / "examples/crossborder_references.jsonl"),
            CA.rows(ROOT / "examples/crossborder_blind_inputs.jsonl"))


@pytest.fixture(scope="module")
def panels_data():
    return tuple(json.loads((ROOT / f"results/longform_{name}_2026-09-30.json").read_text())
                 for name in ("cases", "jev_panels", "jev_questions"))


def test_frozen_visual_data_reproduces_and_preserves_coverage():
    result = reproduce(ROOT)
    assert result == json.loads((ROOT / "results/jev_visuals_2026-09-30.json").read_text())
    comparison = result["shared_typed_comparison"]
    assert comparison["requested_per_model"] == 937
    assert comparison["matched_tasks"] == 117
    assert comparison["requested_outside_shared_intersection"] == 820
    assert comparison["coverage"]["jev"]["usable"] == 937
    assert comparison["coverage"]["deepseek-flash"]["usable"] == 119
    assert comparison["coverage"]["deepseek-flash"]["recorded_unusable"] == 1
    assert comparison["coverage"]["deepseek-flash"]["missing"] == 817
    assert comparison["coverage"]["gemma-abliterated"]["recorded_unusable"] == 23
    screening = comparison["families"]["crossborder_screening"]
    assert screening["requested_per_model"] == 288
    assert screening["matched_tasks"] == 31
    assert screening["matched_scenario_groups"] == 16
    assert {m: r["correct"] for m, r in screening["models"].items()} == {
        "jev": 30, "gpt-oss-20b": 26, "deepseek-flash": 30,
        "kimi-k3": 30, "gemma4-31b": 30, "gemma-abliterated": 24}
    sharing = comparison["families"]["safe_action_boundary"]
    assert sharing["requested_per_model"] == 576
    assert sharing["matched_tasks"] == 32
    assert all(r["correct"] == r["usable"] == 32 for r in sharing["models"].values())
    assert sharing["questions"] == ["Under the stated action policy, is sending the redacted summary authorized now?"]
    assert sum(f["matched_tasks"] for f in comparison["families"].values()) == 117
    arithmetic = comparison["families"]["financial_arithmetic"]
    assert arithmetic["models"]["jev"]["correct"] == 6
    assert arithmetic["matched_tasks"] == 13


def test_full_blind_contract_and_reference_digest_are_checked(comparison_data):
    tasks, observations, references, blind = deepcopy(comparison_data)
    blind[0]["state"]["worker_authorized_exact_sharing"] = True
    with pytest.raises(ValueError, match="blind_input_contract"):
        shared_tasks(tasks, observations, references, blind)
    tasks, observations, references, blind = deepcopy(comparison_data)
    tasks[0]["task_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="projection_reference"):
        shared_tasks(tasks, observations, references, blind)


def test_unknown_or_duplicate_shared_observations_are_rejected(comparison_data):
    tasks, observations, references, blind = deepcopy(comparison_data)
    observations[0]["model_id"] = "unmeasured-future-model"
    with pytest.raises(ValueError, match="unknown_or_duplicate"):
        shared_tasks(tasks, observations, references, blind)
    tasks, observations, references, blind = deepcopy(comparison_data)
    with pytest.raises(ValueError, match="unknown_or_duplicate"):
        shared_tasks(tasks, observations + [observations[0]], references, blind)


def test_exact_shared_intersection_excludes_missing_tasks(comparison_data):
    tasks, observations, references, blind = comparison_data
    base = shared_tasks(tasks, observations, references, blind)
    key = base["families"]["crossborder_screening"]["shared_task_ids"][0]
    fewer = [r for r in observations if (r["model_id"], r["task_id"]) != ("jev", key)]
    result = shared_tasks(tasks, fewer, references, blind)
    assert result["requested_per_model"] == 937
    assert result["matched_tasks"] == 116
    assert result["coverage"]["jev"]["missing"] == 1
    assert result["families"]["crossborder_screening"]["matched_tasks"] == 30


def test_full_context_preserves_raw_polarity_and_separate_strata(panels_data):
    result = context_panels(*panels_data)
    assert result["panels_requested"] == result["panels_completed"] == 10
    assert result["typed_answers"] == 120
    assert result["strata"]["original_advice"] == {
        "cases": 4, "panels_requested": 8, "panels_completed": 8,
        "typed_answers": 96, "binary_answers": 80, "categorical_answers": 16}
    assert result["strata"]["explicit_analysis_variant"]["typed_answers"] == 24
    case1 = next(r for r in result["panels"] if r["case_id"] == "WRITEUP-16674-CASE-1" and r["arm"] == "bare")
    assert case1["binary_probabilities"]["financial_pressure"] == .9
    assert case1["binary_probabilities"]["consent_sufficiency"] == .1
    assert case1["binary_probabilities"]["crime_conclusion"] == .04
    assert "Raw model probabilities" in result["interpretation"]["quantity"]


@pytest.mark.parametrize("probability", [True, None, float("nan"), 1.1, -.1])
def test_invalid_raw_probabilities_are_rejected(panels_data, probability):
    cases, panels, questions = deepcopy(panels_data)
    panels[0]["validated_answers"]["financial_pressure"]["probability"] = probability
    with pytest.raises(ValueError, match="invalid_panel_probability"):
        context_panels(cases, panels, questions)


def test_choice_mass_and_selected_membership_stay_strict(panels_data):
    cases, panels, questions = deepcopy(panels_data)
    choice = panels[0]["validated_answers"]["priority_next_step"]
    choice["probabilities"]["check_crossborder_applicability"] -= .01
    with pytest.raises(ValueError, match="choice_probabilities"):
        context_panels(cases, panels, questions)
    cases, panels, questions = deepcopy(panels_data)
    panels[0]["validated_answers"]["priority_next_step"]["selected"] = "invented-remedy"
    with pytest.raises(ValueError, match="selected_value"):
        context_panels(cases, panels, questions)


def test_panel_source_identity_duplicates_and_extra_fields_fail(panels_data):
    cases, panels, questions = deepcopy(panels_data)
    cases[0]["prompt"] += " editorial addition"
    with pytest.raises(ValueError, match="source_case_digest"):
        context_panels(cases, panels, questions)
    cases, panels, questions = deepcopy(panels_data)
    with pytest.raises(ValueError, match="duplicate_panel"):
        context_panels(cases, panels + [panels[0]], questions)
    panels[0]["unreviewed_text"] = "unexpected field"
    with pytest.raises(ValueError, match="panel_fields"):
        context_panels(cases, panels, questions)


def test_missing_panel_remains_in_requested_denominator(panels_data):
    cases, panels, questions = panels_data
    result = context_panels(cases, panels[1:], questions)
    assert result["panels_requested"] == 10
    assert result["panels_completed"] == 9
    assert result["typed_answers"] == 108
