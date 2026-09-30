from copy import deepcopy
from pathlib import Path
import pytest

from duecare_eval.source_completion import assess, reproduce


def fixture():
    row = {"request_id": "SRCQ-" + "1" * 26, "case_id": "a" * 64, "probe_id": "p", "view_id": "original_full", "repeat": 0,
        "track": "source_context", "model": "jev-1.13.0", "original_status": "provider_error", "status": "completed",
        "observation_source": "terminal_supplement", "decision": {"probability": .4}, "request_sha256": "b" * 64,
        "selected_receipt_sha256": "c" * 64, "original_receipt_sha256": "d" * 64}
    return row, [{"probe_id": "p", "decision_type": "binary_probability"}]


def test_original_failure_and_supplement_are_separate():
    row, catalog = fixture()
    result = assess([row], catalog)
    assert result["primary_usable"] == 0 and result["combined_usable"] == 1
    assert result["primary_errors"] == {"provider_error": 1}
    assert result["supplemental_usable"] == 1


def test_duplicate_or_relabelled_primary_fails():
    row, catalog = fixture()
    with pytest.raises(ValueError):
        assess([row, row], catalog)
    changed = deepcopy(row); changed["observation_source"] = "primary"
    with pytest.raises(ValueError, match="relabelled"):
        assess([changed], catalog)


def test_final_completion_reproduces_all_denominators():
    result = reproduce(Path(__file__).resolve().parents[1])
    assert result["requested"] == 56358 and result["primary_usable"] == 56325
    assert result["combined_usable"] == 56348 and result["remaining_unusable"] == 10
    assert result["by_track"]["perspective_expansion"]["combined_usable"] == 3643
