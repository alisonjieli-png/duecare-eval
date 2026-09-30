from copy import deepcopy
import json
from pathlib import Path
import pytest

from duecare_eval.anchor_pilot import assess, reproduce

ROOT = Path(__file__).resolve().parents[1]


def packet():
    return json.loads((ROOT / "results/longform_anchor_pilot_2026-09-30.json").read_text())


def test_pilot_reproduces_requested_and_matched_order_counts():
    result = reproduce(ROOT)
    assert result == json.loads((ROOT / "results/longform_anchor_pilot_2026-09-30.findings.json").read_text())
    assert result["pointwise"]["requested"] == 125
    assert result["pointwise"]["assessed_overall_grade"] == 122
    assert result["pairwise"]["pilot_requested"] == 100
    assert result["pairwise"]["full_prepared_bank_requests"] == 500
    assert result["pairwise"]["stable_swaps"] == 39


def test_unknown_pair_and_duplicate_candidate_rejected():
    values = packet(); values["pairwise"][0]["candidate_a"] = "unknown"
    with pytest.raises(ValueError):
        assess(values)
    values = packet(); values["candidates"][1] = deepcopy(values["candidates"][0])
    with pytest.raises(ValueError):
        assess(values)


def test_boolean_is_not_an_ordinal_grade():
    values = packet(); values["candidates"][0]["assessed_grade"] = True
    with pytest.raises(ValueError):
        assess(values)
