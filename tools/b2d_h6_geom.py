#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H6 — the behavioural pass: does removing 8,976 B of dead CSS change anything?

WHY A BROWSER PASS EXISTS FOR A CSS DELETION

The byte gate cannot see style.css at all. The pages carry only its URL and a
token, so deleting 37 rules is invisible to a rendered capture, and the honest
question — "did any element's computed style or box move?" — is one no snapshot
can answer.

The static argument is this batch's complete one: every selector in every cut
rule contains one of the four dead tokens, and those four tokens have zero
occurrences across all 75 captures and zero across the live source tree, so no
cut selector can match any element in any render. The sweep here is what keeps
that argument honest: it measures the claim instead of trusting it. A bug in the
prune tool — a rule half-cut, a comment treated as a selector, a stray brace —
would show up as a moved box on the pages that carry the neighbouring live
rules, and nowhere else.

METHOD

Two sweeps of the same pages against two installations of the pre-flight copy —
the baseline commit, then the candidate — compared page by page, every element
that carries a class. Not one sweep compared against remembered numbers: the
numbers are the thing under test.

Provenance is asserted per page and is not relaxed by the retry: the served sheet
must be the pre-flight copy AND advertise the version this sweep expects, and the
sweep stores the sheet's own sha256, which --compare then checks against the
sha256 of that commit's style.css. Two sweeps that silently rendered the same
sheet would otherwise report a perfect match while proving nothing.

The phone sweep is a six-page sample rather than all of them. Stated plainly
because the asymmetry matters: the assertion is breakpoint-independent (the cut
rules cannot match at any width), so the desktop sweep is the complete one and
the sample exists to catch a breakpoint-specific box, not to claim a completeness
it does not have.

usage:
    b2d_h6_geom.py --label baseline  --sha <sha> --ver 2.10.60 --out base.json
    b2d_h6_geom.py --label candidate --sha <sha> --ver 2.10.61 --out cand.json
    b2d_h6_geom.py --compare base.json cand.json
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
PREFLIGHT_DIR = 'sinofresh-theme-preflight'
HERE = os.path.dirname(os.path.abspath(__file__))
PATHS = os.path.join(HERE, 'b2d_s3_paths.txt')

# ------------------------------------------------------------- quiescence ---
# A two-state render comparison is a measurement of the SITE, and the site is
# not exclusively ours: someone edited a formula page in wp-admin at 18:21:29
# DURING the candidate sweep, and the result was that one page came back 24
# elements heavier at 390px and unchanged at 1440px — which reads exactly like a
# batch regression and is actually an editor typing. There is no way to notice
# that from the numbers alone, so the sweep has to refuse to run blind.
#
# The fingerprint comes from the REST API's `modified` field, not from the
# database: no credentials in the repo, and no way to quietly disable the check
# by leaving a variable unset. If it cannot be read, the sweep ABORTS.
FP_TYPES = ('sf_formula', 'pages', 'posts')
FP_FIELDS = 'id,modified'

DESKTOP = (1440, 900)
PHONE = (390, 844)
PHONE_SAMPLE = [
    '/',
    '/products/soft-chews/',
    '/products/tablets/',
    '/formulas/joint-support-soft-chews/',
    '/formulas/calming-soft-chews/',
    '/zh/formulas/joint-support-soft-chews/',
]

PROPS = [
    'display', 'position', 'float', 'clear', 'width', 'height',
    'marginTop', 'marginRight', 'marginBottom', 'marginLeft',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'borderTopWidth', 'borderBottomWidth', 'borderLeftWidth', 'borderRightWidth',
    'borderTopStyle', 'borderTopColor', 'borderRadius',
    'backgroundColor', 'color', 'opacity', 'visibility', 'overflow',
    'fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing',
    'fontVariantNumeric', 'textAlign', 'textTransform', 'whiteSpace',
    'textDecorationLine', 'verticalAlign', 'listStyleType',
    'gridTemplateColumns', 'gridTemplateRows', 'gap', 'columnGap', 'rowGap',
    'flexDirection', 'flexWrap', 'flexGrow', 'flexBasis', 'alignItems',
    'justifyContent', 'boxShadow', 'transform', 'zIndex',
]

PROBE = r"""
(() => {
  try {
    const P = %s;
    const sheet = (document.querySelector("link[href*='style.css']") || {}).href || '';
    const out = {};
    const els = document.querySelectorAll('[class]');
    const all = document.querySelectorAll('*').length;
    els.forEach((el, i) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const box = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
      let sig = box.join(',');
      for (const p of P) { sig += '|' + cs[p]; }
      const key = i + '|' + el.tagName + '|' + (el.id || '') + '|' + (el.className || '');
      out[key] = sig;
    });
    return {sheet: sheet, vw: window.innerWidth, vh: window.innerHeight,
            nClassed: els.length, nAll: all, els: out};
  } catch (e) {
    return {error: String(e && e.message ? e.message : e)};
  }
})()
""" % json.dumps(PROPS)


def content_fingerprint(auth):
    """A digest of every post's (id, modified) — i.e. "is the site still".

    Not a substitute for the render comparison; a precondition for trusting it.
    Paginated and ordered by id, so the digest depends on content, not on the
    order the server happened to return rows in.
    """
    import hashlib
    h = hashlib.sha256()
    total = 0
    for t in FP_TYPES:
        page = 1
        while page <= 10:
            url = ('%s/wp-json/wp/v2/%s?per_page=100&page=%d&orderby=id&order=asc'
                   '&_fields=%s' % (HOST, t, page, FP_FIELDS))
            rc, out, err = run(['curl', '-s', '-u', auth,
                                '-H', 'X-SF-Preflight: 1', url], 90)
            if rc != 0 or not out.startswith('['):
                raise SystemExit(
                    'FATAL quiescence query failed (%s page %d): %s. The sweep '
                    'compares two renders of a live site; without this check a '
                    'concurrent edit is indistinguishable from a regression.'
                    % (t, page, (out or err)[:200]))
            h.update(out.encode('utf-8'))
            n = out.count('"id"')
            total += n
            if n < 100:
                break
            page += 1
    return {'sha': h.hexdigest(), 'rows': total}


def run(cmd, timeout=240):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=240):
    """agent-browser eval prints a JSON string literal: decode twice."""
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    try:
        first = json.loads(out)
    except Exception:
        return out
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return first
    return first


def sheet_sha(url, auth):
    r = subprocess.run(['curl', '-s', '-u', auth, url], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest()


def local_css_sha(sha):
    r = subprocess.run(['git', 'show', '%s:sinofresh-theme/style.css' % sha],
                       cwd=os.path.dirname(HERE), capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest()


class Sweep(object):
    def __init__(self, auth, label, sha, expect_ver):
        self.auth = auth
        self.label = label
        self.sha = sha
        self.expect_ver = expect_ver
        self.ver = expect_ver
        self.page = {}
        self.css_sha = {}
        self.errors = []
        self.fp = {}

    def attach(self):
        b64 = base64.b64encode(self.auth.encode('utf-8')).decode('ascii')
        user, _, pw = self.auth.partition(':')
        run(['agent-browser', 'close', '--all'])
        rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw])
        if rc != 0:
            raise SystemExit('FATAL set credentials: %s %s' % (out, err))
        rc, out, err = run(['agent-browser', 'open', HOST + '/'])
        if rc != 0:
            raise SystemExit('FATAL open: %s %s' % (out, err))
        # Custom header and Basic auth in ONE call: each of `set credentials`
        # and `set headers` rebuilds the context, so whichever runs second wins.
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs])
        run(['agent-browser', 'errors', '--clear'])

    def freeze(self):
        """Stop time before sampling.

        Measured, not assumed: an A/A run (the same install swept twice) came
        back with two /about/ divs differing in `opacity` and `transform` while
        their boxes were identical — i.e. a transition caught at two different
        phases, on the same bytes. A sweep that samples a moving target can
        only ever be compared with a tolerance, and this batch's whole method is
        that a comparison must be able to say "no difference" exactly.

        So both sides are sampled with transitions and animations disabled and
        the scroll pinned to 0. The override is applied identically to both
        installs, so it cannot favour either; and what it removes from the
        comparison is animation PHASE, not animation BEHAVIOUR — nothing in
        this batch's declared scope touches an animated selector (all four dead
        families have zero hits in the 75-page capture).
        """
        ev("(()=>{let s=document.getElementById('sf-geom-freeze');"
           "if(!s){s=document.createElement('style');s.id='sf-geom-freeze';"
           "s.textContent='*,*::before,*::after{transition:none!important;"
           "animation:none!important}';document.head.appendChild(s);}"
           "window.scrollTo(0,0);void document.body.offsetHeight;return true;})()")

    def measure(self, path, width, height, tag):
        url = HOST + path + '?sfgeom=%s%s' % (tag, time.strftime('%H%M%S'))
        st = None
        for attempt in (1, 2, 3):
            run(['agent-browser', 'open', url])
            run(['agent-browser', 'reload'])          # reload keeps the header
            run(['agent-browser', 'set', 'viewport', str(width), str(height)])
            time.sleep(0.5)
            self.freeze()
            st = ev(PROBE)
            if isinstance(st, dict) and 'error' in st:
                self.errors.append((path, 'probe: %s' % st['error']))
                st = None
                time.sleep(0.8)
                continue
            sheet = (st or {}).get('sheet') or ''
            if PREFLIGHT_DIR in sheet and ('ver=' + self.expect_ver) in sheet:
                if st.get('vw') and abs(st['vw'] - width) > 2:
                    raise SystemExit('FATAL viewport did not take: %s != %s'
                                     % (st['vw'], width))
                return st
            print('   ..   %s attempt %d served %r (wanted %s in %s)'
                  % (path, attempt, sheet or 'no sheet', self.expect_ver, PREFLIGHT_DIR))
            time.sleep(0.8)
        raise SystemExit('FATAL not the pre-flight copy at ver=%s after three attempts on %s '
                         '(sheet=%r). A wrong install or a wrong header order serves '
                         'the wrong bytes.' % (self.expect_ver, path, (st or {}).get('sheet')))

    def sweep(self, paths, viewport):
        width, height = viewport
        for i, p in enumerate(paths, 1):
            st = self.measure(p, width, height, '%dx%d' % (width, i))
            sheet = st.pop('sheet')
            self.page['%s|%s' % (p, width)] = st
            if sheet not in self.css_sha:
                self.css_sha[sheet] = sheet_sha(sheet, self.auth)
            print('   %3d/%d  %-52s classed=%-5d all=%-5d css=%s'
                  % (i, len(paths), p, st['nClassed'], st['nAll'],
                     self.css_sha[sheet][:12]))
        return self


# --------------------------------------------------------------- comparison ---
# Two normalisations sit between the sweeps and the verdict, and both were
# forced by measurement rather than chosen for convenience.

# 1. THE DECLARED DELETION. The payload batch H6 removed was
#    <script type="application/json" class="sf-formulas-data"> — an ELEMENT, so
#    it counted in nAll and it held a slot in the ordinal keys, which shifts
#    every later sibling by one. It is stripped from the BASELINE only: if the
#    candidate still carries one, that is a failure, not a neutral edit, and
#    [M4]/[M5]/[M8] are what proves this stays true.
PAYLOAD_KEY_RE = re.compile(r'\|\|sf-formulas-data$')

# 2. A PER-REQUEST ID. Gravity Forms stamps its phone widget with a uniqid
#    hash: the same page served twice gave country-item-sx-6ab2509a215d6 and
#    country-item-sx-6ab253bb94fad. That is noise in the same class as the
#    email-obfuscation tokens the byte gate masks.
#
#    The rule is principled, not an enumeration: a run of 8+ hex digits inside
#    an id is a generated token. Enumerating the three ids A/A happened to
#    expose would have been a rule that only covers what was already seen —
#    which is how a gate passes a page nobody swept. Justification for the
#    rule's breadth: no id this site declares contains an 8+ hex run (sf-…,
#    configurator, inquiry-form), and the run is replaced in the KEY only — the
#    id itself is not a rendered property, and no declared change in this batch
#    touches an id. Every distinct id the mask rewrote is printed, so the
#    reader can see exactly what was absorbed.
HEX_RUN_RE = re.compile(r'[0-9a-f]{8,}')

# 3. A SLIDER'S PROGRESS BAR. `.sf-slider-progress__bar` is a 3px fill whose
#    width and transform are written by the slider script every frame — the
#    freeze above cannot stop it, because it is JS writing an inline style, not
#    a CSS animation. A/A pinned it down exactly: 290/292, 293/298, 96/105 on
#    three consecutive runs of the SAME install.
#    Only its box and its transform are dropped; every other computed property
#    is still compared, and [NC8] is what keeps that true — changing this
#    element's background must still fail.
VOLATILE_CLASS = ('sf-slider-progress__bar',)
VOLATILE_PROPS = ('transform',)


def strip_payload(els):
    """(kept-in-order, removed-count) with the declared element dropped."""
    kept, removed = [], 0
    for k, v in els.items():
        idx, tag, eid, cls = k.split('|', 3)
        if PAYLOAD_KEY_RE.search(k):
            removed += 1
            continue
        kept.append((int(idx), tag, eid, cls, v))
    kept.sort(key=lambda t: t[0])
    return kept, removed


def renumber(kept):
    """Re-key by post-filter order, masking generated tokens inside ids and the
    slider fill whose geometry is rewritten every frame.

    Returns (els, [distinct ids rewritten], [volatile elements dropped]).
    """
    out, masked, volatile = {}, [], []
    for n, (_idx, tag, eid, cls, v) in enumerate(kept):
        if HEX_RUN_RE.search(eid):
            masked.append(eid)
            eid = HEX_RUN_RE.sub('<H>', eid)
        if any(c in cls for c in VOLATILE_CLASS):
            f = v.split('|')
            f[0] = '<volatile-box>'
            for p in VOLATILE_PROPS:
                f[PROPS.index(p) + 1] = '<volatile>'
            v = '|'.join(f)
            volatile.append(cls)
        out['%d|%s|%s|%s' % (n, tag, eid, cls)] = v
    return out, masked, volatile


def compare(a, b, aa=False):
    fails, notes = [], []
    keys = [k for k in a['page'] if k in b['page']]
    missing = [k for k in a['page'] if k not in b['page']] + \
              [k for k in b['page'] if k not in a['page']]
    if missing:
        fails.append('the two sweeps cover different pages: %s' % missing[:4])

    # the two sweeps must have rendered DIFFERENT stylesheets, and each must be
    # the commit's own file — otherwise a perfect match proves nothing
    sa = set(a['css_sha'].values())
    sb = set(b['css_sha'].values())
    notes.append('%s sheets: %s' % (a['label'], sorted(s[:12] for s in sa)))
    notes.append('%s sheets: %s' % (b['label'], sorted(s[:12] for s in sb)))
    if len(sa) != 1 or len(sb) != 1:
        fails.append('a sweep served more than one stylesheet: %s / %s' % (sa, sb))
    if sa == sb and not aa:
        fails.append('BOTH sweeps served the SAME sheet — the install did not land')
    if aa:
        notes.append('A/A mode: the two sweeps are the SAME install, so an '
                     'identical sheet is the expected state, and everything '
                     'this run flags is noise by construction.')
    la = local_css_sha(a['sha'])
    lb = local_css_sha(b['sha'])
    notes.append('%s: git+sha256 style.css %s (served %s)'
                 % (a['label'], la[:12], sorted(s[:12] for s in sa)))
    notes.append('%s: git+sha256 style.css %s (served %s)'
                 % (b['label'], lb[:12], sorted(s[:12] for s in sb)))
    if sa != {la}:
        fails.append('%s served a sheet that is not its commit\'s style.css' % a['label'])
    if sb != {lb}:
        fails.append('%s served a sheet that is not its commit\'s style.css' % b['label'])

    moved = 0
    declared_removals = 0
    declared_pages = 0
    masked_ids = []
    volatile_els = []
    for k in sorted(keys):
        pa, pb = a['page'][k], b['page'][k]
        path, width = k.rsplit('|', 1)

        ka, ra = strip_payload(pa['els'])
        kb, rb = strip_payload(pb['els'])
        n_all_a = pa['nAll'] - ra
        n_all_b = pb['nAll'] - rb
        if rb:
            fails.append('%s @%s: the CANDIDATE still carries %d declared-for-'
                         'removal element(s)' % (path, width, rb))
        declared_removals += ra
        if ra:
            declared_pages += 1
        ea, ma, va = renumber(ka)
        eb, mb, vb = renumber(kb)
        masked_ids.extend(ma)
        masked_ids.extend(mb)
        volatile_els.extend(va)
        volatile_els.extend(vb)

        if n_all_a != n_all_b:
            fails.append('%s @%s: element count %d -> %d (after removing the '
                         'declared %d)' % (path, width, n_all_a, n_all_b, ra))
        only_a = [x for x in ea if x not in eb]
        only_b = [x for x in eb if x not in ea]
        if only_a or only_b:
            fails.append('%s @%s: elements present on one side only (%d/%d) e.g. %s'
                         % (path, width, len(only_a), len(only_b),
                            (only_a or only_b)[:2]))
            continue
        diff = [x for x in ea if ea[x] != eb[x]]
        if diff:
            moved += len(diff)
            for x in diff[:4]:
                av, bv = ea[x].split('|'), eb[x].split('|')
                props_changed = [PROPS[i - 1] for i in range(1, min(len(av), len(bv)))
                                 if av[i] != bv[i]]
                fails.append('%s @%s: %s  box %s -> %s  props %s'
                             % (path, width, x.split('|')[2] or x.split('|')[1],
                                av[0], bv[0], props_changed or '(box only)'))
    notes.append('elements compared: %d across %d page-views'
                 % (sum(len(a['page'][k]['els']) for k in keys), len(keys)))
    notes.append('declared deletion applied: %d element(s) on %d page(s), '
                 'stripped from the baseline only (candidate residuals would FAIL)'
                 % (declared_removals, declared_pages))
    notes.append('per-request ids masked: %d occurrence(s), %d distinct: %s'
                 % (len(masked_ids), len(set(masked_ids)),
                    sorted(set(masked_ids))[:6]))
    notes.append('volatile elements (box + transform dropped, rest compared): '
                 '%d occurrence(s) of %s'
                 % (len(volatile_els), sorted(set(volatile_els))[:3]))
    notes.append('differing elements: %d' % moved)
    # the site must have held still for BOTH sweeps, or none of the above means
    # what it says
    for doc in (a, b):
        f = doc.get('fp') or {}
        before, after = f.get('before'), f.get('after')
        if not before or not after:
            fails.append('%s has no quiescence fingerprint — the run predates '
                         'the check and cannot be trusted' % doc['label'])
            continue
        notes.append('%s content fingerprint %s.. -> %s.. (%d posts)'
                     % (doc['label'], before['sha'][:10], after['sha'][:10],
                        after['rows']))
        if before['sha'] != after['sha']:
            fails.append('%s: THE SITE WAS EDITED DURING THIS SWEEP '
                         '(%s.. -> %s..) — a content edit and a batch regression '
                         'are indistinguishable in these numbers'
                         % (doc['label'], before['sha'][:10], after['sha'][:10]))
    for n in notes:
        print('  ' + n)
    for f in fails:
        print('  FAIL ' + f)
    print('  %s  geometry/computed-style: %d differing element(s) over %d page-views'
          % ('PASS' if not fails else 'FAIL', moved, len(keys)))
    return 0 if not fails else 1


def negctl(a, b):
    """Negative controls for the COMPARATOR, not for the site.

    The two normalisations above (strip the declared payload, mask a
    per-request id) are exactly the kind of thing that can quietly turn a gate
    into a rubber stamp: a filter that drops too much will report "no
    difference" for a pair that differs. So each is exercised in both
    directions — what it is meant to absorb must pass, and what it is not meant
    to touch must still fail.
    """
    rows = []

    def run_case(label, mutate, want_fail):
        import copy
        A = copy.deepcopy(a)
        B = copy.deepcopy(b)
        mutate(A, B)
        rc = compare(A, B)
        got_fail = bool(rc)
        rows.append((label, got_fail, want_fail, got_fail == want_fail))
        return got_fail

    def first_key(mut):
        return next(iter(mut['page']))

    def add_payload(A, B):
        k = None
        for pk, pv in B['page'].items():
            if PAYLOAD_KEY_RE.search('\n'.join(pv['els'])):
                continue
            k = pk
            break
        pv = B['page'][k]
        pv['els']['0|SCRIPT||sf-formulas-data'] = '0,0,0,0|none'
        pv['nAll'] += 1

    def drop_element(A, B):
        k = first_key(B)
        pv = B['page'][k]
        pv['els'].pop(next(iter(pv['els'])))
        pv['nAll'] -= 1

    def move_box(A, B):
        k = first_key(B)
        pv = B['page'][k]
        ek = next(iter(pv['els']))
        v = pv['els'][ek].split('|')
        parts = v[0].split(',')
        parts[0] = str(int(parts[0]) + 3)          # shift x by 3px
        v[0] = ','.join(parts)
        pv['els'][ek] = '|'.join(v)

    def change_prop(A, B):
        k = first_key(B)
        pv = B['page'][k]
        ek = next(iter(pv['els']))
        v = pv['els'][ek].split('|')
        v[-1] = '4242'                             # the last PROPS entry is zIndex
        pv['els'][ek] = '|'.join(v)

    def remask_id(A, B):
        """A DIFFERENT hash on a masked id must be absorbed, not reported."""
        hit = False
        for pv in B['page'].values():
            for ek in list(pv['els']):
                idx, tag, eid, cls = ek.split('|', 3)
                if HEX_RUN_RE.search(eid):
                    new = HEX_RUN_RE.sub('ffffffffffff', eid)
                    if new == eid:
                        new = HEX_RUN_RE.sub('eeeeeeeeeeee', eid)
                    pv['els']['%s|%s|%s|%s' % (idx, tag, new, cls)] = pv['els'].pop(ek)
                    hit = True
                    break
            if hit:
                break
        if not hit:
            raise SystemExit('FATAL no masked id in the captures — this control '
                             'cannot run, and that is a finding, not a skip')

    def similar_but_unmasked_id(A, B):
        """An id with NO generated run in it must still be reported."""
        k = first_key(B)
        pv = B['page'][k]
        ek = next(iter(pv['els']))
        idx, tag, eid, cls = ek.split('|', 3)
        pv['els']['%s|%s|%s|%s' % (idx, tag, (eid or 'x') + '-renamed', cls)] \
            = pv['els'].pop(ek)

    def nothing(A, B):
        pass

    def volatile_other_prop(A, B):
        """The volatile element is not exempt from inspection: its OTHER
        properties must still be compared."""
        hit = False
        for pv in B['page'].values():
            for ek, ev in pv['els'].items():
                idx, tag, eid, cls = ek.split('|', 3)
                if any(c in cls for c in VOLATILE_CLASS):
                    f = ev.split('|')
                    f[PROPS.index('backgroundColor') + 1] = 'rgb(9, 9, 9)'
                    pv['els'][ek] = '|'.join(f)
                    hit = True
                    break
            if hit:
                break
        if not hit:
            raise SystemExit('FATAL no volatile element in the captures — '
                             'this control cannot run, and that is a finding')

    print('== comparator negative controls ==')
    run_case('NC1 the candidate still carries a payload element — must FAIL',
             add_payload, True)
    run_case('NC2 an element is missing on the candidate side — must FAIL',
             drop_element, True)
    run_case('NC3 one box moved — must FAIL', move_box, True)
    run_case('NC4 one computed property changed — must FAIL', change_prop, True)
    run_case('NC5 a masked id carries a DIFFERENT hash — must pass '
             '(that is what the mask is for)', remask_id, False)
    run_case('NC6 an id with no generated run, renamed — must FAIL '
             '(the mask rewrites hex runs, not ids in general)',
             similar_but_unmasked_id, True)
    run_case('NC7 the pair is left alone — must pass', nothing, False)
    run_case('NC8 the volatile element changes in a NON-dropped property — '
             'must FAIL (it is not exempt, only its box and transform are)',
             volatile_other_prop, True)

    print()
    bad = 0
    for label, got, want, ok in rows:
        got_s = 'FAIL' if got else 'PASS'
        want_s = 'FAIL' if want else 'PASS'
        print('  %s  %-72s got %s want %s'
              % ('ok  ' if ok else 'FAIL', label[:72], got_s, want_s))
        if not ok:
            bad += 1
    print('  %s  comparator negctl: %d/%d controls behave as declared'
          % ('PASS' if not bad else 'FAIL', len(rows) - bad, len(rows)))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--label')
    ap.add_argument('--sha')
    ap.add_argument('--ver')
    ap.add_argument('--out')
    ap.add_argument('--compare', nargs=2, metavar=('A.json', 'B.json'))
    ap.add_argument('--aa', action='store_true',
                    help='the two files are the SAME install; an identical '
                         'sheet and zero differences are both expected')
    ap.add_argument('--negctl', nargs=2, metavar=('BASE.json', 'CAND.json'),
                    help='exercise the comparator itself, both directions')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or
                    'sfdev:VkEws18Kl5V1qp3TpZ6s')
    ap.add_argument('--paths', default=PATHS)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--phone', action='store_true', default=True)
    args = ap.parse_args()

    if args.negctl:
        return negctl(json.load(open(args.negctl[0])),
                      json.load(open(args.negctl[1])))

    if args.compare:
        a = json.load(open(args.compare[0]))
        b = json.load(open(args.compare[1]))
        return compare(a, b, aa=args.aa)

    for f in ('label', 'sha', 'ver', 'out'):
        if not getattr(args, f):
            ap.error('--%s is required for a sweep' % f)

    with open(args.paths, encoding='utf-8') as fh:
        paths = [p.strip() for p in fh if p.strip()]
    if args.limit:
        paths = paths[:args.limit]

    s = Sweep(args.auth, args.label, args.sha, args.ver)
    s.attach()
    s.fp['before'] = content_fingerprint(args.auth)   # the site must be still
    print('== desktop %dx%d, %d pages ==' % (DESKTOP[0], DESKTOP[1], len(paths)))
    s.sweep(paths, DESKTOP)
    phone = [p for p in PHONE_SAMPLE if p in paths]
    print('== phone %dx%d, %d pages (sample, stated as such) =='
          % (PHONE[0], PHONE[1], len(phone)))
    s.sweep(phone, PHONE)
    s.fp['after'] = content_fingerprint(args.auth)
    run(['agent-browser', 'close', '--all'])

    doc = {'label': s.label, 'sha': s.sha, 'ver': s.ver, 'fp': s.fp,
           'css_sha': s.css_sha, 'page': s.page, 'errors': s.errors}
    json.dump(doc, open(args.out, 'w'), indent=1)
    print('wrote %s (%d page-views, %d probe errors)'
          % (args.out, len(s.page), len(s.errors)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
