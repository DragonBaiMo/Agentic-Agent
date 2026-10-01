"""SPDX-License-Identifier: MIT

Production scheduling invariants using local diagnostic bytes, never generated artwork.
"""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scheduling import Coordinator
from scheduling.graph import prepare_graph, stamp
from scheduling.metrics import report, validate_timing

TMP = ROOT / 'tmp/scheduling-tests'
TMP.mkdir(parents=True, exist_ok=True)


class SchedulingTests(unittest.TestCase):
    """Isolated transactional projects cover recovery, retries, versions, and safety."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.txt'
        self.source.write_text('diagnostic')
        self.plan = {'schema': 'schedule-1', 'tasks': [
            {'id': 'A', 'input_files': ['source.txt']}, {'id': 'B'},
            {'id': 'A-layer', 'depends_on': ['A']}]}
        self.queue = Coordinator(self.root)
        self.queue.initialize(self.plan)

    def tearDown(self):
        self.temp.cleanup()

    def returned(self, claim):
        """Create one actual durable diagnostic result through the public interface."""
        return self.queue.returned(claim['id'], claim['attempt_id'], self.source)

    def accept(self, claim):
        """Exercise all three distinct persistence, registration and adoption steps."""
        self.returned(claim)
        self.queue.register(claim['id'], claim['attempt_id'])
        self.queue.adopt(claim['id'], claim['attempt_id'])

    def test_bounded_window_does_not_double_claim(self):
        self.assertEqual(len(self.queue.claim()), 2)
        self.assertEqual(self.queue.claim(), [])

    def test_child_released_without_waiting_for_sibling(self):
        first, _ = self.queue.claim()
        self.accept(first)
        self.assertEqual(self.queue.claim()[0]['id'], 'A-layer')

    def test_registration_does_not_claim_artwork_quality(self):
        first, _ = self.queue.claim()
        self.returned(first)
        self.queue.register('A', first['attempt_id'])
        self.assertEqual(self.queue.snapshot()['jobs']['A-layer']['state'], 'waiting')

    def test_return_is_durable_before_registration(self):
        first, _ = self.queue.claim()
        result = self.returned(first)
        self.assertEqual((self.root / result['file']).read_bytes(), self.source.read_bytes())
        self.assertEqual(Coordinator(self.root).snapshot()['jobs']['A']['state'], 'returned')

    def test_idempotent_return_and_registration(self):
        first, _ = self.queue.claim()
        expected = self.returned(first)
        self.assertEqual(self.returned(first), expected)
        self.assertEqual(self.queue.register('A', first['attempt_id']), expected)
        self.assertEqual(self.queue.register('A', first['attempt_id']), expected)

    def test_conflicting_callback_rejected(self):
        first, _ = self.queue.claim()
        self.returned(first)
        self.source.write_text('different')
        with self.assertRaisesRegex(ValueError, 'conflicting_result'):
            self.returned(first)

    def test_recovery_quarantines_unknown_call(self):
        self.queue.claim()
        state = self.queue.recover()
        self.assertEqual(state['jobs']['A']['state'], 'unknown')
        self.assertEqual(self.queue.claim(), [])

    def test_late_result_resolves_unknown_without_resubmitting(self):
        first, _ = self.queue.claim()
        self.queue.recover()
        self.accept(first)
        self.assertEqual(len(self.queue.snapshot()['jobs']['A']['attempts']), 1)

    def test_recovery_preserves_returned_asset(self):
        first, _ = self.queue.claim()
        self.returned(first)
        self.assertEqual(self.queue.recover()['jobs']['A']['state'], 'returned')

    def test_unknown_error_never_retries(self):
        first, _ = self.queue.claim()
        self.queue.fail('A', first['attempt_id'], 'unknown')
        self.assertEqual(self.queue.claim(), [])

    def test_transient_failure_retries_only_failed_job(self):
        first, _ = self.queue.claim()
        self.queue.fail('A', first['attempt_id'], 'transient', 0)
        again = self.queue.claim()
        self.assertEqual([item['id'] for item in again], ['A'])
        self.assertNotEqual(again[0]['attempt_id'], first['attempt_id'])

    def test_retry_limit_is_total_attempts(self):
        first, _ = self.queue.claim()
        self.queue.fail('A', first['attempt_id'], 'transient', 0)
        second = self.queue.claim()[0]
        self.queue.fail('A', second['attempt_id'], 'transient', 0)
        third = self.queue.claim()[0]
        self.queue.fail('A', third['attempt_id'], 'transient', 0)
        self.assertEqual(self.queue.snapshot()['jobs']['A']['state'], 'failed')

    def test_rate_limit_shrinks_window_and_honors_retry_after(self):
        first, _ = self.queue.claim()
        with patch('time.time', return_value=100), patch('random.uniform', return_value=0):
            self.queue.fail('A', first['attempt_id'], 'rate_limit', 30)
        state = self.queue.snapshot()
        self.assertEqual(state['window'], 1)
        self.assertEqual(state['jobs']['A']['retry_at'], 130)

    def test_permanent_error_stops_only_failed_branch(self):
        first, second = self.queue.claim()
        self.queue.fail('A', first['attempt_id'], 'permanent')
        self.accept(second)
        self.assertEqual(self.queue.snapshot()['jobs']['B']['state'], 'adopted')

    def test_stale_attempt_rejected(self):
        self.queue.claim()
        with self.assertRaisesRegex(ValueError, 'stale_attempt'):
            self.queue.returned('A', 'old', self.source)

    def test_input_change_invalidates_only_descendants(self):
        first, second = self.queue.claim()
        self.accept(first)
        self.accept(second)
        child = self.queue.claim()[0]
        self.accept(child)
        self.source.write_text('revision two')
        state = self.queue.reconcile_plan(self.plan)
        self.assertEqual(state['jobs']['A']['state'], 'ready')
        self.assertEqual(state['jobs']['A-layer']['state'], 'waiting')
        self.assertEqual(state['jobs']['B']['state'], 'adopted')
        self.assertEqual(len(state['archived']), 2)

    def test_changed_input_before_claim_requires_reconcile(self):
        self.source.write_text('changed after initialization')
        with self.assertRaisesRegex(ValueError, 'reconcile_changed_inputs'):
            self.queue.claim()

    def test_active_plan_cannot_be_replaced(self):
        self.queue.claim()
        with self.assertRaisesRegex(ValueError, 'resolve_active_calls_first'):
            self.queue.reconcile_plan(self.plan)

    def test_saved_result_tampering_blocks_reuse(self):
        first, second = self.queue.claim()
        self.accept(first)
        self.accept(second)
        result = self.queue.snapshot()['jobs']['A']['result']
        (self.root / result['file']).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'saved_result_changed'):
            self.queue.reconcile_plan(self.plan)

    def test_missing_timing_stays_unknown(self):
        self.accept(self.queue.claim()[0])
        actual = report(self.queue.snapshot())
        self.assertEqual(actual['measured_calls'], 0)
        self.assertIsNone(actual['registration_p90_seconds'])
        self.assertEqual(actual['server_parallelism'], 'unknown')

    def test_measured_timing_uses_caller_clock(self):
        first, _ = self.queue.claim()
        start, end = stamp(), stamp()
        start['monotonic_ns'], end['monotonic_ns'] = 100, 1000000100
        timing = {'submit': start, 'return': end, 'clock_id': 'test', 'basis': 'diagnostic_fixture'}
        self.queue.returned('A', first['attempt_id'], self.source, timing)
        self.queue.register('A', first['attempt_id'])
        self.assertEqual(report(self.queue.snapshot())['call_p50_seconds'], 1)

    def test_cycle_rejected(self):
        plan = {'schema': 'schedule-1', 'tasks': [{'id': 'X', 'depends_on': ['X']}]}
        with self.assertRaisesRegex(ValueError, 'cycle_or_missing'):
            prepare_graph(self.root, plan)

    def test_path_escape_rejected(self):
        plan = {'schema': 'schedule-1', 'tasks': [{'id': 'X', 'input_files': ['../secret']}]}
        with self.assertRaisesRegex(ValueError, 'outside_project'):
            prepare_graph(self.root, plan)

    def test_duplicate_ids_rejected(self):
        plan = {'schema': 'schedule-1', 'tasks': [{'id': 'X'}, {'id': 'X'}]}
        with self.assertRaisesRegex(ValueError, 'duplicate_id'):
            prepare_graph(self.root, plan)

    def test_invalid_timing_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_timing'):
            validate_timing({'submit': 0})

    def test_native_host_without_monotonic_clock_is_labeled(self):
        first, _ = self.queue.claim()
        start = {'utc': '2026-09-30T14:00:00+00:00', 'monotonic_ns': None}
        end = {'utc': '2026-09-30T14:00:02+00:00', 'monotonic_ns': None}
        self.queue.returned('A', first['attempt_id'], self.source,
            {'submit': start, 'return': end, 'clock_id': 'native', 'basis': 'actual_tool_boundary_UTC_only'})
        row = report(self.queue.snapshot())['rows'][0]
        self.assertEqual(row['client_seconds'], 2)
        self.assertEqual(row['duration_basis'], 'UTC_wall_clock_only')

    def test_mixed_clock_pair_rejected(self):
        start, end = stamp(), stamp()
        end['monotonic_ns'] = None
        with self.assertRaisesRegex(ValueError, 'inconsistent_clock'):
            validate_timing({'submit': start, 'return': end, 'clock_id': 'native', 'basis': 'fixture'})

    def test_invalid_retry_after_rejected(self):
        first, _ = self.queue.claim()
        with self.assertRaisesRegex(ValueError, 'invalid_retry_after'):
            self.queue.fail('A', first['attempt_id'], 'rate_limit', float('nan'))

    def test_adoption_without_registration_rejected(self):
        first, _ = self.queue.claim()
        with self.assertRaisesRegex(ValueError, 'register_before_adopt'):
            self.queue.adopt('A', first['attempt_id'])

    def test_reinitialization_preserves_old_state(self):
        with self.assertRaisesRegex(ValueError, 'schedule_exists'):
            self.queue.initialize(self.plan)
        self.assertEqual(len(self.queue.snapshot()['jobs']), 3)


if __name__ == '__main__':
    unittest.main()
