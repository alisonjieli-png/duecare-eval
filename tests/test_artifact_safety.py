import json

from duecare_eval import artifact_safety as A


def test_operational_exploitation_content_is_restricted():
    r = A.classify_text(
        "Implementation: [method redacted] involving worker wages.",
        fictional=True,
    )
    assert r["classification"] == A.RESTRICTED_RED_TEAM
    assert r["public_export_allowed"] is False


def test_bounded_fictional_bad_advice_without_a_playbook_can_be_an_eval_fixture():
    r = A.classify_text(
        "This fictional benchmark answer wrongly says the employer may keep the passport.",
        fictional=True,
    )
    assert r["classification"] == A.PUBLIC_SYNTHETIC


def test_protective_avoidance_language_is_not_mistaken_for_evasion():
    r = A.classify_text(
        "To avoid confrontation, the worker should preserve the contract and seek advice.",
        fictional=True,
    )
    assert r["classification"] == A.PUBLIC_SYNTHETIC
    assert r["operational_harm_signal"] is False


def test_jsonl_audit_reports_lines_without_copying_harmful_text(tmp_path):
    path = tmp_path / "rows.jsonl"
    rows = [
        {"id": "safe", "response": "A fictional deficient answer."},
        {"id": "restricted", "response":
         "Implementation: [method redacted] involving worker fees."},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    audit = A.audit_jsonl(path, fictional=True)
    assert audit["flagged_rows"] == 1
    assert audit["flags"][0]["id"] == "restricted"
    assert "response" not in audit["flags"][0]
    assert audit["public_export_allowed"] is False
