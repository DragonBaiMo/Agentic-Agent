"""Distribute built artifacts into each platform's real install location.

Usage::

    python scripts/distribute.py --dry-run          # preview only
    python scripts/distribute.py                    # distribute to all
    python scripts/distribute.py --target codex
    python scripts/distribute.py --no-build         # skip rebuild step

By default this runs ``build.py`` first to ensure ``build/`` is fresh.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters import all_adapters, expand_path, get_adapter, load_source  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Distribute built artifacts to local install paths.")
    parser.add_argument("--target", nargs="+", default=["all"])
    parser.add_argument("--build", type=Path, default=REPO_ROOT / "build")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "source")
    parser.add_argument("--dry-run", action="store_true", help="print planned actions only")
    parser.add_argument("--no-build", action="store_true", help="skip rebuild before distribute")
    parser.add_argument(
        "--mode",
        choices=("replace", "merge"),
        default="replace",
        help="replace: wipe destination subdir before copy; merge: overlay files",
    )
    return parser.parse_args(argv)


def resolve_targets(targets: list[str]):
    if "all" in targets:
        return all_adapters()
    return [get_adapter(t) for t in targets]


def _rebuild(source_dir: Path, build_dir: Path, adapters) -> None:
    if not source_dir.is_dir():
        raise SystemExit(f"[error] source not found: {source_dir}")
    source = load_source(source_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    for adapter in adapters:
        report = adapter.build(source, build_dir / adapter.display_name)
        print(f"[build] {report.summary()}")


def _distribute_one(adapter, build_dir: Path, dry_run: bool, mode: str) -> None:
    platform_root = build_dir / adapter.display_name
    if not platform_root.is_dir():
        print(f"[skip] {adapter.display_name}: build dir missing — run build first")
        return
    for mapping in adapter.install_targets():
        src = platform_root / mapping.src_subpath
        dst = expand_path(mapping.dst_path)
        if not src.exists():
            print(f"[skip] {adapter.display_name}: {src} missing")
            continue
        action = "REPLACE" if mode == "replace" else "MERGE"
        print(f"[{action}] {adapter.display_name}: {src} -> {dst}")
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == "replace":
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        else:  # merge
            if src.is_dir():
                _merge_tree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)


def _merge_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _merge_tree(item, target)
        else:
            shutil.copy2(item, target)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    adapters = resolve_targets(args.target)
    if not adapters:
        print("[error] no adapters selected", file=sys.stderr)
        return 2

    if not args.no_build:
        _rebuild(args.source, args.build, adapters)

    for adapter in adapters:
        _distribute_one(adapter, args.build, args.dry_run, args.mode)

    if args.dry_run:
        print("[dry-run] no changes applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
