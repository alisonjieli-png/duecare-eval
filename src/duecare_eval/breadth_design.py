"""Offline integrity and matching checks for the dated breadth/depth design."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFINITION_SHA256 = 'ca38ac2d8c0b91df2181755bc73f0ac751d1659bdbd4eb8b4fccdb7b135cb3fb'
BANK_COUNTS = {'action_menu_requests.jsonl': 30, 'ilo_application_requests.jsonl': 40,
               'ilo_knowledge_requests.jsonl': 2, 'breadth_prose_requests.jsonl': 96,
               'breadth_canary_v2_requests.jsonl': 16, 'breadth_typed_canary_requests.jsonl': 16}
CASE_PREFIX = 'Authored staged research scenario. The facts below describe a constructed comparison, with no claim of a verified individual incident.\n\n'
FORBIDDEN_INPUT_KEYS = {'expected', 'reference_answers', 'gold', 'condition_label', 'criterion_scores', 'flag_evidence'}


def digest(value):
    raw = value if isinstance(value, bytes) else value.encode('utf-8') if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def no_reference_keys(value):
    if isinstance(value, dict):
        require(not (set(value) & FORBIDDEN_INPUT_KEYS), 'reference_key_in_model_input')
        for child in value.values():
            no_reference_keys(child)
    elif isinstance(value, list):
        for child in value:
            no_reference_keys(child)


def model_input(row):
    """Return only the declared model-facing fields, leaving references outside."""
    value = {'messages': deepcopy(row['messages'])} if 'messages' in row else {'state': deepcopy(row['state']), 'questions': deepcopy(row['questions'])}
    no_reference_keys(value)
    return value


def validate_identity(row):
    core = deepcopy(row)
    claimed = core.pop('instrument_sha256')
    request_id = core.pop('request_id')
    # The original seal includes state/questions digests and explicit order
    # arrays before hashing. Only these two final identity fields are removed.
    require(digest(core) == claimed, 'instrument_digest_mismatch')
    require(request_id == 'BD-'+claimed[:24], 'request_identity_mismatch')
    require(row['protocol'] == 'duecare-breadth-depth/1.0.0', 'instrument_protocol')
    require(digest(row['state']) == row['state_sha256'], 'state_digest_mismatch')
    require(digest(row['questions']) == row['questions_sha256'], 'question_digest_mismatch')
    require(row['question_order'] == list(row['questions']), 'question_order_mismatch')
    actions = row['questions'].get('priority_next_step', {}).get('criteria', {})
    require(row['action_order'] == list(actions), 'action_order_mismatch')
    if actions:
        require(row['state']['action_options'] == [{'id': key, 'description': value} for key, value in actions.items()], 'explicit_action_order_mismatch')
    if 'messages' in row:
        require(digest(row['messages']) == row['messages_sha256'], 'message_digest_mismatch')
    no_reference_keys(row['state'])
    model_input(row)
    require(bool(row['leakage_group_id']), 'sampling_group_required')


def visible_events(row, definitions):
    f = row['factors']
    timeline = next((item['timeline'] for item in definitions['authored_timelines'] if item['theme'] == f['theme'] and item['condition'] == f['condition']), None)
    require(timeline is not None, 'unknown_authored_timeline')
    require(f['stage'] in definitions['stages'] and f['context'] in definitions['contexts'], 'unknown_stage_or_context')
    index = definitions['stages'].index(f['stage'])
    events = timeline[index:index+1] if f['context'] == 'minimal' else timeline[:index+1]
    return timeline, events


def expected_prose_state(row, definitions, ilo_sources):
    f = row['factors']
    timeline, events = visible_events(row, definitions)
    require(f['question_type'] in definitions['question_templates'], 'unknown_question_form')
    case_text = CASE_PREFIX+'\n\n'.join(event['text'] for event in events)
    state = {'case_text': case_text, 'question': definitions['question_templates'][f['question_type']],
             'visible_event_stages': [event['stage'] for event in events]}
    if f['context'] == 'evidence_enriched':
        state['reference_sources'] = deepcopy(ilo_sources)
    require(row['transformation']['timeline_sha256'] == digest(timeline), 'timeline_digest_mismatch')
    require(row['transformation']['visible_facts_sha256'] == digest(events), 'visible_fact_digest_mismatch')
    expected_case = 'SCEN-'+digest({'protocol': row['protocol'], 'theme': f['theme'], 'condition': f['condition'], 'timeline': timeline})[:20]
    require(row['case_id'] == expected_case, 'authored_case_identity')
    return state, events


def validate_prose(row, definitions, ilo_sources):
    f = row['factors']
    require(f['harness'] in ('off','on'), 'unknown_scaffold_level')
    state, events = expected_prose_state(row, definitions, ilo_sources)
    require(row['state'] == state, 'visible_context_mismatch_or_future_fact')
    user = state['case_text']
    if f['context'] == 'evidence_enriched':
        user += '\n\nScoped reference statements:\n'+'\n'.join(f"{s['id']}: {s['summary']} Scope: {s['scope']} Source: {s['url']}" for s in ilo_sources)
    user += '\n\nQuestion:\n'+state['question']
    messages = ([{'role': 'system', 'content': definitions['scaffold_text']}] if f['harness'] == 'on' else [])+[{'role':'user','content':user}]
    require(row['messages'] == messages, 'prose_message_or_scaffold_mismatch')
    require(row['questions'] == {}, 'prose_uses_free_answer_mode')
    require(row['matched_set_id'] == 'PAIR-'+digest({key:f[key] for key in ('theme','stage','question_type')})[:20], 'matched_set_identity')
    require(row['condition_pair_id'] == 'CONTROL-'+digest({key:f[key] for key in ('theme','stage','question_type','context','harness')})[:20], 'condition_pair_identity')
    require(row['evidence_packet_sha256'] == (definitions['ilo_evidence_packet_sha256'] if f['context'] == 'evidence_enriched' else None), 'evidence_factor_mismatch')
    facts = {}
    for event in events:
        for key, value in event['explicit_facts'].items():
            if value is not None or key not in facts:
                facts[key] = value
    actual = row['expected']['visible_explicit_facts']
    require(set(actual) == set(facts) and all(actual[key]['value'] == value for key,value in facts.items()), 'visible_fact_reference_mismatch')
    require(row['leakage_group_id'] == 'WRITEUP-16674-RECRUITMENT-FAMILY' and row['split'] == 'evaluation_only_authored_family', 'authored_family_split_mismatch')


def validate_row(row, definitions, ilo_sources):
    validate_identity(row)
    source_hashes = definitions['source_prompt_sha256']
    source_id = row.get('source_case_id', row['case_id'])
    if row['source_type'] in ('exact_published_prompt', 'documented_full_notebook_variant'):
        require(source_id in source_hashes and row['source_prompt_sha256'] == source_hashes[source_id], 'original_source_hash')
        require(digest(row['state']['original_source_prompt']) == source_hashes[source_id], 'original_source_text_changed')
        require(row['expected'] == {}, 'original_case_reference_must_be_descriptive')
        require(row['matched_set_id'] == 'MATCH-'+digest({'case':source_id,'study':row['study']})[:20], 'original_matched_set_identity')
        order_factors = {key:value for key,value in row['factors'].items() if key != 'order'}
        require(row['order_pair_id'] == 'ORDER-'+digest({'case':source_id,'study':row['study'],'factors':order_factors})[:20], 'original_order_pair_identity')
        require((source_id.startswith('NOTEBOOK-')) == (row['source_type'] == 'documented_full_notebook_variant'), 'notebook_provenance_scope')
        baseline = definitions['baseline_questions']
        require(list(row['questions'])[:12] == list(baseline), 'baseline_question_identity')
        for key, question in baseline.items():
            require(row['questions'][key]['type'] == question['type'] and row['questions'][key]['instructions'] == question['instructions'], 'baseline_question_text_changed')
            if key != 'priority_next_step':
                require(row['questions'][key] == question, 'baseline_question_choices_changed')
        menu_kind = row['factors']['menu']
        menu = deepcopy(baseline['priority_next_step']['criteria'])
        if menu_kind == 'fallback_removed':
            del menu['check_crossborder_applicability']
        elif menu_kind == 'concrete_protective':
            menu = definitions['concrete_menu']
        else:
            require(menu_kind == 'original', 'unknown_menu')
        require(row['questions']['priority_next_step']['criteria'] == menu, 'menu_content_changed')
        require({'insufficient_information','several_steps_or_context_dependent'} <= set(menu), 'abstention_choices_missing')
        if row['study'] == 'ilo_case_application':
            require({k:v for k,v in row['questions'].items() if k not in baseline} == definitions['ilo_application_questions'], 'ilo_application_questions_changed')
            expected_sources = ilo_sources if row['factors']['evidence'] == 'supplied_ilo' else None
            require(row['state'].get('reference_sources') == expected_sources, 'ilo_evidence_factor_changed')
        else:
            require(row['study'] == 'action_menu_ablation' and len(row['questions']) == 12, 'source_study_kind')
    elif row['study'] == 'ilo_standard_knowledge':
        controls = definitions['knowledge_controls']
        require(len(row['questions']) == 8 and set(row['questions']) == {c['id'] for c in controls}, 'knowledge_question_set')
        require(Counter(v['value'] for v in row['expected'].values()) == {True:4,False:4}, 'knowledge_balance')
        require(all(type(v['value']) is bool for v in row['expected'].values()), 'knowledge_reference_boolean')
        for control in controls:
            key = control['id']
            require(row['questions'][key]['instructions'] == 'Assess whether this statement accurately describes the named international labour standard: '+control['statement'], 'knowledge_statement_changed')
            require(row['expected'][key] == {'value':control['expected'],'source_ids':[control['source_id']],'basis':'explicit_standard_statement'}, 'knowledge_reference_changed')
        require(row['state'].get('reference_sources') == (ilo_sources if row['factors']['evidence'] == 'supplied_ilo' else None), 'knowledge_evidence_factor')
    else:
        require(row['source_type'] == 'authored_stage_derivative', 'unknown_source_type')
        require(source_id == definitions['source_case_by_theme'][row['factors']['theme']] and row['source_prompt_sha256'] == source_hashes[source_id], 'derivative_source_identity')
        if row['study'] == 'breadth_context_harness_prose':
            validate_prose(row, definitions, ilo_sources)
        else:
            require(row['study'] == 'breadth_context_harness_typed_canary', 'unknown_study')
            expected_prose_state(row, definitions, ilo_sources)


def factorial_coordinates(definitions):
    axes = ('themes','conditions','stages','question_templates','contexts','harnesses')
    for values in itertools.product(*(list(definitions[key]) for key in axes)):
        yield dict(zip(('theme','condition','stage','question_type','context','harness'), values))


def validate_design(root=ROOT):
    root = Path(root)
    folder = root/'examples/breadth_depth_v1'
    definitions_raw = (folder/'design_definitions.json').read_bytes()
    require(digest(definitions_raw) == DEFINITION_SHA256, 'definition_fixture_digest')
    definitions = json.loads(definitions_raw)
    ilo_raw = (root/'results/protection_harness_ilo_sources_v1.json').read_bytes()
    require(digest(ilo_raw) == definitions['ilo_evidence_packet_sha256'], 'ilo_v1_source_fixture_digest')
    ilo_sources = json.loads(ilo_raw)['sources']
    manifest = json.loads((folder/'manifest.json').read_text())
    require(len(manifest['banks']) == 6 and {item['file'] for item in manifest['banks']} == set(BANK_COUNTS), 'bank_inventory')
    banks, unique = {}, {}
    for item in manifest['banks']:
        raw = (folder/item['file']).read_bytes()
        require(digest(raw) == item['sha256'], 'bank_file_digest:'+item['file'])
        require(raw.endswith(b'\n'), 'complete_line_bank_required')
        rows = [json.loads(line) for line in raw.splitlines() if line]
        require(len(rows) == item['rows'] == BANK_COUNTS[item['file']], 'bank_row_count')
        require(len({r['request_id'] for r in rows}) == len(rows), 'duplicate_request_within_bank')
        for row in rows:
            validate_row(row, definitions, ilo_sources)
            if row['request_id'] in unique:
                require(unique[row['request_id']] == row, 'conflicting_cross_bank_identity')
            unique[row['request_id']] = row
        banks[item['file']] = rows
    prose = banks['breadth_prose_requests.jsonl']
    original_ids = set(definitions['source_prompt_sha256'])
    action_coordinates = {(r['case_id'],r['factors']['menu'],r['factors']['order']) for r in banks['action_menu_requests.jsonl']}
    require(action_coordinates == set(itertools.product(original_ids, ('original','fallback_removed','concrete_protective'), ('forward','reverse'))), 'action_factorial_coverage')
    application_coordinates = {(r['case_id'],r['factors']['evidence'],r['factors']['framing'],r['factors']['order']) for r in banks['ilo_application_requests.jsonl']}
    require(application_coordinates == set(itertools.product(original_ids, ('absent','supplied_ilo'), ('domestic_approval_focus','labour_standard_focus'), ('forward','reverse'))), 'ilo_factorial_coverage')
    require({r['factors']['evidence'] for r in banks['ilo_knowledge_requests.jsonl']} == {'absent','supplied_ilo'}, 'knowledge_evidence_coverage')
    order_pairs = defaultdict(list)
    framing_pairs = defaultdict(list)
    for row in banks['action_menu_requests.jsonl']+banks['ilo_application_requests.jsonl']:
        order_pairs[row['order_pair_id']].append(row)
        if row['study'] == 'ilo_case_application':
            framing_pairs[(row['case_id'],row['factors']['evidence'],row['factors']['order'])].append(row)
    for pair in order_pairs.values():
        require(len(pair) == 2 and pair[0]['action_order'] == list(reversed(pair[1]['action_order'])), 'submitted_reverse_order_pair')
    for pair in framing_pairs.values():
        states = [deepcopy(row['state']) for row in pair]
        for state in states:
            state.pop('assessment_focus')
        require(len(states) == 2 and states[0] == states[1], 'framing_changes_more_than_lens')
    factor_keys = ('theme','stage','question_type','condition','context','harness')
    expected_coordinates = {tuple(block)+(condition,context,harness) for block in definitions['pilot_blocks'] for condition,context,harness in itertools.product(definitions['conditions'],definitions['contexts'],definitions['harnesses'])}
    require({tuple(row['factors'][key] for key in factor_keys) for row in prose} == expected_coordinates, 'prose_pilot_factor_coverage')
    by_id = {r['request_id']:r for r in prose}
    canary = banks['breadth_canary_v2_requests.jsonl']
    require(all(by_id.get(r['request_id']) == r for r in canary), 'canary_must_be_exact_subset')
    require(len(unique) == 184 and sum(len(rows) for rows in banks.values()) == 200, 'stored_unique_counts')
    counts = Counter(r['factors']['question_type'] for r in prose)
    require(counts == dict.fromkeys(definitions['question_templates'], 12), 'eight_question_forms_balance')
    groups = defaultdict(dict)
    context_groups = defaultdict(dict)
    for row in prose:
        f = row['factors']
        groups[tuple(f[k] for k in ('theme','condition','stage','question_type','context'))][f['harness']] = row
        if f['context'] in ('minimal','whole_case'):
            context_groups[tuple(f[k] for k in ('theme','condition','stage','question_type','harness'))][f['context']] = row
    require(len(groups) == 48, 'scaffold_pair_count')
    for pair in groups.values():
        require(set(pair) == {'off','on'}, 'scaffold_pair_coverage')
        require(pair['off']['messages'] == pair['on']['messages'][1:], 'scaffold_user_bytes_differ')
    same_context = 0
    for pair in context_groups.values():
        require(set(pair) == {'minimal','whole_case'}, 'context_pair_coverage')
        equal = pair['minimal']['state']['case_text'] == pair['whole_case']['state']['case_text']
        require(equal == (pair['minimal']['factors']['stage'] == 'before_commitment'), 'context_history_semantics')
        same_context += equal
    require(len(context_groups) == 32 and same_context == 12, 'context_pair_counts')
    canary_ids = {r['request_id'] for r in canary}
    expected_canary_coordinates = {tuple(block)+(condition,context,harness) for block in definitions['canary_blocks'] for condition,context,harness in itertools.product(definitions['conditions'],('minimal','whole_case'),definitions['harnesses'])}
    require({tuple(row['factors'][key] for key in factor_keys) for row in canary} == expected_canary_coordinates, 'realized_canary_coordinates')
    for row in banks['breadth_typed_canary_requests.jsonl']:
        require(row['paired_prose_request_id'] in canary_ids, 'typed_prose_pair_identity')
        counterpart = by_id[row['paired_prose_request_id']]
        require({key:row['factors'][key] for key in counterpart['factors']} == counterpart['factors'], 'typed_prose_factor_mismatch')
        for key in ('case_id','source_case_id','source_prompt_sha256','transformation','leakage_group_id','split','matched_set_id','condition_pair_id'):
            require(row[key] == counterpart[key], 'typed_prose_case_scope')
        for key in ('case_text','question','visible_event_stages'):
            require(row['state'][key] == counterpart['state'][key], 'typed_prose_visible_context')
        require(row['state'].get('duecare_text_scaffold') == (definitions['scaffold_text'] if row['factors']['harness'] == 'on' else None), 'typed_scaffold_factor')
        expected_state = {**counterpart['state'], 'material_type':'Authored staged research comparison; the available case text supplies the facts for the baseline questions.', 'action_options':row['state']['action_options']}
        if row['factors']['harness'] == 'on':
            expected_state['duecare_text_scaffold'] = definitions['scaffold_text']
        require(row['state'] == expected_state, 'typed_extra_context_or_future_fact')
        baseline = definitions['baseline_questions']
        require(list(row['questions']) == list(baseline), 'typed_twelve_question_set')
        for key in baseline:
            require(row['questions'][key]['instructions'] == baseline[key]['instructions'], 'typed_baseline_text')
            if key != 'priority_next_step':
                require(row['questions'][key] == baseline[key], 'typed_baseline_schema')
        expected_menu = {**definitions['concrete_menu'], 'explain_records_no_escalation':'Explain the verified records and worker choices; ordinary help is sufficient without escalation.'}
        require(row['questions']['priority_next_step']['type'] == 'choice' and row['questions']['priority_next_step']['criteria'] == expected_menu, 'typed_concrete_menu')
        require('explain_records_no_escalation' in row['action_order'], 'benign_ordinary_help_option')
        require(set(row['expected']) == {'financial_pressure','deduction_control','exit_consequences','consent_sufficiency'}, 'typed_reference_scope')
        concern = row['factors']['condition'] == 'concern'
        require(all(type(item['value']) is bool for item in row['expected'].values()), 'typed_reference_boolean')
        require(all(row['expected'][key]['value'] == (not concern if key == 'consent_sufficiency' else concern) for key in row['expected']), 'typed_explicit_reference')
        require(row['action_reference']['unique_first_choice'] is False, 'multiple_supported_actions_preserved')
    coordinates = list(factorial_coordinates(definitions))
    require(len(coordinates) == manifest['full_factorial']['factorial_conditions_per_model'] == 1152, 'factorial_count')
    require(manifest['full_factorial']['status'] == 'design_manifest_prepared_no_dispatch', 'factorial_execution_scope')
    execution = json.loads((root/'results/ilo_menu_execution_2026-10-01.json').read_text())
    require({k:execution[k] for k in ('requested','attempted','usable','unattempted','http_status')} == {'requested':72,'attempted':1,'usable':0,'unattempted':71,'http_status':402}, 'dated_jev_execution_coverage')
    require(len(execution['requests']) == 1 and execution['requests'][0]['request_id'] in unique, 'jev_request_receipt_join')
    context = json.loads((root/'results/context_scaffold_observations_2026-10-01.json').read_text())
    require(context['requested'] == context['recorded'] == context['usable'] == len(context['observations']) == 32, 'dated_context_generation_coverage')
    observed = set()
    for row in context['observations']:
        key = (row['target_id'], row['instrument_request_id'])
        require(key not in observed and row['instrument_request_id'] in canary_ids, 'context_observation_identity')
        observed.add(key)
        source = by_id[row['instrument_request_id']]
        require(row['case_id'] == source['case_id'] and row['factors'] == source['factors'] and row['status'] == 'completed', 'context_observation_scope')
    observed_models = {key[0] for key in observed}
    require(len(observed_models) == 2 and all({request_id for model,request_id in observed if model == target} == canary_ids for target in observed_models), 'context_exact_two_model_coverage')
    return {'schema': 'duecare-public-breadth-validation/1.0.0', 'banks': manifest['banks'],
            'stored_rows': 200, 'unique_request_specs': 184, 'duplicate_subset_rows': 16,
            'overlap': 'The 16 prose canary rows are exact members of the 96-row prose bank. The 16 typed panels have distinct IDs and pair with those same case/context conditions.',
            'source_prompts_verified': len(definitions['source_prompt_sha256']), 'question_form_counts': dict(counts),
            'scaffold_pairs_same_user_bytes': 48, 'minimal_whole_pairs': 32,
            'first_stage_identical_context_pairs': 12, 'later_stage_distinct_context_pairs': 20,
            'typed_prose_pairs': 16, 'full_factorial_prepared_design_conditions': 1152,
            'jev_execution': {k:execution[k] for k in ('requested','attempted','usable','unattempted','http_status')},
            'context_generations': {'requested':32,'usable':32,'model_count':len({key[0] for key in observed})},
            'interpretation': 'Prepared request specifications, model-generation receipts and substantive answer assessments remain separate. The dated Jev attempt supplies no usable ILO/menu finding. Context judgments have their own full-text review.',
            'provider_calls_by_validator': 0}
