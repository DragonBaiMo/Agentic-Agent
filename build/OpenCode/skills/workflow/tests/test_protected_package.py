"""SPDX-License-Identifier: MIT. Read-only OPC geometry and identity boundaries."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from pptx_backend.protected_package import NS, expected_frame, verify_protected_media
from protected_fixtures import archive, change_xml, fixture, group_picture

SLIDE = "ppt/slides/slide7.xml"


class ProtectedPackageTest(unittest.TestCase):
    """These synthetic parser cases do not substitute for real rendered PPTX QA."""

    def setUp(self):
        temporary = Path(__file__).parents[1] / "tmp"
        temporary.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary)
        self.addCleanup(self.temp.cleanup)
        self.root, self.plan, self.files = fixture(self.temp.name)

    def verify(self):
        """Serialize this test input and inspect it without changing its bytes."""
        return verify_protected_media(
            self.root, self.plan, archive(self.root / "case.pptx", self.files)
        )

    def reject(self, mutate, code, part=SLIDE):
        """Keep each test's mutation and expected rejection visible at its call site."""
        change_xml(self.files, part, mutate)
        with self.assertRaisesRegex(ValueError, code):
            self.verify()

    def test_plain_original(self):
        result = self.verify()
        self.assertEqual(result["pictures"][0]["slide_part"], SLIDE)
        self.assertTrue(result["pictures"][0]["contain_frame_verified"])

    def test_contain_centers_without_stretch(self):
        result = expected_frame({"item": {"box": [0, 0, 100, 100]}, "size": [4, 2]})
        self.assertEqual(result, [0, 238125, 952500, 476250])

    def test_canvas_mismatch(self):
        self.plan["canvas"] = [401, 300]
        with self.assertRaisesRegex(ValueError, "protected_canvas_mismatch"):
            self.verify()

    def test_no_declarations(self):
        self.plan["protected_media"] = []
        with self.assertRaisesRegex(ValueError, "protected_media_required"):
            self.verify()

    def test_embedded_bytes_changed(self):
        self.files["ppt/media/source.png"] = b"different"
        with self.assertRaisesRegex(ValueError, "protected_embedded_bytes_changed"):
            self.verify()

    def test_wrong_content_type(self):
        self.reject(
            lambda r: r[0].set("ContentType", "image/jpeg"),
            "protected_content_type",
            "[Content_Types].xml",
        )

    def test_external_image_relationship(self):
        self.reject(
            lambda r: r[0].set("TargetMode", "External"),
            "external_relationship",
            "ppt/slides/_rels/slide7.xml.rels",
        )

    def test_missing_relationship_target(self):
        self.files.pop("ppt/media/source.png")
        with self.assertRaisesRegex(ValueError, "relationship_target_missing"):
            self.verify()

    def test_hidden_slide(self):
        self.reject(lambda r: r.set("show", "0"), "protected_slide_hidden")

    def test_timed_slide(self):
        self.reject(
            lambda r: ET.SubElement(r, "{" + NS["p"] + "}timing"),
            "protected_slide_timing_unsupported",
        )

    def test_root_group_rotation(self):
        self.reject(
            lambda r: ET.SubElement(
                r.find("p:cSld/p:spTree/p:grpSpPr", NS),
                "{" + NS["a"] + "}xfrm",
                {"rot": "1"},
            ),
            "protected_parent_transform_unsupported",
        )

    def test_nested_protected_picture(self):
        self.reject(group_picture, "protected_grouped_picture_unsupported")

    def test_duplicate_protected_name(self):
        self.reject(
            lambda r: r.find("p:cSld/p:spTree", NS).append(
                copy.deepcopy(r.find(".//p:pic", NS))
            ),
            "protected_picture_not_unique",
        )

    def test_hidden_picture(self):
        self.reject(
            lambda r: r.find(".//p:cNvPr", NS).set("hidden", "true"),
            "protected_picture_hidden",
        )

    def test_picture_rotation(self):
        self.reject(
            lambda r: r.find(".//p:pic/p:spPr/a:xfrm", NS).set("rot", "60000"),
            "protected_rotation_or_flip",
        )

    def test_picture_flip(self):
        self.reject(
            lambda r: r.find(".//p:pic/p:spPr/a:xfrm", NS).set("flipH", "1"),
            "protected_rotation_or_flip",
        )

    def test_video_metadata_is_not_a_static_picture(self):
        self.reject(
            lambda r: ET.SubElement(
                ET.SubElement(r.find(".//p:nvPicPr", NS), "{" + NS["p"] + "}nvPr"),
                "{" + NS["a"] + "}videoFile",
            ),
            "protected_nonvisual_media_or_action",
        )

    def test_click_action_is_not_plain_picture_proof(self):
        self.reject(
            lambda r: ET.SubElement(
                r.find(".//p:cNvPr", NS),
                "{" + NS["a"] + "}hlinkClick",
                {"action": "ppaction://media"},
            ),
            "protected_nonvisual_media_or_action",
        )

    def test_picture_crop(self):
        self.reject(
            lambda r: ET.SubElement(
                r.find(".//p:blipFill", NS), "{" + NS["a"] + "}srcRect", {"l": "1"}
            ),
            "protected_crop",
        )

    def test_picture_stretched(self):
        self.reject(
            lambda r: r.find(".//a:ext", NS).set("cx", "1906000"),
            "protected_contain_frame_mismatch",
        )

    def test_invalid_frame_number(self):
        self.reject(
            lambda r: r.find(".//a:off", NS).set("x", "-"), "protected_frame_invalid"
        )

    def test_actual_frame_outside_even_near_tolerance(self):
        self.plan["slides"][0]["elements"][0]["box"][0] = 0
        self.reject(
            lambda r: r.find(".//a:off", NS).set("x", "-1"),
            "protected_frame_outside_canvas",
        )

    def test_image_effect(self):
        self.reject(
            lambda r: ET.SubElement(
                r.find(".//a:blip", NS),
                "{" + NS["a"] + "}alphaModFix",
                {"amt": "50000"},
            ),
            "protected_blip_effect_or_link",
        )

    def test_geometry_mask(self):
        self.reject(
            lambda r: r.find(".//a:prstGeom", NS).set("prst", "ellipse"),
            "protected_mask",
        )

    def test_explicit_zero_crop(self):
        change_xml(
            self.files,
            SLIDE,
            lambda r: ET.SubElement(
                r.find(".//p:blipFill", NS), "{" + NS["a"] + "}srcRect", {"l": "0"}
            ),
        )
        self.assertEqual(self.verify()["status"], "passed")


if __name__ == "__main__":
    unittest.main()
