"""Reconcile the two dated public accounting summaries without live provider access."""
import json
from pathlib import Path


def summarize(root):
    root = Path(root)
    read = lambda name: json.loads((root / 'results' / name).read_text())
    jev = read('jev_call_accounting_2026-10-01.json')
    native = read('native_call_accounting_2026-10-01.json')
    j, n = jev['totals'], native['aggregate']
    for field in ('physical_api_attempts', 'recorded_outcomes', 'unknown_outcomes'):
        if sum(row[field] for row in j['by_campaign'].values()) != j[field]:
            raise ValueError('Jev campaign subtotal mismatch: '+field)
    for field in ('native_attempt_reservations', 'native_recorded_outcomes', 'native_open_reservations'):
        if sum(row[field] for row in native['by_campaign'].values()) != n[field]:
            raise ValueError('Native campaign subtotal mismatch: '+field)
    if j['recorded_outcomes'] + j['unknown_outcomes'] != j['physical_api_attempts']:
        raise ValueError('Jev outcome coverage mismatch')
    if n['native_recorded_outcomes'] + n['native_open_reservations'] != n['native_attempt_reservations']:
        raise ValueError('Native outcome coverage mismatch')
    if sum(n['native_statuses'].values()) != n['native_attempt_reservations']:
        raise ValueError('Native outcome status mismatch')
    latest = sum(native['by_campaign'][key]['native_attempt_reservations'] for key in
                 ('model-expansion', 'matched-context', 'matched-context-adapter', 'glm-low-control', 'context-scaffold'))
    return {
        'scope': 'Exact subtotal of the listed canonical campaigns and declared supplements; earlier smoke/probe history is excluded.',
        'jev_attempts': j['physical_api_attempts'],
        'native_attempt_reservations': n['native_attempt_reservations'],
        'combined_recorded_attempts_or_reservations': j['physical_api_attempts'] + n['native_attempt_reservations'],
        'recorded_outcomes': j['recorded_outcomes'] + n['native_recorded_outcomes'],
        'unknown_outcomes': j['unknown_outcomes'] + n['native_open_reservations'],
        'cli_invocations_separate': n['all_cli_invocations'], 'cli_internal_provider_calls': None,
        'newest_native_attempts': latest, 'newest_jev_attempts': j['by_campaign']['rc4_ilo_menu']['physical_api_attempts'],
        'jev_captured_at': jev['captured_at'], 'native_captured_at': native['capture_completed_at'],
        'case_scope': 'Repeated decisions, grading and retries share cases. Physical attempts and logical answers carry separate denominators.',
    }
