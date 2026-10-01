"""SPDX-License-Identifier: MIT

Verify exclusive output creation, no input writes, and explicit CLI failures.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixtures import SHEET, WORKBOOK, pair, workbook

import restore_chart_dependencies as cli
from bounded_pptx.opc import write_package


class CliTests(unittest.TestCase):
    """Use private fixture directories and simulated I/O errors without permissions changes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source, authored = pair()
        self.source = self.root / "source.pptx"
        self.source.write_bytes(write_package(source))
        self.authored = self.root / "authored.pptx"
        self.authored.write_bytes(write_package(authored))
        self.output = self.root / "new"
        self.argv = [
            "--source",
            str(self.source),
            "--authored",
            str(self.authored),
            "--out-dir",
            str(self.output),
        ]

    def test_cli_success_and_unchanged_inputs(self):
        old_source, old_authored = self.source.read_bytes(), self.authored.read_bytes()
        self.assertEqual(cli.main(self.argv), 0)
        self.assertEqual(self.source.read_bytes(), old_source)
        self.assertEqual(self.authored.read_bytes(), old_authored)
        self.assertTrue((self.output / "candidate.pptx").is_file())
        proof = json.loads((self.output / "proof.json").read_text())
        self.assertTrue(proof["authored_slide_and_notes_bytes_unchanged"])

    def test_existing_directory_is_never_reused(self):
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_text("original")
        self.assertEqual(cli.main(self.argv), 2)
        self.assertEqual(sentinel.read_text(), "original")
        self.assertFalse((self.output / "candidate.pptx").exists())

    def test_dangling_output_symlink_is_rejected(self):
        self.output.symlink_to(self.root / "missing", target_is_directory=True)
        self.assertEqual(cli.main(self.argv), 2)
        self.assertTrue(self.output.is_symlink())

    def test_missing_input_reports_io_failure(self):
        self.source.unlink()
        self.assertEqual(cli.main(self.argv), 3)
        self.assertFalse(self.output.exists())

    def test_symlink_loop_reports_io_failure(self):
        self.source.unlink()
        self.source.symlink_to(self.source)
        self.assertEqual(cli.main(self.argv), 3)
        self.assertFalse(self.output.exists())

    def test_same_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source_equals_authored"):
            cli.run(self.source, self.source, self.output)

    def test_source_directory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "input_not_file"):
            cli.run(self.root, self.authored, self.output)

    def test_invalid_zip_has_no_output(self):
        self.source.write_bytes(b"broken")
        self.assertEqual(cli.main(self.argv), 2)
        self.assertFalse(self.output.exists())

    def test_candidate_write_failure_cleans_partial_output(self):
        with patch.object(
            Path, "write_bytes", side_effect=PermissionError("simulated disk denial")
        ):
            self.assertEqual(cli.main(self.argv), 3)
        self.assertFalse(self.output.exists())
        self.assertTrue(self.source.exists())

    def test_receipt_write_failure_cleans_partial_output(self):
        with patch.object(
            Path, "write_text", side_effect=OSError("simulated disk full")
        ):
            self.assertEqual(cli.main(self.argv), 3)
        self.assertFalse(self.output.exists())

    def test_missing_output_parent_does_not_create_ancestors(self):
        with self.assertRaises(FileNotFoundError):
            cli.run(self.source, self.authored, self.root / "absent" / "new")
        self.assertFalse((self.root / "absent").exists())

    def changed_source_restore(self, source, authored):
        """Simulate another process changing the source after semantic validation."""
        result = self.actual_restore(source, authored)
        self.source.write_bytes(b"changed outside this invocation")
        return result

    def test_detects_source_change_before_output(self):
        self.actual_restore = cli.restore_dependencies
        with patch.object(
            cli, "restore_dependencies", side_effect=self.changed_source_restore
        ):
            self.assertEqual(cli.main(self.argv), 2)
        self.assertFalse(self.output.exists())

    def test_subprocess_missing_arguments_exit_two(self):
        result = subprocess.run(
            [sys.executable, str(Path(cli.__file__))],
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"--source", result.stderr)

    def test_subprocess_success_records_machine_status(self):
        result = subprocess.run(
            [sys.executable, str(Path(cli.__file__)), *self.argv],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)["event"], "dependencies_restored")

    def test_subprocess_bad_zip_records_blocked_status(self):
        self.source.write_bytes(b"broken")
        result = subprocess.run(
            [sys.executable, str(Path(cli.__file__)), *self.argv],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["reason"], "invalid_zip")

    def test_subprocess_huge_exponent_is_bounded_and_has_no_output(self):
        source, _ = pair()
        book = workbook()
        book[SHEET] = book[SHEET].replace(b">12<", b">1e" + b"9" * 100 + b"<")
        source[WORKBOOK] = write_package(book)
        self.source.write_bytes(write_package(source))
        result = subprocess.run(
            [sys.executable, str(Path(cli.__file__)), *self.argv],
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["reason"], "numeric_value_limit")
        self.assertFalse(self.output.exists())

    def test_subprocess_deep_xml_is_bounded_and_has_no_output(self):
        source, _ = pair()
        source["deep.xml"] = b"<x>" * 1000 + b"</x>" * 1000
        self.source.write_bytes(write_package(source))
        result = subprocess.run(
            [sys.executable, str(Path(cli.__file__)), *self.argv],
            capture_output=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["reason"], "xml_depth_limit")
        self.assertFalse(self.output.exists())
