from concurrent.futures import ThreadPoolExecutor
import pytest
from duecare_eval.ledger import Journal, BudgetRefusal


def policy(**changes):return {"max_calls":3,"max_reserved_output_tokens":30,"max_request_bytes":1024,**changes}


def test_concurrent_reservations_cannot_overspend(tmp_path):
    journal=Journal(tmp_path,policy())
    def reserve(n):
        try:journal.reserve(str(n),"fixture","model",{"n":n},10);return True
        except BudgetRefusal:return False
    with ThreadPoolExecutor(max_workers=8) as executor:accepted=list(executor.map(reserve,range(15)))
    assert sum(accepted)==3 and journal.summary()["reserved_calls"]==3


def test_interrupted_call_is_not_replayed(tmp_path):
    journal=Journal(tmp_path,policy());journal.reserve("a","fixture","model",{},10)
    with pytest.raises(BudgetRefusal,match="unknown_no_replay"):journal.reserve("a","fixture","model",{},10)


def test_completed_result_reused_without_extra_reservation(tmp_path):
    journal=Journal(tmp_path,policy());journal.reserve("a","fixture","model",{},10)
    journal.complete("a",{"status":"completed","content":"OK","usage":None})
    assert journal.reserve("a","fixture","model",{},10)["cached"]
    assert journal.summary()["reserved_calls"]==1 and journal.summary()["missing_usage_records"]==1


def test_changed_payload_and_budget_cannot_resume(tmp_path):
    journal=Journal(tmp_path,policy());journal.reserve("a","fixture","model",{},10)
    with pytest.raises(BudgetRefusal,match="request_changed"):journal.reserve("a","fixture","model",{"changed":True},10)
    with pytest.raises(BudgetRefusal,match="policy_changed"):Journal(tmp_path,policy(max_calls=8))


def test_output_reservation_not_refunded_after_failure(tmp_path):
    journal=Journal(tmp_path,policy(max_reserved_output_tokens=10))
    journal.reserve("a","fixture","model",{},10);journal.complete("a",{"status":"provider_error"})
    with pytest.raises(BudgetRefusal,match="output_allocation"):journal.reserve("b","fixture","model",{},1)


def test_quota_stops_later_dispatch(tmp_path):
    journal=Journal(tmp_path,policy());journal.reserve("a","fixture","model",{},1)
    journal.complete("a",{"status":"quota"})
    with pytest.raises(BudgetRefusal,match="quota"):journal.reserve("b","fixture","model",{},1)


def test_oversize_input_refused_before_reservation(tmp_path):
    journal=Journal(tmp_path,policy(max_request_bytes=10))
    with pytest.raises(BudgetRefusal,match="request_byte"):journal.reserve("a","fixture","model",{"large":"x"*20},1)
    assert journal.summary()["reserved_calls"]==0


def test_journal_is_durable_and_reloadable_across_instances(tmp_path):
    # A new Journal over the same directory (as a resumed run would create)
    # must see every committed event, including ones written under checkpoint
    # fsync throttling, and must not re-append a policy row.
    first=Journal(tmp_path,policy(max_calls=20))
    for n in range(5):
        first.reserve(f"k{n}","fixture","model",{"n":n},1)
        first.complete(f"k{n}",{"status":"completed","content":"ok","usage":{"total_tokens":1}})
    lines_before=len((tmp_path/"calls.jsonl").read_text().splitlines())
    second=Journal(tmp_path,policy(max_calls=20))
    assert len((tmp_path/"calls.jsonl").read_text().splitlines())==lines_before
    assert second.summary()["reserved_calls"]==5 and second.summary()["completed_calls"]==5
    # a completed key is still served from cache after the reload
    assert second.reserve("k0","fixture","model",{"n":0},1)["cached"]


def test_checkpoint_flushes_everything_appended(tmp_path):
    journal=Journal(tmp_path,policy(max_calls=20),fsync="never")
    journal.reserve("a","fixture","model",{},1)
    journal.complete("a",{"status":"completed","content":"ok","usage":None})
    journal.checkpoint()
    assert (tmp_path/"calls.jsonl").read_text().count("\n")==3
    with pytest.raises(ValueError):Journal(tmp_path,policy(),fsync="sometimes")
