"""Offline contract examples and independently specified text edge cases."""

import copy
import importlib
import json
from pathlib import Path
import re

import pytest


TEXT_DIRECTORY = Path(__file__).parents[1] / "components" / "text"
MODULE_NAMES = sorted(path.stem for path in TEXT_DIRECTORY.glob("*.py") if not path.name.startswith("_"))


def module(name):
    return importlib.import_module("harness_components.components.text." + name)


def call(name, payload):
    return module(name).run(payload)


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_declared_examples_and_no_input_mutation(name):
    component = module(name)
    assert component.SPEC["id"] == "text." + name
    assert component.SPEC["version"] == "1.0.0"
    assert component.SPEC["effects"] == ["pure"]
    assert component.SPEC["input_schema"]["additionalProperties"] is False
    assert component.SPEC["output_schema"]["additionalProperties"] is False
    json.dumps(component.SPEC, allow_nan=False)
    for example in component.SPEC["examples"]:
        payload = copy.deepcopy(example["input"])
        assert component.run(payload) == example["output"]
        assert payload == example["input"]


@pytest.mark.parametrize("name", MODULE_NAMES)
@pytest.mark.parametrize("bad_payload", [None, [], "text", 1, True])
def test_every_component_requires_plain_object(name, bad_payload):
    with pytest.raises(TypeError):
        call(name, bad_payload)


@pytest.mark.parametrize("name", MODULE_NAMES)
def test_every_component_rejects_unknown_fields(name):
    payload = copy.deepcopy(module(name).SPEC["examples"][0]["input"])
    payload["unknown_field"] = "untrusted"
    with pytest.raises(ValueError):
        call(name, payload)


@pytest.mark.parametrize("name,payload,expected", [
    ("trim_whitespace", {"text": "\u00a0a\u2003", "side": "left"}, {"text": "a\u2003"}),
    ("trim_whitespace", {"text": ""}, {"text": ""}),
    ("collapse_whitespace", {"text": " \n\t", "trim": False}, {"text": " "}),
    ("collapse_whitespace", {"text": "\u00a0x\u2003y\t", "trim": False}, {"text": " x y "}),
    ("normalize_newlines", {"text": "\r\r\n\u2028", "newline": "crlf"}, {"text": "\r\n\r\n\u2028"}),
    ("trim_line_ends", {"text": "a\t\u2028b \r\nc\u00a0 "}, {"text": "a\u2028b\r\nc\u00a0"}),
    ("remove_blank_lines", {"text": "\u00a0\r\nx\r\n\t"}, {"text": "x\r\n", "removed": 2}),
    ("dedent_text", {"text": "\ta\n  b"}, {"text": "\ta\n  b"}),
    ("indent_text", {"text": "\n \n", "prefix": ">", "include_blank": True}, {"text": ">\n> \n"}),
    ("split_lines", {"text": ""}, {"lines": []}),
    ("split_lines", {"text": "a\r\nb\u2028", "keepends": True}, {"lines": ["a\r\n", "b\u2028"]}),
    ("join_lines", {"lines": [], "final_separator": True}, {"text": "\n"}),
    ("number_lines", {"text": "x\n", "start": -1}, {"lines": [{"number": -1, "text": "x"}]}),
    ("stable_unique_lines", {"text": "A\na\n\nA\n"}, {"lines": ["A", "a", ""], "removed": 1}),
    ("sort_lines", {"text": "ß\nSS\nss", "casefold": True}, {"lines": ["ß", "SS", "ss"]}),
    ("chunk_lines", {"lines": [], "size": 5}, {"chunks": []}),
    ("split_paragraphs", {"text": "\n \n"}, {"paragraphs": []}),
    ("codepoint_length", {"text": "👩\u200d💻"}, {"length": 3}),
    ("utf8_length", {"text": "e\u0301"}, {"bytes": 3}),
    ("unicode_normalize", {"text": "ﬀ①", "form": "NFKC"}, {"text": "ff1", "changed": True}),
    ("unicode_normalize", {"text": "é", "form": "NFC"}, {"text": "é", "changed": False}),
    ("casefold_text", {"text": "İß"}, {"text": "i\u0307ss", "changed": True}),
    ("strip_combining_marks", {"text": "øé\u20dd"}, {"text": "øe", "removed_marks": 2}),
    ("unicode_inventory", {"text": "\x00"}, {"characters": [{"character": "\x00", "codepoint": "U+0000", "name": "", "category": "Cc", "count": 1, "first_offset": 0}]}),
    ("unicode_category_counts", {"text": ""}, {"categories": []}),
    ("detect_bidi_controls", {"text": "שלום\u200d"}, {"controls": []}),
    ("remove_controls", {"text": "a\u200db\n", "include_format": True, "allow": ""}, {"text": "ab", "removed": [{"offset": 1, "codepoint": "U+200D"}, {"offset": 3, "codepoint": "U+000A"}]}),
    ("normalize_decimal_digits", {"text": "०9Ⅷ²"}, {"text": "09Ⅷ²", "changed": 1}),
    ("ascii_slug", {"text": "東京"}, {"slug": ""}),
    ("character_frequencies", {"text": "e\u0301e"}, {"characters": [{"character": "e", "count": 2}, {"character": "\u0301", "count": 1}]}),
    ("word_spans", {"text": "e\u0301 can't"}, {"tokens": [{"text": "e", "start": 0, "end": 1}, {"text": "can", "start": 3, "end": 6}, {"text": "t", "start": 7, "end": 8}]}),
    ("whitespace_tokens", {"text": "\u00a0e\u0301\u2003"}, {"tokens": [{"text": "e\u0301", "start": 1, "end": 3}]}),
    ("token_frequencies", {"tokens": ["ß", "SS", "x"], "casefold": True}, {"tokens": [{"token": "ss", "count": 2}, {"token": "x", "count": 1}]}),
    ("token_ngrams", {"tokens": ["a"], "n": 2}, {"ngrams": []}),
    ("split_camel_case", {"text": "JSONParser fooBar"}, {"parts": ["JSON", "Parser", "foo", "Bar"]}),
    ("acronym_candidates", {"text": "éAPI API_ API"}, {"candidates": [{"text": "API", "start": 10, "end": 13}]}),
    ("common_prefix", {"texts": []}, {"prefix": ""}),
    ("common_suffix", {"texts": ["a", ""]}, {"suffix": ""}),
    ("truncate_codepoints", {"text": "abc", "limit": 0, "marker": "..."}, {"text": "", "truncated": True}),
    ("truncate_codepoints", {"text": "abc", "limit": 1, "marker": "..."}, {"text": ".", "truncated": True}),
    ("extract_between", {"text": "[a[b]c]", "opening": "[", "closing": "]"}, {"found": True, "text": "a[b", "start": 1, "end": 4}),
    ("extract_between", {"text": "a[b", "opening": "[", "closing": "]"}, {"found": False, "text": "", "start": -1, "end": -1}),
    ("replace_literal", {"text": "aaa", "old": "a", "new": "\\1", "count": 0}, {"text": "aaa", "replaced": 0}),
    ("find_literal_spans", {"text": "ß SS İ ß", "needle": "ß"}, {"spans": [[0, 1], [7, 8]]}),
    ("find_literal_spans", {"text": "ß SS İ ß", "needle": "SS"}, {"spans": [[2, 4]]}),
    ("find_literal_spans", {"text": "ß SS İ ß", "needle": "İ"}, {"spans": [[5, 6]]}),
    ("find_literal_spans", {"text": "aaa", "needle": "aa"}, {"spans": [[0, 2]]}),
    ("escape_regex_literal", {"text": "[x]"}, {"pattern": "\\[x\\]"}),
    ("literal_alternation_pattern", {"literals": []}, {"pattern": "(?!)"}),
    ("split_literal", {"text": ",a,,", "separator": ",", "maxsplit": 1}, {"parts": ["", "a,,"]}),
    ("partition_literal", {"text": "a", "separator": "=", "last": True}, {"before": "", "separator": "", "after": "a", "found": False}),
    ("merge_spans", {"spans": [[0, 1], [1, 2], [1, 1]], "text_length": 2, "merge_touching": False}, {"spans": [[0, 1], [1, 2]]}),
    ("redact_spans", {"text": "abcdef", "spans": [[1, 3], [2, 5]], "marker": "X"}, {"text": "aXf", "spans": [[1, 5]]}),
    ("mask_spans", {"text": "e\u0301🙂", "spans": [[1, 3]], "mask": "!"}, {"text": "e!!", "spans": [[1, 3]]}),
    ("span_context", {"text": "abc", "spans": [[0, 0]], "context": 5}, {"contexts": [{"start": 0, "end": 0, "match": "", "before": "", "after": "abc", "context_start": 0, "context_end": 3}]}),
    ("replace_spans", {"text": "abc", "replacements": [{"start": 3, "end": 3, "replacement": "!"}]}, {"text": "abc!", "replaced": 1}),
    ("line_offsets", {"text": ""}, {"lines": [{"line": 1, "start": 0, "end": 0}]}),
    ("offset_to_line_column", {"text": "é\r\n🙂", "offset": 2}, {"line": 1, "column": 2}),
    ("line_column_to_offset", {"text": "é\r\n🙂", "line": 2, "column": 1}, {"offset": 4}),
    ("wrap_text", {"text": "abcdefgh", "width": 3, "break_long_words": False}, {"lines": ["abcdefgh"]}),
    ("normalize_punctuation", {"text": "'plain' -"}, {"text": "'plain' -", "changed_codepoints": 0}),
])
def test_independent_edge_cases(name, payload, expected):
    assert call(name, payload) == expected


@pytest.mark.parametrize("email,status,reason", [
    ("\"a b\"@example.org", "unsupported", "quoted_or_header_syntax"),
    ("\"a@b\"@example.org", "unsupported", "quoted_or_header_syntax"),
    ("a@[127.0.0.1]", "unsupported", "domain_literal"),
    ("é@example.org", "unsupported", "internationalized_address"),
    ("a@例え.test", "unsupported", "internationalized_address"),
    ("a..b@example.org", "invalid", "local_dot_atom"),
    ("a@example..org", "invalid", "domain_labels"),
    ("a@-example.org", "invalid", "domain_labels"),
    ("a@example.org.", "invalid", "domain_labels"),
    (" a@example.org", "invalid", "local_dot_atom"),
    ("a@example.org ", "invalid", "domain_labels"),
    ("a@b@example.org", "invalid", "expected_one_at_sign"),
    ("a@example.org\r\nBcc:x@example.org", "invalid", "control_character"),
    ("a" * 65 + "@example.org", "invalid", "length_limit"),
    ("", "invalid", "expected_one_at_sign"),
])
def test_email_subset_failures_are_explicit(email, status, reason):
    assert call("email_normalize", {"email": email}) == {
        "status": status, "reason": reason, "local": "", "domain": "", "normalized": ""}


def test_email_preserves_case_dots_tags_and_ascii_atext():
    address = "A.b+Tag/Box=ok@EXAMPLE.ORG"
    assert call("email_normalize", {"email": address}) == {
        "status": "supported", "reason": "", "local": "A.b+Tag/Box=ok",
        "domain": "example.org", "normalized": "A.b+Tag/Box=ok@example.org"}
    assert call("email_compare", {"left": "A+tag@example.org", "right": "A@example.org"})["equal"] is False
    assert call("email_compare", {"left": "A@EXAMPLE.ORG", "right": "A@example.org"})["equal"] is True
    assert call("email_compare", {"left": "bad", "right": "bad"})["comparable"] is False


def test_email_mask_invalid_output_does_not_echo_input():
    assert call("email_mask", {"email": "bad"}) == {"status": "invalid", "reason": "expected_one_at_sign", "masked": ""}
    assert call("email_mask", {"email": "Ab@example.org", "reveal_prefix": 1}) == {"status": "supported", "reason": "", "masked": "A***@example.org"}


def test_email_candidate_keeps_complete_punctuation_token_and_source_offsets():
    result = call("email_candidates", {"text": "🙂 a@example.org, x@example.org"})["candidates"]
    assert [(item["text"], item["start"], item["end"]) for item in result] == [
        ("a@example.org,", 2, 16), ("x@example.org", 17, 30)]
    assert result[0]["mailbox"]["status"] == "unsupported"
    assert result[1]["mailbox"]["status"] == "supported"


def test_email_groups_preserve_duplicate_addresses():
    assert call("email_group_by_domain", {"emails": ["a@EXAMPLE.ORG", "a@example.org"]}) == {
        "groups": [{"domain": "example.org", "emails": ["a@example.org", "a@example.org"]}], "rejected": []}


def test_lexicon_casefold_matches_keep_original_codepoint_spans():
    lexicon = [{"term": "SS", "meanings": ["double s"]}, {"term": "İ", "meanings": ["dotted I"]}]
    result = call("slang_matches", {"text": "ß SS İ x", "lexicon": lexicon})
    assert result == {"matches": [
        {"text": "ß", "term": "SS", "start": 0, "end": 1, "meanings": ["double s"], "ambiguous": False},
        {"text": "SS", "term": "SS", "start": 2, "end": 4, "meanings": ["double s"], "ambiguous": False},
        {"text": "İ", "term": "İ", "start": 5, "end": 6, "meanings": ["dotted I"], "ambiguous": False},
    ]}
    assert call("expand_lexicon", {"text": "ß SS İ x", "lexicon": lexicon}) == {
        "text": "double s double s dotted I x", "replaced": 3, "ambiguous_spans": []}


def test_lexicon_word_boundaries_ambiguity_and_no_context_inference():
    lexicon = [{"term": "op", "meanings": ["original poster", "overpowered"]}]
    assert call("expand_lexicon", {"text": "stop OP op_", "lexicon": lexicon}) == {
        "text": "stop OP op_", "replaced": 0, "ambiguous_spans": [[5, 7]]}
    assert call("slang_lookup", {"term": "OP", "lexicon": lexicon, "casefold": False}) == {
        "found": False, "meanings": [], "ambiguous": False}
    assert call("slang_matches", {"text": "op", "lexicon": []}) == {"matches": []}


@pytest.mark.parametrize("name,payload,error", [
    ("trim_whitespace", {"text": 1}, TypeError),
    ("trim_whitespace", {}, ValueError),
    ("trim_whitespace", {"text": "x", "side": "middle"}, ValueError),
    ("chunk_lines", {"lines": [1], "size": 1}, TypeError),
    ("chunk_lines", {"lines": [], "size": True}, TypeError),
    ("chunk_lines", {"lines": [], "size": 0}, ValueError),
    ("token_ngrams", {"tokens": [], "n": -1}, ValueError),
    ("utf8_length", {"text": "\ud800"}, ValueError),
    ("unicode_normalize", {"text": "a", "form": "nfc"}, ValueError),
    ("find_literal_spans", {"text": "abc", "needle": ""}, ValueError),
    ("split_literal", {"text": "abc", "separator": ""}, ValueError),
    ("literal_alternation_pattern", {"literals": [""]}, ValueError),
    ("mask_spans", {"text": "abc", "spans": [[0, 2]], "mask": "xx"}, ValueError),
    ("mask_spans", {"text": "abc", "spans": [[True, 2]]}, TypeError),
    ("mask_spans", {"text": "abc", "spans": [[0, 4]]}, ValueError),
    ("redact_spans", {"text": "abc", "spans": [[2, 1]]}, ValueError),
    ("merge_spans", {"spans": [[0, 1, 2]], "text_length": 3}, ValueError),
    ("replace_spans", {"text": "abc", "replacements": [{"start": 0, "end": 2, "replacement": "x"}, {"start": 1, "end": 3, "replacement": "y"}]}, ValueError),
    ("replace_spans", {"text": "abc", "replacements": [{"start": 0, "end": 0, "replacement": "x"}, {"start": 0, "end": 0, "replacement": "y"}]}, ValueError),
    ("offset_to_line_column", {"text": "a", "offset": 2}, ValueError),
    ("line_column_to_offset", {"text": "a", "line": 2, "column": 0}, ValueError),
    ("line_column_to_offset", {"text": "a", "line": 1, "column": 2}, ValueError),
    ("email_normalize", {"email": None}, TypeError),
    ("email_mask", {"email": "a@example.org", "marker": ""}, ValueError),
    ("slang_lookup", {"term": "idk", "lexicon": [{"term": "idk", "meanings": []}]}, ValueError),
    ("slang_lookup", {"term": "idk", "lexicon": [{"term": "idk", "meanings": [""]}]}, ValueError),
    ("slang_lookup", {"term": "idk", "lexicon": [{"term": "idk", "meanings": [1]}]}, TypeError),
    ("slang_lookup", {"term": "a", "lexicon": [{"term": "two words", "meanings": ["x"]}]}, ValueError),
    ("slang_lookup", {"term": "ß", "lexicon": [{"term": "ß", "meanings": ["x"]}, {"term": "SS", "meanings": ["y"]}]}, ValueError),
])
def test_rejected_types_and_values(name, payload, error):
    with pytest.raises(error):
        call(name, payload)


def test_literal_generated_patterns_cannot_activate_input_metacharacters():
    inputs = ["(a+)+$", "[", "\\1", "a|b", ".*"]
    pattern = call("literal_alternation_pattern", {"literals": inputs})["pattern"]
    for literal in inputs:
        assert re.fullmatch(pattern, literal) is not None
    assert re.fullmatch(pattern, "aaaaaaaaaa") is None


@pytest.mark.parametrize("text", ["", "a", "a\n", "\n\n", "é\r\n🙂e\u0301"])
def test_line_coordinate_roundtrip_at_every_valid_original_offset(text):
    for offset in range(len(text) + 1):
        coordinates = call("offset_to_line_column", {"text": text, "offset": offset})
        assert call("line_column_to_offset", {"text": text, **coordinates}) == {"offset": offset}
