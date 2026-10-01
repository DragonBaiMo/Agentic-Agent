"""SPDX-License-Identifier: MIT

Export one pure visual prompt and actual reference. This does not invoke a model.
Usage: python scripts/visual_job.py --project DIR --task LAYER_ID --out NEW_DIR
"""

import argparse
import json
from pathlib import Path
import shutil

from project_io import digest, inside, load_plan, write_json


def prepare(root, task, destination):
    """Bind one task to real reference bytes, filtering copy to the owned text roles."""
    root, destination = Path(root), Path(destination)
    if destination.exists():
        raise ValueError("job_exists")
    plan = load_plan(root)
    copy = {item["id"]: item["value"] for item in plan["copy"]}
    reference = plan.get("master", {}).get("file")
    if task == "master":
        template = "design.txt"
        values = {"width": plan["canvas"][0], "height": plan["canvas"][1],
                  "direction": plan["direction"], "copy": "\n".join(copy.values())}
        alpha = False
    else:
        layer = next(item for item in plan["layers"] if item["id"] == task)
        if layer["type"] != "image":
            raise ValueError("native_text_uses_typesetter")
        if not reference:
            raise ValueError("master_required")
        # NOTE: Typography must not inherit a neighboring object's glass material.
        template = {"background": "background.txt", "typography": "typography.txt",
                    "glass": "glass.txt"}.get(layer["kind"], "layer.txt")
        values = {"width": plan["canvas"][0], "height": plan["canvas"][1], "owns": layer["owns"],
                  "excludes": layer.get("excludes", ""), "occlusion": layer.get("occlusion", "自然补全被遮挡处"),
                  "copy": "\n".join(copy[key] for key in layer.get("copy_ids", [])) or "无文字",
                  "target": str(layer.get("target_box", "沿用参考图位置")),
                  "effects": str(layer.get("effect_box", "保留自然软边，不额外扩散"))}
        alpha = layer.get("alpha", False)
        values["background"] = "真实透明" if alpha else "完整不透明画面"
    body = (Path(__file__).parents[1] / "prompts" / template).read_text(encoding="utf-8").format(**values)
    source = inside(root, reference) if reference else None
    if source and not source.is_file():
        raise ValueError("reference_missing")
    destination.mkdir(parents=True)
    (destination / "DRAW.txt").write_text(body, encoding="utf-8")
    reference_name = None
    if source:
        reference_name = "reference" + source.suffix.lower()
        shutil.copy2(source, destination / reference_name)
    receipt = {"task": task, "status": "prepared_not_executed", "record_scope": "preparation_snapshot",
               "prompt_template": template, "reference_file": reference_name,
               "source_reference": reference, "reference_sha256": digest(source) if source else None,
               "prompt_sha256": digest(destination / "DRAW.txt"), "transparent_background": alpha,
               "backend_binding_observed": False, "effective_backend_prompt": "not_exposed"}
    write_json(destination / "request.json", receipt)
    return receipt


def main():
    """Explicit project/task/output arguments; no implicit API or credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, args.task, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
