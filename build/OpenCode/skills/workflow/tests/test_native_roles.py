"""SPDX-License-Identifier: MIT

Exercise additive native-style and solid-background contracts without artwork.
Run with unittest discovery; each plan stays independent of compiled mutations.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from pptx_backend.contract import compile_deck


class NativeRolesTests(unittest.TestCase):
    """Keep the old explicit-style path while resolving named roles predictably."""

    def setUp(self):
        self.plan = {
            'schema_version': 'pptx-1', 'canvas': [1280, 720],
            'theme': {'background': '#102B36'},
            'text_styles': {'title': {'typeface': 'Noto Sans CJK SC',
                                    'fontSize': 64, 'color': '#FFFFFF'}},
            'slides': [{'id': 'S01', 'elements': [
                {'id': 'title', 'kind': 'text', 'text': '夜读计划',
                 'box': [80, 80, 1000, 100], 'style_role': 'title'}]}]}

    def test_solid_background_needs_no_image_file(self):
        actual, pending = compile_deck(Path.cwd(), self.plan, {})
        self.assertNotIn('background', actual)
        self.assertEqual(actual['theme']['background'], '#102B36')
        self.assertEqual(pending, [])

    def test_role_resolves_without_mutating_source(self):
        before = copy.deepcopy(self.plan)
        actual, _ = compile_deck(Path.cwd(), self.plan, {})
        self.assertEqual(actual['slides'][0]['elements'][0]['style'],
                         self.plan['text_styles']['title'])
        actual['slides'][0]['elements'][0]['style']['color'] = '#000000'
        self.assertEqual(self.plan, before)

    def test_explicit_style_overrides_role_atomically(self):
        self.plan['text_styles']['title']['insets'] = {'top': 0, 'bottom': 0}
        self.plan['slides'][0]['elements'][0]['style'] = {
            'fontSize': 52, 'insets': {'top': 4, 'bottom': 4}}
        actual, _ = compile_deck(Path.cwd(), self.plan, {})
        style = actual['slides'][0]['elements'][0]['style']
        self.assertEqual(style['fontSize'], 52)
        self.assertEqual(style['color'], '#FFFFFF')
        self.assertEqual(style['insets'], {'top': 4, 'bottom': 4})

    def test_old_explicit_style_stays_unchanged(self):
        item = self.plan['slides'][0]['elements'][0]
        del item['style_role']
        item['style'] = {'fontSize': 40, 'bold': True}
        actual, _ = compile_deck(Path.cwd(), self.plan, {})
        self.assertEqual(actual, self.plan)

    def test_unknown_role_identifies_the_source_object(self):
        self.plan['slides'][0]['elements'][0]['style_role'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown_text_style: S01/title/missing'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_nonobject_role_is_rejected(self):
        self.plan['text_styles']['title'] = ['fontSize', 64]
        with self.assertRaisesRegex(ValueError, 'invalid_text_style: S01/title/title'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_nonobject_override_is_rejected(self):
        self.plan['slides'][0]['elements'][0]['style'] = None
        with self.assertRaisesRegex(TypeError, 'invalid_text_style_override: S01/title'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_missing_background_rejects_implicit_default(self):
        del self.plan['theme']
        with self.assertRaisesRegex(ValueError, 'missing_solid_background'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_invalid_solid_color_is_rejected(self):
        self.plan['theme']['background'] = 'linear-gradient(red, blue)'
        with self.assertRaisesRegex(ValueError, 'invalid_solid_background'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_missing_explicit_background_does_not_silently_fall_back(self):
        self.plan['background'] = 'missing.png'
        with self.assertRaisesRegex(ValueError, 'missing_slides_or_background'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_null_background_reports_the_field(self):
        self.plan['background'] = None
        with self.assertRaisesRegex(ValueError, 'invalid_background: background'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_nonobject_theme_reports_the_field(self):
        self.plan['theme'] = []
        with self.assertRaisesRegex(TypeError, 'invalid_solid_background: theme'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_negative_font_size_reports_the_role_and_field(self):
        self.plan['text_styles']['title']['fontSize'] = -3
        with self.assertRaisesRegex(ValueError, 'invalid_text_style_value: S01/title/title/fontSize'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_string_bold_is_not_a_boolean(self):
        self.plan['text_styles']['title']['bold'] = 'false'
        with self.assertRaisesRegex(ValueError, 'invalid_text_style_value: S01/title/title/bold'):
            compile_deck(Path.cwd(), self.plan, {})

    def test_empty_typeface_is_not_a_font(self):
        self.plan['text_styles']['title']['typeface'] = ' '
        with self.assertRaisesRegex(ValueError, 'invalid_text_style_value: S01/title/title/typeface'):
            compile_deck(Path.cwd(), self.plan, {})


if __name__ == '__main__':
    unittest.main()
