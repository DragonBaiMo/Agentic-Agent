"""SPDX-License-Identifier: MIT

Native-host JSON commands, concurrent claims and idempotent shared image receipts.
"""

from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import schedule
from project_io import write_json
from scheduling import Coordinator

TMP = ROOT / 'tmp/scheduling-cli-tests'
TMP.mkdir(parents=True, exist_ok=True)


class ScheduleCliTests(unittest.TestCase):
    """Use real state and bytes with parsers, including recovery around receipt commit."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.png'
        self.source.write_bytes(b'local diagnostic bytes, not an image')
        self.plan = {'schema': 'schedule-1', 'tasks': [{'id': 'A'}, {'id': 'B'}]}
        self.queue = Coordinator(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def call(self, command, payload=None):
        """Execute actual parser and parse its machine JSON; logs stay separate."""
        args = ['schedule', '--project', str(self.root), command]
        if payload is not None:
            path = self.root / 'payload.json'
            write_json(path, payload)
            args.extend(['--payload', str(path)])
        output = io.StringIO()
        with patch.object(sys, 'argv', args), contextlib.redirect_stdout(output):
            schedule.main()
        return json.loads(output.getvalue())

    def test_cli_init_claim_register_and_report(self):
        self.call('init', {'plan': self.plan})
        first = self.call('next')[0]
        identity = {'identifier': first['id'], 'attempt_id': first['attempt_id']}
        self.call('return', {**identity, 'source': str(self.source)})
        self.call('register', identity)
        self.call('adopt', identity)
        self.assertEqual(self.call('status')['jobs']['A']['state'], 'adopted')
        self.assertEqual(self.call('report')['attempt_count'], 2)

    def test_cli_failure_is_nonzero_and_structured(self):
        with self.assertLogs(level='ERROR') as logs, self.assertRaises(SystemExit) as error:
            self.call('status')
        self.assertEqual(error.exception.code, 2)
        self.assertIn('schedule_command_failed', logs.output[0])

    def test_competing_claims_do_not_exceed_global_window(self):
        self.queue.initialize(self.plan, window=1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.queue.claim)
            second = pool.submit(Coordinator(self.root).claim)
            results = first.result() + second.result()
        self.assertEqual(len(results), 1)

    def test_shared_image_receipt_is_idempotent_after_crash(self):
        self.queue.initialize(self.plan)
        first = self.queue.claim()[0]
        self.queue.returned('A', first['attempt_id'], self.source,
                            image_record={'origin': 'user_supplied', 'tool': 'diagnostic_fixture'})
        self.queue.register('A', first['attempt_id'])
        # NOTE: Reproduce a lost state commit after the shared receipt was durable.
        with self.queue.transaction() as state:
            state['jobs']['A']['state'] = 'returned'
        self.queue.register('A', first['attempt_id'])
        self.assertEqual(len(json.loads((self.root / 'receipts.json').read_text())), 1)

    def test_bad_public_metadata_is_rejected_before_storage(self):
        self.queue.initialize(self.plan)
        first = self.queue.claim()[0]
        with self.assertRaisesRegex(ValueError, 'public_record_fields_only'):
            self.queue.returned('A', first['attempt_id'], self.source, image_record={'credential': 'blocked'})
        self.assertNotIn('credential', json.dumps(self.queue.snapshot()))

    def test_invalid_window_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_window'):
            self.queue.initialize(self.plan, window=0)

    def test_invalid_attempt_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_attempt_limit'):
            self.queue.initialize(self.plan, max_attempts=0)


if __name__ == '__main__':
    unittest.main()
