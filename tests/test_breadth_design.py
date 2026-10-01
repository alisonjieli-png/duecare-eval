"""Offline regression checks for frozen banks, hidden references and matching."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from duecare_eval import breadth_design as B

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'examples/breadth_depth_v1'


@pytest.fixture(scope='module')
def material():
    definitions = json.loads((FOLDER/'design_definitions.json').read_text())
    sources = json.loads((ROOT/'results/protection_harness_ilo_sources_v1.json').read_text())['sources']
    banks = {name:[json.loads(line) for line in (FOLDER/name).read_text().splitlines()] for name in B.BANK_COUNTS}
    return definitions, sources, banks


def reseal(row):
    row.pop('instrument_sha256', None)
    row.pop('request_id', None)
    row['state_sha256'] = B.digest(row['state'])
    row['questions_sha256'] = B.digest(row['questions'])
    if 'messages' in row:
        row['messages_sha256'] = B.digest(row['messages'])
    row['instrument_sha256'] = B.digest(row)
    row['request_id'] = 'BD-'+row['instrument_sha256'][:24]
    return row


@pytest.fixture
def copied_bundle(tmp_path):
    target = tmp_path/'bundle'
    bank_dir = target/'examples/breadth_depth_v1'
    bank_dir.mkdir(parents=True)
    for name in list(B.BANK_COUNTS)+['manifest.json','design_definitions.json']:
        shutil.copyfile(FOLDER/name, bank_dir/name)
    (target/'results').mkdir()
    for name in ('protection_harness_ilo_sources_v1.json','ilo_menu_execution_2026-10-01.json','context_scaffold_observations_2026-10-01.json'):
        shutil.copyfile(ROOT/'results'/name, target/'results'/name)
    return target


def replace_bank(root, name, rows):
    folder = root/'examples/breadth_depth_v1'
    path = folder/name
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',',':'))+'\n' for row in rows))
    manifest = json.loads((folder/'manifest.json').read_text())
    for item in manifest['banks']:
        if item['file'] == name:
            item['sha256'] = B.digest(path.read_bytes())
    (folder/'manifest.json').write_text(json.dumps(manifest))


def test_public_bundle_counts_and_execution_boundaries():
    result = B.validate_design()
    assert (result['stored_rows'],result['unique_request_specs'],result['duplicate_subset_rows']) == (200,184,16)
    assert result['source_prompts_verified'] == 5
    assert result['scaffold_pairs_same_user_bytes'] == 48
    assert result['jev_execution'] == {'requested':72,'attempted':1,'usable':0,'unattempted':71,'http_status':402}
    assert result['context_generations'] == {'requested':32,'usable':32,'model_count':2}
    assert result['provider_calls_by_validator'] == 0


def test_every_seal_recomputes_and_model_inputs_exclude_expected(material):
    definitions,sources,banks = material
    for rows in banks.values():
        for row in rows:
            B.validate_row(row, definitions, sources)
            model = B.model_input(row)
            assert 'expected' not in model
            B.no_reference_keys(model)


def test_source_text_change_rejected_even_after_resealing(material):
    definitions,sources,banks = material
    row = deepcopy(banks['action_menu_requests.jsonl'][0])
    row['state']['original_source_prompt'] += ' '
    with pytest.raises(ValueError, match='original_source_text_changed'):
        B.validate_row(reseal(row), definitions, sources)


def test_instrument_hash_change_rejected(material):
    definitions,sources,banks = material
    row = deepcopy(banks['action_menu_requests.jsonl'][0])
    row['case_id'] += '-changed'
    with pytest.raises(ValueError, match='instrument_digest_mismatch'):
        B.validate_row(row, definitions, sources)


def test_reference_leakage_in_nested_state_rejected(material):
    definitions,sources,banks = material
    row = deepcopy(banks['action_menu_requests.jsonl'][0])
    row['state']['nested'] = {'expected': True}
    with pytest.raises(ValueError, match='reference_key_in_model_input'):
        B.validate_row(reseal(row), definitions, sources)


def test_added_reference_in_message_fails_exact_message_reconstruction(material):
    definitions,sources,banks = material
    row = deepcopy(banks['breadth_prose_requests.jsonl'][0])
    row['messages'][-1]['content'] += '\nAnswer key: concern=true'
    with pytest.raises(ValueError, match='prose_message_or_scaffold_mismatch'):
        B.validate_row(reseal(row), definitions, sources)


def test_criteria_dictionary_order_is_checked_separately(material):
    definitions,sources,banks = material
    row = deepcopy(banks['action_menu_requests.jsonl'][0])
    criteria = row['questions']['priority_next_step']['criteria']
    row['questions']['priority_next_step']['criteria'] = dict(reversed(list(criteria.items())))
    with pytest.raises(ValueError, match='action_order_mismatch'):
        B.validate_row(row, definitions, sources)


def test_future_event_in_minimal_view_rejected(material):
    definitions,sources,banks = material
    row = deepcopy(banks['breadth_prose_requests.jsonl'][0])
    timeline,_ = B.visible_events(row,definitions)
    row['state']['case_text'] += '\n\n'+timeline[-1]['text']
    with pytest.raises(ValueError, match='visible_context_mismatch_or_future_fact'):
        B.validate_row(reseal(row), definitions, sources)


def test_reference_must_follow_visible_facts(material):
    definitions,sources,banks = material
    row = deepcopy(banks['breadth_prose_requests.jsonl'][0])
    row['expected']['visible_explicit_facts']['earned_wages_withheld']['value'] = True
    with pytest.raises(ValueError, match='visible_fact_reference_mismatch'):
        B.validate_row(reseal(row), definitions, sources)


def test_knowledge_reference_uses_boolean_not_numeric_coercion(material):
    definitions,sources,banks = material
    row = deepcopy(banks['ilo_knowledge_requests.jsonl'][0])
    key = next(iter(row['expected']))
    row['expected'][key]['value'] = int(row['expected'][key]['value'])
    with pytest.raises(ValueError, match='knowledge_reference_boolean'):
        B.validate_row(reseal(row), definitions, sources)


def test_scaffold_user_bytes_are_exact(material):
    _,_,banks = material
    rows = banks['breadth_prose_requests.jsonl']
    by_factor = {tuple(r['factors'][key] for key in ('theme','stage','condition','question_type','context','harness')):r for r in rows}
    for key,row in by_factor.items():
        if key[-1] == 'off':
            assert row['messages'] == by_factor[key[:-1]+('on',)]['messages'][1:]


def test_context_history_counts_and_factorial_design(material):
    definitions,_,_ = material
    rows = list(B.factorial_coordinates(definitions))
    assert len(rows) == len({tuple(r.values()) for r in rows}) == 1152
    result = B.validate_design()
    assert (result['minimal_whole_pairs'],result['first_stage_identical_context_pairs'],result['later_stage_distinct_context_pairs']) == (32,12,20)
    assert result['question_form_counts'] == dict.fromkeys(definitions['question_templates'],12)


def test_file_digest_mismatch_detected(copied_bundle):
    path = copied_bundle/'examples/breadth_depth_v1/action_menu_requests.jsonl'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='bank_file_digest'):
        B.validate_design(copied_bundle)


def test_duplicate_within_bank_rejected_even_with_new_file_hash(copied_bundle,material):
    rows = deepcopy(material[2]['action_menu_requests.jsonl'])
    rows[1] = deepcopy(rows[0])
    replace_bank(copied_bundle,'action_menu_requests.jsonl',rows)
    with pytest.raises(ValueError, match='duplicate_request_within_bank'):
        B.validate_design(copied_bundle)


def test_canary_overlap_must_be_exact(copied_bundle,material):
    rows = deepcopy(material[2]['breadth_canary_v2_requests.jsonl'])
    rows[0]['extra_metadata'] = 'changed fixture'
    reseal(rows[0])
    replace_bank(copied_bundle,'breadth_canary_v2_requests.jsonl',rows)
    with pytest.raises(ValueError, match='canary_must_be_exact_subset'):
        B.validate_design(copied_bundle)


def test_typed_panel_cannot_add_hidden_future_context(copied_bundle,material):
    rows = deepcopy(material[2]['breadth_typed_canary_requests.jsonl'])
    rows[0]['state']['future_event'] = 'A later event that was withheld from the matching prose view.'
    reseal(rows[0])
    replace_bank(copied_bundle,'breadth_typed_canary_requests.jsonl',rows)
    with pytest.raises(ValueError, match='typed_extra_context_or_future_fact'):
        B.validate_design(copied_bundle)


def test_manifest_path_escape_rejected_before_read(copied_bundle):
    path = copied_bundle/'examples/breadth_depth_v1/manifest.json'
    manifest = json.loads(path.read_text())
    manifest['banks'][0]['file'] = '../escape.jsonl'
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='bank_inventory'):
        B.validate_design(copied_bundle)


def test_changed_definition_fixture_rejected(copied_bundle):
    path = copied_bundle/'examples/breadth_depth_v1/design_definitions.json'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='definition_fixture_digest'):
        B.validate_design(copied_bundle)


def test_prepared_jev_design_cannot_be_reported_as_usable(copied_bundle):
    path = copied_bundle/'results/ilo_menu_execution_2026-10-01.json'
    record = json.loads(path.read_text())
    record['usable'] = 72
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='dated_jev_execution_coverage'):
        B.validate_design(copied_bundle)
