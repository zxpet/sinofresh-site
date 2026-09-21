#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2a — the hover-to-preview gate, tested both ways.

The brief says hover must not switch the main image on a touch device. The
switch is JS-driven, so the gate is `matchMedia("(hover: hover)")` read once at
module scope (`CAN_HOVER`), not a CSS @media block — a stylesheet cannot stop a
listener from being bound. A CSS @media (hover: hover) is therefore NOT the
right thing to look for here.

Real touch emulation is unavailable in this tool: `set device "iPhone 16"`
switches the UA string and the layout viewport but leaves
`navigator.maxTouchPoints === 0` and `(hover: hover) === true` (measured), so it
is not a touch device as far as the browser is concerned and the check would
pass for the wrong reason. A page init script that answers `(hover: hover)`
false is used instead, and it is labelled a STUB: it drives the exact query the
code reads, which makes the gate falsifiable, but it does not emulate a finger.

  * positive control (no stub): hovering a thumbnail DOES switch the frame
  * the interesting one (stub):  hovering a thumbnail does NOT

Both run against the pre-flight copy (X-SF-Preflight: 1), verified per phase, so
a header that failed to attach cannot make the pair agree on the live theme.

usage:
    b2d_h2a_hover.py [--url URL]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

STUB = r"""(function () {
  var orig = window.matchMedia;
  window.__HOVER_STUB__ = true;
  window.matchMedia = function (q) {
    if (String(q).indexOf('hover: hover') !== -1) {
      return { matches: false, media: String(q), onchange: null,
               addListener: function () {}, removeListener: function () {},
               addEventListener: function () {}, removeEventListener: function () {},
               dispatchEvent: function () { return false; } };
    }
    return orig.apply(window, arguments);
  };
})();"""

STATE = r"""
(() => {
  const stage = document.querySelector('.sf-fdetail2__media .sf-gallery__stage');
  if (!stage) return JSON.stringify({ error: 'no stage' });
  const slides = Array.prototype.slice.call(stage.querySelectorAll('.sf-gallery__slide'));
  const thumbs = Array.prototype.slice.call(
    document.querySelectorAll('.sf-fdetail2__media .sf-gallery__thumbs .sf-gallery__thumb'));
  const sel = document.querySelectorAll('.sf-fdetail2__media .sf-gallery__thumb[aria-selected="true"]');
  return JSON.stringify({
    stub: !!window.__HOVER_STUB__,
    canHover: !!(window.matchMedia && window.matchMedia('(hover: hover)').matches),
    /* The gallery hands the frames from the no-JS switch ([hidden]) to the
       class-based one on init (slide.hidden = false, then --off on the rest),
       so "which frame is showing" is the frame WITHOUT --off. Reading [hidden]
       here reports 0 forever and makes both phases look identical. */
    visible: slides.findIndex(function (s) {
      return !s.classList.contains('sf-gallery__slide--off');
    }),
    slides: slides.length,
    thumbs: thumbs.length,
    selected: sel.length,
    selectedIdx: thumbs.indexOf(sel[0]),
    sheet: (document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]') || {}).href || ''
  });
})()
"""

THUMB3 = '.sf-fdetail2__media .sf-gallery__thumbs .sf-gallery__thumb:nth-child(3)'


def run(args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc])
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    first = json.loads(out)
    return json.loads(first) if isinstance(first, str) else first


def phase(url, headers, auth, stub_path, label):
    run(['agent-browser', 'close', '--all'])
    cmd = ['agent-browser', 'open', url, '--headers', json.dumps(headers)]
    if stub_path:
        cmd += ['--init-script', stub_path]
    rc, out, err = run(cmd)
    if rc != 0:
        print('FATAL open in %s: %s %s' % (label, out, err))
        return None, None, None
    run(['agent-browser', 'set', 'viewport', '1440', '1000'])
    time.sleep(0.5)
    before = ev(STATE)
    if 'preflight' not in (before.get('sheet') or ''):
        print('FATAL %s: the pre-flight header did not attach' % label)
        return before, None, None
    if stub_path and not before.get('stub'):
        print('FATAL %s: the init script did not run' % label)
        return before, None, None
    run(['agent-browser', 'scrollintoview', THUMB3])
    time.sleep(0.3)
    run(['agent-browser', 'hover', THUMB3])
    time.sleep(0.4)
    after = ev(STATE)
    run(['agent-browser', 'close', '--all'])
    return before, after, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='https://dev.zxpet.com/formulas/calming-soft-chews/')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()

    b64 = base64.b64encode(args.auth.encode('utf-8')).decode('ascii')
    headers = {'X-SF-Preflight': '1', 'Authorization': 'Basic ' + b64}
    url = args.url + '?sfcap=h2ahover' + time.strftime('%H%M%S')

    tmp = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8')
    tmp.write(STUB)
    tmp.close()

    try:
        print('== 正对照：本机有 hover 能力（无 stub）==')
        b, a, _ = phase(url, headers, args.auth, None, 'positive')
        if b is None:
            return 2
        print('  before: canHover=%s visible=%s thumbs=%s sheet=%s' % (
            b['canHover'], b['visible'], b['thumbs'], (b['sheet'] or '')[-40:]))
        print('  after : canHover=%s visible=%s selectedIdx=%s' % (
            a['canHover'], a['visible'], a['selectedIdx']))
        pos_ok = a['visible'] == 2 and a['selectedIdx'] == 2

        print('\n== 关键对照：STUB 让 (hover: hover) 为假（非真实触屏，仅驱动代码读取的那个查询）==')
        b2, a2, _ = phase(url, headers, args.auth, tmp.name, 'stub')
        if b2 is None:
            return 2
        print('  before: stub=%s canHover=%s visible=%s thumbs=%s' % (
            b2['stub'], b2['canHover'], b2['visible'], b2['thumbs']))
        print('  after : stub=%s canHover=%s visible=%s selectedIdx=%s' % (
            a2['stub'], a2['canHover'], a2['visible'], a2['selectedIdx']))
        neg_ok = a2['visible'] == b2['visible'] == 0

        print('\n%-34s %s' % ('正对照 hover 切换主图', 'PASS' if pos_ok else 'FAIL'))
        print('%-34s %s' % ('stub 下 hover 不切换主图', 'PASS' if neg_ok else 'FAIL'))
        if pos_ok and neg_ok:
            print('\nPASS: the gate is load-bearing — the same gesture switches the frame '
                  'when the query says hover, and does nothing when it says no hover')
            return 0
        print('\nFAIL: the pair did not separate')
        return 1
    finally:
        os.unlink(tmp.name)


if __name__ == '__main__':
    sys.exit(main())
