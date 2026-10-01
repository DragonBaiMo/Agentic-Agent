# SPDX-License-Identifier: MIT
"""Read-only eligibility check for exact-cell diagnostics on unmerged PPTX tables.

Usage: python inspect_plain_tables.py SOURCE.pptx ACTIONS.json
Merged or ambiguous targets require review of visible native table structure.
"""

import json
import posixpath
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
MAX_XML = 8 * 1024 * 1024  # NOTE: Bound only inspected XML, not unrelated media.


def read_xml(archive, name):
    """Read one unique bounded XML part; never extract or follow external targets."""
    matches = [entry for entry in archive.infolist() if entry.filename == name]
    if len(matches) != 1 or matches[0].file_size > MAX_XML:
        raise ValueError("table_structure_part_missing_duplicate_or_large")
    data = archive.read(matches[0])
    if b"\x00" in data or re.search(rb"<!\s*(DOCTYPE|ENTITY)", data, re.IGNORECASE):
        raise ValueError("table_structure_unsupported_xml")
    return ET.fromstring(data)


def slide_part(archive, slide):
    """Resolve slide order from actual relationships, not slide filename numbering."""
    presentation = read_xml(archive, "ppt/presentation.xml")
    slides = presentation.findall("p:sldIdLst/p:sldId", NS)
    if type(slide) is not int or slide < 1 or slide > len(slides):
        raise ValueError("table_slide_out_of_range")
    rid = slides[slide - 1].attrib["{" + NS["r"] + "}id"]
    rels = read_xml(archive, "ppt/_rels/presentation.xml.rels")
    matches = [rel for rel in rels if rel.get("Id") == rid]
    if len(matches) != 1 or matches[0].get("TargetMode") == "External":
        raise ValueError("table_slide_relationship_unsupported")
    relation = matches[0]
    if not relation.get("Type", "").endswith("/slide"):
        raise ValueError("table_slide_relationship_unsupported")
    target = relation.get("Target", "")
    if "\\" in target or ":" in target:
        raise ValueError("table_slide_relationship_unsupported")
    part = posixpath.normpath(posixpath.join("ppt", target)).lstrip("/")
    if part.startswith("../") or not part.endswith(".xml"):
        raise ValueError("table_slide_relationship_unsupported")
    return part


def selected_table(tree, action):
    """Map only an exact named table or the single table on the owner slide."""
    tables = []
    for frame in tree.findall(".//p:graphicFrame", NS):
        table = frame.find("a:graphic/a:graphicData/a:tbl", NS)
        name = frame.find("p:nvGraphicFramePr/p:cNvPr", NS)
        if table is not None and (
            not action.get("name")
            or name is not None
            and name.get("name") == action["name"]
        ):
            tables.append(table)
    if len(tables) != 1:
        raise ValueError("table_structure_target_ambiguous")
    return tables[0]


def check_table(table, action):
    """Reject merged or ragged tables instead of certifying invisible covered cells."""
    rows = table.findall("a:tr", NS)
    columns = len(table.findall("a:tblGrid/a:gridCol", NS))
    cells = [row.findall("a:tc", NS) for row in rows]
    if not rows or not columns or any(len(row) != columns for row in cells):
        raise ValueError("table_structure_not_rectangular")
    for row in cells:
        for cell in row:
            if (
                cell.get("hMerge", "0") in ("1", "true")
                or cell.get("vMerge", "0") in ("1", "true")
                or int(cell.get("gridSpan", "1")) != 1
                or int(cell.get("rowSpan", "1")) != 1
            ):
                raise ValueError("merged_table_requires_visible_structure_review")
    return {
        "slide": action["slide"],
        "name": action.get("name", ""),
        "rows": len(rows),
        "columns": columns,
        "merged": False,
    }


def inspect(source, actions):
    """Check only tables targeted by this diagnostic; leave the deck unchanged."""
    with ZipFile(source) as archive:
        results = []
        for action in actions:
            if action["kind"] != "table":
                continue
            try:
                tree = read_xml(archive, slide_part(archive, action["slide"]))
                results.append(check_table(selected_table(tree, action), action))
            except ValueError as error:
                raise ValueError(
                    f"{error}; slide={action['slide']}; table={action.get('name') or 'single table'}"
                ) from error
        return results


def main():
    """Emit machine-readable proof or a stable nonzero refusal for this edit route."""
    try:
        actions = json.loads(Path(sys.argv[2]).read_text())["actions"]
        result = inspect(Path(sys.argv[1]), actions)
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    except (ValueError, KeyError, OSError, ET.ParseError, BadZipFile) as error:
        sys.stderr.write(
            json.dumps(
                {
                    "level": "ERROR",
                    "event": "table_eligibility_failed",
                    "detail": str(error),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
