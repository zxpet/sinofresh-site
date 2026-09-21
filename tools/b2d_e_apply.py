#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step E — delete three sections from the eight dosage pages.

The dosage pages are card-wall pages (they list the formulas of one dosage
form). This batch removes the detail sections so the page reads
Hero -> card wall -> configurator -> How We Work -> FAQ -> related -> CTA:

  1. sf-facts band      — B2D-S5 "core facts + Direct Answer" (marker pair)
  2. sf-spectable       — "Typical specifications" table (group JSON literal)
  3. sf-actives / B2D-S1 — the [sf_formula_actives] wrapper (open marker only;
     the block ends at its own <!-- /wp:group -->, so the span runs to the
     next top-level comment, <!-- Block 9: How We Work -->)

Only deletions plus the version bump 2.10.51 -> 2.10.52. Nothing is added:
the [sf_formula_actives] / [sf_formula_detail_actives] shortcodes and every
.sf-* CSS rule stay exactly as they are (code and CSS are kept for the F1
batch to re-use).

Known consequence, accepted in the batch decision: the formula DETAIL pages'
hero meta line ("Soft Chews · MOQ ... · Lead time ...") is composed by
sinofresh_formula_spec_cell() from the sf-spectable cells of the dosage-page
template. With the table gone it degrades to the bare form label — the
function's designed fallback — and 21 detail pages (plus their zh renders)
are expected to differ; F1 will re-point spec_cell at the new facts row.

usage:
    python3 tools/b2d_e_apply.py --check     # dry run, prints the plan
    python3 tools/b2d_e_apply.py --apply     # writes the files
"""

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(HERE), "sinofresh-theme")
TPL = os.path.join(THEME, "templates")

SLUGS = [
    "soft-chews", "tablets", "powders", "pastes",
    "drops", "liquids", "fish-oil", "dental-chews",
]

OLD_VER = "2.10.51"
NEW_VER = "2.10.52"

# --- span 1: the B2D-S5 band, marker pair --------------------------------
S5_OPEN = "<!-- B2D-S5: core facts -->"
S5_CLOSE = "<!-- /B2D-S5 -->"

# --- span 2: sf-spectable through B2D-S1, two anchors ---------------------
# Start: the spectable group's own serialised JSON (unique per page, 8/8
# above).  End: exclusive — the next top-level comment after the B2D-S1
# group closes.  Everything between the two anchors goes, and the blank
# line layout is preserved because both anchors sit on their own lines and
# the deletion stops right before the end anchor.
SPEC_START = '<!-- wp:group {"tagName":"section","className":"sf-spectable","layout"'
BLOCK9 = "<!-- Block 9: How We Work -->"


def fail(msg):
    print("FAIL  " + msg)
    sys.exit(1)


def cut_span(text, start_marker, end_marker, label):
    """Delete [start of start_marker, start of end_marker).

    The end anchor itself is NOT consumed, so the blank line that preceded
    it stays and the file keeps its one-blank-line rhythm.  Returns
    (new_text, deleted_bytes)."""
    if text.count(start_marker) != 1:
        fail("%s: start marker occurs %d time(s), expected exactly 1: %r"
             % (label, text.count(start_marker), start_marker[:60]))
    if text.count(end_marker) != 1:
        fail("%s: end marker occurs %d time(s), expected exactly 1: %r"
             % (label, text.count(end_marker), end_marker[:60]))
    s = text.index(start_marker)
    e = text.index(end_marker)
    if e <= s:
        fail("%s: end anchor precedes the start anchor" % label)
    gone = text[s:e]
    return text[:s] + text[e:], gone


def rewrite_template(slug):
    """Return (new_text, [deleted_1, deleted_2]) or (None, None) if done."""
    path = os.path.join(TPL, "page-%s.html" % slug)
    with open(path, encoding="utf-8") as fh:
        orig = fh.read()

    if S5_OPEN not in orig and SPEC_START not in orig:
        return None, None

    text = orig
    gone = []

    # -- span 1: B2D-S5.  The close marker is consumed too, and exactly one
    # of the two surrounding blank lines goes with it so exactly one is left.
    if text.count(S5_OPEN) != 1 or text.count(S5_CLOSE) != 1:
        fail("%s: B2D-S5 marker pair not (1,1)" % slug)
    s = text.index(S5_OPEN)
    e = text.index(S5_CLOSE) + len(S5_CLOSE)
    if text[e:e + 2] != "\n\n":
        fail("%s: expected a blank line right after %s" % (slug, S5_CLOSE))
    gone.append(text[s:e + 2])
    text = text[:s] + text[e + 2:]

    # -- span 2: spectable + B2D-S1, one contiguous cut.
    text, g2 = cut_span(text, SPEC_START, BLOCK9, slug)
    gone.append(g2)

    # per-page sanity on what is being deleted: the three sections and the
    # page's own shortcode, and none of the sections that must survive.
    joined = "\n".join(gone)
    for needle in (S5_OPEN, "sf-spectable", "sf-facts",
                   "B2D-S1", '[sf_formula_actives form="%s"]' % slug):
        if needle not in joined:
            fail("%s: deleted span lacks %r" % (slug, needle))
    for survivor in ("<h2", "Frequently Asked Questions",
                     "How We Work", "Related Dosage Forms",
                     "sf-formulas", "configurator"):
        if survivor in joined:
            fail("%s: deleted span contains survivor content %r"
                 % (slug, survivor))
    if gone[1].startswith(SPEC_START) and BLOCK9 in gone[1]:
        fail("%s: end anchor was swallowed" % slug)

    return text, gone


def rewrite_style(text):
    if text.count("Version: %s" % OLD_VER) != 1:
        fail("style.css: 'Version: %s' not found exactly once" % OLD_VER)
    return text.replace("Version: %s" % OLD_VER, "Version: %s" % NEW_VER, 1)


def rewrite_functions(text):
    needle = "'%s'" % OLD_VER
    if text.count(needle) != 1:
        fail("functions.php: %r not found exactly once" % needle)
    return text.replace(needle, "'%s'" % NEW_VER, 1)


def self_check(style_text, fn_text, templates):
    """Read-back assertions that do not depend on the apply run."""
    if "Version: %s" % NEW_VER not in style_text:
        fail("self-check: style.css version not bumped")
    if "Version: %s" % OLD_VER in style_text:
        fail("self-check: old version still in style.css")
    if "'%s'" % NEW_VER not in fn_text:
        fail("self-check: functions.php version not bumped")
    for slug, text in templates.items():
        for gone_marker in (S5_OPEN, S5_CLOSE, "sf-spectable",
                            "B2D-S1", "sf-facts", "sf-actives"):
            if gone_marker in text:
                fail("self-check: %s still contains %r" % (slug, gone_marker))
        for keep in (BLOCK9, "Frequently Asked Questions",
                     "sf-formulas", "[sf_formula_actives" if False else "Related"):
            if keep not in text:
                fail("self-check: %s lost %r" % (slug, keep))
    # code + CSS stay untouched
    fn_path = os.path.join(THEME, "functions.php")
    css_path = os.path.join(THEME, "style.css")
    with open(fn_path, encoding="utf-8") as fh:
        fnt = fh.read()
    for sc in ("sf_formula_actives", "sf_formula_detail_actives"):
        if sc not in fnt:
            fail("self-check: shortcode %s missing from functions.php" % sc)
    with open(css_path, encoding="utf-8") as fh:
        csst = fh.read()
    for cls in (".sf-spectable", ".sf-actives", ".sf-facts"):
        if cls not in csst:
            fail("self-check: CSS class %s missing from style.css" % cls)
    if csst.count(":has(") != 163:
        fail("self-check: style.css :has( count drifted (expected 163)")


def main():
    do_apply = "--apply" in sys.argv
    if not do_apply and "--check" not in sys.argv:
        print(__doc__)
        sys.exit(2)

    print("== batch 2D step E: delete sf-facts / sf-spectable / B2D-S1 "
          "on 8 dosage pages ==")

    templates = {}
    for slug in SLUGS:
        new_text, gone = rewrite_template(slug)
        templates[slug] = new_text
        if new_text is None:
            print("  %-13s already applied (markers absent)" % slug)
            continue
        old_len = len(open(os.path.join(TPL, "page-%s.html" % slug),
                           encoding="utf-8").read())
        print("  %-13s %6d -> %6d B  (-%d, two spans: %d + %d)"
              % (slug, old_len, len(new_text), old_len - len(new_text),
                 len(gone[0]), len(gone[1])))

    style_path = os.path.join(THEME, "style.css")
    fn_path = os.path.join(THEME, "functions.php")
    with open(style_path, encoding="utf-8") as fh:
        style_text = fh.read()
    with open(fn_path, encoding="utf-8") as fh:
        fn_text = fh.read()
    style_new = rewrite_style(style_text)
    fn_new = rewrite_functions(fn_text)
    print("  style.css     %6d -> %6d B  (version only)"
          % (len(style_text), len(style_new)))
    print("  functions.php %6d -> %6d B  (version only)"
          % (len(fn_text), len(fn_new)))

    if not do_apply:
        print("\nDRY RUN — no files written")
        return

    for slug, text in templates.items():
        if text is None:
            continue
        with open(os.path.join(TPL, "page-%s.html" % slug), "w",
                  encoding="utf-8") as fh:
            fh.write(text)
    with open(style_path, "w", encoding="utf-8") as fh:
        fh.write(style_new)
    with open(fn_path, "w", encoding="utf-8") as fh:
        fh.write(fn_new)

    # read back and assert
    with open(style_path, encoding="utf-8") as fh:
        style_rb = fh.read()
    with open(fn_path, encoding="utf-8") as fh:
        fn_rb = fh.read()
    rb = {}
    for slug in SLUGS:
        with open(os.path.join(TPL, "page-%s.html" % slug),
                  encoding="utf-8") as fh:
            rb[slug] = fh.read()
    self_check(style_rb, fn_rb, rb)
    print("\nAPPLIED + read-back self-check PASS")


if __name__ == "__main__":
    main()
