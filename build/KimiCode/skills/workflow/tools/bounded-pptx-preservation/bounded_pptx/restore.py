"""SPDX-License-Identifier: MIT

Prove and restore one static native chart's lost original workbook dependency.
Input bytes are immutable; all facts are recomputed here, never caller supplied.
"""

import copy
import re
from xml.etree import ElementTree as ET

from .opc import (
    NS,
    digest,
    read_package,
    relationships,
    rels_part,
    require,
    resolve_target,
    tree_value,
    write_package,
    xml,
)
from .workbook import verify_workbook

CHART_TYPE = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TYPES = "[Content_Types].xml"


def chart_part(files):
    """Require one declared and one actual chart root with the same part identity."""
    types = xml(files[TYPES])
    require(types.tag == "{" + NS["ct"] + "}Types", "content_types_root")
    declared = [
        node.get("PartName", "").lstrip("/")
        for node in types
        if node.get("ContentType") == CHART_TYPE
    ]
    actual = [
        name
        for name, body in files.items()
        if name.endswith(".xml") and xml(body).tag == "{" + NS["c"] + "}chartSpace"
    ]
    require(
        len(declared) == len(actual) == 1 and declared == actual,
        "single_chart_required",
    )
    return actual[0]


def chart_owner(files, part):
    """Resolve the native chart from its real slide relationship, rejecting reuse."""
    owners = []
    for name, data in files.items():
        match = re.fullmatch(r"ppt/slides/slide([1-9][0-9]*)\.xml", name)
        if match is None:
            continue
        refs = xml(data).findall(".//c:chart", NS)
        if not refs:
            continue
        edges = {node.get("Id"): node for node in relationships(files, name)}
        for ref in refs:
            edge = edges.get(ref.get("{" + NS["r"] + "}id"))
            require(
                edge is not None and edge.get("Type") == NS["r"] + "/chart",
                "chart_owner_relation",
            )
            assert (
                edge is not None
            )  # NOTE: require() rejects missing edges even under python -O.
            require(
                resolve_target(name, edge.get("Target")) == part, "chart_owner_target"
            )
            owners.append(int(match.group(1)))
    require(len(owners) == 1, "chart_owner_not_unique")
    return owners[0]


def original_dependency(source, authored, part):
    """Prove source chart identity after removing only its single externalData node."""
    original = xml(source[part])
    reduced = copy.deepcopy(original)
    external = reduced.findall("c:externalData", NS)
    require(len(external) == 1, "external_data_not_unique")
    relations = relationships(source, part)
    require(len(relations) == 1, "chart_dependency_not_unique")
    relation = relations[0]
    require(relation.get("Type") == NS["r"] + "/package", "chart_dependency_type")
    require(
        relation.get("Id") == external[0].get("{" + NS["r"] + "}id"),
        "external_data_relationship",
    )
    workbook = resolve_target(part, relation.get("Target"))
    require(
        workbook.startswith("ppt/embeddings/") and workbook.endswith(".xlsx"),
        "workbook_target",
    )
    require(
        [name for name in source if name.endswith(".xlsx")] == [workbook],
        "single_workbook_required",
    )
    require(
        not any(name.endswith(".xlsx") for name in authored),
        "authored_workbook_collision",
    )
    require(rels_part(part) not in authored, "authored_chart_relationship_collision")
    reduced.remove(external[0])
    require(
        tree_value(reduced) == tree_value(xml(authored[part])), "chart_identity_changed"
    )
    return workbook, verify_workbook(source[workbook], original)


def restore_content_type(source, authored, workbook):
    """Append only the original xlsx Default, leaving all authored types intact."""
    old, new = xml(source[TYPES]), xml(authored[TYPES])
    originals = [node for node in old if node.get("Extension") == "xlsx"]
    require(
        len(originals) == 1 and originals[0].tag == "{" + NS["ct"] + "}Default",
        "source_xlsx_type_not_unique",
    )
    require(originals[0].get("ContentType") == XLSX_TYPE, "source_xlsx_type_invalid")
    require(
        not any(
            node.get("Extension") == "xlsx" or node.get("PartName") == "/" + workbook
            for node in new
        ),
        "authored_xlsx_type_collision",
    )
    require(
        not any(node.get("PartName") == "/" + workbook for node in old),
        "source_xlsx_type_ambiguous",
    )
    new.append(copy.deepcopy(originals[0]))
    # NOTE: OPC requires the content-types namespace as the default for this part.
    ET.register_namespace("", NS["ct"])
    return ET.tostring(new, encoding="utf-8", xml_declaration=True)


def restore_dependencies(source_bytes, authored_bytes):
    """Return restored bytes and proof; reject every unproved dependency condition.

    This operation never writes slide/notes parts or constructs a new workbook.
    It preserves the authoring tool's output and restores only original bytes.
    """
    source, authored = read_package(source_bytes), read_package(authored_bytes)
    part = chart_part(source)
    require(chart_part(authored) == part, "chart_part_changed")
    owner = chart_owner(source, part)
    require(chart_owner(authored, part) == owner, "chart_owner_changed")
    workbook, validation = original_dependency(source, authored, part)
    restored = dict(authored)
    restored[TYPES] = restore_content_type(source, authored, workbook)
    original_parts = [part, rels_part(part), workbook]
    for name in original_parts:
        restored[name] = source[name]
    changed = sorted(name for name in authored if authored[name] != restored[name])
    added = sorted(set(restored) - set(authored))
    require(changed == sorted([part, TYPES]), "unexpected_changed_part")
    require(added == sorted([rels_part(part), workbook]), "unexpected_added_part")
    output = write_package(restored)
    require(read_package(output) == restored, "output_roundtrip_mismatch")
    proof = {
        "source_sha256": digest(source_bytes),
        "authored_sha256": digest(authored_bytes),
        "restored_sha256": digest(output),
        "chart_owner_slide": owner,
        "restored_parts": {name: digest(source[name]) for name in original_parts},
        "changed_parts": changed,
        "added_parts": added,
        "removed_parts": [],
        "authored_slide_and_notes_bytes_unchanged": True,
        "workbook": validation,
    }
    return output, proof
