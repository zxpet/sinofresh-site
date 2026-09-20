#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step 2 — idempotent rewriter for the product-gallery band.

Inserts one block into each of the eight `templates/page-{slug}.html`, between
the hero group and the `#formulas` group. Nothing else is touched: the
shortcode, the script and the CSS live in their own files and are written by
hand, so this tool only has the one repeated, byte-level job to do.

The anchor is the `#formulas` block comment, which opens the band that follows
the hero, and the insert goes immediately BEFORE it:

    </section>
    <!-- /wp:group -->
    <blank>
    <!-- wp:group {"tagName":"section","anchor":"formulas"

Those 32 bytes of lead-in are asserted too, not assumed: an earlier revision
of this tool anchored on the trailing `</section>` instead and put the gallery
INSIDE the hero group — where the hero's own padding-bottom then opened a
20px-plus dark-green gap under the light band. The depth check below is what
makes that class of mistake impossible: the marker has to land at section
nesting depth 0, i.e. as a sibling of the hero, never as its child.

The inserted container is the `#formulas` block's own comment with
`anchor`/`className` swapped and `backgroundColor` added, so the JSON key
order matches what core writes for the two reference blocks that already
carry those keys (`sf-factory` = className+backgroundColor, `inquiry-form` =
anchor+backgroundColor). The `<section>` line follows the same two
references: id first, then class, then style.

Usage:
    python3 tools/b2d_s2_apply.py --check     # dry run, prints the plan
    python3 tools/b2d_s2_apply.py --apply     # writes the eight files
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(HERE), "sinofresh-theme")

SLUGS = [
    "soft-chews", "tablets", "powders", "pastes",
    "drops", "liquids", "fish-oil", "dental-chews",
]

# The insertion point: the start of the `#formulas` group comment (54 chars).
ANCHOR = '<!-- wp:group {"tagName":"section","anchor":"formulas"'
ANCHOR_SHA16 = "218660a632760365"
# The scan report quotes the 60-char slice of the full four-line context.
ANCHOR_PREFIX_SHA16 = "8aa9e570f058aa72"
# The 31 bytes that must sit directly in front of it — the hero group's close.
LEAD_IN = "</section>\n<!-- /wp:group -->\n\n"

SECTION_OPEN = re.compile(r"<section\b")
SECTION_CLOSE = re.compile(r"</section>")

MARKER = "<!-- B2D-S2: gallery -->"

# `form="__FORM__"` is substituted per page. str.replace is used rather than
# str.format because the block comment is full of balanced braces.
#
# The block opens with a BLANK LINE, and that is load-bearing rather than
# cosmetic. A plain HTML comment sitting between two blocks changes how much
# whitespace do_blocks() preserves at that junction: the hero's tail renders as
# `</section>\n\n\n` when a block follows immediately, but `</section>\n\n\n\n`
# when the baseline's block boundary is there instead. One blank line in front
# of the marker restores the missing newline, so deleting the band from the
# render reproduces the baseline byte for byte — which is what makes the
# confinement proof exact instead of "exact apart from whitespace".
TEMPLATE = (
    "\n" + MARKER + "\n"
    '<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery",'
    '"backgroundColor":"bg-light","layout":{"type":"constrained"},'
    '"style":{"spacing":{"padding":{"top":"var:preset|spacing|80",'
    '"bottom":"var:preset|spacing|80"}}}} -->\n'
    '<section id="gallery" class="wp-block-group sf-gallery '
    'has-bg-light-background-color has-background" '
    'style="padding-top:var(--wp--preset--spacing--80);'
    'padding-bottom:var(--wp--preset--spacing--80)">\n'
    "<!-- wp:html -->\n"
    '[sf_formula_gallery form="__FORM__"]\n'
    "<!-- /wp:html -->\n"
    "</section>\n"
    "<!-- /wp:group -->\n\n"
)

# What the insertion puts in front of the marker, i.e. how much whitespace it
# adds to the hero's tail. Asserted after the write so it cannot silently
# change without the confinement proof being revisited.
LEADING_BLANK_LINES = 1

DATA_ATTRS = (
    MARKER,
    '"anchor":"gallery"',
    'class="wp-block-group sf-gallery has-bg-light-background-color has-background"',
    "sf-gallery__slide",
)


def template_path(slug):
    return os.path.join(THEME, "templates", "page-%s.html" % slug)


def build(slug):
    return TEMPLATE.replace("__FORM__", slug)


def section_depth(text, offset):
    """How many <section> elements are still open at `offset`."""
    head = text[:offset]
    return len(SECTION_OPEN.findall(head)) - len(SECTION_CLOSE.findall(head))


def check_one(slug):
    """Return (text, new_text, problems). Collects every problem, not the first."""
    path = template_path(slug)
    problems = []
    if not os.path.exists(path):
        return None, None, ["missing file %s" % path]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    hits = text.count(ANCHOR)
    if hits != 1:
        problems.append("anchor occurs %d times, expected exactly 1" % hits)
    fhits = text.count('"anchor":"formulas"')
    if fhits != 1:
        problems.append('anchor":"formulas" occurs %d times, expected 1' % fhits)

    # Already applied? Then the run is a no-op rather than a double insert.
    if MARKER in text:
        problems.append("already carries %s — nothing to do" % MARKER)
    for token in DATA_ATTRS[1:]:
        if token in text:
            problems.append("unexpected pre-existing %r" % token)

    if not text.endswith("\n"):
        problems.append("file does not end with a newline")

    if problems:
        return text, None, problems

    offset = text.index(ANCHOR)

    # The hero group has to be closed and the line blank before the anchor,
    # otherwise the insert is landing somewhere other than between the two
    # bands. Asserted, not assumed.
    if text[offset - len(LEAD_IN):offset] != LEAD_IN:
        problems.append("anchor is not preceded by the hero's </section> close: %r"
                        % text[max(0, offset - 40):offset])

    # The marker must be a SIBLING of the hero, at depth 0. This is the check
    # that catches "inserted inside the hero group", which is structurally
    # wrong even though the markup still balances.
    if section_depth(text, offset) != 0:
        problems.append("insert point is inside %d open <section> element(s)"
                        % section_depth(text, offset))

    if problems:
        return text, None, problems

    block = build(slug)
    new_text = text[:offset] + block + text[offset:]

    # The insert must be a pure addition at exactly one offset.
    if new_text[:offset] != text[:offset]:
        problems.append("bytes before the insert point changed")
    if new_text[offset + len(block):] != text[offset:]:
        problems.append("bytes after the insert point changed")
    if len(new_text) - len(text) != len(block):
        problems.append("file grew by the wrong amount")
    if new_text.count(MARKER) != 1:
        problems.append("marker count after insert != 1")
    if new_text.count(LEAD_IN + "\n" * LEADING_BLANK_LINES + MARKER) != 1:
        problems.append("hero close is not separated from the marker by exactly "
                        "%d blank line(s)" % LEADING_BLANK_LINES)
    if not new_text[offset:].startswith("\n" * LEADING_BLANK_LINES + MARKER):
        problems.append("insertion no longer starts with %d blank line(s) before "
                        "the marker — the confinement proof depends on it"
                        % LEADING_BLANK_LINES)
    if section_depth(new_text, new_text.index(MARKER)) != 0:
        problems.append("marker does not sit at section depth 0 after the insert")
    # Section tags must stay balanced across the whole file.
    if len(SECTION_OPEN.findall(new_text)) != len(SECTION_CLOSE.findall(new_text)):
        problems.append("unbalanced <section> tags after the insert")

    # Re-parsing the JSON comment is the only way to prove the block is
    # well-formed rather than merely well-balanced.
    for line in block.splitlines():
        if line.startswith("<!-- wp:group "):
            blob = line[len("<!-- wp:group "):-len(" -->")]
            try:
                json.loads(blob)
            except ValueError as exc:
                problems.append("block comment is not valid JSON: %s" % exc)

    return text, new_text, problems


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--check", "--apply"):
        print(__doc__)
        return 2

    if hashlib.sha256(ANCHOR.encode()).hexdigest()[:16] != ANCHOR_SHA16:
        print("FATAL: ANCHOR sha256[:16] drift")
        return 1

    # The scan report quotes the first 60 characters of this same four-line
    # context. Re-deriving its sha here keeps this tool and that document from
    # drifting apart.
    if hashlib.sha256((LEAD_IN + ANCHOR)[:60].encode()).hexdigest()[:16] != ANCHOR_PREFIX_SHA16:
        print("FATAL: scan-report 60-char lead-in sha drift (expected %s)"
              % ANCHOR_PREFIX_SHA16)
        return 1

    total_problems = 0
    plan = []
    for slug in SLUGS:
        text, new_text, problems = check_one(slug)
        if problems:
            total_problems += len(problems)
            print("[FAIL] %-14s %s" % (slug, "; ".join(problems)))
            continue
        plan.append((slug, text, new_text))
        print("[ok  ] %-14s %7d -> %7d (+%d)"
              % (slug, len(text), len(new_text), len(new_text) - len(text)))

    if total_problems:
        print("\n%d problem(s) — nothing written." % total_problems)
        return 1

    print("\nall eight anchors unique and preceded by the hero close; "
          "every insert lands at section depth 0; insert size = %d bytes"
          % len(build(SLUGS[0])))
    print("(scan-report lead-in sha %s still matches the 60-char slice)"
          % ANCHOR_PREFIX_SHA16)

    if mode == "--check":
        print("dry run (--check): no file written")
        return 0

    for slug, text, new_text in plan:
        path = template_path(slug)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        with open(path, encoding="utf-8") as fh:
            back = fh.read()
        if back != new_text:
            print("FATAL: read-back mismatch on %s" % path)
            return 1
        print("[wrote] %s  %d bytes" % (path, len(back)))

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
