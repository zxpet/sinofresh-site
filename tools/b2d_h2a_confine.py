#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2a confinement gate — the detail band is rewritten, nothing else moves.

Batch H2a is NOT a zero-diff batch the way H1 was: the detail band on all 21
records (and their 21 zh twins) is rebuilt, so 42 pages are expected to differ.
The gate's job is therefore two-sided, and the harder half is the negative one:

  * exactly 42 pages may differ, and they must be exactly the detail pages;
  * on each of those 42 pages, every byte OUTSIDE the band must be identical —
    head, header, hero, Specification, FAQ, More, CTA, footer;
  * the band itself must differ (a page that did not change means the template
    was not the one served);
  * the FAQPage JSON-LD must be byte-identical, because the FAQ shortcode and
    its schema read one function and neither is in this batch.

Expected diffs are declared once (page set + band) so a regression that moves a
byte somewhere else cannot hide behind the 42.

The `?ver=` fold is this batch's declared difference, applied to BOTH sides: the
style version moves 2.10.54 -> 2.10.55 and formula-gallery 1.0.0 -> 2.0.0, which
would otherwise make all 75 pages differ and drown the signal. Gate 1 proves the
fold hid exactly those tokens and no others, so folding is not a blind spot.

Gates:
  [1] assets    the style token is 2.10.54 on every base page and 2.10.55 on
                every candidate page; formula-gallery is 2.0.0 on candidate
                detail pages; the asset/version inventory differs ONLY by the
                style token on the 33 pages that must not change; no admin asset
                reaches a front page; the served style.css bytes match the
                working tree (candidate) and the pre-batch commit (live)
  [2] pages     masked comparison with `?ver=` folded: exactly the 42 detail
                pages differ, the other 33 are identical
  [3] band      markers present on all 42 candidate pages and absent from the
                base; every region outside the band byte-identical (masked);
                the band itself NOT identical
  [4] source    the candidate theme files match the sha256 table taken off the
                server, and the new functions sit at top level (tokenizer)
  [5] jsonld    exactly one FAQPage block per detail page, byte-identical
                between base and candidate
  [6] wiring    one source per fact: the params shortcode registered once and
                the old one gone, the intro class emitted from PHP and defined
                in CSS once, the cert row through sf_render_cert_badges() only,
                and the shortcode actually ran on all 42 rendered pages

Negative control: --neg points the candidate at the base — gates 2, 3 and 6
must refuse. --sabotage <kind> runs against a deliberately broken candidate;
every kind must FAIL.

usage:
    b2d_h2a_confine.py --base DIR --new DIR --cand-files SHA256 --theme DIR \
        [--served-css FILE --served-css-live FILE] [--neg] [--sabotage K]
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location('sf_masked_cmp', os.path.join(HERE, 'sf_masked_cmp.py'))
MASKED = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MASKED)

VER = re.compile(r"\?ver=[^\"'&\s]+")
STYLE_VER = re.compile(r"/themes/([a-z0-9-]+)/style\.css\?ver=([0-9a-z.\-]+)")
GALLERY_VER = re.compile(r"/assets/js/formula-gallery\.js\?ver=([0-9a-z.\-]+)")
ASSET_VER = re.compile(r"(?:href|src)=['\"]([^'\"]+?)\?ver=([^'\"]*)['\"]")
LDJSON = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)

BASE_STYLE_VER = '2.10.54'
NEW_STYLE_VER = '2.10.55'
BASE_GALLERY_VER = '1.0.0'
NEW_GALLERY_VER = '2.0.0'

DETAIL_EN = re.compile(r'^formulas__.+\.html$')
DETAIL_ZH = re.compile(r'^zh__formulas__.+\.html$')

# Every marker the rewritten band must carry, on all 42 pages. They are the
# structure the brief fixed: two columns, the parameter list, its rows, the
# intro paragraph and the CTA.
BAND_MARKERS = [
    'sf-fdetail2',
    'sf-fdetail2__inner',
    'sf-fdetail2__media',
    'sf-fdetail2__side',
    'sf-fdetail2__intro',
    'sf-fdetail2__params',
    'sf-fdetail2__term',
    'sf-fdetail2__value',
    'sf-fdetail2__cta',
]
BAND_CLASS = re.compile(r'class="[^"]*\bsf-fdetail2\b[^"]*"')
BAND_ROOT = re.compile(r'<section class="wp-block-group sf-fdetail2 ')
OLD_NS = 'sf-fdetail-media'

# Class TOKENS, not substrings: "sf-fdetail2__intro2" contains
# "sf-fdetail2__intro" and "sf-fdetail2__cta-lost" contains
# "sf-fdetail2__cta", so a substring test passes on a renamed class and the
# sabotage matrix proved it (intro-class-lost and cta-lost both slipped
# through). Splitting the attribute into tokens and comparing set membership
# is the fix, and the markers are then required to appear INSIDE the band
# region so a stray class elsewhere on the page cannot satisfy them.
CLASS_ATTR = re.compile(r'class=["\']([^"\']*)["\']')


def class_tokens(html):
    if not html:
        return set()
    out = set()
    for m in CLASS_ATTR.finditer(html):
        out.update(m.group(1).split())
    return out

# Regions that must be byte-identical (after the shared mask set). Each is
# (label, start marker, tag to balance). 'band' is the one region that must
# DIFFER, and it is bounded by the hero's end and the Specification's start.
REGIONS = [
    ('doc-head', None, None),                     # start of document -> hero
    ('hero', '<section class="wp-block-group has-card-white-color has-text-color sf-hero-inner', 'section'),
    ('specification', '<section class="wp-block-group sf-fdetail has-card-white-background-color', 'section'),
    ('faq', '<section class="wp-block-group sf-fdetail sf-fdetail-faq', 'section'),
    ('more', '<section class="wp-block-group sf-fdetail-more', 'section'),
    ('cta', '<section class="wp-block-group has-card-white-color has-text-color has-primary-background-color', 'section'),
    ('doc-tail', '<footer class="wp-block-template-part">', None),   # footer -> end of document
]

# The candidate files whose bytes must be the ones the server serves. Taken off
# the deployed pre-flight copy, so gate 4 proves "the candidate == the server's
# copy" rather than "the candidate == itself".
THEME_FILES = [
    'functions.php',
    'style.css',
    'templates/single-sf_formula.html',
    'assets/js/formula-gallery.js',
    'inc/formula-admin.php',
    'assets/admin/sf-mb-precheck.js',
]

SABOTAGE = [
    'band-reverted', 'stray-byte-elsewhere', 'detail-not-changed',
    'jsonld-drift', 'intro-class-lost', 'style-ver-stale',
    'admin-leak', 'other-asset-ver-moved', 'gallery-ver-stale', 'cta-lost',
    'php-intro-reverted',
]


def read(p):
    with open(p, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def sha(p):
    if not os.path.exists(p):
        return ''
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def masked(text):
    return MASKED.masked(text)[0]


def fold(text):
    return VER.sub('?ver=', text)


def cut(html, start, tag):
    """Slice from `start`, closing the first balanced <tag>…</tag> pair."""
    i = html.find(start)
    if i < 0:
        return None
    if tag is None:
        return html[i:]
    open_re = re.compile(r'<%s\b' % tag)
    close = '</%s>' % tag
    depth, pos = 0, i
    while True:
        m = open_re.search(html, pos)
        c = html.find(close, pos)
        if c < 0:
            return None
        if m is not None and m.start() < c:
            depth += 1
            pos = m.end()
        else:
            depth -= 1
            pos = c + len(close)
            if depth == 0:
                return html[i:pos]


def detail_pages(names):
    return sorted(n for n in names if DETAIL_EN.match(n) or DETAIL_ZH.match(n))


def band_slice(html):
    """The declared diff region: from just after the hero to just before Spec.

    Bounded by the hero section's closing tag and the Specification section's
    opening tag, so it exists on both sides without depending on the new markup
    and without reading block delimiters (the renderer consumes those, so a
    `<!-- /wp:group -->` anchor finds nothing in a captured page).
    """
    hero = cut(html, '<section class="wp-block-group has-card-white-color has-text-color sf-hero-inner', 'section')
    spec = html.find('sf-fdetail has-card-white-background-color')
    spec_start = html.rfind('<section', 0, spec) if spec > 0 else -1
    if hero is None or spec_start < 0:
        return None
    start = html.find(hero) + len(hero)
    if start >= spec_start:
        return None
    return html[start:spec_start]


def load_manifest(base_dir):
    rows = []
    for line in read(os.path.join(base_dir, 'MANIFEST.tsv')).splitlines():
        if not line or line.startswith('#') or line.startswith('path\t'):
            continue
        p = line.split('\t')[0].strip('/').replace('/', '__')
        rows.append((p or 'root') + '.html')
    return rows


def build_work(args, sabotage, tmp):
    """A mutable copy of the candidate side, broken on purpose."""
    pages = os.path.join(tmp, 'pages')
    shutil.copytree(args.new_dir, pages, ignore=shutil.ignore_patterns('MANIFEST.tsv'))
    theme = os.path.join(tmp, 'theme')
    os.makedirs(theme)
    for rel in THEME_FILES:
        src = os.path.join(args.theme, rel)
        dst = os.path.join(theme, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    shutil.copy(args.cand_files, os.path.join(tmp, 'cand-files.sha256'))

    def page(name):
        return os.path.join(pages, name)

    def write(p, s):
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(s)

    one_en = 'formulas__calming-soft-chews.html'
    one_zh = 'zh__formulas__calming-soft-chews.html'

    if sabotage == 'band-reverted':
        # The rewritten band is swapped back for batch G's markup, on the page
        # bytes themselves: gate 3 must notice the markers are gone.
        p = page(one_en)
        s = read(p)
        write(p, s.replace('sf-fdetail2__params', OLD_NS + '__facts', 1))
    elif sabotage == 'stray-byte-elsewhere':
        p = page('blog.html')          # a page that must not change at all
        write(p, read(p) + '\n')
    elif sabotage == 'detail-not-changed':
        shutil.copy(os.path.join(args.base_dir, one_en), page(one_en))
    elif sabotage == 'jsonld-drift':
        p = page(one_zh)
        s = read(p)
        i = s.find('FAQPage')
        j = s.find('"', s.find('"text"', i) + 7)
        assert j > 0, 'FAQ answer marker missing'
        write(p, s[:j] + 'Drifted' + s[j:])
    elif sabotage == 'intro-class-lost':
        p = page(one_en)
        s = read(p)
        write(p, s.replace('class="sf-fdetail2__intro"', 'class="sf-fdetail2__intro2"', 1))
    elif sabotage == 'style-ver-stale':
        p = page(one_en)
        s = read(p)
        write(p, s.replace('style.css?ver=' + NEW_STYLE_VER, 'style.css?ver=' + BASE_STYLE_VER, 1))
    elif sabotage == 'admin-leak':
        p = page('blog.html')
        s = read(p)
        write(p, s.replace('</head>', '<link rel="stylesheet" href="https://dev.zxpet.com/wp-content/themes/sinofresh-theme/assets/admin/sf-mb.css?ver=1.0.0" /></head>', 1))
    elif sabotage == 'other-asset-ver-moved':
        # A token the batch did not declare: the fold would swallow it, so gate 1
        # has to catch it through the inventory instead.
        p = page('blog.html')
        s = read(p)
        m = ASSET_VER.search(s)
        assert m, 'no asset url on blog.html'
        write(p, s.replace(m.group(0), m.group(0).replace('?ver=' + m.group(2), '?ver=9.9.9'), 1))
    elif sabotage == 'gallery-ver-stale':
        p = page(one_en)
        s = read(p)
        write(p, s.replace('formula-gallery.js?ver=' + NEW_GALLERY_VER, 'formula-gallery.js?ver=' + BASE_GALLERY_VER, 1))
    elif sabotage == 'cta-lost':
        p = page(one_en)
        s = read(p)
        write(p, s.replace('class="sf-fdetail2__cta"', 'class="sf-fdetail2__cta-lost"', 1))
    elif sabotage == 'php-intro-reverted':
        p = os.path.join(theme, 'functions.php')
        s = read(p)
        write(p, s.replace('sf-fdetail2__intro', OLD_NS + '__intro', 1))
    return pages, theme


def gate_assets(args, pages, fails, notes):
    base_names = [n for n in os.listdir(args.base_dir) if n.endswith('.html')]
    new_names = [n for n in os.listdir(pages) if n.endswith('.html')]

    def style_vers(d, names):
        seen = {}
        for n in names:
            m = STYLE_VER.search(read(os.path.join(d, n)))
            seen.setdefault(m.group(2) if m else '(none)', []).append(n)
        return seen

    bv = style_vers(args.base_dir, base_names)
    nv = style_vers(pages, new_names)
    if list(bv) != [BASE_STYLE_VER]:
        fails.append('[1] base style token is %s, expected only %s' % (sorted(bv), BASE_STYLE_VER))
    else:
        notes.append('[1] base side: style token %s on all %d pages' % (BASE_STYLE_VER, len(bv[BASE_STYLE_VER])))
    if list(nv) != [NEW_STYLE_VER]:
        fails.append('[1] candidate style token is %s, expected only %s (%s)' % (
            sorted(nv), NEW_STYLE_VER, {k: v[:3] for k, v in nv.items() if k != NEW_STYLE_VER}))
    else:
        notes.append('[1] candidate side: style token %s on all %d pages' % (NEW_STYLE_VER, len(nv[NEW_STYLE_VER])))

    # formula-gallery: new token on every detail page, old token on none.
    bad = []
    for n in new_names:
        s = read(os.path.join(pages, n))
        m = GALLERY_VER.search(s)
        want = NEW_GALLERY_VER if (DETAIL_EN.match(n) or DETAIL_ZH.match(n)) else None
        got = m.group(1) if m else None
        if want and got != want:
            bad.append('%s want %s got %s' % (n, want, got))
        if not want and got is not None:
            bad.append('%s carries formula-gallery unexpectedly (%s)' % (n, got))
    if bad:
        fails.append('[1] formula-gallery version wrong: %s' % bad[:3])
    else:
        notes.append('[1] formula-gallery %s on all 42 detail pages, absent elsewhere' % NEW_GALLERY_VER)

    # No admin asset on a front page.
    leak = [n for n in new_names if 'assets/admin/' in read(os.path.join(pages, n))]
    if leak:
        fails.append('[1] admin assets leak into front pages: %s' % leak[:3])
    else:
        notes.append('[1] no admin asset is referenced by any front page')

    # The inventory on the 33 pages that must not change: only the style token.
    inv_ok, unexpected = 0, []
    for n in new_names:
        if DETAIL_EN.match(n) or DETAIL_ZH.match(n):
            continue
        a = sorted(ASSET_VER.findall(read(os.path.join(args.base_dir, n))))
        b = sorted(ASSET_VER.findall(read(os.path.join(pages, n))))
        moved = []
        da = {u.rsplit('/', 1)[-1]: v for u, v in a}
        db = {u.rsplit('/', 1)[-1]: v for u, v in b}
        for k in set(da) | set(db):
            if da.get(k) != db.get(k):
                moved.append((k, da.get(k), db.get(k)))
        if moved == [('style.css', BASE_STYLE_VER, NEW_STYLE_VER)]:
            inv_ok += 1
        else:
            unexpected.append((n, moved))
    if unexpected:
        fails.append('[1] undeclared version movement on %d page(s): %s' % (len(unexpected), unexpected[:2]))
    else:
        notes.append('[1] %d stable pages: the only moved token is style.css %s -> %s' % (
            inv_ok, BASE_STYLE_VER, NEW_STYLE_VER))

    # The served stylesheet must BE the working tree's, on both sides. A token
    # that moved while the bytes did not would be a cache lie in either
    # direction (new URL, old file / old URL, new file).
    if args.served_css:
        local = sha(os.path.join(args.theme, 'style.css'))
        served = sha(args.served_css)
        if served != local:
            fails.append('[1] the candidate style.css served is not the working tree file')
        else:
            notes.append('[1] candidate style.css served == working tree (sha %s…)' % served[:12])
    if args.served_css_live:
        pre = subprocess.run(['git', '-C', ROOT, 'show', '1d4bd96:sinofresh-theme/style.css'],
                             capture_output=True)
        if pre.returncode != 0:
            fails.append('[1] cannot read the pre-batch style.css out of git')
        else:
            want = hashlib.sha256(pre.stdout).hexdigest()
            got = sha(args.served_css_live)
            if got != want:
                fails.append('[1] live style.css is not the pre-batch file (got %s… want %s…)' % (got[:12], want[:12]))
            else:
                notes.append('[1] live style.css still == pre-batch commit (sha %s…)' % got[:12])


def gate_pages(args, pages, fails, notes):
    names = load_manifest(args.base_dir)
    if len(names) != 75:
        fails.append('[2] manifest carries %d paths (want 75)' % len(names))
    expected = set(detail_pages(names))
    diff, same, missing = [], [], []
    for rel in names:
        b = os.path.join(pages, rel)
        if not os.path.exists(b):
            missing.append(rel)
            continue
        a = masked(fold(read(os.path.join(args.base_dir, rel))))
        c = masked(fold(read(b)))
        (diff if a != c else same).append(rel)
    if missing:
        fails.append('[2] candidate capture missing %d page(s): %s' % (len(missing), missing[:3]))
    got, want = set(diff), expected
    if got != want:
        fails.append('[2] diff set is wrong: %d differ, expected 42; extra=%s missing=%s' % (
            len(diff), sorted(got - want)[:4], sorted(want - got)[:4]))
    else:
        notes.append('[2] exactly the 42 detail pages differ (%d en + %d zh); %d others identical' % (
            len([n for n in want if DETAIL_EN.match(n)]),
            len([n for n in want if DETAIL_ZH.match(n)]), len(same)))

    # Folding must be what removes the other 33 — otherwise the "identical"
    # half is an artefact of the fold and proves nothing.
    unfolded = [r for r in names if os.path.exists(os.path.join(pages, r))
                and masked(read(os.path.join(args.base_dir, r))) != masked(read(os.path.join(pages, r)))]
    if len(unfolded) != 75:
        fails.append('[2] unfolded comparison differs on %d pages (want 75: the token moved everywhere)' % len(unfolded))
    else:
        notes.append('[2] unfolded: all 75 differ, so the fold hides exactly the declared token')


def gate_band(args, pages, fails, notes):
    names = detail_pages(load_manifest(args.base_dir))
    bad_marker, bad_old, region_bad, band_same = [], [], [], []
    for n in names:
        a = read(os.path.join(args.base_dir, n))
        c = read(os.path.join(pages, n))
        ba, bc = band_slice(a), band_slice(c)
        tok_c, tok_a = class_tokens(bc), class_tokens(ba)
        for m in BAND_MARKERS:
            if m not in tok_c:
                bad_marker.append('%s:%s' % (n, m))
            if m in tok_a:
                bad_marker.append('%s:%s(already in base)' % (n, m))
        if not BAND_ROOT.search(c):
            bad_marker.append('%s:band-root' % n)
        if OLD_NS in class_tokens(c):
            bad_old.append(n)
        if OLD_NS not in tok_a:
            bad_old.append('%s(old ns missing from base band)' % n)
        for label, start, tag in REGIONS:
            if start is None:
                # doc-head ends where the hero begins; doc-tail runs from the footer.
                if label == 'doc-head':
                    end = c.find('<section class="wp-block-group has-card-white-color has-text-color sf-hero-inner')
                    enda = a.find('<section class="wp-block-group has-card-white-color has-text-color sf-hero-inner')
                else:
                    continue
                if end < 0 or enda < 0:
                    region_bad.append('%s:%s(anchor)' % (n, label))
                    continue
                ca, cc = a[:enda], c[:end]
            else:
                ra, rc = cut(a, start, tag), cut(c, start, tag)
                if ra is None or rc is None:
                    region_bad.append('%s:%s(anchor)' % (n, label))
                    continue
                ca, cc = ra, rc
            # Fold the declared token here too: it lives in the head and tail of
            # every page, and leaving it unfolded would report the whole document
            # as "changed outside the band" on all 42 pages — the exact false
            # positive that would make this gate useless.
            if masked(fold(ca)) != masked(fold(cc)):
                region_bad.append('%s:%s' % (n, label))
        ba, bc = band_slice(a), band_slice(c)
        if ba is None or bc is None:
            region_bad.append('%s:band(anchor)' % n)
        elif masked(fold(ba)) == masked(fold(bc)):
            band_same.append(n)
    if bad_marker:
        fails.append('[3] band markers missing on candidate pages: %s' % bad_marker[:5])
    else:
        notes.append('[3] all %d detail pages carry the %d band markers and the band root' % (
            len(names), len(BAND_MARKERS)))
    if bad_old:
        fails.append('[3] batch G namespace still present (or absent from base): %s' % bad_old[:5])
    else:
        notes.append('[3] the old band namespace is gone from all %d rendered pages' % len(names))
    if region_bad:
        fails.append('[3] region changed outside the band: %s' % region_bad[:6])
    else:
        notes.append('[3] head/hero/Specification/FAQ/More/CTA/footer byte-identical on all %d pages' % len(names))
    if band_same:
        fails.append('[3] the band did not change on: %s' % band_same[:5])
    else:
        notes.append('[3] the band itself differs on all %d pages (the change is where it was declared)' % len(names))


def gate_source(args, theme, pages, fails, notes):
    table = {}
    for line in read(os.path.join(os.path.dirname(theme), 'cand-files.sha256')).splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            table[parts[1].lstrip('*').strip()] = parts[0]
    if not table:
        fails.append('[4] candidate file table is empty')
    checked = 0
    for rel, want in table.items():
        got = sha(os.path.join(theme, rel))
        if got != want:
            fails.append('[4] %s is not the file recorded off the server' % rel)
        else:
            checked += 1
    if checked == len(table) and table:
        notes.append('[4] all %d candidate theme files match the server-side sha256 table' % checked)

    php = os.path.expanduser('~/Library/Application Support/Local/lightning-services/'
                             'php-8.2.29+0/bin/darwin-arm64/bin/php')
    if os.path.exists(php):
        proc = subprocess.run([php, os.path.join(ROOT, 'tools', 'b2d_c_php_scope.php'),
                               os.path.join(theme, 'functions.php'),
                               'sinofresh_formula_params', 'sinofresh_formula_gallery_slots',
                               'sinofresh_formula_video_id', 'sinofresh_formula_chip_list',
                               'sinofresh_formula_tier_table'],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        off = [l for l in out.splitlines() if 'TOPLEVEL' in l and 'depth 0' not in l]
        found = [l for l in out.splitlines() if 'TOPLEVEL' in l]
        if off or len(found) != 5:
            fails.append('[4] tokenizer: %d/5 functions at top level; offending=%s' % (len(found) - len(off), off[:3]))
        else:
            notes.append('[4] tokenizer: all 5 new functions at top level (depth 0)')
    else:
        fails.append('[4] Local PHP not found, top-level assertion could not run')


def gate_jsonld(args, pages, fails, notes):
    names = detail_pages(load_manifest(args.base_dir))
    bad_count, drift, no_faq = [], [], []
    for n in names:
        a = read(os.path.join(args.base_dir, n))
        c = read(os.path.join(pages, n))
        ba = [b for b in LDJSON.findall(a) if '"FAQPage"' in b]
        bc = [b for b in LDJSON.findall(c) if '"FAQPage"' in b]
        if len(bc) != 1:
            no_faq.append('%s(%d)' % (n, len(bc)))
            continue
        if len(ba) != 1:
            bad_count.append('%s(base %d)' % (n, len(ba)))
            continue
        if masked(ba[0]) != masked(bc[0]):
            drift.append(n)
    if no_faq:
        fails.append('[5] candidate does not carry exactly one FAQPage block: %s' % no_faq[:5])
    if bad_count:
        fails.append('[5] base FAQPage count != 1: %s' % bad_count[:5])
    if drift:
        fails.append('[5] FAQPage JSON-LD drifted on: %s' % drift[:5])
    if not (no_faq or bad_count or drift):
        notes.append('[5] FAQPage JSON-LD byte-identical on all %d detail pages (one block each)' % len(names))


def gate_wiring(args, theme, pages, fails, notes):
    fn = read(os.path.join(theme, 'functions.php'))
    css = read(os.path.join(theme, 'style.css'))
    tpl = read(os.path.join(theme, 'templates/single-sf_formula.html'))

    checks = [
        ("[6] sf_formula_params registered exactly once", fn.count("add_shortcode('sf_formula_params'") == 1),
        ("[6] sf_formula_factsheet no longer registered", fn.count("add_shortcode('sf_formula_factsheet'") == 0),
        ("[6] the old shortcode name survives nowhere but the note", fn.count('sf_formula_factsheet') <= 1),
        ("[6] template calls the params shortcode once", tpl.count('[sf_formula_params]') == 1),
        ("[6] template carries no batch G class", 'sf-fdetail-media' not in tpl),
        ("[6] intro class emitted from PHP exactly once", fn.count('sf-fdetail2__intro"') == 1),
        ("[6] intro class defined in CSS exactly once", css.count('.sf-fdetail2__intro {') == 1),
        ("[6] params list defined in CSS exactly once", css.count('.sf-fdetail2__params {') == 1),
        ("[6] params reads the Site Settings badges", 'sf_render_cert_badges()' in fn),
    ]
    # The cert row must not have a second source inside the params function.
    body = fn[fn.find('function sinofresh_formula_params'):]
    body = body[:body.find('\nadd_shortcode')]
    checks.append(("[6] params does not read the dosage cert cell",
                   'sf_formula_certifications_value' not in body
                   and "'Certifications'" not in body.replace("$rows['Certifications']", '')))
    for label, ok in checks:
        if not ok:
            fails.append(label)
    if not [l for l, ok in checks if not ok]:
        notes.append('[6] all %d wiring assertions hold' % len(checks))

    # The strongest wiring proof: the shortcode actually ran, on every page.
    names = detail_pages(load_manifest(args.base_dir))
    unrun, norow = [], []
    for n in names:
        c = read(os.path.join(pages, n))
        if c.count('<dl class="sf-fdetail2__params"') != 1:
            unrun.append(n)
            continue
        if '<dt class="sf-fdetail2__term"' not in c or '<dd class="sf-fdetail2__value"' not in c:
            norow.append(n)
    if unrun:
        fails.append('[6] the params list is not rendered exactly once on: %s' % unrun[:5])
    elif norow:
        fails.append('[6] params list has no rows on: %s' % norow[:5])
    else:
        notes.append('[6] the params shortcode rendered one populated list on all %d pages' % len(names))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--cand-files', required=True)
    ap.add_argument('--theme', required=True)
    ap.add_argument('--served-css', default=None)
    ap.add_argument('--served-css-live', default=None)
    ap.add_argument('--neg', action='store_true')
    ap.add_argument('--sabotage', choices=SABOTAGE)
    args = ap.parse_args()

    fails, notes = [], []
    args.base_dir = args.base
    args.new_dir = args.new
    tmp = tempfile.mkdtemp(prefix='h2a-gate-')
    try:
        if args.neg:
            args.new_dir = args.base
        pages, theme = build_work(args, args.sabotage, tmp)
        if args.neg:
            # The negative control must also carry the base theme, or gate 4
            # would fail for the wrong reason and prove nothing.
            for rel in THEME_FILES:
                src = os.path.join(args.theme, rel)
                if rel == 'functions.php':
                    # the pre-batch functions.php: same file, class name back
                    s = read(src).replace('sf-fdetail2__intro', OLD_NS + '__intro')
                    with open(os.path.join(theme, rel), 'w', encoding='utf-8') as fh:
                        fh.write(s)
                elif rel == 'style.css':
                    pre = subprocess.run(['git', '-C', ROOT, 'show', '1d4bd96:sinofresh-theme/style.css'],
                                         capture_output=True)
                    if pre.returncode == 0:
                        with open(os.path.join(theme, rel), 'wb') as fh:
                            fh.write(pre.stdout)
            with open(os.path.join(tmp, 'cand-files.sha256'), 'w', encoding='utf-8') as fh:
                for rel in THEME_FILES:
                    fh.write('%s  %s\n' % (sha(os.path.join(theme, rel)), rel))

        gate_assets(args, pages, fails, notes)
        gate_pages(args, pages, fails, notes)
        gate_band(args, pages, fails, notes)
        gate_source(args, theme, pages, fails, notes)
        gate_jsonld(args, pages, fails, notes)
        gate_wiring(args, theme, pages, fails, notes)

        mode = 'NEGATIVE CONTROL' if args.neg else ('SABOTAGE:' + args.sabotage if args.sabotage else 'CANDIDATE')
        print('=' * 72)
        print('Batch H2a gate — %s' % mode)
        print('=' * 72)
        for n in notes:
            print('  ok   ' + n)
        for f in fails:
            print('  FAIL ' + f)
        print('-' * 72)
        if args.neg or args.sabotage:
            if fails:
                print('VERDICT: FAIL as required (%d finding(s))' % len(fails))
                return 0
            print('VERDICT: PASSED — the control was not caught, the gate is blind')
            return 1
        if fails:
            print('VERDICT: FAIL (%d finding(s))' % len(fails))
            return 1
        print('VERDICT: PASS — all six gates hold')
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
