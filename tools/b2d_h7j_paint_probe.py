#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H7j paint probe — what the six current-item marks actually paint, and which
rule paints it.

Why a separate file from the E2E: the first version of this probe reported
"all seven slugs neutral", which reads as "the CSS never applies". It was the
probe. The swap helper read `H.className` AFTER the previous iteration had
already rewritten it, so the `none` pass deleted the `sf-header--nav-*` token
and every later pass had nothing left to substitute — leaving the header with
no variant class at all for the rest of the run. The served page ships
`sf-header--nav-underline`, so a helper that mutates in place silently degrades
into a helper that measures the neutral state six times.

This one captures the base class ONCE, outside the loop, and derives every
slug from that constant.

It also answers the second question the neutral run left open: for the `color`
mark, `font-weight` read 600 (so the rule matched) while `color` read white
(so something outranked it). Enumerating every `color` declaration that matches
the element, with its specificity and its sheet order, names the winner
instead of guessing at it.
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
B64 = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PATH = "/about/"          # the About item is the marked one here
HEADERS = json.dumps({"X-SF-Preflight": "1",
                      "Authorization": "Basic " + B64})

SLUGS = ["none", "underline", "bg", "thick-line", "color", "left-line", "pill"]


def ab(*a, timeout=180):
    p = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip()


def ev(js):
    raw = ab("eval", js)
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


# The swap sets the class and the read is a SEPARATE round trip, with a real
# pause between them. That is not politeness: the link declares
#     transition: color 0.15s, border-color 0.15s
# so `color` and `border-color` ANIMATE while `border-width`, `background-color`,
# `padding` and `border-radius` snap. A single-eval probe therefore reads the
# outgoing colour and the incoming width in the same object, which is how the
# first run came to report `color: white` for the brand-green mark and
# `border-bottom-color: white` for a mark that declares transparent — both
# correct readings of the wrong instant. Measured 2026-09-23.
SET = """(slug) => {
  const H = document.querySelector('header.sf-header');
  const c = window.__sfBase.split(/\\s+/).filter(t => t && !/^sf-header--nav-/.test(t));
  if (slug !== 'none') c.push('sf-header--nav-' + slug);
  H.className = c.join(' ');
  return H.className;
}"""

READ = """(() => {
  const R = e => { const b = e.getBoundingClientRect();
    return { t:+b.top.toFixed(1), l:+b.left.toFixed(1), w:+b.width.toFixed(1),
             r:+b.right.toFixed(1), b:+b.bottom.toFixed(1), h:+b.height.toFixed(1) }; };
  const paint = e => { const s = getComputedStyle(e);
    return { color:s.color, fw:s.fontWeight, bbw:s.borderBottomWidth, bbc:s.borderBottomColor,
             blw:s.borderLeftWidth, blc:s.borderLeftColor, bg:s.backgroundColor,
             pl:s.paddingLeft, pr:s.paddingRight, pb:s.paddingBottom, br:s.borderRadius,
             fs:s.fontSize, box:R(e) }; };
  const act = document.querySelector('.sf-nav__link.is-active');
  const links = Array.from(document.querySelectorAll(
      '.wp-block-navigation__container > .wp-block-navigation-item > .sf-nav__link'));
  const sib = links.find(a => !a.classList.contains('is-active'));
  const hov = Array.from(document.querySelectorAll(':hover'))
                   .filter(e => e.classList && e.classList.contains('sf-nav__link')).length;
  return { cls: document.querySelector('header.sf-header').className,
           hov, nLinks: links.length,
           act: act ? paint(act) : null,
           sib: sib ? paint(sib) : null };
})()"""

# Which rule actually sets `color` on the marked link, in cascade order.
WHY = """(() => {
  const H = document.querySelector('header.sf-header');
  const el = document.querySelector('.sf-nav__link.is-active');
  const SPEC = sel => {
    // strip :where() (zero), count :not(...) as its argument
    let s = 0, i = 0, inW = 0;
    const txt = sel.replace(/:where\\(([^()]*)\\)/g, '');
    const a = (txt.match(/\\[[^\\]]*\\]/g) || []).length;
    const b = (txt.match(/\\.[A-Za-z0-9_-]+/g) || []).length;
    const c = (txt.match(/::?[A-Za-z-]+/g) || []).length;
    return [a, b, c].join(',');
  };
  const hits = [];
  let order = 0;
  for (const sheet of Array.from(document.styleSheets)) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    if (!rules) continue;
    for (const r of Array.from(rules)) {
      order++;
      if (!r.selectorText) continue;
      for (const sel of r.selectorText.split(',')) {
        let m = false;
        try { m = el.matches(sel.trim()); } catch (e) { m = false; }
        if (m && r.style && r.style.color) {
          hits.push({ sel: sel.trim(), spec: SPEC(sel.trim()), order,
                      color: r.style.color,
                      href: (sheet.href || 'inline') });
        }
      }
    }
  }
  return { cls: H.className, color: getComputedStyle(el).color,
           themeVal: getComputedStyle(document.documentElement)
                       .getPropertyValue('--wp--preset--color--brand-green'),
           hits };
})()"""


def main():
    ab("close", "--all")
    ab("open", BASE + PATH)
    time.sleep(2.5)
    ab("set", "headers", HEADERS)
    ab("reload")
    time.sleep(2.5)
    ab("set", "viewport", "1440", "900")
    time.sleep(1.0)

    got = ev("JSON.stringify({p: location.pathname, t: document.title, "
             "w: innerWidth, h1: document.querySelectorAll('h1').length})")
    print("served:", got)
    if not isinstance(got, dict) or got.get("p") != PATH or got.get("w") != 1440:
        print("!! not on the served page at the right width — aborting")
        return 2
    # prove it is the candidate, not the live theme
    art = ev("""(() => { const l = Array.from(document.querySelectorAll('link[rel=stylesheet]'))
                            .map(x => x.href).filter(h => h.includes('sinofresh-theme'));
                 return { theme: l[0] || null,
                          pre: !!(l[0] || '').includes('-preflight'),
                          v71: (l[0] || '').includes('ver=2.10.71'),
                          hdr: document.querySelector('header.sf-header').className }; })()""")
    print("artifact:", art)
    if not (art.get("pre") and art.get("v71")):
        print("!! this is not the 2.10.71 preflight copy — aborting")
        return 2

    ev("window.__sfBase = document.querySelector('header.sf-header').className;")
    base = ev("window.__sfBase")
    print("base class:", base)
    if "sf-header--nav-" not in (base or ""):
        print("!! served header carries no variant class — aborting")
        return 2

    SETTLE = 0.45   # > the declared 0.15s transition, with margin
    table = {}
    for slug in SLUGS:
        ev("window.__sfSet = %s; window.__sfSet(%s);" % (SET, json.dumps(slug)))
        time.sleep(SETTLE)
        table[slug] = ev(READ)

    # Widened by column, so a number of columns can never drift out of step
    # with the format string (the first draft lost an argument here).
    #
    # `blc` is printed because leaving it out let a real defect through: the
    # left-line mark's active rule is (0,3,0) while its own base rule — which
    # declares `border-left: 3px solid transparent` — is (0,4,0). The base wins,
    # so the mark's 3px rule is transparent and the padding was doing all the
    # visible work. Nothing in the table showed it, because nothing in the
    # table was the colour. Measured 2026-09-23.
    WID = [11, 22, 22, 5, 11, 6, 6, 22, 6, 8, 9, 14]
    COLS = ["slug", "act.color", "act.bg", "bbw", "bbc", "fw", "blw", "blc", "pl",
            "br", "sib.bg", "act.w x h"]

    def row(cells):
        return " ".join(str(c).ljust(w)[:w] for c, w in zip(cells, WID))

    print("\n" + row(COLS))
    for s in SLUGS:
        a = (table.get(s) or {}).get("act")
        b = (table.get(s) or {}).get("sib")
        if not a:
            print("%-11s (no marked link)" % s)
            continue
        print(row([s, a["color"], a["bg"], a["bbw"], a["bbc"], a["fw"],
                   a["blw"], a["blc"], a["pl"], a["br"], (b or {}).get("bg", "-"),
                   "%.1fx%.1f" % (a["box"]["w"], a["box"]["h"])]))
    hov = {s: (table.get(s) or {}).get("hov") for s in SLUGS}
    nlinks = {(table.get(s) or {}).get("nLinks") for s in SLUGS}
    print("\nlinks per container: %s   hover leak: %s" % (nlinks, set(hov.values())))
    if set(hov.values()) != {0}:
        print("!! a nav link is under the pointer — paints below are hover values")
        return 2

    print("\n--- which rule wins `color` / `border-color`, per slug ---")
    for slug in ["none"] + SLUGS[1:]:
        ev("window.__sfSet(%s);" % json.dumps(slug))
        time.sleep(SETTLE)
        why = ev(WHY)
        mine = [h for h in why.get("hits", []) if "sinofresh-theme" in h["href"]]
        print("%-11s computed=%-20s ours=%s" %
              (slug, why.get("color"),
               [(h["sel"], h["color"], h["spec"], h["order"]) for h in mine] or "—"))

    print("\n--- ...and the same under the shipped default ---")
    ev("window.__sfSet('underline');")
    time.sleep(SETTLE)
    print(json.dumps(ev(WHY), indent=1)[:2000])

    ab("close")
    return 0


if __name__ == "__main__":
    sys.exit(main())
