# SPDX-License-Identifier: MIT
"""Restore proved dependencies to a NEW directory; strict finalization follows.

Usage: python restore_chart_dependencies.py --source SRC --authored DRAFT --out-dir NEW
Exit 0 writes candidate.pptx and proof.json, 2 rejects input, 3 reports file failure.
The candidate is not a deliverable until finalize_restoration.mjs has passed.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from bounded_pptx import restore_dependencies
from bounded_pptx.opc import MAX_BYTES, digest, require

LOGGER = logging.getLogger(__name__)


def event(level, code, **details):
    """Emit one structured event without logging presentation content."""
    LOGGER.log(
        level,
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": logging.getLevelName(level),
                "event": code,
                **details,
            },
            ensure_ascii=False,
        ),
    )


def run(source_path, authored_path, output_dir):
    """Read inputs once, recompute proof, and exclusively create output directory.

    Input hashes are rechecked before any output. A partially written candidate is
    removed on local file failure; existing files and directories are never reused.
    """
    source_path, authored_path = (
        source_path.resolve(strict=True),
        authored_path.resolve(strict=True),
    )
    require(source_path != authored_path, "source_equals_authored")
    require(source_path.is_file() and authored_path.is_file(), "input_not_file")
    require(
        max(source_path.stat().st_size, authored_path.stat().st_size) <= MAX_BYTES,
        "archive_size_limit",
    )
    require(not output_dir.exists() and not output_dir.is_symlink(), "output_exists")
    source, authored = source_path.read_bytes(), authored_path.read_bytes()
    result, proof = restore_dependencies(source, authored)
    require(
        digest(source_path.read_bytes()) == proof["source_sha256"],
        "source_changed_during_check",
    )
    require(
        digest(authored_path.read_bytes()) == proof["authored_sha256"],
        "authored_changed_during_check",
    )
    output_dir.mkdir(parents=False, exist_ok=False)
    try:
        (output_dir / "candidate.pptx").write_bytes(result)
        (output_dir / "proof.json").write_text(
            json.dumps(proof, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        # NOTE: Only paths created by this invocation can enter this cleanup branch.
        (output_dir / "candidate.pptx").unlink(missing_ok=True)
        (output_dir / "proof.json").unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return proof


def main(argv=None):
    """Validate the CLI and expose explicit blocked/failed statuses to callers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--authored", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        proof = run(args.source, args.authored, args.out_dir)
        event(logging.INFO, "dependencies_restored", **proof)
        return 0
    except ValueError as error:
        event(logging.WARNING, "restoration_blocked", reason=str(error))
        return 2
    except (OSError, RuntimeError) as error:
        event(logging.ERROR, "restoration_io_failed", reason=str(error))
        return 3


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
