#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile a PPTX plan and its single data source; never generate art implicitly.

Usage: python scripts/pptx_project.py --project DIR --plan deck.json --out builds/B01/compiled.json
Exit 2 means invalid input or art labels need a verified synchronized replacement.
"""
import argparse
import json
import logging
from pathlib import Path
from project_io import read_json, write_json
from pptx_backend.contract import compile_deck, inside

LOGGER = logging.getLogger(__name__)


def main():
    """Compile to a new version directory and retain exact pending replacement jobs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--plan', default='deck.json')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        plan = read_json(inside(args.project, args.plan))
        data = read_json(inside(args.project, plan['data_file'])) if plan.get('data_file') else {}
        compiled, pending = compile_deck(args.project, plan, data)
        output = inside(args.project, args.out)
        if output.exists():
            raise ValueError('output_exists: ' + args.out)
        if pending:
            write_json(output.parent / 'pending-art-replacements.json', pending)
            raise ValueError('stale_art_labels')
        write_json(output, compiled)
        LOGGER.info(json.dumps({'level': 'INFO', 'event': 'deck_compiled', 'output': str(output)}))
    except (ValueError, TypeError, KeyError, OSError) as error:
        LOGGER.error(json.dumps({'level': 'ERROR', 'event': 'deck_compile_failed', 'detail': str(error)}))
        raise SystemExit(2) from error


if __name__ == '__main__':
    main()
