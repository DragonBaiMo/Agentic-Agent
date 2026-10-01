"""SPDX-License-Identifier: MIT

Independently read real PSD layers. No similarity scores or artistic gates.
Usage: python scripts/verify_psd.py --psd FILE --config JSON --out DIR
"""

import argparse
import json
import logging
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage

from review_psd import make_review

MESSAGES = json.loads((Path(__file__).parents[1] / "resources/messages.zh-CN.json").read_text())
LOGGER = logging.getLogger("workflow.verify")
LOGGER.addHandler(logging.NullHandler())


def require(condition, detail):
    """Raise even under Python -O; packaging errors must never become silent passes."""
    if not condition:
        raise ValueError(f'{MESSAGES["structure_failed"]}: {detail}')


def ordered(config, group):
    """Match the assembler's stable bottom-to-top ordering inside one folder."""
    items = config["art"] + config["text"]
    return [item for _, item in sorted(enumerate(items),
            key=lambda pair: pair[1].get("z", pair[0])) if item["group"] == group]


def check_structure(psd, config):
    """Validate each named layer's type, text, ordering, visibility and basic pixels."""
    require(psd.size == (config["width"], config["height"]), "dimensions")
    require([group.name for group in psd] == config["groups"], "groups")
    result = []
    for group in psd:
        require(group.is_group(), group.name)
        items = ordered(config, group.name)
        require([layer.name for layer in group] == [item["name"] for item in items], "layer_order")
        for layer, item in zip(group, items):
            result.append(check_layer(layer, item))
    require(len(result) >= 2, "not_layered")
    return result


def check_layer(layer, item):
    """Read pixels and native text by exact layer identity, never a sorted text bag."""
    expected_type = "type" if "value" in item else "pixel"
    require(layer.kind == expected_type, f'{item["name"]}: type')
    if expected_type == "type":
        require(layer.text == item["value"], f'{item["name"]}: text')
    require(layer.visible == (not item.get("hidden", False)), f'{item["name"]}: visible')
    require(abs(layer.opacity / 255 - item.get("opacity", 1)) <= 1 / 255, "opacity")
    blend_keys = {"normal": b"norm", "multiply": b"mul ", "screen": b"scrn", "overlay": b"over"}
    require(layer.blend_mode.value == blend_keys[item.get("blend", "normal")], "blend")
    image = layer.topil()
    require(image is not None, f'{item["name"]}: pixels')
    alpha = image.convert("RGBA").getchannel("A").getextrema()
    require(alpha[1] > 0, f'{item["name"]}: empty')
    # NOTE: PSD may trim transparent margins. Source-alpha validation is in assembly.
    return {"name": layer.name, "type": layer.kind, "bounds": list(layer.bbox),
            "alpha_extrema": list(alpha), "visible": layer.visible,
            "blend": item.get("blend", "normal"), "opacity": layer.opacity / 255}


def verify(args):
    """Run bounded technical checks and optionally produce images for a visual reviewer."""
    config = json.loads(args.config.read_text(encoding="utf-8"))
    psd = PSDImage.open(args.psd)
    layers = check_structure(psd, config)
    if args.preview:
        with Image.open(args.preview) as preview:
            require(preview.size == psd.size, "preview_dimensions")
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"technical_passed": True, "dimensions": list(psd.size),
              "groups": len(psd), "layers": layers,
              "native_type_layers": len(config["text"]),
              "visual_review": "not_performed_by_code", "photoshop_gui": "not_tested"}
    if args.review:
        report["review_files"] = make_review(psd, args.out, args.master, args.toggle)
    (args.out / "independent-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def arguments():
    """Explicit files only; at most eight selected toggles avoid accidental huge jobs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psd", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--master", type=Path)
    parser.add_argument("--toggle", action="append", default=[])
    args = parser.parse_args()
    require(len(args.toggle) <= 8, "toggle_limit")
    require(args.review or not (args.master or args.toggle), "review_required")
    return args


def main():
    """Write structured status and persistent logs without storing user copy in logs."""
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    log_dir = args.out / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / "verification.jsonl", encoding="utf-8")
    handler.setFormatter(logging.Formatter('{"timestamp":"%(asctime)s","level":"%(levelname)s","message":%(message)s}'))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    try:
        report = verify(args)
        LOGGER.info(json.dumps(MESSAGES["review_done"], ensure_ascii=False))
        print(json.dumps(report, ensure_ascii=False))  # NOTE: CLI result protocol, not a log.
    except Exception as error:
        LOGGER.error(json.dumps({"message": MESSAGES["verify_failed"], "error": str(error)}, ensure_ascii=False))
        raise


if __name__ == "__main__":
    main()
