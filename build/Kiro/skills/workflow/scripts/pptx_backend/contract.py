"""SPDX-License-Identifier: MIT

Compile local deck resources and reject stale artistic data labels.
Public functions accept project-relative resources; they never call image tools.
"""
import copy
import hashlib
import math
from pathlib import Path


def inside(root, value):
    """Resolve a project resource; reject traversal and symlink escapes."""
    path = (Path(root).resolve() / value).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('outside_project: ' + value)
    return path


def data_value(data, key):
    """Read a dot-separated key without evaluating expressions or source code."""
    value = data
    for part in key.split('.'):
        value = value[part]
    return value


def resolve_data(source):
    """Calculate only declared reductions; reject invalid or ambiguous baselines."""
    data = copy.deepcopy(source)
    for spec in data.pop('_derived', []):
        old, new = data_value(data, spec['baseline']), data_value(data, spec['current'])
        if spec['operation'] != 'reduction_percent' or old <= 0 or new < 0:
            raise ValueError('invalid_derived: ' + spec['key'])
        data[spec['key']] = round(100 * (old - new) / old, spec.get('decimals', 0))
    return data


def numeric_box(value):
    """Validate finite xywh geometry, including intentional negative edge positions."""
    if len(value) != 4 or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in value):
        raise ValueError('invalid_box')
    if value[2] <= 0 or value[3] <= 0:
        raise ValueError('empty_box')


def pending_art(root, data, bindings):
    """Identify mismatched values or changed bytes; visual approval remains human/agent work."""
    pending = []
    for item in bindings:
        actual = data_value(data, item['key'])
        digest = hashlib.sha256(inside(root, item['file']).read_bytes()).hexdigest()
        if actual != item['approved_value'] or digest != item['sha256']:
            pending.append({'object_id': item['object_id'], 'key': item['key'],
                            'old_value': item['approved_value'], 'new_value': actual,
                            'file': item['file'], 'reason': 'value_or_asset_changed'})
    return pending


def compile_deck(root, plan, source):
    """Return a resolved deck and pending art jobs, preserving source JSON unchanged."""
    result = copy.deepcopy(plan)
    if result.get('schema_version') != 'pptx-1':
        raise ValueError('unsupported_deck_schema')
    numeric_box([0, 0, *result['canvas']])
    if not result['slides'] or not inside(root, result['background']).is_file():
        raise ValueError('missing_slides_or_background')
    data = resolve_data(source)
    pending = pending_art(root, data, result.get('art_bindings', []))
    for binding in result.get('data_bindings', []):
        target = result
        for key in binding['path'][:-1]:
            target = target[key]
        target[binding['path'][-1]] = data_value(data, binding['key'])
    slide_ids = [page['id'] for page in result['slides']]
    if len(slide_ids) != len(set(slide_ids)):
        raise ValueError('duplicate_slide_id')
    for page in result['slides']:
        check_page(root, page)
    return result, pending


def check_page(root, page):
    """Validate used resources and identifiers; no artificial layer-count or visual-score gate."""
    ids = [item['id'] for item in page['elements']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate_object_id: ' + page['id'])
    for item in page['elements']:
        kind = item['kind']
        if kind not in ('image', 'text', 'chart', 'table', 'rule'):
            raise ValueError('unsupported_object: ' + kind)
        if kind == 'image' and not inside(root, item['file']).is_file():
            raise ValueError('missing_asset: ' + item['file'])
        if kind in ('image', 'text', 'rule'):
            numeric_box(item['box'])
        if kind == 'image' and not item.get('alt'):
            raise ValueError('missing_image_description: ' + item['id'])

