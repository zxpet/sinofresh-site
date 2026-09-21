#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2a — measure the rewritten detail band at the five brief widths.

Drives agent-browser from Python, sequentially, for two reasons this project
already paid for: a shell loop with command substitution drifts between
iterations (the eval target silently moves), and `set headers` / `set
credentials` each rebuild the browser context, so the order below is the only
one that both keeps the pre-flight header and keeps it attached to the right
origin:

    close --all -> open <origin> -> set headers{Authorization + X-SF-Preflight}
                -> reload -> set viewport -> eval/screenshot

`set credentials` is NOT used: it would wipe the custom header, and without the
header every capture would be the LIVE theme while looking perfectly normal.

What is measured, and why each number matters:

  * grid-template-columns on the band's inner grid — the breakpoint contract
    (single column up to 768, two columns from 769, rail 72px+1fr from 1101)
  * the thumbnail rail's flex-direction — vertical rail is the brief; the
    481-768 band is the one place it is meant to lie down
  * scrollWidth - clientWidth — the rail is exactly 72px and the site has no
    global border-box reset, so a 1px border on a 72px tile would overflow the
    page by 2px and nothing else would report it
  * matchMedia('(hover: hover)') — the hover-to-switch path must be absent on
    touch, not merely hard to trigger
  * matchMedia('(prefers-reduced-motion: reduce)')

usage:
    b2d_h2a_responsive.py --out DIR [--url URL] [--auth user:pass]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

VIEWPORTS = [(480, 900), (768, 1000), (1024, 1000), (1101, 1000), (1440, 1000)]

MEASURE = r"""
(() => {
  const q = (s) => document.querySelector(s);
  const cs = (el) => el ? getComputedStyle(el) : null;
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) }; };
  const inner = q('.sf-fdetail2__inner');
  const media = q('.sf-fdetail2__media');
  const side  = q('.sf-fdetail2__side');
  const rail  = q('.sf-fdetail2__media .sf-gallery__thumbs');
  const stage = q('.sf-fdetail2__media .sf-gallery__stage');
  const params= q('.sf-fdetail2__params');
  const band  = q('section.sf-fdetail2');
  return JSON.stringify({
    vw: window.innerWidth, vh: window.innerHeight,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bandW: box(band), innerW: box(inner), mediaW: box(media), sideW: box(side), stageW: box(stage),
    gridDisplay: cs(inner) && cs(inner).display,
    gridCols: cs(inner) && cs(inner).gridTemplateColumns,
    gridGap: cs(inner) && cs(inner).gap,
    railDir: cs(rail) && cs(rail).flexDirection,
    railWrap: cs(rail) && cs(rail).flexWrap,
    railW: box(rail),
    thumbCount: document.querySelectorAll('.sf-fdetail2__media .sf-gallery__thumb').length,
    thumbBox: box(q('.sf-fdetail2__media .sf-gallery__thumb')),
    thumbBoxSizing: cs(q('.sf-fdetail2__media .sf-gallery__thumb')) && cs(q('.sf-fdetail2__media .sf-gallery__thumb')).boxSizing,
    paramsDisplay: cs(params) && cs(params).display,
    paramsCols: cs(params) && cs(params).gridTemplateColumns,
    rows: document.querySelectorAll('.sf-fdetail2__term').length,
    certBadges: document.querySelectorAll('.sf-fdetail2__params .sf-cert-badge').length,
    hoverHover: window.matchMedia('(hover: hover)').matches,
    reduceMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    ver: (document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]') || {}).href || '',
    jsLoaded: typeof window.__sfGalleryLoaded === 'undefined' ? 'n/a' : window.__sfGalleryLoaded
  });
})()
"""


def run(args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=120):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    # agent-browser prints the result as a JSON string literal; the payload is
    # itself JSON, so it takes two parses. One parse leaves a str and every
    # .get() after it fails far away from the real cause.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--url', default='https://dev.zxpet.com/formulas/calming-soft-chews/')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    # After the deploy the same measurements must be taken against the LIVE
    # theme, and the only difference is the provenance assertion: the candidate
    # run must SEE the pre-flight header work (stylesheet URL contains
    # "preflight"), the live run must see it absent while still proving the new
    # bytes (ver=2.10.55). Without a mode switch the live run would either be
    # refused by the candidate assertion or, worse, silently measure the
    # pre-flight copy and be reported as "live".
    ap.add_argument('--mode', choices=('candidate', 'live'), default='candidate')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    b64 = base64.b64encode(args.auth.encode('utf-8')).decode('ascii')
    stamp = time.strftime('%H%M%S')
    url = args.url + '?sfcap=h2aresp' + stamp

    rc, out, err = run(['agent-browser', 'close', '--all'])
    print('close --all:', out or err or 'ok')

    # set credentials BEFORE open, or the very first navigation dies on
    # ERR_INVALID_AUTH_CREDENTIALS. It is wiped again by `set headers` on the
    # next step, which is why the custom header carries the Basic value too.
    user, _, pw = args.auth.partition(':')
    rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw])
    print('set credentials:', out or err or 'ok')

    rc, out, err = run(['agent-browser', 'open', 'https://dev.zxpet.com/'])
    if rc != 0:
        print('FATAL open:', out, err)
        return 2
    hdrs = {'Authorization': 'Basic ' + b64}
    if args.mode == 'candidate':
        hdrs['X-SF-Preflight'] = '1'
    headers = json.dumps(hdrs)
    rc, out, err = run(['agent-browser', 'set', 'headers', headers])
    print('set headers (%s + Basic):' % ('X-SF-Preflight' if args.mode == 'candidate' else 'no custom header'),
          out or err or 'ok')
    # Page errors are collected from the very first paint, so the buffer is
    # cleared immediately before the navigation under test: the only way to know
    # the list belongs to THIS load rather than to the origin probe above.
    err_rc, err_out, err_err = run(['agent-browser', 'errors', '--clear'])
    print('errors buffer cleared:', (err_out or err_err or 'ok').strip()[:120])

    rc, out, err = run(['agent-browser', 'open', url])
    run(['agent-browser', 'reload'])
    print('opened', url)

    # Prove the capture is the candidate and not the live theme before spending
    # five screenshots on it: a header that failed to attach looks exactly like
    # a successful run.
    probe = ev(MEASURE)
    if not isinstance(probe, dict):
        print('FATAL eval did not return an object:', probe)
        return 2
    ver = probe.get('ver', '')
    print('  stylesheet:', ver)
    if args.mode == 'candidate':
        if 'preflight' not in ver:
            print('FATAL the pre-flight header did not attach: that is the LIVE theme')
            run(['agent-browser', 'close', '--all'])
            return 2
    else:
        if 'preflight' in ver:
            print('FATAL --mode live is serving the PRE-FLIGHT copy: the header attached anyway')
            run(['agent-browser', 'close', '--all'])
            return 2
        if '2.10.55' not in ver:
            print('FATAL --mode live stylesheet is not the deployed version: %s' % ver)
            run(['agent-browser', 'close', '--all'])
            return 2
        print('  live provenance ok: no -preflight in the asset URL, ver=2.10.55')

    # The consent banner is a fixed overlay sitting over the bottom of the
    # band, and it covered the parameter rows in the first run — the screenshots
    # were of the banner, not the band. Accepting it is a real user action and
    # it persists in the session; if it somehow survives, it is hidden and that
    # is said out loud rather than left as a quiet edit.
    rc, out, err = run(['agent-browser', 'eval', '-b', base64.b64encode(
        b"document.querySelector('.sf-cookie-banner .sf-cookie-banner__btn')"
        b"&&document.querySelector('.sf-cookie-banner .sf-cookie-banner__btn').click(),"
        b"'clicked'").decode('ascii')])
    time.sleep(0.8)
    gone = ev("!!document.querySelector('.sf-cookie-banner')")
    if gone:
        ev("(function(){var b=document.querySelector('.sf-cookie-banner');"
           "if(b)b.style.display='none';return 'hidden';})()")
        print('consent banner: still present after Accept All -> hidden for the shots')
    else:
        print('consent banner: accepted (gone)')

    results = []
    for w, h in VIEWPORTS:
        run(['agent-browser', 'set', 'viewport', str(w), str(h)])
        time.sleep(0.6)
        m = ev(MEASURE)
        results.append((w, m))
        print('  %4d px  ok' % w)

    # The screenshots need a viewport tall enough to hold the whole band: an
    # element screenshot taller than the viewport comes back with the overflow
    # painted blank, which reads as "the parameter rows are missing" when they
    # are simply below the fold. Width is the breakpoint variable and does not
    # move; height is raised only here, and the geometry was already measured at
    # the brief's own heights above.
    for w, m in results:
        band_h = (m.get('bandW') or {}).get('h') or 900
        want = min(2600, max(900, int(band_h) + 700))
        run(['agent-browser', 'set', 'viewport', str(w), str(want)])
        time.sleep(0.6)
        shot = os.path.join(args.out, 'band-%d.png' % w)
        run(['agent-browser', 'screenshot', 'section.sf-fdetail2', shot])

    # A mobile viewport, for the layout only. This is NOT a touch device as far
    # as the browser is concerned: `set device` switches the UA and the layout
    # viewport but leaves maxTouchPoints 0 and `(hover: hover)` true (measured
    # on iPhone 16), so no honest hover assertion can be made here. The hover
    # gate is covered by tools/b2d_h2a_hover.py, which drives the exact media
    # query the gallery reads. The device list is short and closed; an unknown
    # name makes `set device` print an error and do nothing, which is why the
    # return code is read.
    rc, out, err = run(['agent-browser', 'set', 'device', 'iPhone 16'])
    if rc != 0:
        print('FATAL set device refused:', (out + err).strip())
        run(['agent-browser', 'close', '--all'])
        return 2
    run(['agent-browser', 'reload'])
    time.sleep(0.8)
    touch = ev(MEASURE)
    run(['agent-browser', 'screenshot', 'section.sf-fdetail2', os.path.join(args.out, 'band-mobile-device.png')])

    # Reduced motion.
    run(['agent-browser', 'set', 'viewport', '1101', '1000'])
    run(['agent-browser', 'set', 'media', 'light', 'reduced-motion'])
    time.sleep(0.5)
    rm = ev(MEASURE)

    run(['agent-browser', 'close', '--all'])

    print('\n%-7s %-9s %-24s %-22s %-10s %-9s %s' % (
        'width', 'overflow', 'grid-template-columns', 'rail dir / wrap', 'rail w×h', 'thumb', 'rows/certs'))
    for w, m in results:
        print('%-7s %-9s %-24s %-22s %-10s %-9s %s/%s' % (
            w, m.get('overflowX'),
            (m.get('gridCols') or '')[:24],
            '%s / %s' % (m.get('railDir'), m.get('railWrap')),
            '%sx%s' % ((m.get('railW') or {}).get('w'), (m.get('railW') or {}).get('h')),
            '%sx%s' % ((m.get('thumbBox') or {}).get('w'), (m.get('thumbBox') or {}).get('h')),
            m.get('rows'), m.get('certBadges')))

    # Console/page errors for the whole navigation, read from the browser
    # rather than inferred from the pixels.
    err_rc, err_out, err_err = run(['agent-browser', 'errors'])
    err_txt = (err_out or '').strip()

    with open(os.path.join(args.out, 'responsive.json'), 'w', encoding='utf-8') as fh:
        json.dump({'viewports': [{'w': w, 'm': m} for w, m in results],
                   'touch': touch, 'reduced_motion': rm,
                   'url': url, 'stylesheet': ver, 'mode': args.mode,
                   'page_errors': err_txt}, fh, indent=2, ensure_ascii=False)

    print('\nmobile device viewport: vw=%s overflowX=%s paramsCols=%s rail=%s (hover media NOT emulated: hoverHover=%s)'
          % (touch.get('vw'), touch.get('overflowX'), touch.get('paramsCols'),
             touch.get('railDir'), touch.get('hoverHover')))
    print('reduced-motion   : reduceMotion=%s' % rm.get('reduceMotion'))

    bad = [w for w, m in results if m.get('overflowX')]
    if bad:
        print('\nFAIL horizontal overflow at: %s' % bad)
        return 1
    if touch.get('overflowX'):
        print('\nFAIL horizontal overflow at the mobile device viewport')
        return 1
    if not rm.get('reduceMotion'):
        print('\nFAIL prefers-reduced-motion was not honoured')
        return 1

    # The brief's two other geometric contracts, asserted rather than eyeballed:
    # the vertical rail is exactly 72px wherever the band is two-column, and the
    # parameter list carries the six populated rows on every width.
    rail_bad = [w for w, m in results if w >= 1101 and (m.get('railW') or {}).get('w') != 72]
    if rail_bad:
        print('\nFAIL rail is not 72px at two-column widths: %s' % rail_bad)
        return 1
    rows_bad = [w for w, m in results if m.get('rows') != 6]
    if rows_bad:
        print('\nFAIL parameter rows != 6 at: %s' % rows_bad)
        return 1

    # Console/page errors for the whole navigation, read from the browser
    # rather than inferred from the pixels.
    benign = (not err_txt) or err_txt.lower().startswith('no page errors') or err_txt.lower() == 'none'
    print('\npage errors: %s' % (err_txt[:400] if err_txt else '(none)'))
    if not benign:
        print('FAIL page errors were reported during the live load')
        return 1

    print('\nPASS: no overflow at any width or on the mobile viewport; rail 72px on two-column widths; '
          '6 parameter rows on every width; reduced-motion honoured; 0 page errors; '
          'hover gate covered by b2d_h2a_hover.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
