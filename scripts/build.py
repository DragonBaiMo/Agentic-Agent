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
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from adapters import all_adapters, get_adapter, load_source  # noqa: E402
from build_platform import (  # noqa: E402
    normalize_platform,
    prepare_neutral_source,
    prepare_platform_source,
)


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
    parser.add_argument(
        "--platform",
        default="auto",
        choices=("auto", "macos", "linux", "windows"),
        help="platform profile used to rewrite source before build (default: auto)",
    )
    parser.add_argument(
        "--neutral-source",
        type=Path,
        default=None,
        help="generated OS-neutral intermediate source directory (default: <build>/_neutral_source)",
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

    adapters = resolve_targets(args.target)
    if not adapters:
        print("[error] no adapters selected", file=sys.stderr)
        return 2

    platform = normalize_platform(args.platform)
    neutral_source_dir = args.neutral_source or (args.build / "_neutral_source")
    neutral_report = prepare_neutral_source(args.source, neutral_source_dir)
    print(
        f"[neutral-source] source-signals={len(neutral_report.findings)} "
        f"rewrites={len(neutral_report.rewrites)} -> {neutral_report.out_root}"
    )

    with TemporaryDirectory(prefix="agentic-agent-source-") as temp_dir:
        platform_source_dir = Path(temp_dir) / "source"
        platform_report = prepare_platform_source(
            neutral_report.out_root,
            platform_source_dir,
            platform,
        )
        source = load_source(platform_report.out_root)
        print(
            f"[source] platform={platform} "
            f"agents={len(source.agents)} skills={len(source.skills)} "
            f"neutral-signals={len(platform_report.findings)} "
            f"rewrites={len(platform_report.rewrites)}"
        )

        args.build.mkdir(parents=True, exist_ok=True)
        for adapter in adapters:
            out_root = args.build / adapter.display_name
            if out_root.exists():
                shutil.rmtree(out_root)
            report = adapter.build(source, out_root)
            print(report.summary())
            for w in report.warnings:
                print(f"  warn: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
