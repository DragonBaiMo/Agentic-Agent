#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a deck image job or register a real result without pretending to call a model.

Project jobs.json contains explicit task prompts/references. Registration is single-writer.
Use --help and references/pptx-tools.md for the caller-visible evidence contract.
"""
import argparse
import datetime
import json
import logging
from pathlib import Path
import re
import shutil
from execution_record import execution_result
from project_io import digest, inside, read_json, write_json


def prepare(root, task, output):
    """Copy actual reference bytes and a pure prompt into a new immutable job directory."""
    spec = read_json(root / 'jobs.json')['tasks'][task]
    destination = inside(root, output)
    if destination.exists():
        raise ValueError('job_exists')
    sources = [inside(root, name) for name in spec.get('references', [])]
    if any(not source.is_file() for source in sources):
        raise ValueError('reference_missing')
    if not spec['prompt'].strip() or type(spec['transparent_background']) is not bool:
        raise ValueError('invalid_job')
    destination.mkdir(parents=True)
    (destination / 'DRAW.txt').write_text(spec['prompt'], encoding='utf-8')
    references = []
    for index, source in enumerate(sources, 1):
        name = f'reference-{index}{source.suffix.lower()}'
        shutil.copyfile(source, destination / name)
        references.append({'file': name, 'sha256': digest(source)})
    request = {'task': task, 'status': 'prepared_not_executed', 'references': references,
               'transparent_background': spec['transparent_background'],
               'prompt_sha256': digest(destination / 'DRAW.txt')}
    write_json(destination / 'request.json', request)
    return {'job': output, 'references': len(references)}


def register(args):
    """Save returned bytes and actual public arguments; no silent adoption into deck.json."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.task):
        raise ValueError('invalid_task_id')
    root = args.project.resolve()
    receipt = execution_result(args.source,args.origin,args.tool,args.call_id,args.execution)
    record_id = getattr(args, 'record_id', None)
    if record_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', record_id):
        raise ValueError('invalid_record_id')
    records = read_json(root / 'receipts.json') if (root / 'receipts.json').exists() else []
    if record_id:
        # NOTE: The scheduler may crash after receipt commit but before state commit.
        matches = [item for item in records if item.get('record_id') == record_id]
        if matches:
            prior = matches[0]
            if (prior['result_sha256'] != receipt['result_sha256'] or prior['task'] != args.task
                    or prior['adoption_status'] != args.status or prior['origin'] != args.origin):
                raise ValueError('record_id_collision')
            return {'file': prior['file'], 'status': prior['adoption_status']}
        receipt['record_id'] = record_id
    relative = f'{args.status}/{args.task}-{receipt["result_sha256"][:16]}{args.source.suffix.lower()}'
    destination = inside(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copyfile(args.source, destination)
    elif digest(destination) != digest(args.source):
        raise ValueError('asset_collision')
    receipt.update(task=args.task,file=relative,adoption_status=args.status,reason=args.reason,
                   recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if args.job:
        receipt['preparation'] = read_json(inside(root,args.job) / 'request.json')
    target = root / 'receipts.json'
    records.append(receipt)
    write_json(target, records)
    return {'file': relative, 'status': args.status}


def main():
    """Expose explicit preparation/registration commands with bounded local writes."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--out', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('--source', type=Path, required=True)
    rec.add_argument('--origin', choices=['generated','user_supplied','conversation_history'], required=True)
    rec.add_argument('--tool', required=True)
    rec.add_argument('--call-id', default='not_exposed')
    rec.add_argument('--record-id')
    rec.add_argument('--job')
    rec.add_argument('--execution', type=Path)
    rec.add_argument('--status', choices=['assets','rejected'], default='assets')
    rec.add_argument('--reason', default='')
    for item in (prep, rec):
        item.add_argument('--project', type=Path, required=True)
        item.add_argument('--task', required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    try:
        result = prepare(args.project,args.task,args.out) if args.command == 'prepare' else register(args)
        logging.info(json.dumps({'level':'INFO','event':'image_job_'+args.command,**result},ensure_ascii=False))
    except (ValueError, KeyError, OSError) as error:
        logging.error(json.dumps({'level':'ERROR','event':'image_job_failed','detail':str(error)}))
        raise SystemExit(2) from error


if __name__ == '__main__':
    main()
