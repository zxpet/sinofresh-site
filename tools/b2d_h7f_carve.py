#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7f — carve the inquiry basket out of style.css.

Why a tool and not ten Edit calls: the deletion is not one contiguous block.
The basket's CSS shares four rule *headers* with the certificate dialog and the
inquiry dialog (one backdrop, one fade, one z-index stack, one scroll lock, one
reduced-motion block), so the honest description of the change is "delete these
ranges, keep those selector lines", not "delete section 45". Ten hand edits
against a 291 KB file is ten chances to delete a shared selector; this script
asserts the first and last line of every range before it cuts, so a stale line
number fails loudly instead of silently eating the wrong rule.

    python3 tools/b2d_h7f_carve.py --dry-run
    python3 tools/b2d_h7f_carve.py --apply

Line numbers are the ones measured on the pre-carve file (2.10.66). Every range
is verified by its boundary lines; nothing is deleted on a line number alone.
"""

import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(os.path.dirname(HERE), "sinofresh-theme", "style.css")

# --- ranges to DELETE, 1-based inclusive, with boundary assertions ----------
# (start, end, first_line_expected, last_line_expected, label)
CUTS = [
    (6330, 6367, "",
     "",
     "blank + section 46 (basket pre-fill notice)"),
    (6323, 6324, "\t.sf-basket-overlay,",
     "\t.sf-basket-drawer,",
     "reduced-motion shared block: the two basket selectors"),
    (6315, 6322, "\t.sf-basket-btn,",
     "",
     "reduced-motion block that was basket-only"),
    (6290, 6312, "",
     "}",
     "blank + 'Responsive' divider + the 480px basket media block"),
    (6285, 6285, "body.sf-basket-lock,",
     "body.sf-basket-lock,",
     "scroll-lock: the basket selector (cert + inquiry stay)"),
    (6032, 6282, "",
     "}",
     "blank + the whole .sf-basket-drawer rule block"),
    (6027, 6027, ".sf-basket-overlay[hidden],",
     ".sf-basket-overlay[hidden],",
     "shared [hidden] rule: the basket selector"),
    (6021, 6021, ".sf-basket-overlay.is-open,",
     ".sf-basket-overlay.is-open,",
     "shared .is-open rule: the basket selector"),
    (6010, 6010, ".sf-basket-overlay,",
     ".sf-basket-overlay,",
     "shared backdrop rule: the basket selector"),
    (5960, 6005, "",
     "",
     "blank + .sf-basket-btn / :hover / __badge / __badge[hidden]"),
]

# --- ranges to REPLACE, 1-based inclusive, with boundary assertions --------
# (start, end, first_line_expected, last_line_expected, new_lines, label)
REPLACEMENTS = [
    (6006, 6009,
     "/* --- Overlay + drawer ----------------------------------------------------- */",
     "   three components cannot drift. */",
     ["/* --- Overlay: certificate dialog + inquiry dialog ------------------------- */",
      "/* Shared by the certificate dialog (section 50) and the inquiry dialog (batch",
      "   H4): one backdrop, one fade, one z-index stack — the two cannot drift. */"],
     "'Overlay + drawer' divider + the three-way shared comment"),
    (5950, 5956,
     "/* === 45. Inquiry basket: header bag + badge + slide-in drawer ============",
     "/* --- Header bag button --------------------------------------------------- */",
     ["/* === 45. Header CTA alignment (the inquiry basket's former section) =======",
      "   The bag button that used to sit inside .sf-header__cta was removed in batch",
      "   H7f, with its drawer, its script and this section's rules. The container",
      "   stays because the Get a Quote button lives in it, and this rule is what",
      "   keeps that button centred against the taller logo row. */"],
     "section 45 banner + intro (the rule below it is KEPT)"),
]

# --- text-anchor rewrites (must be unique) --------------------------------
REWRITES = [
    ("/* Scroll lock while the drawer is open. */",
     "/* Scroll lock while a dialog is open. */",
     "scroll-lock comment"),
    ("\t/* Hide only the Get a Quote button on phones (it wrapped onto its own\n"
     "\t   40px row); the inquiry basket icon inside the same container stays. */",
     "\t/* Hide the Get a Quote button on phones (it wrapped onto its own 40px\n"
     "\t   row); the hero already carries the same action. The basket icon that\n"
     "\t   used to sit beside it went in batch H7f. */",
     "section 27b: '...the inquiry basket icon ... stays'"),
    ("\t/* Hug the basket: under space-between the auto margin soaks up all free\n"
     "\t   space, so the hamburger stops floating mid-bar (24px column gap minus\n"
     "\t   the open button's -10px right margin = a 14px visual gap to the bag).\n"
     "\t   Child combinator is required — the overlay's inner <ul> ALSO carries\n"
     "\t   .wp-block-navigation, and an auto margin there shoves the whole open\n"
     "\t   menu column to the right edge. */",
     "\t/* Hug the right edge: under space-between the auto margin soaks up all\n"
     "\t   free space, so the hamburger stops floating mid-bar. (Before batch H7f\n"
     "\t   it hugged the basket button that sat to its right.) Child combinator is\n"
     "\t   required — the overlay's inner <ul> ALSO carries .wp-block-navigation,\n"
     "\t   and an auto margin there shoves the whole open menu column to the right\n"
     "\t   edge. */",
     "section 27b: 'Hug the basket' comment"),
    # --- the four stale references the 'basket' sweep below caught on the
    #     first run: prose in the certificate dialog (section 50) and the
    #     inquiry dialog that explains their z-index step in terms of a
    #     component that no longer exists.
    ("   are the inquiry basket's — section 45 carries both class names on those\n"
     "   rules, so there is one definition and no drift. A centred dialog needs the",
     "   are shared with the inquiry dialog — section 45 carries both class names on\n"
     "   those rules, so there is one definition and no drift. A centred dialog needs\n"
     "   the",
     "section 50 header: '...are the inquiry basket's...'"),
    ("\t/* The backdrop rules at section 45 hand out 10000 and the basket drawer\n"
     "\t   adds 10001 on top of them. The dialog is the active layer whenever it\n"
     "\t   is up, so it takes its own step above the whole basket stack instead of\n"
     "\t   relying on document order to break the tie. */",
     "\t/* The backdrop rules at section 45 hand out 10000. The dialog is the\n"
     "\t   active layer whenever it is up, so it takes its own step above that\n"
     "\t   stack instead of relying on document order to break the tie. */",
     "section 50 panel: the 10010 z-index rationale"),
    ("   The dialog follows the certificate dialog's shape rather than the basket\n"
     "   drawer's: the outer element is the backdrop AND the centring box (flex,\n"
     "   inset 0), the panel inside it is what fades and rises. One backdrop\n"
     "   definition, three components. */",
     "   The dialog follows the certificate dialog's shape rather than the basket\n"
     "   drawer's (deleted in batch H7f): the outer element is the backdrop AND the\n"
     "   centring box (flex, inset 0), the panel inside it is what fades and rises.\n"
     "   One backdrop definition, two components. */",
     "inquiry dialog header: '...rather than the basket drawer's...'"),
    ("\t/* One generous step above the basket stack (10000/10001): the dialog is\n"
     "\t   the active layer whenever it is up. */",
     "\t/* One generous step above the backdrop's 10000: the dialog is the active\n"
     "\t   layer whenever it is up. */",
     "inquiry dialog panel: the 10010 z-index rationale"),
]

TOKEN_OLD = "Version: 2.10.66"
TOKEN_NEW = "Version: 2.10.67"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run or --apply")

    src = io.open(CSS, encoding="utf-8").read()
    before_bytes = len(src.encode("utf-8"))
    lines = src.split("\n")
    n = len(lines)
    print("style.css: %d lines, %d bytes" % (n, before_bytes))

    # 1. verify every range, build the delete set + replacement map
    delete = set()
    replace = {}
    skip = set()
    for (s, e, f_exp, l_exp, label) in CUTS:
        assert 1 <= s <= e <= n, (label, s, e, n)
        assert lines[s - 1] == f_exp, (label, "first", s, repr(lines[s - 1]), repr(f_exp))
        assert lines[e - 1] == l_exp, (label, "last", e, repr(lines[e - 1]), repr(l_exp))
        for i in range(s, e + 1):
            assert i not in delete, ("overlap", label, i)
            assert i not in replace, ("overlap", label, i)
            delete.add(i)
        print("  CUT  %5d-%-5d %3d lines  %s" % (s, e, e - s + 1, label))

    for (s, e, f_exp, l_exp, new, label) in REPLACEMENTS:
        assert 1 <= s <= e <= n, (label, s, e, n)
        assert lines[s - 1] == f_exp, (label, "first", s, repr(lines[s - 1]), repr(f_exp))
        assert lines[e - 1] == l_exp, (label, "last", e, repr(lines[e - 1]), repr(l_exp))
        for i in range(s, e + 1):
            assert i not in delete, ("overlap", label, i)
            assert i not in replace, ("overlap", label, i)
            assert i not in skip, ("overlap", label, i)
        # the replacement text goes in ONCE, at the range's first line; the rest
        # of the range is dropped. (Keying every line in the range is the bug
        # that printed section 45's banner seven times on the first run.)
        replace[s] = (label, new)
        for i in range(s + 1, e + 1):
            skip.add(i)
        print("  REPL %5d-%-5d %3d -> %d lines  %s" % (s, e, e - s + 1, len(new), label))

    # 2. every shared selector we keep must still be there exactly once
    keep = ["\t.sf-certmodal,", "\t.sf-inquiry-modal {",
            ".sf-certmodal.is-open,", ".sf-inquiry-modal.is-open {",
            ".sf-certmodal[hidden],", ".sf-inquiry-modal[hidden] {",
            "body.sf-certmodal-lock,", "body.sf-inquiry-lock {",
            "\t.sf-certmodal,", "\t.sf-certmodal__panel {",
            ".sf-header .sf-header__cta {", "\talign-items: center;"]
    for k in keep:
        assert lines.count(k) >= 1, ("keep-missing", k)
    assert src.count(".sf-certmodal,") == 2, src.count(".sf-certmodal,")

    # 3. assemble
    out = []
    for i in range(1, n + 1):
        if i in replace:
            out.extend(replace[i][1])
        elif i in delete or i in skip:
            continue
        else:
            out.append(lines[i - 1])
    text = "\n".join(out)

    # 3b. a replacement's text must land exactly once — the guard for the
    #     seven-copies-of-section-45 bug.
    for (s, e, f_exp, l_exp, new, label) in REPLACEMENTS:
        for nl in new:
            c = text.count(nl + "\n")
            assert c == 1, ("replacement not applied exactly once", label, c, nl)

    # 4. text-anchor rewrites
    for old, new, label in REWRITES:
        c = text.count(old)
        assert c == 1, (label, c)
        text = text.replace(old, new)
        print("  RW   %s" % label)

    # 5. version token
    c = text.count(TOKEN_OLD)
    assert c == 1, (TOKEN_OLD, c)
    text = text.replace(TOKEN_OLD, TOKEN_NEW)
    print("  TOKEN %s -> %s" % (TOKEN_OLD, TOKEN_NEW))

    # 6. nothing basket-ish may survive, and the kept spine must be intact
    leftovers = [l for l in text.split("\n") if "sf-basket" in l]
    assert not leftovers, leftovers
    for must in ["\t.sf-certmodal,", "\t.sf-inquiry-modal {",
                 "body.sf-certmodal-lock,", "body.sf-inquiry-lock {",
                 ".sf-header .sf-header__cta {",
                 "/* === 47. Contact page: inquiry band split",
                 "/* === 45. Header CTA alignment",
                 "/* === 50. Certificate request modal"]:
        assert must in text, ("lost", must)
    for gone in ["sf-basket", "Inquiry basket", "basket.js", "2.10.66"]:
        assert gone not in text, ("still-there", gone)
    # every surviving mention of the word must be prose. A selector would be a
    # rule for an element that no template emits any more.
    prose = [l for l in text.split("\n") if "basket" in l.lower()]
    for l in prose:
        s = l.strip()
        assert not s.startswith((".", "#", ":", ",", "}")), ("selector-ish", l)
        assert "{" not in l and "}" not in l, ("selector-ish", l)
        assert s.startswith(("/*", "*")) or not s.endswith(";"), ("declaration", l)
    print("  prose mentions of 'basket' kept: %d" % len(prose))

    after_bytes = len(text.encode("utf-8"))
    print("\nresult: %d lines, %d bytes (%+d bytes)"
          % (len(text.split("\n")), after_bytes, after_bytes - before_bytes))

    if args.apply:
        io.open(CSS, "w", encoding="utf-8").write(text)
        print("WROTE %s" % CSS)
    else:
        print("dry run — nothing written")


if __name__ == "__main__":
    main()
