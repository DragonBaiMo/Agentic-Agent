"""SPDX-License-Identifier: MIT. CLI failure and exclusive receipt publication."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from protected_fixtures import fixture
from verify_protected_media import bounded_json, write_receipt

SCRIPT = Path(__file__).parents[1] / "scripts/verify_protected_media.py"


class ProtectedCliTest(unittest.TestCase):
    """Exit failures do not modify source PPTX/PNG or leave successful receipts."""

    def setUp(self):
        temporary = Path(__file__).parents[1] / "tmp"
        temporary.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary)
        self.addCleanup(self.temp.cleanup)
        self.root, self.plan, _ = fixture(self.temp.name)

    def run_cli(self, output="result.json"):
        """Execute the actual command, bounded to ten seconds."""
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project",
                str(self.root),
                "--plan",
                "deck.json",
                "--pptx",
                "source.pptx",
                "--out",
                output,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_real_command_success_preserves_source(self):
        before = hashlib.sha256((self.root / "source.pptx").read_bytes()).hexdigest()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "result.json").read_text())
        self.assertEqual(receipt["pptx_sha256"], before)
        self.assertEqual(
            hashlib.sha256((self.root / "source.pptx").read_bytes()).hexdigest(), before
        )

    def test_invalid_plan_has_no_receipt(self):
        self.plan["canvas"] = [1, 1]
        (self.root / "deck.json").write_text(json.dumps(self.plan))
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected_slot_outside_canvas", result.stderr)
        self.assertFalse((self.root / "result.json").exists())

    def test_existing_receipt_not_replaced(self):
        (self.root / "result.json").write_text("retained")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / "result.json").read_text(), "retained")
        self.assertEqual(list(self.root.glob(".protected-*")), [])

    def test_source_as_output_not_replaced(self):
        before = (self.root / "source.pptx").read_bytes()
        result = self.run_cli("source.pptx")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / "source.pptx").read_bytes(), before)

    def test_publication_failure_cleans_private_partial(self):
        with patch("verify_protected_media.os.link", side_effect=OSError("injected")):
            with self.assertRaisesRegex(OSError, "injected"):
                write_receipt(self.root / "result.json", {"status": "passed"})
        self.assertFalse((self.root / "result.json").exists())
        self.assertEqual(list(self.root.glob(".protected-*")), [])

    def test_oversized_json_rejected(self):
        with patch("verify_protected_media.MAX_JSON_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "protected_json_size_limit"):
                bounded_json(self.root / "deck.json")

    def test_non_object_json_rejected(self):
        (self.root / "deck.json").write_text("[]")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected_json_object_required", result.stderr)


if __name__ == "__main__":
    unittest.main()
