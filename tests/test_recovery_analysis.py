import copy
from functools import lru_cache
import json
from pathlib import Path

import pytest

from duecare_eval import recovery_analysis as R


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def released():
    return json.loads((ROOT / "results/jev_recovery_2026-09-30.json").read_text())


def test_recovery_overlay_reproduces_and_preserves_original_errors():
    findings = R.reproduce(ROOT)
    assert findings == released()["findings"]
    expected = {"core": (11999, 12000, 1), "attacks": (7199, 7200, 1),
                "judge": (2785, 2788, 5), "referral": (16790, 16798, 10)}
    for lane, (original, overlay, failures) in expected.items():
        value = findings["coverage"][lane]
        assert value["original_completed"] == original
        assert value["overlay_completed"] == overlay
        assert value["original_unsuccessful"] == failures
    assert findings["supplement"]["statuses"] == {"completed": 13, "provider_error": 4}


def test_duplicate_supplement_cannot_increase_coverage():
    data = copy.deepcopy(released())
    data["observations"].append(data["observations"][0])
    with pytest.raises(ValueError, match="distinct"):
        R.validate(data)


def test_completed_original_case_cannot_be_replaced():
    data = copy.deepcopy(released())
    data["observations"][0]["task_id"] = data["original"]["core"]["ids_by_status"]["completed"][0]
    with pytest.raises(ValueError, match="originally unsuccessful"):
        R.validate(data)


def test_raw_text_is_outside_observation_allowlist():
    data = copy.deepcopy(released())
    data["observations"][0]["reason"] = "unreviewed response text"
    with pytest.raises(ValueError, match="allowlist"):
        R.validate(data)


def test_original_denominator_is_fixed():
    data = copy.deepcopy(released())
    data["original"]["core"]["requested"] -= 1
    with pytest.raises(ValueError, match="denominator"):
        R.validate(data)


def test_nonfinite_decision_is_rejected():
    data = copy.deepcopy(released())
    data["observations"][0]["decision"]["probabilities"]["1"] = float("nan")
    with pytest.raises(ValueError, match="numeric allowlist"):
        R.validate(data)


def test_source_provenance_accepts_digests_only():
    data = copy.deepcopy(released())
    data["provenance"]["supplement_manifest_sha256"] = "/private/path"
    with pytest.raises(ValueError, match="SHA-256"):
        R.validate(data)
