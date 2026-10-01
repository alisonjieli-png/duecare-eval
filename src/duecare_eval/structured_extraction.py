"""Versioned extraction of complete returned objects and valid numeric fields.

The anchored decoder reads the existing inner answers object. It inserts no
characters, and the original whole-envelope status remains a separate field.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from .contracts import loads_strict
from . import matched_context as M

VERSION = "duecare-structured-field-extraction/1.2.0"
INNER = "duecare-anchored-answers-object/1.0.0"
KINDS = ("plain_json", "whole_fence", "anchored_object")
KNOWN = "duecare-question-schema-field-extraction/1.0.0"
PARTIAL = {kind: VERSION + ":" + kind for kind in KINDS + tuple("question_schema/" + k for k in KINDS)}
EXTRA = {"cohort", "source_span", "missing_type_tags"}
POLICY = {
    "complete_order": ["original strict completion", "earliest complete whole-response fenced JSON", "earliest complete anchored inner answers object", "earliest complete object under exact known question schemas with missing redundant type tags recorded"],
    "partial_order": "When no complete candidate is available, select the earliest transport-completed, exact-ID object with at least one individually valid field. Use known question schemas for eligible missing type tags; conflicting types and extra fields remain invalid. If none has a valid field, retain the earliest exact-ID object and its validation errors. Format priority within an attempt is plain JSON, whole-response fence, anchored inner object.",
    "anchoring": "The response begins with an object and the exact first key answers. Decode the already complete inner object; the remaining text must be empty or one outer closing brace. No character is added or removed inside the decoded object.",
    "numeric_contract": "Preserve raw values. Enforce exact question IDs, type tags, finite probabilities, option membership and selected maxima. Choice mass tolerance0.0001; no normalization. Retain every maximum at ties.",
    "missing_type_tags": "A separate known-question-schema method reads unchanged values when type is absent and the fields are exactly noul for a binary question, or choice plus probabilities for a choice question. The declared question supplies its schema. Wrong type tags and extra keys remain invalid; missing_type_tags is explicit metadata.",
    "binary_half": "An exact positive probability0.5 is an uncertainty/tie, displayed as0.5 rather than credited as clear recognition.",
    "original_layers": "The September30 baseline and October1 adapter snapshots retain their original statuses, counts and selected observations. This is an additional named interpretation layer.",
}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite_json_value")


def anchored_object(text):
    if not isinstance(text, str):
        raise ValueError("missing_response_text")
    match = re.match(r'^\s*\{\s*"answers"\s*:\s*', text)
    if not match:
        raise ValueError("answers_anchor_required")
    decoder = json.JSONDecoder(object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    value, end = decoder.raw_decode(text, match.end())
    if not isinstance(value, dict) or text[end:].strip() not in ("", "}"):
        raise ValueError("complete_single_answers_object_required")
    return value, [match.end(), end]


def known_schema_values(obj, questions):
    if not isinstance(obj, dict) or set(obj) != set(questions):
        raise ValueError("question_id_population_mismatch")
    adapted, missing = {}, []
    for key, value in obj.items():
        question = questions[key]
        expected = {"noul"} if question["type"] == "noul" else {"choice", "probabilities"}
        if isinstance(value, dict) and "type" not in value and set(value) == expected:
            adapted[key] = {"type": question["type"], **value}
            missing.append(key)
        else:
            adapted[key] = value
    valid, invalid = M.validate_raw(adapted, questions)
    return valid, invalid, sorted(missing)


def candidates(row, questions):
    if row.get("transport_status") != "completed":
        return []
    text = row.get("response")
    result = []
    for kind in KINDS:
        try:
            span = None
            if kind == "anchored_object":
                obj, span = anchored_object(text)
            else:
                body = loads_strict(text if kind == "plain_json" else M.whole_fence(text))
                if not isinstance(body, dict) or set(body) != {"answers"}:
                    raise ValueError("answer_envelope_fields")
                obj = body["answers"]
            valid, invalid = M.validate_raw(obj, questions)
            result.append({"kind": kind, "valid": valid, "invalid": invalid, "span": span, "missing_type_tags": []})
            known_valid, known_invalid, missing = known_schema_values(obj, questions)
            if missing:
                result.append({"kind": "question_schema/" + kind, "valid": known_valid, "invalid": known_invalid,
                               "span": span, "missing_type_tags": missing})
        except (ValueError, TypeError):
            pass
    return result


def select_attempt(attempts, questions):
    ordered = sorted(attempts, key=lambda r: r["attempt"])
    if len({r["attempt"] for r in ordered}) != len(ordered):
        raise ValueError("duplicate_attempt")
    strict = [r for r in ordered if r["status"] == "completed"]
    if strict:
        selected = strict[-1]
        valid, invalid = M.parse_object(selected["response"], questions)
        if invalid:
            raise ValueError("strict_completion_values_mismatch")
        return selected, "strict_plain_json", valid, invalid
    decoded = [(row, option) for row in ordered for option in candidates(row, questions)]
    for kind, method in (("whole_fence", M.FENCE_METHOD), ("anchored_object", INNER)):
        for row, option in decoded:
            if option["kind"] == kind and not option["invalid"]:
                return row, method, option["valid"], option["invalid"]
    for row, option in decoded:
        if option["kind"].startswith("question_schema/") and not option["invalid"]:
            return row, KNOWN + ":" + option["kind"].split("/", 1)[1], option["valid"], option["invalid"]
    # Each actual object has one partial view: the known-schema view when
    # redundant tags are missing, otherwise its original strict field view.
    partial_options = []
    for row in ordered:
        options = candidates(row, questions)
        for kind in KINDS:
            option = next((o for o in options if o["kind"] == "question_schema/" + kind), None)
            option = option or next((o for o in options if o["kind"] == kind), None)
            if option is not None:
                partial_options.append((row, option))
    partial = next(((row, option) for row, option in partial_options if option["valid"]), partial_options[0] if partial_options else None)
    if partial:
        row, option = partial
        return row, PARTIAL[option["kind"]], option["valid"], option["invalid"]
    return (ordered[-1], "unavailable", {}, {}) if ordered else (None, "unattempted", {}, {})


def summarize(records, manifest, source_records, cases, questions, evidence):
    if any(set(row) != M.FIELDS | EXTRA for row in records) or set(manifest["cohorts"]) != {"baseline", "adapter_v1_1"}:
        raise ValueError("extended_projection_allowlist")
    grouped = {cohort: [r for r in records if r["cohort"] == cohort] for cohort in manifest["cohorts"]}
    if sum(map(len, grouped.values())) != len(records):
        raise ValueError("unknown_cohort")
    source = {(cohort, r["target_id"], r["case_id"], r["arm"]): r for cohort, values in source_records.items() for r in values}
    known_methods = {KNOWN + ":" + kind for kind in KINDS}
    methods = {INNER, *PARTIAL.values(), *known_methods}
    for cohort, rows in grouped.items():
        M.validate([{k: v for k, v in r.items() if k not in EXTRA} for r in rows], manifest["cohorts"][cohort],
                   cases, questions, evidence, expected_targets=12 if cohort == "baseline" else 3,
                   require_jev=cohort == "baseline", extra_methods=methods)
        for row in rows:
            original = source[cohort, row["target_id"], row["case_id"], row["arm"]]
            for name in ("model_requested", "context_id", "prompt_sha256", "semantic_payload_sha256", "strict_status", "attempts", "reused_archived_jev"):
                if row[name] != original[name]:
                    raise ValueError("original_observation_provenance_changed")
            if row["selection_method"] in methods:
                selected = next(a for a in row["attempts"] if a["attempt"] == row["selected_attempt"])
                if selected["transport_status"] != "completed":
                    raise ValueError("extraction_requires_complete_transport")
                if row["selection_method"] in {INNER, *known_methods} and row["analysis_status"] != "completed":
                    raise ValueError("complete_object_method_requires_all_fields")
            span = row["source_span"]
            anchored = row["selection_method"] == INNER or row["selection_method"].endswith(":anchored_object") or row["selection_method"].endswith("/anchored_object")
            if anchored != (span is not None) or span is not None and (not isinstance(span, list) or len(span) != 2 or any(type(x) is not int for x in span) or not 0 <= span[0] < span[1]):
                raise ValueError("invalid_returned_object_span")
            missing = row["missing_type_tags"]
            if (not isinstance(missing, list) or missing != sorted(set(missing)) or not set(missing) <= set(questions)
                    or bool(missing) != (row["selection_method"] in known_methods or "question_schema/" in row["selection_method"])):
                raise ValueError("missing_type_metadata_mismatch")
    def coverage(rows):
        return {"requested_panels": len(rows), "strict_complete": sum(r["strict_status"] == "completed" for r in rows),
                "complete_panels": sum(r["analysis_status"] == "completed" for r in rows),
                "partial_panels": sum(r["analysis_status"] == "partial" for r in rows),
                "typed_fields_requested": len(rows) * len(questions), "typed_fields_available": sum(len(r["answers"]) for r in rows),
                "methods": dict(sorted(Counter(r["selection_method"] for r in rows).items()))}
    cohorts = {cohort: {"totals": coverage(rows), "models": {target: coverage([r for r in rows if r["target_id"] == target])
               for target in manifest["cohorts"][cohort]["targets"]}} for cohort, rows in grouped.items()}
    working = {}
    for target in manifest["cohorts"]["baseline"]["targets"]:
        cohort = "adapter_v1_1" if target in {"glm-5-3", "glm-5-3-flash"} else "baseline"
        selected = [r for r in grouped[cohort] if r["target_id"] == target]
        working[target] = {"source_cohort": cohort,
            "native_condition": "think=low;4096output cap" if cohort == "adapter_v1_1" else "original recorded binding",
            "selection_reason": "Supported thinking control from provider metadata" if cohort == "adapter_v1_1" else "Original benchmark condition retained",
            **coverage(selected),
            "binary_exact_half": sum(v.get("probability") == .5 for r in selected for v in r["answers"].values()),
            "panels": [{k: r[k] for k in ("case_id", "arm", "strict_status", "analysis_status", "selection_method", "answers", "invalid_answers")} for r in selected]}
    index = {(t, r["case_id"], r["arm"]): r for t, x in working.items() for r in x["panels"]}
    case_ids = sorted(c["case_id"] for c in cases if c["stratum"] == "original_advice")
    intersection = {arm: {"complete_case_ids": [c for c in case_ids if all(index[t, c, arm]["analysis_status"] == "completed" for t in working)],
                         "by_question": {q: [c for c in case_ids if all(q in index[t, c, arm]["answers"] for t in working)] for q in questions}}
                    for arm in ("bare", "grounded")}
    return {"schema": VERSION, "snapshot_at": manifest["snapshot_at"], "policy": POLICY,
            "cohorts": cohorts, "working_configurations": working, "working_config_intersection": intersection,
            "interpretation": "Working configurations explicitly select supported GLM thinking controls and retain original conditions for other targets. Charts display raw case/arm/probe values, all tied maxima and missing values. These are elicited judgments with distinct adapter/interpretation conditions; no overall accuracy or model-quality ranking is inferred."}


def reproduce(root):
    root = Path(root)
    prefix = root / "results/structured_extraction_2026-10-01"
    manifest = json.loads(prefix.with_suffix(".manifest.json").read_text())
    for path, expected in manifest["files"].items():
        if sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError("structured_projection_hash_mismatch")
    def rows(name):
        return [json.loads(line) for line in (root / "results" / name).read_text().splitlines() if line.strip()]
    def read(name):
        return json.loads((root / "results" / name).read_text())
    return summarize(rows("structured_extraction_2026-10-01.jsonl"), manifest,
        {"baseline": rows("matched_context_2026-09-30.jsonl"), "adapter_v1_1": rows("matched_context_adapter_2026-10-01.jsonl")},
        read("longform_cases_2026-09-30.json"), read("longform_jev_questions_2026-09-30.json"), read("longform_primary_sources_2026-09-30.json"))
