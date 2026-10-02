"""SPDX-License-Identifier: MIT

Media preflight boundaries; synthetic ZIPs are parser fixtures, not slide deliverables.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pptx_backend.media_preflight import CONTENT_NS, REL_NS, inspect_media

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
TMP = ROOT / "tmp/media-preflight-tests"
TMP.mkdir(parents=True, exist_ok=True)


def relation(kind, target="../media/clip.bin", external=False):
    """Construct one declared relation without ever contacting its target."""
    mode = ' TargetMode="External"' if external else ""
    return (f'<Relationships xmlns="{REL_NS}"><Relationship Id="rId2" '
            f'Type="{R}/{kind}" Target="{target}"{mode}/></Relationships>')


def write_fixture(path, *, relations=None, body="", extra=None, types=""):
    """Write only the minimal parseable package needed by the media inspection tests."""
    files = {
        "[Content_Types].xml": f'<Types xmlns="{CONTENT_NS}">{types}</Types>',
        "_rels/.rels": relation("officeDocument", "ppt/presentation.xml"),
        "ppt/presentation.xml": f'<p:presentation xmlns:p="{P}"/>',
        "ppt/slides/slide1.xml": f'<p:sld xmlns:p="{P}" xmlns:a="{A}">{body}</p:sld>',
    }
    if relations is not None:
        files["ppt/slides/_rels/slide1.xml.rels"] = relations
    files.update(extra or {})
    with ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


class MediaPreflightTests(unittest.TestCase):
    """Refuse media or unknown inputs before any destructive import/export path."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TMP)
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.pptx"

    def test_plain_png_and_unused_video_type_are_clear(self):
        write_fixture(self.source, relations=relation("image", "../media/poster.png"),
                      types='<Default Extension="mp4" ContentType="video/mp4"/>',
                      extra={"ppt/media/poster.png": b"not-decoded-in-this-preflight"})
        result = inspect_media(self.source)
        self.assertEqual(result["status"], "CLEAR")
        self.assertFalse(result["full_fidelity_verified"])

    def test_embedded_video_relation_does_not_need_extension(self):
        write_fixture(self.source, relations=relation("video"),
                      extra={"ppt/media/clip.bin": b"payload"})
        result = inspect_media(self.source)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["findings"][0]["target_present"])

    def test_external_video_is_not_fetched_or_printed(self):
        write_fixture(self.source, relations=relation("video", "https://invalid.example/secret", True))
        result = inspect_media(self.source)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["findings"][0]["mode"], "external")
        self.assertNotIn("secret", json.dumps(result))

    def test_external_audio_requires_unverified_support(self):
        write_fixture(self.source, relations=relation("audio", "https://invalid.example/a", True))
        self.assertEqual(inspect_media(self.source)["findings"][0]["media_kind"], "audio")

    def test_embedded_audio_blocks(self):
        write_fixture(self.source, relations=relation("audio"), extra={"ppt/media/clip.bin": b"a"})
        self.assertEqual(inspect_media(self.source)["status"], "BLOCKED")

    def test_ordinary_external_hyperlink_remains_clear(self):
        write_fixture(self.source, relations=relation("hyperlink", "https://invalid.example/a", True))
        self.assertEqual(inspect_media(self.source)["status"], "CLEAR")

    def test_playback_object_without_payload_blocks(self):
        write_fixture(self.source, body='<p:timing><p:video/></p:timing>')
        self.assertEqual(inspect_media(self.source)["findings"][0]["kind"], "playback_object")

    def test_strict_drawingml_video_object_blocks(self):
        write_fixture(self.source, body='<s:videoFile xmlns:s="http://purl.oclc.org/ooxml/drawingml/main"/>')
        self.assertEqual(inspect_media(self.source)["status"], "BLOCKED")

    def test_p14_media_object_blocks(self):
        write_fixture(self.source, body='<x:media xmlns:x="http://schemas.microsoft.com/office/powerpoint/2010/main"/>')
        self.assertEqual(inspect_media(self.source)["status"], "BLOCKED")

    def test_hidden_slide_object_is_not_skipped(self):
        write_fixture(self.source, extra={"ppt/slides/slide2.xml":
                      f'<p:sld xmlns:p="{P}" xmlns:a="{A}" show="0"><a:videoFile/></p:sld>'})
        self.assertEqual(inspect_media(self.source)["findings"][0]["part"], "ppt/slides/slide2.xml")

    def test_notes_relationship_is_not_skipped(self):
        write_fixture(self.source, extra={"ppt/notesSlides/_rels/notesSlide1.xml.rels": relation("media")})
        self.assertEqual(inspect_media(self.source)["status"], "BLOCKED")

    def test_layout_relationship_is_not_skipped(self):
        write_fixture(self.source, extra={"ppt/slideLayouts/_rels/slideLayout1.xml.rels": relation("video")})
        self.assertEqual(inspect_media(self.source)["status"], "BLOCKED")

    def test_orphan_typed_media_is_classified(self):
        write_fixture(self.source, types='<Override PartName="/ppt/media/blob.bin" ContentType="VIDEO/MP4"/>',
                      extra={"ppt/media/blob.bin": b"payload"})
        finding = inspect_media(self.source)["findings"][0]
        self.assertEqual(finding["kind"], "orphan_media_part")
        self.assertEqual(finding["detected_by"], "content_type")

    def test_orphan_filename_media_is_classified(self):
        write_fixture(self.source, extra={"ppt/media/clip.mp4": b"payload"})
        finding = inspect_media(self.source)["findings"][0]
        self.assertEqual(finding["kind"], "orphan_media_part")
        self.assertEqual(finding["detected_by"], "filename")

    def test_media_word_in_plain_content_is_clear(self):
        write_fixture(self.source, body='<p:sp><a:t>video overview and audio notes</a:t></p:sp>')
        self.assertEqual(inspect_media(self.source)["status"], "CLEAR")

    def test_invalid_zip_is_unknown(self):
        self.source.write_bytes(b"not a zip")
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_malformed_xml_is_unknown(self):
        write_fixture(self.source, extra={"ppt/notesSlides/notesSlide1.xml": "<broken"})
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_entity_declaration_is_unknown(self):
        write_fixture(self.source, extra={"ppt/notesSlides/notesSlide1.xml": '<!DOCTYPE a [<!ENTITY b "x">]><a/>'})
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_duplicate_parts_are_unknown(self):
        write_fixture(self.source)
        with warnings.catch_warnings(), ZipFile(self.source, "a") as archive:
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr("ppt/presentation.xml", f'<p:presentation xmlns:p="{P}"/>')
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_xml_size_limit_is_unknown(self):
        write_fixture(self.source)
        with patch("pptx_backend.media_preflight.MAX_XML_BYTES", 10):
            self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_parseable_non_presentation_zip_is_unknown(self):
        write_fixture(self.source, extra={"ppt/presentation.xml": "<other/>"})
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_conflicting_mime_declarations_are_unknown(self):
        write_fixture(self.source, types=(
            '<Default Extension="bin" ContentType="video/mp4"/>'
            '<Default Extension="bin" ContentType="image/png"/>'),
            extra={"ppt/media/clip.bin": b"payload"})
        self.assertEqual(inspect_media(self.source)["status"], "UNKNOWN")

    def test_cli_blocks_without_changing_source(self):
        write_fixture(self.source, relations=relation("video"))
        before = self.source.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/inspect_pptx_media.py"),
                                 str(self.source)], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.source])

    def test_edit_entry_blocks_before_runtime_import_or_output(self):
        write_fixture(self.source, relations=relation("video"))
        actions = Path(self.temp.name) / "actions.json"
        actions.write_text('{"actions":[],"expected_text":[],"render_indices":[]}')
        before = self.source.read_bytes()
        result = subprocess.run(["node", str(ROOT / "scripts/verify_pptx_edits.mjs"),
                                 "--project", self.temp.name, "--input", self.source.name,
                                 "--actions", actions.name, "--out", "must-not-exist"],
                                env={**os.environ, "RUNTIME_PYTHON": sys.executable,
                                     "RUNTIME_NODE_MODULES": str(Path(self.temp.name) / "missing")},
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stderr)
        self.assertNotIn("ERR_MODULE_NOT_FOUND", result.stderr)
        self.assertFalse((Path(self.temp.name) / "must-not-exist").exists())
        self.assertEqual(self.source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
