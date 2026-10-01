"""SPDX-License-Identifier: MIT

Keep actual returned images and receipts; rejected assets never become active.
Usage: python scripts/record_asset.py --project DIR --task ID --source IMAGE --origin user_supplied --tool user_upload
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid

from PIL import Image

from execution_record import execution_result
from project import snapshot
from project_io import digest, load_plan, read_json, write_json


def record(root, task, source, origin, tool, job=None, call_id="not_exposed", status="usable", reason="", execution=None):
    """Copy a real image, retain provenance, and optionally adopt it after caller visual review."""
    root, source = Path(root), Path(source)
    plan = load_plan(root)
    layer = None if task == "master" else next(item for item in plan["layers"] if item["id"] == task)
    if layer and layer["type"] != "image":
        raise ValueError("native_text_uses_typesetter")
    if origin == "generated" and not job:
        raise ValueError("generated_asset_requires_job")
    request = read_json(Path(job) / "request.json") if job else None
    if request and request["task"] != task:
        raise ValueError("wrong_job_task")
    with Image.open(source) as image:
        size, mode = list(image.size), image.mode
        image.verify()
    if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("unsupported_image_extension")
    executed = execution_result(source, origin, tool, call_id, execution)
    identifier = uuid.uuid4().hex[:12]
    # SAFETY(1.1): IDs, not source filenames or layer names, form writable basenames.
    relative = ("assets/" if status == "usable" else "rejected/") + identifier + source.suffix.lower()
    shutil.copy2(source, root / relative)
    receipt = {"id": identifier, "task": task, "file": relative, "sha256": digest(source),
               "size": size, "mode": mode, "origin": origin, "tool": tool, "call_id": call_id,
               "status": status, "reason": reason, "request": request,
               "request_scope": "preparation_snapshot", "execution": executed,
               "recorded_at": datetime.now(timezone.utc).isoformat()}
    receipt["requested_visual_prompt"] = (Path(job) / "DRAW.txt").read_text(encoding="utf-8") if job else "not_exposed"
    snapshot(root)
    receipts = read_json(root / "receipts.json")
    receipts.append(receipt)
    write_json(root / "receipts.json", receipts)
    if status == "usable":
        if task == "master":
            plan["master"] = {"file": relative, "origin": origin, "receipt_id": identifier}
        else:
            layer.update(file=Path(relative).name, source_size=size, receipt_id=identifier)
        write_json(root / "plan.json", plan)
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    with (logs / "assets.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"timestamp": receipt["recorded_at"], "level": "INFO", "event": "asset_recorded",
                                "asset_id": identifier, "status": status}) + "\n")
    return {"receipt": receipt, "visual_approval": "caller_decision_not_code_score",
            "next": "recheck placement and master consistency before compiling"}


def main():
    """Require actual source/tool provenance; do not invent a tool call ID."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--origin", required=True, choices=("generated", "user_supplied", "conversation_history"))
    parser.add_argument("--tool", required=True)
    parser.add_argument("--job", type=Path)
    parser.add_argument("--call-id", default="not_exposed")
    parser.add_argument("--status", choices=("usable", "rejected"), default="usable")
    parser.add_argument("--reason", default="")
    parser.add_argument("--execution", type=Path)
    args = parser.parse_args()
    print(json.dumps(record(args.project, args.task, args.source, args.origin, args.tool,
                            args.job, args.call_id, args.status, args.reason, args.execution), ensure_ascii=False))


if __name__ == "__main__":
    main()
