"""SPDX-License-Identifier: MIT

Exercise cache/workbook consistency and reject unsupported spreadsheet features.
"""

import unittest

from fixtures import CHART, SHEET, TYPES, WORKBOOK, pair, workbook

from bounded_pptx import restore_dependencies
from bounded_pptx.opc import write_package


class WorkbookTests(unittest.TestCase):
    """Mutate one source cell or range at a time without trusting caller proof."""

    def setUp(self):
        self.source, self.authored = pair()
        self.workbook = workbook()

    def blocked(self, reason):
        self.source[WORKBOOK] = write_package(self.workbook)
        with self.assertRaisesRegex(ValueError, reason):
            restore_dependencies(
                write_package(self.source), write_package(self.authored)
            )

    def change_both_charts(self, before, after):
        self.source[CHART] = self.source[CHART].replace(before, after)
        self.authored[CHART] = self.authored[CHART].replace(before, after)

    def test_rejects_cell_value_mismatch(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b">12<", b">13<")
        self.blocked("chart_workbook_mismatch")

    def test_rejects_category_mismatch(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b"Day1", b"Day2")
        self.blocked("chart_workbook_mismatch")

    def test_rejects_formula_cell(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b"<v>12", b"<f>SUM(C1:C2)</f><v>12"
        )
        self.blocked("workbook_formula")

    def test_rejects_workbook_extra_part(self):
        self.workbook["xl/styles.xml"] = b"<styles/>"
        self.blocked("unsupported_workbook_profile")

    def test_rejects_workbook_wrong_type(self):
        self.workbook[TYPES] = self.workbook[TYPES].replace(
            b"worksheet+xml", b"worksheet.other"
        )
        self.blocked("workbook_content_types")

    def test_rejects_workbook_extra_metadata(self):
        self.workbook["xl/workbook.xml"] = self.workbook["xl/workbook.xml"].replace(
            b"</workbook>", b"<definedNames/></workbook>"
        )
        self.blocked("unsupported_workbook_metadata")

    def test_rejects_second_sheet(self):
        self.workbook["xl/workbook.xml"] = self.workbook["xl/workbook.xml"].replace(
            b"</sheets>", b'<sheet name="Two" r:id="rS"/></sheets>'
        )
        self.blocked("workbook_sheet")

    def test_rejects_unsupported_cell_type(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b'r="B2"', b'r="B2" t="b"')
        self.blocked("unsupported_cell_type")

    def test_rejects_nonfinite_cell(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b">12<", b">NaN<")
        self.blocked("nonfinite_numeric_value")

    def test_rejects_invalid_numeric_cell(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b">12<", b">anything<")
        self.blocked("invalid_numeric_value")

    def test_rejects_huge_numeric_exponent(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b">12<", b">1e999<")
        self.blocked("numeric_value_limit")

    def test_rejects_huge_numeric_coefficient(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b">12<", b">" + b"1" * 500 + b"<"
        )
        self.blocked("numeric_value_limit")

    def test_rejects_excessive_precision(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b">12<", b">" + b"1" * 40 + b"<"
        )
        self.blocked("numeric_value_limit")

    def test_rejects_duplicate_cell(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b"</row>", b'<c r="B2"><v>12</v></c></row>'
        )
        self.blocked("workbook_cell_address")

    def test_rejects_missing_cell(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b'<c r="B2"><v>12</v></c>', b""
        )
        self.blocked("chart_workbook_mismatch")

    def test_rejects_rich_string(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(
            b"<is><t>Day1</t></is>", b"<is><r><t>Day1</t></r></is>"
        )
        self.blocked("unsupported_inline_string")

    def test_rejects_missing_numeric_value(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b"<v>12</v>", b"")
        self.blocked("unsupported_numeric_cell")

    def test_rejects_horizontal_reference(self):
        self.change_both_charts(b"$A$2:$A$2", b"$A$2:$B$2")
        self.blocked("reference_sheet_or_axis")

    def test_rejects_wrong_sheet_reference(self):
        self.change_both_charts(b"Data!", b"Other!")
        self.blocked("reference_sheet_or_axis")

    def test_rejects_external_reference(self):
        self.change_both_charts(b"Data!", b"[Outside.xlsx]Data!")
        self.blocked("unsupported_chart_reference")

    def test_rejects_huge_range(self):
        self.change_both_charts(b"$A$2:$A$2", b"$A$2:$A$50000")
        self.blocked("reference_length")

    def test_rejects_wrong_cache_count(self):
        self.change_both_charts(b'ptCount val="1"', b'ptCount val="2"')
        self.blocked("chart_cache_count")

    def test_rejects_wrong_cache_index(self):
        self.change_both_charts(b'pt idx="0"', b'pt idx="1"')
        self.blocked("chart_cache_order")

    def test_rejects_unsupported_chart_type(self):
        self.change_both_charts(b"barChart", b"lineChart")
        self.blocked("unsupported_chart_type")

    def test_rejects_missing_reference(self):
        self.change_both_charts(b"numRef", b"numLit")
        self.blocked("series_reference_missing")

    def test_rejects_extra_reference(self):
        self.change_both_charts(b"</c:ser>", b"<c:f>Data!$A$2:$A$2</c:f></c:ser>")
        self.blocked("unsupported_extra_reference")

    def test_accepts_consistently_changed_dataset(self):
        self.workbook[SHEET] = self.workbook[SHEET].replace(b">12<", b">23.5<")
        self.change_both_charts(b">12<", b">23.50<")
        self.source[WORKBOOK] = write_package(self.workbook)
        _, proof = restore_dependencies(
            write_package(self.source), write_package(self.authored)
        )
        self.assertEqual(proof["workbook"]["references_verified"], 2)

    def test_accepts_quoted_sheet_reference(self):
        self.change_both_charts(b"Data!", b"'Data'!")
        _, proof = restore_dependencies(
            write_package(self.source), write_package(self.authored)
        )
        self.assertEqual(proof["workbook"]["sheet"], "Data")
