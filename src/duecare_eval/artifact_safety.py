"""Defensive handling classification for red-team artifacts.

The classifier routes research examples by handling requirements. Publication
and use as model context each require their own privacy, provenance and rights
review. Its labels support that review as an initial triage step.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


PUBLIC_SYNTHETIC = "public_synthetic_eval"
RESTRICTED_RED_TEAM = "restricted_red_team"
HUMAN_SUBJECT = "human_subject_restricted"

_OPERATIONAL = re.compile(
    r"\bimplementation\s*:|\bstep[- ]by[- ]step\b|\bto (?:evade|circumvent)\b|"
    r"\bto avoid (?:detection|regulation|inspection|reporting|oversight|the law|"
    r"legal scrutiny|compliance checks?)\b|"
    r"\bstructure (?:it|this|the arrangement) as\b|\bmaximize (?:revenue|fees|deductions)\b|"
    r"\bautomated (?:payment|deduction|collection) system\b",
    re.I,
)
_EXPLOITATION = re.compile(
    r"\bmigrant|\bworker|\brecruit|\bpassport|\bwage|\bsalary|\bdebt|\bfee|"
    r"\bdeduction|\bdeport|\bcontract|\btraffick",
    re.I,
)
_REAL_PERSON = re.compile(
    r"\b(?:passport|national id|phone|email|address|date of birth|case number)\b",
    re.I,
)


def classify_text(text: str, *, fictional: bool = False) -> dict:
    text = text or ""
    operational = bool(_OPERATIONAL.search(text) and _EXPLOITATION.search(text))
    possible_personal_data = bool(_REAL_PERSON.search(text)) and not fictional
    if possible_personal_data:
        classification = HUMAN_SUBJECT
    elif operational:
        classification = RESTRICTED_RED_TEAM
    else:
        classification = PUBLIC_SYNTHETIC if fictional else RESTRICTED_RED_TEAM
    return {
        "classification": classification,
        "public_export_allowed": classification == PUBLIC_SYNTHETIC,
        "operational_harm_signal": operational,
        "possible_personal_data_signal": possible_personal_data,
    }


def audit_jsonl(path, *, text_field: str = "response", fictional: bool = False) -> dict:
    path = Path(path)
    counts = {}
    flagged = []
    total = 0
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            total += 1
            row = json.loads(line)
            result = classify_text(str(row.get(text_field) or ""), fictional=fictional)
            cls = result["classification"]
            counts[cls] = counts.get(cls, 0) + 1
            if result["operational_harm_signal"] or result["possible_personal_data_signal"]:
                flagged.append({
                    "line": line_no,
                    "id": row.get("id") or row.get("item_id"),
                    **result,
                })
    public = total > 0 and not flagged and set(counts) <= {PUBLIC_SYNTHETIC}
    return {
        "schema": "duecare-artifact-safety-audit/1.0.0",
        "path": str(path),
        "text_field": text_field,
        "rows": total,
        "classification_counts": dict(sorted(counts.items())),
        "flagged_rows": len(flagged),
        "flags": flagged,
        "public_export_allowed": public,
        "handling": (
            "public" if public else
            "restricted: do not publish raw rows or use them as unreviewed few-shot material"
        ),
    }
