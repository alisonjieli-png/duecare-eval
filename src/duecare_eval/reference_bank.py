"""Validate the authored original-case bank and its blind judging packets."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re


REGISTERS = {"plain", "colloquial", "professional", "technical", "dense"}
POINT_FIELDS = {"candidate_id", "case_id", "task", "evidence", "candidate_response", "rubric_id", "applicable_criteria"}
PAIR_FIELDS = {"request_id", "case_id", "task", "evidence", "candidate_a_response", "candidate_b_response", "rubric_id", "applicable_criteria"}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def word_count(text):
    return len(re.findall(r"\b\w+(?:['’-]\w+)*\b", text))


def validate_bank(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != "duecare-public-reference-bank/1.0.0":
        raise ValueError("Select the supported original-case reference bank version.")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("A reference-bank artifact differs from its manifest digest.")
    cases = json.loads((root / "cases.json").read_text())
    lookup = {row["case_id"]: row for row in cases}
    candidates = rows(root / "candidates.jsonl")
    blind = rows(root / "blind_candidates.jsonl")
    pairs = rows(root / "pairs_evaluator.jsonl")
    blind_pairs = rows(root / "blind_pairs.jsonl")
    if len(cases) != 5 or len(lookup) != 5 or len(candidates) != 125 or len(blind) != 125:
        raise ValueError("The bank requires five source cases and 125 candidate answers.")
    by_id, profile_by_cell = {}, {}
    normalized = set()
    for row in candidates:
        case = lookup[row["case_id"]]
        response = row["candidate_response"]
        expected_id = "CAND-" + sha256(canonical([row["case_id"], response]).encode()).hexdigest()[:24]
        if row["candidate_id"] != expected_id or expected_id in by_id:
            raise ValueError("Candidate IDs must be distinct opaque response-content hashes.")
        if sha256(response.encode()).hexdigest() != row["response_sha256"]:
            raise ValueError("A candidate response differs from its recorded digest.")
        if sha256(case["task"].encode()).hexdigest() != row["original_prompt_sha256"] or row["original_prompt_sha256"] != case["original_prompt_sha256"]:
            raise ValueError("The full original source prompt changed.")
        profile = row["profile"]
        if not profile["minimum_words"] <= word_count(response) <= profile["maximum_words"] or word_count(response) != row["word_count"]:
            raise ValueError("A candidate's measured length falls outside its declared band.")
        if type(row["proposed_tier"]) is not int or row["proposed_tier"] not in range(1, 6):
            raise ValueError("Proposed tiers must use the five-level scale.")
        if row["proposed_tier"] == 5 and (row["canonical_tier_label"] != "best" or row["display_tier_label"] != "great"):
            raise ValueError("Great is the display label for canonical best, tier 5.")
        if row["hosted_assessed_grade"] is not None:
            raise ValueError("Measured assessments belong in separate observation records.")
        cell = row["case_id"], profile["length_slot"]
        if cell in profile_by_cell and profile_by_cell[cell] != profile:
            raise ValueError("Profile assignments must stay identical across proposed tiers within a case.")
        profile_by_cell[cell] = profile
        normalized.add(" ".join(re.findall(r"\b\w+(?:['’-]\w+)*\b", response.casefold())))
        by_id[expected_id] = row
    if len(normalized) != 125 or set(Counter((r["case_id"], r["proposed_tier"]) for r in candidates).values()) != {5}:
        raise ValueError("Every case/tier needs five distinct presentation examples.")
    for tier in range(1, 6):
        subset = [r for r in candidates if r["proposed_tier"] == tier]
        if Counter(r["profile"]["register"] for r in subset) != Counter({name: 5 for name in REGISTERS}):
            raise ValueError("Registers must remain balanced across proposed tiers.")
    cells = Counter((p["register"], p["length_slot"]) for p in profile_by_cell.values())
    if len(cells) != 25 or set(cells.values()) != {1}:
        raise ValueError("The five-case register/length rotation changed.")
    seen = set()
    for packet in blind:
        if set(packet) != POINT_FIELDS or packet["candidate_id"] in seen:
            raise ValueError("Blind pointwise packets must use the field allowlist and unique IDs.")
        seen.add(packet["candidate_id"])
        row = by_id[packet["candidate_id"]]
        case = lookup[row["case_id"]]
        if packet["case_id"] != row["case_id"] or packet["candidate_response"] != row["candidate_response"] or packet["task"] != case["task"] or packet["evidence"] != case["evidence"]:
            raise ValueError("A blind pointwise packet differs from its source case or candidate.")
    if seen != set(by_id):
        raise ValueError("Every authored candidate needs exactly one pointwise packet.")
    pair_map, groups = {}, defaultdict(list)
    for pair in pairs:
        if pair["request_id"] in pair_map:
            raise ValueError("Pair request IDs must be unique.")
        left, right = by_id[pair["candidate_a"]], by_id[pair["candidate_b"]]
        if left["case_id"] != right["case_id"] or left["case_id"] != pair["case_id"]:
            raise ValueError("Pairs must compare answers to the same full source case.")
        pair_map[pair["request_id"]] = pair
        groups[pair["pair_id"]].append(pair)
    if len(pair_map) != 500 or len(groups) != 250:
        raise ValueError("The comparison design requires 250 pairs in both orders.")
    degree = Counter()
    for group in groups.values():
        if len(group) != 2 or group[0]["candidate_a"] != group[1]["candidate_b"] or group[0]["candidate_b"] != group[1]["candidate_a"]:
            raise ValueError("Each logical pair must preserve both answer orders.")
        degree[group[0]["candidate_a"]] += 1
        degree[group[0]["candidate_b"]] += 1
    if set(degree.values()) != {4} or set(degree) != set(by_id):
        raise ValueError("Every candidate must have four planned opponents.")
    seen_pairs = set()
    for packet in blind_pairs:
        if set(packet) != PAIR_FIELDS or packet["request_id"] in seen_pairs or packet["request_id"] not in pair_map:
            raise ValueError("Blind pair packets must use the field allowlist and unique known IDs.")
        seen_pairs.add(packet["request_id"])
        pair = pair_map[packet["request_id"]]
        case = lookup[pair["case_id"]]
        if (packet["case_id"] != case["case_id"] or packet["task"] != case["task"] or packet["evidence"] != case["evidence"]
                or packet["candidate_a_response"] != by_id[pair["candidate_a"]]["candidate_response"]
                or packet["candidate_b_response"] != by_id[pair["candidate_b"]]["candidate_response"]):
            raise ValueError("A pair presentation differs from its full source task or exact candidates.")
    if seen_pairs != set(pair_map):
        raise ValueError("Every planned pair presentation needs one blind packet.")
    return {"underlying_source_cases": 5, "authored_candidates": 125, "candidates_per_proposed_tier_per_case": 5,
            "exact_published_prompts": sum(c["source_provenance"]["source_type"] == "exact_published_prompt" for c in cases),
            "documented_full_notebook_variants": sum(c["source_provenance"]["source_type"] == "documented_full_notebook_variant" for c in cases),
            "blind_pointwise_requests": len(blind), "logical_pairs": len(groups), "blind_pair_presentations": len(blind_pairs),
            "planned_judging_requests_per_judge": len(blind) + len(blind_pairs),
            "word_count_range": [min(row["word_count"] for row in candidates), max(row["word_count"] for row in candidates)],
            "proposed_tier_counts": dict(sorted(Counter(str(row["proposed_tier"]) for row in candidates).items())),
            "register_counts": dict(sorted(Counter(row["profile"]["register"] for row in candidates).items())),
            "format_counts": dict(sorted(Counter(row["profile"]["format"] for row in candidates).items())),
            "response_assessment_status": "Authored proposals; hosted observations are stored separately.", "passed": True}
