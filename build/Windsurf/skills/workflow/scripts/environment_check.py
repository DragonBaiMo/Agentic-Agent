"""SPDX-License-Identifier: MIT

Read-only runtime and selected-font diagnostics for project.py doctor.
This does not install packages, identify font faces, or approve image-tool access.
"""

from importlib import metadata, util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from project_io import read_json

ROOT = Path(__file__).parents[1]


def python_dependencies():
    """Compare installed distribution versions with the shipped exact lock."""
    result = []
    for line in (ROOT / "requirements.lock").read_text().splitlines():
        name, expected = line.split("==", 1)
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        result.append({"name": name, "expected": expected, "installed": installed,
                       "version_matches": installed == expected})
    return result


def selected_fonts(plan_file):
    """Resolve the same environment override as the renderer; do not guess faces."""
    if plan_file is None:
        return "check_selected_font_paths"
    plan_file = Path(plan_file).resolve()
    result = []
    for font in read_json(plan_file).get("fonts", []):
        candidate = os.environ.get(font.get("env", "")) or font.get("path")
        path = (plan_file.parent / candidate).resolve() if isinstance(candidate, str) else None
        result.append({"family": font.get("family"), "postscript": font.get("postscript"),
                       "path": str(path) if path else None, "exists": bool(path and path.is_file()),
                       "font_identity_verified": False})
    return result


def inspect_environment(plan_file=None):
    """Report facts with a bounded Node subprocess; failures remain visible data."""
    node = shutil.which("node")
    node_runtime = {"available": False}
    if node:
        try:
            process = subprocess.run([node, str(ROOT / "scripts/doctor.cjs")], capture_output=True,
                                     text=True, timeout=15, check=True)
            node_runtime = json.loads(process.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            node_runtime = {"available": True, "error_type": type(error).__name__}
    # NOTE: Preserve 1.1 field names; added detail is diagnostic, not an art gate.
    return {"node": node, "pillow": util.find_spec("PIL") is not None,
            "psd_tools": util.find_spec("psd_tools") is not None,
            "python_version": platform.python_version(), "python_supported": sys.version_info >= (3, 12),
            "python_dependencies": python_dependencies(), "node_runtime": node_runtime,
            "image_tool": "must_be_discovered_in_host", "fonts": selected_fonts(plan_file)}
