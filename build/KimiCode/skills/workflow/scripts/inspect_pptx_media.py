"""SPDX-License-Identifier: MIT

Inspect PPTX before the current JS editing route. Exit 0: media clear; 2: blocked/unknown.
Usage: python scripts/inspect_pptx_media.py SOURCE.pptx
"""

import argparse
import json
import sys
from pathlib import Path

from pptx_backend.media_preflight import inspect_media


def main():
    """Emit one bounded-inspection receipt; do not create or overwrite a PPTX."""
    messages = json.loads((Path(__file__).parents[1]
                          / "resources/media-preflight.zh-CN.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=messages["description"])
    parser.add_argument("source", help=messages["source"])
    args = parser.parse_args()
    result = inspect_media(Path(args.source))
    result["message"] = messages[result["status"]]
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0 if result["status"] == "CLEAR" else 2


if __name__ == "__main__":
    raise SystemExit(main())
