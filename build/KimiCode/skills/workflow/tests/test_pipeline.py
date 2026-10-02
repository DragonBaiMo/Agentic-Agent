"""SPDX-License-Identifier: MIT

Real existing-asset pipeline: new plan, import, compile, build, reopen and hand over.
Requires npm ci and the example fonts. Does not call any image model.
"""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from deliver_project import package
from project import initialize
from project_io import compile_plan, digest, read_json
from record_asset import record
from review_assets import moved_view, viewer
from review_psd import hide_view, render
from verify_psd import check_structure

TMP = ROOT / "tmp/pipeline-tests"
TMP.mkdir(parents=True, exist_ok=True)


def setup_project(destination):
    """Migrate the real sample recipe through the same bridge a new project uses."""
    manifest = read_json(ROOT / "examples/future-lab.json")
    copy = [{"id": f"copy-{i}", "value": item["value"]} for i, item in enumerate(manifest["text"])]
    layers = [{"id": f"art-{i}", "type": "image", "kind": "background" if i == 0 else "object",
               "alpha": item["expect_alpha"], "owns": item["name"], "copy_ids": [],
               **{key: item[key] for key in ("name", "group", "crop", "destination")}}
              for i, item in enumerate(manifest["art"])]
    layers.extend({"id": f"type-{i}", "type": "native_text", "copy_id": f"copy-{i}",
                   "name": item["name"], "group": item["group"],
                   "style": {key: value for key, value in item.items() if key not in ("name", "group", "value")}}
                  for i, item in enumerate(manifest["text"]))
    plan = {"entry": "existing_design", "output_name": "future-laboratory", "canvas": [1024, 1536],
            "direction": "Historical asset reconstruction test", "copy": copy, "layers": layers,
            "fonts": manifest["fonts"], "groups": manifest["groups"], "master": {}}
    plan_file = destination / "input-plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False))
    root = destination / "project"
    initialize(root, plan_file)
    assets = ROOT / "assets/future-lab"
    record(root, "master", assets / "reference-preview.png", "conversation_history", "prior_delivered_artifact")
    for i, item in enumerate(manifest["art"]):
        record(root, f"art-{i}", assets / item["file"], "conversation_history", "prior_image_generation")
    compile_plan(root)
    build = root / "builds/B01"
    subprocess.run(["node", str(ROOT / "scripts/assemble.cjs"), "--config", str(root / "manifest.json"),
                    "--out", str(build)], check=True, capture_output=True, timeout=60)
    return root, build


class PipelineTests(unittest.TestCase):
    """Reuse one immutable PSD across independent read/packaging assertions."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=TMP)
        cls.root, cls.build = setup_project(Path(cls.temporary.name))
        cls.psd = cls.build / "future-laboratory.psd"

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_true_psd_and_portable_source_package(self):
        handover = self.root / "START_HERE.md"
        handover.write_text("Replay verified; no new image generation or Photoshop GUI validation.")
        output = self.root / "source.zip"
        result = package(self.root, self.build, handover, output, "final")
        self.assertEqual(result["crc_and_hashes"], "passed")
        with zipfile.ZipFile(output) as archive:
            self.assertIn("output/future-laboratory.psd", archive.namelist())
            self.assertIn("manifest.json", archive.namelist())
            report = json.loads(archive.read("output/technical-check.json"))
            self.assertEqual(len(report["layers"]), 11)
            self.assertEqual(report["native_type_layers"], 8)
            self.assertFalse(json.loads(archive.read("DELIVERY_STATUS.json"))["user_visual_approval"])

    def test_viewer_exports_real_layers(self):
        master = self.root / read_json(self.root / "plan.json")["master"]["file"]
        result = viewer(self.psd, master, self.root / "review/viewer")
        self.assertEqual(result["layers"], 11)
        self.assertTrue(Path(result["viewer"]).is_file())

    def test_move_is_diagnostic_only(self):
        before = digest(self.psd)
        destination = self.root / "review/moved.png"
        moved_view(self.psd, "核心 / 橙色玻璃能量球", destination)
        self.assertEqual(digest(self.psd), before)
        self.assertTrue(destination.is_file())

    def test_hide_real_leaf_preserves_unrelated_type_pixels(self):
        psd = PSDImage.open(self.psd)
        check_structure(psd, read_json(self.root / "manifest.json"))
        before = render(psd)
        destination = self.root / "review/hidden-ring.png"
        destination.parent.mkdir(exist_ok=True)
        hide_view(psd, "装置 / 钴蓝陶瓷与拉丝金属", destination)
        with Image.open(destination) as image:
            # NOTE: The title region is above the ring and must remain pixel-identical.
            self.assertEqual(image.crop((0, 0, 1024, 370)).tobytes(),
                             before.crop((0, 0, 1024, 370)).tobytes())
        self.assertFalse(psd.is_updated())

    def test_package_rejects_asset_path_escape(self):
        file = self.root / "manifest.json"
        before = file.read_bytes()
        manifest = json.loads(before)
        manifest["art"][0]["file"] = "../plan.json"
        file.write_text(json.dumps(manifest))
        handover = self.root / "safety-handover.md"
        handover.write_text("Safety test only")
        try:
            with self.assertRaisesRegex(ValueError, "basename"):
                package(self.root, self.build, handover, self.root / "unsafe.zip", "review")
        finally:
            file.write_bytes(before)

    def test_package_rejects_output_path_escape(self):
        file = self.root / "manifest.json"
        before = file.read_bytes()
        manifest = json.loads(before)
        manifest["name"] = "../outside"
        file.write_text(json.dumps(manifest))
        try:
            with self.assertRaisesRegex(ValueError, "basename"):
                package(self.root, self.build, self.root / "unused.md", self.root / "unused.zip", "review")
        finally:
            file.write_bytes(before)


if __name__ == "__main__":
    unittest.main()
