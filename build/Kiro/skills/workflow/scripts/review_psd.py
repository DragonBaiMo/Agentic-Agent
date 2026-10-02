"""SPDX-License-Identifier: MIT

Optional review images from independently reconstructed PSD layers.
Nothing here edits the PSD, chooses acceptable artwork or computes a pass score.
"""

from PIL import Image, ImageOps


def render(psd, layer_filter=None):
    """Reconstruct layer data instead of trusting the PSD merged-image cache."""
    return psd.composite(force=True, layer_filter=layer_filter).convert("RGBA")


def side_by_side(master, rebuilt):
    """Return a neutral two-up contact sheet: original left, reconstruction right."""
    size = rebuilt.size
    sheet = Image.new("RGB", (size[0] * 2, size[1]), "#e8e8e8")
    with Image.open(master) as image:
        sheet.paste(ImageOps.contain(image.convert("RGB"), size), (0, 0))
    sheet.paste(rebuilt, (size[0], 0), rebuilt)
    return sheet


def hide_view(psd, name, destination):
    """Render without one unique layer/folder; preserve visibility and update state."""
    matches = [layer for layer in psd.descendants() if layer.name == name]
    if len(matches) != 1:
        raise ValueError(f"toggle_name: {name}")
    target = matches[0]
    # NOTE: Setting visible marks the whole document updated, changing compositor
    # behavior even after restoring it. A read-only filter also respects hidden ancestors.
    render(psd, lambda layer: layer is not target and layer.is_visible()).save(destination)


def make_review(psd, out, master=None, toggles=()):
    """Create a reconstruction, optional master pairing and selected hide views."""
    rebuilt = render(psd)
    rebuilt.save(out / "reconstructed.png")
    files = {"reconstructed": "reconstructed.png", "toggles": []}
    if master:
        side_by_side(master, rebuilt).save(out / "master-left-rebuilt-right.png")
        files["comparison"] = "master-left-rebuilt-right.png"
    for index, name in enumerate(toggles):
        filename = f"hidden-{index + 1}.png"
        hide_view(psd, name, out / filename)
        files["toggles"].append({"layer": name, "file": filename})
    return files
