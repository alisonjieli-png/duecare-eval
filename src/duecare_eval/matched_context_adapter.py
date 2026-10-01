"""Separate deployment-condition findings for the original matched contexts."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .contracts import canonical, sha
from . import matched_context as M

VERSION = "duecare-matched-context-adapter-analysis/1.0.0"
CONDITIONS = {"gpt-oss-20b": "native_json_format", "glm-5-3": "native_think_low", "glm-5-3-flash": "native_think_low"}
EXTRA = {"condition_id", "baseline_request_sha256", "prepared_request_sha256"}


def summarize(records, manifest, baseline, cases, questions, evidence):
    if any(set(r) != M.FIELDS | EXTRA for r in records) or set(manifest["targets"]) != set(CONDITIONS):
        raise ValueError("adapter_projection_allowlist")
    stripped = [{k: v for k, v in r.items() if k not in EXTRA} for r in records]
    case_lookup = M.validate(stripped, manifest, cases, questions, evidence, expected_targets=3, require_jev=False)
    previous = {(r["target_id"], r["case_id"], r["arm"]): r for r in baseline}
    for row in records:
        key = (row["target_id"], row["case_id"], row["arm"])
        prior = previous[key]
        if row["condition_id"] != CONDITIONS[key[0]] or row["semantic_payload_sha256"] != prior["semantic_payload_sha256"]:
            raise ValueError("adapter_condition_or_context_changed")
        semantic = M.context(case_lookup[key[1]], key[2], questions, evidence)
        body = {"model": row["model_requested"], "messages": [
            {"role": "system", "content": manifest["formatting_instruction"]},
            {"role": "user", "content": canonical(semantic)}], "stream": False,
            "think": "low" if key[0] == "gpt-oss-20b" else False,
            "options": {"temperature": 0.0, "num_predict": 4096}}
        if sha(body) != row["baseline_request_sha256"] or any(a["request_sha256"] != sha(body) for a in prior["attempts"]):
            raise ValueError("baseline_payload_reconstruction_mismatch")
        if key[0] == "gpt-oss-20b":
            body["format"] = "json"
        else:
            body["think"] = "low"
        if sha(body) != row["prepared_request_sha256"] or any(a["request_sha256"] != sha(body) for a in row["attempts"]):
            raise ValueError("intervention_payload_reconstruction_mismatch")
    conditions = {}
    for target, condition in CONDITIONS.items():
        current = [r for r in records if r["target_id"] == target]
        original = [r for r in baseline if r["target_id"] == target]
        def coverage(population):
            return {"requested": 8, "recorded": sum(bool(r["attempts"]) for r in population),
                    "strict_complete": sum(r["strict_status"] == "completed" for r in population),
                    "analysis_complete": sum(r["analysis_status"] == "completed" for r in population),
                    "typed_fields_requested": 96, "typed_fields_available": sum(len(r["answers"]) for r in population),
                    "strict_outcomes": dict(sorted(Counter(r["strict_status"] for r in population).items()))}
        pairs = []
        for row in current:
            old = previous[target, row["case_id"], row["arm"]]
            pairs.extend([row["case_id"], row["arm"], q] for q in questions if q in row["answers"] and q in old["answers"])
        conditions[target] = {"condition_id": condition, "model": manifest["targets"][target]["model"],
                              "baseline": coverage(original), "followup": coverage(current),
                              "same_model_matched_numeric_fields": pairs,
                              "panels": [{k: r[k] for k in ("case_id", "arm", "strict_status", "analysis_status", "selection_method", "answers", "invalid_answers")} for r in current]}
    return {"schema": VERSION, "snapshot_at": manifest["snapshot_at"], "requested": 24,
            "physical_calls": manifest["physical_calls"], "conditions": conditions,
            "interpretation": {
                "intervention": "The same full source state, twelve questions and chat formatting instruction are reconstructed byte-for-byte. GPT-OSS20B adds format=json; both GLM targets change think=false to supported think=low. Output cap4096 and temperature0 are retained.",
                "deployment": "Each condition has its own eight-panel denominator and keeps original baseline failures. These are adapter/deployment comparisons, with one panel per case/arm, rather than a claim of model improvement.",
                "preflight": "The first context is included in each eight-panel cohort. Remaining contexts dispatch only after a valid complete semantic panel. A failed preflight leaves seven unattempted in coverage.",
                "cloud_format": "Ollama's structured-output documentation states that its Cloud currently lacks structured-output support. GPT's format=json request is an observed capability probe; enforced JSON was unavailable in this recorded preflight.",
                "calibration": "Raw probabilities and returned maximum choices remain model judgments. Independent correctness, legal interpretation and real-world probability calibration remain open.",
            }}


def reproduce(root):
    root = Path(root)
    prefix = root / "results/matched_context_adapter_2026-10-01"
    manifest = json.loads(prefix.with_suffix(".manifest.json").read_text())
    for path, expected in manifest["files"].items():
        if sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError("adapter_snapshot_hash_mismatch")
    def rows(name):
        return [json.loads(line) for line in (root / "results" / name).read_text().splitlines() if line.strip()]
    def read(name):
        return json.loads((root / "results" / name).read_text())
    return summarize(rows("matched_context_adapter_2026-10-01.jsonl"), manifest,
                     rows("matched_context_2026-09-30.jsonl"), read("longform_cases_2026-09-30.json"),
                     read("longform_jev_questions_2026-09-30.json"), read("longform_primary_sources_2026-09-30.json"))
