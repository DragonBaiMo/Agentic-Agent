"""SPDX-License-Identifier: MIT

Reject known-invalid PSD plans before claiming or writing a new project directory.
I/O failures remain distinct from these deterministic validation failures.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from project import initialize

TMP = ROOT / 'tmp/project-init-tests'
TMP.mkdir(parents=True, exist_ok=True)


class ProjectInitTests(unittest.TestCase):
    """Each failed input can be corrected without cleaning a partial project."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / 'project'
        self.plan_file = self.directory / 'plan.json'
        self.plan = json.loads((ROOT / 'examples/new-poster.plan.json').read_text())

    def tearDown(self):
        self.temporary.cleanup()

    def write_plan(self):
        """Keep fixture serialization outside the behavior under test."""
        self.plan_file.write_text(json.dumps(self.plan), encoding='utf-8')

    def test_duplicate_layer_id_does_not_create_project(self):
        self.plan['layers'].append(copy.deepcopy(self.plan['layers'][0]))
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'duplicate_id'):
            initialize(self.root, self.plan_file)
        self.assertFalse(self.root.exists())

    def test_duplicate_copy_id_keeps_existing_empty_directory_empty(self):
        self.root.mkdir()
        self.plan['copy'].append(copy.deepcopy(self.plan['copy'][0]))
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'duplicate_id'):
            initialize(self.root, self.plan_file)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_canvas_does_not_create_project(self):
        self.plan['canvas'] = [15, 100]
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'canvas'):
            initialize(self.root, self.plan_file)
        self.assertFalse(self.root.exists())

    def test_corrected_plan_can_retry_the_same_destination(self):
        self.plan['layers'].append(copy.deepcopy(self.plan['layers'][0]))
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'duplicate_id'):
            initialize(self.root, self.plan_file)
        self.plan['layers'].pop()
        self.write_plan()
        result = initialize(self.root, self.plan_file)
        self.assertFalse(result['master_exists'])
        self.assertEqual(json.loads((self.root / 'plan.json').read_text()), self.plan)

    def test_missing_plan_does_not_create_project(self):
        with self.assertRaises(FileNotFoundError):
            initialize(self.root, self.plan_file)
        self.assertFalse(self.root.exists())

    def test_existing_project_remains_untouched(self):
        self.root.mkdir()
        sentinel = self.root / 'keep.txt'
        sentinel.write_text('existing work', encoding='utf-8')
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'project_not_empty'):
            initialize(self.root, self.plan_file)
        self.assertEqual(sentinel.read_text(), 'existing work')
        self.assertEqual(list(self.root.iterdir()), [sentinel])


if __name__ == '__main__':
    unittest.main()
