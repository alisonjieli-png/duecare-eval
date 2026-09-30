from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
import threading
from pathlib import Path

from .contracts import canonical, sha


class BudgetRefusal(RuntimeError):
    pass


class Journal:
    """Cross-process reservations with immutable policy and append-only events.

    Each write flushes to the OS while an inter-process flock guards concurrent
    writers. Device-level fsync occurs at checkpoints. A crash may lose the
    un-fsynced tail, so recovery should reconcile journal state with provider
    receipts before dispatch. ``fsync="never"`` is available for scratch data.

    An in-process lock serializes threads. Parsed rows stay in a memory cache;
    size and modification-time checks trigger a reread after another process
    changes the file. This avoids repeated full-file parsing on every call.
    """
    def __init__(self, directory: Path, policy: dict, fsync: str | int = "checkpoint"):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "calls.jsonl"
        self.policy = policy
        if fsync not in ("checkpoint", "never") and (type(fsync) is not int or fsync < 1):
            raise ValueError("invalid_fsync_policy")
        self.fsync_policy = fsync
        self._appends_since_fsync = 0
        self._fsynced = False
        for field in ("max_calls", "max_reserved_output_tokens", "max_request_bytes"):
            if type(policy.get(field)) is not int or policy[field] < 1:
                raise ValueError("finite_positive_budget_required")
        self._local = threading.RLock()
        self._rows = None
        self._stat = None
        with self.locked() as stream:
            rows = self.rows(stream)
            self._rows = rows
            self._stat = self._current_stat()
            if rows:
                if rows[0].get("policy") != policy:
                    raise BudgetRefusal("policy_changed_on_resume")
            else:
                self.append(stream, {"event": "policy", "policy": policy})

    @contextmanager
    def locked(self):
        with self._local:
            with self.path.open("a+", encoding="utf-8") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                try:
                    yield stream
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def _current_stat(self):
        try:
            st = os.stat(self.path)
            return (st.st_size, st.st_mtime_ns)
        except FileNotFoundError:
            return None

    def _rows_cached(self, stream):
        """Return parsed rows, re-reading from disk only if another process
        appended since our last view of the file."""
        current = self._current_stat()
        if self._rows is None or (self._stat is not None and current != self._stat):
            self._rows = self.rows(stream)
            self._stat = self._current_stat()
        return self._rows

    @staticmethod
    def rows(stream):
        stream.seek(0)
        return [json.loads(line) for line in stream if line.strip()]

    def append(self, stream, value):
        stream.seek(0, 2)
        value = {"at": datetime.now(timezone.utc).isoformat(), **value}
        stream.write(canonical(value) + "\n")
        stream.flush()
        # Device-level flush at checkpoint boundaries only; see the class note.
        self._appends_since_fsync += 1
        interval = self.fsync_policy if type(self.fsync_policy) is int else 32
        if self.fsync_policy == "checkpoint" and self._appends_since_fsync >= interval:
            os.fsync(stream.fileno())
            self._appends_since_fsync = 0
            self._fsynced = True
        # The exclusive lock keeps this append and the cache update together.
        if self._rows is not None:
            self._rows.append(value)
        self._stat = self._current_stat()

    def checkpoint(self):
        """Flush every pending append to durable storage."""
        if self._appends_since_fsync == 0 and self._fsynced:
            return
        with self.locked() as stream:
            stream.flush()
            os.fsync(stream.fileno())
        self._appends_since_fsync = 0
        self._fsynced = True

    def reserve(self, key: str, provider: str, model: str, payload: dict, output_limit: int):
        if type(output_limit) is not int or output_limit < 0:
            raise ValueError("invalid_output_allocation")
        size = len(canonical(payload).encode())
        if size > self.policy["max_request_bytes"]:
            raise BudgetRefusal("request_byte_limit")
        digest = sha(payload)
        with self.locked() as stream:
            rows = self._rows_cached(stream)
            existing = [x for x in rows if x.get("key") == key]
            if existing:
                reservation = next(x for x in existing if x["event"] == "reserved")
                if reservation["request_sha256"] != digest or reservation["model"] != model or reservation["provider"] != provider:
                    raise BudgetRefusal("request_changed_on_resume")
                complete = [x for x in existing if x["event"] == "completed"]
                if complete:
                    return {"cached": True, "result": complete[-1]["result"]}
                raise BudgetRefusal("prior_attempt_outcome_unknown_no_replay")
            reserved = [x for x in rows if x["event"] == "reserved"]
            if len(reserved) >= self.policy["max_calls"]:
                raise BudgetRefusal("call_ceiling")
            if sum(x["output_allocation"] for x in reserved) + output_limit > self.policy["max_reserved_output_tokens"]:
                raise BudgetRefusal("output_allocation_ceiling")
            if any(x.get("result", {}).get("status") in ("quota", "allocation_violation") for x in rows):
                raise BudgetRefusal("provider_quota_or_allocation_stop")
            self.append(stream, {"event": "reserved", "key": key, "provider": provider, "model": model,
                                 "request_sha256": digest, "request_bytes": size, "output_allocation": output_limit})
        return {"cached": False}

    def complete(self, key: str, result: dict):
        with self.locked() as stream:
            rows = self._rows_cached(stream)
            if not any(x.get("key") == key and x["event"] == "reserved" for x in rows):
                raise ValueError("completion_without_reservation")
            if any(x.get("key") == key and x["event"] == "completed" for x in rows):
                raise ValueError("duplicate_completion")
            self.append(stream, {"event": "completed", "key": key, "result": result})

    def summary(self):
        with self.locked() as stream:
            rows = self._rows_cached(stream)
        # Reading the summary is the point where a campaign is finished; make
        # the journal durable before its numbers are reported or written into
        # a frozen run receipt.
        self.checkpoint()
        attempts = [x for x in rows if x["event"] == "reserved"]
        completed = [x for x in rows if x["event"] == "completed"]
        results = [x["result"] for x in completed]
        usages = [r.get("usage") for r in results]
        # Sum reported cash cost and retain a count of calls awaiting cost data.
        known_costs = [r.get("cash_cost_usd") for r in results if isinstance(r.get("cash_cost_usd"), (int, float))]
        return {"reserved_calls": len(attempts), "completed_calls": len(completed),
                "unknown_outcomes": len(attempts) - len(completed),
                "known_total_tokens": sum(u.get("total_tokens", 0) for u in usages if u and u.get("total_tokens") is not None),
                "missing_usage_records": sum(not u or u.get("total_tokens") is None for u in usages),
                "known_cash_cost_usd": round(sum(known_costs), 6) if known_costs else 0.0,
                "calls_with_cash_record": len(known_costs),
                "calls_without_cash_record": len(results) - len(known_costs),
                "cash_cost": round(sum(known_costs), 6) if known_costs else None, "policy": self.policy}
