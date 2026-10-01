#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tightly crop transparent semantic art and compensate its original canvas placement.

Use --help for xywh parameters. Pixel colors and surviving alpha values are unchanged.
The ledger identifies weak discarded pixels, which require visual soft-edge review.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
from PIL import Image
from project_io import write_json


def crop_asset(source, destination, target, threshold=1, padding=6, region=None):
    """Save a new crop and return exact source/crop/target frames with alpha observations."""
    if destination.exists() or destination.resolve() == source.resolve():
        raise ValueError('output_exists')
    if not 1 <= threshold <= 255 or padding < 0:
        raise ValueError('invalid_crop_settings')
    tx, ty, tw, th = target
    if min(tw, th) <= 0:
        raise ValueError('invalid_target')
    image = Image.open(source).convert('RGBA')
    source_size = image.size
    x, y, w, h = region or [0, 0, *source_size]
    if min(x, y) < 0 or min(w, h) <= 0 or x+w > source_size[0] or y+h > source_size[1]:
        raise ValueError('invalid_region')
    selected = image.crop((x, y, x+w, y+h))
    alpha = selected.getchannel('A')
    bounds = alpha.point(lambda a: 255 if a >= threshold else 0).getbbox()
    if bounds is None:
        raise ValueError('empty_alpha')
    l, t, r, b = bounds
    box = [max(0, l-padding)+x, max(0, t-padding)+y,
           min(w, r+padding)+x, min(h, b+padding)+y]
    cropped = image.crop(box)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(destination)
    sx, sy = tw/source_size[0], th/source_size[1]
    # NOTE: Cropping changes the bitmap origin; placement must preserve the old canvas transform.
    placed = [tx+box[0]*sx, ty+box[1]*sy, (box[2]-box[0])*sx, (box[3]-box[1])*sy]
    before = sum(v*n for v, n in enumerate(alpha.histogram()))
    after = sum(v*n for v, n in enumerate(cropped.getchannel('A').histogram()))
    return {'source_size': source_size, 'region_xywh': [x,y,w,h],
            'crop_xywh': [box[0],box[1],box[2]-box[0],box[3]-box[1]],
            'original_target_xywh': target, 'target_xywh': placed,
            'threshold': threshold, 'padding': padding, 'discarded_alpha_mass': before-after,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}


def main():
    """Expose crop geometry as explicit CLI data and keep a reusable ledger beside it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', type=float, nargs=4, required=True, metavar=('X','Y','W','H'))
    parser.add_argument('--region', type=int, nargs=4)
    parser.add_argument('--threshold', type=int, default=1)
    parser.add_argument('--padding', type=int, default=6)
    parser.add_argument('--ledger', type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        if args.ledger.exists():
            raise ValueError('ledger_exists')
        result = crop_asset(args.input,args.output,args.target,args.threshold,args.padding,args.region)
        write_json(args.ledger, result)
        logging.info(json.dumps({'level':'INFO','event':'alpha_cropped','ledger':str(args.ledger)}))
    except (ValueError, OSError) as error:
        logging.error(json.dumps({'level':'ERROR','event':'alpha_crop_failed','detail':str(error)}))
        raise SystemExit(2) from error


if __name__ == '__main__':
    main()
