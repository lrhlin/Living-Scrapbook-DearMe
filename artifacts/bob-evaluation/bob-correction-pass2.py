import sys
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

GARLAND_FILLS = {'#d4a820', '#c89c10', '#b88c08'}
LIGHT_FILLS = {'#ff4040', '#ff3030', '#ffe040', '#60a0ff', '#40e060'}


def ns(tag):
    return f'{{{NS}}}{tag}'


def is_garland_group(elem):
    """True if this <g> is a gold bead garland group."""
    if elem.tag != ns('g'):
        return False
    fill = elem.get('fill', '').strip().lower()
    return fill in GARLAND_FILLS


def is_fairy_light(elem):
    """True if this element is a fairy-light circle (not spire tip, not garland bead)."""
    if elem.tag != ns('circle'):
        return False
    fill = elem.get('fill', '').strip().lower()
    return fill in LIGHT_FILLS


def rect_to_path(elem):
    x = float(elem.get('x', 0))
    y = float(elem.get('y', 0))
    w = float(elem.get('width', 0))
    h = float(elem.get('height', 0))
    return f'M{x},{y} h{w} v{h} h{-w} Z'


def polygon_to_path(elem):
    pts = elem.get('points', '').split()
    if not pts:
        return ''
    pairs = [p.split(',') for p in pts]
    return 'M' + ' L'.join(','.join(p) for p in pairs) + ' Z'


def main():
    src, dst = sys.argv[1], sys.argv[2]
    tree = ET.parse(src)
    root = tree.getroot()

    defs = root.find(ns('defs'))
    if defs is None:
        defs = ET.SubElement(root, ns('defs'))
        root.insert(0, defs)

    # --- Remove existing broken outline group ---
    for child in list(root):
        if child.get('id') == 'outline':
            root.remove(child)
            break

    # --- Collect the tree silhouette geometry for the clip path and outline ---
    # We need: all tier paths (fill url(#treeGrad) or treeGrad2), trunk rects,
    # stand polygon and stand rect.
    silhouette_elements = []  # list of (tag, attribs) to replicate

    # Walk direct children of root (the flat original structure)
    # We also need to handle groups like <g id='stand'>
    def collect_silhouette(container):
        for elem in container:
            tag = elem.tag
            fill = elem.get('fill', '')
            eid = elem.get('id', '')
            # Tree tier paths
            if tag == ns('path') and ('treeGrad' in fill):
                silhouette_elements.append(('path', elem.get('d', '')))
            # Trunk rects (dark brown fill, not standGrad)
            if tag == ns('rect') and 'standGrad' not in fill and '#4a3010' in fill:
                silhouette_elements.append(('path', rect_to_path(elem)))
            # Second trunk rect (lighter highlight - include for coverage)
            if tag == ns('rect') and '#6a4820' in fill:
                silhouette_elements.append(('path', rect_to_path(elem)))
            # Stand polygon
            if tag == ns('polygon') and 'standGrad' in fill:
                silhouette_elements.append(('path', polygon_to_path(elem)))
            # Stand rect
            if tag == ns('rect') and 'standGrad' in fill:
                silhouette_elements.append(('path', rect_to_path(elem)))
            # Recurse into groups (e.g. <g id='stand'>)
            if tag == ns('g'):
                # Only recurse into structural groups, not garland or ornament groups
                gid = elem.get('id', '')
                gfill = elem.get('fill', '')
                if gid in ('stand', 'outline') or gid.startswith('tier'):
                    collect_silhouette(elem)
                elif not gfill:  # structural group without a fill override
                    collect_silhouette(elem)

    collect_silhouette(root)

    # --- Build clip path from silhouette (union of all tier+stand paths) ---
    # Remove any existing treeClip
    for existing in list(defs):
        if existing.get('id') == 'treeClip':
            defs.remove(existing)

    clip_el = ET.SubElement(defs, ns('clipPath'))
    clip_el.set('id', 'treeClip')
    # Add a small outset: use a filter on the clipPath's path is not supported.
    # Instead we union all paths into one compound path element with a small
    # stroke trick: we cannot stroke inside clipPath. So we use a filter-enlarged
    # clipPath. clipPath does NOT support filter=, but we can use a child
    # <use> trick via a referenced filter... also not standard.
    # Best approach: build the clip from paths WITH a constant outward offset
    # approximated by collecting all paths and setting clip-rule=nonzero.
    # The garland beads should be clipped to foliage edges; a 0px clip is fine
    # since beads that land on bough-tips should still show (they are on the tree).
    # The clip just needs to cut off beads/lights that overshoot the silhouette.
    # We use a generous clip: the actual paths union already covers the full foliage.
    all_d = ' '.join(d for (_, d) in silhouette_elements if d)
    clip_path_el = ET.SubElement(clip_el, ns('path'))
    clip_path_el.set('d', all_d)
    clip_path_el.set('clip-rule', 'nonzero')
    clip_path_el.set('fill-rule', 'nonzero')

    # --- Build the vector outline (stroke-based, no feMorphology) ---
    # Render all silhouette paths with thick rounded stroke in warm white,
    # filled and stroked so the 14-unit stroke gives ~7 units on each side.
    outline_g = ET.Element(ns('g'))
    outline_g.set('id', 'outline')
    outline_g.set('fill', '#fffef5')
    outline_g.set('stroke', '#fffef5')
    outline_g.set('stroke-width', '14')
    outline_g.set('stroke-linejoin', 'round')
    outline_g.set('stroke-linecap', 'round')
    outline_g.set('opacity', '1')
    for (_tag, d) in silhouette_elements:
        p = ET.SubElement(outline_g, ns('path'))
        p.set('d', d)

    # --- Wrap all original children (except defs) in artwork group ---
    children = [c for c in list(root) if c.tag != ns('defs')]
    artwork_g = ET.Element(ns('g'))
    artwork_g.set('id', 'artwork')
    for c in children:
        root.remove(c)

    # --- Apply clips: garland groups and fairy-light circles ---
    # We rebuild children into artwork_g, modifying garland groups and
    # wrapping fairy lights in clipped groups.
    # Collect fairy light circles that are direct children:
    fairy_lights = []
    other_children = []
    for elem in children:
        if is_fairy_light(elem):
            fairy_lights.append(elem)
        else:
            other_children.append(elem)

    # For each non-fairy-light child, if it is a garland group, add clip-path
    for elem in other_children:
        if is_garland_group(elem):
            elem.set('clip-path', 'url(#treeClip)')
        artwork_g.append(elem)

    # Append fairy lights in a single clipped wrapper (after ornaments, before spire)
    # Actually the spire is already in other_children so lights go at correct z-order.
    # We insert the clipped lights group just before the spire-related elements.
    # For simplicity: just append a clipped group at end of artwork_g;
    # fairy lights are small dots, z-order relative to ornaments doesn't matter visually.
    if fairy_lights:
        lg = ET.SubElement(artwork_g, ns('g'))
        lg.set('id', 'fairy_lights')
        lg.set('clip-path', 'url(#treeClip)')
        for elem in fairy_lights:
            lg.append(elem)

    # --- Assemble: outline first (behind everything), then artwork ---
    root.append(outline_g)
    root.append(artwork_g)

    ET.indent(tree, space='  ')
    tree.write(dst, xml_declaration=True, encoding='unicode')


main()

