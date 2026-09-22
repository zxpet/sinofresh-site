#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5 — the two gates, both of which have to hold.

WHY TWO

Every batch before this one could be judged by bytes. H5 cannot: it is a batch
whose whole point is that the same pages gain schema properties and lose a set
of unhelpful alts, so a byte gate reports 75 pages different and a gate that
accepts "the JSON still parses" reports green after someone deletes `brand`.
Both are false greens.

  * the JSON-LD SEMANTIC gate parses every ld+json block on both sides and
    requires deep equality with a strict allowance: a key may be ADDED, never
    changed and never dropped. It then requires the set of added key paths to
    equal the set this batch declares — an unexplained addition is a failure
    even though the rule would permit it.
  * the rendered-HTML WHITELIST byte gate cuts the ld+json blocks out of both
    sides, inverts the declared alt substitutions on the candidate, and then
    requires byte equality. Anything outside the whitelist — one character in
    the wrong place — shows up as a diff page.

Neither gate can be satisfied by damaging the other: the semantic gate does not
look at the rest of the page, and the byte gate cannot see inside the blocks it
cuts. Running both is the claim.

AND A THIRD CLAIM, because two gates are still not enough

Both gates above answer "did the declared change happen, and nothing else".
Neither answers "did it happen EVERYWHERE it was declared, or only in some of
the places". A substitution the batch forgot is byte-identical to the baseline,
so the inversion finds it equal and reports green; and it is not an added or
changed schema key, so the semantic gate never sees it either. Measured on the
first build of this batch: 398 occurrences of the eight declared strings on the
baseline, 272 replaced, and the 126 that were not — the gallery's first frame
and its stage on all 42 formula pages, in three attributes — passed every
assertion in both gates.

The whitelist gate therefore carries a coverage assertion as well: after the
batch the declared OLD string must have zero occurrences on the candidate. The
substitution is declared as the STRING, not as `alt="STRING"`, because the
gallery renders the same string in `alt`, `data-label` and `aria-label`, and an
attribute-shaped description hides the other two by construction.

The same defect is also stated as an invariant rather than as a substitution, so
that it outlives the declared pair list: ONE product still carries ONE alt,
counted per FILE across the whole site. That is the sentence the missing carrier
broke, and it is checkable without knowing which files the batch meant to edit.

WHAT IS DERIVED RATHER THAN RETYPED

  * the alt pairs come from tools/b2d_h5_apply.py, which parses the clause map
    out of functions.php — the same map the templates were edited from;
  * the noise masks come from tools/sf_masked_cmp.py, minus the two Cloudflare
    entries, because the blobs are DECODED before comparing instead of erased
    (batch H4e's lesson: a mask that erases content makes the gate blind to
    changes in that content);
  * the expected audience, isRelatedTo and additionalProperty values are read
    off the candidate pages themselves — the dosage <h1>, the visible tile and
    card links, the .sf-facts-mini row — so the gate checks the schema against
    the page rather than against a copy of the PHP's opinion;
  * the declared addition set is asserted, not described.

CROSS-CHECKS THAT A SCHEMA BATCH NEEDS AND A BYTE BATCH DOES NOT

  * every isRelatedTo URL must equal a URL the page visibly links to (the card
    grid on a formula page, the tile grid on a dosage page), in the same order;
  * every dosage additionalProperty value must equal the .sf-facts-mini cell
    the page displays;
  * the Cloudflare email blobs are counted on both sides before decoding, so
    decoding them cannot hide a removed address.

usage:
    b2d_h5_gate.py --baseline DIR --candidate DIR [--json OUT]
    b2d_h5_gate.py --baseline DIR --candidate DIR --aa DIR
    b2d_h5_gate.py --baseline DIR --candidate DIR --matrix
    b2d_h5_gate.py --baseline DIR --candidate DIR --negctl

exit 0 = every assertion held; 1 = at least one failed.
"""
import argparse
import collections
import glob
import html as htmlmod
import json
import os
import re
import shutil
import sys

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILE_DIR)
sys.path.insert(0, FILE_DIR)

import sf_masked_cmp            # noqa: E402  (the one mask set)
import b2d_h5_apply as app      # noqa: E402  (the one alt description)

BASE_DEFAULT = os.path.join(ROOT, '_backup', 'b2d-h5-baselines')
CAND_DEFAULT = os.path.join(ROOT, '_backup', 'b2d-h5-candidates')

PREFLIGHT_DIR = 'sinofresh-theme-preflight'
VER_TOKEN = 'ver=<TOKEN>'
# style.css did not move in this batch, so the version token does not either —
# which is exactly why provenance is asserted by content below and not by a
# version string. H5-0 bumped 2.10.59 -> 2.10.60; H5 inherits 2.10.60.
VER = '2.10.60'

LDJSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
LDJSON_ANY = re.compile(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', re.S)
LDJSON_CUT = '<script type="application/ld+json">LDJSON</script>'
CF_ATTR = re.compile(r'data-cfemail="([0-9a-f]+)"')
CF_LINK = re.compile(r"email-protection#([0-9a-f]+)")
# The theme's own stylesheet, not "every ver= on the page": a page also carries
# the enqueue versions of eight scripts and of core's own assets, and folding
# all of them would mask a real asset bump. This is the token RULES section B
# names as the cache's only key.
STYLE_VER = re.compile(
    r'(sinofresh-theme(?:-preflight)?/style\.css\?ver=)([0-9][0-9.]*)')

FACTS_CELL = re.compile(
    r'<span class="sf-facts-mini__value" data-label="([^"]+)">(.*?)</span>', re.S)
TILE_LINK = re.compile(r'sf-tile__media"><a href="([^"]+)"')
CARD_LINK = re.compile(r'<h3 class="sf-fcard__name"><a href="([^"]+)">')
MORE_HEADING = re.compile(r'More ([^<]{0,40}) Formulas')
H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
# A formula page's own dosage page, as the page itself states it: the middle
# crumb. Read off the page rather than derived from the post's taxonomy,
# because the claim being checked is that the schema agrees with what the
# visitor can see, and the breadcrumb is what the visitor sees.
CRUMB_FORM = re.compile(
    r'sf-breadcrumb__crumb--form"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')

KNOWS_ABOUT = [
    'Soft Chews', 'Tablets', 'Powders', 'Pastes', 'Drops', 'Liquids',
    'Fish Oil', 'Dental Chews',
    'Pet Supplement OEM/ODM Manufacturing', 'Private Label Pet Supplements',
]
DOSAGE_NAMES = ['MOQ', 'Lead time', 'Certifications', 'Packaging']
FORMULA_NAMES = ['Ingredients', 'Guaranteed Analysis', 'Standard Specs']
# data-label -> the name the schema must state (the visible label, not the
# machine one: the row prints "Packaging" over data-label="Packaging formats").
DOSAGE_LABEL = {'MOQ': 'MOQ', 'Lead time': 'Lead time',
                'Certifications': 'Certifications',
                'Packaging formats': 'Packaging'}

# The scale of the alt normalisation, asserted rather than counted after the
# fact: 75 header + 75 footer logos.
LOGO_TOTAL = 150

# The eight product-still strings, counted on the BASELINE with the closing
# quote as the boundary. The boundary is not cosmetic: the post-batch string
# begins with the pre-batch one, so an unbounded `old in text` counts every
# new occurrence as an old one too and the census reads 398/398 on any
# candidate, correct or not.
#
#   314  alt="..."         272 on the cards and the 56 template tiles,
#                          42 on the gallery's first frame (see COVERAGE)
#    42  data-label="..."  the gallery's first frame
#    42  aria-label="..."  the gallery stage, role="tabpanel"
#   ---
#   398
PRODUCT_TOTAL = 398

_DROPPED = {'cf_email_link', 'cf_email_attr'}
NOISE = [(p, r, n) for (p, r, n) in sf_masked_cmp.MASKS if n not in _DROPPED]
assert len(sf_masked_cmp.MASKS) - len(NOISE) == 2, \
    'expected to drop exactly the two Cloudflare masks, dropped %d' \
    % (len(sf_masked_cmp.MASKS) - len(NOISE))


# ---------------------------------------------------------------- helpers ---

def slug(path):
    s = path.strip('/').replace('/', '__')
    return s or 'root'


def attr_count(pages, value):
    """How many times `value` is an attribute value, on either side.

    Quote-bounded on purpose — see PRODUCT_TOTAL.
    """
    needle = value + '"'
    return sum(len(re.findall(re.escape(needle), t)) for t in pages.values())


def bare_count(pages, value):
    """How many times `value` appears at all, attribute or not."""
    return sum(t.count(value) for t in pages.values())


STALE = re.compile(r'%s(?!\s*—\s)')   # `old` NOT followed by the clause marker


def stale_hits(pages, old):
    """Occurrences of the pre-batch string that the batch failed to reach.

    `old in text` cannot answer this: the post-batch string BEGINS with the
    pre-batch one, so a plain count is non-zero on a correct candidate and the
    assertion has to be written as `== 0` on something that cannot be a prefix.
    A negative lookahead on the separator says exactly what is meant: the old
    string with no clause of its own after it.

    Attribute-agnostic on purpose. The batch declares the STRING, and the same
    string is carried by alt=, data-label= and aria-label=; a rule shaped like
    `alt="..."` would leave the other two behind and call it a pass.
    """
    pat = re.compile(re.escape(old) + r'(?!\s*—\s)')
    return sum(len(pat.findall(t)) for t in pages.values())


def cfd(hexstr):
    """Cloudflare's email obfuscation: first byte is the key, rest is XOR."""
    raw = bytes.fromhex(hexstr)
    if not raw:
        return ''
    key = raw[0]
    return ''.join(chr(c ^ key) for c in raw[1:])


def decode_emails(t):
    t = CF_ATTR.sub(lambda m: 'data-cfemail="' + cfd(m.group(1)) + '"', t)
    t = CF_LINK.sub(lambda m: 'email-protection#' + cfd(m.group(1)), t)
    return t


def clean(t):
    for pat, repl, _ in NOISE:
        t = pat.sub(repl, t)
    return t


def norm(t):
    return clean(decode_emails(t))


def fold_ver(t):
    return STYLE_VER.sub(lambda m: m.group(1) + VER_TOKEN, t)


def manifest(path):
    """path -> (code, bytes, sha256) from a fetch MANIFEST."""
    out = {}
    fn = os.path.join(path, 'MANIFEST.tsv')
    if not os.path.exists(fn):
        return out
    for ln in open(fn, encoding='utf-8'):
        if ln.startswith('#') or ln.startswith('path\t'):
            continue
        p = ln.rstrip('\n').split('\t')
        if len(p) >= 4:
            out[p[0]] = (p[1], int(p[2]), p[3])
    return out


def read_pages(d):
    return {os.path.basename(f)[:-5]: open(f, encoding='utf-8', errors='replace').read()
            for f in glob.glob(os.path.join(d, '*.html'))}


def ld_raw(t):
    return LDJSON.findall(t)


def ld_parsed(t):
    """[(raw, obj)] for every ld+json block, in document order."""
    out = []
    for raw in LDJSON.findall(t):
        try:
            out.append((raw, json.loads(raw)))
        except Exception as exc:
            out.append((raw, {'__parse_error__': str(exc)}))
    return out


def types_of(t):
    return [o.get('@type') for _, o in ld_parsed(t)]


class Report(object):
    """Assertions, with the detail clipped.

    A schema gate compares whole objects, so an unclipped failure message can
    be a page of JSON for one broken key — and the useful part is the path,
    not the value. Clipping keeps a failing run readable; the full evidence
    goes to --json.
    """

    CLIP = 260

    def __init__(self):
        self.fails = []
        self.passes = 0
        self.notes = collections.OrderedDict()

    def ok(self, label, cond, detail=''):
        if cond:
            self.passes += 1
        else:
            detail = str(detail)
            if len(detail) > self.CLIP:
                detail = detail[:self.CLIP] + ' …(%d more chars)' % (len(detail) - self.CLIP)
            self.fails.append('%s%s' % (label, (' — ' + detail) if detail else ''))
        return bool(cond)

    def eq(self, label, got, want):
        return self.ok(label, got == want, 'got %s want %s' % (str(got)[:200], str(want)[:200]))


def superset(base, cand, path='$', added=None, violations=None):
    """Deep compare: cand must contain base unchanged; extra keys are added.

    A list is NOT allowed to grow inside an existing key: a grown list is a
    change to that key, not an addition to it, and the batch's additions are
    all whole keys. Recording the reason separately from the rule keeps the
    failure message useful.
    """
    added = [] if added is None else added
    violations = [] if violations is None else violations
    if isinstance(base, dict):
        if not isinstance(cand, dict):
            violations.append('%s: type %s -> %s' % (path, type(base).__name__, type(cand).__name__))
            return added, violations
        for k in base:
            if k not in cand:
                violations.append('%s.%s: dropped' % (path, k))
                continue
            superset(base[k], cand[k], '%s.%s' % (path, k), added, violations)
        for k in cand:
            if k not in base:
                added.append('%s.%s' % (path, k))
        return added, violations
    if isinstance(base, list):
        if not isinstance(cand, list):
            violations.append('%s: list -> %s' % (path, type(cand).__name__))
            return added, violations
        if len(base) != len(cand):
            violations.append('%s: length %d -> %d' % (path, len(base), len(cand)))
        for i, (b, c) in enumerate(zip(base, cand)):
            superset(b, c, '%s[%d]' % (path, i), added, violations)
        return added, violations
    if base != cand:
        violations.append('%s: %r -> %r' % (path, base, cand))
    return added, violations


def page_inputs(t):
    """The facts the schema is checked AGAINST, read off the page itself."""
    facts = {}
    for label, cell in FACTS_CELL.findall(t):
        facts[label] = htmlmod.unescape(re.sub('<[^>]*>', '', cell).strip())
    return {
        'facts': facts,
        'tiles': TILE_LINK.findall(t),
        'cards': CARD_LINK.findall(t),
        'more': (MORE_HEADING.findall(t) or [''])[0],
        'h1': (H1.findall(t) or [''])[0],
        'crumb': CRUMB_FORM.findall(t),
        'canonical': (CANONICAL.findall(t) or [''])[0],
    }


def species_of(headline):
    """The species a headline names, via the clause after " for "."""
    headline = htmlmod.unescape(re.sub('<[^>]*>', '', headline))
    m = re.search(r'\bfor\s+(.+)$', headline, re.I)
    if not m:
        return []
    out = []
    for w in re.findall(r'\b(dogs?|cats?|puppies|kittens)\b', m.group(1), re.I):
        w = w.capitalize()
        w = {'Dog': 'Dogs', 'Cat': 'Cats', 'Puppy': 'Puppies', 'Kitten': 'Kittens'}.get(w, w)
        if w not in out:
            out.append(w)
    return out


IMG_TAG = re.compile(r'<img\b[^>]*>', re.I)
ATTR = re.compile(r'\b(src|alt)="([^"]*)"', re.I)
FORM_SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes',
              'drops', 'liquids', 'fish-oil', 'dental-chews']
PRODUCT_STILL = re.compile(r'^(%s)\.webp$' % '|'.join(FORM_SLUGS))


def form_labels(pages):
    """still filename -> the dosage label, read off the pages themselves.

    Derived rather than retyped: every dosage page's tile grid names seven of
    the eight forms in its own alt text, so the sixteen pages together state
    the slug-to-label mapping without the gate owning a copy of it. A file that
    gets two different labels is itself a finding, so the values are returned
    as lists and the caller asserts they are singletons.
    """
    out = collections.defaultdict(set)
    for t in pages.values():
        for tag in IMG_TAG.findall(t):
            a = dict(ATTR.findall(tag))
            f = a.get('src', '').rsplit('/', 1)[-1]
            if not PRODUCT_STILL.match(f):
                continue
            m = re.match(r'SINO FRESH (.+?) private label pet supplement product',
                         htmlmod.unescape(a.get('alt', '')))
            if m:
                out[f].add(m.group(1))
    return {f: sorted(v) for f, v in out.items()}


def still_alts(pages):
    """page -> file -> {every alt attached to that file ON that page}.

    The invariant this exists to state: within one page, ONE image file carries
    ONE alt. The same .webp is described by the card markup, by the seven
    sibling tiles in the eight dosage templates, and by the first frame of the
    detail page's gallery — three carriers, and the first build of this batch
    found two of them. The substitution census cannot express this on its own,
    because the carrier it missed was byte-identical to the baseline and so
    "already agreed" with it. Asking the question per (page, file) answers what
    the census cannot: do the carriers say the same thing?

    Deliberately per PAGE, not per site. A still is legitimately reused off the
    product pages with a different alt — the case-study posts and the /products/
    index describe their own context ("Private label dental chews
    manufacturing") — and that is not drift. What is drift is one page telling
    two stories about one file.
    """
    out = collections.defaultdict(lambda: collections.defaultdict(set))
    for k, t in pages.items():
        for tag in IMG_TAG.findall(t):
            attrs = dict(ATTR.findall(tag))
            src = attrs.get('src', '')
            if 'alt' not in attrs or not src:
                continue
            out[k][src.rsplit('/', 1)[-1]].add(htmlmod.unescape(attrs['alt']))
    return out


# ------------------------------------------------------------------ gates ---

def gate_sides(rep, base_dir, cand_dir, base, cand):
    mb, mc = manifest(base_dir), manifest(cand_dir)
    rep.eq('[0] baseline paths', len(mb), 75)
    rep.eq('[0] candidate paths', len(mc), 75)
    rep.eq('[0] the two sides fetched the same paths', sorted(mb), sorted(mc))
    bad = [(p, mb[p][0]) for p in mb if mb[p][0] != '200']
    rep.eq('[0] baseline all 200', bad, [])
    bad = [(p, mc[p][0]) for p in mc if mc[p][0] != '200']
    rep.eq('[0] candidate all 200', bad, [])

    short = [k for k, t in list(base.items()) + list(cand.items())
             if len(t) < 30000 or '</html>' not in t[-2000:]]
    rep.eq('[0] every page complete (no truncated capture)', short, [])
    rep.eq('[0] both dirs carry 75 pages', (len(base), len(cand)), (75, 75))

    bad = [k for k, t in list(base.items()) + list(cand.items())
           if PREFLIGHT_DIR not in t]
    rep.eq('[0] every page was served by the pre-flight copy', bad, [])

    # Provenance by CONTENT, because this batch does not move the version
    # token (no CSS change). The two assertions below are the whole claim that
    # the baseline capture predates the batch and the candidate capture is it.
    rep.eq('[0] baseline: the pre-batch logo alt', sum(t.count('alt="sinofresh"') for t in base.values()), LOGO_TOTAL)
    rep.eq('[0] baseline: no knowsAbout anywhere',
           sum(t.count('knowsAbout') for t in base.values()), 0)
    rep.eq('[0] candidate: the post-batch logo alt',
           sum(t.count('alt="SINO FRESH logo"') for t in cand.values()), LOGO_TOTAL)
    rep.eq('[0] candidate: no pre-batch logo alt left',
           sum(t.count('alt="sinofresh"') for t in cand.values()), 0)
    rep.eq('[0] candidate: knowsAbout on every page',
           sum(1 for t in cand.values() if 'knowsAbout' in t), 75)
    rep.eq('[0] both sides on ver %s' % VER,
           sorted({v for t in list(base.values()) + list(cand.values())
                   for _, v in STYLE_VER.findall(t)}), [VER])
    # Every enqueue token must be identical on both sides: this batch touches
    # no asset, so a moved script version would be a change nobody declared.
    # Comparing the sets (not the pages) keeps it cheap.
    def enqueue_tokens(pages):
        return sorted({m.group(1) for t in pages.values()
                       for m in re.finditer(r'\?ver=([0-9][0-9.]*)', t)})
    rep.eq('[0] the enqueue token set is the same on both sides',
           enqueue_tokens(base), enqueue_tokens(cand))
    rep.notes['sides'] = {'baseline_bytes': sum(len(t) for t in base.values()),
                          'candidate_bytes': sum(len(t) for t in cand.values()),
                          'enqueue_tokens': enqueue_tokens(base)}


def gate_jsonld(rep, base, cand):
    """Semantic gate + the asserted declaration set."""
    block_counts, type_mismatch, violations = {}, [], []
    added_paths = collections.Counter()
    for k in sorted(base):
        bb, cc = ld_parsed(base[k]), ld_parsed(cand[k])
        block_counts[k] = (len(bb), len(cc))
        if len(bb) != len(cc):
            violations.append('%s: %d ld+json blocks -> %d' % (k, len(bb), len(cc)))
            continue
        tb = [o.get('@type') for _, o in bb]
        tc = [o.get('@type') for _, o in cc]
        if tb != tc:
            type_mismatch.append('%s: %s -> %s' % (k, tb, tc))
            continue
        for i, ((_, ob), (_, oc)) in enumerate(zip(bb, cc)):
            if '__parse_error__' in oc:
                violations.append('%s block %d: candidate does not parse (%s)'
                                  % (k, i, oc['__parse_error__']))
                continue
            # Path roots are the @type, not the block index: the same block
            # sits at a different index on different templates (a formula page
            # leads with FAQPage, a plain page with BreadcrumbList), so an
            # index-rooted path would make one property look like several and
            # the declared-set assertion could never be written down.
            root = ob.get('@type') if isinstance(ob, dict) else 'block%d' % i
            a, v = superset(ob, oc, '$%s' % root)
            for p in a:
                added_paths[p] += 1
            for msg in v:
                violations.append('%s block %d: %s' % (k, i, msg))

    rep.eq('[1] ld+json block count identical on all 75 pages',
           [k for k in block_counts if block_counts[k][0] != block_counts[k][1]], [])
    rep.eq('[1] the @type sequence identical on all 75 pages', type_mismatch, [])
    rep.eq('[1] no key changed and no key dropped, anywhere', violations[:12], [])

    # The declared change set. Anything added that is not on this list is a
    # failure even though the rule above would allow it: an undeclared schema
    # property is exactly the kind of drift this batch is supposed to prevent.
    declared = {
        '$Organization.knowsAbout': 75,
        '$Product.additionalProperty': 16,   # the sixteen dosage pages
        '$Product.audience': None,           # asserted per page in gate 3
        '$Product.isRelatedTo': 58,
    }
    seen = sorted(added_paths)
    rep.eq('[1] the added key paths are exactly the declared ones',
           seen, sorted(declared))
    rep.eq('[1] knowsAbout added on 75 pages',
           added_paths.get('$Organization.knowsAbout'), 75)
    rep.eq('[1] additionalProperty added on the 16 dosage pages',
           added_paths.get('$Product.additionalProperty'), 16)
    rep.eq('[1] isRelatedTo added on all 58 Product pages',
           added_paths.get('$Product.isRelatedTo'), 58)
    rep.eq('[1] offers added on no page (the tier table is empty)',
           added_paths.get('$Product.offers'), None)
    rep.eq('[1] offers appears on no page at all',
           sum(1 for t in cand.values() if '"offers"' in t), 0)

    # no page lost a block, and no page gained an unexpected one
    rep.eq('[1] every page still carries its Organization block',
           sum(1 for t in cand.values() if '"@type":"Organization"' in t
               or '"@type": "Organization"' in t), 75)
    return added_paths


def gate_whitelist(rep, base, cand):
    """Rendered HTML: cut the schema out, invert the declared alt edit, compare."""
    pairs = app.alt_pairs()
    pair_counts = collections.Counter()
    diff_pages = []
    cut_mismatch = []
    cf_counts = []
    census = collections.OrderedDict()

    # ----------------------------------------------------------------------
    # THE COVERAGE RULE — the half that a displacement gate cannot express.
    #
    # "Every declared substitution happened" is satisfied by a build that
    # substituted in 272 of 314 places, because the 42 it forgot are
    # byte-identical to the baseline and therefore agree with it. The
    # inversion below is blind to them by construction: it rewrites the NEW
    # string back to the OLD one and then finds the untouched pages equal.
    #
    # So the census asserts the other half as well: after the batch the OLD
    # string is GONE. That is the assertion that fails on the build this gate
    # was first run against, and it is the reason the gate is a pair.
    # ----------------------------------------------------------------------
    logo_old = bare_count(base, app.LOGO_OLD)
    logo_new = bare_count(cand, app.LOGO_NEW)
    logo_left = stale_hits(cand, app.LOGO_OLD)
    rep.eq('[2] logo alt: pre-batch count on the baseline', logo_old, LOGO_TOTAL)
    rep.eq('[2] logo alt: post-batch count on the candidate', logo_new, LOGO_TOTAL)
    rep.eq('[2] logo alt: none of the pre-batch string survives', logo_left, 0)

    tot_b = tot_c = tot_left = tot_bare_left = 0
    for old, new in pairs:
        b = attr_count(base, old)
        c = attr_count(cand, new)
        left = attr_count(cand, old)
        bare_left = stale_hits(cand, old)
        tot_b += b
        tot_c += c
        tot_left += left
        tot_bare_left += bare_left
        name = old.split(' private label')[0]
        census[name] = {'baseline_old': b, 'candidate_new': c,
                        'candidate_old_attr': left, 'candidate_old_bare': bare_left}
        rep.ok('[2] %s: the declared string existed before the batch' % name,
               b > 0, 'count %d' % b)
        rep.ok('[2] %s: replaced everywhere, nothing left behind' % name,
               c == b and left == 0 and bare_left == 0,
               'baseline %d -> new %d, old still present %d attr / %d bare'
               % (b, c, left, bare_left))
    rep.eq('[2] the eight product strings: the declared 398 occurrences on the baseline',
           tot_b, PRODUCT_TOTAL)
    rep.eq('[2] the eight product strings: every occurrence replaced', tot_c, tot_b)
    rep.eq('[2] the eight product strings: zero occurrences left behind', tot_left, 0)
    rep.eq('[2] COVERAGE — no pre-batch product string survives anywhere in the HTML',
           tot_bare_left, 0)

    for k in sorted(base):
        b_blocks, c_blocks = ld_raw(base[k]), ld_raw(cand[k])
        if len(b_blocks) != len(c_blocks):
            cut_mismatch.append('%s: %d -> %d blocks' % (k, len(b_blocks), len(c_blocks)))
            continue
        cf_counts.append((k, len(CF_ATTR.findall(base[k])), len(CF_ATTR.findall(cand[k])),
                          len(CF_LINK.findall(base[k])), len(CF_LINK.findall(cand[k]))))

        b_cut = LDJSON_ANY.sub(LDJSON_CUT, base[k])
        c_cut = LDJSON_ANY.sub(LDJSON_CUT, cand[k])
        # Invert the declared substitutions on the candidate. Attribute-
        # agnostic: the thing being declared is the STRING, and the gallery
        # renders it in three attributes (alt, data-label, aria-label), so an
        # `alt="..."`-shaped rule would silently leave two of them behind.
        c_cut, n = re.subn(re.escape(app.LOGO_NEW), app.LOGO_OLD, c_cut)
        pair_counts[app.LOGO_NEW] += n
        for old, new in pairs:
            c_cut, n = re.subn(re.escape(new), old, c_cut)
            pair_counts[new] += n
        if norm(fold_ver(b_cut)) != norm(fold_ver(c_cut)):
            diff_pages.append(k)

    rep.eq('[2] the ld+json blocks cut out cleanly on both sides', cut_mismatch, [])
    rep.eq('[2] undo_declared(candidate) == baseline, page by page', diff_pages, [])

    # Decoding the Cloudflare blobs must not hide an added or removed address:
    # the counts are compared BEFORE decoding, on both sides.
    bad = ['%s attr %d->%d link %d->%d' % row for row in cf_counts
           if row[1] != row[2] or row[3] != row[4]]
    rep.eq('[2] the obfuscated email blob counts match before decoding', bad, [])

    rep.eq('[2] every declared substitution was applied',
           sorted(pair_counts), sorted([app.LOGO_NEW] + [n for _, n in pairs]))
    rep.eq('[2] logo inverted 150 times', pair_counts[app.LOGO_NEW], LOGO_TOTAL)
    for old, new in pairs:
        b = attr_count(base, old)
        rep.eq('[2] %s inverted %d times' % (old[:32], b), pair_counts[new], b)

    rep.notes['alt_census'] = census
    rep.notes['alt_totals'] = {'baseline_old': tot_b, 'candidate_new': tot_c,
                               'candidate_old': tot_left}
    rep.notes['logo'] = {'old': logo_old, 'new': logo_new, 'left': logo_left}
    return census


def gate_properties(rep, base, cand):
    """The properties, checked against the page each one describes.

    Every expectation is read OFF a candidate page rather than from a second
    copy of the PHP's opinion, so the gate fails when the schema and the page
    disagree instead of when they agree with each other and both disagree with
    the site. The three anchors used:

      * the dosage page's own .sf-facts-mini band  -> additionalProperty
      * the formula page's breadcrumb form crumb   -> which dosage page states
                                                      this product's species
      * the tile grid / card grid hrefs            -> isRelatedTo, in order
    """
    prod_pages, dosage_pages, formula_pages = [], [], []
    ka_bad, prop_bad, rel_bad, aud_bad, crumb_bad = [], [], [], [], []
    prop_ok = rel_ok = aud_ok = 0
    aud_expected, aud_seen = {}, {}

    # Pass 1 — the species each dosage page states about itself. Keyed by the
    # page's own slug so a formula page can be checked against the exact page
    # its breadcrumb points at.
    #
    # The marker is the four-row .sf-facts-mini band, NOT the tile grid: the
    # grid is also rendered by the three index pages (/, /zh/, /products/) as
    # a navigation block, so a tile-based test counts 19 pages and calls three
    # of them products. The band exists on exactly the sixteen.
    species_by_page = {}
    tiled = []
    for k, t in cand.items():
        inp = page_inputs(t)
        if inp['tiles']:
            tiled.append(k)
        if inp['facts']:
            species_by_page[k] = species_of(inp['h1'])
            dosage_pages.append(k)
    rep.eq('[3] the pages with a tile grid: the 16 dosage pages + the 3 indexes',
           sorted(tiled), sorted(list(species_by_page) + ['products', 'root', 'zh']))
    rep.eq('[3] the facts band marks exactly the 16 dosage pages',
           len(species_by_page), 16)

    for k in sorted(cand):
        t = cand[k]
        inp = page_inputs(t)
        objs = [o for _, o in ld_parsed(t)]
        prod = next((o for o in objs if o.get('@type') == 'Product'), None)
        org = next((o for o in objs if o.get('@type') == 'Organization'), None)

        # F. knowsAbout, on every page, the ten declared topics
        if org is not None and org.get('knowsAbout') != KNOWS_ABOUT:
            ka_bad.append('%s: %r' % (k, org.get('knowsAbout')))

        is_dosage = bool(inp['facts'])
        is_formula = bool(inp['crumb'])
        if is_formula:
            formula_pages.append(k)
        if prod is not None:
            prod_pages.append(k)

        # The species expectation. On a dosage page the page states it in its
        # own h1. On a formula page the same claim belongs to the dosage page
        # the breadcrumb links to, so that page's h1 is the expectation —
        # the form's own page, found by the link the visitor can click, not
        # by re-deriving the taxonomy in the gate.
        if is_dosage:
            expect = species_by_page[k]
        elif is_formula:
            crumb_url, crumb_text = inp['crumb'][0]
            expect = species_by_page.get(slug(crumb_url), [])
            if slug(crumb_url) not in species_by_page:
                crumb_bad.append('%s: breadcrumb form crumb %r is not a page'
                                 % (k, crumb_url))
            elif htmlmod.unescape(re.sub('<[^>]*>', '', crumb_text)).strip() != inp['more']:
                crumb_bad.append('%s: crumb %r != More-heading %r'
                                 % (k, crumb_text, inp['more']))
        else:
            expect = []

        if prod is not None:
            got = [a.get('audienceType') for a in prod.get('audience', [])] \
                if 'audience' in prod else []
            aud_expected[k] = expect
            aud_seen[k] = got
            if got != expect:
                aud_bad.append('%s: audience %r != the page says %r' % (k, got, expect))
            elif got:
                aud_ok += 1

        # additionalProperty against the page's own band
        if prod is not None:
            props = prod.get('additionalProperty')
            if is_dosage:
                want = [{'@type': 'PropertyValue',
                         'name': DOSAGE_LABEL.get(label, label),
                         'value': value}
                        for label, value in inp['facts'].items()]
                # the band's own order, which is the order PHP reads it in
                order = ['MOQ', 'Lead time', 'Certifications', 'Packaging formats']
                want = [w for lbl in order for w in want
                        if w['name'] == DOSAGE_LABEL.get(lbl, lbl)]
                if props != want:
                    prop_bad.append('%s: additionalProperty != the visible band' % k)
                elif [p['name'] for p in props] != DOSAGE_NAMES:
                    prop_bad.append('%s: names %r' % (k, [p['name'] for p in props]))
                else:
                    prop_ok += 1
            elif is_formula:
                names = [p['name'] for p in props] if props else []
                if names != FORMULA_NAMES:
                    prop_bad.append('%s: formula names %r' % (k, names))
                else:
                    prop_ok += 1
            else:
                if props is not None:
                    prop_bad.append('%s: not a Product page but has additionalProperty' % k)

        # isRelatedTo must equal what the page visibly links to, in order
        if prod is None:
            continue
        if 'isRelatedTo' not in prod:
            if is_dosage or is_formula:
                rel_bad.append('%s: no isRelatedTo' % k)
            continue
        urls = [r.get('url') for r in prod['isRelatedTo']]
        origin = ''
        m = re.match(r'(https?://[^/]+)', inp['canonical'])
        if m:
            origin = m.group(1)
        if is_dosage:
            want_urls = [(origin + u) if u.startswith('/') else u for u in inp['tiles']]
        elif is_formula:
            want_urls = inp['cards']
        else:
            want_urls = []
        if urls != want_urls:
            rel_bad.append('%s: isRelatedTo %r != the page links %r' % (k, urls, want_urls))
        else:
            rel_ok += 1

    rep.eq('[3] Product pages: 58', len(prod_pages), 58)
    rep.eq('[3] dosage pages: 16', len(dosage_pages), 16)
    rep.eq('[3] formula pages: 42', len(formula_pages), 42)

    # D. One still, one alt — asserted per (page, file) rather than per
    # substitution, so it holds even if the declared pair list above goes
    # stale. This is the assertion that fails on the build the gate was first
    # run against: 42 formula pages, each describing its own .webp two ways.
    declared = dict(app.alt_pairs())          # pre-batch string -> post-batch
    labels = form_labels(cand)
    rep.eq('[3] the dosage label of each still is one thing, site-wide',
           sorted(f for f, v in labels.items() if len(v) != 1), [])
    rep.eq('[3] a label is stated for all eight stills',
           sorted(labels), sorted(f + '.webp' for f in FORM_SLUGS))
    label_of = {f: v[0] for f, v in labels.items() if len(v) == 1}
    alts = still_alts(cand)
    conflicts, not_declared = [], []
    for k, files in sorted(alts.items()):
        for f, vals in sorted(files.items()):
            if not PRODUCT_STILL.match(f):
                continue
            if len(vals) > 1:
                conflicts.append('%s: %s -> %r' % (k, f, sorted(vals)))
            # The positive half, on the product pages only: the still must say
            # the declared thing, not merely agree with itself. Off the product
            # pages a still is legitimately reused with its own context's alt.
            new = declared.get('SINO FRESH %s private label pet supplement product'
                               % label_of.get(f, ''))
            if (k in dosage_pages or k in formula_pages) and new and vals != {new}:
                not_declared.append('%s: %s -> %r' % (k, f, sorted(vals)))
    rep.eq('[3] CARRIERS — no page describes one image two different ways',
           conflicts[:8], [])
    rep.eq('[3] product pages state the declared alt for every still',
           not_declared[:8], [])
    rep.notes['still_conflicts'] = conflicts
    rep.notes['still_not_declared'] = not_declared
    rep.notes['form_labels'] = labels
    rep.notes['still_pages'] = len([1 for files in alts.values()
                                    if any(PRODUCT_STILL.match(f) for f in files)])

    rep.eq('[3] knowsAbout is the ten declared topics on all 75 pages', ka_bad[:6], [])
    rep.eq('[3] the breadcrumb form crumb is a page and matches the More heading',
           crumb_bad[:6], [])
    rep.eq('[3] additionalProperty matches the page in every case', prop_bad[:8], [])
    rep.eq('[3] additionalProperty pages accounted for', prop_ok, 58)
    rep.eq('[3] audience matches what the page states', aud_bad[:8], [])
    rep.eq('[3] isRelatedTo matches the page links, in order', rel_bad[:8], [])
    rep.eq('[3] isRelatedTo present on all 58 Product pages', rel_ok, 58)
    rep.eq('[3] audience present exactly where the page names a species',
           sorted(aud_seen), sorted(aud_expected))
    rep.eq('[3] audience pages', aud_ok, sum(1 for k in aud_expected if aud_expected[k]))

    rep.notes['audience'] = {'pages': {k: aud_seen[k] for k in sorted(aud_seen)
                                       if aud_seen[k]},
                             'expected_pages': sum(1 for k in aud_expected
                                                   if aud_expected[k])}
    rep.notes['isRelatedTo_pages'] = rel_ok
    rep.notes['product_pages'] = len(prod_pages)
    rep.notes['dosage_pages'] = len(dosage_pages)
    rep.notes['formula_pages'] = len(formula_pages)
    return aud_seen


def load(d):
    pages = read_pages(d)
    return pages


def run(base_dir, cand_dir, json_out=None, quiet=False):
    rep = Report()
    base, cand = load(base_dir), load(cand_dir)
    gate_sides(rep, base_dir, cand_dir, base, cand)
    if not rep.fails:
        gate_jsonld(rep, base, cand)
        gate_whitelist(rep, base, cand)
        gate_properties(rep, base, cand)
    else:
        rep.ok('later gates skipped: capture integrity did not hold', False)

    verdict = 'PASS' if not rep.fails else 'FAIL'
    if not quiet:
        print('=' * 78)
        print('H5 GATE: %s — %d assertions passed, %d failed' % (verdict, rep.passes, len(rep.fails)))
        for f in rep.fails:
            print('  FAIL %s' % f)
        print('  notes: %s' % json.dumps(rep.notes, ensure_ascii=False)[:900])
        print('=' * 78)
    if json_out:
        with open(json_out, 'w', encoding='utf-8') as fh:
            json.dump({'verdict': verdict, 'passed': rep.passes,
                       'failed': rep.fails, 'notes': rep.notes}, fh,
                      ensure_ascii=False, indent=1)
    return verdict, rep


# ------------------------------------------------------- A/A, matrix, neg ---

def work_copy(src, dst):
    """A mutable copy of a capture, built without a recursive delete.

    Two constraints shaped this: the scratch copy has to be reset between
    mutations, and this project's shell guard refuses a bulk recursive delete
    (>50 paths in a turn), so `copytree` + `rmtree` per mutation does not run
    at all. Instead the directory is populated once and each mutation only
    overwrites the ONE file it targets, restoring it from the source first.
    Cheaper than a reset as well: 76 copies for the whole run instead of 76
    per mutation.
    """
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(src, '*')):
        shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
    return dst


class Scratch(object):
    """A scratch copy of the candidate that remembers what it has touched.

    Every mutation has to be UNDONE before the next one, and undoing only the
    file the next mutation targets is not enough: the previous mutation is
    still in place in its own file and the gate fails on that instead. The
    first build of this runner reported a control as passing while its message
    named an earlier, unrelated file — a control whose stated cause is not its
    actual cause is not a control. So the reset covers every file this run has
    written, not just the next target.
    """

    def __init__(self, src, dst):
        self.src = src
        self.dir = work_copy(src, dst)
        self.touched = set()

    def reset(self):
        for f in self.touched:
            shutil.copy2(os.path.join(self.src, f), os.path.join(self.dir, f))
        self.touched.clear()

    def edit(self, fname, fn):
        """Apply fn to one page's text. Returns the original text."""
        with open(os.path.join(self.dir, fname), encoding='utf-8', errors='replace') as fh:
            original = fh.read()
        mutated = fn(original)
        if mutated != original:
            with open(os.path.join(self.dir, fname), 'w', encoding='utf-8') as fh:
                fh.write(mutated)
            self.touched.add(fname)
        return original

    def edit_all(self, fn):
        """Apply fn to every captured page (used by the marker control)."""
        for f in glob.glob(os.path.join(self.dir, '*.html')):
            name = os.path.basename(f)
            with open(f, encoding='utf-8', errors='replace') as fh:
                t = fh.read()
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(fn(t))
            self.touched.add(name)

    def run(self, baseline, quiet=True):
        return run(baseline, self.dir, quiet=quiet)


def aa(args):
    """Two independent captures of the same candidate must agree."""
    c1, c2 = load(args.candidate), load(args.aa)
    rep = Report()
    rep.eq('A/A: same page set', sorted(c1), sorted(c2))
    diff = [k for k in c1 if norm(fold_ver(c1[k])) != norm(fold_ver(c2[k]))]
    rep.eq('A/A: the two candidate captures are byte-identical after masking', diff, [])
    pairs = app.alt_pairs()
    cans = []
    for pages in (c1, c2):
        cans.append((
            bare_count(pages, app.LOGO_NEW),
            tuple(attr_count(pages, n) for _, n in pairs),
        ))
    rep.eq('A/A: the declared census is reproduced identically', cans[0], cans[1])
    print('A/A: %s — %d passed, %d failed' % ('PASS' if not rep.fails else 'FAIL',
                                              rep.passes, len(rep.fails)))
    for f in rep.fails:
        print('  FAIL %s' % f)
    return 0 if not rep.fails else 1


def defect_gallery(t):
    """The exact shape this batch first shipped, reproduced on a captured page.

    The gallery's three carriers — the stage's aria-label, the first frame's
    data-label and that frame's img alt — revert to the bare pre-batch string
    while the card above them keeps the clause. Nothing here is an added or
    changed schema key, and every reverted occurrence is byte-identical to the
    baseline, so this is invisible to both original gates by construction. The
    matrix and the named controls both use it: if it ever stops being caught,
    the coverage assertion has quietly been dropped.
    """
    i = t.find('sf-gallery__stage')
    if i < 0:
        return t
    head, tail = t[:i], t[i:]
    for old, new in app.alt_pairs():
        tail = tail.replace(new, old, 3)
    return head + tail


MUTATIONS = [
    ('knowsAbout dropped', lambda t: t.replace('"knowsAbout"', '"xKnowsAbout"', 1)),
    ('knowsAbout shortened', lambda t: t.replace('"Private Label Pet Supplements"', '"Private Label"', 1)),
    ('additionalProperty dropped',
     lambda t: t.replace('additionalProperty', 'xadditionalProperty', 1) if 'additionalProperty' in t else t),
    ('additionalProperty value changed',
     lambda t: t.replace('"value":"FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC"',
                         '"value":"FDA, cGMP"', 1)),
    ('an undeclared key added', lambda t: t.replace('"category":"Pet Supplements"',
                                                    '"category":"Pet Supplements","sku":"X"', 1)),
    ('audience dropped', lambda t: t.replace('"audience":', '"xaudience":', 1) if '"audience"' in t else t),
    ('audienceType changed', lambda t: t.replace('"audienceType":"Cats"', '"audienceType":"Fish"', 1)),
    ('isRelatedTo shortened', lambda t: re.sub(r'(isRelatedTo":\[\{"@type":"Product".*?)\},\{"@type":"Product"', r'\1', t, count=1, flags=re.S)),
    ('isRelatedTo reordered', lambda t: re.sub(r'("isRelatedTo":\[)(.*?)(\])', lambda m: m.group(1) + ','.join(reversed(m.group(2).split('},{'))) + m.group(3), t, count=1, flags=re.S)),
    ('logo alt reverted on 3 pages', lambda t: t.replace(app.LOGO_NEW, app.LOGO_OLD, 2) if app.LOGO_NEW in t else t),
    ('one form clause reverted', lambda t: t.replace(app.alt_pairs()[5][1], app.alt_pairs()[5][0], 1)),
    ('an unrelated alt changed', lambda t: t.replace(
        'Soft Chews production line at the SINO FRESH GMP facility in Linyi, China',
        'CHANGED', 1)),
    # The next two isolate the coverage rule: the byte gate's inversion
    # rewrites NEW back to OLD and would find them equal to the baseline, so
    # only "the old string is gone" catches them. If these two ever stop being
    # caught, the gate has quietly become a displacement check again.
    ('the gallery aria-label left un-normalised',
     lambda t: t.replace('aria-label="' + app.alt_pairs()[6][1] + '"',
                         'aria-label="' + app.alt_pairs()[6][0] + '"', 1)),
    ('the gallery data-label left un-normalised',
     lambda t: t.replace('data-label="' + app.alt_pairs()[6][1] + '"',
                         'data-label="' + app.alt_pairs()[6][0] + '"', 1)),
    ('the gallery frame and stage left un-normalised', defect_gallery),
    ('an ld+json block removed', lambda t: LDJSON_ANY.sub('', t, count=1) if LDJSON_ANY.search(t) else t),
    ('the printed heading edited', lambda t: t.replace('</h1>', '</h2>', 1)),
]


def matrix(args):
    """Mutate a copy of the candidate and require the gate to catch it.

    Each mutation is applied to ONE page per page class that carries the thing
    being mutated, so a mutation that only exists on some pages still gets a
    page to land on. Every page the run has touched is reset before each
    variant, otherwise a variant's failure can be caused by the previous
    variant's mutation and the named cause is a fiction.
    """
    caught, missed = [], []
    scratch = Scratch(args.candidate, os.path.join(ROOT, '_backup', 'b2d-h5-matrix'))
    variants = {
        'dosage': 'products__soft-chews.html',
        'formula': 'formulas__joint-support-soft-chews.html',
        'plain': 'about.html',
    }
    for name, fn in MUTATIONS:
        ok_any = False
        for cls, fname in variants.items():
            scratch.reset()
            original = scratch.edit(fname, fn)
            if not scratch.touched:
                continue
            verdict, rep = scratch.run(args.baseline)
            if verdict == 'FAIL':
                ok_any = True
                caught.append((name, cls, rep.fails[0][:96]))
            else:
                missed.append((name, cls))
        if not ok_any and not any(m[0] == name for m in missed):
            missed.append((name, 'ANCHOR-MISS'))
    scratch.reset()
    print('MATRIX: %d mutations, %d caught, %d missed'
          % (len(MUTATIONS), len(set(n for n, _, _ in caught)), len(missed)))
    for name, cls, why in caught:
        print('  CAUGHT  %-40s (%s) %s' % (name, cls, why))
    for name, cls in missed:
        print('  MISSED  %-40s (%s)' % (name, cls))
    return 0 if not missed else 1


def negcontrol(args):
    """Named controls that must FAIL — a gate that only ever passes proves nothing."""
    results = []
    scratch = Scratch(args.candidate, os.path.join(ROOT, '_backup', 'b2d-h5-negctl'))

    def control(label, fname, fn, all_pages=False, expect_edit=True):
        scratch.reset()
        if all_pages:
            scratch.edit_all(fn)
        else:
            scratch.edit(fname, fn)
        # An anchor that does not exist makes the control a no-op, and a no-op
        # control passes by proving nothing. Refuse to record it.
        if expect_edit and not scratch.touched:
            raise SystemExit('control %r changed nothing — the anchor is wrong'
                             % label)
        verdict, rep = scratch.run(args.baseline)
        results.append((label, verdict, rep.fails[0][:96] if rep.fails else ''))

    control('candidate as-is (must PASS)', 'about.html', lambda t: t,
            expect_edit=False)
    control('a truncated capture (must FAIL)', 'about.html', lambda t: t[:len(t) // 2])
    control('a page keeps the pre-batch logo alt (must FAIL)', 'contact.html',
            lambda t: t.replace(app.LOGO_NEW, app.LOGO_OLD))
    # The anchor is `"category":"Pet Supplements"`, which lives in the Product
    # block and therefore only on the pages that have one — a dosage page. The
    # first build aimed this control at a plain page, changed nothing, and the
    # control "passed" by producing no failure at all.
    control('an undeclared schema key (must FAIL)', 'products__soft-chews.html',
            lambda t: t.replace('"category":"Pet Supplements"',
                                '"category":"Pet Supplements","sku":"X"', 1))
    control('one non-alt attribute left stale (must FAIL)',
            'formulas__joint-support-soft-chews.html',
            lambda t: t.replace('aria-label="' + app.alt_pairs()[6][1] + '"',
                                'aria-label="' + app.alt_pairs()[6][0] + '"', 1))
    # The whole defect, replayed: all three carriers of the gallery's string
    # reverted at once. This is the control that says the coverage rule is
    # still load-bearing and not just decoration next to the inversion.
    control('the gallery frame and stage left un-normalised (must FAIL)',
            'formulas__joint-support-soft-chews.html', defect_gallery)
    control('captures with no pre-flight marker (must FAIL)', None,
            lambda t: t.replace(PREFLIGHT_DIR, 'sinofresh-theme'), all_pages=True)

    scratch.reset()
    ok = 0
    for label, verdict, why in results:
        want = 'PASS' if 'must PASS' in label else 'FAIL'
        good = verdict == want
        ok += good
        print('  %-6s %-52s %s' % ('ok' if good else 'WRONG', label, why))
    print('NEGCTL: %d/%d behaved as required' % (ok, len(results)))
    return 0 if ok == len(results) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default=BASE_DEFAULT)
    ap.add_argument('--candidate', default=CAND_DEFAULT)
    ap.add_argument('--json', default=None)
    ap.add_argument('--aa', default=None, help='a second candidate capture to compare')
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--negctl', action='store_true')
    args = ap.parse_args()

    if args.aa:
        return aa(args)
    if args.matrix:
        return matrix(args)
    if args.negctl:
        return negcontrol(args)
    verdict, _ = run(args.baseline, args.candidate, args.json)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
