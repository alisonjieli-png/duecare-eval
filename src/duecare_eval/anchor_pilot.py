"""Numeric outcomes for the blind long-form candidate and pairwise pilot."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


def assess(packet):
    candidates = packet["candidates"]
    pairs = packet["pairwise"]
    if len(candidates) != 125 or len({r["candidate_id"] for r in candidates}) != 125:
        raise ValueError("candidate_denominator_changed")
    lookup = {r["candidate_id"]: r for r in candidates}
    if len(pairs) != 100 or len({r["request_id"] for r in pairs}) != 100:
        raise ValueError("pairwise_denominator_changed")
    for row in candidates:
        if type(row["proposed_tier"]) is not int or row["proposed_tier"] not in range(1, 6) or (row["assessed_grade"] is not None and (type(row["assessed_grade"]) is not int or row["assessed_grade"] not in range(1, 6))):
            raise ValueError("invalid_tier_or_grade")
        if any(v is not None and (type(v) is not int or v not in (0, 1, 2)) for v in row["criterion_scores"].values()):
            raise ValueError("invalid_criterion_score")
        if any(k in row for k in ("response", "candidate_response", "task", "quote")):
            raise ValueError("candidate_text_in_numeric_release")
    groups = defaultdict(list)
    for row in pairs:
        if row["candidate_a"] not in lookup or row["candidate_b"] not in lookup or row["winner"] not in ("A", "B", "tie", None):
            raise ValueError("unknown_pair_candidate_or_winner")
        if lookup[row["candidate_a"]]["case_id"] != row["case_id"] or lookup[row["candidate_b"]]["case_id"] != row["case_id"]:
            raise ValueError("cross_case_pair_changed")
        groups[row["pair_id"]].append(row)
    if len(groups) != 50 or any(len(g) != 2 for g in groups.values()):
        raise ValueError("paired_order_coverage_changed")
    complete = stable = 0
    for values in groups.values():
        a, b = values
        if a["candidate_a"] != b["candidate_b"] or a["candidate_b"] != b["candidate_a"]:
            raise ValueError("pair_orders_are_not_swapped")
        if a["winner"] is not None and b["winner"] is not None:
            complete += 1
            def identity(row):
                return row["candidate_a"] if row["winner"] == "A" else row["candidate_b"] if row["winner"] == "B" else "tie"
            stable += identity(a) == identity(b)
    def pointwise(values):
        measured = [r for r in values if r["assessed_grade"] is not None]
        return {"requested": len(values), "assessed_overall_grade": len(measured), "unavailable_grade": len(values) - len(measured),
            "exact_intent_matches": sum(r["proposed_tier"] == r["assessed_grade"] for r in measured),
            "intent_assessed_matrix": {str(t): {str(g): sum(r["proposed_tier"] == t and r["assessed_grade"] == g for r in measured) for g in range(1, 6)} for t in range(1, 6)},
            "outcomes": dict(Counter(r["status"] for r in values))}
    strata = {}
    for stratum in sorted({r["stratum"] for r in pairs}):
        subset = [r for r in pairs if r["stratum"] == stratum]
        usable = [r for r in subset if r["winner"] is not None]
        aligned = 0
        for row in usable:
            ta, tb = lookup[row["candidate_a"]]["proposed_tier"], lookup[row["candidate_b"]]["proposed_tier"]
            wanted = "tie" if ta == tb else "A" if ta > tb else "B"
            aligned += row["winner"] == wanted
        strata[stratum] = {"requested": len(subset), "discrete_winners_available": len(usable), "intent_relation_matches": aligned,
                          "ties": sum(r["winner"] == "tie" for r in usable)}
    return {"schema": "duecare-longform-anchor-pilot-findings/1.0.0", "pointwise": pointwise(candidates),
        "by_case": {cid: pointwise([r for r in candidates if r["case_id"] == cid]) for cid in sorted({r["case_id"] for r in candidates})},
        "by_length_profile": {str(p): pointwise([r for r in candidates if r["length_slot"] == p]) for p in range(5)},
        "by_register": {reg: pointwise([r for r in candidates if r["register"] == reg]) for reg in sorted({r["register"] for r in candidates})},
        "pairwise": {"pilot_requested": 100, "full_prepared_bank_requests": 500,
            "discrete_winners_available": sum(r["winner"] is not None for r in pairs),
            "strict_probability_distributions_available": sum(r["probabilities"] is not None for r in pairs),
            "logical_pairs": 50, "complete_swaps": complete, "stable_swaps": stable, "by_stratum": strata},
        "interpretation": "Intended tiers describe authored candidate design. Assessed grades and pairwise choices are measured model proposals. Intent matches describe this controlled bank, with independent substantive validation open."}


def reproduce(root):
    root = Path(root)
    manifest = json.loads((root / "results/longform_anchor_pilot_2026-09-30.manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if Path(name).name != name or sha256((root / "results" / name).read_bytes()).hexdigest() != expected:
            raise ValueError("anchor_pilot_digest_mismatch")
    packet = json.loads((root / "results/longform_anchor_pilot_2026-09-30.json").read_text())
    if packet["schema"] != "duecare-longform-anchor-pilot-numeric/1.0.0":
        raise ValueError("unknown_anchor_pilot_schema")
    bank = root / "examples/reference_bank_v1"
    for name, field in (("candidates.jsonl", "bank_candidates_sha256"), ("pairs_evaluator.jsonl", "bank_pairs_evaluator_sha256")):
        if sha256((bank / name).read_bytes()).hexdigest() != manifest[field]:
            raise ValueError("reference_bank_digest_mismatch")
    authored = {r["candidate_id"]: r for r in (json.loads(line) for line in (bank / "candidates.jsonl").read_text().splitlines() if line.strip())}
    pair_source = {r["request_id"]: r for r in (json.loads(line) for line in (bank / "pairs_evaluator.jsonl").read_text().splitlines() if line.strip())}
    for row in packet["candidates"]:
        ref = authored.get(row["candidate_id"])
        if ref is None or ref["case_id"] != row["case_id"] or ref["proposed_tier"] != row["proposed_tier"] or ref["response_sha256"] != row["candidate_response_sha256"]:
            raise ValueError("candidate_crosswalk_mismatch")
    for row in packet["pairwise"]:
        ref = pair_source.get(row["source_pair_request_id"])
        if ref is None or any(ref[k] != row[k] for k in ("candidate_a", "candidate_b", "case_id", "pair_id", "stratum")):
            raise ValueError("pair_crosswalk_mismatch")
    return assess(packet)
