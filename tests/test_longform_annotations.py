from copy import deepcopy
import json
from pathlib import Path
import pytest

from duecare_eval.longform_annotations import reproduce, validate

ROOT = Path(__file__).resolve().parents[1]


def data():
    manifest = json.loads((ROOT / "results/longform_annotations_2026-09-30.manifest.json").read_text())
    records = [json.loads(line) for line in (ROOT / "results/longform_annotations_2026-09-30.jsonl").read_text().splitlines()]
    return records, manifest


def test_release_reproduces_fieldwise_denominators_exactly():
    result = reproduce(ROOT)
    expected = json.loads((ROOT / "results/longform_annotations_2026-09-30.findings.json").read_text())
    assert result == expected
    assert result["totals"]["requested"] == result["totals"]["generated"] == 50
    assert result["totals"]["criteria"]["factual_legal_calibration"]["unavailable"] == 2
    assert result["totals"]["strict_grade_packets_completed"] == 3
    assert result["totals"]["citation_values_complete"] == 50


def test_raw_text_and_duplicate_units_are_rejected():
    records, manifest = data()
    bad = deepcopy(records); bad[0]["response"] = "private text"
    with pytest.raises(ValueError):
        validate(bad, manifest)
    with pytest.raises(ValueError):
        validate(records + [records[0]], manifest)


@pytest.mark.parametrize("value", [True, float("nan"), 1.1])
def test_invalid_behavior_probabilities_fail(value):
    records, manifest = data()
    records[0]["behavior_probabilities"]["operational_facilitation"] = value
    with pytest.raises(ValueError):
        validate(records, manifest)


def test_strict_probability_mass_remains_strict():
    records, manifest = data()
    record = next(r for r in records if r["score_distributions"]["overall_quality"]["strict_valid"])
    record["score_distributions"]["overall_quality"]["probabilities"] = {str(i): .19 for i in range(5)}
    with pytest.raises(ValueError, match="strict_distribution"):
        validate(records, manifest)


def test_critical_caps_cannot_be_overwritten_by_an_index():
    records, manifest = data()
    record = next(r for r in records if r["critical_cap_reasons"] and r["raw_overall_grade"] and r["raw_overall_grade"] > 2)
    record["proposed_overall_grade"] = 5
    with pytest.raises(ValueError, match="cap_grade"):
        validate(records, manifest)
