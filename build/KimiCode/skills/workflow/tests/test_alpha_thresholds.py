"""SPDX-License-Identifier: MIT

Regress probe/crop threshold semantics with diagnostic pixels, never design assets.
Run: python -m unittest discover -s tests -p test_alpha_thresholds.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from crop_alpha import crop_asset
from probe_assets import inspect

TMP = ROOT / "tmp/alpha-threshold-tests"
TMP.mkdir(parents=True, exist_ok=True)


class AlphaThresholdTests(unittest.TestCase):
    """Pin both existing numeric contracts and the newly explicit comparison label."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "source.png"
        image = Image.new("RGBA", (5, 1))
        image.putdata([(20, 40, 60, a) for a in (0, 1, 2, 255, 0)])
        image.save(self.source)
        self.original = self.source.read_bytes()

    def tearDown(self):
        self.temporary.cleanup()

    def test_probe_declares_strict_comparison_without_changing_boxes(self):
        result = inspect(self.source)
        self.assertEqual(result["alpha_bbox_comparison"], "alpha > threshold")
        self.assertEqual(result["alpha_bbox"]["1"], (2, 0, 4, 1))
        self.assertEqual(result["alpha_bbox"]["250"], (3, 0, 4, 1))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_crop_default_includes_alpha_one(self):
        output = self.directory / "crop.png"
        result = crop_asset(self.source, output, [0, 0, 50, 10], padding=0)
        self.assertEqual(result["crop_xywh"], [1, 0, 3, 1])
        self.assertEqual(result["target_xywh"], [10, 0, 30, 10])
        with Image.open(output) as cropped:
            self.assertEqual(cropped.getchannel("A").tobytes(), bytes([1, 2, 255]))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_crop_two_corresponds_to_probe_one_but_records_discarded_mass(self):
        output = self.directory / "crop.png"
        result = crop_asset(self.source, output, [0, 0, 50, 10], threshold=2, padding=0)
        self.assertEqual(result["crop_xywh"], [2, 0, 2, 1])
        self.assertEqual(result["discarded_alpha_mass"], 1)
        with Image.open(output) as cropped:
            self.assertEqual(cropped.getchannel("A").tobytes(), bytes([2, 255]))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_rgb_is_not_claimed_as_a_transparent_cutout(self):
        source = self.directory / "rgb.png"
        Image.new("RGB", (2, 1)).save(source)
        result = inspect(source)
        self.assertIsNone(result["alpha_extrema"])
        self.assertEqual(result["alpha_bbox"], {})


if __name__ == "__main__":
    unittest.main()
