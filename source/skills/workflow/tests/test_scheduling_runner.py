"""SPDX-License-Identifier: MIT

Exercise real async overlap and event order with deterministic local diagnostic tasks.
"""

import asyncio
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scheduling import Coordinator, run
from scheduling.metrics import report
from scheduling.runner import ServiceFailure

TMP = ROOT / 'tmp/scheduling-runner-tests'
TMP.mkdir(parents=True, exist_ok=True)


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    """No network or model costs; fixture delays test scheduling, not service speed."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temp.name)
        self.source = self.root / 'local-result.txt'
        self.source.write_text('local diagnostic')
        self.queue = Coordinator(self.root)
        self.queue.initialize({'schema': 'schedule-1', 'tasks': [
            {'id': 'fast'}, {'id': 'slow'}, {'id': 'child', 'depends_on': ['fast']}]})
        self.events = {}

    def tearDown(self):
        self.temp.cleanup()

    async def invoke(self, claim):
        """Stand in for a latency-skewed external adapter without claiming model calls."""
        self.events[claim['id'] + '-start'] = time.monotonic()
        await asyncio.sleep({'fast': .01, 'slow': .2, 'child': .01}[claim['id']])
        self.events[claim['id'] + '-end'] = time.monotonic()
        return {'source': self.source}

    async def inspect(self, claim, state):
        """Validate local bytes as a fixture, never artwork or rendered slide quality."""
        self.assertEqual(state['jobs'][claim['id']]['state'], 'registered')
        return True

    async def test_child_starts_before_slow_sibling_returns(self):
        state = await run(self.queue, self.invoke, self.inspect)
        self.assertLess(self.events['child-start'], self.events['slow-end'])
        self.assertEqual(state['jobs']['child']['state'], 'adopted')
        self.assertEqual(report(state)['measured_calls'], 3)

    async def test_slow_inspection_does_not_delay_other_registration(self):
        async def slow_inspect(claim, state):
            await asyncio.sleep(.25)
            return True
        task = asyncio.create_task(run(self.queue, self.invoke, slow_inspect))
        await asyncio.sleep(.23)
        state = self.queue.snapshot()
        self.assertEqual(state['jobs']['slow']['state'], 'registered')
        await task

    async def test_timeout_is_unknown_and_never_auto_reissued(self):
        state = await run(self.queue, self.invoke, self.inspect, timeout=.001)
        self.assertEqual(state['jobs']['fast']['state'], 'unknown')
        self.assertEqual(len(state['jobs']['fast']['attempts']), 1)
        self.assertEqual(report(state)['measured_calls'], 2)

    async def test_known_failure_retries_only_affected_call(self):
        async def transient(claim):
            if claim['id'] == 'fast' and claim['attempt_id'].endswith('-1'):
                raise ServiceFailure('transient', 0)
            return await self.invoke(claim)
        state = await run(self.queue, transient, self.inspect)
        self.assertEqual(len(state['jobs']['fast']['attempts']), 2)
        self.assertEqual(len(state['jobs']['slow']['attempts']), 1)
        self.assertEqual(state['jobs']['child']['state'], 'adopted')

    async def test_returned_results_resume_without_invocation(self):
        first, second = self.queue.claim()
        self.queue.returned(first['id'], first['attempt_id'], self.source)
        self.queue.returned(second['id'], second['attempt_id'], self.source)
        state = await run(self.queue, self.invoke, self.inspect)
        self.assertNotIn('fast-start', self.events)
        self.assertNotIn('slow-start', self.events)
        self.assertEqual(state['jobs']['child']['state'], 'adopted')

    async def test_review_rejection_preserves_result_and_blocks_descendants(self):
        async def reject(claim, state):
            return False
        state = await run(self.queue, self.invoke, reject)
        self.assertEqual(state['jobs']['fast']['state'], 'registered')
        self.assertEqual(state['jobs']['child']['state'], 'waiting')

    async def test_deadline_leaves_no_untracked_active_tasks(self):
        state = await run(self.queue, self.invoke, self.inspect, deadline_seconds=.001)
        self.assertNotIn('running', {job['state'] for job in state['jobs'].values()})

    async def test_inspection_error_does_not_cancel_unrelated_call(self):
        async def broken_inspection(claim, state):
            if claim['id'] == 'fast':
                raise ValueError('diagnostic_local_failure')
            return True
        state = await run(self.queue, self.invoke, broken_inspection)
        self.assertEqual(state['jobs']['slow']['state'], 'adopted')
        self.assertEqual(state['jobs']['fast']['state'], 'registered')
        self.assertEqual(state['jobs']['fast']['consumer_error']['phase'], 'inspect')

    async def test_missing_local_result_does_not_repeat_model_call(self):
        async def missing_result(claim):
            if claim['id'] == 'fast':
                return {'source': self.root / 'missing.png'}
            return await self.invoke(claim)
        state = await run(self.queue, missing_result, self.inspect)
        self.assertEqual(state['jobs']['fast']['state'], 'unknown')
        self.assertEqual(len(state['jobs']['fast']['attempts']), 1)
        self.assertEqual(state['jobs']['slow']['state'], 'adopted')


if __name__ == '__main__':
    unittest.main()
