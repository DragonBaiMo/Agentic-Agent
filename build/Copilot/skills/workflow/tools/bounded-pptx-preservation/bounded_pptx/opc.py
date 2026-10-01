"""SPDX-License-Identifier: MIT

Read bounded OPC packages in memory; never extract untrusted paths to disk.
"""

import hashlib
import io
import posixpath
import re
import zipfile
import zlib
from xml.etree import ElementTree as ET

NS = {
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}
MAX_BYTES = 128 * 1024 * 1024
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 2000


class Unsupported(ValueError):
    """The input cannot be proved safe within this supported static-chart route."""


def require(condition, code):
    """Raise a stable machine code instead of allowing an ambiguous repair."""
    if not condition:
        raise Unsupported(code)


def digest(data):
    """Compute a receipt identity from the exact bytes used by this invocation."""
    return hashlib.sha256(data).hexdigest()


def xml(data):
    """Reject declarations with entity expansion and oversized XML before parsing."""
    require(len(data) <= MAX_XML_BYTES, "xml_size_limit")
    require(b"\x00" not in data, "unsupported_xml_encoding")
    require(
        not re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", data, re.IGNORECASE), "xml_entity"
    )
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise Unsupported("invalid_xml") from error
    stack = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        require(depth <= 64, "xml_depth_limit")
        stack.extend((child, depth + 1) for child in element)
    return root


def tree_value(element):
    """Ignore namespace prefix spelling only; retain content and attribute values."""
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        element.text or "",
        tuple(tree_value(child) for child in element),
        element.tail or "",
    )


def read_package(data):
    """Read CRC-checked unique canonical entries within fixed memory bounds."""
    require(len(data) <= MAX_BYTES, "archive_size_limit")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            require(len(entries) <= MAX_MEMBERS, "member_count_limit")
            require(
                sum(e.file_size for e in entries) <= MAX_BYTES, "expanded_size_limit"
            )
            names = [entry.filename for entry in entries]
            require(len(names) == len(set(names)), "duplicate_member")
            for entry in entries:
                name = entry.filename
                require(not entry.is_dir(), "directory_member")
                require(not (entry.flag_bits & 1), "encrypted_member")
                require(not re.search(r"[\\:\x00-\x1f]", name), "unsafe_member")
                require(
                    name == posixpath.normpath(name)
                    and not name.startswith(("/", "../")),
                    "unsafe_member",
                )
                require(name not in ("", ".", ".."), "unsafe_member")
            files = {entry.filename: archive.read(entry) for entry in entries}
    except (
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        zlib.error,
        EOFError,
    ) as error:
        raise Unsupported("invalid_zip") from error
    require("[Content_Types].xml" in files, "content_types_missing")
    # NOTE: External relationships anywhere in the supplied package are unsupported.
    for name, body in files.items():
        require(
            not name.endswith(".bin") and "_xmlsignatures/" not in name,
            "active_or_signed_package",
        )
        if name.endswith(".rels"):
            owner = owner_of_rels(name)
            for relation in relationships(files, owner):
                require(
                    resolve_target(owner, relation.get("Target")) in files,
                    "relationship_target_missing",
                )
        elif name.endswith(".xml"):
            xml(body)
    return files


def rels_part(part):
    """Return the standard OPC relationship part for a known owner."""
    return posixpath.join(
        posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels"
    )


def owner_of_rels(part):
    """Map a canonical relationship part to its package owner, including root."""
    if part == "_rels/.rels":
        return ""
    require("/_rels/" in part and part.endswith(".rels"), "invalid_relationship_part")
    folder, name = part.rsplit("/_rels/", 1)
    return posixpath.join(folder, name[:-5])


def resolve_target(owner, target):
    """Resolve OPC absolute/relative targets; reject URI, fragment and escape forms."""
    require(
        bool(target) and not re.search(r"[\\:%?#\x00-\x1f]", target), "unsafe_target"
    )
    result = posixpath.normpath(
        target.lstrip("/")
        if target.startswith("/")
        else posixpath.join(posixpath.dirname(owner), target)
    )
    require(
        result not in ("", ".", "..") and not result.startswith("../"), "target_escape"
    )
    return result


def relationships(files, owner):
    """Return uniquely identified internal relationships without inventing targets."""
    part = rels_part(owner)
    require(part in files, "relationship_part_missing")
    root = xml(files[part])
    require(root.tag == "{" + NS["rel"] + "}Relationships", "relationship_root")
    ids = [item.get("Id") for item in root]
    require(all(ids) and len(ids) == len(set(ids)), "relationship_id")
    for item in root:
        require(item.tag == "{" + NS["rel"] + "}Relationship", "relationship_element")
        require(
            item.get("TargetMode", "Internal") == "Internal", "external_relationship"
        )
        require(bool(item.get("Type")), "relationship_type")
        resolve_target(owner, item.get("Target", ""))
    return list(root)


def write_package(files):
    """Serialize verified parts without altering their uncompressed bytes."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return stream.getvalue()
