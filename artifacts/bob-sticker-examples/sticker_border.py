"""Add a round vector border from an SVG's actual artwork geometry."""
from copy import deepcopy
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
SHAPES = {'path', 'circle', 'ellipse', 'rect', 'polygon', 'polyline', 'line'}
ALLOWED = SHAPES | {'svg', 'title', 'desc', 'defs', 'g', 'linearGradient',
                    'radialGradient', 'stop', 'clipPath'}


def validate(root):
    ids = []
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] not in ALLOWED:
            raise ValueError('Unsupported SVG element')
        if element.get('id'):
            ids.append(element.get('id'))
        for name, value in element.attrib.items():
            if name.lower().startswith('on') or 'href' in name.lower():
                raise ValueError('Scripts and external resources are not allowed')
            for target in re.findall(r'url\((.*?)\)', value):
                if not target.strip(' \"\'').startswith('#'):
                    raise ValueError('Only local SVG resources are allowed')
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate SVG ids')


def add_border(source, destination, radius=7):
    root = ET.fromstring(Path(source).read_text())
    validate(root)
    artwork = next((e for e in root if e.get('id') == 'artwork'), None)
    if artwork is None:
        raise ValueError('Expected a top-level artwork group')
    backing = deepcopy(artwork)

    def whiten(element, inherited):
        paint = dict(inherited)
        for key in ('fill', 'stroke', 'stroke-width'):
            if key in element.attrib:
                paint[key] = element.get(key)
        element.attrib.pop('id', None)
        element.set('opacity', '1')
        element.set('fill-opacity', '1')
        element.set('stroke-opacity', '1')
        if element.tag.rsplit('}', 1)[-1] in SHAPES:
            element.set('fill', 'none' if paint['fill'] == 'none' else '#fffdf7')
            width = float(paint['stroke-width']) if paint['stroke'] != 'none' else 0
            element.set('stroke', '#fffdf7')
            element.set('stroke-width', str(2 * radius + width))
            element.set('stroke-linejoin', 'round')
            element.set('stroke-linecap', 'round')
        for child in element:
            whiten(child, paint)

    whiten(backing, {'fill': '#000', 'stroke': 'none', 'stroke-width': '1'})
    backing.set('id', 'sticker-border')
    root.insert(list(root).index(artwork), backing)
    validate(root)
    ET.indent(root, space='  ')
    Path(destination).write_text(ET.tostring(root, encoding='unicode') + '\n')


if __name__ == '__main__':
    add_border(sys.argv[1], sys.argv[2])
