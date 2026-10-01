"""SPDX-License-Identifier: MIT

Regress material routing, alpha facts, provenance and environment diagnostics.
Fixtures are diagnostic pixels, never substitute poster assets.
"""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from environment_check import inspect_environment, selected_fonts
from execution_record import execution_result, public_arguments
from probe_assets import alpha_distribution
from project import initialize
from project_io import digest, read_json, write_json
from record_asset import record
from visual_job import prepare

TMP = ROOT / "tmp/production-support-tests"
TMP.mkdir(parents=True, exist_ok=True)


class ProductionSupportTests(unittest.TestCase):
    """Use an isolated project for every public helper and rejected-input path."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TMP)
        self.directory = Path(self.temporary.name)
        self.project = self.directory / "project"
        initialize(self.project, ROOT / "examples/new-poster.plan.json")
        self.source = self.directory / "source.png"
        Image.new("RGBA", (16, 16), (20, 80, 120, 254)).save(self.source)
        record(self.project, "master", self.source, "user_supplied", "upload")
        self.arguments = self.directory / "public.json"
        write_json(self.arguments, {"prompt": "Actual submitted task", "referenced_image_paths": ["source.png"],
                                    "transparent_background": True})

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_plan_keeps_two_unapproved_checkpoints(self):
        interaction = read_json(self.project / "plan.json")["interaction"]
        self.assertEqual(interaction["mode"], "staged")
        self.assertEqual(interaction["stop_at"], ["master", "layer_architecture"])
        self.assertFalse(interaction["user_visual_approval"])

    def test_existing_autonomous_plan_is_not_forcibly_changed_or_approved(self):
        plan = read_json(self.project / "plan.json")
        plan["interaction"] = {"mode": "autonomous", "stop_at": [], "user_visual_approval": False}
        input_file = self.directory / "autonomous.json"
        write_json(input_file, plan)
        target = self.directory / "continued"
        initialize(target, input_file)
        self.assertEqual(read_json(target / "plan.json")["interaction"], plan["interaction"])

    def test_typography_uses_its_own_material_template(self):
        job = self.project / "jobs/title"
        result = prepare(self.project, "headline", job)
        self.assertEqual(result["prompt_template"], "typography.txt")
        self.assertIn("夜航", (job / "DRAW.txt").read_text())
        self.assertNotIn("NIGHT VOYAGE", (job / "DRAW.txt").read_text())

    def test_glass_uses_transmission_template_and_real_reference(self):
        job = self.project / "jobs/glass"
        result = prepare(self.project, "bottle", job)
        self.assertEqual(result["prompt_template"], "glass.txt")
        self.assertEqual(digest(job / result["reference_file"]), digest(self.source))

    def test_alpha_distribution_distinguishes_empty_border_and_dense_body(self):
        alpha = Image.new("L", (5, 1))
        alpha.putdata([0, 1, 229, 254, 255])
        self.assertEqual(alpha_distribution(alpha), {"transparent_0": 1, "translucent_1_229": 2,
                         "near_opaque_230_255": 2, "opaque_255": 1, "nonzero": 4,
                         "near_opaque_fraction_of_nonzero": 0.5})

    def test_fully_empty_alpha_has_no_division_score(self):
        result = alpha_distribution(Image.new("L", (2, 2), 0))
        self.assertIsNone(result["near_opaque_fraction_of_nonzero"])
        self.assertEqual(result["nonzero"], 0)

    def test_actual_arguments_remain_separate_from_prepared_prompt(self):
        job = self.project / "jobs/title"
        prepare(self.project, "headline", job)
        before = digest(job / "request.json")
        receipt = record(self.project, "headline", self.source, "generated", "model", job,
                         execution=self.arguments)["receipt"]
        self.assertEqual(receipt["request"]["status"], "prepared_not_executed")
        self.assertEqual(receipt["execution"]["status"], "result_recorded")
        self.assertEqual(receipt["execution"]["public_arguments"]["submitted_prompt"], "Actual submitted task")
        self.assertEqual(receipt["execution"]["public_arguments"]["submitted_references"][0]["sha256"], digest(self.source))
        self.assertEqual(receipt["execution"]["backend_binding_observed"], "not_exposed")
        self.assertEqual(digest(job / "request.json"), before)

    def test_unknown_execution_fields_are_rejected_before_asset_copy(self):
        write_json(self.arguments, {"prompt": "task", "transparent_background": True, "api_key": "diagnostic-sentinel"})
        with self.assertRaisesRegex(ValueError, "public_fields"):
            public_arguments(self.arguments)

    def test_missing_execution_reference_is_not_claimed_as_submitted(self):
        write_json(self.arguments, {"prompt": "task", "transparent_background": True, "referenced_image_paths": ["missing.png"]})
        with self.assertRaisesRegex(ValueError, "reference_missing"):
            public_arguments(self.arguments)

    def test_execution_requires_boolean_transparency(self):
        write_json(self.arguments, {"prompt": "task", "transparent_background": "true"})
        with self.assertRaisesRegex(ValueError, "transparency"):
            public_arguments(self.arguments)

    def test_import_is_not_relabelled_as_a_model_call(self):
        with self.assertRaisesRegex(ValueError, "generated_origin"):
            execution_result(self.source, "conversation_history", "prior_tool", "not_exposed", self.arguments)

    def test_unexposed_public_arguments_stay_unexposed(self):
        result = execution_result(self.source, "generated", "model", "not_exposed")
        self.assertEqual(result["public_arguments"], "not_recorded")
        self.assertEqual(result["call_id"], "not_exposed")

    def test_font_environment_override_and_missing_identity(self):
        plan = self.directory / "font-plan.json"
        write_json(plan, {"fonts": [{"path": "missing.ttf", "env": "POSTER_TEST_FONT", "family": "Example", "postscript": "Example"}]})
        with patch.dict("os.environ", {"POSTER_TEST_FONT": str(self.source)}):
            result = selected_fonts(plan)
        self.assertTrue(result[0]["exists"])
        self.assertFalse(result[0]["font_identity_verified"])

    def test_missing_font_is_reported(self):
        plan = self.directory / "font-plan.json"
        write_json(plan, {"fonts": [{"path": "missing.ttf", "family": "Example"}]})
        self.assertFalse(selected_fonts(plan)[0]["exists"])

    def test_missing_node_is_reported_without_install(self):
        with patch("environment_check.shutil.which", return_value=None):
            result = inspect_environment()
        self.assertEqual(result["node_runtime"], {"available": False})

    def test_node_timeout_is_bounded_and_reported(self):
        with patch("environment_check.shutil.which", return_value="node"), patch("environment_check.subprocess.run", side_effect=subprocess.TimeoutExpired("node", 15)):
            result = inspect_environment()
        self.assertEqual(result["node_runtime"]["error_type"], "TimeoutExpired")

    def test_actual_runtime_can_load_locked_node_dependencies(self):
        result = inspect_environment()
        self.assertTrue(result["node_runtime"]["supported"])
        self.assertTrue(result["node_runtime"]["dependencies"][0]["loadable"])
        self.assertTrue(result["node_runtime"]["dependencies"][1]["loadable"])


if __name__ == "__main__":
    unittest.main()
