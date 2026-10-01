"""SPDX-License-Identifier: MIT. Small parser fixtures, never slide deliverables.

The incomplete OPC fixture exercises read-only checks. Real authoring and rendering
are verified separately with the unchanged Artifact Tool B08 presentation.
"""

import hashlib
import json
import struct
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image
from pptx_backend.protected_package import NS


def archive(path, files):
    """Write deliberately small parser inputs only, including malformed variants."""
    with ZipFile(path, "w", ZIP_DEFLATED) as result:
        for name, body in files.items():
            result.writestr(name, body)
    return path


def change_xml(files, part, mutate):
    """Apply a test-only mutation to one fixture part."""
    root = ET.fromstring(files[part])
    mutate(root)
    files[part] = ET.tostring(root)


def corrupt_png():
    """Return CRC-valid chunks whose compressed pixel data cannot decode."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", b"bad-zlib")
        + chunk(b"IEND", b"")
    )


def fixture(directory):
    """Return a bounded static PNG, declared slot, and minimal parser package."""
    root = Path(directory)
    Image.new("RGBA", (4, 2), (10, 20, 30, 255)).save(root / "original.png")
    body = (root / "original.png").read_bytes()
    plan = {
        "schema_version": "pptx-1",
        "canvas": [400, 300],
        "background": "original.png",
        "slides": [
            {
                "id": "S01",
                "elements": [
                    {
                        "id": "photo",
                        "kind": "image",
                        "file": "original.png",
                        "box": [20, 40, 200, 100],
                        "alt": "Fixture",
                    }
                ],
            }
        ],
        "protected_media": [
            {
                "slide_id": "S01",
                "object_id": "photo",
                "file": "original.png",
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        ],
    }
    p, a, r, rel, ct = (NS[key] for key in ("p", "a", "r", "rel", "ct"))
    files = {
        "[Content_Types].xml": f'<Types xmlns="{ct}"><Default Extension="png" ContentType="image/png"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="{rel}"><Relationship Id="root" Type="{r}/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
        "ppt/presentation.xml": f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst><p:sldId r:id="page"/></p:sldIdLst><p:sldSz cx="3810000" cy="2857500"/></p:presentation>',
        "ppt/_rels/presentation.xml.rels": f'<Relationships xmlns="{rel}"><Relationship Id="page" Type="{r}/slide" Target="slides/slide7.xml"/></Relationships>',
        "ppt/slides/slide7.xml": f'<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:r="{r}"><p:cSld><p:spTree><p:grpSpPr/><p:pic><p:nvPicPr><p:cNvPr name="photo"/></p:nvPicPr><p:blipFill><a:blip r:embed="asset"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="190500" y="381000"/><a:ext cx="1905000" cy="952500"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic></p:spTree></p:cSld></p:sld>',
        "ppt/slides/_rels/slide7.xml.rels": f'<Relationships xmlns="{rel}"><Relationship Id="asset" Type="{r}/image" Target="../media/source.png"/></Relationships>',
        "ppt/media/source.png": body,
    }
    (root / "deck.json").write_text(json.dumps(plan), encoding="utf-8")
    archive(root / "source.pptx", files)
    return root, plan, files


def group_picture(root):
    """Put the protected object beneath an unsupported local group."""
    tree = root.find("p:cSld/p:spTree", NS)
    picture = tree.find("p:pic", NS)
    tree.remove(picture)
    ET.SubElement(tree, "{" + NS["p"] + "}grpSp").append(picture)
