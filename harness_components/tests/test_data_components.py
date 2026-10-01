"""Independent fixtures for the pure data component collection."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import socket

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / 'components/data').glob('[a-z]*.py'))
MODULES = {path.stem: importlib.import_module('harness_components.components.data.' + path.stem)
           for path in FILES}


def run(name, **payload):
    return MODULES[name].run(payload)


@pytest.mark.parametrize('name', list(MODULES))
def test_declared_examples_are_pure_strict_and_serializable(name, monkeypatch):
    module = MODULES[name]
    assert module.SPEC['id'] == 'data.' + name
    assert module.SPEC['effects'] == ['pure']
    assert module.SPEC['sources']
    def refuse(*args, **kwargs):
        raise AssertionError('pure component attempted an external effect')
    monkeypatch.setattr(socket, 'socket', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)
    monkeypatch.setattr('builtins.open', refuse)
    for example in module.SPEC['examples']:
        payload = deepcopy(example['input'])
        assert module.run(payload) == example['output']
        assert payload == example['input']
        json.dumps(module.run(payload), allow_nan=False)
        with pytest.raises(ValueError, match='unknown_fields'):
            module.run({**payload, 'unexpected': None})
        with pytest.raises(ValueError):
            module.run([])
        missing = dict(payload)
        missing.pop(next(iter(missing)))
        with pytest.raises(ValueError, match='missing_fields'):
            module.run(missing)


@pytest.mark.parametrize('text', [
    '{"a":1,"a":2}', '{"nested":{"x":1,"x":2}}', 'NaN', 'Infinity', '-Infinity',
    '1e400', '{"x":"raw\nnewline"}', 'true false', '\ufeff{}', '"\\ud800"',
])
def test_strict_json_rejects_ambiguous_or_nonportable_values(text):
    with pytest.raises(ValueError):
        run('json_parse', text=text)


def test_json_unicode_scalar_and_type_semantics():
    assert run('json_parse', text='"\\ud83d\\ude00"') == {'value': '😀'}
    assert run('json_equal', left={'b': 2, 'a': 1}, right={'a': 1, 'b': 2}) == {'equal': True}
    assert run('json_equal', left=1, right=1.0) == {'equal': False}
    assert run('json_compact', value='é') == {'text': '"é"'}
    with pytest.raises(ValueError, match='string_object_key'):
        run('json_compact', value={1: 'x'})
    with pytest.raises(ValueError, match='json_value_required'):
        run('json_compact', value=(1, 2))
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match='cyclic'):
        run('json_compact', value=cyclic)


def test_json_lines_boundaries_and_digest_order():
    assert run('jsonl_parse', text='') == {'values': []}
    assert run('jsonl_parse', text='1\r\nfalse\r\n') == {'values': [1, False]}
    for text in ['\n', '1\n\n', '1\n \n2']:
        with pytest.raises(ValueError, match='blank_jsonl_line'):
            run('jsonl_parse', text=text)
    assert run('json_digest', value={'a': 1, 'b': 2}) == run('json_digest', value={'b': 2, 'a': 1})


@pytest.mark.parametrize('pointer', ['a', '#/a', '/a~', '/a~2', '/arr/01', '/arr/-', '/arr/-1', '/arr/2'])
def test_pointer_syntax_and_existing_index_boundaries(pointer):
    with pytest.raises(ValueError):
        run('pointer_get', value={'arr': [10, 20]}, pointer=pointer)


def test_pointer_empty_keys_escapes_and_no_unicode_normalization():
    value = {'': 0, '~1': 1, 'a/b': 2, 'é': 3, 'e\u0301': 4}
    assert run('pointer_get', value=value, pointer='/') == {'value': 0}
    assert run('pointer_get', value=value, pointer='/~01') == {'value': 1}
    assert run('pointer_get', value=value, pointer='/a~1b') == {'value': 2}
    assert run('pointer_get', value=value, pointer='/e\u0301') == {'value': 4}
    assert run('pointer_set', value=value, pointer='', replacement=None) == {'value': None}
    with pytest.raises(ValueError, match='missing'):
        run('pointer_set', value=value, pointer='/new', replacement=5)
    with pytest.raises(ValueError, match='unescaped_pointer_slash'):
        run('pointer_unescape', token='a/b')


def test_object_collision_rules_copying_and_empty_containers():
    with pytest.raises(ValueError, match='rename_collision'):
        run('object_rename', object={'a': 1, 'b': 2}, mapping={'a': 'b'})
    assert run('object_rename', object={'a': 1, 'b': 2}, mapping={'a': 'b', 'b': 'a'}) == {'object': {'b': 1, 'a': 2}}
    with pytest.raises(ValueError, match='duplicate_object_key'):
        run('object_from_pairs', pairs=[['a', 1], ['a', 2]])
    with pytest.raises(ValueError, match='duplicate_requested_key'):
        run('object_project', object={'a': 1}, keys=['a', 'a'])
    assert run('object_flatten', value={'x': [], 'y': {}, 'a.b': [None]}) == {'leaves': {'/x': [], '/y': {}, '/a.b/0': None}}
    source = {'a': {'x': [1]}}
    result = run('object_project', object=source, keys=['a'])
    result['object']['a']['x'].append(2)
    assert source == {'a': {'x': [1]}}


def test_record_grouping_dedup_and_filter_do_not_confuse_boolean_and_integer():
    records = [{'k': 1}, {'k': True}, {'k': 1}, {'k': None}]
    grouped = run('records_group', records=records, key='k')['groups']
    assert [len(group['records']) for group in grouped] == [2, 1, 1]
    assert run('records_deduplicate', records=records, keys=['k']) == {
        'records': [{'k': 1}, {'k': True}, {'k': None}], 'removed': 1}
    assert run('records_filter', records=records, key='k', value=True) == {'records': [{'k': True}]}
    with pytest.raises(ValueError, match='duplicate_index_key'):
        run('records_index', records=[{'k': 'x'}, {'k': 'x'}], key='k')
    with pytest.raises(ValueError, match='string_index_key'):
        run('records_index', records=[{'k': 1}], key='k')
    with pytest.raises(ValueError, match='columns_mismatch'):
        run('records_transpose', records=[{'a': 1}, {'b': 2}])
    with pytest.raises(ValueError, match='boolean_required'):
        run('records_sort', records=[{'k': 'a'}], key='k', reverse=1)


@pytest.mark.parametrize('text', ['a,b\n1\n', 'a,b\n1,2,3\n', 'a,"unterminated', 'a,b"c', '"a"x,b', 'a,\x00'])
def test_csv_malformed_quoting_widths_and_nul_are_refused(text):
    with pytest.raises(ValueError):
        run('csv_parse', text=text)


def test_csv_embedded_newlines_quotes_bom_and_duplicate_headers():
    text = '\ufeffa,b\r\n"one\ntwo","a""b"\r\n'
    assert run('csv_records', text=text) == {
        'header': ['a', 'b'], 'records': [{'a': 'one\ntwo', 'b': 'a"b'}], 'bom_removed': True}
    for text in ['a,a\n1,2\n', 'a,\n1,2\n', '']:
        with pytest.raises(ValueError):
            run('csv_records', text=text)
    with pytest.raises(ValueError, match='string_required'):
        run('csv_format', rows=[['a'], [None]])
    rows = [['=1', '  +2', '-3', '@a', '\ttext', '\rtext', '\ntext', '＝1', 'safe']]
    flags = run('csv_formula_flags', rows=rows)['flags']
    assert [flag['column'] for flag in flags] == list(range(8))
    assert rows[0][0] == '=1'
    assert run('csv_format', rows=[['=1']]) == {'text': '=1\r\n'}
    literal_bom = run('csv_format', rows=[['\ufeffliteral', 'value']])['text']
    assert literal_bom == '"\ufeffliteral","value"\r\n'
    assert run('csv_parse', text=literal_bom) == {'rows': [['\ufeffliteral', 'value']], 'bom_removed': False}


@pytest.mark.parametrize('url', [
    'https://example.org/%Q0', 'https://example.org/%', ' https://example.org',
    'https://example.org/\npath', 'https://example.org:99999', 'https://example.org:',
    'https://example.org:True', 'https://example.org\\x', 'https://[not-ipv6]/',
])
def test_url_structural_errors_are_refused(url):
    with pytest.raises(ValueError):
        run('url_split', url=url)


def test_http_normalization_retains_path_query_order_and_empty_markers():
    assert run('url_normalize_http', url='HTTPS://EXAMPLE.org:443/Case/%2f?a=1&a=2#F') == {
        'url': 'https://example.org/Case/%2f?a=1&a=2#F'}
    assert run('url_normalize_http', url='HTTP://[2001:DB8::1]:80/Case?#') == {
        'url': 'http://[2001:db8::1]/Case?#'}
    assert run('url_split', url='/relative/path?x=1')['hostname'] is None
    with pytest.raises(ValueError, match='absolute_http'):
        run('url_normalize_http', url='/relative/path')
    with pytest.raises(ValueError, match='userinfo'):
        run('url_normalize_http', url='https://user:pass@example.org/')
    assert run('url_userinfo', url='https://@example.org') == {'has_userinfo': True, 'has_password_separator': False}


def test_percent_and_form_query_semantics():
    assert run('percent_decode', text='a+b%20c') == {'text': 'a+b c'}
    assert run('query_parse', query='a+b=x%2By&k&k=&x=1&x=2') == {
        'pairs': [['a b', 'x+y'], ['k', ''], ['k', ''], ['x', '1'], ['x', '2']]}
    for value in ['%FF', '%C3%28', '%ZZ', '%1']:
        with pytest.raises(ValueError):
            run('percent_decode', text=value)
        with pytest.raises(ValueError):
            run('query_parse', query='q=' + value)
    with pytest.raises(ValueError, match='too_few_items'):
        run('query_encode', pairs=[['one']])
    assert run('url_query_remove', url='https://e.org/?a%20b=1&a+b=2&x=%2f#F', keys=['a b']) == {'url': 'https://e.org/?x=%2f#F'}
    assert run('url_query_remove', url='https://e.org/?#', keys=['missing']) == {'url': 'https://e.org/?#'}
    assert run('url_query_append', url='https://e.org/?#', pairs=[]) == {'url': 'https://e.org/?#'}


@pytest.mark.parametrize('text', ['YQ=', 'YR==', 'YQ===', 'Y Q==', 'YQ==\n', '!!!!', 'é'])
def test_base64_refuses_noncanonical_encodings(text):
    with pytest.raises(ValueError):
        run('base64_decode', text=text)


def test_bytes_are_exact_unsigned_octets_and_decoding_is_strict():
    for value in [[True], [-1], [256], [1.0]]:
        with pytest.raises(ValueError):
            run('base64_encode', bytes=value)
    assert run('base64_decode', text='') == {'bytes': []}
    assert run('utf8_decode', bytes=[239, 187, 191, 65]) == {'text': '\ufeffA'}
    for value in [[255], [192, 175], [237, 160, 128]]:
        with pytest.raises(ValueError):
            run('utf8_decode', bytes=value)
    for value in ['f', '0x12', '0f ff', 'gg']:
        with pytest.raises(ValueError):
            run('hex_decode', text=value)
    assert run('sha256_utf8', text='é') != run('sha256_utf8', text='e\u0301')
    assert run('bytes_equal', left=[0], right=[0, 0]) == {'equal': False}
