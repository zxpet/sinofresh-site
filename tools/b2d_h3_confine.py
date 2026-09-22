#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H3 gate — the confined-addition proof, the page set, and the matrix.

H3 adds two bands and one structured-data block to a formula detail page. The
proof is the mirror image of H2b2's deletion proof:

    the candidate must equal the baseline with exactly three declared runs
    inserted and exactly one version token moved, on exactly the pages that
    carry them, and be unchanged elsewhere.

Three declared runs:

  A  the content band          inserted immediately before the FAQ's lead comment
  B  the sampling band         inserted immediately before the related-formulas comment
  C  the HowTo JSON-LD script  inserted immediately after the FAQPage script

One declared token move: style.css?ver=2.10.56 -> 2.10.57, on all 75 pages,
because the enqueue version is site-wide. That is why the comparison folds the
token, and why the fold must be shown to be *exactly* the declared move: the
gate asserts the full asset/version inventory is unchanged apart from it.

The three runs are pinned as literals, but not on trust: gate [3] asserts the
band bytes inside runs A and B are byte-identical to what the shipped renderers
produce (rendered locally from the theme's own source), and that run C carries
the four steps the same source declares. So a pinned literal cannot drift from
the code — only the whitespace wrapper and the template's own comment around
them are taken from the capture.

Run C is *located* by parsing, not by matching: a translated page's JSON-LD is
re-serialized pretty-printed on the way out, so a literal `"@type":"HowTo"`
match finds only the 21 English detail pages and silently ignores the 21
translated ones. Every JSON-LD lookup below reads @type out of the parsed
block; see ld_types().

usage:
    b2d_h3_confine.py --base DIR --cand DIR [--theme DIR] [--served FILE] [--json OUT]
    b2d_h3_confine.py --base DIR --cand DIR --theme DIR --matrix
    b2d_h3_confine.py --base DIR --cand DIR --served FILE --negctl
    b2d_h3_confine.py --base DIR --cand DIR --pin-run A|B|C
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sf_masked_cmp import masked                                     # noqa: E402

# ---------------------------------------------------------------- constants --
STYLE_OLD = 'style.css?ver=2.10.56'
STYLE_NEW = 'style.css?ver=2.10.57'
BASE_COMMIT = '3b9fc23'

VER = re.compile(r'\?ver=[\w.\-]+')
ASSET = re.compile(r'/([\w.\-]+\.(?:css|js))\?ver=([\w.\-]+)')
LDJSON = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)

DETAIL = re.compile(r'^(zh__)?formulas__[\w\-]+\.html$')

CONTENT_OPEN = '<section class="sf-fdetail-content">'
SAMPLING_OPEN = '<section class="sf-sampling">'
ACTIVES_OPEN = '<section class="sf-fdetail-actives">'
FAQ_OPEN = '<section class="wp-block-group sf-fdetail sf-fdetail-faq'
MORE_OPEN = '<section class="wp-block-group sf-fdetail-more'

# What runs A and B are anchored to. Not the <section> tags: the template's own
# comments sit above those tags, the block renderer strips the `<!-- wp:* -->`
# delimiters but keeps plain comments, and the bands went in above the comments.
# Anchoring on the section tag places both bands one comment too late.
FAQ_COMMENT = '<!-- Batch C: the formula FAQ.'
MORE_COMMENT = '<!-- Block 4: related formulas -->'
HOWTO_TYPE = 'HowTo'
FAQ_TYPE = 'FAQPage'

# The three declared insertions. The bands are checked against the renderers;
# the wrapper around them is what the block template contributes.
RUN_A = ('<!-- Batch H3: the detailed content area. It sits after the three data bands\n'
         '     and before the FAQ so the card-white reading surface runs unbroken from\n'
         '     the Specification cards to the end of the FAQ, each band separated by its\n'
         '     own heading. The band is a shortcode because it has to vanish completely\n'
         '     on a record whose fields are still empty. -->\n'
         '\n%CONTENT%\n\n')
RUN_B = ('<!-- Batch H3: how sampling works. Static copy, so unlike the content band it\n'
         '     always renders; it closes the white reading surface after the FAQ, and the\n'
         '     bg-light related-formulas grid below it opens the light tail before the\n'
         '     green CTA. Same shortcode the HowTo schema reads its steps from. -->\n'
         '\n%SAMPLING%\n\n\n')
RUN_C = '\n<script type="application/ld+json">%HOWTO%</script>\n'

FROZEN = ['assets/js/formulas.js', 'assets/js/basket.js',
          'inc/config-pdf.php', 'inc/formula-pools.php']

EXPECT_TITLES = ['Submit Inquiry', 'Confirm Details', 'Sampling & Quality Check', 'Ship & Evaluate']

# The four groups the content band can render, in the order the renderer
# declares them. How many of them actually appear is data, not code — today
# exactly one does, because Storage is a constant line and the other fields
# are empty on all 21 records.
GROUP_LABELS = ['Recommended For', 'Use Cases', "Who It's For",
                'Packaging &amp; Specifications']


def read(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def pages(d):
    return sorted(n for n in os.listdir(d) if n.endswith('.html'))


def is_detail(name):
    return bool(DETAIL.match(name))


def fold(text):
    """The declared version move, normalised away so everything else must match."""
    return text.replace(STYLE_NEW, STYLE_OLD)


def clean(text):
    return masked(fold(text))[0]


# ------------------------------------------------------- JSON-LD lookups ----
# The serialization of a JSON-LD block is NOT stable across this site's two
# language pipelines. An English page carries the compact form wp_json_encode
# produces — `"@type":"HowTo"`, `https://schema.org`. A translated page is
# re-serialized on the way out, pretty-printed with escaped slashes —
# `"@type": "HowTo"`, `https:\/\/schema.org`. Measured 2026-09-22 across the 42
# detail pages: 21 compact, 21 pretty, identically in the baseline and in the
# candidate. So no lookup here may match on the literal serialization; every
# one parses the block and reads @type. A literal match would have left this
# gate blind to half the detail pages while still reporting green.


def ld_types(body):
    """Every @type string anywhere in one JSON-LD body, or None if unparseable."""
    try:
        obj = json.loads(body.strip())
    except ValueError:
        return None
    found = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get('@type')
            if isinstance(t, str):
                found.append(t)
            elif isinstance(t, list):
                found.extend(x for x in t if isinstance(x, str))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(obj)
    return found


def ld_blocks(text):
    """[(start, end, types|None)] for every ld+json script, document order."""
    return [(m.start(), m.end(), ld_types(m.group(1))) for m in LDJSON.finditer(text)]


def count_ld_blocks(text, want):
    """How many ld+json blocks declare `want` among their @types."""
    return sum(1 for _, _, ty in ld_blocks(text) if ty and want in ty)


def has_ld_type(text, want):
    return count_ld_blocks(text, want) > 0


def find_ld_block(text, want):
    """(start, end) of the first block declaring `want`, else None."""
    for s, e, ty in ld_blocks(text):
        if ty and want in ty:
            return (s, e)
    return None


def ld_bodies(text):
    """The inner text of every ld+json script, in document order."""
    return [m.group(1) for m in LDJSON.finditer(text)]


def compact_json(body):
    """A JSON body re-serialized the way wp_json_encode writes it."""
    return json.dumps(json.loads(body.strip()), separators=(',', ':'),
                      ensure_ascii=False)


def normalize_ld(text):
    """Every JSON-LD body rewritten to the compact wp_json_encode form.

    The translated pipeline re-serializes these blocks pretty-printed, so a
    rebuild that inserts the compact run cannot match a translated page byte
    for byte. Normalising both sides collapses that formatting difference and
    nothing else: the rewrite parses and re-dumps, so any payload change
    survives it, and gate [5] separately asserts every pre-existing block is
    byte-identical — this cannot hide a change. A body that does not parse is
    left alone, so it still shows up as a difference.
    """
    out, last = [], 0
    for m in LDJSON.finditer(text):
        out.append(text[last:m.start()])
        whole, body = m.group(0), m.group(1)
        try:
            rewritten = whole[:m.start(1) - m.start()] + compact_json(body) \
                + whole[m.end(1) - m.start():]
        except ValueError:
            rewritten = whole
        out.append(rewritten)
        last = m.end()
    out.append(text[last:])
    return ''.join(out)


def run_c_problem(c, exp, n):
    """'' when run C on page n is the declared HowTo, else why it is not.

    Byte equality only holds on the compact side. A translated page's JSON-LD
    is pretty-printed on the way out, so there the assertion is that the block
    parses to the declared object AND that compacting it reproduces the
    declared bytes — which is what proves the difference is formatting alone
    and not a different payload. Without the second half the check would be
    weaker than it looks: a payload change would still show up, but so would a
    change that merely happened to parse.
    """
    declared = exp['howto_json'].strip()
    bodies = [b for b in ld_bodies(c) if 'HowTo' in (ld_types(b) or [])]
    if len(bodies) != 1:
        return '%s: the HowTo run appears %d times' % (n, len(bodies))
    body = bodies[0].strip()
    if body == declared:
        return ''
    if ld_types(body) is None:
        return '%s: the HowTo block does not parse' % n
    if compact_json(body) != declared:
        return '%s: the HowTo payload is not the one the band renders from' % n
    return ''


def run_between(text, open_marker, close='</section>'):
    """The band's own markup: from its opening section tag to the first close.

    Safe because each new band is a single flat <section> with no nested
    section of its own — asserted by the caller through the byte comparison in
    gate [3], which would fail if the extraction had clipped or overrun.
    """
    i = text.find(open_marker)
    if i < 0:
        return None
    j = text.find(close, i)
    if j < 0:
        return None
    return text[i:j + len(close)]


def insert_before(text, anchor, run):
    i = text.find(anchor)
    if i < 0:
        return None
    return text[:i] + run + text[i:]


def insert_howto(text, run):
    span = find_ld_block(text, FAQ_TYPE)
    if span is None:
        return None
    at = span[1]
    # The emitter's block ends with "</script>\n" and run C opens with its own
    # "\n", so the two together leave a blank line between the FAQPage script
    # and the HowTo one. Inserting flush against "</script>" would land run C
    # before that newline and lose the blank line the page actually has.
    if text[at:at + 1] == '\n':
        at += 1
    return text[:at] + run + text[at:]


def load_unit():
    spec = importlib.util.spec_from_file_location(
        'b2d_h3_render_unit', os.path.join(HERE, 'b2d_h3_render_unit.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def local_expectations(php):
    """The bands and the steps, rendered from the theme's own source.

    This is the anchor that stops the pinned runs from being a rubber stamp:
    the substantive bytes must come from the shipped functions, not from a
    capture of them.
    """
    u = load_unit()
    body = """
$GLOBALS['SF_SINGULAR'] = true;
$GLOBALS['SF_ID']       = 21;
$GLOBALS['SF_META']     = array();
echo json_encode(array(
	'content'  => sinofresh_formula_content(),
	'sampling' => sinofresh_formula_sampling(),
	'steps'    => sinofresh_sampling_steps(),
), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
"""
    src = (u.PREAMBLE + '\n' + u.extract_admin(u.read(u.ADMIN)) + '\n\n'
           + u.extract_region(u.read(u.FUNCTIONS)) + '\n' + body)
    tmp = os.path.join(tempfile.gettempdir(), 'h3-expect.php')
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(src)
    p = subprocess.run([php, tmp], capture_output=True, text=True)
    os.remove(tmp)
    if p.returncode != 0 or 'Warning' in p.stdout:
        raise SystemExit('could not render the expectations locally:\n' + p.stdout + p.stderr)
    data = json.loads(p.stdout)
    content, sampling = data['content'], data['sampling']
    steps = data['steps']

    howto = {
        '@context': 'https://schema.org',
        '@type': 'HowTo',
        'name': 'How Sampling Works',
        'totalTime': 'P3D',
        'step': [{'@type': 'HowToStep', 'position': i + 1,
                  'name': s['title'], 'text': s['text']} for i, s in enumerate(steps)],
    }
    howto_json = json.dumps(howto, ensure_ascii=False, separators=(',', ':'))
    return {
        'content': content,
        'sampling': sampling,
        'steps': steps,
        'howto_json': howto_json,
        'run_a': RUN_A.replace('%CONTENT%', content),
        'run_b': RUN_B.replace('%SAMPLING%', sampling),
        'run_c': RUN_C.replace('%HOWTO%', howto_json),
    }


def load_served(path):
    table = {}
    if not path or not os.path.exists(path):
        return None
    for line in read(path).splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            table[parts[1].strip()] = parts[0]
    return table


# ---------------------------------------------------------------- gates ------

def check_inputs(base, cand, fails, notes, exp):
    for label, d in (('baseline', base), ('candidate', cand)):
        if not os.path.isdir(d):
            fails.append('[0] %s directory does not exist: %s' % (label, d))
        elif len(pages(d)) != 75:
            fails.append('[0] %s holds %d pages, expected 75' % (label, len(pages(d))))
    if len(exp['steps']) != 4:
        fails.append('[0] the renderer declares %d sampling steps, expected 4' % len(exp['steps']))
    if not fails:
        notes.append('[0] both captures hold 75 pages; the renderer declares 4 steps')


def check_pageset(base, cand, fails, notes, exp):
    want = set(n for n in pages(base) if is_detail(n))
    diff, same, folded = [], [], 0
    for n in pages(base):
        b, c = read(os.path.join(base, n)), read(os.path.join(cand, n))
        if clean(b) != clean(c):
            diff.append(n)
        else:
            same.append(n)
        if masked(b)[0] != masked(c)[0]:
            folded += 1
    miss, extra = want - set(diff), set(diff) - want
    if miss or extra:
        fails.append('[1] page set wrong: %d differ, expected %d; missing=%s extra=%s'
                     % (len(diff), len(want), sorted(miss)[:4], sorted(extra)[:4]))
    else:
        notes.append('[1] exactly the declared %d detail pages differ; %d identical'
                     % (len(want), len(same)))
    # The fold has to be *necessary and sufficient*. Necessary: before folding,
    # every page differs, because the enqueue version is site-wide. Sufficient:
    # after folding, only the declared detail pages differ (asserted above).
    # The two together are what pins the only permitted difference to the token.
    if folded != len(pages(base)):
        fails.append('[1] the token did not move on every page: %d of %d differ before the fold '
                     'is applied' % (folded, len(pages(base))))
    else:
        notes.append('[1] the token moved on all %d pages, and folding it leaves exactly the '
                     '%d detail pages differing' % (folded, len(want)))

    stray, thin = [], []
    for n in pages(cand):
        c = read(os.path.join(cand, n))
        counts = (c.count(CONTENT_OPEN), c.count(SAMPLING_OPEN),
                  count_ld_blocks(c, HOWTO_TYPE))
        if is_detail(n):
            if counts != (1, 1, 1):
                thin.append('%s has content/sampling/howto = %s' % (n, counts))
        elif any(counts):
            stray.append('%s carries %s' % (n, counts))
    if thin:
        fails.append('[1] a detail page is missing one of the three runs: %s' % thin[:4])
    else:
        notes.append('[1] all 42 detail pages carry the content band, the sampling band and '
                     'the HowTo schema exactly once each')
    if stray:
        fails.append('[1] a non-detail page carries a new run: %s' % stray[:4])
    else:
        notes.append('[1] none of the 33 other pages carries any of them')


def check_confined(base, cand, fails, notes, exp):
    """The main gate: rebuild the candidate from the baseline and compare."""
    bad, bad_reason = [], []
    for n in pages(base):
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        if not is_detail(n):
            if clean(braw) != clean(craw):
                bad.append(n)
            if CONTENT_OPEN in braw or SAMPLING_OPEN in braw or has_ld_type(braw, HOWTO_TYPE):
                bad_reason.append('%s baseline already carries a new run' % n)
            continue
        t = insert_howto(braw, exp['run_c'])
        if t is None:
            bad_reason.append('%s: no FAQPage script to anchor the HowTo against' % n)
            continue
        t = insert_before(t, FAQ_COMMENT, exp['run_a'])
        if t is None:
            bad_reason.append('%s: no FAQ lead comment to anchor the content band '
                              'against' % n)
            continue
        t = insert_before(t, MORE_COMMENT, exp['run_b'])
        if t is None:
            bad_reason.append('%s: no related-formulas comment to anchor the sampling '
                              'band against' % n)
            continue
        # clean() folds AND masks; comparing the folded rebuild against an
        # unfolded capture would convict the token itself on every page.
        # normalize_ld() then removes the one serialization difference the
        # translated pipeline introduces.
        if normalize_ld(clean(t)) != normalize_ld(clean(craw)):
            bad.append(n)
    if bad or bad_reason:
        fails.append('[2] the page is not the declared addition: %s' % (bad[:4] + bad_reason[:4]))
    else:
        notes.append('[2] all 42 pages rebuild byte-for-byte as the baseline plus exactly the '
                     'three declared runs, and the other 33 are unchanged apart from the token')


def check_runs(base, cand, fails, notes, exp):
    """[3] The pinned runs are the renderers' own bytes, not a copy of the page."""
    bad, extra = [], []
    for n in pages(cand):
        if not is_detail(n):
            continue
        c = read(os.path.join(cand, n))
        for label, marker, want, key in (('content', CONTENT_OPEN, exp['content'], 'A'),
                                         ('sampling', SAMPLING_OPEN, exp['sampling'], 'B')):
            got = run_between(c, marker)
            if got != want:
                bad.append('%s: %s band %s != the renderer' % (n, label,
                                                               (got or '')[:40]))
                continue
            # the band must appear once, and the wrapper around it must hold
            # nothing but whitespace and the template's own comment
            if c.count(want) != 1:
                extra.append('%s: the %s band appears %d times' % (n, label, c.count(want)))
        problem = run_c_problem(c, exp, n)
        if problem:
            extra.append(problem)
    if bad:
        fails.append('[3] a served band is not what the renderer produces: %s' % bad[:4])
    else:
        notes.append('[3] both served bands are byte-identical to the local render of the '
                     'shipped functions on all 42 pages')
    if extra:
        fails.append('[3] a declared run appears more than once: %s' % extra[:4])
    else:
        notes.append('[3] each declared run appears exactly once per detail page')


def check_served(theme, served, fails, notes, exp):
    table = load_served(served)
    if table is None:
        fails.append('[4] no served manifest: the tree cannot be shown to be the copy the '
                     'server holds (a missing reference is a failure, not a skip)')
    else:
        bad, n = [], 0
        for dirpath, dirnames, filenames in os.walk(theme):
            dirnames[:] = [d for d in dirnames if d not in ('_backup', '__pycache__')]
            for f in filenames:
                if f in ('.DS_Store',) or f.startswith('._'):
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, theme).replace(os.sep, '/')
                n += 1
                want = table.get(rel)
                got = hashlib.sha256(open(p, 'rb').read()).hexdigest()
                if want is None:
                    bad.append('%s absent from the manifest' % rel)
                elif want != got:
                    bad.append('%s %s != %s' % (rel, got[:12], want[:12]))
        if bad:
            fails.append('[4] working tree vs served copy: %s' % bad[:4])
        else:
            notes.append('[4] all %d files match the served pre-flight copy byte-for-byte' % n)
    for rel in FROZEN:
        if not os.path.exists(os.path.join(theme, rel)):
            fails.append('[4] contract file missing: %s' % rel)
    notes.append('[4] the four K1-K7 contract files are present')

    p = subprocess.run(['git', '-C', ROOT, 'diff', '--name-only', BASE_COMMIT,
                        '--', 'sinofresh-theme'], capture_output=True, text=True)
    changed = sorted(x for x in p.stdout.split() if x)
    want = sorted(['sinofresh-theme/functions.php', 'sinofresh-theme/style.css',
                   'sinofresh-theme/templates/single-sf_formula.html'])
    if changed != want:
        fails.append('[4] the theme change set is not the declared three files: %s' % changed)
    else:
        notes.append('[4] the theme change set versus %s is exactly functions.php, style.css '
                     'and the detail template' % BASE_COMMIT)


def check_jsonld(base, cand, fails, notes, exp):
    drift, bad_howto, bad_h1, bad_count = [], [], [], []
    for n in pages(base):
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        bl = LDJSON.findall(braw)
        cl = LDJSON.findall(craw)
        howto = [x for x in cl if 'HowTo' in (ld_types(x) or [])]
        rest = [x for x in cl if 'HowTo' not in (ld_types(x) or [])]
        if rest != bl:
            drift.append(n)
        if is_detail(n):
            if len(howto) != 1:
                bad_count.append('%s has %d HowTo blocks' % (n, len(howto)))
            else:
                try:
                    obj = json.loads(howto[0])
                except ValueError as e:
                    bad_howto.append('%s does not parse (%s)' % (n, e))
                    obj = None
                if obj is not None and obj != json.loads(exp['howto_json']):
                    bad_howto.append('%s does not match the declared steps' % n)
        elif howto:
            bad_count.append('%s carries a HowTo block' % n)
        if braw.count('<h1') != 1 or craw.count('<h1') != 1:
            bad_h1.append(n)
    if drift:
        fails.append('[5] a pre-existing JSON-LD block changed: %s' % drift[:4])
    else:
        notes.append('[5] every baselined JSON-LD block is byte-identical on all 75 pages')
    if bad_count:
        fails.append('[5] HowTo block count wrong: %s' % bad_count[:4])
    else:
        notes.append('[5] exactly one HowTo per detail page, none anywhere else')
    if bad_howto:
        fails.append('[5] the HowTo payload is not the declared schema: %s' % bad_howto[:4])
    else:
        notes.append('[5] the HowTo parses and equals the steps the band renders from')
    if bad_h1:
        fails.append('[5] h1 count is not 1: %s' % bad_h1[:4])
    else:
        notes.append('[5] exactly one h1 per page on all 75 pages')


def check_structure(base, cand, fails, notes, exp):
    bad_order, bad_h2, bad_kept = [], [], []
    for n in pages(cand):
        if not is_detail(n):
            continue
        c = read(os.path.join(cand, n))
        order = [c.find(ACTIVES_OPEN), c.find(CONTENT_OPEN), c.find(FAQ_OPEN),
                 c.find(SAMPLING_OPEN), c.find(MORE_OPEN)]
        if any(i < 0 for i in order) or order != sorted(order):
            bad_order.append('%s %s' % (n, order))
        band = run_between(c, CONTENT_OPEN) or ''
        problems = []
        n_h2, n_h3 = band.count('<h2'), band.count('<h3')
        n_block = band.count('sf-fdetail-content__block')
        labels = re.findall(r'<h2 class="sf-fdetail-content__(?:heading|subtitle)">([^<]*)</h2>',
                            band)
        if n_h3:
            problems.append('%d h3 inside the band' % n_h3)
        if n_h2 != n_block:
            problems.append('%d h2 for %d groups' % (n_h2, n_block))
        if not 1 <= n_h2 <= len(GROUP_LABELS):
            problems.append('%d groups (max %d)' % (n_h2, len(GROUP_LABELS)))
        if len(labels) != n_h2:
            problems.append('an h2 in the band is not a group heading')
        order = [GROUP_LABELS.index(x) for x in labels if x in GROUP_LABELS]
        if len(order) != len(labels) or order != sorted(order):
            problems.append('groups %s not in the declared order' % labels)
        if problems:
            bad_h2.append('%s: %s' % (n, '; '.join(problems)))
        for label, needle in (('H2a params', 'sf-fdetail2__params'),
                              ('FAQ accordion', 'sf-faq__item'),
                              ('hero CTA', 'sf-quote-cta'),
                              ('related grid', 'sf-fgrid')):
            if needle not in c:
                bad_kept.append('%s lost %s' % (n, label))
    if bad_order:
        fails.append('[6] the new bands are not where the template puts them: %s' % bad_order[:4])
    else:
        notes.append('[6] on all 42 pages the order is actives < content < FAQ < sampling < grid')
    if bad_h2:
        fails.append('[6] the content band headings are wrong: %s' % bad_h2[:4])
    else:
        notes.append('[6] the content band renders one h2 per group, no h3, in the declared '
                     'order (only the packaging group has data today, within it only Storage)')
    if bad_kept:
        fails.append('[6] an existing band was lost: %s' % bad_kept[:4])
    else:
        notes.append('[6] params, FAQ accordion, hero CTA and the related grid all survive')


def check_versions(base, cand, fails, notes, exp):
    moved, wrong, other = [], [], []
    for n in pages(base):
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        bm, cm = dict(ASSET.findall(braw)), dict(ASSET.findall(craw))
        if bm.get('style.css') != '2.10.56':
            wrong.append('%s baseline style ver %s' % (n, bm.get('style.css')))
        if cm.get('style.css') != '2.10.57':
            wrong.append('%s candidate style ver %s' % (n, cm.get('style.css')))
        moved.append(n)
        for k in set(bm) | set(cm):
            if k == 'style.css':
                continue
            if bm.get(k) != cm.get(k):
                other.append('%s %s %s -> %s' % (n, k, bm.get(k), cm.get(k)))
    if wrong:
        fails.append('[7] the style token did not move as declared: %s' % wrong[:4])
    else:
        notes.append('[7] style.css 2.10.56 -> 2.10.57 on all %d pages' % len(moved))
    if other:
        fails.append('[7] an undeclared version token moved: %s' % other[:4])
    else:
        notes.append('[7] no other asset version token moved on any page')


GATES = [('0', check_inputs), ('1', check_pageset), ('2', check_confined),
         ('3', check_runs), ('4', check_served), ('5', check_jsonld),
         ('6', check_structure), ('7', check_versions)]


def run(base, cand, theme, served, exp, verbose=True):
    fails, notes = [], []
    for tag, fn in GATES:
        if fn is check_served:
            fn(theme, served, fails, notes, exp)
        else:
            fn(base, cand, fails, notes, exp)
        if fn is check_inputs and fails:
            break
    if verbose:
        print('=' * 72)
        for note in notes:
            print('  ok   ' + note)
        print('-' * 72)
        if fails:
            for f in fails:
                print('  FAIL ' + f)
            print('VERDICT: FAIL — %d gate problem(s)' % len(fails))
        else:
            print('VERDICT: PASS — all eight gates hold')
    return fails, notes


# ------------------------------------------------------------- sabotage ------

def mutate(name, base, cand, theme, exp, tmp):
    P, T = os.path.join(tmp, 'pages'), os.path.join(tmp, 'theme')
    shutil.copytree(cand, P)
    shutil.copytree(theme, T,
                    ignore=shutil.ignore_patterns('_backup', '__pycache__', '.DS_Store', '._*'))
    det = 'formulas__joint-support-soft-chews.html'
    zh = 'zh__formulas__joint-support-soft-chews.html'
    dose = 'products__soft-chews.html'
    pp = lambda n: os.path.join(P, n)
    w = lambda p, s: open(p, 'w', encoding='utf-8').write(s)
    s = read(pp(det))
    band = run_between(s, CONTENT_OPEN)

    if name == 'content-band-removed':
        w(pp(det), s.replace(band, '', 1))
    elif name == 'sampling-band-removed':
        w(pp(det), s.replace(run_between(s, SAMPLING_OPEN), '', 1))
    elif name == 'howto-removed':
        w(pp(det), s.replace(exp['run_c'], '', 1))
    elif name == 'howto-step-dropped':
        short = s.replace('"position":4,', '"_position":4,', 1)
        w(pp(det), short)
    elif name == 'content-band-on-a-dosage-page':
        w(pp(dose), read(pp(dose)).replace('</body>', band + '</body>', 1))
    elif name == 'zh-howto-payload-changed':
        # Keep the pretty formatting and change one step's text: only a check
        # that parses the block can see this, and the compact serialization the
        # rebuild inserts must not be allowed to mask it.
        sz = read(pp(zh))
        w(pp(zh), sz.replace(
            '"text": "Tell us your target formula, flavor, and packaging ideas."',
            '"text": "Send us your target formula, flavor and packaging ideas."', 1))
    elif name == 'zh-content-band-removed':
        sz = read(pp(zh))
        w(pp(zh), sz.replace(run_between(sz, CONTENT_OPEN), '', 1))
    elif name == 'style-token-not-bumped':
        w(pp(zh), s.replace(zh and STYLE_NEW, STYLE_OLD, 1))
    elif name == 'undeclared-token-moved':
        w(pp(zh), read(pp(zh)).replace('formulas.js?ver=1.1.0', 'formulas.js?ver=1.1.1', 1))
    elif name == 'faqpage-changed':
        t = read(pp(det))
        s0, e0 = find_ld_block(t, FAQ_TYPE)
        w(pp(det), t[:s0] + t[s0:e0].replace(FAQ_TYPE, FAQ_TYPE + 'X', 1) + t[e0:])
    elif name == 'detail-page-unchanged':
        w(pp(det), read(os.path.join(base, det)))
    elif name == 'storage-line-changed':
        w(pp(det), s.replace('Cool, dry place out of direct sunlight',
                             'Store somewhere cool, out of direct sunlight', 1))
    elif name == 'packaging-heading-demoted':
        w(pp(det), s.replace('class="sf-fdetail-content__subtitle"',
                             'class="sf-fdetail-content__subtitle" data-x', 1).replace(
                                 '<h2 class="sf-fdetail-content__subtitle">',
                                 '<h3 class="sf-fdetail-content__subtitle">', 1))
    elif name == 'band-moved-after-the-grid':
        w(pp(det), s.replace(band, '', 1).replace('</body>', band + '</body>', 1))
    elif name == 'second-h1-introduced':
        w(pp(det), s.replace(band, band + '<h1>Extra</h1>', 1))
    else:
        raise SystemExit('unknown sabotage variant %r' % name)
    return P, T


# Two of these aim at a translated page on purpose. Almost every mutation
# below lands on the English page, and the translated pipeline is the one
# whose JSON-LD is re-serialized — so without them the parse-based run C
# check and normalize_ld() would never be exercised by a failure.
MATRIX = ['content-band-removed', 'sampling-band-removed', 'howto-removed',
          'howto-step-dropped', 'content-band-on-a-dosage-page', 'style-token-not-bumped',
          'undeclared-token-moved', 'faqpage-changed', 'detail-page-unchanged',
          'storage-line-changed', 'packaging-heading-demoted', 'band-moved-after-the-grid',
          'second-h1-introduced', 'zh-howto-payload-changed', 'zh-content-band-removed']


def negcontrol(base, cand, theme, served, exp, tmp, name):
    if name == 'served-manifest-missing':
        return run(base, cand, theme, os.path.join(tmp, 'nope.manifest'), exp,
                   verbose=False)[0], 'served manifest points at a nonexistent path'
    if name == 'baseline-empty':
        d = os.path.join(tmp, 'empty')
        os.makedirs(d, exist_ok=True)
        return run(d, cand, theme, served, exp, verbose=False)[0], \
            'baseline directory is empty'
    if name == 'candidate-equals-baseline':
        d = os.path.join(tmp, 'asbase')
        shutil.copytree(base, d)
        return run(base, d, theme, served, exp, verbose=False)[0], \
            'candidate is a copy of the baseline'
    raise SystemExit('unknown negative control %r' % name)


NEGCTL = ['served-manifest-missing', 'baseline-empty', 'candidate-equals-baseline']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--theme', default=os.path.join(ROOT, 'sinofresh-theme'))
    ap.add_argument('--served')
    ap.add_argument('--json')
    ap.add_argument('--php', default=os.path.expanduser(
        '~/Library/Application Support/Local/lightning-services/php-8.2.29+0'
        '/bin/darwin-arm64/bin/php'))
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--negctl', action='store_true')
    ap.add_argument('--sabotage')
    ap.add_argument('--pin-run', choices=['A', 'B', 'C'],
                    help='print the declared run and the capture text it must equal')
    args = ap.parse_args(argv)

    exp = local_expectations(args.php)

    if args.pin_run:
        if args.pin_run == 'C':
            marker, key = HOWTO_TYPE, 'run_c'
        elif args.pin_run == 'A':
            marker, key = CONTENT_OPEN, 'run_a'
        else:
            marker, key = SAMPLING_OPEN, 'run_b'
        print('declared run %s (%d bytes):' % (args.pin_run, len(exp[key])))
        print(repr(exp[key]))
        n = 'formulas__joint-support-soft-chews.html'
        if args.cand and os.path.exists(os.path.join(args.cand, n)):
            c = read(os.path.join(args.cand, n))
            if args.pin_run == 'C':
                s0, e0 = find_ld_block(c, HOWTO_TYPE)
                print('\ncapture text (the whole HowTo script element):')
                print(repr(c[s0 - 1:e0 + 1]))
            else:
                i = c.find(marker)
                j = c.rfind('<!-- Batch H3', 0, i)
                k = c.find('<!-- /wp:html -->', i) + len('<!-- /wp:html -->')
                print('\ncapture text (comment + block wrapper + band):')
                print(repr(c[j:k]))
        return 0

    if args.matrix:
        print('=== sabotage matrix — every variant must be caught ===')
        rows, missed = [], []
        for name in MATRIX:
            tmp = tempfile.mkdtemp(prefix='h3-sab-')
            try:
                P, T = mutate(name, args.base, args.cand, args.theme, exp, tmp)
                fails, notes = run(args.base, P, T, args.served, exp, verbose=False)
                caught = bool(fails)
                gates = sorted(set(f.split(']')[0] + ']' for f in fails))
                rows.append({'variant': name, 'caught': caught, 'gates': gates,
                             'detail': fails[:3]})
                print('  %-34s %s   %s' % (name, 'CAUGHT' if caught else 'MISSED',
                                           ' '.join(gates) or '-'))
                if not caught:
                    missed.append(name)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        print('-' * 72)
        print('  %d/%d variants caught' % (len(MATRIX) - len(missed), len(MATRIX)))
        if missed:
            print('MISSED: %s' % missed)
        if args.json:
            json.dump({'matrix': rows, 'missed': missed},
                      open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1 if missed else 0

    if args.negctl:
        print('=== negative controls — each precondition break must FAIL ===')
        rows, wrong = [], []
        for name in NEGCTL:
            tmp = tempfile.mkdtemp(prefix='h3-neg-')
            try:
                fails, desc = negcontrol(args.base, args.cand, args.theme, args.served, exp,
                                         tmp, name)
                caught = bool(fails)
                named = bool(re.findall(r'^\[\d+\]', ' '.join(fails)))
                rows.append({'control': name, 'description': desc, 'failed': caught,
                             'named_verdict': named, 'detail': fails[:2]})
                print('  %-28s %s  %s' % (name, 'FAIL (as required)' if caught and named
                                          else 'NOT A VERDICT', desc))
                if not (caught and named):
                    wrong.append(name)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        print('-' * 72)
        print('  %d/%d controls failed as required' % (len(NEGCTL) - len(wrong), len(NEGCTL)))
        if wrong:
            print('  WRONG: %s' % wrong)
        if args.json:
            json.dump({'controls': rows, 'wrong': wrong},
                      open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1 if wrong else 0

    if args.sabotage:
        tmp = tempfile.mkdtemp(prefix='h3-sab-')
        try:
            P, T = mutate(args.sabotage, args.base, args.cand, args.theme, exp, tmp)
            fails, notes = run(args.base, P, T, args.served, exp)
            return 1 if fails else 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if not (args.base and args.cand):
        ap.error('--base and --cand are required')
    fails, notes = run(args.base, args.cand, args.theme, args.served, exp)
    if args.json:
        json.dump({'fails': fails, 'notes': notes, 'runs': {k: len(exp[k]) for k in
                                                            ('run_a', 'run_b', 'run_c')}},
                  open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
