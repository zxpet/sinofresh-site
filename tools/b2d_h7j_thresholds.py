#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H7j header thresholds — where the 20px gap moves the header's own flex lines.

Measured 2026-09-23 with b2d_h7j_rows.py: the 20px gap makes the nav 62px
wider (6 gaps x 10px), and a wider middle child changes WHERE the header's
flex lines fall. "The header is 139px tall at 900 on both builds" is not the
same fact as "the header is laid out the same at 900", and the two disagree,
so this file exists.

Reported per build:

  one-row floor      the narrowest viewport that still holds logo | nav | CTA
                     on one flex line.
  nav+cta floor      the narrowest viewport that still holds the nav and the
                     CTA on one line. Below it the header takes a third row
                     and gets taller -- a real side effect of the wider nav,
                     and the reason this is measured rather than assumed.
  hamburger boundary WP's own responsive boundary. It leaves BOTH the open
                     button and the desktop container rendered at one width,
                     and the block gap applies between them, so the header
                     height there is reported too.
  height sweep       header height at every width in a range, so any other
                     band where the two builds differ is found rather than
                     missed.

  tools/b2d_h7j_thresholds.py --mode live
  tools/b2d_h7j_thresholds.py --mode pre
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
B64 = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PF = json.dumps({"X-SF-Preflight": "1", "Authorization": "Basic " + B64})
PATH = "/products/soft-chews/"

JS = """(() => {
  const H = document.querySelector('header.sf-header');
  const b = H.querySelector('.wp-block-navigation__responsive-container-open');
  const c = H.querySelector('.wp-block-navigation__responsive-container');
  const vis = e => { if (!e) return null; const s = getComputedStyle(e);
    return s.display !== 'none' && e.getBoundingClientRect().width > 0; };
  const ctr = e => e ? (e.getBoundingClientRect().top + e.getBoundingClientRect().height / 2) : null;
  const logo = ctr(H.querySelector('.sf-logo')), nav = ctr(H.querySelector('nav')),
        cta = ctr(H.querySelector('.sf-header__cta'));
  const on = (a, z) => a !== null && z !== null && Math.abs(a - z) <= 6;
  const u = H.querySelector('.wp-block-navigation ul');
  return { vw: innerWidth, hH: Math.round(H.getBoundingClientRect().height),
           logo, nav, cta, oneRow: on(logo, nav) && on(nav, cta),
           logoNav: on(logo, nav), navCta: on(nav, cta),
           hamb: vis(b), cont: vis(c),
           gap: u ? getComputedStyle(u).columnGap : null,
           navW: Math.round(H.querySelector('nav').getBoundingClientRect().width),
           overflow: document.documentElement.scrollWidth > innerWidth };
})()"""


def ab(*a, timeout=180):
    return subprocess.run(["agent-browser", *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def ev(js):
    r = ab("eval", js)
    if not r:
        raise RuntimeError("empty eval")
    o = json.loads(r)
    return json.loads(o) if isinstance(o, str) else o


def session(pre):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    if pre:
        ab("set", "headers", PF)
        time.sleep(0.6)
        ab("reload")
        time.sleep(2.5)
    else:
        ab("set", "credentials", USER, PASS)
        time.sleep(0.6)
        ab("open", BASE + "/")
        time.sleep(2.2)


def at(w):
    ab("open", BASE + PATH)
    time.sleep(1.7)
    for _ in range(3):
        ab("set", "viewport", str(w), "900")
        time.sleep(0.75)
        r = ev(JS)
        if r.get("vw") == w:
            return r
        time.sleep(0.4)
    return None


def floor_of(pred, wide, narrow):
    """Widest-to-narrowest boundary for a predicate that holds on the wide side.

    `wide` must satisfy the predicate and `narrow` must not, with wide > narrow.
    Returns (holds_at, fails_at) with holds_at == fails_at + 1.
    """
    while wide - narrow > 1:
        mid = (wide + narrow) // 2
        r = at(mid)
        if r is None:
            raise RuntimeError("viewport %d did not take" % mid)
        if pred(r):
            wide = mid
        else:
            narrow = mid
    return wide, narrow


def main():
    pre = "--mode" in sys.argv and sys.argv[sys.argv.index("--mode") + 1] == "pre"
    tag = "PRE 2.10.71" if pre else "LIVE 2.10.69"
    session(pre)
    print("== %s ==" % tag)

    r = at(1440)
    print("at 1440: gap=%s navW=%s hH=%s oneRow=%s" % (r["gap"], r["navW"], r["hH"], r["oneRow"]))

    a, b = floor_of(lambda x: x["oneRow"], 1200, 800)
    ra, rb = at(a), at(b)
    print("one-row floor : all three share a line at %d (hH=%s); at %d they do not (hH=%s)"
          % (a, ra["hH"], b, rb["hH"]))

    c, d = floor_of(lambda x: x["navCta"], a, 769)
    rc, rd = at(c), at(d)
    print("nav+cta floor : nav and cta share a line at %d (hH=%s); at %d they do not (hH=%s)"
          % (c, rc["hH"], d, rd["hH"]))

    print("\n-- the hamburger boundary --")
    for w in (602, 601, 600, 599, 598):
        r = at(w)
        print("   %-5s hH=%-4s hamb=%-5s cont=%-5s oneRow=%s" % (w, r["hH"], r["hamb"], r["cont"], r["oneRow"]))

    print("\n-- the nav+cta band, width by width --")
    for w in range(c + 3, d - 3, -1):
        r = at(w)
        print("   %-5s hH=%-4s [logo|nav]=%-5s [nav|cta]=%-5s ovf=%s"
              % (w, r["hH"], r["logoNav"], r["navCta"], r["overflow"]))

    print("\n-- header height sweep (320..1600, step 40) --")
    seen = []
    for w in list(range(1600, 779, -40)) + list(range(780, 319, -20)):
        r = at(w)
        seen.append((w, r["hH"]))
    bands, cur = [], None
    for w, h in seen:
        if cur and cur[2] == h:
            cur = (cur[0], w, h)
        else:
            if cur:
                bands.append(cur)
            cur = (w, w, h)
    bands.append(cur)
    for hi, lo, h in bands:
        print("   hH=%-4s  from %d down to %d" % (h, hi, lo))
    ab("close")


if __name__ == "__main__":
    main()
