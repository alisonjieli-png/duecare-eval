"""Plain-language output for readers; analysis records stay machine-readable."""

ERROR_HINTS = {
    "unexpected_source_fields_or_duplicate_request": "A source record has unexpected fields or repeats a request ID.",
    "unknown_probe_or_repeat": "A record refers to an unknown question or an invalid repetition number.",
    "mixed_model_protocol": "This analysis expects Jev 1.13.0 records. Keep other model versions in a separate study.",
    "invalid_binary_probability": "A probability must be a finite number between 0 and 1.",
    "invalid_distribution": "A response distribution has missing choices, invalid probabilities, or an incorrect total.",
    "observations_exceed_requested": "There are more observations than planned requests. Check for duplicates or mixed runs.",
    "duplicate_case_view_probe_repeat": "Two records describe the same case, information view, question and repeat.",
    "invalid_style_record": "A comparison record has an unknown or repeated request ID, or unexpected fields.",
    "invalid_style_winner": "A comparison result must name A, B or tie.",
    "duplicate_or_unknown_response_id": "Match each response to a unique task ID in the selected answer keys. Check repeated or unknown IDs.",
    "invalid_response_record": "Each response needs a string task_id and a decision object. Follow the released response examples.",
    "hidden_reference_fields_in_input": "A model input contains reference fields. Check the input builder before sending tasks to a model.",
    "oracle_self_check_failed": "The scorer returned a different result from its answer keys. Run the tests and inspect the discrepancy.",
    "invalid_or_duplicate_decision_task_id": "Give each reference task a unique string task_id.",
    "invalid_decision_task_schema": "A reference task has an unexpected schema. Use the released reference format.",
    "invalid_decision_type": "Use a supported decision_type from the released reference examples.",
    "incomplete_decision_task": "A reference task needs its declared input, question and expected result.",
    "invalid_binary_expected": "A binary reference needs an expected value of true or false.",
    "invalid_ordinal_expected": "An ordinal reference needs an expected grade from 1 through 5.",
    "invalid_categorical_contract": "Check that each categorical reference names an expected choice from its choices list.",
    "invalid_multilabel_contract": "Check that expected labels belong to the task's labels list.",
    "decision_group_split_leakage": "Keep every variant of a source group in the same evaluation split.",
    "decision_task_digest_mismatch": "A task differs from its recorded digest. Use the matching reference version or record the intended revision.",
}


def explain_error(error):
    if isinstance(error, FileNotFoundError):
        return f"The file is missing: {error.filename}. Use a complete checkout, or check the path you supplied."
    if isinstance(error, PermissionError):
        return f"Access to {error.filename} needs read or write permission. Choose an accessible path."
    if isinstance(error, KeyError):
        return f"A required field is missing: {error.args[0]}. Check the input schema against the release examples."
    code, separator, detail = str(error).partition(":")
    if code in ERROR_HINTS:
        return ERROR_HINTS[code] + (f" Record: {detail}." if separator else "")
    return str(error)


def findings_text(findings):
    """Show each study's coverage alongside its measured results."""
    source = findings["source_studies"]["source_questions"]
    referral = findings["source_studies"]["referral_control"]
    matched = source["matched_question_groups"]
    lines = ["DueCare findings", f"Evidence captured through {findings['snapshot_at']}", "",
             f"Source questions: {source['completed']:,} of {source['requested']:,} assessments complete.",
             f"Referrals and control: {referral['completed']:,} of {referral['requested']:,} complete."]
    if matched["complete_groups"]:
        lines += ["", f"Matched question study: {matched['complete_groups']:,} groups from {matched['distinct_source_texts']:,} source prompts.",
                  f"Average change on repeat calls: {matched['mean_absolute_repeat_change']:.3f}.",
                  f"Average range across question variants: {matched['mean_within_repeat_wording_span']:.3f}.",
                  "These measure different kinds of variation. Some question variants change meaning."]
    labels = {"deepseek-v4.1-flash": "DeepSeek Flash", "kimi-k3": "Kimi K3"}
    lines += ["", "Style-control results:"]
    for model, result in findings["style_judges"].items():
        lines.append(f"  {labels.get(model, model)}: {result['correct']:,} of {result['completed']:,} outputs match the policy reference "
                     f"({result['completed']:,} of {result['requested']:,} requests complete).")
    lines += ["", "Each result applies to the declared tasks and screening policy.",
              "Read docs/PAPER.md for interpretation. Add --json for the complete analysis."]
    return "\n".join(lines)


def comparisons_text(findings):
    """Show full coverage and the exact matched populations for each comparison."""
    names = {key: details["model"] for key, details in findings["models"].items()}
    lines = ["DueCare model comparisons", f"Evidence captured through {findings['snapshot_at']}"]
    for suite, result in findings["suites"].items():
        shared = result["all_model_intersection"]
        lines += ["", f"{suite}: {result['requested_per_model']:,} requested tasks per model.",
                  f"Shared across all {len(result['models'])} models: {shared['tasks']:,} usable tasks."]
        for model, value in result["models"].items():
            matched = shared["models"][model]
            lines.append(f"  {names.get(model, model)}: {value['correct']:,}/{value['usable']:,} correct on usable outputs; "
                         f"{value['usable']:,}/{value['requested']:,} usable. "
                         f"Shared subset: {matched['correct']:,}/{matched['usable']:,} correct.")
        lines.append("  Pairwise usable task counts:")
        for pair in result["pairwise"]:
            lines.append(f"    {names.get(pair['left'], pair['left'])} / {names.get(pair['right'], pair['right'])}: "
                         f"{pair['matched_tasks']:,}")
    lines += ["", "Response-tier assessments:"]
    for result in findings["tier_assessment"]:
        lines.append(f"  {result['campaign']} / {result['producer']}, judged by {result['judge']}: "
                     f"{result['assessed']:,}/{result['requested']:,} assessed; "
                     f"{result['exact_tier_matches']:,}/{result['tier_comparisons']:,} match the requested tier.")
    lines += ["", "Each comparison uses its own shared task IDs and recorded configuration.",
              "Add --json for grouped uncertainty, per-family results and complete coverage records."]
    return "\n".join(lines)
