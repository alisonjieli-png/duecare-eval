import json
from pathlib import Path
import shutil
import pytest
from duecare_eval.case_exhibits import verify

ROOT = Path(__file__).resolve().parents[1]


def test_complete_case_exhibits_preserve_the_pair():
    assert verify(ROOT) == {'complete_responses': 3, 'new_inference_calls': 0, 'historical_grades_unchanged': True}


@pytest.mark.parametrize('mutation', ['response', 'prompt', 'context', 'duplicate'])
def test_changed_exhibit_fails(tmp_path, mutation):
    dest = tmp_path / 'results'
    dest.mkdir()
    for name in ('longform_cases_2026-09-30.json', 'longform_text_reviews_2026-09-30.json',
                 'complete_case_exhibits_2026-10-01.json'):
        shutil.copyfile(ROOT / 'results' / name, dest / name)
    path = dest / 'complete_case_exhibits_2026-10-01.json'
    value = json.loads(path.read_text())
    if mutation == 'response': value['records'][0]['response'] += ' edited'
    elif mutation == 'prompt': value['records'][0]['messages'][-1]['content'] += ' edited'
    elif mutation == 'context': value['records'][1]['messages'].pop(0)
    else: value['records'].append(value['records'][0])
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError): verify(tmp_path)
