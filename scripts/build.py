"""Build platform-specific artifacts from ``source/`` into ``build/<Platform>/``.

Usage::

    python scripts/build.py                   # build all registered platforms
    python scripts/build.py --target copilot
    python scripts/build.py --target codex copilot

Extending: implement a new ``PlatformAdapter`` under ``adapters/<name>/`` and
register it in ``adapters/__init__.py``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adapters import all_adapters, get_adapter, load_source  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build agent/skill artifacts per platform.")
    parser.add_argument(
        "--target",
        nargs="+",
        default=["all"],
        help="platform names to build, or 'all' (default).",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT / "source",
        help="source directory (default: ./source)",
    )
    parser.add_argument(
        "--build",
        type=Path,
        default=REPO_ROOT / "build",
        help="build output root (default: ./build)",
    )
    return parser.parse_args(argv)


def resolve_targets(targets: list[str]):
    if "all" in targets:
        return all_adapters()
    return [get_adapter(t) for t in targets]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.source.is_dir():
        print(f"[error] source not found: {args.source}", file=sys.stderr)
        return 2

    source = load_source(args.source)
    print(f"[source] agents={len(source.agents)} skills={len(source.skills)}")

    adapters = resolve_targets(args.target)
    if not adapters:
        print("[error] no adapters selected", file=sys.stderr)
        return 2

    args.build.mkdir(parents=True, exist_ok=True)
    for adapter in adapters:
        out_root = args.build / adapter.display_name
        report = adapter.build(source, out_root)
        print(report.summary())
        for w in report.warnings:
            print(f"  warn: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
