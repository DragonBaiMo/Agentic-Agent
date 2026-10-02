"""SPDX-License-Identifier: MIT

Start, resume, snapshot and compile a PSD project without approval tickets.
Usage: python scripts/project.py init --project DIR --plan PLAN.json
"""

import argparse
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from environment_check import inspect_environment
from project_io import (
    compile_plan,
    inside,
    load_plan,
    read_json,
    validate_plan,
    write_json,
)


def snapshot(root):
    """Save the active plan and receipts; generated assets remain immutable in place."""
    target = Path(root) / "revisions" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6])
    target.mkdir(parents=True)
    for name in ("plan.json", "receipts.json"):
        source = Path(root) / name
        if source.exists():
            shutil.copy2(source, target / name)
    return {"snapshot": str(target)}


def initialize(root, plan_file):
    """Validate known plan constraints before writing; preserve existing projects."""
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError("project_not_empty")
    # NOTE: Invalid identifiers/canvas must not leave a directory that blocks retry.
    # I/O failures during the subsequent writes can still leave partial output.
    plan = validate_plan(read_json(plan_file))
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("inputs", "design", "assets", "jobs", "rejected", "review", "builds", "revisions", "logs"):
        (root / folder).mkdir(exist_ok=True)
    write_json(root / "plan.json", plan)
    write_json(root / "receipts.json", [])
    return status(root)


def status(root):
    """Report observable files and pending work, not a synthetic approval status."""
    root = Path(root)
    plan = load_plan(root)
    images = [item for item in plan["layers"] if item["type"] == "image"]
    available = [item["id"] for item in images if item.get("file") and inside(root, "assets/" + item["file"]).is_file()]
    master = plan.get("master", {}).get("file")
    return {"project": str(root), "entry": plan["entry"], "master_exists": bool(master and inside(root, master).is_file()),
            "available_images": available, "pending_images": [item["id"] for item in images if item["id"] not in available],
            "native_text_roles": [item["copy_id"] for item in plan["layers"] if item["type"] == "native_text"],
            "receipts": len(read_json(root / "receipts.json")), "resume_note": plan.get("resume_note", "")}


def restore(root, source):
    """Restore a named project snapshot after saving the current pointers; never delete images."""
    root = Path(root).resolve()
    source = Path(source).resolve()
    if not source.is_relative_to(root / "revisions") or not (source / "plan.json").is_file():
        raise ValueError("invalid_snapshot")
    saved = snapshot(root)
    for name in ("plan.json", "receipts.json"):
        if (source / name).is_file():
            write_json(root / name, read_json(source / name))
    return {"restored": str(source), "previous": saved["snapshot"]}


def main():
    """Run a bounded project command; stdout is JSON and failures are nonzero."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "init", "status", "snapshot", "restore", "compile"))
    parser.add_argument("--project", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "doctor":
        plan_file = args.plan or (args.project / "plan.json" if args.project else None)
        result = inspect_environment(plan_file)
    else:
        if not args.project:
            parser.error("--project")
        if args.command == "init" and not args.plan:
            parser.error("--plan")
        if args.command == "restore" and not args.snapshot:
            parser.error("--snapshot")
        operations = {"init": lambda: initialize(args.project, args.plan), "status": lambda: status(args.project),
                      "snapshot": lambda: snapshot(args.project), "restore": lambda: restore(args.project, args.snapshot),
                      "compile": lambda: compile_plan(args.project)}
        result = operations[args.command]()
    print(json.dumps(result, ensure_ascii=False))  # NOTE: CLI result, not an application log.


if __name__ == "__main__":
    main()
