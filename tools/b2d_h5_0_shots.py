#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5-0 — screenshots.

The gate proves the bytes and the geometry pass proves the cascade; this
produces the frames that let a human confirm both without re-running either.
It drives the geometry tool's session rather than a second browser driver:
two drivers disagree eventually, and the one nobody runs is the one that is
wrong.

Every frame carries the pre-flight provenance assertion — Sweep.measure
refuses to return unless the stylesheet is the copy's AND advertises the
version this sweep expects — so a screenshot cannot silently show the live
theme, and cannot silently show the wrong install either.

usage:
    b2d_h5_0_shots.py --out DIR [--expect-ver 2.10.60] [--auth user:pass]
"""

import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'h50geom', os.path.join(HERE, 'b2d_h5_0_geom.py'))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

EN = '/formulas/joint-support-soft-chews/'
ZH = '/zh/formulas/joint-support-soft-chews/'
PHONE_PAGE = '/formulas/bladder-support-powder/'

FLOOR = 8000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--expect-ver', default='2.10.60')
    ap.add_argument('--sha', default='')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    s = G.Sweep(args.auth, 'shots', args.sha, args.expect_ver)
    s.attach()

    taken = []
    fails = []

    def shot(name, selector=None, full=False, note=''):
        path = os.path.join(args.out, name)
        cmd = ['agent-browser', 'screenshot']
        if full:
            cmd.append('--full')
        if selector:
            cmd.append(selector)
        cmd.append(path)
        G.run(cmd)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        taken.append((name, note, size))
        if size < FLOOR:
            fails.append('%s is %d bytes — under the %d floor' % (name, size, FLOOR))
        print('   %-30s %8d B  %s' % (name, size, note))

    def view(path, width, height, tag, scroll_to=None):
        st = s.measure(path, width, height, tag)
        if scroll_to is not None:
            G.ev('window.scrollTo(0, %d)' % scroll_to)
            time.sleep(0.5)
        return st

    # --- desktop, English -------------------------------------------------
    st = view(EN, 1440, 900, 'shots-desktop-top')
    shot('01-desktop-top.png', note='at the top of a formula page')

    band_y = ((st.get('band') or {}).get('box') or {}).get('y') or 0
    view(EN, 1440, 900, 'shots-desktop-band', scroll_to=max(0, band_y - 60))
    shot('02-desktop-band.png', note='the two-column band in the viewport')

    view(EN, 1440, 900, 'shots-desktop-bandel', scroll_to=max(0, band_y - 60))
    shot('03-desktop-band-element.png', 'section.sf-fdetail2',
         note='the whole band, desktop')
    shot('04-desktop-column.png', '.sf-fdetail2__side',
         note='the parameters column and its new heading')

    view(EN, 1440, 900, 'shots-desktop-full', scroll_to=0)
    shot('05-desktop-full.png', full=True, note='full page, desktop')

    # --- desktop, Chinese -------------------------------------------------
    st = view(ZH, 1440, 900, 'shots-zh')
    band_y = ((st.get('band') or {}).get('box') or {}).get('y') or 0
    view(ZH, 1440, 900, 'shots-zh-band', scroll_to=max(0, band_y - 60))
    shot('06-zh-band.png', 'section.sf-fdetail2', note='the same band on /zh/')

    # --- phone ------------------------------------------------------------
    st = view(PHONE_PAGE, 390, 844, 'shots-phone-top')
    shot('07-phone-top.png', note='phone, top of page')
    band_y = ((st.get('band') or {}).get('box') or {}).get('y') or 0
    view(PHONE_PAGE, 390, 844, 'shots-phone-band', scroll_to=max(0, band_y - 20))
    shot('08-phone-band.png', note='phone, the band stacked')

    print()
    if fails:
        for f in fails:
            print('   FAIL %s' % f)
        print('VERDICT: FAIL — %d of %d frames under the floor' % (len(fails), len(taken)))
        return 1
    print('VERDICT: PASS — %d shots, all above the %d-byte floor (min %d, max %d)'
          % (len(taken), FLOOR, min(s for _, _, s in taken), max(s for _, _, s in taken)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
