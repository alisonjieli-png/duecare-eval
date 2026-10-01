"""Private caller-supplied slang/acronym lexicon helpers.

Matches express only the supplied lexicon. They establish neither contextual
meaning nor a speaker's age, identity, location or demographic membership.
"""
import re
from ._shared import STRING, STRINGS, array, obj
LEXICON = array(obj({"term": STRING, "meanings": STRINGS}))
def index_lexicon(entries, casefold):
    result = {}
    for entry in entries:
        term, meanings = entry["term"], entry["meanings"]
        if re.fullmatch(r"\w+", term) is None:
            raise ValueError("lexicon term must be a nonempty Python-regex word token")
        if not meanings or any(not meaning for meaning in meanings) or len(set(meanings)) != len(meanings):
            raise ValueError("meanings must be nonempty, distinct strings")
        key = term.casefold() if casefold else term
        if key in result:
            raise ValueError("duplicate lexicon key after case normalization")
        result[key] = entry
    return result
def matches(text, index, casefold):
    result = []
    for match in re.finditer(r"\w+", text):
        key = match.group().casefold() if casefold else match.group()
        if key in index:
            entry = index[key]
            result.append({"text": match.group(), "term": entry["term"], "start": match.start(), "end": match.end(), "meanings": list(entry["meanings"]), "ambiguous": len(entry["meanings"]) > 1})
    return result
