"""SPDX-License-Identifier: MIT

Exercise the new-project bridge, provenance, copy filtering and reversible state.
Tests use existing images or tiny diagnostic fixtures, never new generated art.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from project import initialize, snapshot, restore, status
from project_io import compile_plan, inside, read_json, write_json
from record_asset import record
from visual_job import prepare
from review_assets import gallery
from deliver_project import package

TMP = ROOT / "tmp/project-tests"
TMP.mkdir(parents=True, exist_ok=True)


class ProjectTests(unittest.TestCase):
    """Keep independent temporary projects so failures cannot alter production assets."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.root = Path(self.temporary.name) / "project"
        self.plan_file = ROOT / "examples/new-poster.plan.json"
        initialize(self.root, self.plan_file)
        self.source = Path(self.temporary.name) / "source.png"
        Image.new("RGBA", (32, 40), (20, 80, 160, 180)).save(self.source)

    def tearDown(self):
        self.temporary.cleanup()

    def test_start_status_and_collision(self):
        result = status(self.root)
        self.assertFalse(result["master_exists"])
        self.assertEqual(len(result["pending_images"]), 5)
        self.assertEqual(result["native_text_roles"], ["caption"])
        with self.assertRaises(ValueError):
            initialize(self.root, self.plan_file)

    def test_new_master_prompt_has_complete_copy(self):
        job = self.root / "jobs/design-01"
        result = prepare(self.root, "master", job)
        prompt = (job / "DRAW.txt").read_text()
        self.assertIn("夜航", prompt)
        self.assertIn("EAU DE PARFUM · 50 mL", prompt)
        self.assertEqual(result["status"], "prepared_not_executed")
        self.assertIsNone(result["reference_file"])

    def test_layer_job_filters_unowned_text_and_copies_reference(self):
        record(self.root, "master", self.source, "user_supplied", "upload")
        job = self.root / "jobs/bottle-01"
        result = prepare(self.root, "bottle", job)
        prompt = (job / "DRAW.txt").read_text()
        self.assertIn("NIGHT VOYAGE", prompt)
        self.assertNotIn("EAU DE PARFUM", prompt)
        self.assertNotIn("夜航", prompt)
        self.assertTrue((job / result["reference_file"]).is_file())
        with self.assertRaises(ValueError):
            prepare(self.root, "bottle", job)

    def test_missing_reference_and_native_task_fail(self):
        with self.assertRaises(ValueError):
            prepare(self.root, "bottle", self.root / "jobs/missing")
        with self.assertRaises(ValueError):
            prepare(self.root, "caption", self.root / "jobs/native")

    def test_rejected_asset_does_not_replace_active(self):
        record(self.root, "bottle", self.source, "conversation_history", "model")
        before = read_json(self.root / "plan.json")["layers"][2]["file"]
        result = record(self.root, "bottle", self.source, "conversation_history", "model", status="rejected", reason="bad edge")
        after = read_json(self.root / "plan.json")["layers"][2]["file"]
        self.assertEqual(before, after)
        self.assertTrue((self.root / result["receipt"]["file"]).is_file())

    def test_generated_result_requires_prepared_matching_task(self):
        with self.assertRaises(ValueError):
            record(self.root, "bottle", self.source, "generated", "model")
        record(self.root, "master", self.source, "user_supplied", "upload")
        job = self.root / "jobs/bottle"
        prepare(self.root, "bottle", job)
        with self.assertRaises(ValueError):
            record(self.root, "headline", self.source, "generated", "model", job)
        result = record(self.root, "bottle", self.source, "generated", "model", job)
        self.assertEqual(result["receipt"]["call_id"], "not_exposed")

    def test_snapshot_restore_preserves_images(self):
        saved = snapshot(self.root)["snapshot"]
        result = record(self.root, "master", self.source, "user_supplied", "upload")
        restore(self.root, saved)
        self.assertFalse(status(self.root)["master_exists"])
        self.assertTrue((self.root / result["receipt"]["file"]).is_file())
        with self.assertRaises(ValueError):
            restore(self.root, self.root)

    def test_compile_maps_copy_and_rejects_missing_assets(self):
        with self.assertRaises(ValueError):
            compile_plan(self.root)
        plan = read_json(self.root / "plan.json")
        plan["layers"] = [plan["layers"][0], plan["layers"][-1]]
        write_json(self.root / "plan.json", plan)
        record(self.root, "background", self.source, "user_supplied", "upload")
        result = compile_plan(self.root)
        manifest = read_json(result["manifest"])
        self.assertEqual(manifest["text"][0]["value"], "EAU DE PARFUM · 50 mL")
        self.assertEqual(manifest["art"][0]["source_size"], [32, 40])
        self.assertEqual(manifest["art"][0]["destination"], [0, 0, 1080, 1350])

    def test_gallery_and_diagnostic_package(self):
        image = self.root / "review/candidates.png"
        gallery([self.source, self.source], image)
        with Image.open(image) as opened:
            self.assertEqual(opened.size, (800, 600))
        handover = self.root / "START_HERE.md"
        handover.write_text("Diagnostic only; no PSD completed.")
        result = package(self.root, None, handover, self.root / "diagnostic.zip", "diagnostic")
        self.assertEqual(result["crc_and_hashes"], "passed")

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            inside(self.root, "../outside")


if __name__ == "__main__":
    unittest.main()
