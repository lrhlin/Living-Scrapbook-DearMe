import sys, re, xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

def ns(tag):
    return f'{{{NS}}}{tag}'

def main():
    src, dst = sys.argv[1], sys.argv[2]
    tree = ET.parse(src)
    root = tree.getroot()

    # Collect viewBox / dimensions
    vb = root.get('viewBox', '0 0 640 880')
    w = root.get('width', '640')
    h = root.get('height', '880')

    defs = root.find(ns('defs'))
    if defs is None:
        defs = ET.SubElement(root, ns('defs'))
        root.insert(0, defs)

    # --- 1. Remove the existing broken outline group ---
    for g in root.findall(ns('g')):
        if g.get('id') == 'outline':
            root.remove(g)
            break

    # --- 2. Assign id to artwork group so we can clone it ---
    # Wrap all non-defs children in a group with id='artwork' if not already
    children = [c for c in list(root) if c.tag != ns('defs')]
    artwork_g = ET.Element(ns('g'))
    artwork_g.set('id', 'artwork')
    for c in children:
        root.remove(c)
    for c in children:
        artwork_g.append(c)

    # --- 3. Build the tree silhouette clip path from the tier paths ---
    # Extract all path/polygon/rect/ellipse children of artwork for the
    # tree body tiers only: collect the 8 tier paths plus stand rect/polygon.
    # We will union them by listing them all inside a clipPath using
    # clip-rule evenodd on a containing rect (inverted) -- simpler approach:
    # just use the existing tier paths + stand polygons as a clip.
    tier_paths = []
    for elem in list(artwork_g):
        # collect tree tier paths (they have fill url(#treeGrad) or treeGrad2)
        fill = elem.get('fill', '')
        if elem.tag == ns('path') and ('treeGrad' in fill):
            tier_paths.append(elem.get('d', ''))
        # also include the trunk rect
        if elem.tag == ns('rect'):
            x = float(elem.get('x', 0))
            y = float(elem.get('y', 0))
            rw = float(elem.get('width', 0))
            rh = float(elem.get('height', 0))
            if rw < 40 and rh > 50:  # trunk
                tier_paths.append(f'M{x},{y} h{rw} v{rh} h{-rw} Z')
        # stand polygon
        if elem.tag == ns('polygon') and 'standGrad' in elem.get('fill', ''):
            pts = elem.get('points', '')
            nums = pts.split()
            if nums:
                pairs = [p.split(',') for p in nums]
                d = 'M' + ' L'.join(','.join(p) for p in pairs) + ' Z'
                tier_paths.append(d)
        # stand rect
        if elem.tag == ns('rect') and 'standGrad' in elem.get('fill', ''):
            x = float(elem.get('x', 0))
            y = float(elem.get('y', 0))
            rw = float(elem.get('width', 0))
            rh = float(elem.get('height', 0))
            tier_paths.append(f'M{x},{y} h{rw} v{rh} h{-rw} Z')

    clip_path_data = ' '.join(tier_paths)

    # Create clipPath element for decorations
    clip_el = ET.SubElement(defs, ns('clipPath'))
    clip_el.set('id', 'treeClip')
    clip_path_el = ET.SubElement(clip_el, ns('path'))
    clip_path_el.set('d', clip_path_data)
    # small outset via filter on clip is not standard; instead expand paths
    # by wrapping in a filter with feMorphology dilate=10 so ornaments
    # on bough tips are included. Use a feFlood+feComposite trick:
    # Actually clipPath doesn't support filters. Use a rect-based approach:
    # Add a large outset rect and use clip-path with a feFlood workaround.
    # Simplest reliable solution: add 20px margin expand via rect behind path.
    # Instead: apply the clip only to the lights/beads group, not ornaments.
    clip_path_el.set('clip-rule', 'evenodd')
    # Add a full-canvas rect as first child so clip is additive (union)
    # Actually we want to EXCLUDE outside, so just use the paths as union.
    clip_path_el.set('clip-rule', 'nonzero')

    # --- 4. Create filter for white morphological dilation (the outline) ---
    filt = ET.SubElement(defs, ns('filter'))
    filt.set('id', 'dilateOutline')
    filt.set('x', '-5%')
    filt.set('y', '-3%')
    filt.set('width', '110%')
    filt.set('height', '106%')
    filt.set('color-interpolation-filters', 'sRGB')
    # dilate the alpha channel
    morph = ET.SubElement(filt, ns('feMorphology'))
    morph.set('in', 'SourceAlpha')
    morph.set('operator', 'dilate')
    morph.set('radius', '7')
    morph.set('result', 'dilated')
    # flood white
    flood = ET.SubElement(filt, ns('feFlood'))
    flood.set('flood-color', '#fffef5')
    flood.set('flood-opacity', '1')
    flood.set('result', 'white')
    # composite: white where dilated
    comp = ET.SubElement(filt, ns('feComposite'))
    comp.set('in', 'white')
    comp.set('in2', 'dilated')
    comp.set('operator', 'in')
    comp.set('result', 'outline')
    # merge outline ONLY (we keep original graphic in artwork group, not here)
    merge = ET.SubElement(filt, ns('feMerge'))
    mn = ET.SubElement(merge, ns('feMergeNode'))
    mn.set('in', 'outline')

    # --- 5. Create outline layer: clone artwork, apply filter, render white ---
    outline_use = ET.Element(ns('use'))
    outline_use.set('{http://www.w3.org/1999/xlink}href', '#artwork')
    outline_use.set('href', '#artwork')
    outline_use.set('filter', 'url(#dilateOutline)')
    outline_use.set('id', 'outline')

    # --- 6. Clip stray lights/beads: wrap lights in a group with clip-path ---
    # Find all circle elements that are fairy lights or beads (small r, specific fills)
    # and group them, applying treeClip with a small morphology-expanded version.
    # For simplicity, we apply clip-path to a wrapper group around ALL artwork
    # children that are small decorative circles (lights + beads).
    # We identify them: they are direct children with tag circle and r<=5
    lights = []
    beads = []
    others = []
    for elem in list(artwork_g):
        if elem.tag == ns('circle'):
            r = float(elem.get('r', 99))
            if r <= 5:
                lights.append(elem)
                continue
        others.append(elem)

    # Rebuild artwork_g children: others first, then lights wrapped in clipped group
    for elem in list(artwork_g):
        artwork_g.remove(elem)
    for elem in others:
        artwork_g.append(elem)
    if lights:
        lg = ET.SubElement(artwork_g, ns('g'))
        lg.set('clip-path', 'url(#treeClip)')
        for elem in lights:
            lg.append(elem)

    # --- 7. Assemble root: outline use first, then artwork ---
    root.append(outline_use)
    root.append(artwork_g)

    ET.indent(tree, space='  ')
    tree.write(dst, xml_declaration=True, encoding='unicode')

main()

