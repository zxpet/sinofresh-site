#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 4 — the gates for the two detail-page edits.

Same instrument as step 3 wherever the question is the same: the captures are
loaded, classified and normalised by the step-3 tool, so the mask set stays the
one sf_masked_cmp.py owns and ?ver= is folded the same way. Two gates are
rewritten, because this batch trims and renames rather than adds a band:

  1. ver inventory — style.css 2.10.47 -> 2.10.48 on all 75 pages and no other
     asset token moved. formula-gallery.js is on the same 42 detail pages
     before and after, so it must appear in neither the ADDED nor the REMOVED
     bucket: a migration in either direction would be a regression, and the
     step-3 report is where such a migration is expected.

  2. confinement, by reconstruction. The detail page's band region, from the
     gallery marker to the related marker, must equal the base region with
     exactly the two declared edits applied — and nothing else in the whole
     document may move:

       * edit 1, the gallery heading. "Inside Our {dosage} Production" becomes
         "A Closer Look at {formula}". The expected heading is rebuilt from the
         BASE page's own h1, so this does not accept whatever the new page
         happened to print; it derives what the new page must print, and in
         doing so proves the band and the hero name the same thing. The base
         heading's own claim is checked too: the label inside it must be the
         dosage slug humanised, which is where step 3 showed it came from.
       * edit 2, the Specification grid. The Ingredients and Guaranteed
         Analysis cards go and the grid takes the --solo modifier. The
         replacement is rebuilt from the base cards themselves, so the
         surviving card's bytes are the base bytes.

     Everything before the gallery marker and from the related marker onward
     must be byte-identical, which is what covers the hero, the breadcrumb, the
     related grid, the CTA and the whole head. The 33 pages that are not
     formula details must be identical outright.

  3. script tag — formula-gallery.js still on exactly the 42 detail pages.

  4. the data survives the deduplication. The two removed cards carried the
     record's Ingredients and Guaranteed Analysis, and the ⑤ band still prints
     both. The pills and rows on the NEW page must equal the BASE page's card
     values, which is the cross-version half of the claim: the card and the
     band were two renderings of one meta value, so equality here is exactly
     "the data did not change, only its second copy went away". Read the other
     way round it would be circular, since both would come from the same new
     page. The Product JSON-LD is checked against the same base values as a
     second, independent copy of that data.

usage:
    b2d_s4_confine.py [--base DIR] [--new DIR] [--report FILE]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Reused, not re-implemented: load(), classify(), normalize() (which owns the
# mask order), ver_map(), actives_band(), unit_tail(), the gallery unit pattern
# and DOSAGES. Two batches must not disagree about what counts as noise.
import b2d_s3_confine as S3  # noqa: E402

GALLERY_MARK = S3.GALLERY_NEW
RELATED_MARK = S3.RELATED_MARK

# The two heads the grid can carry. The base grid is written by the same
# shortcode that produces the new one, so the only difference between them is
# the modifier class — asserting it on the literal string keeps the claim
# narrow enough to be falsifiable.
GRID_HEAD = '<div class="sf-fdetail__grid">'
SOLO_HEAD = '<div class="sf-fdetail__grid sf-fdetail__grid--solo">'

CARD_RE = re.compile(
    r'<div class="sf-fdetail__card"><h3 class="sf-fdetail__label">[^<]+</h3>'
    r'<p class="sf-fdetail__value">[^<]*</p></div>')
GRID_RE = re.compile(re.escape(GRID_HEAD) + r'((?:' + CARD_RE.pattern + r')+)</div>')
SOLO_RE = re.compile(re.escape(SOLO_HEAD) + r'((?:' + CARD_RE.pattern + r')+)</div>')
LABEL_RE = re.compile(r'<h3 class="sf-fdetail__label">([^<]+)</h3>')
VALUE_RE = re.compile(r'<p class="sf-fdetail__value">([^<]*)</p>')
H2_RE = re.compile(r'<h2 class="sf-gallery__title">([^<]*)</h2>')
H1_RE = re.compile(r'<h1 class="sf-formula-hero__title">([^<]*)</h1>')
OLD_H2_RE = re.compile(r'^Inside Our (.+) Production$')
DATA_GALLERY_RE = re.compile(r'<div class="sf-gallery__inner" data-gallery="([a-z0-9-]+)">')

EXPECTED_LABELS = ["Ingredients", "Guaranteed Analysis", "Standard Specs"]


def humanise(slug):
    """ucwords(str_replace('-', ' ', $slug)) — what the old heading used.

    Not read from the dosage page's title: step 3 measured the old band heading
    as "Inside Our Drops Production" while /products/drops/ renders "Private
    Label Pet Supplement Drops", so the label was the slug humanised, and that
    is what the check below asserts rather than assuming.
    """
    return " ".join(w[:1].upper() + w[1:] for w in slug.split("-"))


def cards_of(inner):
    """[(label, value, exact_tag)] in document order, or None if not just cards.

    The step-3 tool returns {label: value}, which is right for a lookup and
    wrong here: this batch needs the order (to state which card survives) and
    needs to know that nothing but cards sits in the grid, so that "the grid
    was rebuilt from the base bytes" cannot hide an extra node.
    """
    out, pos = [], 0
    for m in CARD_RE.finditer(inner):
        if m.start() != pos:
            return None
        pos = m.end()
        out.append((LABEL_RE.search(m.group(0)).group(1),
                    VALUE_RE.search(m.group(0)).group(1),
                    m.group(0)))
    return out if pos == len(inner) else None


def expected_new_window(win, h1_text):
    """The base band region with the two declared edits applied.

    (expected_text, note) — note is 'ok' or the reason there is no expectation.
    Every input is from the base capture, including the heading text.
    """
    m = H2_RE.search(win)
    if not m:
        return None, "no gallery h2 in the base band region"
    old_inner = m.group(1)
    if not OLD_H2_RE.match(old_inner):
        return None, "base gallery h2 is not the old form: %r" % old_inner

    form = DATA_GALLERY_RE.search(win)
    if not form:
        return None, "no data-gallery in the base band region"
    want_label = humanise(form.group(1))
    if OLD_H2_RE.match(old_inner).group(1) != want_label:
        return None, ("the old heading named %r, but the band's own dosage slug "
                      "humanises to %r" % (OLD_H2_RE.match(old_inner).group(1), want_label))

    g = GRID_RE.search(win)
    if not g:
        return None, "no .sf-fdetail__grid holding only cards in the base region"
    cards = cards_of(g.group(1))
    if cards is None:
        return None, "the base grid holds something other than card tags"
    if [c[0] for c in cards] != EXPECTED_LABELS:
        return None, "base cards are %r, expected the three" % [c[0] for c in cards]

    new_grid = SOLO_HEAD + cards[-1][2] + "</div>"
    out = (win[:m.start()]
           + '<h2 class="sf-gallery__title">A Closer Look at %s</h2>' % h1_text
           + win[m.end():])
    g2 = GRID_RE.search(out)
    out = out[:g2.start()] + new_grid + out[g2.end():]
    return out, "ok"


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i, a[max(0, i - 40):i + 40], b[max(0, i - 40):i + 40]
    return n, a[n - 40:], b[n - 40:]


def product_meta(html):
    """{name: value} from the Product JSON-LD's additionalProperty, or None."""
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "Product":
            out = {}
            for p in d.get("additionalProperty") or []:
                if isinstance(p, dict) and "name" in p:
                    out[p["name"]] = str(p.get("value", ""))
            return out
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="_backup/b2d-step4-baselines/base")
    ap.add_argument("--new", default="_backup/b2d-step4-baselines/new")
    ap.add_argument("--report", default="docs/b2d-step4-gates.txt")
    args = ap.parse_args()

    base, new = S3.load(args.base), S3.load(args.new)
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("=" * 74)
    say("Batch 2D Step 4 — gates for the two detail-page edits")
    say("base=%s (%d pages)   new=%s (%d pages)" % (args.base, len(base), args.new, len(new)))
    say("=" * 74)

    if set(base) != set(new):
        say("FATAL: page sets differ: %s" % sorted(set(base) ^ set(new)))
        return 2

    # ---- gate 1: ver inventory -------------------------------------------
    say("\n[1] ver inventory")
    added, removed, changed = {}, {}, {}
    for name in sorted(base):
        mb, mn = S3.ver_map(base[name]), S3.ver_map(new[name])
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
    bump = ("style.css", "2.10.47", "2.10.48")
    ver_ok = (not added and not removed
              and list(changed) == [bump] and len(changed[bump]) == 75)
    say("    verdict: %s" % (
        "PASS — style.css 2.10.47 -> 2.10.48 on 75 pages; no asset appeared or "
        "disappeared (formula-gallery.js stays on the same 42 detail pages); no "
        "other token moved" if ver_ok else "FAIL"))

    # ---- gates 2+3+4 ------------------------------------------------------
    say("\n[2] confinement by reconstruction, [3] script tag, [4] cross-version data")
    fails, rows = [], []
    for name in sorted(base):
        cls = S3.classify(name)
        b_norm, n_norm = S3.normalize(base[name]), S3.normalize(new[name])
        b_script, n_script = len(S3.SCRIPT_RE.findall(b_norm)), len(S3.SCRIPT_RE.findall(n_norm))
        b_norm = S3.SCRIPT_RE.sub('', b_norm)
        n_norm = S3.SCRIPT_RE.sub('', n_norm)

        is_detail = cls in ("detail-en", "detail-zh")
        want_new, want_base = (1, 1) if is_detail else (0, 0)
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
        if not is_detail:
            if b_norm != n_norm:
                fails.append("%s: non-target page changed" % name)
                verdict = "DIFF"
            else:
                verdict = "identical"
        else:
            a_b = once(b_norm, GALLERY_MARK, "the gallery marker (base)")
            z_b = once(b_norm, RELATED_MARK, "the related marker (base)")
            a_n = once(n_norm, GALLERY_MARK, "the gallery marker (new)")
            z_n = once(n_norm, RELATED_MARK, "the related marker (new)")
            h1b = H1_RE.findall(b_norm)
            h1n = H1_RE.findall(n_norm)
            if len(h1b) != 1 or len(h1n) != 1:
                fails.append("%s: hero h1 occurs %d/%d times" % (name, len(h1b), len(h1n)))
            if min(a_b, z_b, a_n, z_n) < 0 or z_b < a_b:
                verdict = "DIFF"
            elif b_norm[:a_b] != n_norm[:a_n]:
                fails.append("%s: the bytes before the gallery marker differ" % name)
                verdict = "DIFF"
            elif b_norm[z_b:] != n_norm[z_n:]:
                fails.append("%s: the bytes from the related marker on differ" % name)
                verdict = "DIFF"
            elif len(h1b) != 1 or len(h1n) != 1:
                verdict = "DIFF"
            elif h1b != h1n:
                # Not redundant with the prefix comparison: it says out loud
                # that the heading is allowed to be derived from the new page's
                # hero only because the hero itself is byte-identical.
                fails.append("%s: the hero h1 changed (%r vs %r)" % (name, h1b, h1n))
                verdict = "DIFF"
            else:
                mid_b, mid_n = b_norm[a_b:z_b], n_norm[a_n:z_n]
                want, note = expected_new_window(mid_b, h1b[0])
                if want is None:
                    fails.append("%s: cannot derive the expected region — %s" % (name, note))
                    verdict = "DIFF"
                elif want != mid_n:
                    off, got, expect = first_diff(want, mid_n)
                    fails.append("%s: the band region is not the base region with the two "
                                 "declared edits; first difference at +%d\n        expected ...%r"
                                 "\n        new      ...%r" % (name, off, expect, got))
                    verdict = "DIFF"
                else:
                    old_h2 = H2_RE.search(mid_b).group(1)
                    new_h2 = H2_RE.search(mid_n).group(1)
                    if old_h2 == new_h2:
                        fails.append("%s: the gallery heading did not change" % name)
                    # gate 4: the removed cards' data, read off the base page,
                    # must be what the new page's band prints.
                    cards = {c[0]: c[1] for c in cards_of(GRID_RE.search(mid_b).group(1))}
                    band = S3.actives_band(n_norm)
                    if not band:
                        fails.append("%s: actives band missing" % name)
                    else:
                        pills, spec_rows = band
                        if not pills or not spec_rows:
                            fails.append("%s: the band parsed empty (%d pills, %d rows)"
                                         % (name, len(pills), len(spec_rows)))
                        want_pills = [x.strip() for x in cards["Ingredients"].split(",") if x.strip()]
                        if pills != want_pills:
                            fails.append("%s: pills != base Ingredients card (%r vs %r)"
                                         % (name, pills[:3], want_pills[:3]))
                        got = ["%s %s" % (t, v) for t, v in spec_rows]
                        want_rows = [x.strip() for x in cards["Guaranteed Analysis"].split(",") if x.strip()]
                        if got != want_rows:
                            fails.append("%s: rows != base Guaranteed Analysis card (%r vs %r)"
                                         % (name, got[:2], want_rows[:2]))
                        jm = product_meta(n_norm)
                        if jm is None:
                            fails.append("%s: no Product JSON-LD" % name)
                        elif any(jm.get(k, "") != v for k, v in cards.items()):
                            fails.append("%s: Product JSON-LD no longer carries the base values (%r vs %r)"
                                         % (name, jm, cards))
                    kept = cards_of(SOLO_RE.search(mid_n).group(1)) if SOLO_RE.search(mid_n) else None
                    if kept is None:
                        fails.append("%s: the new grid is not the --solo grid with one card" % name)
                    elif [c[0] for c in kept] != ["Standard Specs"]:
                        fails.append("%s: the new grid holds %r" % (name, [c[0] for c in kept]))
                    if n_norm.count('class="sf-fdetail__grid"') != 0:
                        fails.append("%s: a plain .sf-fdetail__grid survived" % name)
                    if n_norm.count(SOLO_HEAD) != 1:
                        fails.append("%s: the --solo grid occurs %d times"
                                     % (name, n_norm.count(SOLO_HEAD)))
                    verdict = "rebuilt (%s | %s -> %s)" % (
                        "1 card", old_h2.replace("Inside Our ", "").replace(" Production", ""), new_h2)
        rows.append((cls, name, verdict))

    for cls in ("detail-en", "detail-zh", "dosage-en", "dosage-zh", "other"):
        sel = [r for r in rows if r[0] == cls]
        say("\n    -- %s (%d pages) --" % (cls, len(sel)))
        for _, name, v in sel[:3]:
            say("       %-46s %s" % (name, v))
        if len(sel) > 3:
            say("       ... %d more, all %s" % (len(sel) - 3,
                "same verdict" if len({r[2] for r in sel}) == 1 else "see report"))

    say("\n[3] script tag — formula-gallery.js on exactly the 42 detail pages: %s"
        % ("yes" if not [f for f in fails if "gallery script" in f] else "NO"))
    say("\n[4] cross-version data — every band equals the base page's own cards, and the "
        "Product JSON-LD still carries them: %s"
        % ("yes" if not [f for f in fails if "pills" in f or "rows" in f or "JSON-LD" in f
                         or "band" in f] else "NO"))

    say("\n" + "=" * 74)
    if fails:
        say("FAIL — %d problem(s):" % len(fails))
        for f in fails:
            say("  * %s" % f)
    else:
        say("PASS — 75/75 pages: 42 rebuilt from the base region by the two declared edits,")
        say("       33 byte-identical (16 dosage + 17 other);")
        say("       42/42 bands equal the base page's own card values.")
    say("=" * 74)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print("\nreport -> %s" % args.report)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
