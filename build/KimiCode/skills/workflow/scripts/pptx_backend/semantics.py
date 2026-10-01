#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Name real picture objects and promote their shared background into the master.

Usage: pptx_semantics.py --input draft.pptx --output named.pptx --manifest JSON
Only this project's fresh exports are supported. Existing user decks are rejected.
"""
import argparse
import copy
import hashlib
import json
import logging
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
LOGGER = logging.getLogger(__name__)


def qn(prefix, name):
    """Return one namespace-qualified OOXML name."""
    return '{' + NS[prefix] + '}' + name


def relationships(files, part):
    """Read a part's actual relationship tree, never guessing a target."""
    rel = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    return rel, ET.fromstring(files[rel])


def target(files, part, relation_type):
    """Resolve exactly one required relationship to its package-relative part."""
    _, rels = relationships(files, part)
    matches = [r for r in rels if r.attrib['Type'].endswith('/' + relation_type)]
    if len(matches) != 1:
        raise ValueError(f'Expected one {relation_type} relationship on {part}')
    return posixpath.normpath(posixpath.join(posixpath.dirname(part), matches[0].attrib['Target'])).lstrip('/')


def serialize(element):
    """Preserve namespace semantics when writing XML bytes."""
    return ET.tostring(element, encoding='utf-8', xml_declaration=True)


def promote_background(files, slide_part, pic, known_hash):
    """Move a known clean background image into the actual shared slide master."""
    layout = target(files, slide_part, 'slideLayout')
    master = target(files, layout, 'slideMaster')
    rid = pic.find('p:blipFill/a:blip', NS).attrib[qn('r', 'embed')]
    _, slide_rels = relationships(files, slide_part)
    relation = next(r for r in slide_rels if r.attrib['Id'] == rid)
    media = posixpath.normpath(posixpath.join(posixpath.dirname(slide_part), relation.attrib['Target'])).lstrip('/')
    digest = hashlib.sha256(files[media]).hexdigest()
    if known_hash and digest != known_hash:
        raise ValueError('Slides do not use the same background bytes')
    rel_path, master_rels = relationships(files, master)
    new_id = 'rIdSharedOpticalBackground'
    if not any(r.attrib['Id'] == new_id for r in master_rels):
        ET.SubElement(master_rels, qn('rel', 'Relationship'), {'Id': new_id,
            'Type': NS['r'] + '/image', 'Target': posixpath.relpath(media, posixpath.dirname(master))})
    master_xml = ET.fromstring(files[master])
    csld = master_xml.find('p:cSld', NS)
    old = csld.find('p:bg', NS)
    if old is not None:
        csld.remove(old)
    bg = ET.Element(qn('p', 'bg'))
    props = ET.SubElement(bg, qn('p', 'bgPr'))
    fill = copy.deepcopy(pic.find('p:blipFill', NS))
    fill.tag = qn('a', 'blipFill')
    fill.find('a:blip', NS).set(qn('r', 'embed'), new_id)
    props.append(fill)
    csld.insert(0, bg)
    files[master], files[rel_path] = serialize(master_xml), serialize(master_rels)
    return digest, master


def transform(source, destination, manifest):
    """Create a new package with named pictures and one verified background master."""
    if destination.exists() or source.resolve() == destination.resolve():
        raise ValueError('Output must be a new file')
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise ValueError('Input ZIP CRC failed')
        files = {name: archive.read(name) for name in archive.namelist()}
    seen_hash = None
    masters = set()
    for index, slide in enumerate(manifest['slides'], 1):
        part = f'ppt/slides/slide{index}.xml'
        xml = ET.fromstring(files[part])
        tree = xml.find('p:cSld/p:spTree', NS)
        pics = tree.findall('p:pic', NS)
        # NOTE: A solid native master has no synthetic picture to promote.
        background_count = 1 if 'background' in manifest else 0
        if len(pics) != len(slide['images']) + background_count:
            raise ValueError(f'Unexpected picture count on slide {index}')
        if background_count:
            seen_hash, master = promote_background(files, part, pics[0], seen_hash)
            tree.remove(pics[0])
        else:
            layout = target(files, part, 'slideLayout')
            master = target(files, layout, 'slideMaster')
        masters.add(master)
        semantic_pics = pics[background_count:]
        for pic, spec in zip(semantic_pics, slide['images'], strict=True):
            props = pic.find('p:nvPicPr/p:cNvPr', NS)
            props.set('name', spec['id'])
            props.set('descr', spec['alt'])
        fixed = [pic for pic, spec in zip(semantic_pics, slide['images'], strict=True) if spec.get('fixed_layout')]
        if fixed:
            move_fixed_art(files, part, tree, fixed, index)
        files[part] = serialize(xml)
    if len(masters) != 1:
        raise ValueError('Expected one shared custom master for the whole deck')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return {'slides': len(manifest['slides']), 'master': next(iter(masters)),
            'shared_background_sha256': seen_hash, 'output': str(destination)}


def move_fixed_art(files, slide_part, slide_tree, pictures, index):
    """Place wide decorative edge-light on a real layout so it cannot intercept slide clicks."""
    old_layout = target(files, slide_part, 'slideLayout')
    master = target(files, old_layout, 'slideMaster')
    new_layout = f'ppt/slideLayouts/slideLayout_format_{index}.xml'
    if new_layout in files:
        raise ValueError('Layout output collision')
    layout_xml = ET.fromstring(files[old_layout])
    layout_tree = layout_xml.find('p:cSld/p:spTree', NS)
    layout_xml.find('p:cSld', NS).set('name', f'Fixed optical accent {index}')
    _, layout_rels = relationships(files, old_layout)
    slide_rel_path, slide_rels = relationships(files, slide_part)
    for picture in pictures:
        rid = picture.find('p:blipFill/a:blip', NS).attrib[qn('r', 'embed')]
        relation = copy.deepcopy(next(r for r in slide_rels if r.attrib['Id'] == rid))
        media = posixpath.normpath(posixpath.join(posixpath.dirname(slide_part), relation.attrib['Target'])).lstrip('/')
        relation.set('Target', posixpath.relpath(media, posixpath.dirname(new_layout)))
        layout_rels.append(relation)
        layout_tree.append(copy.deepcopy(picture))
        slide_tree.remove(picture)
    new_rels = posixpath.join(posixpath.dirname(new_layout), '_rels', posixpath.basename(new_layout)+'.rels')
    files[new_layout], files[new_rels] = serialize(layout_xml), serialize(layout_rels)
    next(r for r in slide_rels if r.attrib['Type'].endswith('/slideLayout')).set('Target', posixpath.relpath(new_layout, posixpath.dirname(slide_part)))
    files[slide_rel_path] = serialize(slide_rels)
    master_rel_path, master_rels = relationships(files, master)
    new_id = f'rIdFixedOpticalLayout{index}'
    ET.SubElement(master_rels, qn('rel', 'Relationship'), {'Id': new_id, 'Type': NS['r']+'/slideLayout', 'Target': posixpath.relpath(new_layout, posixpath.dirname(master))})
    master_xml = ET.fromstring(files[master])
    ids = master_xml.find('p:sldLayoutIdLst', NS)
    number = max(int(item.attrib['id']) for item in ids)+1
    ET.SubElement(ids, qn('p', 'sldLayoutId'), {'id': str(number), qn('r', 'id'): new_id})
    files[master], files[master_rel_path] = serialize(master_xml), serialize(master_rels)
    types = ET.fromstring(files['[Content_Types].xml'])
    # NOTE: OPC content-types requires its namespace as the default, not a prefix.
    ET.register_namespace('', 'http://schemas.openxmlformats.org/package/2006/content-types')
    ET.SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Override', {'PartName':'/'+new_layout, 'ContentType':'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'})
    files['[Content_Types].xml'] = serialize(types)


def main():
    """Validate local CLI arguments and report a bounded export transformation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    result = transform(args.input, args.output, json.loads(args.manifest.read_text()))
    LOGGER.info(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
