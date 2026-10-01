"""SPDX-License-Identifier: MIT. Source identity and declared slot boundaries."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pptx_backend.protected_sources import (
    check_canvas,
    check_slot,
    png_source,
    resolve_bindings,
)
from protected_fixtures import corrupt_png, fixture


class ProtectedSourcesTest(unittest.TestCase):
    """Sources stay byte-identical; invalid contracts fail before geometry use."""

    def setUp(self):
        temporary = Path(__file__).parents[1] / "tmp"
        temporary.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary)
        self.addCleanup(self.temp.cleanup)
        self.root, self.plan, _ = fixture(self.temp.name)
        self.declaration = self.plan["protected_media"][0]

    def test_static_png_identity(self):
        source = png_source(self.root, self.declaration)
        self.assertEqual(source["size"], (4, 2))
        self.assertEqual(source["body"], (self.root / "original.png").read_bytes())

    def test_changed_source(self):
        self.declaration["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "protected_source_changed"):
            png_source(self.root, self.declaration)

    def test_invalid_digest(self):
        self.declaration["sha256"] = "short"
        with self.assertRaisesRegex(ValueError, "protected_hash_format"):
            png_source(self.root, self.declaration)

    def test_source_escape(self):
        self.declaration["file"] = "../escape.png"
        with self.assertRaisesRegex(ValueError, "path_outside_project"):
            png_source(self.root, self.declaration)

    def test_source_byte_limit(self):
        with patch("pptx_backend.protected_sources.MAX_SOURCE_BYTES", 2):
            with self.assertRaisesRegex(ValueError, "protected_source_size_limit"):
                png_source(self.root, self.declaration)

    def test_source_pixel_limit(self):
        with patch("pptx_backend.protected_sources.MAX_SOURCE_PIXELS", 2):
            with self.assertRaisesRegex(ValueError, "protected_source_pixel_limit"):
                png_source(self.root, self.declaration)

    def test_crc_valid_corrupt_pixels(self):
        body = corrupt_png()
        (self.root / "original.png").write_bytes(body)
        self.declaration["sha256"] = hashlib.sha256(body).hexdigest()
        with self.assertRaisesRegex(ValueError, "protected_invalid_png"):
            png_source(self.root, self.declaration)

    def test_jpeg_with_png_filename(self):
        Image.new("RGB", (2, 2)).save(self.root / "original.png", format="JPEG")
        self.declaration["sha256"] = hashlib.sha256(
            (self.root / "original.png").read_bytes()
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "protected_static_png_required"):
            png_source(self.root, self.declaration)

    def test_duplicate_identity(self):
        self.plan["protected_media"].append(self.declaration.copy())
        with self.assertRaisesRegex(ValueError, "protected_duplicate_binding"):
            resolve_bindings(self.root, self.plan)

    def test_missing_object(self):
        self.declaration["object_id"] = "absent"
        with self.assertRaisesRegex(ValueError, "protected_object_not_unique"):
            resolve_bindings(self.root, self.plan)

    def test_wrong_kind(self):
        self.plan["slides"][0]["elements"][0]["kind"] = "video"
        with self.assertRaisesRegex(ValueError, "protected_file_or_kind_mismatch"):
            resolve_bindings(self.root, self.plan)

    def test_cover_declared(self):
        self.plan["slides"][0]["elements"][0]["fit"] = "cover"
        with self.assertRaisesRegex(
            ValueError, "protected_contain_slide_picture_required"
        ):
            resolve_bindings(self.root, self.plan)

    def test_transform_declared(self):
        self.plan["slides"][0]["elements"][0]["rotation"] = 0
        with self.assertRaisesRegex(ValueError, "protected_transform_unsupported"):
            resolve_bindings(self.root, self.plan)

    def test_canvas_bool(self):
        with self.assertRaisesRegex(ValueError, "protected_canvas_invalid"):
            check_canvas([True, 300])

    def test_canvas_enormous_integer(self):
        with self.assertRaisesRegex(ValueError, "protected_canvas_invalid"):
            check_canvas([10**400, 300])

    def test_slot_nan(self):
        with self.assertRaisesRegex(ValueError, "protected_slot_invalid"):
            check_slot([float("nan"), 0, 100, 100], [400, 300])

    def test_slot_outside(self):
        with self.assertRaisesRegex(ValueError, "protected_slot_outside_canvas"):
            check_slot([-1, 0, 100, 100], [400, 300])

    def test_slot_empty(self):
        with self.assertRaisesRegex(ValueError, "protected_slot_invalid"):
            check_slot([0, 0, 0, 100], [400, 300])


if __name__ == "__main__":
    unittest.main()
