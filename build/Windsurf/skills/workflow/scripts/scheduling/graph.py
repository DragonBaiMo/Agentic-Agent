"""SPDX-License-Identifier: MIT

Validate a small production DAG and hash only explicit inputs and dependencies.
No model, shell, visual approval, or artwork generation is performed here.
"""

import hashlib
import json
import re

from project_io import digest, inside


def stamp():
    """Return UTC plus process-independent monotonic time for this machine boot."""
    import datetime
    import time
    return {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns()}


def fingerprint(value):
    """Hash stable JSON, rejecting NaN rather than silently changing its meaning."""
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def prepare_graph(root, plan):
    """Validate IDs, acyclicity and declared files; return topologically ordered jobs.

    Files are project-relative and read only. Each job keeps its caller-owned spec;
    changed inputs invalidate that job and its real descendants, not sibling pages.
    """
    tasks = plan.get("tasks", [])
    if plan.get("schema") != "schedule-1" or not isinstance(tasks, list) or not tasks:
        raise ValueError("schedule_invalid_plan")
    pending = {}
    for item in tasks:
        identifier = item.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", identifier):
            raise ValueError("schedule_invalid_id")
        if identifier in pending:
            raise ValueError("schedule_duplicate_id")
        if type(item.get('priority', 0)) is not int:
            raise ValueError('schedule_invalid_priority')
        files = item.get('input_files', [])
        if not isinstance(files, list) or any(not isinstance(path, str) for path in files):
            raise ValueError('schedule_invalid_input_files')
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list) or any(not isinstance(x, str) for x in dependencies):
            raise ValueError("schedule_invalid_dependencies")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("schedule_duplicate_dependency")
        pending[identifier] = item
    output = {}
    while pending:
        ready = [key for key, spec in pending.items()
                 if all(dep in output for dep in spec.get("depends_on", []))]
        if not ready:
            raise ValueError("schedule_cycle_or_missing_dependency")
        for key in ready:
            spec = pending.pop(key)
            inputs = {path: digest(inside(root, path)) for path in spec.get("input_files", [])}
            parents = {dep: output[dep]["input_hash"] for dep in spec.get("depends_on", [])}
            output[key] = {"spec": spec, "inputs": inputs, "input_hash": fingerprint([spec, inputs, parents]),
                           "state": "waiting", "attempts": []}
    return output


def refresh(state):
    """Release only adopted dependencies; remember when a job first becomes ready."""
    import time
    for job in state["jobs"].values():
        if job["state"] == "retry_wait" and job["retry_at"] <= time.time():
            job["state"] = "waiting"
        if job["state"] != "waiting":
            continue
        dependencies = job["spec"].get("depends_on", [])
        if all(state["jobs"][dep]["state"] == "adopted" for dep in dependencies):
            job.update(state="ready", ready_at=stamp())


def current_attempt(state, identifier, attempt_id):
    """Reject stale callbacks so an earlier version cannot overwrite a new result."""
    job = state["jobs"][identifier]
    if not job["attempts"] or job["attempts"][-1]["id"] != attempt_id:
        raise ValueError("schedule_stale_attempt")
    return job, job["attempts"][-1]


def verify_inputs(root, state, job):
    """Fail closed on changed input/result bytes before a new call or adoption."""
    if any(digest(inside(root, name)) != identity for name, identity in job['inputs'].items()):
        raise ValueError('schedule_reconcile_changed_inputs')
    for dependency in job['spec'].get('depends_on', []):
        result = state['jobs'][dependency]['result']
        if digest(inside(root, result['file'])) != result['sha256']:
            raise ValueError('schedule_saved_result_changed')
