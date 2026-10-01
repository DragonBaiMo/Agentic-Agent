"""SPDX-License-Identifier: MIT

Test wrapper failure contracts using a controlled finalizer double.
These tests never claim that the double validates an actual presentation.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixtures import pair

from bounded_pptx.opc import write_package

ROOT = Path(__file__).resolve().parents[1]


class WrapperTests(unittest.TestCase):
    """Prove that failed or changed-input runs leave no final deliverable."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source, authored = pair()
        self.source = self.root / "source.pptx"
        self.source.write_bytes(write_package(source))
        self.authored = self.root / "authored.pptx"
        self.authored.write_bytes(write_package(authored))
        self.requirements = self.root / "requirements.json"
        self.requirements.write_text(
            json.dumps({"slideCount": 1, "slideSizeEmu": "10,10", "fonts": ["Fixture"]})
        )
        self.output = self.root / "new"
        self.skill = self.root / "test-skill"
        (self.skill / "container_tools").mkdir(parents=True)
        self.helper = self.skill / "container_tools/artifact_tool_utils.mjs"
        self.helper.write_text(
            'export async function finalizePresentation(){throw new Error("test_finalizer_reject")}'
        )
        self.env = dict(
            os.environ,
            RUNTIME_PYTHON=sys.executable,
            PRESENTATIONS_SKILL_DIR=str(self.skill),
            RUNTIME_NODE_MODULES=str(self.root),
        )
        self.command = [
            os.environ["CODEX_PRIMARY_RUNTIME_NODE"],
            str(ROOT / "finalize_restoration.mjs"),
            "--source",
            str(self.source),
            "--authored",
            str(self.authored),
            "--out-dir",
            str(self.output),
            "--requirements",
            str(self.requirements),
        ]

    def run_wrapper(self):
        return subprocess.run(
            self.command, env=self.env, capture_output=True, timeout=15, check=False
        )

    def test_finalizer_rejection_has_no_final(self):
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"test_finalizer_reject", result.stderr)
        self.assertFalse((self.output / "output/final.pptx").exists())

    def test_finalizer_partial_write_is_removed(self):
        self.helper.write_text(
            'import fs from "node:fs/promises";export async function finalizePresentation(o){await fs.writeFile(o.finalPath,"partial");throw new Error("test_failed_after_write")}'
        )
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"test_failed_after_write", result.stderr)
        self.assertFalse((self.output / "output/final.pptx").exists())

    def test_source_change_after_finalization_removes_final(self):
        self.helper.write_text(
            'import fs from "node:fs/promises";export async function finalizePresentation(o){await fs.copyFile(o.candidatePath,o.finalPath);await fs.writeFile(o.fontPolicy.referencePath,"external-change")}'
        )
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"identity_changed", result.stderr)
        self.assertFalse((self.output / "output/final.pptx").exists())
        self.assertEqual(self.source.read_text(), "external-change")

    def test_bad_source_is_blocked_before_finalizer(self):
        self.source.write_bytes(b"broken")
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"invalid_zip", result.stderr)
        self.assertNotIn(b"test_finalizer_reject", result.stderr)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_untouched(self):
        final = self.output / "output/final.pptx"
        final.parent.mkdir(parents=True)
        final.write_bytes(b"keep")
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(final.read_bytes(), b"keep")

    def test_invalid_requirements_never_deliver(self):
        self.requirements.write_text("{}")
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"invalid_requirements", result.stderr)
        self.assertFalse((self.output / "output/final.pptx").exists())

    def test_missing_runtime_never_writes(self):
        self.env["RUNTIME_PYTHON"] = "relative"
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"missing_runtime", result.stderr)
        self.assertFalse(self.output.exists())
