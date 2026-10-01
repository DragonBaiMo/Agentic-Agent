"""SPDX-License-Identifier: MIT

Compile local deck resources and reject stale artistic data labels.
Public functions accept project-relative resources; they never call image tools.
"""
import copy
import hashlib
import math
import re
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
    if not result['slides']:
        raise ValueError('missing_slides_or_background')
    check_background(root, result)
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
        resolve_text_roles(page, result.get('text_styles', {}))
        check_page(root, page)
    return result, pending


def check_background(root, plan):
    """Keep explicit image backgrounds authoritative; otherwise require a solid color."""
    if 'background' in plan:
        if not isinstance(plan['background'], str) or not plan['background']:
            raise ValueError('invalid_background: background')
        if not inside(root, plan['background']).is_file():
            raise ValueError('missing_slides_or_background')
        return
    theme = plan.get('theme', {})
    if not isinstance(theme, dict):
        raise TypeError('invalid_solid_background: theme')
    color = theme.get('background')
    if color is None:
        raise ValueError('missing_solid_background')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('invalid_solid_background')


def resolve_text_roles(page, roles):
    """Resolve optional role styles in a compiled copy; explicit fields win atomically.

    NOTE: Nested API objects such as insets are replaced whole, never guessed or
    merged from a previous state. Existing text without a role is left unchanged.
    """
    for item in page['elements']:
        if item['kind'] != 'text' or 'style_role' not in item:
            continue
        role = item['style_role']
        source = page['id'] + '/' + item['id']
        if not isinstance(roles, dict) or not isinstance(role, str) or role not in roles:
            raise ValueError('unknown_text_style: ' + source + '/' + str(role))
        if not isinstance(roles[role], dict) or not roles[role]:
            raise ValueError('invalid_text_style: ' + source + '/' + role)
        override = item.get('style', {})
        if not isinstance(override, dict):
            raise TypeError('invalid_text_style_override: ' + source)
        item['style'] = copy.deepcopy(roles[role]) | copy.deepcopy(override)
        validate_role_style(item['style'], source + '/' + role)


def validate_role_style(style, source):
    """Reject invalid core typography values in the new role path, with provenance.

    This is input validation, not a capability or visual-approval gate. Other
    current API fields retain their public types and require actual export QA.
    """
    for key in ('fontSize', 'lineSpacing'):
        value = style.get(key)
        if key in style and (isinstance(value, bool) or not isinstance(value, (int, float))
                             or not math.isfinite(value) or value <= 0):
            raise ValueError('invalid_text_style_value: ' + source + '/' + key)
    for key in ('bold', 'italic'):
        if key in style and not isinstance(style[key], bool):
            raise ValueError('invalid_text_style_value: ' + source + '/' + key)
    if 'typeface' in style and (not isinstance(style['typeface'], str)
                                or not style['typeface'].strip()):
        raise ValueError('invalid_text_style_value: ' + source + '/typeface')


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
