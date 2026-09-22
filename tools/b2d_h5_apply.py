#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5 — the alt normalisation, applied to the eight dosage templates.

WHAT THIS CHANGES, AND WHAT IT DELIBERATELY DOES NOT

Ruling D asked for the image alts to be normalised, not rewritten: the logo,
and the product stills that repeat in the dosage tiles. Two carriers hold those
strings and they have to stay in step:

  * the product stills inside templates/page-{form}.html — seven sibling tiles
    per template, each naming a *different* form, so the string that needs the
    tablets clause lives in the seven templates that are not the tablets page;
  * the card markup [sf_formula_grid] prints, which batch H5 moved into
    sinofresh_formula_product_alt() so the two carriers cannot be edited apart.

This tool owns the first carrier; the function owns the second. Both take their
words from the same place: the clause map is PARSED OUT OF functions.php rather
than retyped here, and the assertion that exactly eight clauses came back stops
someone "helpfully" hard-coding a ninth into this file. Retyping the map is how
the two carriers would drift.

The base strings are likewise not retyped: they are discovered in the templates
(`SINO FRESH {label} private label pet supplement product`), and the slug that
selects the clause is derived from the label the template already prints
("Fish Oil" -> fish-oil). A label with no clause is reported and left alone —
the alt it had is better than an invented one.

NOT IN SCOPE. page-products.html's eight tiles say "Private label soft chews
manufacturing" — a different convention on a page that carries no Product
schema. It is left as it is: this batch normalises the alts ruling D named, and
a wholesale alt rewrite is option B, which was declined.

usage:
    b2d_h5_apply.py --check          # report, change nothing
    b2d_h5_apply.py --apply
    b2d_h5_apply.py --revert
"""
import argparse
import os
import re
import sys

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILE_DIR)
THEME = os.path.join(ROOT, "sinofresh-theme")
FUNCTIONS = os.path.join(THEME, "functions.php")
TEMPLATE_GLOB = "page-%s.html"

FORMS = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids",
         "fish-oil", "dental-chews"]

BASE = "SINO FRESH %s private label pet supplement product"
SEP = " \u2014 "

# The logo pair. The alt WordPress prints is not in the theme at all: the site
# logo is the custom-logo attachment, and its Alt Text is empty, so core falls
# back to get_bloginfo('name') — "sinofresh" (lower case, no noun). The fix is
# the media library's own Alt Text field, so that is what the batch sets; the
# pair is declared here because the byte gate has to invert it on captured HTML.
LOGO_OLD = 'alt="sinofresh"'
LOGO_NEW = 'alt="SINO FRESH logo"'
LOGO_SLUG = "sino-fresh-logo-2"
LOGO_ATTACHMENT_ID = 96

VISUALS_FN = "sinofresh_formula_alt_visuals"
# Matches the label whether or not the clause is already there, so the same
# reader works before the batch, after it, and after a revert — a discovery
# pass that only knows the un-suffixed spelling cannot verify its own output.
BASE_RE = re.compile(
    r'alt="SINO FRESH ([^"]*?) private label pet supplement product(?: \u2014 [^"]*)?"')


def suffix_map():
    """slug -> visual clause, read out of sinofresh_formula_alt_visuals().

    Parsed rather than imported: the map lives in PHP, and a second copy here
    is exactly the duplication this batch is trying to remove. The count
    assertion is the anti-drift guard — a parse that silently returns {} would
    otherwise make every subsequent check pass on an empty change set.
    """
    src = open(FUNCTIONS, encoding="utf-8").read()
    start = src.find("function %s()" % VISUALS_FN)
    if start < 0:
        raise SystemExit("functions.php: %s() not found" % VISUALS_FN)
    body = src[start:src.find("\n}", start)]
    pairs = re.findall(r"'([a-z0-9-]+)'\s*=>\s*'([^']+)'", body)
    out = {}
    for slug, clause in pairs:
        if slug in FORMS:
            out[slug] = clause
    if len(out) != len(FORMS):
        raise SystemExit("functions.php: expected %d clauses, parsed %d (%r)"
                         % (len(FORMS), len(out), sorted(out)))
    return out


def slug_for_label(label):
    return label.strip().lower().replace(" ", "-")


def alt_pairs():
    """[(old_alt_string, new_alt_string)] for the eight product stills.

    Both halves are derived: the label comes out of the templates, the clause
    comes out of the map, and the old string is rebuilt from the label. Nothing
    here is a literal that a reviewer would have to compare with functions.php
    by eye — and because the reader accepts either spelling, the pairs are the
    same before the batch runs and after it, which is what makes --verify and
    --revert possible from one description.
    """
    visuals = suffix_map()
    found = {}
    seen_labels = set()
    for form in FORMS:
        path = os.path.join(THEME, "templates", TEMPLATE_GLOB % form)
        for label in BASE_RE.findall(open(path, encoding="utf-8").read()):
            if label in seen_labels:
                continue
            seen_labels.add(label)
            slug = slug_for_label(label)
            if slug not in visuals:
                print("  !! no clause for %r (from %r in %s)"
                      % (slug, label, os.path.basename(path)), file=sys.stderr)
                continue
            found[BASE % label] = BASE % label + SEP + visuals[slug]
    if len(found) != len(FORMS):
        raise SystemExit("expected %d base strings, found %d: %r"
                         % (len(FORMS), len(found), sorted(found)))
    return sorted(found.items())


def edit(mode):
    pairs = alt_pairs()
    total = 0
    touched = []
    for form in FORMS:
        path = os.path.join(THEME, "templates", TEMPLATE_GLOB % form)
        text = original = open(path, encoding="utf-8").read()
        n = 0
        for old, new in pairs:
            if mode == "revert":
                src, dst = new, old
            else:
                src, dst = old, new
            # idempotent: skip a pair that is already in the requested state
            if 'alt="%s"' % src not in text:
                continue
            c = text.count('alt="%s"' % src)
            text = text.replace('alt="%s"' % src, 'alt="%s"' % dst)
            n += c
        if text != original:
            touched.append((os.path.basename(path), n))
            total += n
            if mode != "check":
                open(path, "w", encoding="utf-8").write(text)
    print("mode=%s  files=%d  replacements=%d" % (mode, len(touched), total))
    for name, n in touched:
        print("  %-28s %d" % (name, n))
    return total


def verify(state="applied"):
    """Per template: the un-suffixed spellings must be gone (state=applied) or
    back (state=reverted), and exactly seven product alts must be present.

    The seven is the check that catches a replacement that ate an image rather
    than a string: every dosage template shows its seven sibling forms.
    """
    pairs = alt_pairs()
    bad = 0
    for form in FORMS:
        path = os.path.join(THEME, "templates", TEMPLATE_GLOB % form)
        text = open(path, encoding="utf-8").read()
        old_total = new_total = 0
        for old, new in pairs:
            o, n = text.count('alt="%s"' % old), text.count('alt="%s"' % new)
            old_total += o
            new_total += n
        if state == "applied":
            if old_total:
                print("  FAIL %s still carries %d un-suffixed product alt(s)"
                      % (os.path.basename(path), old_total))
                bad += 1
            if new_total != 7:
                print("  FAIL %s has %d suffixed product alts, expected 7"
                      % (os.path.basename(path), new_total))
                bad += 1
        else:
            if old_total != 7:
                print("  FAIL %s has %d un-suffixed product alts, expected 7"
                      % (os.path.basename(path), old_total))
                bad += 1
            if new_total:
                print("  FAIL %s still carries %d suffixed product alt(s)"
                      % (os.path.basename(path), new_total))
                bad += 1
    print("verify(%s): %s" % (state, "PASS" if not bad else "FAIL (%d)" % bad))
    return bad


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="report only")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--pairs", action="store_true",
                   help="print the declared pairs and exit")
    args = ap.parse_args()

    if args.pairs:
        for old, new in alt_pairs():
            print("%s\n -> %s" % (old, new))
        print("logo: %s -> %s" % (LOGO_OLD, LOGO_NEW))
        return 0
    if args.verify:
        return 1 if verify("applied") else 0
    if args.check:
        edit("check")
        return 0
    if args.apply:
        edit("apply")
        return 1 if verify("applied") else 0
    edit("revert")
    return 1 if verify("reverted") else 0


if __name__ == "__main__":
    sys.exit(main())
