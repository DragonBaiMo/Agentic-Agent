# SPDX-License-Identifier: MIT
"""Read-only protected PNG check. Exit 0: verified; exit 2: invalid/unsupported.

Usage: --project DIR --plan deck.json --pptx builds/B01/final.pptx --out evidence/media.json
All file arguments are project relative. Receipts are new files and never replace sources.
"""

import argparse
import json
import logging
import os
import tempfile
from pathlib import Path

from pptx_backend.contract import compile_deck
from pptx_backend.protected_package import verify_protected_media
from project_io import inside

LOGGER = logging.getLogger(__name__)
MAX_JSON_BYTES = 1024 * 1024


def bounded_json(path):
    """Read a small project contract; reject oversized JSON before allocation."""
    with Path(path).open("rb") as stream:
        body = stream.read(MAX_JSON_BYTES + 1)
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("protected_json_size_limit")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("protected_json_object_required")
    return value


def write_receipt(output, receipt):
    """Publish one complete new receipt, never overwrite any caller path."""
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".protected-", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
        # NOTE: Same-directory hardlink is atomic and fails if output already exists.
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    """Compile the declared contract, verify actual bytes, and write a new receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        plan = bounded_json(inside(args.project, args.plan))
        source = (
            bounded_json(inside(args.project, plan["data_file"]))
            if plan.get("data_file")
            else {}
        )
        compiled, pending = compile_deck(args.project, plan, source)
        if pending:
            raise ValueError("stale_art_labels")
        receipt = verify_protected_media(
            args.project, compiled, inside(args.project, args.pptx)
        )
        output = inside(args.project, args.out)
        write_receipt(output, receipt)
        LOGGER.info(
            json.dumps(
                {
                    "level": "INFO",
                    "event": "protected_media_verified",
                    "receipt": str(output),
                }
            )
        )
    except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
        LOGGER.error(
            json.dumps(
                {
                    "level": "ERROR",
                    "event": "protected_media_failed",
                    "detail": str(error),
                }
            )
        )
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
