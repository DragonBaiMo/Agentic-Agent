#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""JSON command interface for native tool hosts; see references/rolling-scheduling.md."""

import argparse
import json
import logging
from pathlib import Path
import sqlite3
import sys

from project_io import read_json
from scheduling import Coordinator
from scheduling.metrics import report


def main():
    """Execute one bounded transactional command; stdout JSON, failure exit status 2."""
    messages = read_json(Path(__file__).parents[1] / 'resources/scheduling.zh-CN.json')
    parser = argparse.ArgumentParser(description=messages['cli.description'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('command', choices=['init', 'next', 'return', 'register', 'adopt',
                                         'fail', 'recover', 'reconcile', 'status', 'report'])
    parser.add_argument('--payload', type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        payload = read_json(args.payload) if args.payload else {}
        coordinator = Coordinator(args.project)
        operations = {'init': coordinator.initialize, 'next': coordinator.claim,
                      'return': coordinator.returned, 'register': coordinator.register,
                      'adopt': coordinator.adopt, 'fail': coordinator.fail,
                      'recover': coordinator.recover, 'reconcile': coordinator.reconcile_plan,
                      'status': coordinator.snapshot, 'report': lambda: report(coordinator.snapshot())}
        result = operations[args.command](**payload)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + '\n')
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        logging.error(json.dumps({'level': 'ERROR', 'event': messages['cli.failed'],
                                  'error_type': type(error).__name__, 'code': str(error)}))
        raise SystemExit(2) from error


if __name__ == '__main__':
    main()
