#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step 3 — rewrite templates/single-sf_formula.html.

One file only, but three structural moves, so the transform is written out
and asserted rather than done by hand in an editor:

  1. a new product-gallery band right after the hero      (marker: B2D-S3: gallery)
  2. the existing [sf_formula_body] band MOVED above the
     Specification cards — the module order the brief asks for
  3. two new bands after the Specification cards          (markers: B2D-S3: actives,
                                                           B2D-S3: composition)

Nothing is deleted: the body block keeps its own comment line verbatim, it
just travels. The inverse transform lives in b2d_s3_confine.py, so the
confinement proof is the exact undo of this file.

Anchors are looked up with a count assertion (exactly one occurrence each), so
a second run cannot double-apply, and a changed template fails loudly instead
of silently writing the wrong bytes.

Usage:
    python3 tools/b2d_s3_apply.py --check     # dry run
    python3 tools/b2d_s3_apply.py --apply     # writes the template
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL_REL = "sinofresh-theme/templates/single-sf_formula.html"
TPL = os.path.join(ROOT, TPL_REL)
BASELINE = "cb63af6"          # Batch 2D Step 2 — the commit this batch starts from

# --- the four units ---------------------------------------------------------
# The gallery band reuses the Step-2 container serialisation verbatim, minus
# the per-page `form` attribute: one template serves all 21 formulas, so the
# shortcode resolves the dosage form from the taxonomy itself. A hard-coded
# slug would be wrong on the other 20 pages.
GALLERY_UNIT = (
    "<!-- B2D-S3: gallery -->\n"
    '<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery",'
    '"backgroundColor":"bg-light","layout":{"type":"constrained"},'
    '"style":{"spacing":{"padding":{"top":"var:preset|spacing|80",'
    '"bottom":"var:preset|spacing|80"}}}} -->\n'
    '<section id="gallery" class="wp-block-group sf-gallery '
    'has-bg-light-background-color has-background" '
    'style="padding-top:var(--wp--preset--spacing--80);'
    'padding-bottom:var(--wp--preset--spacing--80)">\n'
    "<!-- wp:html -->\n"
    "[sf_formula_gallery]\n"
    "<!-- /wp:html -->\n"
    "</section>\n"
    "<!-- /wp:group -->\n\n"
)

# The band that travels. Its comment line is the Step-2 baseline's own text —
# left untouched so the render comparison sees a move and not an edit.
BODY_UNIT = (
    "<!-- Block 3: long copy (emitted only when the record has some) -->\n"
    "<!-- wp:html -->\n"
    "[sf_formula_body]\n"
    "<!-- /wp:html -->\n\n"
)

ACTIVES_UNIT = (
    "<!-- B2D-S3: actives -->\n"
    "<!-- wp:html -->\n"
    "[sf_formula_detail_actives]\n"
    "<!-- /wp:html -->\n\n"
)

COMPOSITION_UNIT = (
    "<!-- B2D-S3: composition -->\n"
    "<!-- wp:html -->\n"
    "[sf_formula_detail_composition]\n"
    "<!-- /wp:html -->\n\n"
)

# --- the three anchors ------------------------------------------------------
# Where the hero ends and the Specification band begins.
HERO_SPEC_ANCHOR = "<!-- /wp:group -->\n\n<!-- Block 2: Specification -->"
# Where the Specification band ends and the related-formulas band begins.
# Only meaningful AFTER the body unit has been lifted out of the way, which is
# why the transform removes it first.
SPEC_RELATED_ANCHOR = "<!-- /wp:group -->\n\n<!-- Block 4: related formulas -->"


def transform(text):
    """Baseline template -> Step-3 template. Raises on any surprise."""
    def once(haystack, needle, what):
        n = haystack.count(needle)
        if n != 1:
            raise SystemExit("%s occurs %d times, expected exactly 1" % (what, n))
        return n

    once(text, BODY_UNIT, "the [sf_formula_body] unit")
    once(text, HERO_SPEC_ANCHOR, "the hero -> Specification anchor")
    for unit in (GALLERY_UNIT, ACTIVES_UNIT, COMPOSITION_UNIT):
        if unit in text:
            raise SystemExit("already carries %r" % unit.splitlines()[0])

    # 1. lift the body band out. This has to happen BEFORE the next anchor is
    #    looked up: in the baseline the body unit is exactly what sits between
    #    the Specification cards and the related-formulas band.
    text = text.replace(BODY_UNIT, "", 1)
    once(text, SPEC_RELATED_ANCHOR, "the Specification -> related anchor")
    # 2. gallery + body between the hero and the Specification cards
    text = text.replace(
        HERO_SPEC_ANCHOR,
        "<!-- /wp:group -->\n\n" + GALLERY_UNIT + BODY_UNIT + "<!-- Block 2: Specification -->",
        1,
    )
    # 3. the two new data bands between the Specification cards and the grid
    text = text.replace(
        SPEC_RELATED_ANCHOR,
        "<!-- /wp:group -->\n\n" + ACTIVES_UNIT + COMPOSITION_UNIT + "<!-- Block 4: related formulas -->",
        1,
    )
    return text


def main(apply):
    # newline='' on both ends: the template is LF-only with no BOM today (checked),
    # and universal-newline translation must not be allowed to rewrite CRLF
    # endings on some future edit — that would be a whole-file diff.
    with open(TPL, encoding="utf-8", newline="") as fh:
        cur = fh.read()
    new = transform(cur)

    # Sanity: the three new markers are present exactly once, in the order the
    # brief asks for, and the old block did not simply get duplicated.
    order = [new.index("B2D-S3: gallery"), new.index("[sf_formula_body]"),
             new.index("B2D-S3: actives"), new.index("B2D-S3: composition"),
             new.index("<!-- Block 4: related formulas -->")]
    if order != sorted(order):
        raise SystemExit("module order is wrong: %r" % order)
    if new.count("[sf_formula_body]") != 1:
        raise SystemExit("body shortcode duplicated")
    if new.count("<section") != new.count("</section>"):
        raise SystemExit("unbalanced <section> tags")

    b_cur = len(cur.encode("utf-8"))
    b_new = len(new.encode("utf-8"))
    print("template %s" % TPL_REL)
    print("  bytes %d -> %d  (%+d)" % (b_cur, b_new, b_new - b_cur))
    print("  lines %d -> %d  (%+d)" %
          (cur.count("\n"), new.count("\n"), new.count("\n") - cur.count("\n")))
    for name, needle in (("gallery", GALLERY_UNIT), ("body (moved)", BODY_UNIT),
                         ("actives", ACTIVES_UNIT), ("composition", COMPOSITION_UNIT)):
        print("  %-12s x%d" % (name, new.count(needle)))

    if not apply:
        print("\n--check: nothing written")
        return 0

    with open(TPL, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    p = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (BASELINE, TPL_REL)],
                       capture_output=True)
    print("\n--apply: written. baseline %s is %d B" % (BASELINE, len(p.stdout)))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if cmd not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    sys.exit(main(cmd == "--apply"))
