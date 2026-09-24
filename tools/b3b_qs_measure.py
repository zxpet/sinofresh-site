#!/usr/bin/env python3
"""Measure the rendered geometry of the /quality/ "Quality Control at Every
Step" band, at several viewports, on a running site.

Read-only. It never writes to the site: it opens the page, waits for the
stylesheet to be in place, and reads getBoundingClientRect() off the live DOM.

The point of the tool is the before/after pair. Tick 31 claims the band is
~1800-2000px tall at desktop and should become a 3-column card grid; the only
honest way to say "it shrank by N%" is to measure the same nodes on the same
site before and after.

Usage:
  python3 tools/b3b_qs_measure.py                     # dev, 1440/1280/1024/375
  python3 tools/b3b_qs_measure.py --json out.json
  python3 tools/b3b_qs_measure.py --viewports 1440,375
  python3 tools/b3b_qs_measure.py --base http://localhost:10003   # LocalWP

Auth: dev.zxpet.com sits behind Basic Auth. Credentials are set BEFORE every
open (a fresh context after `close --all` carries neither credentials nor
headers -- the classic 401-page trap where every selector answers 0).
"""
import argparse
import base64
import json
import subprocess
import sys

AB = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/agent-browser'
USER = 'sfdev'
PASS = 'VkEws18Kl5V1qp3TpZ6s'

# Reads the band off the live DOM. Every field answers a claim in the tick:
#   qsH / stepHs  -> the 1800-2000px height claim and the per-step row height
#   stepCols      -> "one step per row" (two tracks) vs "3 cards" (three tracks)
#   imgDims       -> "image ~50%" and the 4:3 ratio
#   numFont       -> "large green numbers" (64px today)
MEASURE = r"""
(() => {
  const R = e => { const b = e.getBoundingClientRect();
                   return { w: Math.round(b.width), h: Math.round(b.height) }; };
  const qs = document.querySelector('.sf-qs');
  const steps = [...document.querySelectorAll('.sf-qs__step')];
  const imgs = [...document.querySelectorAll('.sf-qs__media img')];
  const h2 = [...document.querySelectorAll('h2')]
      .find(h => h.textContent.replace(/\s+/g, ' ').trim()
                 === 'Quality Control at Every Step');
  const cs = steps[0] ? getComputedStyle(steps[0]) : null;
  return {
    path: location.pathname,
    title: document.title,
    theme: [...document.querySelectorAll('link[rel=stylesheet]')]
             .map(l => l.href).filter(h => h.includes('sinofresh-theme')),
    bandH:   qs ? Math.round(qs.getBoundingClientRect().height) : null,
    bandW:   qs ? Math.round(qs.getBoundingClientRect().width) : null,
    h2Top:   h2 ? Math.round(h2.getBoundingClientRect().top + scrollY) : null,
    bandBot: qs ? Math.round(qs.getBoundingClientRect().bottom + scrollY) : null,
    stepCount: steps.length,
    stepHs: steps.map(s => Math.round(s.getBoundingClientRect().height)),
    stepGap: steps.length > 1
             ? Math.round(steps[1].getBoundingClientRect().top
                          - steps[0].getBoundingClientRect().bottom) : null,
    cols:  cs ? cs.gridTemplateColumns : null,
    rowGap: cs ? cs.rowGap : null,
    colGap: cs ? cs.columnGap : null,
    stepsPerRow: (() => {
      // how many steps share the first step's top edge -> 1 today, 3 after
      if (!steps.length) return null;
      const t0 = Math.round(steps[0].getBoundingClientRect().top);
      return steps.filter(s => Math.abs(s.getBoundingClientRect().top - t0) < 2)
                  .length;
    })(),
    imgDims: imgs.map(i => ({ nat: i.naturalWidth + 'x' + i.naturalHeight,
                              box: R(i).w + 'x' + R(i).h })),
    imgRatio: imgs.length ? (() => {
      const b = imgs[0].getBoundingClientRect();
      return (b.width / b.height).toFixed(3);
    })() : null,
    numFont:   steps[0] ? getComputedStyle(steps[0].querySelector('.sf-qs__num')).fontSize : null,
    numColor:  steps[0] ? getComputedStyle(steps[0].querySelector('.sf-qs__num')).color : null,
    // What a reader actually has to scroll past, band top -> band bottom.
    bodyH: document.body.scrollHeight,
    docH:  document.documentElement.scrollHeight
  };
})()
"""


def ab(*args, stdin=None):
    p = subprocess.run([AB] + list(args), input=stdin, capture_output=True,
                       text=True)
    if p.returncode != 0:
        raise SystemExit('agent-browser %s failed: %s' % (' '.join(args),
                                                          p.stderr.strip()))
    return p.stdout


# Simulates the tick-31 proposal (3 columns x 2 rows, photo on top, number
# under it) by injecting an override stylesheet, so the report can quote a
# MEASURED post-change height instead of an arithmetic guess. Pure CSS: the
# DOM already reads .sf-qs > article.sf-qs__step > (.sf-qs__text + figure), so
# flex-direction:column-reverse puts the photo above the copy without touching
# the template -- and without changing the reading order for screen readers.
SIMULATE_CSS = """
.sf-qs { max-width: __MAXW__px; margin: 32px auto 0; display: grid;
         grid-template-columns: repeat(3, minmax(0, 1fr));
         column-gap: __GAP__px; row-gap: __GAP__px; }
.sf-qs__step,
.sf-qs__step:nth-child(even) { display: flex; flex-direction: column-reverse;
         grid-template-columns: none; column-gap: 0; row-gap: 0;
         align-items: stretch; }
.sf-qs__step:nth-child(even) .sf-qs__text,
.sf-qs__step:nth-child(even) .sf-qs__media { grid-column: auto; grid-row: auto; }
.sf-qs__step + .sf-qs__step { margin-top: 0; padding-top: 0; border-top: 0; }
.sf-qs__text { display: flex; flex-direction: column; }
.sf-qs__num  { margin-top: 16px; margin-bottom: 8px; }
/* The phone stack. Without this the injected 3-column rule wins at 375px too
   (it lands later in the sheet, at equal specificity) and the band measures
   764px of 81px thumbnails -- a number that describes the simulation, not the
   proposal. The real proposal keeps one column here. */
@media (max-width: 900px) {
  .sf-qs { grid-template-columns: minmax(0, 1fr); column-gap: 0;
           row-gap: __GAP__px; }
}
"""

# Variant B: the same 3-column grid with the big number moved ON TOP of the
# photo instead of above the heading. It is the only lever that removes height
# without touching the two specs the tick states (4:3 photo, full copy), so the
# report can quote a measured number for it rather than an estimate -- and can
# say exactly which spec a 600px band would have to give up.
SIM_OVERLAY_CSS = """
.sf-qs__step { position: relative; }
.sf-qs__step .sf-qs__num {
  position: absolute; top: 10px; left: 12px; margin: 0; z-index: 2;
  color: #fff; text-shadow: 0 2px 10px rgba(0, 0, 0, .55);
}
.sf-qs__text { padding-top: 10px; }
"""


def evaljs(script):
    """Run JS and return just the value.

    Two wrappers have to come off. `--json` wraps the transport as
    {"success":true,"data":{"origin":...,"result":<value>}}, and when the value
    itself is an object it may still arrive as a JSON *string* literal, so it
    gets a second decode. Stopping at the first decode is how a caller ends up
    calling .get() on a str and failing far from the real cause.
    """
    out = ab('eval', '--json', '--stdin', stdin=script)
    outer = json.loads(out)
    if isinstance(outer, str):
        outer = json.loads(outer)
    if isinstance(outer, dict):
        if outer.get('success') is False:
            raise SystemExit('eval failed: %s' % outer.get('error'))
        data = outer.get('data')
        if isinstance(data, dict) and 'result' in data:
            outer = data['result']
    if isinstance(outer, str):
        try:
            outer = json.loads(outer)
        except ValueError:
            pass
    return outer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://dev.zxpet.com')
    ap.add_argument('--path', default='/quality/')
    ap.add_argument('--viewports', default='1440,1280,1024,375')
    ap.add_argument('--simulate', action='store_true',
                    help='also inject the 3-column proposal and measure it')
    ap.add_argument('--sim-overlay', action='store_true',
                    help='with --simulate: also measure the number-over-photo '
                         'variant, the only lever that shortens the band '
                         'without breaking the 4:3 photo or the full copy')
    ap.add_argument('--sim-maxw', type=int, default=1014)
    ap.add_argument('--sim-gap', type=int, default=28)
    ap.add_argument('--preflight', action='store_true',
                    help='render the preflight COPY theme: the X-SF-Preflight '
                         'header has to travel with Authorization, and the '
                         'served stylesheet is asserted before any measuring')
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    vps = [int(v) for v in args.viewports.split(',') if v.strip()]
    url = args.base.rstrip('/') + args.path

    # Fresh context: credentials must be set before open, or the site answers
    # 401 and every selector silently reads 0.
    ab('close', '--all')
    ab('set', 'credentials', USER, PASS)
    ab('open', url)

    if args.preflight:
        # The copy theme is reached with a request header, and `set headers`
        # rebuilds the browser context -- so it has to carry Authorization
        # itself (the credentials above are gone the moment it runs), and it
        # has to run AFTER an open on the target origin, because a header set
        # on about:blank belongs to about:blank and never applies.
        ab('set', 'headers', json.dumps({
            'Authorization': 'Basic ' + base64.b64encode(
                ('%s:%s' % (USER, PASS)).encode()).decode(),
            'X-SF-Preflight': '1',
        }))
        # reload, not open: another open would drop the custom header again.
        ab('reload')

    out = {}
    for w in vps:
        ab('set', 'viewport', str(w), '900')
        # set viewport reflows; re-read geometry after a settle tick.
        ready = evaljs("(() => ({ rs: document.readyState, "
                       "t: document.title, "
                       "sheets: [...document.querySelectorAll('link[rel=stylesheet]')]"
                       ".filter(l => l.href.includes('sinofresh-theme')).length, "
                       "iw: innerWidth }))()")
        if not ready.get('sheets'):
            raise SystemExit('no theme stylesheet at %dpx -- got %r'
                             % (w, ready))
        out[w] = evaljs(MEASURE)
        out[w]['readyState'] = ready['rs']
        out[w]['title'] = ready['t']

        if args.simulate:
            # Inject the proposal, measure it, then take the sheet back out so
            # the next viewport starts from the shipped bytes again.
            css = (SIMULATE_CSS.replace('__MAXW__', str(args.sim_maxw))
                                .replace('__GAP__', str(args.sim_gap)))
            inject = ("(() => { let s = document.getElementById('sf-sim');"
                      " if (!s) { s = document.createElement('style');"
                      " s.id = 'sf-sim'; document.head.appendChild(s); }"
                      " s.textContent = %s;"
                      " return 'injected'; })()" % json.dumps(css))
            evaljs(inject)
            sim = evaljs(MEASURE)
            out[w]['simulated'] = sim
            if args.sim_overlay:
                evaljs(inject)  # same grid, plus the overlay rules
                evaljs("(() => { document.getElementById('sf-sim').textContent += %s;"
                       " return 'appended'; })()" % json.dumps(SIM_OVERLAY_CSS))
                out[w]['simulated_overlay'] = evaljs(MEASURE)
            evaljs("(() => { const s = document.getElementById('sf-sim');"
                   " if (s) s.remove(); return 'removed'; })()")

    # Which copy did we actually render? A header that failed to apply would
    # have measured the LIVE bytes and printed an honest number for the wrong
    # theme, which is a false green this project has hit before. So it is
    # asserted here rather than assumed from the flag.
    served = evaljs("(() => { const l = [...document.querySelectorAll("
                    "'link[rel=stylesheet]')].map(x => x.href)"
                    ".filter(h => h.includes('/themes/'));"
                    " return { sheets: l, path: location.pathname }; })()")
    sheet = next((h for h in served.get('sheets', [])
                  if '/style.css?' in h), '')
    if args.preflight and 'sinofresh-theme-preflight' not in sheet:
        raise SystemExit('asked for the preflight copy but rendered %r' % sheet)
    if not args.preflight and '/sinofresh-theme-preflight/' in sheet:
        raise SystemExit('asked for the live theme but rendered %r' % sheet)
    if not sheet:
        raise SystemExit('no theme stylesheet on %r' % served.get('path'))

    print('== /quality/  "Quality Control at Every Step"  rendered geometry ==')
    print('   served theme: %s' % sheet.split('/themes/')[-1])
    print('   url: %s' % url)
    for w in vps:
        d = out[w]
        print()
        print('  --- viewport %dpx ---' % w)
        print('    theme sheet   : %s' % (d['theme'][0].split('/')[-1]
                                          if d['theme'] else '(none)'))
        print('    band height   : %s px   (width %s)' % (d['bandH'], d['bandW']))
        print('    band top..bot : %s .. %s' % (d['h2Top'], d['bandBot']))
        print('    steps         : %d   per row: %s' % (d['stepCount'],
                                                       d['stepsPerRow']))
        print('    step heights  : %s' % d['stepHs'])
        print('    step gap      : %s   row-gap %s  col-gap %s'
              % (d['stepGap'], d['rowGap'], d['colGap']))
        print('    grid cols     : %s' % d['cols'])
        print('    images        : %s' % d['imgDims'])
        print('    img ratio     : %s' % d['imgRatio'])
        print('    number        : %s %s' % (d['numFont'], d['numColor']))
        print('    page height   : body %s / doc %s' % (d['bodyH'], d['docH']))

    if any('simulated' in out[w] for w in vps):
        print()
        print('== simulated 3-column proposal (max-width %d, gap %d) =='
              % (args.sim_maxw, args.sim_gap))
        for w in vps:
            s = out[w].get('simulated')
            if not s:
                continue
            before = out[w]['bandH']
            after = s['bandH']
            drop = (1 - after / before) * 100 if before else 0
            print()
            print('  --- viewport %dpx ---' % w)
            print('    band height   : %s px  (was %s)  -> %+.0f%%'
                  % (after, before, -drop))
            print('    steps         : %d   per row: %s' % (s['stepCount'],
                                                           s['stepsPerRow']))
            print('    step heights  : %s' % s['stepHs'])
            print('    grid cols     : %s' % s['cols'])
            print('    images        : %s   ratio %s'
                  % (s['imgDims'], s['imgRatio']))
            print('    number        : %s %s' % (s['numFont'], s['numColor']))
            print('    page height   : body %s / doc %s' % (s['bodyH'], s['docH']))

    if any('simulated_overlay' in out[w] for w in vps):
        print()
        print('== simulated variant B: same grid, number ON the photo ==')
        for w in vps:
            s = out[w].get('simulated_overlay')
            if not s:
                continue
            before = out[w]['bandH']
            after = s['bandH']
            drop = (1 - after / before) * 100 if before else 0
            print()
            print('  --- viewport %dpx ---' % w)
            print('    band height   : %s px  (was %s)  -> %+.0f%%'
                  % (after, before, -drop))
            print('    steps         : %d   per row: %s' % (s['stepCount'],
                                                           s['stepsPerRow']))
            print('    step heights  : %s' % s['stepHs'])
            print('    images        : %s   ratio %s'
                  % (s['imgDims'], s['imgRatio']))
            print('    number        : %s %s' % (s['numFont'], s['numColor']))
            print('    page height   : body %s / doc %s' % (s['bodyH'], s['docH']))

    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(out, fh, indent=2)
        print('\n  json -> %s' % args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
