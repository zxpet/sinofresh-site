#!/usr/bin/env python3
"""Convert the homepage imagery to sized WebP.

The tiles render at ~260px on a 4-column grid (340px full-width on mobile), so
720px square covers both at 2x. The hero renders at ~504px wide, so 1100px
covers 2x. PNG originals are kept untouched.
"""
import os
from PIL import Image

SRC = "/Users/meng/Local Sites/sinofresh/app/public/wp-content/uploads/2026/09"
TILES = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids",
         "fish-oil", "dental-chews"]

for name in TILES:
    src = os.path.join(SRC, name + ".png")
    dst = os.path.join(SRC, name + ".webp")
    im = Image.open(src).convert("RGB")
    im = im.resize((720, 720), Image.LANCZOS)
    im.save(dst, "WEBP", quality=82, method=6)
    print(f"{name}.webp  {os.path.getsize(dst)//1024} KB  (was {os.path.getsize(src)//1024} KB png)")

src = os.path.join(SRC, "hero-facility.png")
dst = os.path.join(SRC, "hero-facility.webp")
im = Image.open(src).convert("RGB")
im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
im.save(dst, "WEBP", quality=84, method=6)
print(f"hero-facility.webp  {os.path.getsize(dst)//1024} KB  {im.size}  (was {os.path.getsize(src)//1024} KB png)")
