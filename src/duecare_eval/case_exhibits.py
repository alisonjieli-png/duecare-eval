"""Verify full public case exhibits against the frozen prompt and review records."""
import json
from hashlib import sha256
from pathlib import Path


def verify(root):
    root = Path(root)
    read = lambda name: json.loads((root / 'results' / name).read_text())
    packet = read('complete_case_exhibits_2026-10-01.json')
    cases = {r['case_id']: r for r in read('longform_cases_2026-09-30.json')}
    reviews = {r['request_id']: r for r in read('longform_text_reviews_2026-09-30.json')['rows']}
    seen = set()
    for row in packet['records']:
        if row['request_id'] in seen:
            raise ValueError('Duplicate case exhibit')
        seen.add(row['request_id'])
        if sha256(row['response'].encode()).hexdigest() != row['response_sha256']:
            raise ValueError('Changed response text')
        prior = reviews[row['request_id']]
        for key in ('case_id', 'arm', 'model_id', 'prompt_sha256', 'request_sha256', 'response_sha256'):
            if row[key] != prior[key]:
                raise ValueError('Exhibit differs from frozen review: ' + key)
        messages = row['messages']
        digest = sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if digest != row['messages_sha256']:
            raise ValueError('Changed executed message bytes')
        if messages[-1] != {'role': 'user', 'content': cases[row['case_id']]['prompt']}:
            raise ValueError('Exhibit lost the exact source prompt')
        roles = [message['role'] for message in messages]
        if roles != (['user'] if row['arm'] == 'bare' else ['system', 'user']):
            raise ValueError('Incomplete executed message sequence')
        if row['arm'] == 'grounded':
            context = json.loads(messages[0]['content'])
            if len(context['dated_evidence']) != 6 or len(context['evaluation_rules']) != 7:
                raise ValueError('Incomplete historical evidence briefing')
    expected = {('WRITEUP-16674-CASE-5', 'bare'), ('WRITEUP-16674-CASE-5', 'grounded'),
                ('WRITEUP-16674-CASE-2', 'grounded')}
    if len(seen) != 3 or {(r['case_id'], r['arm']) for r in packet['records']} != expected:
        raise ValueError('Expected worker-help pair and grounded assignment reply')
    return {'complete_responses': len(seen), 'new_inference_calls': 0, 'historical_grades_unchanged': True}
