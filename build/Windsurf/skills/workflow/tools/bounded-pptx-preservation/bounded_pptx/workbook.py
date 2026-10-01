"""SPDX-License-Identifier: MIT

Prove static single-sheet chart caches against original workbook cells.
The intentionally small workbook profile rejects formulas, shared strings,
macros, styles, external links and any other unproved dependency.
"""

import re
from decimal import Decimal, InvalidOperation

from .opc import NS, read_package, relationships, require, resolve_target, xml

PROFILE = {
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/worksheets/sheet1.xml",
}
CELL = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,5})")
RANGE = re.compile(
    r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_ ]*))!\$([A-Z]{1,3})\$([1-9][0-9]{0,5}):\$([A-Z]{1,3})\$([1-9][0-9]{0,5})"
)
CONTENT_TYPES = {
    ("Default", "rels"): "application/vnd.openxmlformats-package.relationships+xml",
    ("Default", "xml"): "application/xml",
    (
        "Override",
        "/xl/workbook.xml",
    ): "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
    (
        "Override",
        "/xl/worksheets/sheet1.xml",
    ): "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
}


def verify_types(data):
    """Reject workbook profiles with unproved content-type declarations."""
    root = xml(data)
    actual = {
        (
            node.tag.removeprefix("{" + NS["ct"] + "}"),
            node.get("Extension", node.get("PartName")),
        ): node.get("ContentType")
        for node in root
    }
    require(
        root.tag == "{" + NS["ct"] + "}Types"
        and len(root) == len(actual)
        and actual == CONTENT_TYPES,
        "workbook_content_types",
    )


def one_relation(files, owner, suffix, expected):
    """Require the known minimal workbook edge and an existing exact target."""
    relations = relationships(files, owner)
    require(len(relations) == 1, "workbook_relationship_count")
    relation = relations[0]
    require(
        relation.get("Type") == NS["r"] + "/" + suffix, "workbook_relationship_type"
    )
    require(
        resolve_target(owner, relation.get("Target")) == expected,
        "workbook_relationship_target",
    )
    return relation.get("Id")


def read_cells(data):
    """Return a worksheet name and exact cell values for the five-part profile."""
    files = read_package(data)
    require(set(files) == PROFILE, "unsupported_workbook_profile")
    verify_types(files["[Content_Types].xml"])
    one_relation(files, "", "officeDocument", "xl/workbook.xml")
    rid = one_relation(
        files, "xl/workbook.xml", "worksheet", "xl/worksheets/sheet1.xml"
    )
    workbook = xml(files["xl/workbook.xml"])
    require(workbook.tag == "{" + NS["s"] + "}workbook", "workbook_root")
    sheets = workbook.findall("s:sheets/s:sheet", NS)
    require(
        len(sheets) == 1 and sheets[0].get("{" + NS["r"] + "}id") == rid,
        "workbook_sheet",
    )
    require(
        {child.tag for child in workbook} == {"{" + NS["s"] + "}sheets"},
        "unsupported_workbook_metadata",
    )
    sheet = xml(files["xl/worksheets/sheet1.xml"])
    require(sheet.tag == "{" + NS["s"] + "}worksheet", "worksheet_root")
    require(sheet.find(".//s:f", NS) is None, "workbook_formula")
    require(
        {child.tag for child in sheet}
        <= {"{" + NS["s"] + "}dimension", "{" + NS["s"] + "}sheetData"},
        "unsupported_sheet_metadata",
    )
    cells = {}
    for cell in sheet.findall("s:sheetData/s:row/s:c", NS):
        address = cell.get("r", "")
        require(
            CELL.fullmatch(address) is not None and address not in cells,
            "workbook_cell_address",
        )
        kind = cell.get("t", "n")
        require(kind in ("n", "inlineStr"), "unsupported_cell_type")
        if kind == "inlineStr":
            nodes = cell.findall("s:is/s:t", NS)
            require(
                len(nodes) == 1 and len(list(cell)) == 1, "unsupported_inline_string"
            )
            value = nodes[0].text or ""
        else:
            nodes = cell.findall("s:v", NS)
            require(
                len(nodes) == 1 and len(list(cell)) == 1, "unsupported_numeric_cell"
            )
            value = number(nodes[0].text)
        cells[address] = (kind, value)
    require(bool(cells), "workbook_empty")
    return sheets[0].get("name"), cells


def number(value):
    """Parse finite numeric content while avoiding floating-point rounding."""
    require(len(value or "") <= 128, "numeric_value_limit")
    exponent = re.search(r"[eE]([+-]?[0-9]+)$", (value or "").strip())
    require(
        exponent is None or len(exponent.group(1).lstrip("+-")) <= 3,
        "numeric_value_limit",
    )
    try:
        result = Decimal(value or "")
    except InvalidOperation as error:
        raise ValueError("invalid_numeric_value") from error
    require(result.is_finite(), "nonfinite_numeric_value")
    require(
        len(result.as_tuple().digits) <= 34 and abs(result.adjusted()) <= 308,
        "numeric_value_limit",
    )
    return result


def verify_reference(ref, sheet_name, cells, numeric):
    """Compare one bounded vertical absolute range with each ordered cache point."""
    formula = ref.findtext("c:f", namespaces=NS)
    match = RANGE.fullmatch(formula or "")
    require(match is not None, "unsupported_chart_reference")
    assert match is not None  # NOTE: Narrow type after the executable rejection above.
    quoted, bare, first_col, first_row, last_col, last_row = match.groups()
    require(
        (quoted or bare) == sheet_name and first_col == last_col,
        "reference_sheet_or_axis",
    )
    start, end = int(first_row), int(last_row)
    require(0 < end - start + 1 <= 10000, "reference_length")
    cache = ref.find("c:numCache" if numeric else "c:strCache", NS)
    require(cache is not None, "chart_cache_missing")
    require(len(ref) == 2 and len(ref.findall("c:f", NS)) == 1, "chart_reference_shape")
    points = cache.findall("c:pt", NS)
    count = cache.find("c:ptCount", NS)
    require(
        count is not None
        and len(cache.findall("c:ptCount", NS)) == 1
        and count.get("val") == str(len(points)) == str(end - start + 1),
        "chart_cache_count",
    )
    for index, point in enumerate(points):
        require(point.get("idx") == str(index), "chart_cache_order")
        value = point.findtext("c:v", namespaces=NS)
        expected = ("n", number(value)) if numeric else ("inlineStr", value or "")
        require(
            cells.get(first_col + str(start + index)) == expected,
            "chart_workbook_mismatch",
        )


def verify_workbook(data, chart):
    """Prove every supported bar-series category/value reference against source cells."""
    sheet, cells = read_cells(data)
    plot = chart.find("c:chart/c:plotArea", NS)
    require(plot is not None, "plot_missing")
    chart_kinds = [node for node in plot if node.tag.endswith("Chart")]
    require(
        len(chart_kinds) == 1 and chart_kinds[0].tag == "{" + NS["c"] + "}barChart",
        "unsupported_chart_type",
    )
    series = chart_kinds[0].findall("c:ser", NS)
    require(0 < len(series) <= 16, "series_count")
    references = []
    for item in series:
        cat, val = item.find("c:cat/c:strRef", NS), item.find("c:val/c:numRef", NS)
        require(cat is not None and val is not None, "series_reference_missing")
        verify_reference(cat, sheet, cells, False)
        verify_reference(val, sheet, cells, True)
        references.extend([cat, val])
    require(
        len(chart.findall(".//c:f", NS)) == len(references),
        "unsupported_extra_reference",
    )
    return {
        "sheet": sheet,
        "series": len(series),
        "references_verified": len(references),
        "formula_cells": 0,
        "workbook_profile": "five_part_inline_static",
    }
