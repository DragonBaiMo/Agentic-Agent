"""SPDX-License-Identifier: MIT

Read image dimensions, real alpha extrema and threshold bounding boxes.
Usage: python scripts/probe_assets.py IMAGE [IMAGE ...]. This never edits pixels.
"""

import argparse
import json
from pathlib import Path

from PIL import Image


def alpha_distribution(alpha):
    """Count inclusive alpha bands; counts describe pixels, never material quality."""
    histogram = alpha.histogram()
    nonzero = sum(histogram[1:])
    near_opaque = sum(histogram[230:])
    return {"transparent_0": histogram[0], "translucent_1_229": sum(histogram[1:230]),
            "near_opaque_230_255": near_opaque, "opaque_255": histogram[255],
            "nonzero": nonzero,
            "near_opaque_fraction_of_nonzero": near_opaque / nonzero if nonzero else None}


def inspect(file):
    """Return image facts; RGB input is reported as opaque, never as a cutout."""
    with Image.open(file) as image:
        has_alpha = "A" in image.getbands()
        alpha = image.getchannel("A") if has_alpha else None
        return {"file": str(file), "size": list(image.size), "mode": image.mode,
                "alpha_extrema": list(alpha.getextrema()) if has_alpha else None,
                "alpha_distribution": alpha_distribution(alpha) if has_alpha else None,
                "alpha_bbox_comparison": "alpha > threshold",
                "alpha_bbox": {str(level): alpha.point(lambda value, level=level: 255 if value > level else 0).getbbox()
                               for level in (1, 50, 128, 230, 250)} if has_alpha else {}}


def main():
    """Inspect only explicitly supplied local files and emit one JSON array."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([inspect(file) for file in args.files], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
