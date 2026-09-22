#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4 — screenshots.

The end-to-end pass already proves the behaviour; this produces the pictures
that let a human confirm it without re-running anything. It drives the same
harness (tools/b2d_h4_e2e.py) rather than a second copy of it: two drivers
disagree eventually, and the one nobody runs is the one that is wrong.

Every frame carries the pre-flight provenance assertion (the tool's goto
refuses to continue if the stylesheet is not the copy's), so a screenshot
cannot silently show the live theme.

usage:
    b2d_h4_shots.py --out DIR [--auth user:pass]
"""

import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'h4e2e', os.path.join(HERE, 'b2d_h4_e2e.py'))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

DETAIL = E.DETAIL_2ROW
ZH = E.DETAIL_ZH
PLAIN = E.PLAIN


def reveal(p, path, tag, width=1440, height=1000):
    st = p.goto(path, tag, width=width, height=height, wait=1.0)
    for _ in range(40):
        if st['bandTop'] is not None and st['bandTop'] <= st['vh'] * 0.5:
            break
        p.wheel(400)
        st = p.state(tag)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    p = E.Pass(args.auth, args.out)
    p.attach()

    taken = []

    def shot(name, note):
        path = p.shot(name)
        taken.append((name, note, os.path.getsize(path) if os.path.exists(path) else 0))

    # 1 — the page as it opens: no capsule yet.
    st = p.goto(DETAIL, 's1', wait=1.0)
    if st['capHidden']:
        p.ok('shot 1: capsule still hidden at the top of the page')
    else:
        p.fail('shot 1: the capsule is visible at the top')
    shot('h4-01-desktop-top.png', 'the top of a detail page — no capsule')

    # 2 — after the visitor has scrolled to the parameter band.
    st = reveal(p, DETAIL, 's2')
    if st['capHidden']:
        p.fail('shot 2: the capsule never revealed')
    shot('h4-02-desktop-capsule.png',
         'the capsule revealed, above the three existing buttons')

    # 3 — the dialog.
    p.ensure_open('shot 3')
    st = p.state('shot 3')
    shot('h4-03-desktop-dialog.png',
         'the dialog: Your Selection (%d rows) and the four shared steps'
         % len(st['terms']))

    # 4 — the honeypot rejection, which is the only error state a visitor
    #     should never see and the one worth being able to show.
    res = E.ev(E.INJECT % (E.jsstr('Sino Fresh E2E'), E.jsstr('e2e@example.com'),
                           E.jsstr('Sino Fresh'), E.jsstr('CN'),
                           E.jsstr('[%s] screenshot probe — please ignore' % E.MAIL_TAG),
                           E.jsstr('http://spam.example'),
                           "const t = form.querySelector('[name=\"ts\"]');"
                           " if (t) t.value = String(Date.now() - 10000);"))
    E.ev(E.SUBMIT)
    time.sleep(1.2)
    st = p.state('shot 4')
    if 'rejected' not in st['status'].lower():
        p.fail('shot 4: the honeypot was not refused (status %r)' % st['status'])
    shot('h4-04-desktop-honeypot.png',
         'the honeypot refusal — the endpoint is reachable and refusing')

    # 5, 6 — the phone.
    st = reveal(p, DETAIL, 's5', width=390, height=844)
    shot('h4-05-mobile-capsule.png',
         '390x844: three 44px circles and a %dpx capsule, 16px gutter'
         % (st['capBox']['w'] if st['capBox'] else 0))
    p.ensure_open('shot 6')
    st = p.state('shot 6')
    shot('h4-06-mobile-sheet.png',
         'the dialog as a full-height bottom sheet (%dx%d)'
         % (st['panelBox']['w'], st['panelBox']['h']))
    E.run(['agent-browser', 'press', 'Escape'])
    time.sleep(0.4)

    # 7 — the German/Spanish directory's ZH page, same widget, same copy.
    st = reveal(p, ZH, 's7')
    p.ensure_open('shot 7')
    st = p.state('shot 7')
    shot('h4-07-zh-dialog.png',
         'the ZH page: the same capsule and dialog, English copy (the strings '
         'are new and not in TranslatePress yet)')

    # 8 — a page with no capsule at all.
    st = p.goto(PLAIN, 's8', wait=0.9)
    if st['capPresent'] or st['hasScript']:
        p.fail('shot 8: %s carries the capsule or the script' % PLAIN)
    shot('h4-08-plain-page.png',
         'a plain page: none of it, and no inquiry.js enqueued')

    print('-' * 72)
    for name, note, size in taken:
        print('  %-30s %7d B  %s' % (name, size, note))
    floor = [n for n, _, s in taken if s < 8000]
    if floor:
        p.fail('%d screenshot(s) under the 8000-byte floor: %s'
               % (len(floor), floor))
    if p.fails:
        print('VERDICT: FAIL — %d FAIL' % len(p.fails))
        return 1
    print('VERDICT: PASS — %d shots, all above the floor' % len(taken))
    return 0


if __name__ == '__main__':
    sys.exit(main())
