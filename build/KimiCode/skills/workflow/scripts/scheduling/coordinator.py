"""SPDX-License-Identifier: MIT

Bounded DAG claims and immutable result registration; all shared writes are serialized.
Model calls remain in the current host, behind its existing permission checks.
"""

import math
import random
import shutil
import time
from types import SimpleNamespace

from image_job import register as register_image
from project_io import digest, inside
from scheduling.graph import current_attempt, refresh, stamp, verify_inputs
from scheduling.storage import Store


class Coordinator(Store):
    """Manage small artwork DAGs; never infer visual acceptance from successful I/O."""

    def claim(self):
        """Atomically reserve ready jobs up to the current client in-flight window.

        Claim time is not submit time. Unknown calls reserve capacity until resolved,
        preventing an interrupted paid request from silently being duplicated.
        """
        with self.transaction() as state:
            refresh(state)
            occupied = sum(job["state"] in {"running", "unknown"}
                           for job in state["jobs"].values())
            available = max(0, state["window"] - occupied)
            ready = [(key, job) for key, job in state["jobs"].items() if job["state"] == "ready"]
            ready.sort(key=lambda item: -item[1]["spec"].get("priority", 0))
            claims = []
            for key, job in ready[:available]:
                verify_inputs(self.root, state, job)
                attempt_id = f'{job["input_hash"][:16]}-{len(job["attempts"])+1}'
                attempt = {"id": attempt_id, "claimed_at": stamp(), "ready_at": job['ready_at'],
                           "dependency_results": {dep: state['jobs'][dep]['result']['sha256']
                               for dep in job['spec'].get('depends_on', [])}}
                job["attempts"].append(attempt)
                job["state"] = "running"
                claims.append({"id": key, "attempt_id": attempt_id, "spec": job["spec"],
                               "input_hash": job["input_hash"]})
            return claims

    def returned(self, identifier, attempt_id, source, timing=None, image_record=None):
        """Persist actual returned bytes before notifying shared registration.

        Optional timing must describe the real caller boundary. No timestamps are
        reconstructed from file mtime; missing submit/return values remain unknown.
        """
        from pathlib import Path
        from scheduling.metrics import validate_timing
        validate_timing(timing)
        if image_record is not None:
            self._validate_image_record(image_record)
        source = Path(source)
        identity = digest(source)
        with self.transaction() as state:
            job, attempt = current_attempt(state, identifier, attempt_id)
            if job["state"] in {"returned", "registered", "adopted"}:
                if job["result"]["sha256"] != identity:
                    raise ValueError("schedule_conflicting_result")
                return job["result"]
            if job["state"] not in {"running", "unknown"}:
                raise ValueError("schedule_unexpected_return")
            # NOTE: A private attempt directory prevents concurrent image names colliding.
            relative = f"schedule/artifacts/{identifier}/{attempt_id}/result{source.suffix.lower()}"
            destination = inside(self.root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and digest(destination) != identity:
                raise ValueError("schedule_artifact_collision")
            if not destination.exists():
                temporary = destination.with_suffix(destination.suffix + ".partial")
                shutil.copyfile(source, temporary)
                temporary.replace(destination)
            attempt.update(timing=timing, persisted_at=stamp(), outcome='returned')
            job.update(state="returned", result={"file": relative, "sha256": identity},
                       image_record=image_record)
            return job["result"]

    def register(self, identifier, attempt_id):
        """Register exactly one returned artifact, with idempotent image receipt support.

        Registration is bookkeeping, not artwork approval. Returned artifacts survive
        an interrupted receipt write and can be registered again without regeneration.
        """
        with self.transaction() as state:
            job, attempt = current_attempt(state, identifier, attempt_id)
            if job["state"] in {"registered", "adopted"}:
                return job["result"]
            if job["state"] != "returned":
                raise ValueError("schedule_result_not_returned")
            source = inside(self.root, job["result"]["file"])
            if digest(source) != job["result"]["sha256"]:
                raise ValueError("schedule_saved_result_changed")
            if job.get("image_record") is not None:
                self._register_image(job, identifier, attempt_id, source)
            job["state"] = "registered"
            attempt["registered_at"] = stamp()
            return job["result"]

    def _register_image(self, job, identifier, attempt_id, source):
        record = job["image_record"]
        self._validate_image_record(record)
        execution = inside(self.root, record["execution"]) if record.get("execution") else None
        args = SimpleNamespace(project=self.root, task=identifier, source=source,
                               origin=record["origin"], tool=record["tool"],
                               call_id=record.get("call_id", "not_exposed"), execution=execution,
                               status="assets", reason="", job=record.get("job"),
                               record_id=f"{identifier}-{attempt_id}")
        job["image_receipt"] = register_image(args)

    @staticmethod
    def _validate_image_record(record):
        allowed = {"origin", "tool", "call_id", "execution", "job"}
        if not isinstance(record, dict) or set(record) - allowed:
            raise ValueError("schedule_public_record_fields_only")
        if record.get('origin') not in {'generated', 'user_supplied', 'conversation_history'}:
            raise ValueError('schedule_invalid_origin')
        if not isinstance(record.get('tool'), str) or not record['tool']:
            raise ValueError('schedule_tool_required')

    def adopt(self, identifier, attempt_id):
        """Mark an actually inspected/validated result usable and release its children.

        This is the executor's existing quality decision, not another user approval.
        It neither edits deck.json nor asserts that visual quality was machine-proven.
        """
        with self.transaction() as state:
            job, attempt = current_attempt(state, identifier, attempt_id)
            if job["state"] not in {"registered", "adopted"}:
                raise ValueError("schedule_register_before_adopt")
            verify_inputs(self.root, state, job)
            if digest(inside(self.root, job['result']['file'])) != job['result']['sha256']:
                raise ValueError('schedule_saved_result_changed')
            job["state"] = "adopted"
            attempt.setdefault("adopted_at", stamp())
            refresh(state)

    def fail(self, identifier, attempt_id, kind, retry_after=None, timing=None):
        """Bound retries for confirmed no-result failures; unknown outcomes never resend.

        Retry-After seconds are honored without shortening. Limits apply to total
        attempts. Rate limiting halves the future window but does not cancel callers.
        """
        from scheduling.metrics import validate_timing
        validate_timing(timing)
        if kind not in {"transient", "rate_limit", "permanent", "unknown"}:
            raise ValueError("schedule_invalid_failure_kind")
        if retry_after is not None and (not isinstance(retry_after, (int, float)) or
                                       not math.isfinite(retry_after) or retry_after < 0):
            raise ValueError("schedule_invalid_retry_after")
        with self.transaction() as state:
            job, attempt = current_attempt(state, identifier, attempt_id)
            if job["state"] not in {"running", "unknown"}:
                raise ValueError("schedule_failure_after_result")
            attempt.update(failure_kind=kind, failure_at=stamp(), outcome=kind)
            if timing is not None:
                attempt['timing'] = timing
            if kind == "rate_limit":
                state["window"] = max(1, state["window"] // 2)
            if kind == "unknown":
                job["state"] = "unknown"
            elif kind == "permanent" or len(job["attempts"]) >= state["max_attempts"]:
                job["state"] = "failed"
            else:
                delay = retry_after if retry_after is not None else 2 ** len(job["attempts"])
                delay += random.uniform(0, min(1, delay / 4))
                job.update(state="retry_wait", retry_at=time.time() + delay)

    def recover(self):
        """After the old caller has stopped, quarantine unfinished calls for reconciliation.

        Never invoke while another host loop is live. Returned/registered/adopted
        artifacts are left intact and do not consume generation slots.
        """
        with self.transaction() as state:
            for job in state["jobs"].values():
                if job["state"] == "running":
                    job["state"] = "unknown"
                    job["attempts"][-1]["interrupted_at"] = stamp()
            refresh(state)
        return self.snapshot()

    def local_error(self, identifier, attempt_id, phase, error_type):
        """Keep a failed local consumer visible without discarding unrelated tool results."""
        with self.transaction() as state:
            job, attempt = current_attempt(state, identifier, attempt_id)
            job['consumer_error'] = {'phase': phase, 'error_type': error_type, 'at': stamp()}
            if job['state'] == 'running':
                job['state'] = 'unknown'
                attempt['outcome'] = 'unknown'
