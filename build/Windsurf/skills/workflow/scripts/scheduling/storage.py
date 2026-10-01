"""SPDX-License-Identifier: MIT

SQLite-backed single-writer state and crash-safe transactions for a small DAG.
Only this coordinator may mutate shared receipts while a schedule is active.
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from project_io import inside
from scheduling.graph import prepare_graph, refresh, stamp


class Store:
    """Serialize short state/receipt writes across processes, with a bounded lock wait.

    One project owns one database. Connections never span model/network awaits.
    A process crash releases SQLite locks; uncertain calls still need reconciliation.
    """

    def __init__(self, root):
        """Open project-owned storage; no installation, external access, or model call."""
        self.root = Path(root).resolve()
        self.path = inside(self.root, "schedule/state.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def transaction(self):
        """Yield mutable state, atomically commit on success, roll back on any error."""
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT)")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT data FROM state WHERE id=1").fetchone()
            state = json.loads(row[0]) if row else {}
            yield state
            connection.execute("INSERT OR REPLACE INTO state VALUES (1, ?)",
                               (json.dumps(state, ensure_ascii=False, allow_nan=False),))
            connection.commit()
        finally:
            connection.close()

    def initialize(self, plan, window=2, max_attempts=3):
        """Create a new schedule; never reset an existing production history."""
        if type(window) is not int or not 1 <= window <= 32:
            raise ValueError("schedule_invalid_window")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
            raise ValueError("schedule_invalid_attempt_limit")
        jobs = prepare_graph(self.root, plan)
        with self.transaction() as state:
            if state:
                raise ValueError("schedule_exists")
            state.update(schema="schedule-state-1", window=window, max_attempts=max_attempts,
                         jobs=jobs, archived=[], created_at=stamp())
            refresh(state)
        return self.snapshot()

    def snapshot(self):
        """Read a transactionally consistent copy, including persisted wait states."""
        with self.transaction() as state:
            if not state:
                raise ValueError("schedule_not_initialized")
            return json.loads(json.dumps(state))

    def reconcile_plan(self, plan):
        """Invalidate changed inputs and descendants, preserving immutable old evidence.

        Active or uncertain calls must be resolved first. Unchanged adopted assets
        are reused only when their recorded file still exists and matches its hash.
        """
        from project_io import digest
        updated = prepare_graph(self.root, plan)
        with self.transaction() as state:
            if any(job["state"] in {"running", "unknown"} for job in state["jobs"].values()):
                raise ValueError("schedule_resolve_active_calls_first")
            for key, old in state["jobs"].items():
                if key in updated and old["input_hash"] == updated[key]["input_hash"]:
                    result = old.get("result")
                    if result and (not inside(self.root, result["file"]).is_file() or
                                   digest(inside(self.root, result["file"])) != result["sha256"]):
                        raise ValueError("schedule_saved_result_changed")
                    updated[key] = old
                else:
                    state["archived"].append(old)
            state["jobs"] = updated
            refresh(state)
        return self.snapshot()
