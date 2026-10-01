"""Reproduce two authored protection-harness examples entirely offline."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from duecare_eval import protection_harness as H

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT/'results/protection_harness_checks_v2_1.json'


def reproduce():
    examples = ROOT/'examples/protection_harness'
    observations = []
    for name in ('ordinary', 'concern'):
        input_path = examples/(name+'_input.json')
        response_path = examples/(name+'_authored_response.json')
        case = json.loads(input_path.read_text())
        candidate = json.loads(response_path.read_text())
        prepared = H.prepare(case)
        bypass = H.prepare(case, mode='bypass')
        same_full_case = prepared['generation_request']['messages'][-1] == bypass['generation_request']['messages'][0]
        result = H.validate_response(prepared, candidate)
        if not same_full_case or not result['contract_valid']:
            raise ValueError('authored_example_check_failed:'+name)
        missing_actions = deepcopy(candidate)
        missing_actions['protective_actions'] = []
        no_action_result = H.validate_response(prepared, missing_actions)
        unsupported_source = deepcopy(candidate)
        unsupported_source['legal_position']['source_ids'].append('UNAPPROVED_EXAMPLE_SOURCE')
        unsupported_source['approved_source_ids_used'].append('UNAPPROVED_EXAMPLE_SOURCE')
        source_result = H.validate_response(prepared, unsupported_source)
        # This supplied flag is a validation fixture, rather than an assessment
        # that the authored protective sentence actually recommends retention.
        flags = [{'action_id': 'A1', 'flag': 'retain_identity_documents', 'value': True, 'declared_by': 'reviewer'}]
        flag_result = H.validate_response(prepared, candidate, flags)
        observations.append({
            'case_id': case['case_id'], 'fixture': name, 'response_origin': 'authored_software_demonstration',
            'input_file_sha256': H.sha(input_path.read_bytes()), 'response_file_sha256': H.sha(response_path.read_bytes()),
            'full_case_sha256': case['full_case_sha256'], 'context_sha256': prepared['context_sha256'],
            'harness_generation_request_sha256': prepared['generation_request_sha256'],
            'bypass_generation_request_sha256': bypass['generation_request_sha256'],
            'same_full_case': same_full_case, 'selected_sources': [
                {'id': item['id'], 'source_sha256': item['source_sha256']} for item in prepared['context']['selected_sources']],
            'arithmetic': prepared['context']['arithmetic'], 'validation': result,
            'negative_contract_fixtures': {
                'missing_practical_action_rejected': 'practical_action_missing' in no_action_result['errors'],
                'unapproved_source_rejected': 'unapproved_source_ids_used' in source_result['errors'],
                'declared_flag_fixture_rejected': 'declared_coercive_collection_action' in flag_result['errors']},
        })
    if not all(all(row['negative_contract_fixtures'].values()) for row in observations):
        raise ValueError('negative_contract_fixture_failed')
    return {
        'schema': H.VERSION, 'source_module_sha256': H.sha(Path(H.__file__).read_bytes()),
        'evidence_bundles': [{'file': str(path.relative_to(ROOT)), 'sha256': digest} for path, digest in H.DEFAULT_BUNDLES],
        'coverage': {'authored_cases': 2, 'generation_specs_prepared': 4, 'authored_valid_response_fixtures': 2,
                     'negative_contract_fixtures': 6, 'model_generations': 0, 'independently_validated_model_answers': 0},
        'observations': observations,
        'interpretation': 'Offline software demonstrations with authored inputs and responses. These checks establish reproducibility and contract behavior; model performance, substantive legal accuracy and independently validated safety require separate evidence.',
        'executed_components': ['pinned_bundle_ingestion', 'declared_topic_selection', 'explicit_fact_slots',
                                'supplied_operand_arithmetic', 'request_preparation', 'authored_response_validation', 'exact_full_case_bypass'],
        'planned_or_separately_assessed': ['hosted_generation', 'complete_answer_semantic_review', 'independent_legal_domain_worker_review'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='Compare with the distributed receipt (default).')
    group.add_argument('--write', action='store_true', help='Write a freshly reproduced receipt.')
    args = parser.parse_args()
    findings = reproduce()
    if args.write:
        with RESULT.open('w', encoding='utf-8') as stream:
            json.dump(findings, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    elif findings != json.loads(RESULT.read_text()):
        raise SystemExit('Protection-harness receipt differs from offline reproduction.')
    print('Protection harness: 2 authored cases, 4 prepared requests, 2 valid authored responses and 6 rejection checks reproduced. Model calls: 0.')


if __name__ == '__main__':
    main()
