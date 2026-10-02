"""SPDX-License-Identifier: MIT

Art bindings must guard the image actually used after data bindings resolve.
Small diagnostic assets test resource identity, not visual correctness.
"""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pptx_backend.contract import compile_deck

TMP = ROOT / 'tmp/art-binding-tests'
TMP.mkdir(parents=True, exist_ok=True)


class ArtBindingTargetsTests(unittest.TestCase):
    """Keep each resource-identity counterexample isolated and inputs immutable."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temporary.name)
        Image.new('RGBA', (20, 20), 'white').save(self.root / 'price.png')
        Image.new('RGBA', (20, 20), 'blue').save(self.root / 'other.png')
        self.element = {'id': 'price', 'kind': 'image', 'file': 'price.png',
                        'box': [0, 0, 20, 20], 'alt': 'Diagnostic price asset'}
        self.binding = {'key': 'price', 'approved_value': 80, 'object_id': 'price',
                        'file': 'price.png', 'sha256': hashlib.sha256(
                            (self.root / 'price.png').read_bytes()).hexdigest()}
        self.plan = {'schema_version': 'pptx-1', 'canvas': [20, 20],
                     'theme': {'background': '#FFFFFF'},
                     'slides': [{'id': 'S01', 'elements': [self.element]}],
                     'art_bindings': [self.binding]}

    def tearDown(self):
        self.temporary.cleanup()

    def test_legacy_unique_target_passes_without_mutating_plan(self):
        before = copy.deepcopy(self.plan)
        result, pending = compile_deck(self.root, self.plan, {'price': 80})
        self.assertEqual(pending, [])
        self.assertEqual(result, before)
        self.assertEqual(self.plan, before)

    def test_unrelated_actual_image_cannot_use_an_unchanged_binding(self):
        self.element['file'] = 'other.png'
        with self.assertRaisesRegex(ValueError, 'art_binding_file_mismatch'):
            compile_deck(self.root, self.plan, {'price': 80})

    def test_missing_target_is_rejected(self):
        self.binding['object_id'] = 'renamed-away'
        with self.assertRaisesRegex(ValueError, 'art_binding_target_missing'):
            compile_deck(self.root, self.plan, {'price': 80})

    def test_non_image_target_is_rejected(self):
        self.element.update(kind='text', text='80')
        with self.assertRaisesRegex(ValueError, 'art_binding_requires_image'):
            compile_deck(self.root, self.plan, {'price': 80})

    def test_cross_page_same_id_requires_explicit_scope(self):
        self.plan['slides'].append({'id': 'S02', 'elements': [copy.deepcopy(self.element)]})
        with self.assertRaisesRegex(ValueError, 'art_binding_target_ambiguous'):
            compile_deck(self.root, self.plan, {'price': 80})

    def test_explicit_slide_scope_resolves_cross_page_same_id(self):
        other = copy.deepcopy(self.element)
        other['file'] = 'other.png'
        self.plan['slides'].append({'id': 'S02', 'elements': [other]})
        self.binding['slide_id'] = 'S01'
        _, pending = compile_deck(self.root, self.plan, {'price': 80})
        self.assertEqual(pending, [])

    def test_missing_scoped_slide_does_not_fall_back_to_other_page(self):
        self.binding['slide_id'] = 'S99'
        with self.assertRaisesRegex(ValueError, 'art_binding_target_missing: S99/price'):
            compile_deck(self.root, self.plan, {'price': 80})

    def test_equivalent_relative_path_is_accepted(self):
        self.element['file'] = './price.png'
        _, pending = compile_deck(self.root, self.plan, {'price': 80})
        self.assertEqual(pending, [])

    def test_multiple_values_can_share_one_art_object(self):
        second = copy.deepcopy(self.binding)
        second.update(key='tax', approved_value=5)
        self.plan['art_bindings'].append(second)
        _, pending = compile_deck(self.root, self.plan, {'price': 80, 'tax': 5})
        self.assertEqual(pending, [])

    def test_actual_file_is_checked_after_data_binding_resolution(self):
        self.plan['data_bindings'] = [{'key': 'replacement',
                                     'path': ['slides', 0, 'elements', 0, 'file']}]
        before = copy.deepcopy(self.plan)
        with self.assertRaisesRegex(ValueError, 'art_binding_file_mismatch'):
            compile_deck(self.root, self.plan, {'price': 80, 'replacement': 'other.png'})
        self.assertEqual(self.plan, before)

    def test_bound_value_change_still_requests_replacement(self):
        _, pending = compile_deck(self.root, self.plan, {'price': 90})
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['new_value'], 90)

    def test_scoped_replacement_job_keeps_its_page_identity(self):
        self.plan['slides'].append({'id': 'S02', 'elements': [copy.deepcopy(self.element)]})
        self.binding['slide_id'] = 'S02'
        _, pending = compile_deck(self.root, self.plan, {'price': 90})
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['slide_id'], 'S02')

    def test_changed_used_bytes_still_request_replacement(self):
        self.binding['sha256'] = '0' * 64
        _, pending = compile_deck(self.root, self.plan, {'price': 80})
        self.assertEqual(len(pending), 1)


if __name__ == '__main__':
    unittest.main()
