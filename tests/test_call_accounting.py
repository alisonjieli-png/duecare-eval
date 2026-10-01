import json
from pathlib import Path
import shutil
import pytest
from duecare_eval.call_accounting import summarize

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_call_subtotals_and_outcomes():
    result = summarize(ROOT)
    assert result['jev_attempts'] == 119889
    assert result['native_attempt_reservations'] == 84359
    assert result['combined_recorded_attempts_or_reservations'] == 204248
    assert result['recorded_outcomes'] == 204238
    assert result['unknown_outcomes'] == 10
    assert result['newest_native_attempts'] == 274
    assert result['newest_jev_attempts'] == 1
    assert result['cli_internal_provider_calls'] is None


@pytest.mark.parametrize('name,field', [('jev','physical_api_attempts'), ('native','native_recorded_outcomes')])
def test_changed_accounting_total_is_rejected(tmp_path, name, field):
    dest = tmp_path / 'results'
    dest.mkdir()
    for prefix in ('jev', 'native'):
        source = ROOT / 'results' / (prefix+'_call_accounting_2026-10-01.json')
        shutil.copyfile(source, dest / source.name)
    path = dest / (name+'_call_accounting_2026-10-01.json')
    packet = json.loads(path.read_text())
    packet['totals' if name=='jev' else 'aggregate'][field] += 1
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError): summarize(tmp_path)
