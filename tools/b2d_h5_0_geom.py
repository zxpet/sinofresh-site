#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5-0 — the behavioural pass: does the hero band still render as it did?

WHY A BROWSER PASS EXISTS FOR A TWO-LINE CHANGE

The byte gate proves the rendered document changed by exactly the declared
amount and nothing else. It cannot see the two things this batch can break,
because neither is a byte of markup:

  * computed style. The hero heading lost its element name and kept its class.
    A class rule beats an element rule, so four of the five properties the
    h1 carried in theme.json (size, line-height, tracking, colour) were already
    overridden and came along for free — but font-weight was never declared on
    the class, so it *was* the element rule supplying 700. Measured here:
    every property, both sides, must be identical.
  * the print cascade. The print block reaches this band through an
    element-name list, and that rule is the only thing that turns the title
    black. Measured here by resolving the print-media colour that actually
    applies to the element, which is a question no snapshot can answer.

The rest of the pass is geometry: a wide claim like "the hero band is
untouched" is really four boxes, and the one that may legitimately move is the
two-column band below the hero, because the parameters column gained a heading.

METHOD

Two sweeps of the same 42 pages against two installations of the pre-flight
copy — the baseline commit, then the candidate — compared page by page. Not
one sweep compared against remembered numbers: the numbers are the thing under
test.

  b2d_h5_0_geom.py --label baseline  --sha <baseline-sha> --out base.json
  b2d_h5_0_geom.py --label candidate --sha <cand-sha>     --out cand.json
  b2d_h5_0_geom.py --compare base.json cand.json

The phone sweep is a six-page sample rather than all 42. Stated plainly
because the asymmetry matters: what a narrower viewport changes is the clamp
input and the band's column count, both viewport-level facts, so the property
being asserted is viewport-independent and the desktop sweep is the complete
one. The sample exists to catch a breakpoint-dependent box, not to claim
completeness it does not have.

usage:
    b2d_h5_0_geom.py --label L --sha SHA --out OUT.json [--auth user:pass]
                     [--desktop-limit N]
    b2d_h5_0_geom.py --compare A.json B.json
"""
import argparse
import base64
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

DESKTOP = (1440, 900)
PHONE = (390, 844)

# Six pages in the phone sample: the briefest and the longest titles on each
# language side, so a wrap difference has somewhere to show up.
PHONE_SAMPLE = [
    '/formulas/bladder-support-powder/',
    '/formulas/joint-support-soft-chews/',
    '/formulas/urinary-care-drops/',
    '/zh/formulas/bladder-support-powder/',
    '/zh/formulas/joint-support-soft-chews/',
    '/zh/formulas/urinary-care-drops/',
]

PROBE = r"""
(async () => {
  try {
    await (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve());
    const box = el => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {x: Math.round(r.left), y: Math.round(r.top + window.scrollY),
              w: Math.round(r.width), h: Math.round(r.height)};
    };
    const cs = (el, props) => {
      if (!el) return null;
      const c = getComputedStyle(el), o = {};
      props.forEach(p => { o[p] = c[p] === undefined ? c.getPropertyValue(p) : c[p]; });
      return o;
    };
    const TEXT_PROPS = ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight',
                        'letterSpacing', 'color', 'display', 'textAlign',
                        'marginTop', 'marginBottom', 'fontStyle'];
    const BOX_PROPS = TEXT_PROPS.concat(['paddingTop', 'paddingBottom', 'borderTopWidth']);

    const heroTitle = document.querySelector('.sf-formula-hero__title');
    const heroBand = document.querySelector('section.sf-formula-hero');
    const band = document.querySelector('section.sf-fdetail2');
    const column = document.querySelector('.sf-fdetail2__side');
    const media = document.querySelector('.sf-fdetail2__media');
    const newTitle = document.querySelector('h1.sf-fdetail2__title');
    const intro = document.querySelector('p.sf-fdetail2__intro');
    const h1s = [...document.querySelectorAll('h1')];
    const sheet = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');

    // The colour that actually applies to the hero heading when printing:
    // every matching colour declaration inside a print media block, in
    // document order, with its !important flag. Computed the same way on both
    // sides, so comparing the lists compares the cascade.
    const printColors = el => {
      const out = [];
      if (!el) return out;
      for (const s of document.styleSheets) {
        let rules;
        try { rules = s.cssRules; } catch (e) { continue; }
        for (const r of rules) {
          if (!r.conditionText || !/print/.test(r.conditionText)) continue;
          if (!r.cssRules) continue;
          for (const q of r.cssRules) {
            if (!q.selectorText || !q.style) continue;
            const v = q.style.getPropertyValue('color');
            if (!v) continue;
            let m = false;
            try { m = el.matches(q.selectorText); } catch (e) { m = false; }
            if (m) out.push({sel: q.selectorText.replace(/\s+/g, ' ').trim(),
                             val: v, important: q.style.getPropertyPriority('color') === 'important'});
          }
        }
      }
      return out;
    };

    return {
      href: location.href,
      vw: window.innerWidth,
      sheet: sheet ? sheet.getAttribute('href') : null,
      docHeight: document.documentElement.scrollHeight,
      h1Count: h1s.length,
      h1Texts: h1s.map(h => h.textContent.replace(/\s+/g, ' ').trim()),
      heroTitle: heroTitle ? {
        tag: heroTitle.tagName.toLowerCase(),
        cls: heroTitle.className,
        text: heroTitle.textContent.replace(/\s+/g, ' ').trim(),
        box: box(heroTitle),
        cs: cs(heroTitle, BOX_PROPS),
        printColors: printColors(heroTitle),
      } : null,
      heroBand: heroBand ? {box: box(heroBand), bg: getComputedStyle(heroBand).backgroundColor} : null,
      band: band ? {box: box(band)} : null,
      column: column ? {tag: column.tagName.toLowerCase(), box: box(column)} : null,
      media: media ? {box: box(media)} : null,
      newTitle: newTitle ? {
        tag: newTitle.tagName.toLowerCase(),
        text: newTitle.textContent.replace(/\s+/g, ' ').trim(),
        box: box(newTitle),
        cs: cs(newTitle, TEXT_PROPS),
        firstInColumn: column ? column.firstElementChild === newTitle : null,
        beforeIntro: intro ? (newTitle.compareDocumentPosition(intro) & Node.DOCUMENT_POSITION_FOLLOWING) > 0 : null,
      } : null,
    };
  } catch (e) {
    return {error: String(e && e.message ? e.message : e)};
  }
})()
"""


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180):
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


def detail_paths():
    out = []
    with open(PATHS, encoding='utf-8') as fh:
        for line in fh:
            p = line.strip()
            if re.match(r'^/(zh/)?formulas/[^/]+/$', p):
                out.append(p)
    return out


class Sweep(object):
    def __init__(self, auth, label, sha, expect_ver):
        self.auth = auth
        self.label = label
        self.sha = sha
        self.expect_ver = expect_ver
        self.page = {}
        self.errors = []

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

    def measure(self, path, width, height, tag):
        url = HOST + path + '?sfgeom=%s%s' % (tag, time.strftime('%H%M%S'))
        st = None
        for attempt in (1, 2, 3):
            run(['agent-browser', 'open', url])
            run(['agent-browser', 'reload'])          # reload keeps the header
            run(['agent-browser', 'set', 'viewport', str(width), str(height)])
            time.sleep(0.6)
            st = ev(PROBE)
            if isinstance(st, dict) and 'error' in st:
                self.errors.append((path, 'probe: %s' % st['error']))
                st = None
                time.sleep(0.8)
                continue
            # Provenance, and it is not relaxed by the retry: a wrong header
            # order serves the live theme and every number below would then
            # describe the wrong bytes, silently. The directory alone is not
            # enough — the copy must also be advertising the version this
            # sweep expects, which is what proves the install actually landed.
            sheet = (st or {}).get('sheet') or ''
            if PREFLIGHT_DIR in sheet and ('ver=' + self.expect_ver) in sheet:
                if st.get('vw') and abs(st['vw'] - width) > 2:
                    raise SystemExit('FATAL viewport did not take: %s != %s' % (st['vw'], width))
                return st
            print('   ..   %s attempt %d served %r (wanted %s in %s)'
                  % (path, attempt, sheet or 'no sheet', self.expect_ver, PREFLIGHT_DIR))
            time.sleep(0.8)
        raise SystemExit('FATAL not the pre-flight copy at ver=%s after three attempts on %s '
                         '(sheet=%r). A wrong install or a wrong header order serves '
                         'the wrong bytes.' % (self.expect_ver, path, (st or {}).get('sheet')))

    def sweep(self, paths, viewport, desktop_limit=None):
        width, height = viewport
        items = paths if not desktop_limit else paths[:desktop_limit]
        for i, p in enumerate(items, 1):
            st = self.measure(p, width, height, '%dx%d' % (width, i))
            self.page['%s|%s' % (p, width)] = st
            print('   %3d/%d  %-52s h1=%s hero=%s' %
                  (i, len(items), p,
                   st['h1Count'],
                   (st['heroTitle'] or {}).get('tag')))
        return self


def compare(a, b):
    fails, notes = [], []
    keys = [k for k in a['page'] if k in b['page']]
    missing = [k for k in a['page'] if k not in b['page']] + \
              [k for k in b['page'] if k not in a['page']]
    if missing:
        fails.append('the two sweeps cover different pages: %s' % missing[:4])

    for k in sorted(keys):
        pa, pb = a['page'][k], b['page'][k]
        path, width = k.rsplit('|', 1)

        if (pa.get('heroTitle') or {}).get('tag') != 'h1':
            fails.append('%s @%s: the baseline hero heading is not an h1 (%s)'
                         % (path, width, (pa.get('heroTitle') or {}).get('tag')))
        if (pb.get('heroTitle') or {}).get('tag') != 'div':
            fails.append('%s @%s: the candidate hero heading is not a div (%s)'
                         % (path, width, (pb.get('heroTitle') or {}).get('tag')))

        ta, tb = pa.get('heroTitle') or {}, pb.get('heroTitle') or {}
        if ta.get('box') != tb.get('box'):
            fails.append('%s @%s: the hero heading moved %s -> %s'
                         % (path, width, ta.get('box'), tb.get('box')))
        if ta.get('cs') != tb.get('cs'):
            diff = {p: (ta['cs'].get(p), tb['cs'].get(p))
                    for p in set(ta.get('cs') or {}) | set(tb.get('cs') or {})
                    if (ta.get('cs') or {}).get(p) != (tb.get('cs') or {}).get(p)}
            fails.append('%s @%s: the hero heading renders differently: %s' % (path, width, diff))
        if ta.get('text') != tb.get('text'):
            fails.append('%s @%s: the hero heading text changed' % (path, width))

        if (pa.get('heroBand') or {}).get('box') != (pb.get('heroBand') or {}).get('box'):
            fails.append('%s @%s: the hero band moved %s -> %s'
                         % (path, width, (pa.get('heroBand') or {}).get('box'),
                            (pb.get('heroBand') or {}).get('box')))
        if pa.get('band', {}).get('box') != pb.get('band', {}).get('box'):
            ba = (pa.get('band') or {}).get('box') or {}
            bb = (pb.get('band') or {}).get('box') or {}
            for p in ('x', 'y', 'w'):
                if ba.get(p) != bb.get(p):
                    fails.append('%s @%s: the band\'s %s moved %s -> %s'
                                 % (path, width, p, ba.get(p), bb.get(p)))

        if (pa.get('column') or {}).get('tag') != 'aside':
            fails.append('%s @%s: the baseline column is not an aside' % (path, width))
        if (pb.get('column') or {}).get('tag') != 'div':
            fails.append('%s @%s: the candidate column is not a div' % (path, width))

        # The column gains a heading, so its box is SUPPOSED to grow — what
        # must not move is where it sits and how wide it is. The growth is not
        # allowed to be "roughly a line": it has to be exactly the heading's
        # own box plus the heading's own bottom margin, measured, because
        # anything else means the heading is interacting with a rule that was
        # not accounted for.
        cba = (pa.get('column') or {}).get('box') or {}
        cbb = (pb.get('column') or {}).get('box') or {}
        for p in ('x', 'y', 'w'):
            if cba.get(p) != cbb.get(p):
                fails.append('%s @%s: the parameters column\'s %s moved %s -> %s'
                             % (path, width, p, cba.get(p), cbb.get(p)))
        nt0 = pb.get('newTitle')
        if nt0 and cba.get('h') is not None and cbb.get('h') is not None:
            want = cba['h'] + nt0['box']['h'] + int(re.sub(r'[^0-9-]', '', nt0['cs']['marginBottom'] or '0'))
            if cbb['h'] != want:
                fails.append('%s @%s: the column grew by %d, wanted %d (heading box %d + margin %s)'
                             % (path, width, cbb['h'] - cba['h'], want - cba['h'],
                                nt0['box']['h'], nt0['cs']['marginBottom']))

        # The band is a grid, and it must still behave like one: side by side
        # its height is set by the taller column, stacked by their sum. So it
        # grows by the column's growth only where the column was the taller of
        # the two — which is what makes "the band did not move" a measured
        # claim rather than an assumption.
        ba = (pa.get('band') or {}).get('box') or {}
        bb = (pb.get('band') or {}).get('box') or {}
        ma = (pa.get('media') or {}).get('box') or {}
        mb = (pb.get('media') or {}).get('box') or {}
        if ma != mb:
            fails.append('%s @%s: the media column moved %s -> %s' % (path, width, ma, mb))
        if ba.get('h') is not None and bb.get('h') is not None:
            stacked = (pa.get('column') or {}).get('box', {}).get('y', 0) > ma.get('y', 0)
            if stacked:
                grew = (cbb.get('h', 0) - cba.get('h', 0)) + (mb.get('h', 0) - ma.get('h', 0))
            else:
                grew = max(0, cbb.get('h', 0) - mb.get('h', 0)) - max(0, cba.get('h', 0) - ma.get('h', 0))
            if bb['h'] - ba['h'] != grew:
                # One pixel of slack, and the reason is arithmetic rather than
                # generosity: every box is rounded to an integer, so a
                # prediction built from three rounded numbers can land a pixel
                # away from a quantity that was never an integer to begin with.
                # It is reported rather than swallowed, so a run that is off by
                # one is visible as an off-by-one.
                if abs(bb['h'] - ba['h'] - grew) > 1:
                    fails.append('%s @%s: the band grew by %d, the columns say %d (stacked=%s)'
                                 % (path, width, bb['h'] - ba['h'], grew, stacked))
                else:
                    notes.append('%s @%s: the band grew by %d, the columns predict %d '
                                 '(1px of sub-pixel rounding)'
                                 % (path, width, bb['h'] - ba['h'], grew))
        notes.append('%s @%s: band %s -> %s, column %s -> %s (media stays %s)'
                     % (path, width, ba.get('h'), bb.get('h'), cba.get('h'), cbb.get('h'), ma.get('h')))

        if pa.get('newTitle') is not None:
            fails.append('%s @%s: the baseline already has an sf-fdetail2__title' % (path, width))
        nt = pb.get('newTitle')
        if nt is None:
            fails.append('%s @%s: the candidate has no sf-fdetail2__title' % (path, width))
        else:
            if nt.get('cs', {}).get('fontSize') != '28px':
                fails.append('%s @%s: the new heading is %s, wanted 28px'
                             % (path, width, nt.get('cs', {}).get('fontSize')))
            if nt.get('cs', {}).get('fontWeight') != '700':
                fails.append('%s @%s: the new heading weighs %s, wanted 700'
                             % (path, width, nt.get('cs', {}).get('fontWeight')))
            if nt.get('text') != tb.get('text'):
                fails.append('%s @%s: the new heading does not name the record' % (path, width))
            if not nt.get('firstInColumn'):
                fails.append('%s @%s: the new heading is not the column\'s first child' % (path, width))
            if not nt.get('beforeIntro'):
                fails.append('%s @%s: the new heading does not precede the intro' % (path, width))

        if pa.get('h1Count') != 1 or pb.get('h1Count') != 1:
            fails.append('%s @%s: h1 count %s -> %s' % (path, width, pa.get('h1Count'), pb.get('h1Count')))
        if pa.get('h1Texts') != pb.get('h1Texts'):
            fails.append('%s @%s: the h1 text changed %s -> %s'
                         % (path, width, pa.get('h1Texts'), pb.get('h1Texts')))

        # the print cascade
        pca, pcb = ta.get('printColors') or [], tb.get('printColors') or []
        if not pca or not pcb:
            fails.append('%s @%s: no print-media colour rule reaches the heading (%s / %s)'
                         % (path, width, pca, pcb))
        else:
            if not any(c['val'].lower() in ('#000', '#000000', 'black', 'rgb(0, 0, 0)')
                       and c['important'] for c in pca):
                fails.append('%s @%s: the baseline heading does not print black: %s' % (path, width, pca))
            if not any(c['val'].lower() in ('#000', '#000000', 'black', 'rgb(0, 0, 0)')
                       and c['important'] for c in pcb):
                fails.append('%s @%s: the candidate heading does not print black: %s' % (path, width, pcb))

    return fails, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--label')
    ap.add_argument('--sha')
    ap.add_argument('--out')
    ap.add_argument('--expect-ver', default='2.10.60',
                    help='the theme version the pre-flight copy must advertise')
    ap.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    ap.add_argument('--desktop-limit', type=int, default=0,
                    help='stop the desktop sweep after N pages (for a smoke run)')
    args = ap.parse_args()

    if args.compare:
        a = json.load(open(args.compare[0], encoding='utf-8'))
        b = json.load(open(args.compare[1], encoding='utf-8'))
        print('A: %s (%s)  %d measurements' % (a['label'], a['sha'][:7], len(a['page'])))
        print('B: %s (%s)  %d measurements' % (b['label'], b['sha'][:7], len(b['page'])))
        fails, notes = compare(a, b)
        print()
        for n in notes[:6]:
            print('   ..   %s' % n)
        if len(notes) > 6:
            print('   ..   ... and %d more of the same shape' % (len(notes) - 6))
        for f in fails:
            print('   FAIL %s' % f)
        print()
        print('GEOMETRY VERDICT: %s — %d failed assertions, %d reported movements'
              % ('PASS' if not fails else 'FAIL', len(fails), len(notes)))
        return 0 if not fails else 1

    if not (args.label and args.sha and args.out):
        ap.error('--label, --sha and --out are required unless --compare is used')

    paths = detail_paths()
    print('%s: %d detail pages, desktop %dx%d, expecting ver=%s'
          % (args.label, len(paths), DESKTOP[0], DESKTOP[1], args.expect_ver))
    s = Sweep(args.auth, args.label, args.sha, args.expect_ver)
    s.attach()
    s.sweep(paths, DESKTOP, desktop_limit=args.desktop_limit)
    print('%s: phone sample %dx%d (%d pages)' % (args.label, *PHONE, len(PHONE_SAMPLE)))
    s.sweep(PHONE_SAMPLE, PHONE)
    out = {'label': args.label, 'sha': args.sha,
           'desktop': list(DESKTOP), 'phone': list(PHONE), 'page': s.page}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print('%s: wrote %s (%d measurements)' % (args.label, args.out, len(s.page)))
    if s.errors:
        for e in s.errors:
            print('   !! %s' % (e,))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
