#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure local rolling-DAG overhead with explicitly simulated service latencies.

Run from workflow: python scripts/benchmark_schedule.py --out /new/report.json
No image model, credential, network, or production artwork is used.
"""

import argparse
import asyncio
import copy
from pathlib import Path
import statistics
import tempfile
import time

from project_io import read_json, write_json
from scheduling import Coordinator, run
from scheduling.metrics import report

ROOT = Path(__file__).parents[1]


async def measure(fixture, mode, parent):
    """Time one fresh local project; stage barriers change scheduling, not fixture work."""
    plan = copy.deepcopy(fixture)
    if mode == 'batch-2':
        parents = [task['id'] for task in plan['tasks'] if not task.get('depends_on')]
        for task in plan['tasks']:
            if task.get('depends_on'):
                task['depends_on'] = parents
    window = {'serial': 1, 'batch-2': 2, 'rolling-2': 2, 'rolling-4': 4}[mode]
    with tempfile.TemporaryDirectory(dir=parent) as directory:
        root = Path(directory)
        source = root / 'diagnostic.txt'
        source.write_text(fixture['evidence_kind'], encoding='utf-8')
        coordinator = Coordinator(root)
        coordinator.initialize(plan, window)

        async def invoke(claim):
            await asyncio.sleep(claim['spec']['delay_seconds'])
            return {'source': source}

        async def inspect(claim, state):
            return (root / state['jobs'][claim['id']]['result']['file']).read_bytes() == source.read_bytes()

        begin = time.monotonic()
        state = await run(coordinator, invoke, inspect, deadline_seconds=30)
        elapsed = time.monotonic() - begin
        if any(job['state'] != 'adopted' for job in state['jobs'].values()):
            raise ValueError('benchmark_incomplete')
        return {'mode': mode, 'elapsed_seconds': elapsed, 'metrics': report(state)}


def main():
    """Write reproducible raw trial metrics to a new file; clean all local projects."""
    messages = read_json(ROOT / 'resources/scheduling.zh-CN.json')
    parser = argparse.ArgumentParser(description=messages['benchmark.description'])
    parser.add_argument('--fixture', type=Path, default=ROOT / 'examples/scheduling-benchmark.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.out.exists() or not 1 <= args.repeats <= 10:
        raise ValueError('benchmark_new_output_and_bounded_repeats_required')
    parent = ROOT / 'tmp/scheduling-benchmark'
    parent.mkdir(parents=True, exist_ok=True)
    fixture = read_json(args.fixture)
    modes = ('serial', 'batch-2', 'rolling-2', 'rolling-4')
    trials = [asyncio.run(measure(fixture, mode, parent))
              for _ in range(args.repeats) for mode in modes]
    medians = {mode: statistics.median(item['elapsed_seconds'] for item in trials if item['mode'] == mode)
               for mode in modes}
    write_json(args.out, {'evidence_kind': fixture['evidence_kind'], 'image_calls': 0,
                         'median_seconds': medians, 'trials': trials})
    parent.rmdir()


if __name__ == '__main__':
    main()
