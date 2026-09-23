#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7j — geometry baseline for the two layout items (待办10 / 待办15).

Two questions, both answered by measurement rather than by reading CSS:

  待办10  how far apart are the top-level nav items today, and at which
          viewport does the header run out of room and wrap?

  待办15  .sf-facts-mini is the one band on a dosage page that is NOT on the
          content gutter. Every neighbouring band sits at x = the content
          column edge; the facts band starts at x = 0 and its last item runs to
          the viewport edge. This measures the left/right edge of every
          top-level band so the fix can be stated as "match this number",
          and so the E2E can assert the same number afterwards.

Run against the LIVE dev theme (2.10.69) for the "before" numbers, and against
the preflight copy for the "after" numbers:

    tools/b2d_h7j_measure.py --mode live
    tools/b2d_h7j_measure.py --mode pre

Session recipe: close --all -> set credentials -> open -> set viewport.
`set headers` and `set credentials` rebuild the context and erase each other,
so the preflight mode sets ONE headers call carrying both the custom header and
the Basic credential, then reloads.
"""
import argparse
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
B64 = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()

PATH = "/products/soft-chews/"
WIDTHS = [1440, 1280, 1240, 1200, 1100, 1024, 900, 820, 768, 414, 375]
HEIGHT = 900


def ab(*a, timeout=180):
    p = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip()


def ev(js):
    """agent-browser prints a JSON string literal; decode twice.

    An eval that throws prints its traceback on STDERR and nothing on stdout,
    so an empty stdout is a failure, not an empty answer. Without this guard a
    JS typo (measured: `ctaL` referenced inside its own initialiser) returns ""
    and the next `.get()` raises an AttributeError three frames away from the
    real cause.
    """
    p = subprocess.run(["agent-browser", "eval", js], capture_output=True, text=True, timeout=180)
    raw = p.stdout.strip()
    if not raw:
        raise RuntimeError("eval returned nothing; stderr=%s" % p.stderr.strip()[:400])
    try:
        once = json.loads(raw)
    except Exception:
        return raw
    if isinstance(once, str):
        try:
            return json.loads(once)
        except Exception:
            return once
    return once


SERVED = """(() => {
  const links = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href);
  const theme = links.find(h => h.includes('sinofresh-theme')) || '';
  return { path: location.pathname, title: document.title, theme,
           preflight: theme.includes('-preflight'),
           ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || '' };
})()"""

# --- nav spacing + does the header still hold one row -----------------------
NAV = """(() => {
  const ul = document.querySelector('header .wp-block-navigation__container')
          || document.querySelector('.wp-block-navigation ul');
  const items = ul ? Array.from(ul.children).filter(li => li.classList.contains('wp-block-navigation-item')) : [];
  const g = items.length ? getComputedStyle(items[0].parentElement) : null;
  const gapStyle = g ? g.columnGap : '';
  const boxes = items.map(li => { const r = li.getBoundingClientRect();
                                 return { l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width),
                                          y: Math.round(r.top), label: (li.textContent || '').trim().slice(0, 18) }; });
  const steps = [];
  for (let i = 1; i < boxes.length; i++) steps.push(boxes[i].l - boxes[i - 1].r);
  const oneRow = boxes.length ? boxes.every(b => Math.abs(b.y - boxes[0].y) < 2) : false;
  const header = document.querySelector('header.sf-header');
  const cta = document.querySelector('header.sf-header .sf-header__cta');
  const logo = document.querySelector('header.sf-header .sf-logo');
  const hr = header ? header.getBoundingClientRect() : null;
  return { vw: innerWidth, items: boxes.length, gap: gapStyle, steps,
           oneRow, navL: boxes.length ? boxes[0].l : null,
           navR: boxes.length ? boxes[boxes.length - 1].r : null,
           navW: boxes.length ? boxes[boxes.length - 1].r - boxes[0].l : null,
           headerH: hr ? Math.round(hr.height) : null,
           logoR: logo ? Math.round(logo.getBoundingClientRect().right) : null,
           ctaL: cta ? Math.round(cta.getBoundingClientRect().left) : null,
           ctaW: cta ? Math.round(cta.getBoundingClientRect().width) : null,
           ctaY: cta ? Math.round(cta.getBoundingClientRect().top) : null,
           navY: boxes.length ? boxes[0].y : null };
})()"""

# --- band edges down the page ----------------------------------------------
BANDS = """(() => {
  const out = [];
  const root = document.querySelector('.wp-site-blocks');
  if (!root) return { bands: out, note: 'no wp-site-blocks' };
  const kids = Array.from(root.children);
  kids.forEach((el, i) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.height < 1) return;
    // first and last visible leaf text box inside the band
    const leaves = Array.from(el.querySelectorAll('h1,h2,h3,p,li,span,div,a'))
      .filter(n => { const b = n.getBoundingClientRect();
                     return b.height > 4 && b.width > 4 && n.textContent.trim().length > 0; });
    let firstL = null, lastR = null, firstName = '';
    if (leaves.length) {
      const f = leaves.reduce((a,b) => a.getBoundingClientRect().left <= b.getBoundingClientRect().left ? a : b);
      const l = leaves.reduce((a,b) => a.getBoundingClientRect().right >= b.getBoundingClientRect().right ? a : b);
      firstL = Math.round(f.getBoundingClientRect().left);
      lastR = Math.round(l.getBoundingClientRect().right);
      firstName = (f.className || f.tagName).toString().slice(0, 46);
    }
    out.push({ i, cls: (el.className || el.tagName).toString().slice(0, 66),
               boxL: Math.round(r.left), boxR: Math.round(r.right),
               padL: cs.paddingLeft, padR: cs.paddingRight,
               maxW: cs.maxWidth, firstL, lastR, firstName });
  });
  return { vw: innerWidth, bands: out, pageW: document.documentElement.scrollWidth };
})()"""

FACTS = """(() => {
  const s = document.querySelector('.sf-facts-mini');
  if (!s) return { present: false };
  const cs = getComputedStyle(s);
  const items = Array.from(s.querySelectorAll('.sf-facts-mini__item'));
  const boxes = items.map(it => { const r = it.getBoundingClientRect();
    return { l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), y: Math.round(r.top) }; });
  const sr = s.getBoundingClientRect();
  return { present: true, boxL: Math.round(sr.left), boxR: Math.round(sr.right),
           padL: cs.paddingLeft, padR: cs.paddingRight, justify: cs.justifyContent,
           display: cs.display, gap: cs.columnGap, items: boxes.length, boxes,
           rows: new Set(boxes.map(b => b.y)).size,
           firstL: boxes.length ? boxes[0].l : null,
           lastR: boxes.length ? boxes[boxes.length - 1].r : null,
           overflow: document.documentElement.scrollWidth > innerWidth };
})()"""


def session(mode):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    if mode == "pre":
        ab("set", "headers", json.dumps({"X-SF-Preflight": "1",
                                         "Authorization": "Basic " + B64}))
        time.sleep(0.6)
        ab("reload")
        time.sleep(2.5)
    else:
        ab("set", "credentials", USER, PASS)
        time.sleep(0.6)
        ab("open", BASE + "/")
        time.sleep(2.2)


def set_viewport(w, h):
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.7)
        got = ev("JSON.stringify({w: innerWidth})")
        if isinstance(got, dict) and got.get("w") == w:
            return True
        time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["live", "pre"], required=True)
    ap.add_argument("--path", default=PATH)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    session(args.mode)

    rows = []
    for w in WIDTHS:
        ab("open", BASE + args.path)
        time.sleep(2.0)
        if not set_viewport(w, HEIGHT):
            print("viewport %d did not take" % w, file=sys.stderr)
            continue
        served = ev(SERVED)
        nav = ev(NAV)
        facts = ev(FACTS)
        bands = ev(BANDS)
        rows.append({"w": w, "served": served, "nav": nav, "facts": facts, "bands": bands})
        print("== %d  served=%s ver=%s" % (w, served.get("path"), served.get("ver")))
        print("   nav: items=%s gap=%s steps=%s oneRow=%s box=%s..%s w=%s headerH=%s" % (
            nav.get("items"), nav.get("gap"), nav.get("steps"), nav.get("oneRow"),
            nav.get("navL"), nav.get("navR"), nav.get("navW"), nav.get("headerH")))
        print("   facts: box=%s..%s pad=%s/%s justify=%s firstL=%s lastR=%s rows=%s" % (
            facts.get("boxL"), facts.get("boxR"), facts.get("padL"), facts.get("padR"),
            facts.get("justify"), facts.get("firstL"), facts.get("lastR"), facts.get("rows")))
        for b in bands.get("bands", []):
            print("   band[%s] pad=%s/%s maxW=%s firstL=%s lastR=%s  %s" % (
                b["i"], b["padL"], b["padR"], b["maxW"], b["firstL"], b["lastR"], b["cls"]))

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"mode": args.mode, "path": args.path, "rows": rows}, fh,
                  ensure_ascii=False, indent=1)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
