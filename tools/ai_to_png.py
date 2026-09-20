#!/usr/bin/env python3
"""Render the SINO FRESH .ai artwork to production PNGs (recolor + crop), pixel-perfect
from the source vector — no path reconstruction, so no artifacts.

Outputs (into sinofresh-theme/assets/images/):
  sinofresh-logo-nav.png    wordmark WHITE + icon #5AB735, tagline dropped, transparent bg
  sinofresh-logo-full.png   wordmark WHITE + icon #5AB735 + tagline white (for reference)
and /tmp renders for inspection.
"""
import pymupdf
import numpy as np
from PIL import Image
import os

ROOT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设'
IMG = os.path.join(ROOT, 'sinofresh-theme/assets/images')
OUTDIR = os.path.join(ROOT, 'screenshots/round6')
os.makedirs(OUTDIR, exist_ok=True)

# source colours (0-1 floats from the PDF) -> 8-bit
def f2rgb(f):
    return tuple(int(round(c * 255)) for c in f)

SRC_WORDMARK = f2rgb((0.306, 0.545, 0.42))   # #4E8B6B
SRC_TAGLINE  = f2rgb((0.447, 0.443, 0.443))  # #727171
SRC_ICON     = f2rgb((0.0, 0.541, 0.239))    # #008A3D

NEW_WORDMARK = (255, 255, 255)
NEW_ICON     = (0x5A, 0xB7, 0x35)
NEW_TAGLINE  = (255, 255, 255)

# per-channel tolerance for hue matching. 20 keeps the three source hues
# disjoint: wordmark #4E8B6B vs tagline #727171 differ by 36/26/6 — a wider
# tolerance makes each mask swallow the other and paints the tagline white.
# Antialiased edge pixels keep the pure fill hue, so 20 is still safe.
TOL = 20

def render(path, scale):
    doc = pymupdf.open(path)
    page = doc[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
    img = Image.frombytes('RGBA', (pix.width, pix.height), pix.samples)
    return img

def recolor(img, keep_tagline):
    a = np.asarray(img).astype(np.int16)
    rgb, alpha = a[..., :3], a[..., 3]

    def mask_of(src):
        return (np.abs(rgb - np.array(src)).max(axis=-1) <= TOL) & (alpha > 0)

    m_word = mask_of(SRC_WORDMARK)
    m_tag = mask_of(SRC_TAGLINE)
    m_icon = mask_of(SRC_ICON)

    out = np.zeros_like(a, dtype=np.uint8)
    out[..., 3] = 0

    def paint(mask, color, a_scale=255):
        sel = mask
        out[sel, 0] = color[0]
        out[sel, 1] = color[1]
        out[sel, 2] = color[2]
        out[sel, 3] = (alpha[sel].astype(np.float32) / 255.0 * a_scale).astype(np.uint8)

    paint(m_tag, NEW_TAGLINE, a_scale=int(255 * 0.72))
    # paint after the tagline: the two source hues are close (#4E8B6B vs #727171),
    # so the wordmark must win wherever the tolerance masks overlap
    paint(m_word, NEW_WORDMARK)
    paint(m_icon, NEW_ICON)
    if not keep_tagline:
        # tagline dropped: undo any pixels the tagline pass touched
        out[m_tag & ~m_word & ~m_icon] = 0

    return Image.fromarray(out, 'RGBA'), (m_word.sum(), m_tag.sum(), m_icon.sum())

def autocrop(img, pad=8):
    bbox = img.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(img.width, x1 + pad); y1 = min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))

src = os.path.join(ROOT, 'logo400-130.ai')
SCALE = 3.0  # 400pt -> 1200px wide page; content ~393.5pt -> ~1180px

img = render(src, SCALE)
nav, counts = recolor(img, keep_tagline=False)
full, _ = recolor(img, keep_tagline=True)
print('pixel counts (word/tag/icon):', counts)

nav_c = autocrop(nav)
full_c = autocrop(full)
print('nav size:', nav_c.size, ' full size:', full_c.size)

nav_c.save(os.path.join(IMG, 'sinofresh-logo-nav.png'), optimize=True)
full_c.save(os.path.join(OUTDIR, 'sinofresh-logo-full-ref.png'), optimize=True)
nav_c.save(os.path.join(OUTDIR, 'sinofresh-logo-nav-ref.png'), optimize=True)
print('saved PNGs, nav bytes:', os.path.getsize(os.path.join(IMG, 'sinofresh-logo-nav.png')))

# ---- favicon source check: render the icon .ai too ----
icon_ai = os.path.join(ROOT, '网站网址图标素材512-512.ai')
if os.path.exists(icon_ai):
    pic = render(icon_ai, 3.0)
    pic.save(os.path.join(OUTDIR, 'icon-ai-render-3x.png'))
    print('icon ai page size rendered:', pic.size)
