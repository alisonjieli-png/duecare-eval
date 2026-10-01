"""Offline matched full-context bridge, preserving strict and extracted layers."""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean

from .contracts import canonical, loads_strict, sha

VERSION = "duecare-matched-context-analysis/1.0.0"
FENCE_METHOD = "duecare-whole-response-fence-extraction/1.0.0"
FIELDS = {"target_id", "model_requested", "model_reported", "context_id", "case_id", "arm",
          "prompt_sha256", "semantic_payload_sha256", "strict_status", "analysis_status",
          "selection_method", "selected_attempt", "answers", "invalid_answers", "attempts",
          "reused_archived_jev", "legacy_tie_resolution_differences"}
ATTEMPT_FIELDS = {"attempt", "status", "transport_status", "recorded_at", "receipt_sha256",
                  "response_sha256", "request_sha256"}
STATUSES = {"completed", "invalid_response", "malformed_json", "truncated", "incomplete_response",
            "provider_error", "provider_rejected", "identity_mismatch", "allocation_violation",
            "quota", "empty", "unattempted"}


def probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_raw(answers, questions, native=False):
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("question_id_population_mismatch")
    valid, invalid = {}, {}
    for key, question in questions.items():
        value = answers[key]
        try:
            if not isinstance(value, dict) or value.get("type") != question["type"]:
                raise ValueError("answer_type_mismatch")
            if question["type"] == "noul":
                if set(value) != {"type", "noul"} or not probability(value["noul"]):
                    raise ValueError("invalid_binary_probability")
                valid[key] = {"probability": value["noul"]}
            elif question["type"] == "choice":
                required = {"type", "choice", "probabilities"}
                if not required <= set(value) <= required | ({"confidence"} if native else set()):
                    raise ValueError("invalid_choice_fields")
                probs = value["probabilities"]
                if not isinstance(probs, dict) or set(probs) != set(question["criteria"]) or not all(probability(p) for p in probs.values()):
                    raise ValueError("invalid_choice_distribution")
                if abs(sum(probs.values()) - 1) > 1e-4:
                    raise ValueError("choice_probability_mass")
                if "confidence" in value and not probability(value["confidence"]):
                    raise ValueError("invalid_confidence")
                maxima = sorted(k for k, p in probs.items() if p == max(probs.values()))
                if value["choice"] not in maxima:
                    raise ValueError("selected_choice_not_maximum")
                valid[key] = {"probabilities": probs, "selected": value["choice"], "maxima": maxima}
            else:
                raise ValueError("unsupported_question_type")
        except ValueError as error:
            invalid[key] = str(error)
    return valid, invalid


def parse_object(text, questions):
    body = loads_strict(text)
    if not isinstance(body, dict) or set(body) != {"answers"}:
        raise ValueError("answer_envelope_fields")
    return validate_raw(body["answers"], questions)


def whole_fence(text):
    if not isinstance(text, str):
        raise ValueError("no_whole_response_fence")
    text = text.strip()
    for prefix in ("```json\n", "```\n"):
        if text.startswith(prefix) and text.endswith("\n```"):
            return text[len(prefix):-4]
    raise ValueError("no_whole_response_fence")


def select_attempt(attempts, questions):
    """Deterministic formatting extraction with all original attempts retained."""
    ordered = sorted(attempts, key=lambda r: r["attempt"])
    if len({r["attempt"] for r in ordered}) != len(ordered):
        raise ValueError("duplicate_attempt")
    strict = [r for r in ordered if r["status"] == "completed"]
    if strict:
        selected = strict[-1]
        valid, invalid = parse_object(selected["response"], questions)
        if invalid:
            raise ValueError("strict_completion_values_mismatch")
        return selected, "strict_plain_json", valid, invalid
    for candidate in ordered:
        if candidate.get("transport_status") != "completed" or candidate["status"] != "malformed_json":
            continue
        try:
            valid, invalid = parse_object(whole_fence(candidate.get("response")), questions)
        except (ValueError, TypeError):
            continue
        if not invalid:
            return candidate, FENCE_METHOD, valid, invalid
    if ordered:
        selected = ordered[-1]
        if selected["status"] == "invalid_response":
            valid, invalid = parse_object(selected["response"], questions)
            return selected, "strict_fieldwise", valid, invalid
        return selected, "unavailable", {}, {}
    return None, "unattempted", {}, {}


def context(case, arm, questions, evidence):
    state = {"original_source_prompt": case["prompt"], "source_type": case["provenance"]["source_type"],
             "assessment_scope": "Original research prompt; claims are supplied case assertions whose scope and support require assessment."}
    if arm == "grounded":
        state.update(dated_evidence=evidence["sources"], evaluation_rules=evidence["evaluation_rules"])
    elif arm != "bare":
        raise ValueError("unknown_arm")
    return {"state": state, "questions": questions}


def validate(records, manifest, cases, questions, evidence, *, expected_targets=12, require_jev=True, extra_methods=()):
    by_case = {c["case_id"]: c for c in cases if c["stratum"] == "original_advice"}
    targets = manifest["targets"]
    expected = {(target, case, arm) for target in targets for case in by_case for arm in ("bare", "grounded")}
    if len(records) != len(expected) or len(by_case) != 4 or len(targets) != expected_targets or require_jev and "jev" not in targets:
        raise ValueError("requested_population_mismatch")
    seen = set()
    for row in records:
        if set(row) != FIELDS:
            raise ValueError("observation_field_allowlist")
        key = (row["target_id"], row["case_id"], row["arm"])
        if key in seen or key not in expected:
            raise ValueError("unknown_or_duplicate_observation")
        seen.add(key)
        case = by_case[key[1]]
        semantic = context(case, key[2], questions, evidence)
        if (sha256(case["prompt"].encode()).hexdigest() != case["prompt_sha256"]
                or row["prompt_sha256"] != case["prompt_sha256"]
                or row["semantic_payload_sha256"] != sha(semantic)
                or row["context_id"] != "MFC-" + sha(semantic)[:26]
                or row["model_requested"] != targets[key[0]]["model"]):
            raise ValueError("shared_context_or_model_identity_mismatch")
        if row["strict_status"] not in STATUSES or row["analysis_status"] not in {"completed", "partial", "unavailable"}:
            raise ValueError("unknown_status")
        if type(row["reused_archived_jev"]) is not bool or row["reused_archived_jev"] != (key[0] == "jev"):
            raise ValueError("archive_identity_mismatch")
        if row["answers"] and row["model_reported"] != row["model_requested"]:
            raise ValueError("returned_model_identity_mismatch")
        if (not isinstance(row["answers"], dict) or not set(row["answers"]) <= set(questions)
                or not isinstance(row["invalid_answers"], dict) or not set(row["invalid_answers"]) <= set(questions)
                or set(row["answers"]) & set(row["invalid_answers"])):
            raise ValueError("unknown_answer_ids")
        for name, value in row["answers"].items():
            question = questions[name]
            if question["type"] == "noul":
                if set(value) != {"probability"} or not probability(value["probability"]):
                    raise ValueError("invalid_exported_probability")
            else:
                if set(value) != {"probabilities", "selected", "maxima"}:
                    raise ValueError("invalid_exported_choice")
                probs = value["probabilities"]
                if not isinstance(probs, dict) or set(probs) != set(question["criteria"]) or not all(probability(p) for p in probs.values()) or abs(sum(probs.values()) - 1) > 1e-4:
                    raise ValueError("invalid_exported_distribution")
                maxima = sorted(k for k, p in probs.items() if p == max(probs.values()))
                if value["maxima"] != maxima or value["selected"] not in maxima:
                    raise ValueError("invalid_exported_maximum")
        complete = len(row["answers"]) == len(questions)
        wanted = "completed" if complete else "partial" if row["answers"] else "unavailable"
        if row["analysis_status"] != wanted:
            raise ValueError("availability_mismatch")
        method = row["selection_method"]
        allowed_methods = {"strict_plain_json", FENCE_METHOD, "strict_fieldwise", "unavailable", "unattempted", "archived_native_actual_choice/1.0.0"}
        allowed_methods.update(extra_methods)
        if method not in allowed_methods or method == FENCE_METHOD and (not complete or row["strict_status"] == "completed"):
            raise ValueError("selection_method_mismatch")
        if row["strict_status"] == "completed" and (not complete or method not in {"strict_plain_json", "archived_native_actual_choice/1.0.0"}):
            raise ValueError("strict_completion_selection_mismatch")
        if (method == "archived_native_actual_choice/1.0.0") != row["reused_archived_jev"]:
            raise ValueError("native_selection_identity_mismatch")
        if any(v not in {"answer_type_mismatch", "invalid_binary_probability", "invalid_choice_fields",
                         "invalid_choice_distribution", "choice_probability_mass", "invalid_confidence",
                         "selected_choice_not_maximum", "unsupported_question_type"} for v in row["invalid_answers"].values()):
            raise ValueError("unknown_validation_code")
        ties = row["legacy_tie_resolution_differences"]
        if not isinstance(ties, dict) or not set(ties) <= set(questions) or ties and not row["reused_archived_jev"]:
            raise ValueError("invalid_legacy_tie_metadata")
        for key, tie in ties.items():
            answer = row["answers"].get(key, {})
            if (set(tie) != {"legacy_first_maximum", "actual_returned_choice"}
                    or tie["actual_returned_choice"] != answer.get("selected")
                    or tie["legacy_first_maximum"] not in answer.get("maxima", [])
                    or len(answer.get("maxima", [])) < 2):
                raise ValueError("invalid_legacy_tie_values")
        attempts = row["attempts"]
        if not isinstance(attempts, list) or len({a["attempt"] for a in attempts}) != len(attempts):
            raise ValueError("duplicate_attempt")
        for attempt in attempts:
            if (set(attempt) != ATTEMPT_FIELDS or type(attempt["attempt"]) is not int or attempt["attempt"] not in (1, 2)
                    or attempt["status"] not in STATUSES or not digest(attempt["receipt_sha256"])
                    or not digest(attempt["request_sha256"])
                    or attempt["response_sha256"] is not None and not digest(attempt["response_sha256"])):
                raise ValueError("invalid_attempt_provenance")
        if (attempts and row["selected_attempt"] not in {a["attempt"] for a in attempts}) or (not attempts and (row["selected_attempt"] != 0 or row["strict_status"] != "unattempted" or row["answers"])):
            raise ValueError("selected_attempt_mismatch")
        if attempts:
            latest = max(attempts, key=lambda a: a["attempt"])
            selected = next(a for a in attempts if a["attempt"] == row["selected_attempt"])
            if latest["status"] != row["strict_status"]:
                raise ValueError("strict_latest_outcome_mismatch")
            if method == FENCE_METHOD and (selected["status"] != "malformed_json" or selected["transport_status"] != "completed"):
                raise ValueError("fence_transport_mismatch")
    return by_case


def summarize(records, manifest, cases, questions, evidence):
    by_case = validate(records, manifest, cases, questions, evidence)
    models = {}
    binary = [k for k, q in questions.items() if q["type"] == "noul"]
    index = {(r["target_id"], r["case_id"], r["arm"]): r for r in records}
    for target in manifest["targets"]:
        selected = [r for r in records if r["target_id"] == target]
        probes = {}
        for arm in ("bare", "grounded"):
            probes[arm] = {}
            for name in questions:
                values = {case: index[target, case, arm]["answers"][name] for case in sorted(by_case) if name in index[target, case, arm]["answers"]}
                probes[arm][name] = {"requested_cases": 4, "available_cases": len(values), "values": values}
        models[target] = {"requested_panels": 8, "strict_complete_panels": sum(r["strict_status"] == "completed" for r in selected),
                          "analysis_complete_panels": sum(r["analysis_status"] == "completed" for r in selected),
                          "fence_extracted_panels": sum(r["selection_method"] == FENCE_METHOD for r in selected),
                          "recorded_panels": sum(bool(r["attempts"]) for r in selected),
                          "typed_fields_requested": 96, "typed_fields_available": sum(len(r["answers"]) for r in selected),
                          "strict_outcomes": dict(sorted(Counter(r["strict_status"] for r in selected).items())), "probes": probes}
    shared = {}
    for arm in ("bare", "grounded"):
        shared[arm] = {"requested_cases": 4,
                      "complete_panel_case_ids": sorted(c for c in by_case if all(index[t, c, arm]["analysis_status"] == "completed" for t in manifest["targets"])),
                      "by_question": {q: sorted(c for c in by_case if all(q in index[t, c, arm]["answers"] for t in manifest["targets"])) for q in questions}}
    paired = {}
    for target in manifest["targets"]:
        if target == "jev":
            continue
        matched = [(case, arm, q) for case in sorted(by_case) for arm in ("bare", "grounded") for q in binary
                   if q in index[target, case, arm]["answers"] and q in index["jev", case, arm]["answers"]]
        paired[target] = {"matched_binary_fields": len(matched), "requested_binary_fields": 80,
                          "matched_field_ids": [list(x) for x in matched],
                          "mean_absolute_probability_difference_from_jev": mean(abs(index[target, c, a]["answers"][q]["probability"] - index["jev", c, a]["answers"][q]["probability"]) for c, a, q in matched) if matched else None}
    return {"schema": VERSION, "snapshot_at": manifest["snapshot_at"], "requested_panels": len(records),
            "new_panels_requested": 88, "archived_jev_panels": 8, "new_physical_calls": manifest["new_physical_calls"],
            "models": models, "all_model_intersection": shared, "paired_jev_probability_differences": paired,
            "interpretation": {
                "scope": "The same four full published source cases, two evidence arms and twelve exact elicited questions. Text adapters and native Jev use distinct transport/formatting interfaces.",
                "quantity": "Raw model probabilities and actual selected options, with every maximum retained for tied distributions. These describe propositions and choices, with independent calibration and reference validation open.",
                "coverage": "All twelve targets retain eight requested panels each. Strict formatting, whole-response fence extraction, whole-panel and individual-field availability are separate counts.",
                "comparisons": "Display individual case/arm/probe values. Pairwise differences use only listed matching fields; their denominators differ. They measure agreement with Jev, not correctness or an overall model ranking.",
                "strata": "Four exact published advice cases form this bridge. The analytical notebook variant remains in the separate prose study.",
                "selection": "Strict completion first; otherwise earliest whole-response fenced JSON passing the same numeric/ID checks; otherwise latest original outcome with its available strict fields. Missing syntax and numeric values remain missing.",
            }}


def reproduce(root):
    root = Path(root)
    prefix = root / "results/matched_context_2026-09-30"
    manifest = json.loads(prefix.with_suffix(".manifest.json").read_text())
    for path, expected in manifest["files"].items():
        if sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError("matched_context_file_hash_mismatch")
    records = [loads_strict(line) for line in prefix.with_suffix(".jsonl").read_text().splitlines() if line.strip()]
    def read(name):
        return json.loads((root / "results" / name).read_text())
    return summarize(records, manifest, read("longform_cases_2026-09-30.json"),
                     read("longform_jev_questions_2026-09-30.json"), read("longform_primary_sources_2026-09-30.json"))
