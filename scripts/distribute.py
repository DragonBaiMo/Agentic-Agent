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
import os
import shutil
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class DistributionTarget:
    src_subpath: str
    dst_path: Path
    label: str = ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Distribute built artifacts to local install paths.")
    parser.add_argument("--target", nargs="+", default=["all"])
    parser.add_argument("--build", type=Path, default=REPO_ROOT / "build")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "source")
    parser.add_argument("--dry-run", action="store_true", help="print planned actions only")
    parser.add_argument("--no-build", action="store_true", help="skip rebuild before distribute")
    parser.add_argument(
        "--platform",
        default="auto",
        choices=("auto", "macos", "linux", "windows"),
        help="platform profile used to rewrite source before rebuild (default: auto)",
    )
    parser.add_argument(
        "--neutral-source",
        type=Path,
        default=None,
        help="generated OS-neutral intermediate source directory (default: <build>/_neutral_source)",
    )
    parser.add_argument(
        "--copilot-project",
        type=Path,
        help="also install Copilot agents/skills into <repo>/.github/ for project-level use",
    )
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


def _rebuild(
    source_dir: Path,
    build_dir: Path,
    adapters,
    platform: str,
    neutral_source_dir: Path,
) -> None:
    if not source_dir.is_dir():
        raise SystemExit(f"[error] source not found: {source_dir}")
    neutral_report = prepare_neutral_source(source_dir, neutral_source_dir)
    print(
        f"[neutral-source] source-signals={len(neutral_report.findings)} "
        f"rewrites={len(neutral_report.rewrites)} -> {neutral_report.out_root}"
    )

    with TemporaryDirectory(prefix="agentic-agent-source-") as temp_dir:
        platform_report = prepare_platform_source(
            neutral_report.out_root,
            Path(temp_dir) / "source",
            platform,
        )
        source = load_source(platform_report.out_root)
        print(
            f"[source] platform={platform} "
            f"agents={len(source.agents)} skills={len(source.skills)} "
            f"neutral-signals={len(platform_report.findings)} "
            f"rewrites={len(platform_report.rewrites)}"
        )
        build_dir.mkdir(parents=True, exist_ok=True)
        for adapter in adapters:
            out_root = build_dir / adapter.display_name
            if out_root.exists():
                shutil.rmtree(out_root)
            report = adapter.build(source, out_root)
            print(f"[build] {report.summary()}")

            # Copilot is a personal local install — restore original source files
            # that were neutralized for public platforms.
            if adapter.display_name == "Copilot":
                _restore_personal_files(source_dir, out_root)


def _restore_personal_files(source_dir: Path, copilot_out: Path) -> None:
    """Copy source files that should not be neutralized for personal Copilot install."""
    _PERSONAL_INSTRUCTIONS = [
        "development-environment.instructions.md",
    ]
    instructions_out = copilot_out / "instructions"
    for name in _PERSONAL_INSTRUCTIONS:
        src = source_dir / "instructions" / name
        dst = instructions_out / name
        if src.exists() and dst.exists():
            shutil.copy2(src, dst)
            print(f"[personal] Copilot: restored {name} from source")


def _default_home() -> Path:
    if sys.platform == "win32":
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    else:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if not home:
        raise SystemExit("[error] cannot resolve user home directory")
    return Path(home).expanduser()


def _default_appdata() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata).expanduser()
    if sys.platform == "darwin":
        return _default_home() / "Library" / "Application Support"
    return _default_home() / ".config"


def _expand_install_path(template: str) -> Path:
    path = template.replace("%USERPROFILE%", "${USERPROFILE}")
    replacements = {
        "${USERPROFILE}": str(_default_home()),
        "$USERPROFILE": str(_default_home()),
        "${HOME}": str(_default_home()),
        "$HOME": str(_default_home()),
        "${APPDATA}": str(_default_appdata()),
        "$APPDATA": str(_default_appdata()),
    }
    for token, value in replacements.items():
        path = path.replace(token, value)
    return Path(os.path.expandvars(os.path.expanduser(path)))


def _targets_for(adapter, copilot_project: Path | None) -> list[DistributionTarget]:
    targets = [
        DistributionTarget(
            mapping.src_subpath,
            _expand_install_path(mapping.dst_path),
        )
        for mapping in adapter.install_targets()
    ]

    if adapter.name == "copilot":
        targets.append(
            DistributionTarget(
                "skills",
                _default_home() / ".agents" / "skills",
                "generic Agent Skills",
            )
        )
        if copilot_project is not None:
            project_root = copilot_project.expanduser().resolve()
            targets.extend(
                (
                    DistributionTarget(
                        "agents",
                        project_root / ".github" / "agents",
                        "project Copilot agents",
                    ),
                    DistributionTarget(
                        "skills",
                        project_root / ".github" / "skills",
                        "project Copilot skills",
                    ),
                )
            )

    return targets


def _distribute_one(
    adapter,
    build_dir: Path,
    dry_run: bool,
    mode: str,
    copilot_project: Path | None,
) -> None:
    platform_root = build_dir / adapter.display_name
    if not platform_root.is_dir():
        print(f"[skip] {adapter.display_name}: build dir missing — run build first")
        return
    for target in _targets_for(adapter, copilot_project):
        src = platform_root / target.src_subpath
        dst = target.dst_path
        if not src.exists():
            print(f"[skip] {adapter.display_name}: {src} missing")
            continue
        action = "REPLACE" if mode == "replace" else "MERGE"
        label = f" ({target.label})" if target.label else ""
        print(f"[{action}] {adapter.display_name}{label}: {src} -> {dst}")
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
        _rebuild(
            args.source,
            args.build,
            adapters,
            normalize_platform(args.platform),
            args.neutral_source or (args.build / "_neutral_source"),
        )

    for adapter in adapters:
        _distribute_one(
            adapter,
            args.build,
            args.dry_run,
            args.mode,
            args.copilot_project,
        )

    if args.dry_run:
        print("[dry-run] no changes applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
