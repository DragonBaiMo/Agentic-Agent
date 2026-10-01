"""SPDX-License-Identifier: MIT

Prove the positive repair and rejection of untrusted or ambiguous OPC graphs.
"""

import io
import unittest
import warnings
import zipfile
from unittest.mock import patch
from xml.etree import ElementTree as ET

from fixtures import CHART, RELS, SLIDE, TYPES, WORKBOOK, edges, pair, relation

from bounded_pptx import restore_dependencies
from bounded_pptx.opc import read_package, write_package
from bounded_pptx.restore import CHART_TYPE


class RestorationTests(unittest.TestCase):
    """Each test changes one boundary condition of the known-good unit graph."""

    def setUp(self):
        self.source, self.authored = pair()

    def restore(self):
        return restore_dependencies(
            write_package(self.source), write_package(self.authored)
        )

    def blocked(self, reason):
        with self.assertRaisesRegex(ValueError, reason):
            self.restore()

    def test_restores_only_original_dependency_bytes(self):
        result, proof = self.restore()
        final = read_package(result)
        self.assertEqual(final[CHART], self.source[CHART])
        self.assertEqual(final[WORKBOOK], self.source[WORKBOOK])
        self.assertEqual(final[RELS], self.source[RELS])
        self.assertEqual(final[SLIDE], self.authored[SLIDE])
        self.assertEqual(proof["workbook"]["references_verified"], 2)
        self.assertEqual(proof["changed_parts"], sorted([TYPES, CHART]))
        self.assertTrue(final[TYPES].startswith(b"<?xml"))
        self.assertIn(b"<Types xmlns=", final[TYPES])

    def test_rejects_authored_cache_change(self):
        self.authored[CHART] = self.authored[CHART].replace(b">12<", b">13<")
        self.blocked("chart_identity_changed")

    def test_rejects_authored_style_change(self):
        self.authored[CHART] = self.authored[CHART].replace(
            b"<c:barChart>", b'<c:barChart changed="1">'
        )
        self.blocked("chart_identity_changed")

    def test_rejects_multiple_charts(self):
        self.source["ppt/charts/chart2.xml"] = self.source[CHART]
        self.blocked("single_chart_required")

    def test_rejects_undeclared_chart(self):
        self.source[TYPES] = self.source[TYPES].replace(CHART_TYPE.encode(), b"other")
        self.blocked("single_chart_required")

    def test_rejects_reused_chart(self):
        self.source[SLIDE] = self.source[SLIDE].replace(
            b"</sld>", b'<c:chart r:id="rChart"/></sld>'
        )
        self.blocked("chart_owner_not_unique")

    def test_rejects_missing_owner_relation(self):
        self.source[SLIDE] = self.source[SLIDE].replace(b"rChart", b"unknown")
        self.blocked("chart_owner_relation")

    def test_rejects_wrong_external_data_id(self):
        self.source[CHART] = self.source[CHART].replace(b"rData", b"unknown")
        self.blocked("external_data_relationship")

    def test_rejects_duplicate_external_data(self):
        self.source[CHART] = self.source[CHART].replace(
            b"</c:chartSpace>", b'<c:externalData r:id="rData"/></c:chartSpace>'
        )
        self.blocked("external_data_not_unique")

    def test_rejects_chart_dependency_type(self):
        self.source[RELS] = self.source[RELS].replace(
            b"relationships/package", b"relationships/image"
        )
        self.blocked("chart_dependency_type")

    def test_rejects_existing_workbook(self):
        self.authored[WORKBOOK] = self.source[WORKBOOK]
        self.blocked("authored_workbook_collision")

    def test_rejects_existing_chart_relationship(self):
        self.authored[RELS] = edges("")
        self.blocked("authored_chart_relationship_collision")

    def test_rejects_duplicate_xlsx_type(self):
        root = ET.fromstring(self.source[TYPES])
        root.append(root[0])
        self.source[TYPES] = ET.tostring(root)
        self.blocked("source_xlsx_type_not_unique")

    def test_rejects_wrong_xlsx_type(self):
        self.source[TYPES] = self.source[TYPES].replace(
            b"spreadsheetml.sheet", b"spreadsheetml.other"
        )
        self.blocked("source_xlsx_type_invalid")

    def test_rejects_existing_xlsx_type(self):
        self.authored[TYPES] = self.source[TYPES]
        self.blocked("authored_xlsx_type_collision")

    def test_rejects_external_relationship(self):
        self.source[RELS] = self.source[RELS].replace(
            b"/>", b' TargetMode="External"/>'
        )
        self.blocked("external_relationship")

    def test_rejects_uri_target_without_external_flag(self):
        self.source[RELS] = edges(
            relation("rData", "package", "https://example.invalid/a.xlsx")
        )
        self.blocked("unsafe_target")

    def test_rejects_target_escape(self):
        self.source[RELS] = edges(relation("rData", "package", "../../../outside.xlsx"))
        self.blocked("target_escape")

    def test_rejects_missing_target(self):
        del self.source[WORKBOOK]
        self.blocked("relationship_target_missing")

    def test_rejects_duplicate_relationship_id(self):
        self.source[RELS] = edges(
            relation("rData", "package", "../embeddings/source.xlsx") * 2
        )
        self.blocked("relationship_id")

    def test_rejects_active_package(self):
        self.source["ppt/vbaProject.bin"] = b"anything"
        self.blocked("active_or_signed_package")

    def test_rejects_traversal_member(self):
        self.source["../outside.xml"] = b"<x/>"
        self.blocked("unsafe_member")

    def test_rejects_backslash_member(self):
        self.source["ppt\\outside.xml"] = b"<x/>"
        self.blocked("unsafe_member")

    def test_rejects_directory_member(self):
        self.source["folder/"] = b""
        self.blocked("directory_member")

    def test_rejects_xml_entities(self):
        self.source["test.xml"] = b'<!DOCTYPE x [<!ENTITY v "x">]><x>&v;</x>'
        self.blocked("xml_entity")

    def test_rejects_utf16_xml(self):
        self.source["test.xml"] = "<x/>".encode("utf-16")
        self.blocked("unsupported_xml_encoding")

    def test_rejects_malformed_xml(self):
        self.source["test.xml"] = b"<x>"
        self.blocked("invalid_xml")

    def test_rejects_deep_xml(self):
        self.source["deep.xml"] = b"<x>" * 70 + b"</x>" * 70
        self.blocked("xml_depth_limit")

    def test_accepts_unrelated_slide_without_chart(self):
        self.source["ppt/slides/slide2.xml"] = b"<sld/>"
        self.authored["ppt/slides/slide2.xml"] = b"<sld/>"
        _, proof = self.restore()
        self.assertEqual(proof["chart_owner_slide"], 1)

    def test_rejects_duplicate_zip_members(self):
        stream = io.BytesIO()
        with warnings.catch_warnings(), zipfile.ZipFile(stream, "w") as archive:
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr("same", b"first")
            archive.writestr("same", b"second")
        with self.assertRaisesRegex(ValueError, "duplicate_member"):
            read_package(stream.getvalue())

    def test_rejects_invalid_zip(self):
        with self.assertRaisesRegex(ValueError, "invalid_zip"):
            read_package(b"not a zip")

    def test_rejects_expanded_limit(self):
        data = write_package({"large": b"0" * 5000})
        with (
            patch("bounded_pptx.opc.MAX_BYTES", 1000),
            self.assertRaisesRegex(ValueError, "expanded_size_limit"),
        ):
            read_package(data)

    def test_rejects_member_count(self):
        with patch("bounded_pptx.opc.MAX_MEMBERS", 1):
            self.blocked("member_count_limit")
