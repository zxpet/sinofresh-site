#!/usr/bin/env python3
"""Inspect the SINO FRESH .ai (PDF-compatible) artwork: page size, drawings, colors, even_odd flags."""
import fitz, collections, sys

src = sys.argv[1] if len(sys.argv) > 1 else '/Users/meng/WorkBuddy/sinofresh外贸网站建设/logo400-130.ai'
doc = fitz.open(src)
print('pages:', len(doc))
page = doc[0]
print('mediabox:', page.rect, 'rotation:', page.rotation)

drawings = page.get_drawings()
print('drawing count:', len(drawings))
byfill = collections.Counter()
evenodd = collections.Counter()
types = collections.Counter()
for d in drawings:
    f = d.get('fill')
    key = tuple(round(c, 3) for c in f) if f else None
    byfill[key] += 1
    evenodd[(key, d.get('even_odd'))] += 1
    types[d.get('type')] += 1
print('types:', dict(types))
print('fill colors:')
for k, v in byfill.most_common():
    print('  ', k, v)
print('fill x even_odd:')
for k, v in evenodd.most_common():
    print('  ', k, v)

# bbox of everything
import itertools
xs, ys, xe, ye = [], [], [], []
for d in drawings:
    r = d['rect']
    xs.append(r.x0); ys.append(r.y0); xe.append(r.x1); ye.append(r.y1)
print('content bbox:', min(xs), min(ys), max(xe), max(ye))

# text?
print('text:', repr(page.get_text()[:200]))
print('images:', len(page.get_images(full=True)))
