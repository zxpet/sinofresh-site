#!/usr/bin/env python3
"""Task 1 — wrap every dosage-card image in an <a> pointing at its own
dosage page.  Two markup families:

  A. sf-tile pages (front-page, products, 404, soft-chews/tablets/powders/pastes)
     the media figure carries .sf-tile__media -> link every such figure.
  B. legacy dosage pages (drops/liquids/fish-oil/dental-chews)
     hero + 7 related figures share the same plain classes -> link only the
     7 figures that sit after the "Related Dosage Forms" heading.

Strategy: markup-only edit, CSS untouched.
  * block comment gains linkDestination:"custom" + href
  * <a href> goes INSIDE <figure>, wrapping the sole <img>
  * existing classes (incl. the load-bearing .sf-tile__media) are preserved,
    so `.sf-tile__media` box rules and `.sf-tile:hover .sf-tile__media img`
    zoom keep matching with zero specificity change.
"""
import re
import sys
import os
import json
import shutil

THEME = "/Users/meng/Local Sites/sinofresh/app/public/wp-content/themes/sinofresh-theme"
BACKUP = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/round9-task1-20260916"

MAP = {
    "soft-chews": "/products/soft-chews/",
    "tablets": "/products/tablets/",
    "powders": "/products/powders/",
    "pastes": "/products/pastes/",
    "drops": "/products/drops/",
    "liquids": "/products/liquids/",
    "fish-oil": "/products/fish-oil/",
    "dental-chews": "/products/dental-chews/",
}

MODE_A = [
    "templates/front-page.html",
    "templates/page-products.html",
    "templates/404.html",
    "templates/page-soft-chews.html",
    "templates/page-tablets.html",
    "templates/page-powders.html",
    "templates/page-pastes.html",
]
MODE_B = [
    "templates/page-drops.html",
    "templates/page-liquids.html",
    "templates/page-fish-oil.html",
    "templates/page-dental-chews.html",
]

# <!-- wp:image {..} --> \n <figure class="..">…</figure> \n <!-- /wp:image -->
BLOCK = re.compile(
    r'<!-- wp:image (?P<json>\{[^\n]*?\}) -->(?P<nl>\r?\n)'
    r'(?P<indent>[^\S\n]*)<figure class="(?P<cls>[^"]*)">(?P<inner>.*?)</figure>'
    r'(?P<nl2>\r?\n)(?P<indent2>[^\S\n]*)<!-- /wp:image -->',
    re.S,
)
IMG = re.compile(r'<img\b[^>]*?\bsrc="[^"]*/uploads/[^"]*?/([^"/]+)\.webp"', re.I)


def target_for(inner, where):
    m = IMG.search(inner)
    if not m:
        raise SystemExit(f"no uploads .webp img inside a figure near {where}")
    stem = m.group(1)
    if stem not in MAP:
        raise SystemExit(f"unmapped image stem {stem!r} near {where}")
    return stem, MAP[stem]


def run(dry=True):
    total = 0
    report = []
    for rel, area in [(f, "A") for f in MODE_A] + [(f, "B") for f in MODE_B]:
        path = os.path.join(THEME, rel)
        src = open(path, encoding="utf-8").read()
        out = []
        pos = 0
        hits = []

        for m in BLOCK.finditer(src):
            cls = m.group("cls")
            start = m.start()
            if area == "A":
                if "sf-tile__media" not in cls:
                    continue
            else:
                rel_h2 = src.find("Related Dosage Forms")
                if rel_h2 == -1:
                    raise SystemExit(f"{rel}: no Related Dosage Forms heading")
                if start < rel_h2:
                    continue  # hero
            hits.append((start, m))

        if not hits:
            raise SystemExit(f"{rel}: zero matching image blocks")

        for start, m in hits:
            inner = m.group("inner")
            stem, url = target_for(inner, f"{rel}@{start}")
            out.append(src[pos:start])
            js = m.group("json")
            assert '"linkDestination"' not in js, f"{rel}: already linked"
            new_js = js[:-1] + ',"linkDestination":"custom","href":"%s"}' % url
            img = inner.strip()
            new_block = (
                '<!-- wp:image %s -->%s%s<figure class="%s"><a href="%s">%s</a></figure>%s%s<!-- /wp:image -->'
                % (
                    new_js,
                    m.group("nl"),
                    m.group("indent"),
                    m.group("cls"),
                    url,
                    img,
                    m.group("nl2"),
                    m.group("indent2"),
                )
            )
            out.append(new_block)
            pos = m.end()
            total += 1
        out.append(src[pos:])
        new_src = "".join(out)
        report.append((rel, len(hits), len(new_src) - len(src)))

        if not dry:
            os.makedirs(BACKUP, exist_ok=True)
            shutil.copy2(path, os.path.join(BACKUP, os.path.basename(rel)))
            open(path, "w", encoding="utf-8").write(new_src)

    print(f"{'DRY-RUN' if dry else 'APPLIED'}  total cards linked = {total}")
    for rel, n, dn in report:
        print(f"  {rel:34s} {n:2d} cards   {dn:+d} bytes")
    exp = 8 * 3 + 7 * 8
    print(f"  expected {exp}  ->  {'OK' if total == exp or dry else 'MISMATCH'}")
    return total


if __name__ == "__main__":
    run(dry="--apply" not in sys.argv)
