"""SPDX-License-Identifier: MIT

Read-only hide views must not alter document state or show hidden siblings.
Synthetic diagnostic pixels exercise visibility, not artwork quality.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import Group, PixelLayer

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from review_psd import hide_view

TMP = ROOT / "tmp/review-isolation-tests"
TMP.mkdir(parents=True, exist_ok=True)


def make_source(file):
    """Save independent grouped colors so every test starts with updated=False."""
    psd = PSDImage.new("RGB", (32, 32))
    PixelLayer.frompil(Image.new("RGBA", (32, 32), "white"), psd, "background")
    group = Group.new(psd, "objects")
    PixelLayer.frompil(Image.new("RGBA", (12, 12), "red"), group, "red")
    PixelLayer.frompil(Image.new("RGBA", (12, 12), "blue"), group, "blue", left=16, top=16)
    hidden = Group.new(psd, "hidden-group")
    PixelLayer.frompil(Image.new("RGBA", (32, 32), "green"), hidden, "hidden-green")
    hidden.visible = False
    hidden_leaf = PixelLayer.frompil(Image.new("RGBA", (32, 32), "black"), psd, "hidden-black")
    hidden_leaf.visible = False
    psd.save(file)


class ReviewIsolationTests(unittest.TestCase):
    """Check actual output pixels and state, including failure and hidden input."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "source.psd"
        make_source(self.source)
        self.psd = PSDImage.open(self.source)
        self.out = self.directory / "hidden.png"

    def tearDown(self):
        self.temporary.cleanup()

    def test_hide_leaf_does_not_mark_document_updated(self):
        self.assertFalse(self.psd.is_updated())
        hide_view(self.psd, "red", self.out)
        self.assertFalse(self.psd.is_updated())

    def test_hide_leaf_preserves_sibling_and_hidden_inputs(self):
        hide_view(self.psd, "red", self.out)
        with Image.open(self.out) as image:
            self.assertEqual(image.getpixel((4, 4)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((20, 20)), (0, 0, 255, 255))

    def test_hide_group_hides_children_only(self):
        hide_view(self.psd, "objects", self.out)
        with Image.open(self.out) as image:
            self.assertEqual(image.getpixel((4, 4)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((20, 20)), (255, 255, 255, 255))
        self.assertFalse(self.psd.is_updated())

    def test_already_hidden_group_stays_hidden(self):
        hide_view(self.psd, "hidden-group", self.out)
        with Image.open(self.out) as image:
            self.assertEqual(image.getpixel((4, 4)), (255, 0, 0, 255))
            self.assertEqual(image.getpixel((20, 20)), (0, 0, 255, 255))
        self.assertFalse(self.psd.is_updated())

    def test_already_hidden_leaf_stays_hidden(self):
        hide_view(self.psd, "hidden-black", self.out)
        with Image.open(self.out) as image:
            self.assertEqual(image.getpixel((4, 4)), (255, 0, 0, 255))
        self.assertFalse(self.psd.is_updated())

    def test_preexisting_updated_state_stays_true(self):
        self.psd.mark_updated()
        hide_view(self.psd, "red", self.out)
        self.assertTrue(self.psd.is_updated())

    def test_failed_image_write_keeps_flags_and_update_state(self):
        before = [(layer.name, layer.visible) for layer in self.psd.descendants()]
        with (patch.object(Image.Image, "save", side_effect=OSError("intentional")),
              self.assertRaisesRegex(OSError, "intentional")):
            hide_view(self.psd, "red", self.out)
        self.assertEqual([(layer.name, layer.visible) for layer in self.psd.descendants()], before)
        self.assertFalse(self.psd.is_updated())


if __name__ == "__main__":
    unittest.main()
