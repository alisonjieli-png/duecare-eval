import hashlib
import json
from pathlib import Path
from duecare_eval.contracts import sha

ROOT=Path(__file__).resolve().parents[1]


def read(name):
    return [json.loads(x) for x in (ROOT/name).read_text().splitlines() if x.strip()]


def test_published_source_cases_preserve_exact_digest():
    for r in read('examples/reviewed_source_cases.jsonl'):
        assert hashlib.sha256(r['prompt'].encode()).hexdigest()==r['prompt_utf8_sha256']==r['case_id']


def test_observed_payloads_and_responses_match_without_source_labels():
    cases={r['case_id']:r for r in read('examples/reviewed_source_cases.jsonl')}
    inputs={r['request_id']:r for r in read('examples/observed_source_inputs.jsonl')}
    observed=read('results/observed_source_examples.jsonl')
    assert len(observed)==len(inputs)==27
    for r in observed:
        packet=inputs[r['request_id']]
        assert sha(packet['payload'])==packet['request_sha256']==r['request_sha256']
        assert packet['payload']['state']['state']['original_case_text']==cases[r['case_id']]['prompt']
        assert r['observation_kind']=='actual_hosted_API_response' and r['gold_label'] is None
        assert 'source_grade' not in json.dumps(packet['payload'])


def test_source_catalogs_are_distinct_probes_not_case_multipliers():
    general=json.loads((ROOT/'examples/source_question_catalog.json').read_text())
    referrals=json.loads((ROOT/'examples/referral_question_catalog.json').read_text())
    assert len(general)==105 and len(referrals)==40
    assert len({p['probe_id'] for p in general+referrals})==145
