"""SPDX-License-Identifier: MIT

Caller-observable scheduling metrics. No inferred server/GPU concurrency or queue time.
"""

import datetime
import math


def validate_timing(timing):
    """Accept a paired caller clock only; null timing remains explicitly unmeasured."""
    if timing is None:
        return
    if set(timing) != {"submit", "return", "clock_id", "basis"} or not timing["clock_id"]:
        raise ValueError("schedule_invalid_timing")
    for value in (timing["submit"], timing["return"]):
        if set(value) != {"utc", "monotonic_ns"}:
            raise ValueError("schedule_invalid_stamp")
        if datetime.datetime.fromisoformat(value["utc"]).utcoffset() is None:
            raise ValueError("schedule_timezone_required")
        if value['monotonic_ns'] is not None and (not isinstance(value["monotonic_ns"], int) or value["monotonic_ns"] < 0):
            raise ValueError("schedule_invalid_monotonic")
    begin, end = timing['submit']['monotonic_ns'], timing['return']['monotonic_ns']
    if (begin is None) != (end is None):
        raise ValueError('schedule_inconsistent_clock')
    if begin is not None and end < begin:
        raise ValueError("schedule_reversed_timing")


def percentile(values, fraction):
    """Nearest-rank percentile, or null when no observations support the metric."""
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def elapsed_utc(start, end):
    """Return wall-clock seconds; negative skew remains null instead of fabricated zero."""
    duration = (datetime.datetime.fromisoformat(end) - datetime.datetime.fromisoformat(start)).total_seconds()
    return duration if duration >= 0 else None


def report(state):
    """Summarize actual attempts, queue waits and registration lag, retaining unknowns."""
    rows = []
    for identifier, job in state["jobs"].items():
        for attempt in job["attempts"]:
            timing = attempt.get("timing")
            latency, duration_basis = None, 'not_recorded'
            if timing:
                if timing['submit']['monotonic_ns'] is not None:
                    latency = (timing['return']['monotonic_ns'] - timing['submit']['monotonic_ns']) / 1e9
                    duration_basis = 'monotonic'
                else:
                    latency = elapsed_utc(timing['submit']['utc'], timing['return']['utc'])
                    duration_basis = 'UTC_wall_clock_only'
            registered = attempt.get("registered_at")
            lag = elapsed_utc(timing["return"]["utc"], registered["utc"]) if timing and registered else None
            ready = attempt.get("ready_at")
            queue = elapsed_utc(ready["utc"], attempt["claimed_at"]["utc"]) if ready else None
            rows.append({"job": identifier, "attempt": attempt["id"], "state": job["state"],
                         "outcome": attempt.get('outcome', 'unresolved'),
                         "duration_basis": duration_basis,
                         "client_seconds": latency, "return_to_register_seconds": lag,
                         "ready_to_claim_seconds": queue, "timing": timing})
    durations = [row["client_seconds"] for row in rows if row["client_seconds"] is not None]
    lags = [row["return_to_register_seconds"] for row in rows if row["return_to_register_seconds"] is not None]
    times = sorted((datetime.datetime.fromisoformat(row['timing'][edge]['utc']).timestamp(), delta)
                   for row in rows if row['timing'] for edge, delta in [('submit', 1), ('return', -1)])
    active, peak = 0, 0
    for _, delta in times:
        active += delta
        peak = max(peak, active)
    span = times[-1][0] - times[0][0] if times else 0
    completed = sum(row['outcome'] == 'returned' and row['timing'] is not None for row in rows)
    return {"schema": "schedule-report-1", "attempt_count": len(rows),
            "measured_calls": len(durations), "call_p50_seconds": percentile(durations, .5),
            "call_p90_seconds": percentile(durations, .9), "registration_p90_seconds": percentile(lags, .9),
            "lag_basis": "caller_UTC_to_local_registration_UTC", "server_parallelism": "unknown",
            "client_window": state["window"], "measured_client_peak_inflight": peak if times else None,
            "measured_completion_per_minute": completed * 60 / span if span > 0 else None,
            "client_interval_union_basis": "caller_UTC; not server execution",
            "rows": rows}
