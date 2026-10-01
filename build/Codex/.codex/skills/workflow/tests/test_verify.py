"""SPDX-License-Identifier: MIT

Focused verifier regressions. No artwork similarity tests or network calls.
Run: python -m unittest discover -s tests -p 'test_*.py'
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from probe_assets import inspect
from review_psd import hide_view, make_review
from verify_psd import require, ordered, arguments, check_layer

TMP = Path(__file__).parents[1] / "tmp/python-tests"
TMP.mkdir(parents=True, exist_ok=True)


class VerifyTests(unittest.TestCase):
    """Exercise error handling that cannot be left to a visual reviewer."""

    def test_require_survives_optimization(self):
        with self.assertRaises(ValueError):
            require(False, "intentional_failure")

    def test_order_matches_mixed_manifest(self):
        config = {"art": [{"name": "front", "group": "main", "z": 10}],
                  "text": [{"name": "back", "group": "main", "z": 1}]}
        self.assertEqual([item["name"] for item in ordered(config, "main")], ["back", "front"])

    def test_alpha_probe_opaque_and_translucent(self):
        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            rgb, rgba = Path(directory) / "rgb.png", Path(directory) / "rgba.png"
            Image.new("RGB", (16, 16), "red").save(rgb)
            Image.new("RGBA", (16, 16), (1, 2, 3, 80)).save(rgba)
            self.assertIsNone(inspect(rgb)["alpha_extrema"])
            self.assertEqual(inspect(rgba)["alpha_extrema"], [80, 80])

    def test_review_and_toggle_restore_visibility(self):
        psd = PSDImage.new("RGB", (16, 16))
        layer = PixelLayer.frompil(Image.new("RGBA", (16, 16), "red"), psd, "front")
        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            destination = Path(directory)
            master = destination / "master.png"
            Image.new("RGB", (16, 16), "blue").save(master)
            result = make_review(psd, destination, master, ["front"])
            self.assertTrue(layer.visible)
            self.assertTrue((destination / result["comparison"]).is_file())
            self.assertTrue((destination / "hidden-1.png").is_file())

    def test_hidden_layer_stays_hidden(self):
        psd = PSDImage.new("RGB", (16, 16))
        layer = PixelLayer.frompil(Image.new("RGBA", (16, 16), "red"), psd, "front")
        layer.visible = False
        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            hide_view(psd, "front", Path(directory) / "hidden.png")
        self.assertFalse(layer.visible)

    def test_unknown_toggle_fails(self):
        psd = PSDImage.new("RGB", (16, 16))
        with self.assertRaises(ValueError):
            hide_view(psd, "missing", TMP / "unused.png")

    def test_master_requires_review_switch(self):
        with patch.object(sys, "argv", ["verify", "--psd", "a", "--config", "b", "--out", "c", "--master", "d"]):
            with self.assertRaises(ValueError):
                arguments()

    def test_text_is_bound_to_layer_identity(self):
        layer = Mock(kind="type", text="wrong", visible=True, opacity=255)
        with self.assertRaisesRegex(ValueError, "text"):
            check_layer(layer, {"name": "specific-title", "value": "exact"})

    def test_pixel_layer_cannot_claim_native_type(self):
        layer = Mock(kind="pixel")
        with self.assertRaisesRegex(ValueError, "type"):
            check_layer(layer, {"name": "title", "value": "exact"})

    def test_missing_pixels_fails(self):
        layer = Mock(kind="pixel", visible=True, opacity=255)
        layer.blend_mode.value = b"norm"
        layer.topil.return_value = None
        with self.assertRaisesRegex(ValueError, "pixels"):
            check_layer(layer, {"name": "object"})


if __name__ == "__main__":
    unittest.main()
