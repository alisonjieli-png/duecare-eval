"""Reproduce Jev-inclusive chart data from frozen public observations, offline.

Shared-task agreement and elicited full-context probabilities have separate
denominators, input contracts and interpretations throughout this artifact.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from . import comparison_analysis as CA
from .decisioning import decision_input, validate_decision_tasks

SCHEMA = "duecare-jev-visuals/1.0.0"
MODELS = ("jev", "gpt-oss-20b", "deepseek-flash", "kimi-k3", "gemma4-31b", "gemma-abliterated")
FAMILY_LABELS = {
    "crossborder_screening": "Declared-policy screening route",
    "safe_action_boundary": "Authorization to share a redacted summary",
    "sequential_evidence_update": "Decision update after supplied evidence",
    "source_scope_entailment": "Scoped source entailment",
    "financial_arithmetic": "Financial arithmetic",
}
BINARY_LABELS = {
    "financial_pressure": "Financial burden concern",
    "deduction_control": "Control over wages concern",
    "exit_consequences": "Adverse exit consequences concern",
    "consent_sufficiency": "Freely revocable consent established",
    "crossborder_uncertainty": "Jurisdictional facts unresolved",
    "role_conflict": "Recruitment / lending role conflict",
    "worker_blame": "Worker-blame / repayment pressure",
    "licensing_sufficiency": "Licence claims establish compliance",
    "independent_support": "Independent support proportionate",
    "crime_conclusion": "Categorical criminal conclusion established",
}
CHOICES = {"priority_next_step", "evidence_position"}
PANEL_FIELDS = {"arm", "case_id", "model", "request_id", "request_sha256",
                "prompt_sha256", "recorded_at", "status", "validated_answers", "invalid_answers"}


def file_digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def value_digest(value):
    return sha256(CA.canonical(value).encode()).hexdigest()


def shared_tasks(tasks, observations, references, blind_inputs):
    """Join identical task IDs to full references and exact blind task contracts."""
    CA.validate(tasks, observations, MODELS)
    if any(t["suite"] != "crossborder" for t in tasks):
        raise ValueError("crossborder_suite_required")
    validate_decision_tasks(references)
    refs = {t["task_id"]: t for t in references}
    projected = {t["task_id"]: t for t in tasks}
    blind = {t["task_id"]: t for t in blind_inputs}
    if (set(refs) != set(projected) or set(blind) != set(refs)
            or len(blind) != len(blind_inputs)):
        raise ValueError("reference_blind_population_mismatch")
    for key, task in projected.items():
        reference = refs[key]
        for field in ("task_sha256", "decision_type", "expected", "family", "group_id", "split"):
            if task[field] != reference[field]:
                raise ValueError("projection_reference_mismatch:" + field)
        for field in ("choices", "labels"):
            if task[field] != reference.get(field, []):
                raise ValueError("projection_reference_mismatch:" + field)
        if blind[key] != decision_input(reference):
            raise ValueError("blind_input_contract_mismatch")
    if set(t["family"] for t in tasks) != set(FAMILY_LABELS):
        raise ValueError("unexpected_crossborder_family")
    scored, coverage = {}, {}
    for model in MODELS:
        receipts = [r for r in observations if r["model_id"] == model]
        scored[model] = {r["task_id"]: CA.score(projected[r["task_id"]], r["decision"])
                         for r in receipts if r["status"] == "completed"}
        coverage[model] = {
            "requested": len(tasks), "recorded": len(receipts), "usable": len(scored[model]),
            "recorded_unusable": len(receipts) - len(scored[model]),
            "missing": len(tasks) - len(receipts),
            "outcome_counts": dict(sorted(Counter(r["status"] for r in receipts).items())),
            "reported_model_ids": sorted({r["model_reported"] for r in receipts if r["model_reported"]}),
        }
    common = sorted(set.intersection(*(set(scored[m]) for m in MODELS)))
    families = {}
    for family, label in FAMILY_LABELS.items():
        population = [t for t in tasks if t["family"] == family]
        ids = [key for key in common if projected[key]["family"] == family]
        full = [refs[key] for key in ids]
        policies = sorted({r["state"][name] for r in full
                           for name in ("screening_policy", "action_policy") if name in r["state"]})
        families[family] = {
            "label": label, "requested_per_model": len(population), "matched_tasks": len(ids),
            "matched_scenario_groups": len({projected[k]["group_id"] for k in ids}),
            "shared_task_ids": ids,
            "shared_input_contracts_sha256": value_digest([[key, blind[key]["input_sha256"]] for key in ids]),
            "questions": sorted({r["question"] for r in full}), "supplied_policies": policies,
            "reference_basis": sorted({r["label_basis"] for r in full}),
            "review_status": sorted({r["review_status"] for r in full}),
            "models": {m: CA.metrics([scored[m][key] for key in ids]) for m in MODELS},
        }
    return {
        "requested_per_model": len(tasks), "matched_tasks": len(common),
        "requested_outside_shared_intersection": len(tasks) - len(common),
        "shared_task_ids_sha256": value_digest(common), "coverage": coverage, "families": families,
        "interpretation": {
            "common_contract": "Identical blind task state, evidence, question and declared answer space for each shared task ID; provider-specific transport and response adapters.",
            "screening": "Directly elicited agreement with the supplied screening policy. References are declared research assumptions with independent domain/legal review pending.",
            "action": "Decision authorization for sharing a redacted summary under worker-consent, verified-recipient and safe-channel requirements. No contact was executed.",
            "sampling": "All-six usable intersection of a dated campaign prefix. The full requested population remains the coverage denominator; matched tasks are a selected subset.",
            "unit": "Task counts with scenario-group counts shown; repeated task variants share contexts. Descriptive reference agreement is the plotted quantity.",
            "probabilities": "Existing typed scoring contract retains raw numeric components and normalizes positive categorical mass for scoring; normalization counts remain visible.",
        },
    }


def context_panels(cases, panels, questions):
    """Validate raw recorded Jev probabilities and retain original/variant strata."""
    if set(questions) != set(BINARY_LABELS) | CHOICES:
        raise ValueError("panel_question_population_mismatch")
    for key, question in questions.items():
        required = {"type", "instructions"} | ({"criteria"} if key in CHOICES else set())
        if set(question) != required or not isinstance(question["instructions"], str):
            raise ValueError("invalid_question_contract")
        if question["type"] != ("choice" if key in CHOICES else "noul"):
            raise ValueError("invalid_question_type")
        if key in CHOICES and (not isinstance(question["criteria"], dict) or len(question["criteria"]) < 2):
            raise ValueError("invalid_question_choices")
    case_lookup = {c["case_id"]: c for c in cases}
    if len(case_lookup) != len(cases):
        raise ValueError("duplicate_source_case")
    for case in cases:
        if (sha256(case["prompt"].encode()).hexdigest() != case["prompt_sha256"]
                or case["characters"] != len(case["prompt"])
                or case["stratum"] not in {"original_advice", "explicit_analysis_variant"}):
            raise ValueError("source_case_digest_or_stratum_mismatch")
    seen, request_ids, output = set(), set(), []
    for panel in panels:
        if set(panel) != PANEL_FIELDS:
            raise ValueError("invalid_panel_fields")
        key = (panel["case_id"], panel["arm"])
        if (key in seen or key[0] not in case_lookup or key[1] not in {"bare", "grounded"}
                or panel["request_id"] in request_ids):
            raise ValueError("unknown_or_duplicate_panel")
        case = case_lookup[key[0]]
        if (panel["prompt_sha256"] != case["prompt_sha256"]
                or not CA.digest(panel["request_sha256"]) or panel["model"] != "jev-1.13.0"
                or panel["status"] != "completed" or panel["invalid_answers"]):
            raise ValueError("invalid_panel_identity_or_status")
        answers = panel["validated_answers"]
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise ValueError("panel_answer_population_mismatch")
        binary, categorical = {}, {}
        for name, answer in answers.items():
            if name in BINARY_LABELS:
                if (not isinstance(answer, dict) or set(answer) != {"probability"}
                        or not CA.probability(answer["probability"])):
                    raise ValueError("invalid_panel_probability")
                binary[name] = answer["probability"]
            else:
                if not isinstance(answer, dict) or set(answer) != {"probabilities", "selected", "ambiguous_maximum"}:
                    raise ValueError("invalid_panel_choice")
                probs = answer["probabilities"]
                if (not isinstance(probs, dict) or set(probs) != set(questions[name]["criteria"])
                        or not all(CA.probability(p) for p in probs.values())
                        or abs(sum(probs.values()) - 1) > 1e-9):
                    raise ValueError("invalid_panel_choice_probabilities")
                maxima = {k for k, p in probs.items() if p == max(probs.values())}
                if (answer["selected"] not in maxima or type(answer["ambiguous_maximum"]) is not bool
                        or answer["ambiguous_maximum"] != (len(maxima) > 1)):
                    raise ValueError("invalid_panel_selected_value")
                categorical[name] = answer
        output.append({**{k: panel[k] for k in ("case_id", "arm", "model", "prompt_sha256", "request_id", "request_sha256", "recorded_at")},
                       "stratum": case["stratum"], "theme": case["theme"],
                       "binary_probabilities": binary, "categorical_answers": categorical})
        seen.add(key); request_ids.add(panel["request_id"])
    strata = {}
    for stratum in ("original_advice", "explicit_analysis_variant"):
        selected = [r for r in output if r["stratum"] == stratum]
        requested = sum(c["stratum"] == stratum for c in cases) * 2
        strata[stratum] = {"cases": requested // 2, "panels_requested": requested,
                           "panels_completed": len(selected), "typed_answers": len(selected) * len(questions),
                           "binary_answers": len(selected) * len(BINARY_LABELS),
                           "categorical_answers": len(selected) * len(CHOICES)}
    return {
        "model": "jev-1.13.0", "panels_requested": len(cases) * 2, "panels_completed": len(output),
        "typed_answers": len(output) * len(questions), "strata": strata,
        "binary_probe_order": list(BINARY_LABELS), "binary_probe_labels": BINARY_LABELS,
        "questions": questions, "panels": sorted(output, key=lambda r: (r["stratum"], r["case_id"], r["arm"])),
        "interpretation": {
            "quantity": "Raw model probabilities for the displayed propositions, elicited with twelve explicit questions on each complete source context.",
            "direction": "Each probability follows its exact question. High concern/support probabilities and low consent/licence/criminal-conclusion probabilities describe different propositions; retain row labels.",
            "validation": "Numeric/schema integrity and exact source-prompt hashes are verified offline. Real-world risk calibration and independent domain validation remain open.",
            "comparison": "These Jev target judgments use a typed prompted interface. The five prose targets answered the source advice requests; a matched twelve-question full-context arm for all six systems remains future work.",
            "roles": "Jev target panels, Jev proposed grades of other responses, and Jev reference-bank judging are separately measured roles.",
            "strata": "The four exact published advice prompts form the primary stratum. The documented full notebook attack variant explicitly requests analysis and has its own stratum.",
        },
    }


def reproduce(root):
    root = Path(root)
    paths = ["results/comparison_2026-09-30/snapshot.json", "results/comparison_2026-09-30/tasks.jsonl",
             "results/comparison_2026-09-30/observations.jsonl", "examples/crossborder_references.jsonl",
             "examples/crossborder_blind_inputs.jsonl", "results/longform_cases_2026-09-30.json",
             "results/longform_jev_panels_2026-09-30.json", "results/longform_jev_questions_2026-09-30.json",
             "results/longform_readable_manifest_2026-09-30.json"]
    def read(path):
        return json.loads((root / path).read_text())
    snapshot = read(paths[0])
    if set(snapshot["models"]) != set(MODELS):
        raise ValueError("snapshot_model_population_mismatch")
    for path in paths[1:3]:
        manifest = snapshot["files"][Path(path).name]
        if file_digest(root / path) != manifest["sha256"] or (root / path).stat().st_size != manifest["bytes"]:
            raise ValueError("snapshot_file_digest_mismatch")
    tasks = [r for r in CA.rows(root / paths[1]) if r["suite"] == "crossborder"]
    observations = [r for r in CA.rows(root / paths[2]) if r["suite"] == "crossborder"]
    shared = shared_tasks(tasks, observations, CA.rows(root / paths[3]), CA.rows(root / paths[4]))
    for model in MODELS:
        if snapshot["decision_sources"]["crossborder/" + model]["requested"] != len(tasks):
            raise ValueError("requested_population_mismatch")
    panel_result = context_panels(read(paths[5]), read(paths[6]), read(paths[7]))
    longform_manifest = read(paths[8])
    if (panel_result["panels_requested"] != longform_manifest["context_panels_requested"]
            or panel_result["panels_completed"] != longform_manifest["context_panels_completed"]):
        raise ValueError("context_panel_manifest_mismatch")
    return {"schema": SCHEMA, "method": "offline projection of preserved public numeric observations",
            "input_files": {p: {"sha256": file_digest(root / p), "bytes": (root / p).stat().st_size} for p in paths},
            "model_order": list(MODELS), "served_models": snapshot["models"],
            "comparison_snapshot_at": snapshot["snapshot_at"],
            "longform_snapshot_at": longform_manifest["snapshot_at"],
            "shared_typed_comparison": shared, "jev_full_context": panel_result}
