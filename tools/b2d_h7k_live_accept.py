#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-pull live acceptance for the dev site — batches B/C/D, all five claims.

This is NOT `b2d_h7k_e2e.py`. That one runs against the PREFLIGHT copy behind
`X-SF-Preflight: 1`; this one drops the header and drives what a visitor's
browser actually gets. The `served()` gate is therefore INVERTED: it must prove
the answering theme is `themes/sinofresh-theme/style.css` at `ver=2.10.72` and
explicitly NOT the `-preflight` copy. Before the pull on 2026-09-23 this same
page answered `ver=2.10.69` with six `article.sf-certcard`s, so this gate is the
one that separates "the pull landed" from "we are still reading the old bytes".

Five claims, each anchored to something that fails independently:

1. `style.css?ver=2.10.72` on both a home page and a detail page.
2. the home page's certification band is `sf-certstrip` — six chips, two rows of
   three at 1440 and three rows of two at 375, and NOT ONE `sf-certgrid` /
   `article.sf-certcard` left anywhere. The row/column structure is read from the
   chips' own distinct `top` and `left` values, not from `grid-template-columns`
   alone: the property can say 3 columns while the boxes stack.
3. the detail page's price ladder: three `label.sf-tier` cards, and inside each
   one the PRICE sits above the RANGE which sits above the UNIT. That ordering
   is the claim — the old pill drew `200` then `USD 2.5 / unit`, range first, so
   "the price moved up" is a statement about which box has the smaller `top`,
   read per card rather than from one representative card.
4. the foot of the spec column is a `Send Inquiry` button pointing at
   `/contact/#quote` carrying `data-sf-inquiry-open`, and the hero's old
   `sf-formula-hero__actions` row is gone.
5. the header's current item is PAINTED, not merely classed — the H7j defect was
   a link carrying `is-active` with nothing drawn behind it. The shipped variant
   is `sf-header--nav-underline`, which paints `border-bottom-color`, so that is
   the channel read, against the idle links' own value on the same page.

Run: tools/b2d_h7k_live_accept.py [--frames]
"""
import base64
import json
import os
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
# No X-SF-Preflight: this is the visitor's request, which is the whole point.
LIVE = json.dumps({"Authorization": "Basic " + base64.b64encode(
    ("%s:%s" % (USER, PASS)).encode()).decode()})

HOME = "/"
DETAIL = "/formulas/joint-support-soft-chews/"   # the one record with price tiers
ABOUT = "/about/"
GRIDLESS = "/formulas/ear-care-drops/"           # a detail page whose nav marks Products

CHIPS = ['FDA Registered', 'cGMP Compliant', 'ISO 9001 Certified',
         'FSSC 22000 Certified', 'HACCP Certified', 'BRC Certified']

OUT = "docs/batchH7k-live-shots"
TMP = "_backup/_h7k_live_tmp"
FRAMES = []
RESULTS = []


def ab(*a, timeout=240):
    return subprocess.run(["agent-browser", *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def ev(js):
    """agent-browser prints a JSON string literal; decode twice."""
    raw = ab("eval", js)
    if not raw:
        raise RuntimeError("eval returned nothing")
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


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name
          + ("  | " + str(detail)[:300] if detail else ""))


def session():
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def at(path, w, h=900, settle=2.2):
    ab("open", BASE + path)
    time.sleep(settle)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, p: location.pathname})")
        if isinstance(got, dict) and got.get("w") == w and got.get("p") == path:
            # Sections below the fold carry `.sf-pending` (opacity 0) until a
            # scroll reveals them; a full-page capture of an unscrolled page
            # paints them flat. Walk it once.
            scroll_reveal()
            hid = ev("""(() => { let n = 0;
              document.querySelectorAll('.sf-cookie-banner').forEach(e => {
                e.style.display = 'none'; n++; });
              return JSON.stringify({hidden: n}); })()""")
            if (hid or {}).get("hidden"):
                print("    (hid %s fixed cookie banner(s))" % hid.get("hidden"))
            return got
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def scroll_reveal(step=700, pause=0.4, settle=1.2):
    total = (ev("JSON.stringify({h: document.documentElement.scrollHeight})")
             or {}).get("h") or 0
    y = 0
    while y < total:
        ab("eval", "window.scrollTo(0, %d)" % y)
        time.sleep(pause)
        y += step
    left = (ev("JSON.stringify({n: document.querySelectorAll('.sf-pending').length})")
            or {}).get("n") or 0
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(settle)
    if left:
        print("    !! %d section(s) still unrevealed" % left)
    return left


def served_live(path, why):
    """Which artifact answered — asserted BEFORE anything is asserted about it."""
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, title: document.title, theme,
               live: /themes\\/sinofresh-theme\\//.test(theme) && !theme.includes('-preflight'),
               v72: theme.includes('ver=2.10.72'),
               h1: document.querySelectorAll('h1').length };
    })()""")
    check("LIVE 2.10.72 served, not the preflight copy (%s)  [%s]" % (path, why),
          isinstance(s, dict) and s.get("live") is True and s.get("v72") is True,
          s)
    return s


# ------------------------------------------------------------------ probes

STRIP = """(() => {
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(2), h: +r.height.toFixed(2),
             l: +r.left.toFixed(2), t: +r.top.toFixed(2) }; };
  const chips = Array.from(document.querySelectorAll('li.sf-certstrip__badge'));
  const icons = Array.from(document.querySelectorAll('.sf-certstrip__icon'));
  const more = document.querySelector('.sf-certstrip__more');
  const others = Array.from(document.querySelectorAll('section.sf-section--large'))
                       .filter(x => !x.querySelector('.sf-certstrip'));
  return {
    strip: document.querySelector('.sf-certstrip') ? R(document.querySelector('.sf-certstrip')) : null,
    n: chips.length,
    names: chips.map(c => {
      const e = c.querySelector('.sf-certstrip__name'); return e ? e.textContent.trim() : null; }),
    iconBoxes: icons.map(i => [Math.round(i.getBoundingClientRect().width),
                               Math.round(i.getBoundingClientRect().height)]),
    tops:  [...new Set(chips.map(c => Math.round(c.getBoundingClientRect().top)))].sort((a,b)=>a-b),
    lefts: [...new Set(chips.map(c => Math.round(c.getBoundingClientRect().left)))].sort((a,b)=>a-b),
    lede: (document.querySelector('.sf-certstrip__lede')||{}).textContent||null,
    // `.sf-certstrip__more` is the <p> WRAPPER; the link is inside it. Reading
    // the wrapper's own href returns null and reads as "the link lost its
    // target", which is how this probe was wrong the first time it ran.
    more: more ? { text: more.textContent.trim(),
                   tag: more.tagName.toLowerCase(),
                   inner: (() => { const a = more.querySelector('a');
                     return a ? { href: a.getAttribute('href'),
                                  text: a.textContent.trim() } : null; })() } : null,
    grids: document.querySelectorAll('.sf-certgrid').length,
    oldcards: document.querySelectorAll('article.sf-certcard').length,
    // "every other large section is 48px" was never true and is not the claim:
    // `.sf-section:has(.sf-slot--cover)` (the Insights band on this very page)
    // has carried padding-top: 32px since long before this batch. The claim is
    // "the only section off 48px is the one that rule already covers".
    otherSections: others.map(x => ({
      pad: getComputedStyle(x).paddingTop + ' / ' + getComputedStyle(x).paddingBottom,
      text: (x.textContent || '').trim().slice(0, 20),
      pre32: x.matches('.sf-section:has(.sf-slot--cover)') })),
    vw: innerWidth };
})()"""

TIERS = """(() => {
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(2), h: +r.height.toFixed(2),
             l: +r.left.toFixed(2), t: +r.top.toFixed(2), b: +r.bottom.toFixed(2) }; };
  const cards = Array.from(document.querySelectorAll('label.sf-tier'));
  const T = (c, sel) => { const e = c.querySelector(sel); return e ? e : null; };
  const txt = (c, sel) => { const e = T(c, sel); return e ? e.textContent.trim() : null; };
  const box = (c, sel) => { const e = T(c, sel); return e ? R(e) : null; };
  const cta = document.querySelector('a.sf-fdetail2__cta');
  const sample = document.querySelector('.sf-fdetail-config__sample');
  return {
    n: cards.length,
    cards: cards.map(c => ({
      price: txt(c, '.sf-tier__price'), range: txt(c, '.sf-tier__range'),
      unit: txt(c, '.sf-tier__unit'),
      dots: c.querySelectorAll('.sf-tier__dot').length,
      priceBox: box(c, '.sf-tier__price'), rangeBox: box(c, '.sf-tier__range'),
      unitBox: box(c, '.sf-tier__unit'), box: R(c),
      priceWeight: T(c,'.sf-tier__price') ? getComputedStyle(T(c,'.sf-tier__price')).fontWeight : null,
      checked: (c.querySelector('input')||{}).checked === true })),
    shown: cards.filter(c => c.getBoundingClientRect().width > 1).length,
    sample: sample ? sample.textContent.replace(/\\s+/g, ' ').trim() : null,
    sampleBox: sample ? R(sample) : null,
    cta: cta ? { text: cta.textContent.trim(), href: cta.getAttribute('href'),
                 open: cta.hasAttribute('data-sf-inquiry-open'),
                 box: R(cta), display: getComputedStyle(cta).display,
                 cursor: getComputedStyle(cta).cursor } : null,
    heroActions: document.querySelectorAll('.sf-formula-hero__actions').length,
    vw: innerWidth };
})()"""

NAV = """(() => {
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(2), h: +r.height.toFixed(2),
             l: +r.left.toFixed(2), t: +r.top.toFixed(2) }; };
  const links = Array.from(document.querySelectorAll('a.sf-nav__link'));
  const pick = a => { const s = getComputedStyle(a); return {
    href: a.getAttribute('href'), text: a.textContent.trim(),
    bw: s.borderBottomWidth, bc: s.borderBottomColor, color: s.color,
    fw: s.fontWeight, box: R(a),
    afterBg: getComputedStyle(a, '::after').backgroundColor,
    textDeco: s.textDecorationLine }; };
  const act = links.filter(a => a.classList.contains('is-active'));
  const idle = links.filter(a => !a.classList.contains('is-active'));
  const hdr = Array.from(document.querySelectorAll('[class*="sf-header--nav-"]'))
                   .map(e => (e.className.match(/sf-header--nav-[a-z0-9-]+/) || [''])[0]);
  return { total: links.length, active: act.length,
           variant: [...new Set(hdr)],
           act: act.map(pick), idle: idle.slice(0, 5).map(pick),
           ariaCurrent: document.querySelectorAll('a.sf-nav__link[aria-current]').length,
           vw: innerWidth };
})()"""


def rect(sel):
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               dpr: devicePixelRatio,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))


def shoot(name, sel, pad=0, pad_top=None, mincolours=9):
    from PIL import Image
    r = rect(sel)
    if not r:
        print("FAIL %-44s no element %s" % (name, sel))
        return False
    pt = pad if pad_top is None else pad_top
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-44s no capture" % name)
        return False
    im = Image.open(full)
    sx, sy = im.width / float(r["docW"]), im.height / float(r["docH"])
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pt) * sy)),
           min(im.width, int((r["x"] + r["w"] + pad) * sx)),
           min(im.height, int((r["y"] + r["h"] + pad) * sy)))
    crop = im.crop(box).convert("RGB")
    names = len(crop.getcolors(maxcolors=1 << 20) or [])
    ok = names >= mincolours
    crop.save(os.path.join(OUT, name + ".png"))
    FRAMES.append((name, crop.width, crop.height, names, ok))
    print("%s %-46s %4dx%-5d colours=%-6d"
          % ("OK  " if ok else "FLAT", name, crop.width, crop.height, names))
    return ok


# ------------------------------------------------------------------ claims

def claim_home():
    at(HOME, 1440)
    served_live(HOME, "claim 1+2")
    d = ev(STRIP)
    check("/: the band is the strip, and no old card is left standing",
          isinstance(d, dict) and d.get("strip") and d.get("grids") == 0
          and d.get("oldcards") == 0, {k: d.get(k) for k in ("grids", "oldcards", "n")})
    check("/: six chips, named, in the brief's order",
          (d.get("names") or []) == CHIPS, d.get("names"))
    check("/: every chip carries a 32x32 mark",
          (d.get("iconBoxes") or []) and all(b == [32, 32] for b in d["iconBoxes"]),
          d.get("iconBoxes"))
    check("/: at 1440 the chips are two rows of three",
          len(d.get("tops") or []) == 2 and len(d.get("lefts") or []) == 3,
          {"tops": d.get("tops"), "lefts": d.get("lefts")})
    check("/: the strip is the lede + six chips + a link to the full list",
          (d.get("lede") or "").startswith("Certified to the standards")
          and (d.get("more") or {}).get("tag") == "p"
          and ((d.get("more") or {}).get("inner") or {}).get("href") == "/quality/#certifications",
          {"lede": (d.get("lede") or "")[:44], "more": d.get("more")})
    check("/: the band is 155px-class, not the 607px the six cards took",
          (d.get("strip") or {}).get("h", 9999) <= 220, (d.get("strip") or {}).get("h"))
    others = d.get("otherSections") or []
    off = [s for s in others if s.get("pad") != "48px / 48px" and not s.get("pre32")]
    check("/: the only large section off 48px is the one an older rule already covers",
          bool(others) and not off and any(s.get("pre32") for s in others),
          {"n": len(others), "off": off[:3],
           "pre32": [s.get("text") for s in others if s.get("pre32")]})
    return d


def claim_home_375():
    at(HOME, 375)
    d = ev(STRIP)
    check("375: the chips fall to two columns of three",
          len(d.get("tops") or []) == 3 and len(d.get("lefts") or []) == 2,
          {"tops": d.get("tops"), "lefts": d.get("lefts")})
    check("375: no old card is left standing",
          d.get("grids") == 0 and d.get("oldcards") == 0, d.get("grids"))
    return d


def claim_detail():
    at(DETAIL, 1440)
    served_live(DETAIL, "claim 1+3+4")
    d = ev(TIERS)
    cards = d.get("cards") or []
    check("/formulas/joint-support-soft-chews/: three tier cards render",
          d.get("n") == 3 and d.get("shown") == 3, {"n": d.get("n"), "shown": d.get("shown")})
    check("...each card puts the PRICE above the RANGE above the UNIT",
          len(cards) == 3 and all(
              c["priceBox"] and c["rangeBox"] and c["unitBox"]
              and c["priceBox"]["t"] < c["rangeBox"]["t"] < c["unitBox"]["t"]
              for c in cards),
          [{"p": (c["priceBox"] or {}).get("t"), "r": (c["rangeBox"] or {}).get("t"),
            "u": (c["unitBox"] or {}).get("t")} for c in cards])
    check("...the prices are the record's own, and none is empty",
          [c["price"] for c in cards] == ["US$3.88", "US$3.58", "US$3.28"],
          [c["price"] for c in cards])
    check("...each card keeps its selection dot",
          all(c["dots"] == 1 for c in cards), [c["dots"] for c in cards])
    check("...and the sample row quotes US$50.00 with a Get Sample pill",
          (d.get("sample") or "").find("Sample price") >= 0
          and (d.get("sample") or "").find("US$50.00") >= 0
          and (d.get("sample") or "").lower().find("get sample") >= 0,
          d.get("sample"))
    cta = d.get("cta") or {}
    check("...the foot of the column is a visible Send Inquiry button",
          cta.get("text") == "Send Inquiry" and (cta.get("box") or {}).get("w", 0) > 40
          and (cta.get("box") or {}).get("h", 0) > 20,
          {"text": cta.get("text"), "box": cta.get("box")})
    check("...it points at /contact/#quote and opens the inquiry dialog with JS",
          cta.get("href") == "/contact/#quote" and cta.get("open") is True,
          {"href": cta.get("href"), "open": cta.get("open")})
    check("...and the hero's old action row is gone",
          d.get("heroActions") == 0, d.get("heroActions"))
    return d


def claim_nav(path, want_href, why):
    at(path, 1440)
    served_live(path, "claim 5  (%s)" % why)
    d = ev(NAV)
    act = d.get("act") or []
    idle = d.get("idle") or []
    check("%s: exactly one nav item is marked" % path,
          d.get("active") == 1, {"active": d.get("active"), "total": d.get("total")})
    check("%s: the marked item is the one that owns this page" % path,
          len(act) == 1 and act[0].get("href") == want_href,
          [a.get("href") for a in act])
    # The H7j defect was a class with nothing painted behind it, so the channel
    # the shipped variant actually draws is the one read: border-bottom-color.
    check("%s: it is PAINTED, not just classed — border-bottom is not transparent" % path,
          len(act) == 1 and act[0].get("bc") not in ("transparent", "rgba(0, 0, 0, 0)", None)
          and act[0].get("bw") in ("2px", "4px"),
          {"bc": act[0].get("bc"), "bw": act[0].get("bw")} if act else None)
    check("%s: ...and no idle item wears the same paint" % path,
          bool(idle) and all(i.get("bc") != (act[0].get("bc") if act else None) for i in idle),
          {"idle": [i.get("bc") for i in idle]})
    check("%s: the mark is at least as heavy as the idle items (600 vs 400)" % path,
          len(act) == 1 and act[0].get("fw") == "600"
          and all(i.get("fw") != "600" for i in idle),
          {"act": act[0].get("fw") if act else None,
           "idle": [i.get("fw") for i in idle]})
    return d


def main():
    do_frames = "--frames" in sys.argv
    os.makedirs(TMP, exist_ok=True)
    if do_frames:
        os.makedirs(OUT, exist_ok=True)
    session()

    claim_home()
    if do_frames:
        shoot("live-01-home-certstrip-1440", ".sf-certstrip", pad=16)
    claim_home_375()
    if do_frames:
        shoot("live-02-home-certstrip-375", ".sf-certstrip", pad=12)
    claim_detail()
    if do_frames:
        shoot("live-03-detail-price-tiers-1440",
              '.sf-fdetail-config__group[data-sf-config-group="pricing"]', pad=12)
        shoot("live-04-detail-send-inquiry-1440", ".sf-fdetail2__side", pad=12)
    claim_nav(ABOUT, "/about/", "About is the current page")
    if do_frames:
        shoot("live-05-nav-highlight-about-1440", "header", pad=0)
    claim_nav(GRIDLESS, "/products/", "a detail page belongs to Products")
    if do_frames:
        shoot("live-06-nav-highlight-detail-1440", "header", pad=0)

    ab("close", "--all")
    bad = [n for n, ok, _ in RESULTS if not ok]
    print()
    print("%d/%d checks passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("failing:")
        for n in bad:
            print("  - " + n)
    if do_frames:
        print("frames: %d, flat: %d"
              % (len(FRAMES), sum(1 for f in FRAMES if not f[4])))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
