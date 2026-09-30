import copy
import json
from pathlib import Path
import pytest
from duecare_eval.longform_report import reproduce, summarize, read, readable_text

ROOT=Path(__file__).resolve().parents[1]


def test_release_reproduces():
    assert reproduce(ROOT)==read(ROOT,'longform_readable_findings_2026-09-30.json')


def test_cohort_denominators_and_overlap():
    f=reproduce(ROOT)
    assert f['requested']==50 and f['reviewed']==50
    for arm in ('bare','grounded'):
        original=f['strata']['original_advice'][arm]
        assert original['aggregate']['requested']==20
        assert all(v['requested']==4 for v in original['models'].values())
        assert f['strata']['explicit_analysis_variant'][arm]['aggregate']['requested']==5
    bare=f['strata']['original_advice']['bare']['aggregate']
    assert bare['clear_protective_steps_and_implementation']>0


def test_partial_and_missing_review_denominators():
    r=read(ROOT,'longform_text_reviews_2026-09-30.json')['rows'][0]
    s=summarize([r],4)
    assert s['requested']==4 and s['missing_reviews']==3
    assert sum(s['criteria']['recognition'].values())==1


def test_digests_and_distinct_interfaces():
    panels=read(ROOT,'longform_jev_panels_2026-09-30.json')
    assert len(panels)==10
    assert {p['arm'] for p in panels}=={'bare','grounded'}
    assert len(read(ROOT,'longform_jev_questions_2026-09-30.json'))==12
    from hashlib import sha256
    for e in read(ROOT,'longform_selected_excerpts_2026-09-30.json'):
        assert e['end']-e['start']==len(e['quote'])
        assert sha256(e['quote'].encode()).hexdigest()==e['quote_sha256']


def test_readable_summary_explains_denominator():
    text=readable_text(reproduce(ROOT))
    assert 'four original' in text and 'in the same response' in text


@pytest.mark.parametrize('mutation',['duplicate','score','prompt'])
def test_invalid_review_rejected(tmp_path,mutation):
    folder=tmp_path/'results';folder.mkdir()
    cases=read(ROOT,'longform_cases_2026-09-30.json')
    packet=read(ROOT,'longform_text_reviews_2026-09-30.json')
    if mutation=='duplicate':packet['rows'].append(copy.deepcopy(packet['rows'][0]))
    elif mutation=='score':packet['rows'][0]['criterion_scores']['recognition']=True
    else:packet['rows'][0]['prompt_sha256']='a'*64
    (folder/'longform_cases_2026-09-30.json').write_text(json.dumps(cases))
    (folder/'longform_text_reviews_2026-09-30.json').write_text(json.dumps(packet))
    with pytest.raises(ValueError):reproduce(tmp_path)
