#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step 5 — idempotent rewriter for the
"Core facts + Direct Answer" band on the eight dosage pages.

Writes, in this order:
  1. templates/page-{slug}.html  x8 — one new top-level group inserted
     immediately before the #formulas group (between the hero and the card
     wall), plus the How We Work step 03 wording fix;
  2. style.css — the band's CSS, appended at end of file;
  3. version bump 2.10.50 -> 2.10.51 in style.css + functions.php.

Every step asserts its own preconditions and re-reads what it wrote, so a
half-applied run is impossible: it either rewrites all ten files or it aborts
before touching any.

The eight per-page fact sets are literals in this file on purpose. The pages
are `page` posts with zero post meta (register_post_meta() in functions.php
registers four keys for the sf_formula CPT and nothing else), so the templates
already are the single source of truth for these facts — this batch keeps that
arrangement and adds no editor surface.

Usage:
    python3 tools/b2d_s5_apply.py --check     # dry run, prints the plan
    python3 tools/b2d_s5_apply.py --apply     # writes the files
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(HERE), "sinofresh-theme")

SLUGS = [
    "soft-chews", "tablets", "powders", "pastes",
    "drops", "liquids", "fish-oil", "dental-chews",
]

OLD_VER = "2.10.50"
NEW_VER = "2.10.51"

# The line every one of the eight templates carries exactly once — block 2's
# own serialisation, which the Site Editor round-trips. The new band goes
# directly in front of it.
FORMULAS_ANCHOR = (
    '<!-- wp:group {"tagName":"section","anchor":"formulas","className":"sf-formulas"'
)

# D6. Byte-identical on all eight pages today, and unique per page.
SENT_OLD = "Delivered in 3\u20137 days."
SENT_OLD_LC = "delivered in 3\u20137 days."
SENT_NEW_LC = "delivered in 3\u20137 working days."

# Values that are the same on all eight pages, with where each one comes from.
SAMPLE_LT = "3\u20137 working days"                      # unified with /services/
PROD_LT = "7\u201315 working days after packaging is ready"  # .sf-spectable col 5
CERTS = "FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC"    # hero subtitle

# --------------------------------------------------------------------------- #
# Per-page facts
#
# short      caption noun (the table's accessible name)
# product    the page's own H1, verbatim, entity-encoded as the template holds it
# benefits   "for …" clause taken from that page's <!-- sf-schema-desc --> — the
#            page's own benefit vocabulary, which is also what its configurator
#            data-group="functions" offers. fish-oil is the one page whose
#            schema-desc names formats instead of benefits ("Omega-3 fish oil in
#            softgels, liquid, and pump formats."), so its clause is read from
#            its own functions list, order preserved: Skin & Coat, Joint, Heart,
#            Immune.
# moq        .sf-spectable column 4, verbatim
# pack       configurator data-group="packaging", entry order preserved, the
#            trailing "Custom" option dropped (the band says "+ custom formats"
#            instead, so the two do not stack)
# pack_forms the same option set read as prose for the Direct Answer: lowercase,
#            pluralised head noun, "or custom formats" last
# --------------------------------------------------------------------------- #
PAGES = {
    "soft-chews": dict(
        short="Soft Chews",
        product="Private Label Soft Chews for Dogs &amp; Cats",
        benefits="joint, skin, calming and digestive support",
        moq="from 500\u20131,000 units",
        pack=["Aluminum Stand-up Pouch", "Aluminum Foil Pouch with Zipper",
              "Plastic Bottle", "Jar", "Blister Pack", "Box + Foil"],
        pack_forms="aluminum stand-up pouches, aluminum foil pouches with zipper, "
                   "plastic bottles, jars, blister packs, boxes with foil",
    ),
    "tablets": dict(
        short="Tablets",
        product="Private Label Pet Tablets for Dogs &amp; Cats",
        benefits="joint, multivitamin, skin, digestive and urinary support",
        moq="from 1,000 units",
        pack=["Plastic Bottle", "Jar", "Blister Pack", "Foil Pouch"],
        pack_forms="plastic bottles, jars, blister packs, foil pouches",
    ),
    "powders": dict(
        short="Powders",
        product="Private Label Pet Supplement Powders",
        benefits="probiotics, digestive support and daily nutrition",
        moq="from 500 units",
        pack=["Jar", "Foil Pouch", "Stand-up Pouch"],
        pack_forms="jars, foil pouches, stand-up pouches",
    ),
    "pastes": dict(
        short="Pastes",
        product="Private Label Pet Supplement Pastes",
        benefits="hairball control, digestive support and nutrient delivery",
        moq="from 500 units",
        pack=["Plastic Tube", "Metal Tube", "Aluminum Tube"],
        pack_forms="plastic tubes, metal tubes, aluminum tubes",
    ),
    "drops": dict(
        short="Drops",
        product="Private Label Pet Supplement Drops",
        benefits="calming, oral care, immune and joint support",
        moq="from 500 units",
        pack=["Dropper Bottle", "Glass Bottle", "Plastic Bottle"],
        pack_forms="dropper bottles, glass bottles, plastic bottles",
    ),
    "liquids": dict(
        short="Liquid Supplements",
        product="Private Label Liquid Pet Supplements",
        benefits="multivitamin, joint, immune and skin &amp; coat support",
        moq="from 500 units",
        pack=["Plastic Bottle", "Glass Bottle", "Bottle with Cup"],
        pack_forms="plastic bottles, glass bottles, bottles with cup",
    ),
    "fish-oil": dict(
        short="Fish Oil",
        product="Private Label Fish Oil for Dogs &amp; Cats",
        benefits="skin &amp; coat, joint, heart and immune support",
        moq="from 1,000 units",
        pack=["Plastic Bottle", "Glass Bottle", "Pump Bottle"],
        pack_forms="plastic bottles, glass bottles, pump bottles",
    ),
    "dental-chews": dict(
        short="Dental Chews &amp; Sticks",
        product="Private Label Dental Chews &amp; Sticks for Dogs",
        benefits="plaque control, tartar reduction and fresh breath",
        moq="from 1,000 units",
        pack=["Foil Pouch", "Stand-up Pouch", "Box"],
        pack_forms="foil pouches, stand-up pouches, boxes",
    ),
}

# One sentence, four variables. Same on all eight pages by design: the pattern
# is what an answer engine extracts, the variables are what makes it this page's
# answer.
DA_TPL = ("{product} are manufactured to FDA, cGMP, ISO 9001, FSSC 22000, HACCP and BRC "
          "standards, with a flexible MOQ {moq} and samples ready in {sample}. Formulated "
          "for {benefits}, they ship in {pack_forms} or custom formats. Bulk production "
          "takes {prod}.")


def packaging_value(page):
    """"A, B, C, + custom formats" — the option set, entry order kept."""
    return ", ".join(page["pack"]) + ", + custom formats"


def direct_answer(page):
    words = DA_TPL.format(
        product=page["product"],
        moq=page["moq"],
        sample=SAMPLE_LT,
        benefits=page["benefits"],
        pack_forms=page["pack_forms"],
        prod=PROD_LT,
    )
    return words


def block(slug):
    """The new top-level section, as the template file stores it.

    No H2 anywhere: toc-nav.js numbers the dosage page's anchors from
    querySelectorAll("h2") and would renumber all seven of them. <caption>
    supplies the table's accessible name instead — the arrangement .sf-spectable
    already uses on the same page.
    """
    page = PAGES[slug]
    rows = [
        ("MOQ", page["moq"]),
        ("Sample lead time", SAMPLE_LT),
        ("Production lead time", PROD_LT),
        ("Certifications", CERTS),
        ("Packaging", packaging_value(page)),
    ]
    trs = "".join(
        "<tr>\n<th scope=\"row\">%s</th>\n<td>%s</td>\n</tr>\n" % (k, v)
        for k, v in rows
    )
    return (
        "<!-- B2D-S5: core facts -->\n"
        '<!-- wp:group {"tagName":"section","className":"sf-facts","layout":{"type":"constrained"},'
        '"style":{"spacing":{"padding":{"top":"var:preset|spacing|50","bottom":"var:preset|spacing|50"}}}} -->\n'
        '<section class="wp-block-group sf-facts" '
        'style="padding-top:var(--wp--preset--spacing--50);padding-bottom:var(--wp--preset--spacing--50)">\n'
        "<!-- wp:html -->\n"
        '<table class="sf-facts__table">\n'
        '<caption class="sf-facts__caption">Core facts \u2014 %s</caption>\n'
        "<tbody>\n"
        "%s"
        "</tbody>\n"
        "</table>\n"
        "<!-- /wp:html -->\n"
        '<!-- wp:paragraph {"className":"sf-facts__answer"} -->\n'
        '<p class="sf-facts__answer">%s</p>\n'
        "<!-- /wp:paragraph -->\n"
        "</section>\n"
        "<!-- /wp:group -->\n"
        "<!-- /B2D-S5 -->\n"
        "\n"
    ) % (page["short"], trs, direct_answer(page))


# --------------------------------------------------------------------------- #
# style.css addition
# --------------------------------------------------------------------------- #

CSS_ADDITION = """/* B2D Step5 — core facts + direct answer, between the hero and #formulas on
   the eight dosage pages. The facts a buyer (or a crawler) needs first — MOQ,
   sampling, lead time, certifications, packaging — were four sections down in
   .sf-spectable; this band puts them one screen up. It duplicates three of
   them on purpose and the two bands will drift; that reconciliation is its own
   batch.

   A new class group (.sf-facts__*) rather than a reuse of .sf-spectable: the
   two bands carry overlapping facts, and separate names stop an edit to one
   from silently restyling the other. The visual tokens are copied from
   .sf-spectable so the page keeps one voice — hairline rows, no vertical
   rules, 11px letterspaced caption in the secondary text colour, ink values.
   Labels stay muted instead of taking the green header band, because five
   stacked full-width green rows would out-weigh the hero above them. ------ */
/* No padding declaration here: the 40px top/bottom lives in the block's own
   spacing attribute and reaches the page as an inline style, which a plain
   class rule would lose to. CSS only overrides it below 768px, and that one
   does need !important for the same reason. ------------------------------- */
.sf-facts__table {
\twidth: 100%;
\tmargin: 0;
\tborder-collapse: collapse;
\ttable-layout: fixed;
\tfont-size: 14px;
\tline-height: 1.5;
\tfont-variant-numeric: tabular-nums;
\ttext-align: left;
}
.sf-facts__caption {
\tcaption-side: top;
\tpadding: 0 0 10px;
\ttext-align: left;
\tfont-size: 11px;
\tfont-weight: 700;
\tletter-spacing: 0.08em;
\ttext-transform: uppercase;
\tcolor: var(--wp--preset--color--text-secondary);
}
/* 220px holds "Production lead time" on one line at 12px/700 uppercase; the
   value column then takes whatever is left, which is where the long Packaging
   and Certifications strings need the room. */
.sf-facts__table tbody th {
\twidth: 220px;
\tpadding: 9px 24px 9px 0;
\tborder-bottom: 1px solid var(--wp--preset--color--border-light);
\tfont-size: 12px;
\tfont-weight: 700;
\tletter-spacing: 0.04em;
\ttext-transform: uppercase;
\tcolor: var(--wp--preset--color--text-secondary);
\tvertical-align: top;
}
.sf-facts__table tbody td {
\tpadding: 9px 0;
\tborder-bottom: 1px solid var(--wp--preset--color--border-light);
\tcolor: var(--wp--preset--color--text-primary);
\tvertical-align: top;
}
/* Two selectors: the block is a direct child of a core constrained-layout
   container, and core ships
   `:root :where(.is-layout-constrained) > * { margin-block-start: 24px }`
   at specificity (0,1,0) — the same as a bare class. Pairing the section class
   with the paragraph class wins that without !important. */
.sf-facts .sf-facts__answer {
\tmax-width: 860px;
\tmargin: 24px 0 0;
\tpadding-top: 20px;
\tborder-top: 1px solid var(--wp--preset--color--border-light);
\tfont-size: 15px;
\tline-height: 1.65;
\tcolor: var(--wp--preset--color--text-primary);
}
/* <=767px: the label column cannot hold "Production lead time" next to a
   value, so each field stacks as a labelled row. Same trade .sf-spectable
   makes — display:block drops the table semantics for assistive tech, and
   nothing here needs the hidden header row that pattern uses, because these
   labels are real <th scope="row"> cells and stack above their own value. */
@media (max-width: 767px) {
\t.sf-facts {
\t\tpadding-top: 24px !important;
\t\tpadding-bottom: 28px !important;
\t}
\t.sf-facts__table,
\t.sf-facts__table tbody,
\t.sf-facts__table tr,
\t.sf-facts__table th,
\t.sf-facts__table td {
\t\tdisplay: block;
\t\twidth: 100%;
\t}
\t.sf-facts__table tbody th {
\t\tpadding: 14px 0 2px;
\t\tborder-bottom: 0;
\t}
\t.sf-facts__table tbody td {
\t\tpadding: 0 0 10px;
\t\tborder-bottom: 1px solid var(--wp--preset--color--border-light);
\t}
}
"""


def plan():
    """Return [(label, path, new_bytes)] and abort on any precondition."""
    out = []

    # ---- the eight templates ----------------------------------------------
    for slug in SLUGS:
        assert slug in PAGES, "no fact set for %s" % slug
        tpl_path = os.path.join(THEME, "templates", "page-%s.html" % slug)
        tpl = open(tpl_path, "r", encoding="utf-8", newline="").read()

        assert tpl.count(FORMULAS_ANCHOR) == 1, \
            "%s: #formulas anchor hit %d times (want 1)" % (slug, tpl.count(FORMULAS_ANCHOR))
        assert "B2D-S5" not in tpl, "%s: band already inserted" % slug
        # the D6 sentence, exactly once, and not already carrying the new wording
        assert tpl.count(SENT_OLD_LC) == 1, \
            "%s: %r hit %d times (want 1)" % (slug, SENT_OLD_LC, tpl.count(SENT_OLD_LC))
        assert SENT_NEW_LC not in tpl, "%s: wording already unified" % slug

        new = tpl.replace(FORMULAS_ANCHOR, block(slug) + FORMULAS_ANCHOR, 1)
        new = new.replace(SENT_OLD_LC, SENT_NEW_LC, 1)

        # the band lands between the hero and the card wall, not anywhere else
        seg_start = new.index("<!-- B2D-S5: core facts -->")
        seg_end = new.index(FORMULAS_ANCHOR)
        seg = new[seg_start:seg_end]
        assert seg.count("<section class=\"wp-block-group sf-facts\"") == 1, slug
        assert seg.count("</table>") == 1, slug
        assert seg.count("<h2") == 0, "%s: the band must not carry a heading" % slug
        assert seg.count("<h1") == 0, slug
        assert seg.rstrip().endswith("<!-- /B2D-S5 -->"), slug
        out.append(("templates/page-%s.html" % slug, tpl_path, new))

    # ---- style.css ---------------------------------------------------------
    css_path = os.path.join(THEME, "style.css")
    css = open(css_path, "r", encoding="utf-8", newline="").read()
    assert ".sf-facts__answer" not in css, "style.css already holds the band"
    assert css.count("Version: " + OLD_VER) == 1, "style.css Version line not unique"
    assert css.endswith("\n"), "style.css does not end with a newline"

    css_new = css + CSS_ADDITION
    css_new = css_new.replace("Version: " + OLD_VER, "Version: " + NEW_VER, 1)
    assert css_new.count(NEW_VER) == 1 and OLD_VER not in css_new
    out.append(("style.css", css_path, css_new))

    # ---- functions.php -----------------------------------------------------
    php_path = os.path.join(THEME, "functions.php")
    php = open(php_path, "r", encoding="utf-8", newline="").read()
    php_old = "array(), '" + OLD_VER + "');"
    assert php.count(php_old) == 1, \
        "functions.php holds %d x %s (want 1)" % (php.count(php_old), php_old)
    php_new = php.replace(php_old, "array(), '" + NEW_VER + "');", 1)
    assert php_new.count(NEW_VER) == 1 and OLD_VER not in php_new
    out.append(("functions.php", php_path, php_new))

    return out


def self_check(items):
    """Re-parse what we are about to write, independently of plan()."""
    for label, _path, body in items:
        if label.startswith("templates/"):
            slug = re.search(r"page-(.+)\.html", label).group(1)
            page = PAGES[slug]
            assert body.count("<!-- B2D-S5: core facts -->") == 1, label
            assert body.count("<!-- /B2D-S5 -->") == 1, label
            assert body.count('class="sf-facts__table"') == 1, label
            assert body.count("Core facts \u2014 " + page["short"]) == 1, label
            # five fields, each label once, each value once
            for k, v in (("MOQ", page["moq"]),
                         ("Sample lead time", SAMPLE_LT),
                         ("Production lead time", PROD_LT),
                         ("Certifications", CERTS),
                         ("Packaging", packaging_value(page))):
                assert body.count('<th scope="row">%s</th>' % k) == 1, (label, k)
                assert body.count("<td>%s</td>" % v) == 1, (label, v)
            # the packaging text and its prose twin are two readings of one set
            for opt in page["pack"]:
                assert opt in body, (label, opt)
            # the sentence change, and only that change, in the How We Work step
            assert body.count(SENT_NEW_LC) == 1, label
            assert SENT_OLD_LC not in body, label
            # the Direct Answer, one paragraph, and its word count in range
            da = re.search(r'<p class="sf-facts__answer">(.*?)</p>', body, re.S)
            assert da, "%s: no Direct Answer paragraph" % label
            words = len(da.group(1).split())
            assert 50 <= words <= 80, "%s: Direct Answer is %d words" % (label, words)
            assert da.group(1).count(".") == 3, "%s: expected three sentences" % label
        elif label == "style.css":
            assert body.count(".sf-facts__answer {") == 1
            # once in the base rule, once in the <=767px override
            assert body.count(".sf-facts__table tbody th {") == 2
            assert body.count("Version: " + NEW_VER) == 1
            # the site's :has() count is a standing invariant: 163 in style.css
            # plus 7 in assets/css/configurator.css
            assert body.count(":has(") == 163, "the style.css :has( count moved"
            # the new CSS carries exactly two !important declarations, both the
            # <=767px padding override that has to beat the block's inline
            # spacing. Count the declarations ("!important;"), not the token:
            # the rule's own comment names it once in prose.
            disk = open(_path, "r", encoding="utf-8", newline="").read()
            assert body.count("!important;") - disk.count("!important;") == 2, \
                "the new CSS should add exactly two !important declarations"
            assert CSS_ADDITION.count("!important;") == 2, \
                "CSS_ADDITION drifted to %d !important declarations" % \
                CSS_ADDITION.count("!important;")
            assert body.count(".sf-facts") == CSS_ADDITION.count(".sf-facts"), \
                "the new CSS should be the only .sf-facts in style.css"
        elif label == "functions.php":
            assert body.count("array(), '" + NEW_VER + "');") == 1


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--check", "--apply"):
        print("usage: b2d_s5_apply.py [--check|--apply]")
        return 2

    items = plan()
    self_check(items)

    print("%-28s %10s %10s %10s" % ("file", "bytes", "->", "delta"))
    for label, _path, body in items:
        old = len(open(_path, "rb").read())
        new = len(body.encode("utf-8"))
        print("%-28s %10d %10d %+10d" % (label, old, new, new - old))
    print()
    print("Direct Answer word counts (must be 50-80):")
    for slug in SLUGS:
        w = len(direct_answer(PAGES[slug]).split())
        print("  %-14s %3d %s" % (slug, w, "ok" if 50 <= w <= 80 else "OUT OF RANGE"))
    print("\n10 files staged, all preconditions asserted.")

    if mode == "--check":
        print("dry run — nothing written.")
        return 0

    for label, path, body in items:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        back = open(path, "r", encoding="utf-8", newline="").read()
        assert back == body, "read-back mismatch on %s" % label
    print("written and read back ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
