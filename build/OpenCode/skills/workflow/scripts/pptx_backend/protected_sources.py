"""SPDX-License-Identifier: MIT

Validate opt-in original PNG declarations without modifying source assets.
Only ordinary, untransformed slide pictures using contain are supported.
"""

import hashlib
import io
import re
import warnings

from PIL import Image
from project_io import inside

MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_PIXELS = 50_000_000
# NOTE: Bound geometry before multiplying to EMU; this route is for static slides.
MAX_CANVAS_PX = 1_000_000


def png_source(root, declaration):
    """Read one bounded static PNG and return dimensions plus verified identity."""
    expected = declaration.get("sha256", "")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("protected_hash_format")
    path = inside(root, declaration["file"])
    with path.open("rb") as stream:
        body = stream.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise ValueError("protected_source_size_limit")
    if hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("protected_source_changed")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(body)) as image:
                if image.format != "PNG" or getattr(image, "is_animated", False):
                    raise ValueError("protected_static_png_required")
                size = image.size
                if size[0] * size[1] > MAX_SOURCE_PIXELS:
                    raise ValueError("protected_source_pixel_limit")
                image.verify()
            # NOTE: PNG chunk CRC checks do not decode IDAT; reject corrupt pixels too.
            with Image.open(io.BytesIO(body)) as image:
                image.load()
    except (
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValueError("protected_invalid_png") from error
    return {"sha256": expected, "size": size, "body": body}


def resolve_bindings(root, plan):
    """Resolve declared slide/object identities and reject unsupported protection."""
    check_canvas(plan.get("canvas"))
    declarations = plan.get("protected_media", [])
    if not isinstance(declarations, list):
        raise ValueError("protected_media_array_required")
    bindings, seen = [], set()
    for declaration in declarations:
        if not isinstance(declaration, dict):
            raise ValueError("protected_declaration_required")
        identity = (declaration.get("slide_id"), declaration.get("object_id"))
        if not all(isinstance(value, str) and value for value in identity):
            raise ValueError("protected_identity_required")
        if identity in seen:
            raise ValueError("protected_duplicate_binding")
        seen.add(identity)
        matches = [
            (index, item)
            for index, slide in enumerate(plan["slides"])
            if slide["id"] == identity[0]
            for item in slide["elements"]
            if item["id"] == identity[1]
        ]
        if len(matches) != 1:
            raise ValueError("protected_object_not_unique")
        index, item = matches[0]
        check_object(item, declaration)
        check_slot(item.get("box"), plan["canvas"])
        bindings.append(
            {
                "slide_index": index,
                "item": item,
                "declaration": declaration,
                **png_source(root, declaration),
            }
        )
    return bindings


def check_object(item, declaration):
    """Refuse masks/crops/layout moves instead of silently discarding declarations."""
    if item.get("kind") != "image" or item.get("file") != declaration.get("file"):
        raise ValueError("protected_file_or_kind_mismatch")
    if item.get("fit", "contain") != "contain" or item.get("fixed_layout", False):
        raise ValueError("protected_contain_slide_picture_required")
    unsupported = {
        "crop",
        "rotation",
        "flipHorizontal",
        "flipVertical",
        "geometry",
        "borderRadius",
        "opacity",
        "mask",
    }
    if unsupported.intersection(item):
        raise ValueError("protected_transform_unsupported")


def check_canvas(canvas):
    """Reject non-finite, boolean and excessive dimensions before geometry math."""
    if (
        not isinstance(canvas, list)
        or len(canvas) != 2
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 < value <= MAX_CANVAS_PX
            for value in canvas
        )
    ):
        raise ValueError("protected_canvas_invalid")


def check_slot(box, canvas):
    """Support only finite positive slots fully contained within the declared page."""
    if (
        not isinstance(box, list)
        or len(box) != 4
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and -MAX_CANVAS_PX <= value <= MAX_CANVAS_PX
            for value in box
        )
        or box[2] <= 0
        or box[3] <= 0
    ):
        raise ValueError("protected_slot_invalid")
    x, y, width, height = box
    if x < 0 or y < 0 or x + width > canvas[0] or y + height > canvas[1]:
        raise ValueError("protected_slot_outside_canvas")
