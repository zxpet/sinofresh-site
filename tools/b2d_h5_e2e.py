#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5 — the browser pass: is the schema the served page describes true?

WHY A BROWSER PASS EXISTS FOR A BATCH WITH NO CSS CHANGE

Batch H5 does not touch layout, so geometry is not the interesting variable
here and this sweep does not re-measure boxes. What it does measure is the one
thing no capture can: whether the schema, as a real JS engine parses it in the
served document, agrees with what a real DOM renders on the same page.

The byte gate already compares the schema text against the captured HTML. That
is a statement about bytes. This pass is a statement about the page:

  * every ld+json block on all 75 pages must PARSE — a "the JSON is still
    valid" claim made by actually running JSON.parse in the browser, not by a
    regex that would accept a truncated block;
  * each dosage page's Product.additionalProperty must equal the four rows of
    its own .sf-facts-mini band, read back out of the DOM — the same reading
    the PHP does, done independently;
  * each formula page's isRelatedTo must equal the cards the page actually
    links to, in order; audience must be present exactly where the page's own
    dosage page names a species; and offers must be absent on all 58 Product
    pages (the tier table is empty, so the renderer has nothing to emit);
  * the alt carriers must agree: on one page, one image file carries one alt,
    and it is the declared post-batch string. This is checked on the DOM after
    the browser has resolved the document, which is the setting the defect
    lived in;
  * zero console errors on every page visited.

Provenance is by CONTENT, because the version token does not move in this
batch: the served stylesheet must come from the pre-flight directory, and the
post-batch logo alt must be present. A wrong header order serves the live theme
and every number below would then describe the wrong bytes, silently.

Scope, stated plainly: desktop only (1440x900), all 75 paths, one viewport. The
batch changes no CSS, no markup order and no geometry, so a second viewport
would vary a variable this batch does not touch; what is claimed here is a
full-page sweep at one viewport, and it is claimed as such.

usage:
    b2d_h5_e2e.py --sha <preflight-sha> --out e2e.json [--auth user:pass]
    b2d_h5_e2e.py --report e2e.json
"""
import argparse
import base64
import collections
import html as htmlmod
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
sys.path.insert(0, HERE)
import b2d_h5_apply as app            # noqa: E402  the declared alt pairs

DESKTOP = (1440, 900)
LOGO_NEW = app.LOGO_NEW
# The byte-level declaration carries the attribute (`alt="SINO FRESH logo"`),
# but the DOM reports the *value*. Comparing a value against an attribute
# string is a match that can never be made, so the two spellings are kept as
# two names rather than folded into one.
LOGO_ALT = LOGO_NEW[len('alt="'):-1]
KNOWN_ABOUT = [
    'Soft Chews', 'Tablets', 'Powders', 'Pastes', 'Drops', 'Liquids',
    'Fish Oil', 'Dental Chews',
    'Pet Supplement OEM/ODM Manufacturing', 'Private Label Pet Supplements',
]
DOSAGE_ORDER = ['MOQ', 'Lead time', 'Certifications', 'Packaging formats']
DOSAGE_LABEL = {'MOQ': 'MOQ', 'Lead time': 'Lead time',
                'Certifications': 'Certifications',
                'Packaging formats': 'Packaging'}
FORMULA_NAMES = ['Ingredients', 'Guaranteed Analysis', 'Standard Specs']

PROBE = r"""
(function () {
  try {
    var ld = [];
    var blocks = document.querySelectorAll('script[type="application/ld+json"]');
    for (var i = 0; i < blocks.length; i++) {
      try { ld.push(JSON.parse(blocks[i].textContent)); }
      catch (e) { ld.push({__parse_error__: String(e && e.message ? e.message : e)}); }
    }
    var facts = {};
    var rows = document.querySelectorAll('.sf-facts-mini__value[data-label]');
    for (var j = 0; j < rows.length; j++) {
      facts[rows[j].getAttribute('data-label')] =
        (rows[j].textContent || '').replace(/\s+/g, ' ').trim();
    }
    function hrefs(sel) {
      var out = [];
      var ns = document.querySelectorAll(sel);
      for (var i = 0; i < ns.length; i++) { out.push(ns[i].getAttribute('href')); }
      return out;
    }
    var h1 = document.querySelector('h1');
    var crumb = document.querySelector('.sf-breadcrumb__crumb--form');
    var more = document.querySelector('.sf-fdetail-more > h2');
    var stage = document.querySelector('.sf-gallery__stage');
    var frame = document.querySelector('.sf-gallery__slide[id$="-1"]');
    var form = null;
    if (frame && frame.id) {
      var m = /^sf-gallery-slide-(.+)-1$/.exec(frame.id);
      if (m) { form = m[1]; }
    }
    // Every img on the page whose file is the page's own dosage still, with
    // the alt the browser resolved it to.
    // Every img on the page whose file is the page's own dosage still.
    // Two kinds live here and they are NOT interchangeable:
    //   * the still itself (gallery frame, card media) must carry the string;
    //   * the gallery thumbnail strip is built at RUN TIME, one img inside a
    //     `role="tab"` button that already carries the string as its
    //     accessible name — so that img's alt MUST be empty, or the same
    //     image is announced twice. It does not exist in the served HTML at
    //     all, which is why the capture-only gates never see it.
    // The tab that stands for the still is identified by aria-controls pointing
    // at the frame, not by position: reading "the first thumbnail" would be a
    // coincidence that a reordered gallery would turn into a wrong pass.
    var alts = [];
    var thumbAlts = [];
    var imgs = document.querySelectorAll('img[alt]');
    for (var k = 0; k < imgs.length; k++) {
      var src = imgs[k].getAttribute('src') || '';
      var f = src.split('?')[0].split('/').pop();
      if (!form || f !== form + '.webp') { continue; }
      if (imgs[k].closest('.sf-gallery__thumbs')) { continue; }  // see below
      alts.push(imgs[k].getAttribute('alt'));
    }
    var prodTabAria = null;
    if (frame && frame.id) {
      var tb = document.querySelector('.sf-gallery__thumb[aria-controls="' + frame.id + '"]');
      prodTabAria = tb ? tb.getAttribute('aria-label') : null;
    }
    var thumbImgs = document.querySelectorAll('.sf-gallery__thumbs img');
    for (var t = 0; t < thumbImgs.length; t++) {
      thumbAlts.push(thumbImgs[t].getAttribute('alt'));
    }
    return {
      href: location.href,
      sheet: (function () {
        // The theme's STYLESHEET, not "the first link whose href mentions the
        // theme": that selector matches the favicon first (it lives in the same
        // directory), and a favicon proves nothing about which theme rendered
        // the page. rel=stylesheet is the part that makes this a provenance
        // check rather than a directory-string test.
        var l = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');
        return l ? l.href : '';
      })(),
      vw: window.innerWidth,
      ld: ld,
      facts: facts,
      tiles: hrefs('.sf-tile__media > a'),
      cards: hrefs('.sf-fcard__name > a'),
      h1: h1 ? (h1.textContent || '').replace(/\s+/g, ' ').trim() : '',
      crumb: crumb ? [crumb.getAttribute('href'),
                      (crumb.textContent || '').replace(/\s+/g, ' ').trim()] : null,
      more: more ? (more.textContent || '').replace(/\s+/g, ' ').trim() : '',
      form: form,
      stageAria: stage ? stage.getAttribute('aria-label') : null,
      frameLabel: frame ? frame.getAttribute('data-label') : null,
      frameAlt: (frame && frame.querySelector('img'))
        ? frame.querySelector('img').getAttribute('alt') : null,
      stillAlts: alts,
      thumbAlts: thumbAlts,
      prodTabAria: prodTabAria,
      logoAlt: (function () {
        var l = document.querySelector('img.custom-logo, .custom-logo img, img[class*="logo"]');
        return l ? l.getAttribute('alt') : null;
      })()
    };
  } catch (e) {
    return {error: String(e && e.message ? e.message : e)};
  }
})()
"""


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


def all_paths():
    out = []
    with open(PATHS, encoding='utf-8') as fh:
        for line in fh:
            p = line.strip()
            if p and not p.startswith('#'):
                out.append(p)
    return out


def species_of(headline):
    m = re.search(r'\bfor\s+(.+)$', headline, re.I)
    if not m:
        return []
    out = []
    for w in re.findall(r'\b(dogs?|cats?|puppies|kittens)\b', m.group(1), re.I):
        w = w.capitalize()
        w = {'Dog': 'Dogs', 'Cat': 'Cats', 'Puppy': 'Puppies',
             'Kitten': 'Kittens'}.get(w, w)
        if w not in out:
            out.append(w)
    return out


class Report(object):
    def __init__(self):
        self.fails = []
        self.passes = 0
        self.notes = collections.OrderedDict()

    def ok(self, label, cond, detail=''):
        if cond:
            self.passes += 1
        else:
            self.fails.append('%s%s' % (label, (' — ' + detail) if detail else ''))
        return bool(cond)

    def eq(self, label, got, want):
        return self.ok(label, got == want, 'got %r want %r' % (got, want))


class Sweep(object):
    def __init__(self, auth, sha):
        self.auth = auth
        self.sha = sha
        self.page = {}
        self.probe_errors = []
        # When set, console_errors() replays this list instead of asking the
        # browser. Replay mode has no browser session of its own, so without
        # this the assertion would read whatever session happens to be open —
        # an empty list on a fresh session, i.e. a vacuous pass on the one
        # check that has no other side (a capture cannot record a console).
        self.recorded_errors = None

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

    def measure(self, path, tag):
        url = HOST + path + '?sfe2e=%s%s' % (tag, time.strftime('%H%M%S'))
        width, height = DESKTOP
        st = None
        for attempt in (1, 2, 3):
            run(['agent-browser', 'open', url])
            run(['agent-browser', 'reload'])          # reload keeps the header
            run(['agent-browser', 'set', 'viewport', str(width), str(height)])
            time.sleep(0.6)
            st = ev(PROBE)
            if isinstance(st, dict) and 'error' in st:
                self.probe_errors.append((path, 'probe: %s' % st['error']))
                st = None
                time.sleep(0.8)
                continue
            # Provenance, by content, and not relaxed by the retry: a wrong
            # header order serves the live theme and every number below would
            # then describe the wrong bytes. The version token does not move in
            # this batch, so the copy is identified by its directory and by the
            # post-batch logo alt it renders.
            sheet = (st or {}).get('sheet') or ''
            if PREFLIGHT_DIR in sheet and st.get('logoAlt') == LOGO_ALT:
                if st.get('vw') and abs(st['vw'] - width) > 2:
                    raise SystemExit('FATAL viewport did not take: %s != %s'
                                     % (st['vw'], width))
                return st
            print('   ..   %s attempt %d served sheet=%r logoAlt=%r'
                  % (path, attempt, sheet or 'none', st.get('logoAlt')))
            time.sleep(0.8)
        raise SystemExit('FATAL not the pre-flight copy after three attempts on %s '
                         '(sheet=%r, logoAlt=%r). A wrong install or a wrong header '
                         'order serves the wrong bytes.'
                         % (path, (st or {}).get('sheet'), (st or {}).get('logoAlt')))

    def sweep(self, paths):
        for i, p in enumerate(paths, 1):
            st = self.measure(p, str(i))
            self.page[p] = st
            print('   %3d/%d  %-52s blocks=%d form=%s'
                  % (i, len(paths), p, len(st['ld']), st['form']))
        return self

    def console_errors(self):
        if self.recorded_errors is not None:
            return self.recorded_errors
        rc, out, _ = run(['agent-browser', 'errors'])
        t = out.strip()
        if not t or t.lower() in ('no errors', 'none', '[]'):
            return []
        try:
            return json.loads(t)
        except Exception:
            return [t]


def judge(rep, sweep):
    pages = sweep.page

    # ---------------------------------------------------------------- parse ---
    bad_parse = []
    blocks = 0
    for k, st in sorted(pages.items()):
        blocks += len(st['ld'])
        for i, o in enumerate(st['ld']):
            if '__parse_error__' in o:
                bad_parse.append('%s block %d: %s' % (k, i, o['__parse_error__']))
    rep.eq('[E1] every ld+json block parses in the browser', bad_parse[:6], [])
    rep.ok('[E1] blocks seen', blocks > 0, '%d blocks over %d pages' % (blocks, len(pages)))
    rep.notes['blocks'] = blocks

    # --------------------------------------------------------- page classes ---
    dosage = sorted(k for k, st in pages.items() if st['facts'])
    formula = sorted(k for k, st in pages.items() if st['crumb'])
    prod = sorted(k for k, st in pages.items()
                  if any(o.get('@type') == 'Product' for o in st['ld']))
    rep.eq('[E2] dosage pages (the facts band marks them)', len(dosage), 16)
    rep.eq('[E2] formula pages (the form crumb marks them)', len(formula), 42)
    rep.eq('[E2] Product pages', len(prod), 58)

    # the species each dosage page states, so a formula page can be checked
    # against the exact page its crumb points at
    species_by_page = {}
    for k in dosage:
        species_by_page[slug_of(k)] = species_of(pages[k]['h1'])

    ka_bad, prop_bad, rel_bad, aud_bad, off_bad, crumb_bad = [], [], [], [], [], []
    prop_ok = rel_ok = 0
    aud_present = []
    for k in sorted(pages):
        st = pages[k]
        pr = next((o for o in st['ld'] if o.get('@type') == 'Product'), None)
        org = next((o for o in st['ld'] if o.get('@type') == 'Organization'), None)
        if org is not None and org.get('knowsAbout') != KNOWN_ABOUT:
            ka_bad.append('%s: %r' % (k, org.get('knowsAbout')))

        # offers must be absent while the tier table is empty
        if pr is not None and 'offers' in pr:
            off_bad.append('%s: offers is present' % k)

        # audience, against the page's own form page
        if pr is not None:
            if k in dosage:
                want = species_by_page[slug_of(k)]
            elif k in formula:
                crumb = st['crumb']
                want = species_by_page.get(slug_of_url(crumb[0]), [])
                if slug_of_url(crumb[0]) not in species_by_page:
                    crumb_bad.append('%s: crumb %r is not a dosage page'
                                     % (k, crumb[0]))
                elif crumb[1] != st['more'].replace('More ', '').replace(' Formulas', ''):
                    crumb_bad.append('%s: crumb %r != More heading %r'
                                     % (k, crumb[1], st['more']))
            else:
                want = []
            got = [a.get('audienceType') for a in pr.get('audience', [])] \
                if 'audience' in pr else []
            if got != want:
                aud_bad.append('%s: audience %r != page says %r' % (k, got, want))
            elif got:
                aud_present.append(k)

        if pr is None:
            continue

        # additionalProperty against the DOM's own band
        props = pr.get('additionalProperty')
        if k in dosage:
            order = [DOSAGE_LABEL[l] for l in DOSAGE_ORDER]
            want = [{'@type': 'PropertyValue', 'name': DOSAGE_LABEL[l],
                     'value': st['facts'][l]} for l in DOSAGE_ORDER]
            if props != want:
                prop_bad.append('%s: %r != the DOM band %r' % (k, props, want))
            elif [p['name'] for p in props] != order:
                prop_bad.append('%s: names %r' % (k, [p['name'] for p in props]))
            else:
                prop_ok += 1
        elif k in formula:
            names = [p['name'] for p in props] if props else []
            if names != FORMULA_NAMES:
                prop_bad.append('%s: formula names %r' % (k, names))
            else:
                prop_ok += 1
        else:
            if props is not None:
                prop_bad.append('%s: not a product page but has additionalProperty' % k)

        # isRelatedTo against the links the DOM shows, in order
        if 'isRelatedTo' not in pr:
            if k in dosage or k in formula:
                rel_bad.append('%s: no isRelatedTo' % k)
            continue
        urls = [r.get('url') for r in pr['isRelatedTo']]
        m = re.match(r'(https?://[^/]+)', st['href'])
        origin = m.group(1) if m else ''
        if k in dosage:
            want_urls = [(origin + u) if u.startswith('/') else u for u in st['tiles']]
        elif k in formula:
            want_urls = st['cards']
        else:
            want_urls = []
        if urls != want_urls:
            rel_bad.append('%s: %r != the DOM links %r' % (k, urls, want_urls))
        else:
            rel_ok += 1

    rep.eq('[E3] knowsAbout is the ten declared topics on every page', ka_bad[:6], [])
    rep.eq('[E4] additionalProperty equals the DOM facts band', prop_bad[:6], [])
    rep.eq('[E4] additionalProperty pages accounted for', prop_ok, 58)
    rep.eq('[E5] isRelatedTo equals the DOM links, in order', rel_bad[:6], [])
    rep.eq('[E5] isRelatedTo on all 58 Product pages', rel_ok, 58)
    rep.eq('[E6] audience matches the page the crumb points at', aud_bad[:6], [])
    rep.eq('[E6] the crumb label equals the More heading', crumb_bad[:6], [])
    rep.eq('[E7] offers is absent on all 58 Product pages (empty tier table)',
           off_bad[:6], [])
    rep.notes['audience_pages'] = aud_present

    # -------------------------------------------------------- alt carriers ---
    declared = dict(app.alt_pairs())
    label_by_file = collections.defaultdict(set)
    for k, st in pages.items():
        if not st['form']:
            continue
        m = re.match(r'SINO FRESH (.+?) private label pet supplement product',
                     st['frameAlt'] or '')
        if m:
            label_by_file[st['form'] + '.webp'].add(m.group(1))
    rep.eq('[E8] the frame alt names one label per form, site-wide',
           sorted(f for f, v in label_by_file.items() if len(v) != 1), [])
    # values are sets (the point of the assertion above: one label per form),
    # so index by iterator — v[0] is a TypeError on a set, not an empty value.
    label_of = {f: next(iter(v)) for f, v in label_by_file.items() if len(v) == 1}

    conflicts, wrong = [], []
    for k, st in sorted(pages.items()):
        vals = set()
        if st['frameAlt'] is not None:
            vals.add(st['frameAlt'])
        if st['stageAria'] is not None:
            vals.add(st['stageAria'])
        if st['frameLabel'] is not None:
            vals.add(st['frameLabel'])
        if st.get('prodTabAria') is not None:
            vals.add(st['prodTabAria'])
        vals.update(st['stillAlts'])
        if len(vals) > 1:
            conflicts.append('%s: %r' % (k, sorted(vals)))
        if st['form']:
            want = declared.get('SINO FRESH %s private label pet supplement product'
                                % label_of.get(st['form'] + '.webp', ''))
            if want and vals and vals != {want}:
                wrong.append('%s: %r != %r' % (k, sorted(vals), want))
    rep.eq('[E8] CARRIERS — one page, one image file, one name', conflicts[:6], [])
    rep.eq('[E8] product pages state the declared name (DOM-resolved)', wrong[:6], [])
    # The fourth carrier is the one no capture can hold: the thumbnail strip is
    # built by the gallery script at run time. Its imgs MUST be decorative
    # (`alt=""`) because the tab above each already carries the name — an alt
    # here would announce the same image twice. Asserted, not ignored: "we
    # checked and it is empty on purpose" is a different claim from "we did not
    # look", and only the first one is evidence.
    thumb_bad = ['%s: %r' % (k, sorted(set(st.get('thumbAlts') or [])))
                 for k, st in sorted(pages.items())
                 if set(st.get('thumbAlts') or []) - {''}]
    rep.eq('[E8] the run-time thumbnail strip stays decorative (alt="")',
           thumb_bad[:6], [])
    rep.notes['thumb_pages'] = len([1 for st in pages.values()
                                    if (st.get('thumbAlts') or [])])
    rep.notes['carrier_pages'] = len([1 for st in pages.values() if st['form']])

    # the logo, DOM-resolved
    bad_logo = ['%s: %r' % (k, st['logoAlt']) for k, st in sorted(pages.items())
                if st['logoAlt'] != LOGO_ALT]
    rep.eq('[E9] the site logo announces the normalised alt on all 75 pages',
           bad_logo[:6], [])

    # ------------------------------------------------------------- console ---
    errs = sweep.console_errors()
    rep.eq('[E10] no console errors on any page visited', errs[:3], [])
    rep.eq('[E10] no probe failures', sweep.probe_errors[:3], [])
    rep.notes['console_errors'] = len(errs)
    return rep


def slug_of(k):
    p = k if k.startswith('/') else '/' + k
    return p.strip('/').replace('/', '__')


def slug_of_url(u):
    p = re.sub(r'^https?://[^/]+', '', u)
    return p.strip('/').replace('/', '__')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sha')
    ap.add_argument('--out')
    ap.add_argument('--report')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    if args.report:
        data = json.load(open(args.report, encoding='utf-8'))
        sweep = Sweep('', '')
        sweep.page = data['page']
        sweep.probe_errors = data.get('probe_errors', [])
        sweep.recorded_errors = data.get('console_errors', [])
        rep = Report()
        judge(rep, sweep)
        print('H5 BROWSER PASS (from %s): %s — %d passed, %d failed'
              % (os.path.basename(args.report),
                 'PASS' if not rep.fails else 'FAIL', rep.passes, len(rep.fails)))
        for f in rep.fails:
            print('  FAIL %s' % f)
        for k, v in rep.notes.items():
            print('  note %s: %s' % (k, json.dumps(v)[:220]))
        return 0 if not rep.fails else 1

    if not (args.sha and args.out):
        ap.error('--sha and --out are required unless --report is used')
    paths = all_paths()
    if args.limit:
        paths = paths[:args.limit]
    print('H5 browser pass: %d pages, %dx%d, pre-flight copy at %s'
          % (len(paths), DESKTOP[0], DESKTOP[1], args.sha[:12]))
    s = Sweep(args.auth, args.sha)
    s.attach()
    s.sweep(paths)
    json.dump({'sha': args.sha, 'page': s.page,
               'probe_errors': s.probe_errors,
               'console_errors': s.console_errors()},
              open(args.out, 'w', encoding='utf-8'), indent=1)
    print('wrote %s' % args.out)
    rep = Report()
    judge(rep, s)
    print()
    print('H5 BROWSER PASS: %s — %d passed, %d failed'
          % ('PASS' if not rep.fails else 'FAIL', rep.passes, len(rep.fails)))
    for f in rep.fails:
        print('  FAIL %s' % f)
    return 0 if not rep.fails else 1


if __name__ == '__main__':
    sys.exit(main())
