"""SPDX-License-Identifier: MIT

Restore optional numbered galleries and a self-contained layer viewer from LayerForge.
Export actual decoded PSD pixels. Viewer toggles do not edit or save the PSD.
"""

import argparse
import base64
import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw
from psd_tools import PSDImage

from project_io import write_json, read_json
from review_psd import render


def gallery(files, destination):
    """Create numbered candidate thumbnails; originals are never resized in place."""
    if not files:
        raise ValueError("gallery_empty")
    board = Image.new("RGB", (min(2, len(files)) * 400, math.ceil(len(files) / 2) * 600), "#eeeeee")
    draw = ImageDraw.Draw(board)
    for index, file in enumerate(files):
        with Image.open(file) as image:
            image = image.convert("RGB")
            image.thumbnail((376, 548))
            x, y = (index % 2) * 400 + 12, (index // 2) * 600 + 12
            board.paste(image, (x, y))
            draw.text((x, y + 562), str(index + 1), fill="black")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    board.save(destination)
    write_json(destination.with_suffix(".json"), {str(i + 1): str(p) for i, p in enumerate(files)})
    return str(destination)


def uri(file):
    """Embed trusted, locally generated review PNG bytes without a remote server."""
    return "data:image/png;base64," + base64.b64encode(Path(file).read_bytes()).decode("ascii")


def viewer(psd_file, master, out):
    """Create a real local viewer with actual raster/type cache pixels and blend modes."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    psd = PSDImage.open(psd_file)
    rows = []
    modes = {b"norm": "normal", b"mul ": "multiply", b"scrn": "screen", b"over": "overlay"}
    for index, layer in enumerate(item for item in psd.descendants() if not item.is_group()):
        surface = Image.new("RGBA", psd.size)
        surface.paste(layer.topil().convert("RGBA"), (layer.left, layer.top))
        file = out / f"layer-{index + 1}.png"
        surface.save(file)
        rows.append({"id": str(index + 1), "name": layer.name, "image": uri(file),
                     "blend": modes[layer.blend_mode.value], "opacity": layer.opacity / 255})
    master_copy = out / "master.png"
    with Image.open(master) as image:
        image.convert("RGBA").save(master_copy)
    messages = read_json(Path(__file__).parents[1] / "resources/messages.zh-CN.json")
    data = {"width": psd.width, "height": psd.height, "layers": rows,
            "conformance_note": messages["viewer_note"]}
    template = (Path(__file__).parents[1] / "resources/review.html").read_text(encoding="utf-8")
    page = template.replace("%%TITLE%%", html.escape(Path(psd_file).stem)).replace("%%MASTER%%", uri(master_copy))
    page = page.replace("%%DATA%%", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (out / "review.html").write_text(page, encoding="utf-8")
    return {"viewer": str(out / "review.html"), "layers": len(rows)}


def moved_view(psd_file, name, out):
    """Move one leaf only in memory to expose attached background/text contamination."""
    psd = PSDImage.open(psd_file)
    matches = [layer for layer in psd.descendants() if not layer.is_group() and layer.name == name]
    if len(matches) != 1:
        raise ValueError("move_requires_unique_leaf")
    layer = matches[0]
    before = layer.offset
    layer.offset = (before[0] + max(1, round(psd.width * 0.05)), before[1])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    render(psd).save(out)
    return {"diagnostic": str(out), "production_psd_modified": False}


def main():
    """Choose one optional visual aid; normal production does not run all aids."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("gallery", "viewer", "move"))
    parser.add_argument("--images", nargs="+", type=Path)
    parser.add_argument("--psd", type=Path)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--layer")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "gallery":
        result = gallery(args.images, args.out)
    elif args.command == "viewer":
        result = viewer(args.psd, args.master, args.out)
    else:
        result = moved_view(args.psd, args.layer, args.out)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
