"""SPDX-License-Identifier: MIT

Package a portable selected build, sources, plan and honest delivery status.
No image scores or approval tickets. A final package still needs actual visual review.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
import zipfile

from project_io import inside, read_json
from verify_psd import verify


def package(root, build, handover, destination, mode):
    """Verify real PSD structure for non-diagnostic exports and CRC/hash all ZIP entries."""
    root, destination = Path(root).resolve(), Path(destination)
    if destination.exists():
        raise ValueError("output_exists")
    files = {}
    for name in ("plan.json", "receipts.json", "manifest.json"):
        if (root / name).is_file():
            files[name] = (root / name).read_bytes()
    if mode != "diagnostic":
        config = read_json(root / "manifest.json")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", config["name"]):
            raise ValueError("invalid_output_basename")
        build = Path(build).resolve()
        psd, preview = build / (config["name"] + ".psd"), build / (config["name"] + "-preview.png")
        report = verify(SimpleNamespace(config=root / "manifest.json", psd=psd, preview=preview,
                                        out=build / "delivery-check", review=False))
        files["output/" + psd.name], files["output/" + preview.name] = psd.read_bytes(), preview.read_bytes()
        files["output/technical-check.json"] = json.dumps(report, ensure_ascii=False, indent=2).encode()
        for item in config["art"]:
            if Path(item["file"]).name != item["file"]:
                raise ValueError("asset_requires_basename")
            asset = inside(root, "assets/" + item["file"])
            files["assets/" + item["file"]] = asset.read_bytes()
    plan = read_json(root / "plan.json")
    master = plan.get("master", {}).get("file")
    if master:
        actual = inside(root, master)
        files[actual.relative_to(root).as_posix()] = actual.read_bytes()
    files["START_HERE.md"] = Path(handover).read_bytes()
    files["DELIVERY_STATUS.json"] = json.dumps({"mode": mode, "psd_available": mode != "diagnostic",
        "user_visual_approval": plan.get("interaction", {}).get("user_visual_approval", False),
        "visual_review": "see_START_HERE", "photoshop_gui": "see_START_HERE"}, indent=2).encode()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    if any(Path(name).is_absolute() or ".." in Path(name).parts for name in files):
        raise ValueError("unsafe_archive_path")
    files["MANIFEST.json"] = json.dumps(hashes, indent=2).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("partial_output_exists")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() or any(hashlib.sha256(archive.read(name)).hexdigest() != sha for name, sha in hashes.items()):
                raise ValueError("zip_integrity")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"file": str(destination), "mode": mode, "bytes": destination.stat().st_size, "crc_and_hashes": "passed"}


def main():
    """Require an explicit handover and delivery type instead of inventing final approval."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--handover", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mode", choices=("final", "review", "diagnostic"), default="review")
    args = parser.parse_args()
    if args.mode != "diagnostic" and not args.build:
        parser.error("--build")
    print(json.dumps(package(args.project, args.build, args.handover, args.out, args.mode), ensure_ascii=False))


if __name__ == "__main__":
    main()
