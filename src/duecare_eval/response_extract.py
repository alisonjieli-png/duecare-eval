"""Extract answer text while preserving the raw response and a removal log.

Provider output may contain reasoning channels, labels and commentary around
the answer, for example:

   <think>The user is asking about fees. I should be careful here.</think>
    Here is a brief answer:
    **Verdict:** The fee is likely unlawful.
    Let me know if you have other questions!

Those wrappers affect length, proposition checks, retrieval and analogy grading.
The extractor derives an answer field and records each removal's reason and
character span. Raw provider text remains available for replay and review.
Ambiguous boundaries receive an explicit review status.

Validation classes:
    clean          answer text as received
    stripped       answer recovered after wrapper removal
    refused        declined request, retained as a behavioral outcome
    empty          usable-content check returned empty
    contaminated   remaining wrapper requires review
    ambiguous      answer boundary requires review
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .contracts import canonical, sha

EXTRACTION_PROTOCOL = "response-extraction/1.0.0"

# ---------------------------------------------------------------- patterns

# Reasoning channels are recorded separately from the user-facing answer.
_THINK_BLOCK = re.compile(
    r"<think(?:ing)?>.*?</think(?:ing)?>", re.I | re.S)
_REASONING_BLOCK = re.compile(
    r"<reason(?:ing)?>.*?</reason(?:ing)?>", re.I | re.S)
_SCRATCHPAD = re.compile(
    r"<scratchpad>.*?</scratchpad>", re.I | re.S)
_ANALYSIS_BLOCK = re.compile(
    r"<analysis>.*?</analysis>", re.I | re.S)
_FENCED_THINK = re.compile(
    r"```(?:think|thinking|reasoning|analysis|scratchpad)\b.*?```", re.I | re.S)
# For an unterminated reasoning channel, everything after its tag is scratchpad.
_THINK_UNCLOSED = re.compile(r"<(think|reasoning|analysis|scratchpad)\b[^>]*>.*\Z",
                             re.I | re.S)

# Meta-commentary surrounding the answer.
_PREAMBLE = re.compile(
    r"^\s*(?:sure|certainly|of course|absolutely|okay|ok|alright|got it|happy to help)"
    r"[^\n]{0,120}?:\s*\n+", re.I)
_INTRO_LINE = re.compile(
    r"^\s*(?:here(?:'s| is)|below (?:is|are))\s+(?:a|an|the|my)?\s*"
    r"(?:brief|short|detailed|complete|sample|fictional)?\s*"
    r"(?:answer|response|reply|analysis)?\s*:?\s*\n+", re.I | re.M)
_OUTRO = re.compile(
    r"[\n\s]*(?:let me know if(?: you)?(?: have| need)?|i hope (?:this|that) helps|"
    r"hope this helps|hope that helps|feel free to|would you like me to|"
    r"is there anything else|if you (?:have|need) (?:any )?(?:other|further|more)"
    r"|happy to (?:help|clarify)|please let me know)[^\n]*\Z", re.I)
_TIER_META = re.compile(
    r"[\n\s]*(?:this (?:answer|response) (?:is|would be) (?:a )?|"
    r"(?:intended|target) (?:tier|rating)(?: is)?|tier\s*[:=]\s*\d|"
    r"grade\s*[:=]\s*\d|as requested,? (?:this|the))\b[^\n]*", re.I)
_LABEL_PREFIX = re.compile(
    r"^\s*(?:\*\*)?(?:answer|response|verdict|reply)(?:\*\*)?\s*[:：]\s*", re.I)
_MARKDOWN_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+.*$", re.M)
_BULLET = re.compile(r"^\s{0,3}[-*+]\s+", re.M)
_MD_EMPH = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])", re.S)
# Trailing emphasis markers from an interrupted bold run, e.g. "** x",
# can remain after label removal and receive a formatting cleanup.
_DANGLING_MD = re.compile(r"(?<![\w])\*+(?=\s)|(?<=\s)\*+(?![\w*])")

# A refusal is a distinct behavioral outcome. Its appropriateness is assessed
# against the request, while answer quality is scored on substantive responses.
_REFUSAL = re.compile(
    # Preserve the idiom "I cannot help but note ..." as a substantive response.
    r"\b(i (?:can'?t|cannot|am unable to|won'?t|will not|shall not|'d not|'ll not) "
    r"(?:help(?! but)|assist|provide|comply|do that|do this)|"
    r"i'?m (?:sorry|not able|not going to)|i am (?:sorry|not able|unable)|"
    r"i (?:must|have to) (?:decline|refuse)|"
    r"i (?:don'?t|do not) (?:provide|assist|help)|"
    r"as an ai[, ]|i'?m an ai[, ]|"
    r"against my (?:guidelines|programming|principles)|"
    r"i can'?t (?:in good conscience|help with that))\b", re.I)

#: Fold punctuation for pattern matching, including U+2019 in refusals such as
#: "I’m sorry, but I can’t help". Preserve the original response bytes.
_TYPOGRAPHIC = {
    "‘": "'", "’": "'", "ʼ": "'", "′": "'",
    "“": '"', "”": '"', "–": "-", "—": "-",
    " ": " ", "…": "...",
}


def fold_punctuation(text: str) -> str:
    """Fold typographic punctuation to ASCII so literal patterns can match.

    Apply the folded copy to pattern matching and retain the model's original
    text in the stored answer.
    """
    for bad, good in _TYPOGRAPHIC.items():
        if bad in text:
            text = text.replace(bad, good)
    return text


@dataclass
class Extraction:
    """One extraction result. `raw` is always retained."""

    status: str
    text: str
    raw: str
    removals: list = field(default_factory=list)
    is_refusal: bool = False
    wrapper_words: int = 0
    answer_words: int = 0
    note: str = ""

    @property
    def purity(self) -> float | None:
        """Fraction of the raw text that is actual answer.

        Near 1.0 means the provider returned an answer. Low values mean the
        measurement is dominated by scaffolding, and any metric computed on the
        raw text is mostly measuring the scaffold.
        """
        total = self.wrapper_words + self.answer_words
        if total == 0:
            return None
        return round(self.answer_words / total, 4)

    def as_dict(self) -> dict:
        return {
            "protocol": EXTRACTION_PROTOCOL,
            "status": self.status,
            "text": self.text,
            "is_refusal": self.is_refusal,
            "wrapper_words": self.wrapper_words,
            "answer_words": self.answer_words,
            "purity": self.purity,
            "removals": self.removals,
            "note": self.note,
            "raw_sha256": sha([self.raw]),
            "raw_retained": True,
        }


def _words(text: str) -> int:
    return len(text.split())


def _strip_reasoning(raw: str) -> tuple:
    """Remove scratchpad channels. Returns (text, removals)."""
    removals = []
    text = raw
    for name, pat in (("think", _THINK_BLOCK), ("reasoning", _REASONING_BLOCK),
                      ("scratchpad", _SCRATCHPAD), ("analysis", _ANALYSIS_BLOCK),
                      ("fenced_think", _FENCED_THINK)):
        matches = pat.findall(text)
        if matches:
            removed = sum(_words(m if isinstance(m, str) else " ".join(m)) for m in matches)
            text = pat.sub(" ", text)
            removals.append({"reason": f"reasoning_channel:{name}",
                             "occurrences": len(matches), "words": removed})
    unclosed = _THINK_UNCLOSED.search(text)
    if unclosed:
        removed = _words(unclosed.group(0))
        removals.append({"reason": "reasoning_channel:unterminated",
                         "occurrences": 1, "words": removed,
                         "detail": "model stopped mid-reasoning; tag onward discarded"})
        text = text[:unclosed.start()]
    return text, removals


def _strip_wrappers(text: str) -> tuple:
    """Remove preamble, labels, and outro. Returns (text, removals)."""
    removals = []
    for name, pat in (("preamble", _PREAMBLE), ("intro_line", _INTRO_LINE),
                      ("outro", _OUTRO), ("tier_meta", _TIER_META)):
        matches = list(pat.finditer(text))
        if matches:
            removed = sum(_words(m.group(0)) for m in matches)
            text = pat.sub("\n" if name != "outro" else "\n", text)
            removals.append({"reason": f"wrapper:{name}", "occurrences": len(matches),
                             "words": removed})
    m = _LABEL_PREFIX.match(text)
    if m:
        removals.append({"reason": "wrapper:label_prefix", "occurrences": 1,
                         "words": _words(m.group(0))})
        text = text[m.end():]
    # A label may sit on its own line, e.g. "**Verdict:**\ntext", where the
    # trailing formatting needs its own match.
    lead = re.match(r"^\s*\*?\*?(?:verdict|analysis|assessment|rating)\*?\*?\s*[:：]\s*\*?\*?\s*\n+",
                    text, re.I)
    if lead and not _LABEL_PREFIX.match(text):
        removals.append({"reason": "wrapper:label_line", "occurrences": 1,
                         "words": _words(lead.group(0))})
        text = text[lead.end():]
    return text, removals


def _demarkdown(text: str) -> tuple:
    """Reduce markdown to prose, logging the loss.

    Kept conservative: emphasis and headings go, but list structure and line
    breaks stay, because a bulleted list of three items is still three distinct
    claims and flattening it would hide that structure from the graders.
    """
    removals = []
    before = _words(text)
    t = _MD_HEADING.sub("", text)
    t = _MARKDOWN_BOLD.sub(r"\1", t)
    t = _MD_EMPH.sub(r"\1", t)
    t = _DANGLING_MD.sub("", t)
    t = t.replace("**", "").replace("__", "")
    after = _words(t)
    if after != before:
        removals.append({"reason": "markdown_decoration", "occurrences": None,
                         "words": before - after})
    return t, removals


def _unwrap_envelope(text: str) -> tuple:
    """Return answer text from a recognized JSON envelope.

    Accept fenced JSON and objects such as {"answer": ...}. Parse the object
    and select a recognized answer field. Return (text, removals), preserving
    free prose and the original provider text for review.
    """
    removals = []
    t = text.strip()
    fence = re.match(r"^```(?:json|jsonc|json5)?\s*\n(.*?)\n?```\s*$", t, re.S)
    if fence:
        removals.append({"reason": "envelope:code_fence", "occurrences": 1,
                         "words": _words(t) - _words(fence.group(1))})
        t = fence.group(1).strip()
    if not (t.startswith("{") and t.endswith("}")):
        return text, removals
    try:
        obj = json.loads(t)
    except Exception:
        return text, removals
    if not isinstance(obj, dict):
        return text, removals
    for key in ("answer", "response", "output", "text", "content", "verdict",
                "result", "final_answer", "message"):
        if isinstance(obj.get(key), str) and obj[key].strip():
            removals.append({"reason": f"envelope:json_field:{key}", "occurrences": 1,
                             "words": _words(t) - _words(obj[key]),
                             "detail": "sibling keys discarded; only the answer field is graded"})
            return obj[key].strip(), removals
    return text, removals


def extract(raw: str, min_answer_words: int = 3) -> Extraction:
    """Separate the answer from reasoning, wrappers and markdown.

    Retain ambiguous material and flag it for review. Every applied removal
    has a recorded reason, and the original response remains available.
    """
    if raw is None:
        return Extraction("empty", "", "", note="provider returned no content")
    raw = str(raw)
    if not raw.strip():
        return Extraction("empty", "", raw, note="whitespace only")

    text, removals = _strip_reasoning(raw)
    text, env = _unwrap_envelope(text)
    removals += env
    text, wrap = _strip_wrappers(text)
    removals += wrap
    text, md = _demarkdown(text)
    removals += md

    answer = text.strip()
    answer_words = _words(answer)
    wrapper_words = sum(r.get("words") or 0 for r in removals)
    # Match against folded punctuation. The stored answer keeps the model's own
    # bytes so the raw text stays faithful; only the comparison is normalised,
    # so "I’m sorry, but I can’t help" is recognised as the refusal it is.
    refusal = bool(_REFUSAL.search(fold_punctuation(answer)))

    if not answer:
        return Extraction("empty", "", raw, removals,
                          note="all content was wrapper or reasoning")

    if refusal:
        # Route refusals to the request-appropriateness assessment.
        return Extraction("refused", answer, raw, removals, is_refusal=True,
                          wrapper_words=wrapper_words, answer_words=answer_words,
                          note="model declined; grade the DECISION, not the prose")

    if answer_words < min_answer_words:
        return Extraction("contaminated", answer, raw, removals,
                          wrapper_words=wrapper_words, answer_words=answer_words,
                          note=f"only {answer_words} answer words survive extraction")

    # Purity measures the surviving text after reasoning removal. Report removed
    # reasoning separately so its effect on the raw word count stays visible.
    status = "stripped" if removals else "clean"
    return Extraction(status, answer, raw, removals,
                      wrapper_words=wrapper_words, answer_words=answer_words)


def reasoning_overhead(raw: str) -> int:
    """Words of scratchpad in a raw response.

    Report this alongside answer length to distinguish reasoning volume from
    the text used in answer-quality assessment.
    """
    if not raw:
        return 0
    _, removals = _strip_reasoning(str(raw))
    return sum(r.get("words") or 0 for r in removals)


def validate_batch(records: list, key: str = "response") -> dict:
    """Validate a whole run and report the contamination profile.

    Report the contamination rate alongside extraction statuses and retained
    text. Substantial contamination calls for review before interpreting
    length-sensitive measurements.
    """
    from collections import Counter
    rows = []
    for r in records:
        ex = extract(r.get(key))
        rows.append({
            "id": r.get("id"),
            "status": ex.status,
            "is_refusal": ex.is_refusal,
            "purity": ex.purity,
            "wrapper_words": ex.wrapper_words,
            "answer_words": ex.answer_words,
            "removals": [x["reason"] for x in ex.removals],
            "raw_sha256": ex.as_dict()["raw_sha256"],
        })
    statuses = Counter(r["status"] for r in rows)
    n = len(rows) or 1
    reasons = Counter(x for r in rows for x in r["removals"])
    refusals = sum(1 for r in rows if r["is_refusal"])
    purities = [r["purity"] for r in rows if r["purity"] is not None]
    gradeable = sum(1 for r in rows if r["status"] in ("clean", "stripped"))
    return {
        "protocol": EXTRACTION_PROTOCOL,
        "items": len(rows),
        "status_counts": dict(statuses),
        "gradeable": gradeable,
        "gradeable_rate": round(gradeable / n, 4),
        "refusal_count": refusals,
        "refusal_rate": round(refusals / n, 4),
        "contamination_rate": round(
            (statuses.get("contaminated", 0) + statuses.get("empty", 0)) / n, 4),
        "mean_purity": round(sum(purities) / len(purities), 4) if purities else None,
        "min_purity": round(min(purities), 4) if purities else None,
        "removal_reasons": dict(reasons.most_common()),
        "per_item": rows,
        "interpretation": [
            "gradeable means the item yields an answer after extraction.",
            "refusals are a behavioural outcome and must be scored as decisions, "
            "not as answers; an over-refusal is a failure and a correct refusal "
            "is a pass, and conflating the two inverts the safety metric.",
            "A high contamination rate invalidates length-sensitive metrics for "
            "the whole run, not just the affected items.",
        ],
    }
