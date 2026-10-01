"""SPDX-License-Identifier: MIT

Small synthetic OPC graphs exercise the repair engine, not PowerPoint rendering.
Full real-PPTX validation is separately exercised by the integration command.
"""

from bounded_pptx.opc import NS, write_package
from bounded_pptx.restore import CHART_TYPE, XLSX_TYPE
from bounded_pptx.workbook import CONTENT_TYPES

CHART = "ppt/charts/chart1.xml"
RELS = "ppt/charts/_rels/chart1.xml.rels"
WORKBOOK = "ppt/embeddings/source.xlsx"
SHEET = "xl/worksheets/sheet1.xml"
TYPES = "[Content_Types].xml"
SLIDE = "ppt/slides/slide1.xml"
R = NS["r"]


def edges(body):
    """Wrap exact relationship elements with the standard package namespace."""
    return f'<Relationships xmlns="{NS["rel"]}">{body}</Relationships>'.encode()


def relation(identifier, kind, target):
    """Build an internal fixture edge; callers mutate it for negative cases."""
    return f'<Relationship Id="{identifier}" Type="{R}/{kind}" Target="{target}"/>'


def workbook():
    """Return the supported static five-part workbook with one string/number pair."""
    content_types = "".join(
        f'<{kind} {"Extension" if kind == "Default" else "PartName"}="{key}" ContentType="{value}"/>'
        for (kind, key), value in CONTENT_TYPES.items()
    )
    return {
        TYPES: f'<Types xmlns="{NS["ct"]}">{content_types}</Types>'.encode(),
        "_rels/.rels": edges(relation("rW", "officeDocument", "xl/workbook.xml")),
        "xl/workbook.xml": (
            f'<workbook xmlns="{NS["s"]}" xmlns:r="{R}"><sheets>'
            '<sheet name="Data" sheetId="1" r:id="rS"/></sheets></workbook>'
        ).encode(),
        "xl/_rels/workbook.xml.rels": edges(
            relation("rS", "worksheet", "worksheets/sheet1.xml")
        ),
        SHEET: (
            f'<worksheet xmlns="{NS["s"]}"><sheetData><row r="2">'
            '<c r="A2" t="inlineStr"><is><t>Day1</t></is></c>'
            '<c r="B2"><v>12</v></c></row></sheetData></worksheet>'
        ).encode(),
    }


def cache(kind, column, value):
    """Build one valid ordered range reference and cache point."""
    return (
        f"<c:{kind}Ref><c:f>Data!${column}$2:${column}$2</c:f><c:{kind}Cache>"
        f'<c:ptCount val="1"/><c:pt idx="0"><c:v>{value}</c:v></c:pt>'
        f"</c:{kind}Cache></c:{kind}Ref>"
    )


def pair():
    """Create original and authored dictionaries with only known dependencies lost."""
    source = {
        TYPES: (
            f'<Types xmlns="{NS["ct"]}"><Default Extension="xlsx" ContentType="{XLSX_TYPE}"/>'
            f'<Override PartName="/{CHART}" ContentType="{CHART_TYPE}"/></Types>'
        ).encode(),
        CHART: (
            f'<c:chartSpace xmlns:c="{NS["c"]}" xmlns:r="{R}"><c:chart><c:plotArea>'
            "<c:barChart><c:ser><c:cat>"
            + cache("str", "A", "Day1")
            + "</c:cat><c:val>"
            + cache("num", "B", "12")
            + "</c:val></c:ser></c:barChart></c:plotArea></c:chart>"
            '<c:externalData r:id="rData"/></c:chartSpace>'
        ).encode(),
        RELS: edges(relation("rData", "package", "../embeddings/source.xlsx")),
        WORKBOOK: write_package(workbook()),
        SLIDE: f'<sld xmlns:c="{NS["c"]}" xmlns:r="{R}"><c:chart r:id="rChart"/></sld>'.encode(),
        "ppt/slides/_rels/slide1.xml.rels": edges(
            relation("rChart", "chart", "../charts/chart1.xml")
        ),
        "ppt/notesSlides/notesSlide1.xml": b"<notes>Authored content stays exact</notes>",
    }
    authored = dict(source)
    del authored[RELS]
    del authored[WORKBOOK]
    authored[CHART] = authored[CHART].replace(b'<c:externalData r:id="rData"/>', b"")
    declaration = f'<Default Extension="xlsx" ContentType="{XLSX_TYPE}"/>'.encode()
    authored[TYPES] = authored[TYPES].replace(declaration, b"")
    return source, authored
