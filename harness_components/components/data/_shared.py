"""Shared validation and representation rules; performs no external effects."""
from __future__ import annotations

from copy import deepcopy
import csv
import io
import json
import math
import re
from urllib.parse import parse_qsl, unquote, unquote_plus, urlsplit

S = {'type': 'string'}
B = {'type': 'boolean'}
I = {'type': 'integer'}
A = {'type': 'array'}
O = {'type': 'object'}
ANY = {}
STRINGS = {'type': 'array', 'items': S}
RECORDS = {'type': 'array', 'items': O}
ROWS = {'type': 'array', 'items': {'type': 'array', 'items': S}}
PAIRS = {'type': 'array', 'items': {'type': 'array', 'items': S, 'minItems': 2, 'maxItems': 2}}
BYTES = {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 255}}
JSON_SOURCE = 'https://docs.python.org/3/library/json.html'
POINTER_SOURCE = 'https://www.rfc-editor.org/rfc/rfc6901'
CSV_SOURCE = 'https://docs.python.org/3/library/csv.html'
URL_SOURCE = 'https://docs.python.org/3/library/urllib.parse.html'
BYTES_SOURCE = 'https://docs.python.org/3/library/stdtypes.html#binary-sequence-types-bytes-bytearray-memoryview'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_value(value, ancestors=None):
    """Accept only finite, acyclic JSON values with Unicode scalar strings."""
    ancestors = set() if ancestors is None else ancestors
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        require(math.isfinite(value), 'nonfinite_number')
        return
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeEncodeError as exc:
            raise ValueError('unpaired_unicode_surrogate') from exc
        return
    require(type(value) in (dict, list), 'json_value_required')
    require(id(value) not in ancestors, 'cyclic_value')
    ancestors.add(id(value))
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, 'string_object_key_required')
            json_value(key, ancestors)
            json_value(item, ancestors)
    else:
        for item in value:
            json_value(item, ancestors)
    ancestors.remove(id(value))


def validate(value, schema):
    kind = schema.get('type')
    expected = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if kind in expected:
        require(type(value) is expected[kind], kind + '_required')
    if kind == 'object' and 'properties' in schema:
        require(set(schema.get('required', ())) <= set(value), 'missing_fields')
        if schema.get('additionalProperties') is False:
            require(set(value) <= set(schema['properties']), 'unknown_fields')
        for key, item in value.items():
            if key in schema['properties']:
                validate(item, schema['properties'][key])
    if kind == 'array' and 'items' in schema:
        for item in value:
            validate(item, schema['items'])
    if 'minItems' in schema:
        require(len(value) >= schema['minItems'], 'too_few_items')
    if 'maxItems' in schema:
        require(len(value) <= schema['maxItems'], 'too_many_items')
    if 'minimum' in schema:
        require(value >= schema['minimum'], 'below_minimum')
    if 'maximum' in schema:
        require(value <= schema['maximum'], 'above_maximum')


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def spec(name, description, inputs, outputs, example_input, example_output, sources):
    return {'id': 'data.' + name, 'version': '1.0.0', 'description': description,
            'input_schema': object_schema(inputs), 'output_schema': object_schema(outputs),
            'effects': ['pure'], 'examples': [{'input': example_input, 'output': example_output}],
            'sources': list(sources)}


def check(payload, spec):
    json_value(payload)
    validate(payload, spec['input_schema'])
    return payload


def finish(result, spec):
    json_value(result)
    validate(result, spec['output_schema'])
    return deepcopy(result)


def pairs_object(pairs):
    result = {}
    for pair in pairs:
        require(type(pair) in (list, tuple) and len(pair) == 2 and type(pair[0]) is str,
                'string_key_value_pair_required')
        key, value = pair
        require(key not in result, 'duplicate_object_key')
        result[key] = deepcopy(value)
    return result


def reject_constant(value):
    raise ValueError('nonfinite_number')


def parse_json(text):
    value = json.loads(text, object_pairs_hook=pairs_object, parse_constant=reject_constant)
    json_value(value)
    return value


def compact(value, *, sort_keys=False):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'),
                      sort_keys=sort_keys)


def identity(value):
    """Type-sensitive representation; 1, 1.0 and true remain distinct."""
    return compact(value, sort_keys=True)


def pointer_escape(token):
    return token.replace('~', '~0').replace('/', '~1')


def pointer_unescape(token):
    require('/' not in token, 'unescaped_pointer_slash')
    require(re.search(r'~(?![01])', token) is None, 'invalid_pointer_escape')
    return token.replace('~1', '/').replace('~0', '~')


def pointer_tokens(pointer):
    require(pointer == '' or pointer.startswith('/'), 'pointer_must_start_with_slash')
    return [] if pointer == '' else [pointer_unescape(token) for token in pointer[1:].split('/')]


def pointer_step(value, token):
    if type(value) is dict:
        require(token in value, 'pointer_member_missing')
        return token
    if type(value) is list:
        require(re.fullmatch(r'0|[1-9][0-9]*', token) is not None, 'invalid_pointer_array_index')
        index = int(token)
        require(index < len(value), 'pointer_index_out_of_range')
        return index
    raise ValueError('pointer_traverses_scalar')


def pointer_get(value, pointer):
    for token in pointer_tokens(pointer):
        value = value[pointer_step(value, token)]
    return deepcopy(value)


def pointer_set(value, pointer, replacement):
    value = deepcopy(value)
    tokens = pointer_tokens(pointer)
    if not tokens:
        return deepcopy(replacement)
    parent = value
    for token in tokens[:-1]:
        parent = parent[pointer_step(parent, token)]
    parent[pointer_step(parent, tokens[-1])] = deepcopy(replacement)
    return value


def keys_present(value, keys):
    require(len(keys) == len(set(keys)), 'duplicate_requested_key')
    require(all(key in value for key in keys), 'object_key_missing')


def merge_objects(left, right):
    result = deepcopy(left)
    for key, value in right.items():
        result[key] = (merge_objects(result[key], value)
                       if key in result and type(result[key]) is dict and type(value) is dict
                       else deepcopy(value))
    return result


def flatten(value, pointer=''):
    """Map leaves and empty containers to unambiguous RFC 6901 pointers."""
    if type(value) not in (dict, list) or not value:
        return {pointer: deepcopy(value)}
    result = {}
    items = value.items() if type(value) is dict else enumerate(value)
    for key, item in items:
        result.update(flatten(item, pointer + '/' + pointer_escape(str(key))))
    return result


def record_keys(records, keys):
    for row in records:
        keys_present(row, keys)


def csv_rows(text):
    require('\x00' not in text, 'csv_nul_character')
    bom_removed = text.startswith('\ufeff')
    text = text[1:] if bom_removed else text
    # csv.reader(strict=True) still accepts quote characters inside unquoted
    # fields, so enforce quote placement explicitly before stdlib parsing.
    state, index = 'start', 0
    while index < len(text):
        char = text[index]
        if state == 'quoted':
            if char == '"':
                if index + 1 < len(text) and text[index + 1] == '"':
                    index += 1
                else:
                    state = 'closed'
        elif state == 'closed':
            require(char in ',\r\n', 'csv_characters_after_quote')
            state = 'start'
        elif char == '"':
            require(state == 'start', 'csv_quote_in_unquoted_field')
            state = 'quoted'
        elif char in ',\r\n':
            state = 'start'
        else:
            state = 'unquoted'
        index += 1
    require(state != 'quoted', 'csv_unterminated_quote')
    try:
        rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
    except csv.Error as exc:
        raise ValueError('invalid_csv') from exc
    if rows:
        require(all(len(row) == len(rows[0]) for row in rows), 'csv_row_width_mismatch')
    return rows, bom_removed


def csv_text(rows):
    if rows:
        require(all(len(row) == len(rows[0]) for row in rows), 'csv_row_width_mismatch')
    require(all('\x00' not in cell for row in rows for cell in row), 'csv_nul_character')
    stream = io.StringIO(newline='')
    # A genuine BOM character in the first cell must remain cell data, rather
    # than being mistaken for the optional leading document marker on parsing.
    quoting = csv.QUOTE_ALL if rows and rows[0] and rows[0][0].startswith('\ufeff') else csv.QUOTE_MINIMAL
    csv.writer(stream, lineterminator='\r\n', quoting=quoting).writerows(rows)
    return stream.getvalue()


def validate_percent(text):
    require(re.search(r'%(?![0-9A-Fa-f]{2})', text) is None, 'malformed_percent_escape')


def split_url(text):
    require(not any(ord(char) <= 32 or ord(char) == 127 for char in text), 'url_space_or_control')
    require('\\' not in text, 'url_backslash')
    validate_percent(text)
    try:
        parts = urlsplit(text)
        unused_port = parts.port
        unused_host = parts.hostname
    except ValueError as exc:
        raise ValueError('invalid_url_authority') from exc
    require(not parts.netloc.endswith(':'), 'empty_url_port')
    return parts


def normalize_http(text):
    parts = split_url(text)
    require(parts.scheme in ('http', 'https') and bool(parts.hostname), 'absolute_http_url_required')
    require(parts.username is None and parts.password is None, 'url_userinfo_refused')
    host = parts.hostname.lower()
    require(not any(char in host for char in '/?#@'), 'invalid_http_hostname')
    host = '[' + host + ']' if ':' in host else host
    port = parts.port
    authority = host + (':' + str(port) if port is not None
                       and (parts.scheme, port) not in {('http', 80), ('https', 443)} else '')
    before_fragment, fragment_mark, unused_fragment = text.partition('#')
    query_mark = '?' if '?' in before_fragment else ''
    return (parts.scheme.lower() + '://' + authority + parts.path
            + query_mark + parts.query + fragment_mark + parts.fragment)


def percent_decode(text, *, plus=False):
    validate_percent(text)
    try:
        return (unquote_plus if plus else unquote)(text, encoding='utf-8', errors='strict')
    except UnicodeError as exc:
        raise ValueError('percent_encoding_not_utf8') from exc


def query_pairs(query):
    validate_percent(query)
    try:
        return [list(pair) for pair in parse_qsl(query, keep_blank_values=True,
                encoding='utf-8', errors='strict', separator='&')]
    except UnicodeError as exc:
        raise ValueError('query_encoding_not_utf8') from exc


def string_pairs(pairs):
    require(all(type(pair) is list and len(pair) == 2 and
                all(type(value) is str for value in pair) for pair in pairs), 'string_pair_required')
    return [tuple(pair) for pair in pairs]


def with_query(url, query):
    before_fragment, mark, fragment = url.partition('#')
    base = before_fragment.partition('?')[0]
    return base + ('?' + query if query else '') + (mark + fragment if mark else '')
