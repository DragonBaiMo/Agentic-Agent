# SPDX-License-Identifier: MIT
"""Guard hidden merged cells and resolve actual slide relationships read-only."""

import io
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "scripts" / "pptx_backend")
)
from inspect_plain_tables import (
    NS,
    check_table,
    inspect,
    read_xml,
    slide_part,
)


def table_fixture():
    """Build a plain 2x2 XML table as a boundary fixture, not an authored deliverable."""
    table = ET.Element("{" + NS["a"] + "}tbl")
    grid = ET.SubElement(table, "{" + NS["a"] + "}tblGrid")
    ET.SubElement(grid, "{" + NS["a"] + "}gridCol", {"w": "100"})
    ET.SubElement(grid, "{" + NS["a"] + "}gridCol", {"w": "100"})
    for _ in range(2):
        row = ET.SubElement(table, "{" + NS["a"] + "}tr")
        ET.SubElement(row, "{" + NS["a"] + "}tc")
        ET.SubElement(row, "{" + NS["a"] + "}tc")
    return table


def archive_fixture(external=False, merged=False):
    """Use reversed filenames to ensure slide order comes from relationships."""
    stream = io.BytesIO()
    mode = ' TargetMode="External"' if external else ""
    table = table_fixture()
    if merged:
        table.findall("a:tr/a:tc", NS)[1].set("hMerge", "1")
    slide = f'<p:sld xmlns:p="{NS["p"]}" xmlns:a="{NS["a"]}"><p:graphicFrame><p:nvGraphicFramePr><p:cNvPr name="quote"/></p:nvGraphicFramePr><a:graphic><a:graphicData>{ET.tostring(table, encoding="unicode")}</a:graphicData></a:graphic></p:graphicFrame></p:sld>'
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "ppt/presentation.xml",
            f'<p:presentation xmlns:p="{NS["p"]}" xmlns:r="{NS["r"]}"><p:sldIdLst><p:sldId r:id="later"/></p:sldIdLst></p:presentation>',
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            f'<Relationships><Relationship Id="later" Type="{NS["r"]}/slide" Target="slides/slide2.xml"{mode}/></Relationships>',
        )
        archive.writestr("ppt/slides/slide2.xml", slide)
    stream.seek(0)
    return stream


class PlainTableGuardTest(unittest.TestCase):
    """Reject visible-structure ambiguity without modifying the source ZIP."""

    def test_plain(self):
        result = check_table(table_fixture(), {"slide": 1})
        self.assertEqual(
            result, {"slide": 1, "name": "", "rows": 2, "columns": 2, "merged": False}
        )

    def test_covered_horizontal_cell(self):
        table = table_fixture()
        table.findall("a:tr/a:tc", NS)[1].set("hMerge", "1")
        with self.assertRaisesRegex(ValueError, "merged_table"):
            check_table(table, {"slide": 1})

    def test_visible_merged_owner(self):
        table = table_fixture()
        table.findall("a:tr/a:tc", NS)[0].set("gridSpan", "2")
        with self.assertRaisesRegex(ValueError, "merged_table"):
            check_table(table, {"slide": 1})

    def test_vertical_covered_cell(self):
        table = table_fixture()
        table.findall("a:tr/a:tc", NS)[2].set("vMerge", "true")
        with self.assertRaisesRegex(ValueError, "merged_table"):
            check_table(table, {"slide": 1})

    def test_vertical_owner(self):
        table = table_fixture()
        table.findall("a:tr/a:tc", NS)[0].set("rowSpan", "2")
        with self.assertRaisesRegex(ValueError, "merged_table"):
            check_table(table, {"slide": 1})

    def test_ragged(self):
        table = table_fixture()
        row = table.findall("a:tr", NS)[0]
        row.remove(row[1])
        with self.assertRaisesRegex(ValueError, "not_rectangular"):
            check_table(table, {"slide": 1})

    def test_relationship_order(self):
        with ZipFile(archive_fixture()) as archive:
            self.assertEqual(slide_part(archive, 1), "ppt/slides/slide2.xml")

    def test_external_relationship(self):
        with (
            ZipFile(archive_fixture(external=True)) as archive,
            self.assertRaisesRegex(ValueError, "relationship_unsupported"),
        ):
            slide_part(archive, 1)

    def test_slide_bounds(self):
        with (
            ZipFile(archive_fixture()) as archive,
            self.assertRaisesRegex(ValueError, "slide_out_of_range"),
        ):
            slide_part(archive, 2)

    def test_missing_part(self):
        with (
            ZipFile(archive_fixture()) as archive,
            self.assertRaisesRegex(ValueError, "part_missing"),
        ):
            read_xml(archive, "missing.xml")

    def test_named_table(self):
        result = inspect(
            archive_fixture(), [{"kind": "table", "slide": 1, "name": "quote"}]
        )
        self.assertEqual(result[0]["columns"], 2)

    def test_wrong_name(self):
        with self.assertRaisesRegex(ValueError, "target_ambiguous"):
            inspect(
                archive_fixture(), [{"kind": "table", "slide": 1, "name": "absent"}]
            )

    def test_merged_error_identifies_target(self):
        with self.assertRaisesRegex(ValueError, "merged_table.*slide=1.*table=quote"):
            inspect(
                archive_fixture(merged=True),
                [{"kind": "table", "slide": 1, "name": "quote"}],
            )

    def test_other_actions_unchanged(self):
        self.assertEqual(inspect(archive_fixture(), [{"kind": "image"}]), [])


if __name__ == "__main__":
    unittest.main()
