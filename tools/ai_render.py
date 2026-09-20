#!/usr/bin/env python3
"""Render the .ai page to PNG at high DPI + dump wordmark path bboxes."""
import pymupdf, collections, sys

src = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/logo400-130.ai'
doc = pymupdf.open(src)
page = doc[0]

# 1) wordmark path bboxes
print('=== wordmark (#4E8B6B) path bboxes ===')
rows = []
for d in page.get_drawings():
    f = d.get('fill')
    if f and tuple(round(c, 3) for c in f) == (0.306, 0.545, 0.42):
        r = d['rect']
        rows.append((round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1), len(d['items'])))
for r in sorted(rows):
    print('  x %6.1f-%6.1f  y %5.1f-%5.1f  segs=%d' % r)

print('=== icon (#008A3D) path bboxes ===')
for d in page.get_drawings():
    f = d.get('fill')
    if f and tuple(round(c, 3) for c in f) == (0.0, 0.541, 0.239):
        r = d['rect']
        print('  x %6.1f-%6.1f  y %5.1f-%5.1f  segs=%d' % (r.x0, r.y0, r.x1, r.y1, len(d['items'])))

# 2) render full page at 3x, transparent
mat = pymupdf.Matrix(3, 3)
pix = page.get_pixmap(matrix=mat, alpha=True)
pix.save('/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6/ai-render-3x.png')
print('rendered', pix.width, pix.height)
