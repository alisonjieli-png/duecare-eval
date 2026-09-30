"""Response extraction: the answer is what gets graded, not the scaffold.

A benchmark that grades reasoning traces, JSON envelopes and pleasantries is
measuring the harness, not the model. These cases came from probing the live
tactical endpoint, because the existing bank turned out to be 100% clean and so
could not exercise any of it.
"""
from __future__ import annotations

import json

import pytest

from duecare_eval.response_extract import (EXTRACTION_PROTOCOL, extract,
                                           reasoning_overhead, validate_batch)

CLEAN = "Fees are categorically illegal with no exceptions."


# --- reasoning must be removed, and must not condemn the answer ---

def test_clean_response_passes_through():
    e = extract(CLEAN)
    assert e.status == "clean" and e.text == CLEAN
    assert e.purity == 1.0 and e.is_refusal is False


def test_think_block_is_removed_not_graded():
    raw = "<think>The user asks about fees. I must be careful.</think>The fee may be unlawful."
    e = extract(raw)
    assert "<think>" not in e.text and "careful" not in e.text
    assert e.text.startswith("The fee may be unlawful")
    assert "reasoning_channel:think" in [r["reason"] for r in e.removals]


def test_long_reasoning_does_not_condemn_a_clean_answer():
    """Regression: purity was once computed against the RAW length, so a
    perfectly good answer behind a think block was marked contaminated and
    discarded - throwing away the most trustworthy items."""
    raw = "<think>" + ("I must weigh the jurisdictional scope carefully. " * 40) + \
          "</think>The fee may be unlawful in this scenario."
    e = extract(raw)
    assert e.status == "stripped", e.status
    assert e.answer_words > 3
    assert reasoning_overhead(raw) > 100


def test_unterminated_reasoning_is_discarded():
    raw = "Here is my answer.<think>I need to check the scope before"
    e = extract(raw)
    assert "<think>" not in e.text
    assert "reasoning_channel:unterminated" in [r["reason"] for r in e.removals]


def test_all_thinking_is_empty():
    assert extract("<think>only reasoning here</think>").status == "empty"


# --- wrappers ---

def test_preamble_and_outro_removed():
    e = extract("Sure! Here is a brief answer:\n\nThe fee may be unlawful. "
                "Let me know if you have other questions!")
    assert e.text == "The fee may be unlawful."
    assert e.status == "stripped"


def test_label_prefix_removed():
    assert extract("ANSWER: The fee may be unlawful.").text == "The fee may be unlawful."


def test_markdown_demarshalled_without_damage():
    e = extract("**Verdict:** The fee is likely unlawful.\n- one\n- two")
    assert e.text.startswith("The fee is likely unlawful")
    assert "**" not in e.text


def test_tier_metadata_stripped():
    """A leaked intended-tier label is a benchmark-integrity failure: it tells
    the judge the answer key."""
    e = extract("The fee is unlawful. This answer is a tier 1 benchmark item.")
    assert "tier 1" not in e.text.lower()


# --- structured envelopes: the trap purity alone misses ---

def test_fenced_json_envelope_unwrapped():
    raw = '```json\n{"answer": "Do not pay the fee and keep your passport.",\n "confidence": 0.9}\n```'
    e = extract(raw)
    assert e.text == "Do not pay the fee and keep your passport."
    assert "confidence" not in e.text
    assert "envelope:code_fence" in [r["reason"] for r in e.removals]


def test_bare_json_envelope_unwrapped():
    e = extract('{"answer": "Keep your passport and do not pay the fee."}')
    assert e.text == "Keep your passport and do not pay the fee."


def test_json_without_answer_key_is_left_alone():
    raw = '{"foo": "bar", "baz": 1}'
    assert extract(raw).text == raw


def test_prose_with_numbers_is_not_mistaken_for_json():
    raw = "The fee is 10 percent in Hong Kong and was 25 in 2019."
    assert extract(raw).text == raw


def test_prose_mentioning_braces_is_not_unwrapped():
    raw = "Use the format {answer: your text} when you reply."
    assert extract(raw).text == raw


# --- refusals are decisions, not answers ---

@pytest.mark.parametrize("raw", [
    "I'm sorry, but I can't help with that request.",
    "I cannot assist with that.",
    "As an AI, I must decline.",
])
def test_refusals_are_classified(raw):
    e = extract(raw)
    assert e.status == "refused" and e.is_refusal is True


# --- losslessness and auditability ---

def test_raw_is_always_retained_and_hashed():
    raw = "<think>x</think>The fee may be unlawful."
    d = extract(raw).as_dict()
    assert d["raw_retained"] is True
    assert d["protocol"] == EXTRACTION_PROTOCOL
    assert d["raw_sha256"]


def test_every_removal_states_a_reason_and_word_count():
    raw = "Sure! **Answer:** The fee is unlawful. Let me know if you need more."
    e = extract(raw)
    assert e.removals
    for r in e.removals:
        assert "reason" in r and "words" in r


# --- batch validation ---

def test_validate_batch_reports_contamination_profile():
    rows = [
        {"id": "a", "response": CLEAN},
        {"id": "b", "response": "<think>reasoning only</think>"},
        {"id": "c", "response": "I'm sorry, but I can't help with that."},
        {"id": "d", "response": '```json\n{"answer": "Keep your passport."}\n```'},
    ]
    rep = validate_batch(rows)
    assert rep["items"] == 4
    assert rep["refusal_count"] == 1
    assert rep["status_counts"]["refused"] == 1
    assert rep["gradeable"] >= 2
    assert 0.0 <= rep["contamination_rate"] <= 1.0
    assert "interpretation" in rep
    assert len(rep["per_item"]) == 4


def test_validate_batch_on_empty_input():
    rep = validate_batch([])
    assert rep["items"] == 0 and rep["mean_purity"] is None


# --- typographic punctuation in refusals ---
# Found by the first executed benchmark run: 5 of 20 responses were the string
# "I’m sorry, but I can’t help with that." and every one was classified `clean`
# and graded as an answer. The patterns are ASCII; the models are not.

@pytest.mark.parametrize("text", [
    "I’m sorry, but I can’t help with that.",
    "I’m sorry, but I can’t assist with this request.",
    "I can’t provide that information.",
    "I’m not able to help with this.",
])
def test_typographic_apostrophe_refusals_are_detected(text):
    ex = extract(text)
    assert ex.status == "refused", (text, ex.status, ex.note)
    assert ex.is_refusal is True


def test_ascii_and_typographic_refusals_agree():
    """Same refusal, two encodings, one verdict."""
    ascii_form = extract("I'm sorry, but I can't help with that.")
    typo_form = extract("I’m sorry, but I can’t help with that.")
    assert ascii_form.status == typo_form.status == "refused"
    assert ascii_form.is_refusal == typo_form.is_refusal is True


def test_stored_answer_keeps_the_models_own_bytes():
    """Folding is for matching only. The recorded answer must stay faithful."""
    original = "I’m sorry, but I can’t help with that."
    ex = extract(original)
    assert ex.text == original
    assert ex.raw == original


def test_idiom_is_still_not_a_refusal():
    """"I cannot help but note ..." means the answer is going ahead."""
    ex = extract("I cannot help but note that you should keep your own copy of "
                    "the contract and request a receipt for any fee you pay.")
    assert ex.status != "refused", ex.status


def test_a_real_answer_is_not_mistaken_for_a_refusal():
    ex = extract("Keep your passport. The cap is 20% of first-month salary, so "
                    "request a receipt for anything above that figure and refuse to "
                    "sign a contract listing a higher amount.")
    assert ex.status in ("clean", "stripped")
    assert ex.is_refusal is False
