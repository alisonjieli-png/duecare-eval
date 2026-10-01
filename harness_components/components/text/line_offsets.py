"""Index LF-delimited lines using original code-point offsets."""
from ._shared import STRING, INTEGER, array, obj, check, spec
SPEC = spec("line_offsets", "Index LF-delimited lines with one-based line numbers; end excludes LF, CR remains content, and trailing LF adds an empty line.",
    {"text": STRING}, {"lines": array(obj({"line": INTEGER, "start": INTEGER, "end": INTEGER}))},
    {"text": "a\nb\n"}, {"lines": [{"line": 1, "start": 0, "end": 1}, {"line": 2, "start": 2, "end": 3}, {"line": 3, "start": 4, "end": 4}]})
def run(payload):
    result, start = [], 0
    for number, line in enumerate(check(payload, SPEC)["text"].split("\n"), 1):
        result.append({"line": number, "start": start, "end": start + len(line)})
        start += len(line) + 1
    return {"lines": result}
