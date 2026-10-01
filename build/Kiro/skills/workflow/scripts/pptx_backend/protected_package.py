"""SPDX-License-Identifier: MIT

Read-only proof of protected PNG bytes, ownership and contain geometry in PPTX.
Reuse the published bounded OPC boundary; never create or repair OOXML parts.
"""

import re
import sys
from pathlib import Path

from pptx_backend.protected_sources import check_canvas, resolve_bindings

# NOTE: The tool is shipped with workflow and exposes OPC through its public root.
sys.path.insert(0, str(Path(__file__).parents[2] / "tools/bounded-pptx-preservation"))
from bounded_pptx import opc

NS = {
    **opc.NS,
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def ordered_slides(files, canvas):
    """Resolve actual presentation order, not guessed slide filenames."""
    roots = [
        r
        for r in opc.relationships(files, "")
        if r.get("Type") == NS["r"] + "/officeDocument"
    ]
    opc.require(len(roots) == 1, "protected_presentation_relationship")
    part = opc.resolve_target("", roots[0].get("Target"))
    root = opc.xml(files[part])
    sizes = root.findall("p:sldSz", NS)
    check_canvas(canvas)
    opc.require(
        len(sizes) == 1
        and all(
            sizes[0].get(k) == str(round(v * 9525))
            for k, v in zip(("cx", "cy"), canvas)
        ),
        "protected_canvas_mismatch",
    )
    rels = {r.get("Id"): r for r in opc.relationships(files, part)}
    slides = []
    for item in root.findall("p:sldIdLst/p:sldId", NS):
        relation = rels.get(item.get("{" + NS["r"] + "}id"))
        if relation is None or relation.get("Type") != NS["r"] + "/slide":
            raise opc.Unsupported("protected_slide_relationship")
        slides.append(opc.resolve_target(part, relation.get("Target")))
    opc.require(len(slides) == len(set(slides)), "protected_duplicate_slide_part")
    return slides


def check_png_type(files, media):
    """Verify the resolved OPC content type, not merely a PNG-looking extension."""
    root = opc.xml(files["[Content_Types].xml"])
    types = [
        r.get("ContentType")
        for r in root.findall("ct:Override", NS)
        if r.get("PartName") == "/" + media
    ]
    if not types:
        types = [
            r.get("ContentType")
            for r in root.findall("ct:Default", NS)
            if r.get("Extension") == media.rsplit(".", 1)[-1]
        ]
    opc.require(types == ["image/png"], "protected_content_type")


def zero_rectangle(element):
    """Accept only absent or explicitly zero crop/fill insets."""
    return element is None or (
        not list(element)
        and set(element.attrib) <= {"l", "t", "r", "b"}
        and all(value == "0" for value in element.attrib.values())
    )


def expected_frame(binding):
    """Compute centered contain geometry in EMU from the original pixel ratio."""
    x, y, width, height = binding["item"]["box"]
    source_width, source_height = binding["size"]
    scale = min(width / source_width, height / source_height)
    fitted_width, fitted_height = source_width * scale, source_height * scale
    return [
        round(value * 9525)
        for value in (
            x + (width - fitted_width) / 2,
            y + (height - fitted_height) / 2,
            fitted_width,
            fitted_height,
        )
    ]


def check_geometry(pic, binding, canvas):
    """Refuse crop, effects, masked shapes, rotation, flips and moved/stretched frames."""
    fill = pic.find("p:blipFill", NS)
    opc.require(
        fill is not None and set(fill.attrib) <= {"dpi", "rotWithShape"},
        "protected_blip_fill",
    )
    opc.require(
        all(
            c.tag in {"{" + NS["a"] + "}" + t for t in ("blip", "srcRect", "stretch")}
            for c in fill
        ),
        "protected_fill_transform",
    )
    opc.require(
        len(fill.findall("a:blip", NS)) == 1
        and len(fill.findall("a:stretch", NS)) == 1
        and len(fill.findall("a:srcRect", NS)) <= 1,
        "protected_fill_count",
    )
    opc.require(zero_rectangle(fill.find("a:srcRect", NS)), "protected_crop")
    stretch = fill.find("a:stretch", NS)
    opc.require(
        stretch is not None
        and not stretch.attrib
        and len(list(stretch)) <= 1
        and zero_rectangle(stretch.find("a:fillRect", NS))
        and all(c.tag == "{" + NS["a"] + "}fillRect" for c in stretch),
        "protected_stretch_transform",
    )
    props = pic.find("p:spPr", NS)
    opc.require(
        props is not None and not props.attrib and len(list(props)) == 2,
        "protected_shape_effect",
    )
    geom = props.find("a:prstGeom", NS)
    opc.require(
        geom is not None
        and geom.attrib == {"prst": "rect"}
        and all(
            c.tag == "{" + NS["a"] + "}avLst" and not c.attrib and not list(c)
            for c in geom
        ),
        "protected_mask",
    )
    transform = props.find("a:xfrm", NS)
    opc.require(
        transform is not None
        and all(
            k in {"rot", "flipH", "flipV"} and v in {"0", "false"}
            for k, v in transform.attrib.items()
        ),
        "protected_rotation_or_flip",
    )
    off, ext = transform.find("a:off", NS), transform.find("a:ext", NS)
    opc.require(
        off is not None and ext is not None and len(list(transform)) == 2,
        "protected_frame_missing",
    )
    values = [off.get("x", ""), off.get("y", ""), ext.get("cx", ""), ext.get("cy", "")]
    opc.require(
        all(re.fullmatch(r"-?[0-9]{1,15}", v) for v in values),
        "protected_frame_invalid",
    )
    frame = expected_frame(binding)
    x, y, width, height = map(int, values)
    opc.require(
        x >= 0
        and y >= 0
        and width > 0
        and height > 0
        and x + width <= round(canvas[0] * 9525)
        and y + height <= round(canvas[1] * 9525),
        "protected_frame_outside_canvas",
    )
    opc.require(
        all(abs(int(v) - e) <= 2 for v, e in zip(values, frame)),
        "protected_contain_frame_mismatch",
    )
    return {
        "slot_px": list(binding["item"]["box"]),
        "expected_frame_emu": frame,
        "actual_frame_emu": list(map(int, values)),
    }


def check_slide_context(root):
    """Refuse unsupported inherited transforms and playback-dependent visibility."""
    opc.require(root.get("show", "1") in {"1", "true"}, "protected_slide_hidden")
    opc.require(root.find("p:timing", NS) is None, "protected_slide_timing_unsupported")
    groups = root.findall("p:cSld/p:spTree/p:grpSpPr", NS)
    opc.require(
        len(groups) == 1 and not groups[0].attrib,
        "protected_parent_transform_unsupported",
    )
    children = list(groups[0])
    # NOTE: Only absent/empty transforms are proven by this route; do not normalize guesses.
    opc.require(
        not children
        or (
            len(children) == 1
            and children[0].tag == "{" + NS["a"] + "}xfrm"
            and not children[0].attrib
            and not list(children[0])
        ),
        "protected_parent_transform_unsupported",
    )


def check_picture(files, slide, binding, canvas):
    """Resolve one named ordinary picture to its byte-identical original PNG."""
    root = opc.xml(files[slide])
    check_slide_context(root)
    pictures = root.findall(".//p:pic", NS)
    matches = [
        p
        for p in pictures
        if p.find("p:nvPicPr/p:cNvPr", NS) is not None
        and p.find("p:nvPicPr/p:cNvPr", NS).get("name") == binding["item"]["id"]
    ]
    opc.require(len(matches) == 1, "protected_picture_not_unique")
    pic = matches[0]
    check_nonvisual_properties(pic)
    opc.require(
        pic in root.findall("p:cSld/p:spTree/p:pic", NS),
        "protected_grouped_picture_unsupported",
    )
    opc.require(
        not pic.attrib
        and [child.tag for child in pic]
        == ["{" + NS["p"] + "}" + tag for tag in ("nvPicPr", "blipFill", "spPr")],
        "protected_picture_style_or_extension",
    )
    opc.require(
        pic.find("p:nvPicPr/p:cNvPr", NS).get("hidden", "0") in {"0", "false"},
        "protected_picture_hidden",
    )
    blip = pic.find("p:blipFill/a:blip", NS)
    embed = "{" + NS["r"] + "}embed"
    opc.require(
        blip is not None and set(blip.attrib) == {embed} and not list(blip),
        "protected_blip_effect_or_link",
    )
    relations = [
        r for r in opc.relationships(files, slide) if r.get("Id") == blip.get(embed)
    ]
    opc.require(
        len(relations) == 1 and relations[0].get("Type") == NS["r"] + "/image",
        "protected_image_relationship",
    )
    media = opc.resolve_target(slide, relations[0].get("Target"))
    check_png_type(files, media)
    opc.require(files[media] == binding["body"], "protected_embedded_bytes_changed")
    geometry = check_geometry(pic, binding, canvas)
    return {
        "slide_part": slide,
        "object_id": binding["item"]["id"],
        "media_part": media,
        "sha256": binding["sha256"],
        "contain_frame_verified": True,
        **geometry,
    }


def check_nonvisual_properties(pic):
    """Do not mistake video posters, actions or placeholders for plain PNG objects."""
    properties = pic.find("p:nvPicPr", NS)
    name = properties.find("p:cNvPr", NS)
    allowed = {"{" + NS["p"] + "}" + tag for tag in ("cNvPr", "cNvPicPr", "nvPr")}
    media = properties.findall("p:nvPr", NS)
    opc.require(
        not properties.attrib
        and all(child.tag in allowed for child in properties)
        and len(properties.findall("p:cNvPr", NS)) == 1
        and name is not None
        and not list(name)
        and set(name.attrib) <= {"id", "name", "descr", "title", "hidden"}
        and len(media) <= 1
        and all(not item.attrib and not list(item) for item in media),
        "protected_nonvisual_media_or_action",
    )
    picture_properties = properties.findall("p:cNvPicPr", NS)
    opc.require(
        len(picture_properties) <= 1
        and all(
            not item.attrib
            and all(
                child.tag == "{" + NS["a"] + "}picLocks" and not list(child)
                for child in item
            )
            for item in picture_properties
        ),
        "protected_nonvisual_media_or_action",
    )


def verify_protected_media(root, plan, pptx):
    """Return a read-only proof; bound input before ZIP parsing or any output write."""
    bindings = resolve_bindings(root, plan)
    opc.require(bool(bindings), "protected_media_required")
    with Path(pptx).open("rb") as stream:
        body = stream.read(opc.MAX_BYTES + 1)
    files = opc.read_package(body)
    slides = ordered_slides(files, plan["canvas"])
    opc.require(len(slides) == len(plan["slides"]), "protected_slide_count")
    checked = []
    for binding in bindings:
        try:
            checked.append(
                check_picture(
                    files, slides[binding["slide_index"]], binding, plan["canvas"]
                )
            )
        except ValueError as error:
            identity = binding["declaration"]
            raise ValueError(
                f"{error}: slide={identity['slide_id']}; object={identity['object_id']}"
            ) from error
    return {
        "status": "passed",
        "pptx_sha256": opc.digest(body),
        "pictures": checked,
        "scope": "static_png_bytes_and_contain_geometry_only; visual_visibility_occlusion_and_video_playback_not_verified",
    }
