"""SPDX-License-Identifier: MIT

Shared project paths, atomic JSON, provenance and plan-to-manifest conversion.
No approval engine or model calls. Mutating commands are single-writer tools.
"""

import hashlib
import json
import uuid
from pathlib import Path


def read_json(path):
    """Read explicit local UTF-8 project data; never execute content as code."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def inside(root, relative):
    """Resolve project-owned paths and reject traversal and symlink escapes."""
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("path_outside_project")
    return path


def write_json(path, value):
    """Atomically replace one small project document, not a whole asset directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    """Return a byte identity for provenance, not an artwork similarity score."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_plan(root):
    """Check identifiers needed to route jobs; visual approval is not a field gate."""
    return validate_plan(read_json(Path(root) / "plan.json"))


def validate_plan(plan):
    """Validate an in-memory plan without writes, preserving existing load behavior."""
    identifiers = [item["id"] for item in plan["layers"]]
    copies = [item["id"] for item in plan["copy"]]
    if len(set(identifiers)) != len(identifiers) or len(set(copies)) != len(copies):
        raise ValueError("duplicate_id")
    if len(plan["canvas"]) != 2 or any(not isinstance(v, int) or v < 16 for v in plan["canvas"]):
        raise ValueError("canvas")
    return plan


def compile_plan(root):
    """Convert logical text ownership and actual source filenames to the tested backend."""
    root = Path(root)
    plan = load_plan(root)
    copy = {item["id"]: item["value"] for item in plan["copy"]}
    result = {"name": plan["output_name"], "width": plan["canvas"][0],
              "height": plan["canvas"][1], "groups": plan["groups"],
              "asset_dir": "assets", "fonts": plan.get("fonts", []), "art": [], "text": []}
    for layer in plan["layers"]:
        item = {key: layer[key] for key in ("name", "group", "z", "blend", "opacity", "hidden") if key in layer}
        if layer["type"] == "native_text":
            item.update(layer["style"])
            item.update(value=copy[layer["copy_id"]], copy_id=layer["copy_id"])
            result["text"].append(item)
        elif layer["type"] == "image":
            file = layer.get("file")
            if not file or Path(file).name != file or not inside(root, "assets/" + file).is_file():
                raise ValueError("missing_asset: " + layer["id"])
            size = layer["source_size"]
            item.update(file=file, source_size=size, kind=layer["kind"], expect_alpha=layer.get("alpha", False),
                        crop=layer.get("crop", [0, 0, *size]),
                        destination=layer.get("destination", [0, 0, *plan["canvas"]]),
                        copy_ids=layer.get("copy_ids", []))
            result["art"].append(item)
        else:
            raise ValueError("unsupported_layer_type: " + layer["type"])
    write_json(root / "manifest.json", result)
    return {"manifest": str(root / "manifest.json"), "image_layers": len(result["art"]), "native_text_layers": len(result["text"])}
