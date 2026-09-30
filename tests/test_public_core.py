from collections import Counter
from duecare_eval.decisioning import decision_input, score_decisions
from duecare_eval.public_cli import ROOT, load_rows, oracle
from duecare_eval.expanded_benchmark import fuse
from duecare_eval.response_variation import profiles, REGISTERS


def test_public_oracle_and_full_denominator():
    tasks = load_rows(ROOT / 'examples/crossborder_references.jsonl')
    perfect = score_decisions(tasks, {t['task_id']: oracle(t) for t in tasks})
    assert perfect['completed'] == 937
    assert all(r['correct'] for r in perfect['per_item'])
    incomplete = score_decisions(tasks, {tasks[0]['task_id']: oracle(tasks[0])})
    assert incomplete['completed'] == 1 and incomplete['missing'] == 936


def test_blind_export_exactly_matches_public_transform():
    refs = load_rows(ROOT / 'examples/crossborder_references.jsonl')
    blind = load_rows(ROOT / 'examples/crossborder_blind_inputs.jsonl')
    assert blind == [decision_input(t) for t in refs]
    assert not any('expected' in r for r in blind)


def test_same_family_is_not_independent_and_similarity_is_not_truth():
    vote={'status':'graded','grade':5,'family':'one'}
    assert fuse([vote]*10,similarity=.99)['grade'] is None
    bad={**vote,'family':'two','grade':2}
    assert fuse([vote,bad])['status']=='review_required'


def test_style_assignment_is_quality_independent():
    cells=profiles('example',['short','medium','long','extended'])
    assert Counter(r['register'] for r in cells)=={r:2 for r in REGISTERS}
    assert len({r['format'] for r in cells})==8


def test_arithmetic_labels_and_reported_acceptance_are_recomputable():
    refs=load_rows(ROOT/'examples/crossborder_references.jsonl')
    observed={r['task_id']:r['decision'] for r in load_rows(ROOT/'results/jev_crossborder_responses.jsonl')}
    cases=[r for r in refs if r['family']=='financial_arithmetic']
    assert len(cases)==13
    for r in cases:
        state=r['state']
        if 'monthly_percent' in state:
            expected=state['monthly_percent']*12==state['claimed_simple_annual_percent']
        else:
            expected=sum(state['monthly_percent_components'])==state['claimed_total_percent']
        assert expected is r['expected']
        assert observed[r['task_id']]['probability']>=0.5
    assert sum(r['expected'] for r in cases)==6


def test_style_comparisons_mix_ties_and_real_controls_without_answer_cue():
    refs=load_rows(ROOT/'examples/style_comparison_references.jsonl')
    blind=load_rows(ROOT/'examples/style_comparison_blind_inputs.jsonl')
    assert Counter(r['expected_winner'] for r in refs)=={'tie':864,'A':432,'B':432}
    assert len(refs)==len(blind)==1728
    assert all('expected_winner' not in r and 'method' not in r for r in blind)
    assert all('Both equivalent formulations should tie' not in r['policy'] for r in blind)
