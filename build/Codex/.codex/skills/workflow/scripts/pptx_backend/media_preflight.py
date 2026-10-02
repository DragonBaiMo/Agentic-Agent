"""SPDX-License-Identifier: MIT

Read-only audiovisual preflight for the current JS import/export route.
Inspect bounded XML and ZIP metadata only; never extract media or follow links.
"""

import hashlib
import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAX_PARTS = 10000
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_TOTAL_XML_BYTES = 64 * 1024 * 1024
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MEDIA_EXTENSIONS = {
    ".mp4", ".m4v", ".mov", ".avi", ".wmv", ".webm", ".mkv", ".mpg", ".mpeg",
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".aif", ".aiff",
}
DRAWING_NAMESPACES = {
    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "http://purl.oclc.org/ooxml/drawingml/main",
}
PRESENTATION_NAMESPACES = {
    "http://schemas.openxmlformats.org/presentationml/2006/main",
    "http://purl.oclc.org/ooxml/presentationml/main",
}
PLAYBACK_TAGS = {
    f"{{{ns}}}{tag}" for ns in DRAWING_NAMESPACES
    for tag in ("videoFile", "audioFile", "wavAudioFile", "audioCd")
} | {
    f"{{{ns}}}{tag}" for ns in PRESENTATION_NAMESPACES for tag in ("video", "audio")
} | {
    "{http://schemas.microsoft.com/office/powerpoint/2010/main}media",
    "{http://schemas.microsoft.com/office/powerpoint/2012/main}webVideoPr",
}


def source_identity(source):
    """Hash source bytes in bounded chunks without loading embedded video into memory."""
    digest = hashlib.sha256()
    with Path(source).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def xml_parts(archive):
    """Read bounded, unique XML parts; malformed or encrypted inputs are not clear."""
    entries = [entry for entry in archive.infolist() if not entry.is_dir()]
    names = [entry.filename for entry in entries]
    if len(names) > MAX_PARTS or len(names) != len(set(names)):
        raise ValueError("media_preflight_duplicate_or_many_parts")
    if "[Content_Types].xml" not in names or "_rels/.rels" not in names:
        raise ValueError("media_preflight_not_pptx")
    if any(entry.flag_bits & 1 for entry in entries):
        raise ValueError("media_preflight_encrypted_package")
    selected = [entry for entry in entries if entry.filename.endswith((".xml", ".rels"))]
    if sum(entry.file_size for entry in selected) > MAX_TOTAL_XML_BYTES:
        raise ValueError("media_preflight_total_xml_limit")
    result = {}
    for entry in selected:
        if entry.file_size > MAX_XML_BYTES or entry.flag_bits & 1:
            raise ValueError("media_preflight_large_or_encrypted_xml")
        body = archive.read(entry)
        # NOTE: Do not expand DTD entities or reinterpret unsupported XML encodings.
        if b"\x00" in body or re.search(rb"<!\s*(DOCTYPE|ENTITY)", body, re.IGNORECASE):
            raise ValueError("media_preflight_unsupported_xml")
        result[entry.filename] = ET.fromstring(body)
    validate_roots(result)
    return names, result


def validate_roots(parts):
    """Require an actual presentation root; parseable arbitrary ZIPs are not PPTX."""
    if parts["[Content_Types].xml"].tag != f"{{{CONTENT_NS}}}Types":
        raise ValueError("media_preflight_content_types_root")
    roots = [item for item in parts["_rels/.rels"]
             if item.get("Type", "").endswith("/officeDocument")]
    if len(roots) != 1 or roots[0].get("TargetMode") == "External":
        raise ValueError("media_preflight_presentation_relationship")
    main = internal_target("_rels/.rels", roots[0].get("Target"))
    if main not in parts or parts[main].tag not in {
            f"{{{ns}}}presentation" for ns in PRESENTATION_NAMESPACES}:
        raise ValueError("media_preflight_presentation_root")


def internal_target(part, target):
    """Resolve a ZIP-relative relationship target only; never access its destination."""
    if not target or "\\" in target or ":" in target:
        return None
    owner = "" if part == "_rels/.rels" else part.replace("/_rels/", "/")[:-5]
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), target)).lstrip("/")
    return None if resolved.startswith("../") else resolved


def relationship_findings(parts, names):
    """Classify embedded/external media by relationship type, independently of suffix."""
    findings, referenced = [], set()
    for part, tree in parts.items():
        if not part.endswith(".rels"):
            continue
        if tree.tag != f"{{{REL_NS}}}Relationships":
            raise ValueError("media_preflight_relationship_root")
        ids = [item.get("Id") for item in tree]
        if None in ids or len(ids) != len(set(ids)):
            raise ValueError("media_preflight_relationship_ids")
        for relation in tree:
            if (relation.tag != f"{{{REL_NS}}}Relationship"
                    or not relation.get("Type") or not relation.get("Target")):
                raise ValueError("media_preflight_relationship_record")
            external = relation.get("TargetMode") == "External"
            target = None if external else internal_target(part, relation.get("Target"))
            if target:
                referenced.add(target)
            kind = relation.get("Type", "").rsplit("/", 1)[-1]
            if kind not in {"video", "audio", "media"}:
                continue
            # NOTE: External URLs can contain secrets; record their ID and mode, not the URL.
            findings.append({"kind": "media_relationship", "part": part,
                             "relationship_id": relation.get("Id"), "media_kind": kind,
                             "mode": "external" if external else "embedded",
                             "internal_part": target,
                             "target_present": None if external else target in names})
    return findings, referenced


def content_types(tree):
    """Reject ambiguous declarations instead of allowing a later image type to hide video."""
    defaults, overrides = {}, {}
    for item in tree:
        if item.tag == f"{{{CONTENT_NS}}}Default":
            target, key = defaults, item.get("Extension", "").lower()
        elif item.tag == f"{{{CONTENT_NS}}}Override":
            target, key = overrides, item.get("PartName", "").lstrip("/")
        else:
            raise ValueError("media_preflight_content_type_record")
        mime = item.get("ContentType", "")
        if not key or key in target or not re.fullmatch(r"[^\s/]+/[^\s/]+", mime):
            raise ValueError("media_preflight_content_type_ambiguous")
        target[key] = mime
    return defaults, overrides


def payload_findings(names, parts, referenced):
    """Separate actual audiovisual parts from unused MIME declarations and PNG posters."""
    defaults, overrides = content_types(parts["[Content_Types].xml"])
    findings = []
    for name in names:
        suffix = posixpath.splitext(name)[1].lower()
        mime = overrides.get(name, defaults.get(suffix.lstrip("."), ""))
        typed_media = mime.lower().startswith(("video/", "audio/"))
        if typed_media or suffix in MEDIA_EXTENSIONS:
            findings.append({"kind": "referenced_media_part" if name in referenced
                             else "orphan_media_part", "part": name,
                             "content_type": mime or None,
                             "detected_by": "content_type" if typed_media else "filename"})
    return findings


def inspect_media(source):
    """Return CLEAR/BLOCKED/UNKNOWN for media risk only; source and URLs stay untouched.

    CLEAR permits existing edit checks to continue, not a full-fidelity approval.
    UNKNOWN fails closed when the source cannot be safely inspected.
    """
    result = {"scope": "audiovisual_media_only", "status": "UNKNOWN",
              "source_sha256": None, "findings": [], "full_fidelity_verified": False}
    try:
        before = Path(source).stat()
        result["source_sha256"] = source_identity(source)
        with ZipFile(source) as archive:
            names, parts = xml_parts(archive)
        findings, referenced = relationship_findings(parts, set(names))
        findings.extend(payload_findings(names, parts, referenced))
        findings.extend({"kind": "playback_object", "part": name, "element": element.tag}
                        for name, tree in parts.items() for element in tree.iter()
                        if element.tag in PLAYBACK_TAGS)
        after = Path(source).stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("media_preflight_source_changed")
        result.update(status="BLOCKED" if findings else "CLEAR", findings=findings)
    except (OSError, ValueError, KeyError, RuntimeError, BadZipFile, ET.ParseError) as error:
        result["reason"] = str(error)
    return result
