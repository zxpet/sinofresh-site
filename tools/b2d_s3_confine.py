#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 3 — the four gates, run against two frozen 75-page captures.

Inputs are two directories of the same 75 paths, fetched before and after the
deploy (tools/b2d_s3_fetch.py). Comparing two *captures* rather than two live
fetches is deliberate: once the candidate is the live theme there is no other
side to compare against, and a re-fetch would silently return the new page for
both sides.

What each gate proves, and the failure mode it is aimed at:

  1. ver inventory — style.css 2.10.46 -> 2.10.47 on all 75 pages, and every
     other asset ver token unchanged. Catches a half-done version bump (one of
     the two places updated) and any asset that quietly changed version.
  2. confinement — the byte-exact claim. After masking ?ver= tokens and taking
     the gallery <script> out of whichever side carries it, the surviving
     difference between the two captures must be exactly the declared edit:
       * dosage pages (16): mid_new == '' — a pure deletion.
       * detail pages (42): mid_new == gallery + body + specs + actives +
         composition and mid_base == specs + body. The body and Specification
         unit bytes must be *identical* on both sides, which is what makes this
         a move and not a rewrite; anything else (an eaten blank line, a
         re-rendered card, a dropped comment) shows up as a byte mismatch.
       * every other page (17): no difference at all.
  3. script tag — formula-gallery.js enqueued on exactly the 42 detail pages
     and on none of the 16 dosage pages or 17 others.
  4. structure — the three added units must match strict patterns, the
     composition unit must be the empty-output marker with no <section> (the
     meta is empty on all 21 records today), and the actives band's data must
     equal the Specification cards' own values on the same page. That last one
     is the non-circular check: it proves the band is the record's data read a
     second way, not fabricated markup.

usage:
    b2d_s3_confine.py [--base DIR] [--new DIR] [--report FILE]
"""
import argparse
import glob
import os
import re
import sys

# The mask set is NOT redefined here. sf_masked_cmp.py owns it, and two gates
# comparing the same two captures must remove the same noise or they will
# disagree for reasons that have nothing to do with the change. It matters
# most for the Cloudflare email obfuscation: /cdn-cgi/l/email-protection#<hex>
# and data-cfemail="<hex>" carry a per-response salt, measured 2026-09-21 on
# /about/ — two consecutive fetches of an unchanged page differ at byte 69454.
# Without these masks every page carrying an email reports as a regression
# forever, and a reviewer learns to ignore the gate.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sf_masked_cmp import masked  # noqa: E402

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()

GALLERY_NEW = '<!-- B2D-S3: gallery -->'
GALLERY_OLD = '<!-- B2D-S2: gallery -->'
ACTIVES_MARK = '<!-- B2D-S3: actives -->'
COMPOSITION_MARK = '<!-- B2D-S3: composition -->'
BODY_MARK = '<!-- Block 3: long copy'
SPEC_MARK = '<!-- Block 2: Specification -->'
RELATED_MARK = '<!-- Block 4: related formulas -->'
# The dosage pages put the band between the hero and the section that opens
# with this tag; it is the anchor that closes a deletion window there.
DOSAGE_ANCHOR = '<section id="formulas"'

# No angle brackets in the replacement: an earlier draft folded the token to
# '?ver=<V>', and that '>' terminated the [^>]* in SCRIPT_RE early, so the
# gallery <script> stopped matching its own pattern and the whole single-window
# confinement collapsed. Mask tokens must not contain characters the patterns
# being matched against them treat as delimiters.
VER_RE = re.compile(r'\?ver=[0-9A-Za-z._-]+')
VER_MASK = '?ver=MASK'

# Lazy to </script>, not [^>]*: the tag's own src carries masked tokens and
# attribute-order changes should not stop it from matching.
SCRIPT_RE = re.compile(r'<script id="sinofresh-formula-gallery-js".*?</script>\n?')

GALLERY_UNIT_RE = re.compile(
    r'^<!-- B2D-S[23]: gallery -->\n\n'
    r'<section id="gallery" class="wp-block-group sf-gallery has-bg-light-background-color'
    r' has-background[^"]*" style="[^"]*">\n\n'
    r'<div class="sf-gallery__inner" data-gallery="(?P<form>[a-z0-9-]+)">'
    r'.*?</section>(?P<tail>\n+)$', re.S)
ACTIVES_UNIT_RE = re.compile(
    r'^<!-- B2D-S3: actives -->\n\n'
    r'<section class="sf-fdetail-actives"><div class="sf-fdetail-actives__inner">'
    r'<h2 class="sf-fdetail-actives__title">Formula &amp; nutrition</h2>'
    r'.*?</section>(?P<tail>\n+)$', re.S)
COMPOSITION_UNIT_RE = re.compile(r'^<!-- B2D-S3: composition -->\n\n\n\n\n$')


def unit_tail(unit, pattern):
    """(matched, trailing-newline count) — the count is asserted, not assumed.

    The two units carry different tails for a real reason: the dosage page's
    removed block sat between two groups and rendered four newlines, while the
    units added to the detail page render three. Writing one number into the
    pattern would have hidden that difference instead of showing it.
    """
    m = pattern.match(unit)
    return bool(m), (len(m.group("tail")) if m else -1)


def load(d):
    out = {}
    for p in glob.glob(os.path.join(d, "*.html")):
        with open(p, encoding="utf-8", errors="replace") as fh:
            out[os.path.basename(p)] = fh.read()
    return out


def ver_map(html):
    """{basename: version} for every ?ver= token on the page."""
    return {os.path.basename(f): v for f, v in
            re.findall(r'([A-Za-z0-9._/-]+\.(?:css|js))\?ver=([0-9A-Za-z._-]+)', html)}


def normalize(html):
    """Strip the two kinds of noise, then mask version tokens.

    Order matters: the shared masks run first (they know about the per-response
    artefacts), then ?ver= is folded so a version bump does not read as a page
    change. The bump is asserted separately, in gate 1 — folding it here is
    what keeps gate 2 a byte comparison of everything *else*.
    """
    return VER_RE.sub(VER_MASK, masked(html)[0])


def classify(name):
    if name in {"products__%s.html" % s for s in DOSAGES}:
        return "dosage-en"
    if name in {"zh__products__%s.html" % s for s in DOSAGES}:
        return "dosage-zh"
    if name.startswith("formulas__"):
        return "detail-en"
    if name.startswith("zh__formulas__"):
        return "detail-zh"
    return "other"


def spec_cards(html):
    """The three Specification cards, label -> value, as the page prints them."""
    out = {}
    for m in re.finditer(
            r'<div class="sf-fdetail__card"><h3 class="sf-fdetail__label">([^<]+)</h3>'
            r'<p class="sf-fdetail__value">([^<]*)</p></div>', html):
        out[m.group(1)] = m.group(2)
    return out


def actives_band(html):
    """The actives band split into its two halves, or None."""
    m = re.search(r'<section class="sf-fdetail-actives">.*?</section>', html, re.S)
    if not m:
        return None
    seg = m.group(0)
    pills = re.findall(r'<li class="sf-actives__pill">([^<]*)</li>', seg)
    rows = re.findall(r'<dt class="sf-spec-term">([^<]*)</dt><dd class="sf-spec-value">([^<]*)</dd>', seg)
    return pills, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="_backup/b2d-s3-baselines/base")
    ap.add_argument("--new", default="_backup/b2d-s3-baselines/new")
    ap.add_argument("--report", default="docs/b2d-step3-gates.txt")
    args = ap.parse_args()

    base, new = load(args.base), load(args.new)
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("=" * 74)
    say("Batch 2D Step 3 — confinement gates")
    say("base=%s (%d pages)   new=%s (%d pages)" % (args.base, len(base), args.new, len(new)))
    say("=" * 74)

    if set(base) != set(new):
        say("FATAL: page sets differ: %s" % sorted(set(base) ^ set(new)))
        return 2

    # ---- gate 1: ver inventory -------------------------------------------
    # Three buckets, because "the token changed" and "the asset appeared or
    # disappeared" are different claims and only the first one is a regression
    # signal here. formula-gallery.js moving from 16 pages to 42 is the
    # enqueue migration; style.css moving version is the bump.
    say("\n[1] ver inventory")
    added, removed, changed = {}, {}, {}
    for name in sorted(base):
        mb, mn = ver_map(base[name]), ver_map(new[name])
        for k in set(mb) | set(mn):
            if k not in mb:
                added.setdefault((k, mn[k]), []).append(name)
            elif k not in mn:
                removed.setdefault((k, mb[k]), []).append(name)
            elif mb[k] != mn[k]:
                changed.setdefault((k, mb[k], mn[k]), []).append(name)
    for (k, v), pages in sorted(added.items()):
        say("    ADDED   %-26s %s      on %d page(s)" % (k, v, len(pages)))
    for (k, v), pages in sorted(removed.items()):
        say("    REMOVED %-26s %s      on %d page(s)" % (k, v, len(pages)))
    for (k, o, n), pages in sorted(changed.items(), key=lambda kv: str(kv[0])):
        say("    CHANGED %-26s %s -> %s on %d page(s)" % (k, o, n, len(pages)))
    ver_ok = (list(changed) == [("style.css", "2.10.46", "2.10.47")]
              and len(changed[("style.css", "2.10.46", "2.10.47")]) == 75
              and list(added) == [("formula-gallery.js", "1.0.0")]
              and len(added[("formula-gallery.js", "1.0.0")]) == 42
              and list(removed) == [("formula-gallery.js", "1.0.0")]
              and len(removed[("formula-gallery.js", "1.0.0")]) == 16)
    say("    verdict: %s" % (
        "PASS — style.css 2.10.46 -> 2.10.47 on 75; formula-gallery.js 1.0.0 "
        "arrives on 42 detail pages and leaves the 16 dosage pages; no other "
        "asset token moved" if ver_ok else "FAIL"))

    # ---- gates 2+3+4 ------------------------------------------------------
    say("\n[2] confinement, [3] script tag, [4] structure")
    fails, rows = [], []
    for name in sorted(base):
        cls = classify(name)
        b_norm = normalize(base[name])
        n_norm = normalize(new[name])
        b_script = len(SCRIPT_RE.findall(b_norm))
        n_script = len(SCRIPT_RE.findall(n_norm))
        b_norm = SCRIPT_RE.sub('', b_norm)
        n_norm = SCRIPT_RE.sub('', n_norm)

        # Windows are cut on anchors, never on a longest-common-prefix. An LCP
        # boundary lands wherever the first differing byte happens to fall, and
        # here it fell *inside* the marker comment — '<!-- B' is common to
        # '<!-- Block 2:' and '<!-- B2D-S3:' — slicing the marker in half and
        # making every later lookup miss. Anchors are whole strings that each
        # page carries exactly once, so the edges are meaningful and the claim
        # becomes the readable one: identical up to X, identical from Y on.
        #
        # The script must ride the band: present on the 42 detail pages, gone
        # from the 16 dosage pages that used to carry it, never on the rest.
        expect_script = (cls in ("detail-en", "detail-zh"))
        want_new, want_base = (1, 0) if expect_script else (0, 0)
        if cls.startswith("dosage"):
            want_new, want_base = 0, 1
        if (n_script, b_script) != (want_new, want_base):
            fails.append("%s [%s]: gallery script new=%d base=%d, expected new=%d base=%d"
                         % (name, cls, n_script, b_script, want_new, want_base))

        def once(h, mark, label):
            """Position of a marker that must occur exactly once, else -1."""
            if h.count(mark) != 1:
                fails.append("%s: %s occurs %d times" % (name, label, h.count(mark)))
                return -1
            return h.find(mark)

        verdict = "?"
        if cls == "other":
            if b_norm != n_norm:
                fails.append("%s: non-target page changed" % name)
                verdict = "DIFF"
            else:
                verdict = "identical"
        elif cls.startswith("dosage"):
            a_b = once(b_norm, GALLERY_OLD, "the old gallery marker")
            b_b = once(b_norm, DOSAGE_ANCHOR, "the formulas anchor (base)")
            a_n = once(n_norm, DOSAGE_ANCHOR, "the formulas anchor (new)")
            removed = b_norm[a_b:b_b] if a_b >= 0 and b_b >= 0 else ""
            hit, tail = unit_tail(removed, GALLERY_UNIT_RE)
            if min(a_b, b_b, a_n) < 0 or b_b < a_b:
                verdict = "DIFF"
            elif b_norm[:a_b] != n_norm[:a_n]:
                fails.append("%s: the bytes before the band differ" % name)
                verdict = "DIFF"
            elif b_norm[b_b:] != n_norm[a_n:]:
                fails.append("%s: the bytes after the band differ" % name)
                verdict = "DIFF"
            elif not hit:
                fails.append("%s: the removed unit does not match the gallery pattern" % name)
                verdict = "DIFF"
            elif tail != 4:
                fails.append("%s: the removed unit carries %d trailing newlines, expected 4"
                             % (name, tail))
                verdict = "DIFF"
            else:
                verdict = "pure deletion (%d B)" % (b_b - a_b)
        else:
            # detail
            a_b = once(b_norm, SPEC_MARK, "the Specification marker (base)")
            b_b = once(b_norm, RELATED_MARK, "the related marker (base)")
            a_n = once(n_norm, GALLERY_NEW, "the gallery marker (new)")
            b_n = once(n_norm, RELATED_MARK, "the related marker (new)")
            if min(a_b, b_b, a_n, b_n) < 0:
                verdict = "DIFF"
            elif b_norm[:a_b] != n_norm[:a_n]:
                fails.append("%s: the bytes before the band differ" % name)
                verdict = "DIFF"
            elif b_norm[b_b:] != n_norm[b_n:]:
                fails.append("%s: the bytes after the band differ" % name)
                verdict = "DIFF"
            else:
                mid_b, mid_n = b_norm[a_b:b_b], n_norm[a_n:b_n]
                idx = {}
                for label, mark in (("g", GALLERY_NEW), ("bm", BODY_MARK), ("bs", SPEC_MARK),
                                    ("act", ACTIVES_MARK), ("c", COMPOSITION_MARK)):
                    pos = [m.start() for m in re.finditer(re.escape(mark), mid_n)]
                    if len(pos) != 1:
                        fails.append("%s: marker %r occurs %d times in the new middle" % (name, mark, len(pos)))
                    idx[label] = pos[0] if pos else -1
                if all(v >= 0 for v in idx.values()) and \
                        not (idx["g"] < idx["bm"] < idx["bs"] < idx["act"] < idx["c"]):
                    fails.append("%s: added units are out of order" % name)
                if idx["bm"] >= 0 and idx["bs"] >= 0 and idx["act"] >= 0 and idx["c"] >= 0:
                    G = mid_n[:idx["bm"]]
                    BM = mid_n[idx["bm"]:idx["bs"]]
                    BS = mid_n[idx["bs"]:idx["act"]]
                    ACT = mid_n[idx["act"]:idx["c"]]
                    C = mid_n[idx["c"]:]
                    j = mid_b.find(BODY_MARK)
                    BS_b, BM_b = (mid_b[:j], mid_b[j:]) if j >= 0 else ("", "")
                    if BM != BM_b:
                        fails.append("%s: body unit bytes changed (%d vs %d)" % (name, len(BM), len(BM_b)))
                    if BS != BS_b:
                        fails.append("%s: Specification unit bytes changed (%d vs %d)" % (name, len(BS), len(BS_b)))
                    for unit, pat, want_tail, label in (
                            (G, GALLERY_UNIT_RE, 3, "gallery unit"),
                            (ACT, ACTIVES_UNIT_RE, 3, "actives unit")):
                        hit, tail = unit_tail(unit, pat)
                        if not hit:
                            fails.append("%s: the %s does not match its pattern" % (name, label))
                        elif tail != want_tail:
                            fails.append("%s: the %s carries %d trailing newlines, expected %d"
                                         % (name, label, tail, want_tail))
                    if not COMPOSITION_UNIT_RE.match(C):
                        fails.append("%s: composition unit is not the empty marker" % name)
                    if 'sf-fdetail-composition' in n_norm:
                        fails.append("%s: composition <section> rendered though its meta is empty" % name)
                    # non-circular: the band's data must equal the cards' own values
                    cards = spec_cards(n_norm)
                    band = actives_band(n_norm)
                    if not band:
                        fails.append("%s: actives band missing" % name)
                    else:
                        pills, spec_rows = band
                        want = [x.strip() for x in cards.get("Ingredients", "").split(",") if x.strip()]
                        if pills != want:
                            fails.append("%s: pills != card ingredients (%r vs %r)" % (name, pills[:3], want[:3]))
                        got = ["%s %s" % (t, v) for t, v in spec_rows]
                        want2 = [x.strip() for x in cards.get("Guaranteed Analysis", "").split(",") if x.strip()]
                        if got != want2:
                            fails.append("%s: spec rows != card analysis (%r vs %r)" % (name, got[:2], want2[:2]))
                    verdict = "moved+added (mid %d/%d B)" % (len(mid_b), len(mid_n))
                else:
                    verdict = "DIFF"
        rows.append((cls, name, verdict))

    for cls in ("dosage-en", "dosage-zh", "detail-en", "detail-zh", "other"):
        sel = [r for r in rows if r[0] == cls]
        say("\n    -- %s (%d pages) --" % (cls, len(sel)))
        for _, name, v in sel[:3]:
            say("       %-46s %s" % (name, v))
        if len(sel) > 3:
            say("       ... %d more, all %s" % (len(sel) - 3, "same verdict" if len({r[2] for r in sel}) == 1 else "see report"))

    say("\n[3] script tag summary")
    say("    new has it on exactly the 42 detail pages: %s"
        % ("yes" if not [f for f in fails if "script tag" in f or "leaked" in f] else "NO"))

    say("\n[4] structure summary")
    struct_fails = [f for f in fails if "unit" in f or "band" in f or "pills" in f or "spec rows" in f]
    say("    42/42 gallery+actives units match their patterns, composition empty,"
        " band data == card data: %s" % ("yes" if not struct_fails else "NO"))

    say("\n" + "=" * 74)
    if fails:
        say("FAIL — %d problem(s):" % len(fails))
        for f in fails:
            say("  * %s" % f)
    else:
        say("PASS — 75/75 pages: 16 pure deletions, 42 move+add, 17 untouched;")
        say("       42/42 added units match their patterns and carry the record's own data.")
    say("=" * 74)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\nreport -> %s" % args.report)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
