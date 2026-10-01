"""SPDX-License-Identifier: MIT

Rolling async adapter runner with immediate persistence and one inspection consumer.
Adapters call only authorized tools and explicitly classify confirmed service failures.
"""

import asyncio
import time
import uuid

from scheduling.graph import stamp


class ServiceFailure(Exception):
    """Declare a confirmed service outcome; unclassified exceptions remain unknown."""

    def __init__(self, kind, retry_after=None):
        """Carry a supported failure kind and optional Retry-After seconds, no secrets."""
        super().__init__(kind)
        self.kind = kind
        self.retry_after = retry_after


async def _execute(coordinator, claim, invoke, timeout):
    begin = stamp()
    clock_id = str(uuid.uuid4())
    try:
        result = await asyncio.wait_for(invoke(claim), timeout)
        end = stamp()
    except ServiceFailure as error:
        await asyncio.to_thread(coordinator.fail, claim['id'], claim['attempt_id'],
                                error.kind, error.retry_after, _timing(begin, clock_id))
        return None
    except (Exception, asyncio.CancelledError):
        # NOTE: Cancellation cannot prove the upstream paid operation was cancelled.
        await asyncio.to_thread(coordinator.fail, claim['id'], claim['attempt_id'], 'unknown',
                                timing=_timing(begin, clock_id))
        return None
    timing = result.get('timing', {'submit': begin, 'return': end,
                        'clock_id': clock_id, 'basis': 'adapter_boundary'})
    # NOTE: A registration error must not trigger another model call.
    try:
        await asyncio.to_thread(coordinator.returned, claim['id'], claim['attempt_id'],
                                result['source'], timing, result.get('image_record'))
        await asyncio.to_thread(coordinator.register, claim['id'], claim['attempt_id'])
    except Exception as error:
        await asyncio.to_thread(coordinator.local_error, claim['id'], claim['attempt_id'],
                                'persist_or_register', type(error).__name__)
        return None
    return claim


def _timing(begin, clock_id):
    return {'submit': begin, 'return': stamp(), 'clock_id': clock_id, 'basis': 'adapter_boundary'}


async def _resume_results(coordinator):
    state = await asyncio.to_thread(coordinator.snapshot)
    claims = []
    for identifier, job in state['jobs'].items():
        if job['state'] in {'returned', 'registered'}:
            claim = {'id': identifier, 'attempt_id': job['attempts'][-1]['id'], 'spec': job['spec']}
            await asyncio.to_thread(coordinator.register, identifier, claim['attempt_id'])
            claims.append(claim)
    return claims


async def _inspect(coordinator, claim, inspect):
    try:
        accepted = await inspect(claim, await asyncio.to_thread(coordinator.snapshot))
        if accepted:
            await asyncio.to_thread(coordinator.adopt, claim['id'], claim['attempt_id'])
    except Exception as error:
        await asyncio.to_thread(coordinator.local_error, claim['id'], claim['attempt_id'],
                                'inspect', type(error).__name__)


async def run(coordinator, invoke, inspect, timeout=600, deadline_seconds=3600):
    """Run dependency-ready jobs until done, blocked, or a bounded caller deadline.

    invoke(claim) returns an existing source path and optional public image metadata.
    inspect(claim, state) returns True only after real local/visual validation.
    Local I/O is offloaded, inspections serialize, returned files do not wait for QA.
    A False inspection preserves registered bytes and pauses only their descendants.
    """
    if timeout <= 0 or deadline_seconds <= 0:
        raise ValueError('schedule_positive_timeout_required')
    active, pending_reviews, review = set(), await _resume_results(coordinator), None
    deadline = time.monotonic() + deadline_seconds
    try:
        while time.monotonic() < deadline:
            claims = await asyncio.to_thread(coordinator.claim)
            active.update(asyncio.create_task(_execute(coordinator, item, invoke, timeout))
                          for item in claims)
            if review is None and pending_reviews:
                review = asyncio.create_task(_inspect(coordinator, pending_reviews.pop(0), inspect))
            waiting = active | ({review} if review else set())
            if not waiting:
                state = await asyncio.to_thread(coordinator.snapshot)
                delays = [job['retry_at'] - time.time() for job in state['jobs'].values()
                          if job['state'] == 'retry_wait']
                if not delays:
                    return state
                await asyncio.sleep(min(max(.001, min(delays)), max(0, deadline - time.monotonic())))
                continue
            done, _ = await asyncio.wait(waiting, timeout=max(0, deadline - time.monotonic()),
                                         return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                if task is review:
                    review = None
                else:
                    active.remove(task)
                    if result:
                        pending_reviews.append(result)
    finally:
        # NOTE: Never leave untracked local tasks after timeout or caller cancellation.
        remaining = active | ({review} if review else set())
        for task in remaining:
            task.cancel()
        await asyncio.gather(*remaining, return_exceptions=True)
    return await asyncio.to_thread(coordinator.snapshot)
