"""Shared pure search helpers used by the separately catalogued operations.

Text offsets are zero-based Unicode code-point offsets with an exclusive end.
Search tokens contain Unicode alphanumerics, underscores and following combining
marks, then receive NFKC normalization and casefolding. This deterministic
tokenizer makes no language-segmentation claim.
"""
from collections import Counter
from copy import deepcopy
import json
import math
import re
import shlex
import unicodedata

S = {"type": "string"}
N = {"type": "number"}
I = {"type": "integer", "minimum": 0}
B = {"type": "boolean"}
SCALAR = {"type": ["string", "number", "boolean", "null"]}
SOURCES = {
    "python": "https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str",
    "unicode": "https://docs.python.org/3/library/unicodedata.html",
    "regex": "https://docs.python.org/3/library/re.html",
    "shlex": "https://docs.python.org/3/library/shlex.html",
    "index": "https://nlp.stanford.edu/IR-book/html/htmledition/positional-indexes-1.html",
    "tfidf": "https://nlp.stanford.edu/IR-book/html/htmledition/tf-idf-weighting-1.html",
    "cosine": "https://nlp.stanford.edu/IR-book/html/htmledition/dot-products-1.html",
    "bm25": "https://lucene.apache.org/core/7_6_0/core/org/apache/lucene/search/similarities/BM25Similarity.html",
    "rrf": "https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf",
    "mmr": "https://aclanthology.org/X98-1025/",
    "sqlite": "https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries",
    "like": "https://www.sqlite.org/lang_expr.html#the_like_glob_regexp_match_and_extract_operators",
    "fts5": "https://www.sqlite.org/fts5.html#full_text_query_syntax",
    "metrics": "https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html",
    "math": "https://docs.python.org/3/library/math.html",
    "set": "https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset",
}


def obj(properties, required=None):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required, "additionalProperties": False}


def arr(items, minimum=0, unique=False):
    value = {"type": "array", "items": items, "minItems": minimum}
    if unique: value["uniqueItems"] = True
    return value


def mapping(values):
    return {"type": "object", "properties": {}, "required": [], "additionalProperties": values}


def integer(minimum=0):
    return {"type": "integer", "minimum": minimum}


def number(minimum=None, maximum=None):
    result = {"type": "number"}
    if minimum is not None: result["minimum"] = minimum
    if maximum is not None: result["maximum"] = maximum
    return result


def choice(*values):
    return {"type": "string", "enum": list(values)}


STRINGS = arr(S)
IDS = arr({"type": "string", "minLength": 1}, unique=True)
VECTOR = arr(N)
SPAN = obj({"start": I, "end": I})
CHUNK = obj({"id": S, "start": I, "end": I, "text": S})
DOC = obj({"id": {"type": "string", "minLength": 1}, "text": S})
DOCS = arr(DOC)
INDEX = obj({"document_ids": IDS, "lengths": mapping(I), "postings": mapping(mapping(arr(I, unique=True)))})
RANKING = arr(obj({"id": S, "score": N, "rank": integer(1)}))
SQL_OUTPUT = {"sql": S, "params": arr(SCALAR)}
# The final lookahead requires the absolute end, including under Python's
# search semantics where '$' alone can match before a trailing newline.
IDENTIFIER = {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*(?![\\s\\S])"}


def spec(name, description, inputs, outputs, example_input, example_output, *, sources=("python",)):
    return {"id": "search." + name, "version": "1.0.0", "description": description,
        "input_schema": obj(deepcopy(inputs)), "output_schema": obj(deepcopy(outputs)), "effects": ["pure"],
        "examples": [{"input": deepcopy(example_input), "output": deepcopy(example_output)}],
        "sources": [SOURCES[source] for source in sources]}


def require(condition, reason):
    if not condition: raise ValueError(reason)


def json_value(value):
    if value is None or type(value) in (str, bool, int): return
    if type(value) is float:
        require(math.isfinite(value), "JSON numbers must be finite"); return
    if type(value) is list:
        for item in value: json_value(item)
        return
    if type(value) is dict:
        require(all(type(key) is str for key in value), "JSON object keys must be strings")
        for item in value.values(): json_value(item)
        return
    raise TypeError("JSON values only")


def validate(value, schema, path="payload"):
    kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    matches = {"object": type(value) is dict, "array": type(value) is list, "string": type(value) is str,
        "integer": type(value) is int, "number": type(value) in (int, float), "boolean": type(value) is bool, "null": value is None}
    require(any(matches[kind] for kind in kinds), path + ": wrong JSON type")
    if "enum" in schema: require(value in schema["enum"], path + ": unknown value")
    if type(value) in (int, float):
        try: finite = math.isfinite(value)
        except OverflowError: finite = False
        require(finite, path + ": finite numeric range required")
        if "minimum" in schema: require(value >= schema["minimum"], path + ": below minimum")
        if "maximum" in schema: require(value <= schema["maximum"], path + ": above maximum")
    if type(value) is str:
        require(len(value) >= schema.get("minLength", 0), path + ": too short")
        if "pattern" in schema: require(re.fullmatch(schema["pattern"], value) is not None, path + ": invalid identifier")
    if type(value) is list:
        require(len(value) >= schema.get("minItems", 0), path + ": too few items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False) for item in value]
            require(len(set(encoded)) == len(encoded), path + ": duplicate items")
        for index, item in enumerate(value): validate(item, schema["items"], path + "/" + str(index))
    if type(value) is dict:
        properties = schema["properties"]; additional = schema["additionalProperties"]
        require(set(schema["required"]) <= set(value), path + ": missing fields")
        require(additional is not False or set(value) <= set(properties), path + ": unknown fields")
        for key, item in value.items(): validate(item, properties[key] if key in properties else additional, path + "/" + key)


def check(payload, definition):
    json_value(payload); validate(payload, definition["input_schema"])
    return payload


def finish(result, definition):
    json_value(result); validate(result, definition["output_schema"], "result")
    return result


def normalized(text):
    return unicodedata.normalize("NFKC", text).casefold()


def tokens(text):
    result, start = [], None
    for position, char in enumerate(text):
        word = char.isalnum() or char == "_" or start is not None and unicodedata.category(char).startswith("M")
        if word and start is None: start = position
        elif not word and start is not None:
            result.append({"term": normalized(text[start:position]), "start": start, "end": position}); start = None
    if start is not None: result.append({"term": normalized(text[start:]), "start": start, "end": len(text)})
    return result


def terms(text):
    return [token["term"] for token in tokens(text)]


def phrase_spans(text, phrase):
    wanted, found = terms(phrase), tokens(text)
    if not wanted: return []
    size = len(wanted)
    return [{"start": found[i]["start"], "end": found[i + size - 1]["end"]} for i in range(len(found) - size + 1)
            if [token["term"] for token in found[i:i + size]] == wanted]


def query_parts(query):
    try: parts = shlex.split(query, posix=True)
    except ValueError: raise ValueError("unclosed query quote") from None
    result = {"required": [], "optional": [], "excluded": []}
    for part in parts:
        key = "required" if part.startswith("+") else "excluded" if part.startswith("-") else "optional"
        value = part[1:] if key != "optional" else part
        require(bool(terms(value)), "query clauses need searchable tokens")
        if value not in result[key]: result[key].append(value)
    return result


def occurrences(text, needle):
    if not needle: return []
    result, position = [], 0
    while True:
        start = text.find(needle, position)
        if start < 0: return result
        result.append({"start": start, "end": start + len(needle)})
        position = start + 1


def lines(text):
    result, start = [], 0
    for number, raw in enumerate(text.splitlines(keepends=True), 1):
        content = raw.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")
        result.append({"line": number, "start": start, "end": start + len(content), "text": content})
        start += len(raw)
    return result


def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        require(0 <= start <= end, "ordered nonnegative span required")
        if start == end: continue
        if result and start <= result[-1][1]: result[-1][1] = max(end, result[-1][1])
        else: result.append([start, end])
    return result


def documents(values):
    require(len({row["id"] for row in values}) == len(values), "duplicate document id")
    return values


def index_documents(values):
    documents(values)
    index = {"document_ids": [row["id"] for row in values], "lengths": {}, "postings": {}}
    for row in values:
        words = terms(row["text"]); index["lengths"][row["id"]] = len(words)
        for position, term in enumerate(words): index["postings"].setdefault(term, {}).setdefault(row["id"], []).append(position)
    index["postings"] = dict(sorted(index["postings"].items()))
    return index


def valid_index(index):
    ids = set(index["document_ids"])
    require(set(index["lengths"]) == ids, "index lengths must cover document IDs")
    covered = {identifier: set() for identifier in ids}
    for term, posting in index["postings"].items():
        require(bool(term) and set(posting) <= ids, "unknown posting document or empty term")
        for identifier, positions in posting.items():
            require(positions and positions == sorted(set(positions)), "posting positions must be increasing and nonempty")
            require(all(0 <= p < index["lengths"][identifier] and p not in covered[identifier] for p in positions), "invalid or overlapping posting position")
            covered[identifier].update(positions)
    require(all(len(covered[key]) == index["lengths"][key] for key in ids), "incomplete positional index")
    return index


def tfidf(values):
    index = index_documents(values); n = len(values)
    idf = {term: math.log(n / len(posting)) for term, posting in index["postings"].items()}
    vectors = {row["id"]: {term: count * idf[term] for term, count in Counter(terms(row["text"])).items()} for row in values}
    return idf, vectors


def cosine(a, b):
    require(len(a) == len(b), "vector dimensions differ")
    scale_a, scale_b = max((abs(x) for x in a), default=0), max((abs(x) for x in b), default=0)
    if scale_a == 0 or scale_b == 0: return 0.0
    a, b = [x / scale_a for x in a], [x / scale_b for x in b]
    norm_a, norm_b = math.hypot(*a), math.hypot(*b)
    result = math.fsum((x / norm_a) * (y / norm_b) for x, y in zip(a, b))
    return max(-1.0, min(1.0, result))


def sparse_cosine(a, b):
    keys = sorted(set(a) | set(b))
    return cosine([a.get(key, 0.0) for key in keys], [b.get(key, 0.0) for key in keys])


def ranking(scores, limit):
    return [{"id": identifier, "score": round(score, 12), "rank": rank} for rank, (identifier, score) in enumerate(sorted(scores.items(), key=lambda row: (-row[1], row[0]))[:limit], 1)]


def bm25_parts(values, query, k1, b):
    require(k1 > 0, "k1 must be positive")
    index = index_documents(values); n = len(values)
    average = sum(index["lengths"].values()) / n if n else 0.0
    query_terms = sorted(set(terms(query))); result = {}
    for row in values:
        counts = Counter(terms(row["text"])); length = index["lengths"][row["id"]]
        norm = 1 - b + b * length / average if average else 1.0
        components = []
        for term in query_terms:
            df = len(index["postings"].get(term, {})); frequency = counts.get(term, 0)
            idf = math.log1p((n - df + 0.5) / (df + 0.5)) if n else 0.0
            contribution = idf * frequency * (k1 + 1) / (frequency + k1 * norm) if frequency else 0.0
            components.append({"term": term, "document_frequency": df, "term_frequency": frequency,
                "idf": idf, "length_normalization": norm, "contribution": contribution})
        result[row["id"]] = components
    return result, average


def quoted_identifier(value):
    require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) is not None, "simple SQL identifier required")
    return '"' + value + '"'


def equal_where(values):
    require(bool(values), "explicit nonempty WHERE conditions required")
    clauses, params = [], []
    for key in sorted(values):
        name = quoted_identifier(key)
        if values[key] is None: clauses.append(name + " IS NULL")
        else: clauses.append(name + " = ?"); params.append(values[key])
    return " AND ".join(clauses), params


def fts_quote(value):
    require("\x00" not in value, "FTS text must not contain NUL")
    return '"' + value.replace('"', '""') + '"'


def rank_ids(retrieved, relevant):
    require(len(retrieved) == len(set(retrieved)) and len(relevant) == len(set(relevant)), "ranking and relevance IDs must be unique")
    return set(relevant)


def rr(retrieved, relevant):
    wanted = rank_ids(retrieved, relevant)
    return next((1.0 / rank for rank, identifier in enumerate(retrieved, 1) if identifier in wanted), 0.0)


def dcg(gains, k):
    return math.fsum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains[:k], 1))
