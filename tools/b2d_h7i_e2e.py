#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7i E2E — the price ladder, the sample row, the Send Inquiry button,
the hero goes quiet.

Target: the PREFLIGHT copy (2.10.70), not the live dev theme.

Batch B pushes and does not pull, so dev's live theme is still 2.10.69 and the
candidate exists on the box only as `sinofresh-theme-preflight`, behind the
`X-SF-Preflight: 1` header. That is the opposite of the H7g E2E, which could
run against the served site because batch A pulled.

Session recipe (measured 2026-09-23, and it corrects the earlier note):
    close --all -> open <url> -> set headers {X-SF-Preflight, Authorization}
               -> reload
Only the navigation that PRECEDES `set headers` needs the reload; later `open`s
keep the headers (probed: plain open -> entitled preflight -> zh page -> still
preflight). `set credentials` is deliberately NOT used: it and `set headers`
each rebuild the browser context and the later one erases the former, so the
Basic credential rides inside the same `set headers` call.

Every page re-asserts WHICH artifact served it before asserting anything about
it. The 401 page answers `location.pathname == "/"` with zero stylesheet links
and a blank title, and every other query on it returns 0/false — a shape that
reads exactly like "the new markup never rendered".

What this file is NOT: a pointer-level test. The ladder card, the sample button
and the right-column CTA are driven with element.click(); the dialog contract
(opens, does not navigate, writes the sentence) is what is being measured, and
the pointer path for these controls was established in H7g. Geometry, on the
other hand, is measured for real — the three-column claim and the stack inside
a card are bounding boxes, not class names.
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
B64 = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()

EN = "/formulas/joint-support-soft-chews/"
ZH = "/zh/formulas/joint-support-soft-chews/"
OTHER = "/formulas/liquid-joint-support/"

# The record's own three breaks, as sf_tier_price_label / sf_tier_range_label
# render them, and the sample fee's own label. Post 158 is the only record in
# the dev DB carrying sf_formula_price_tiers AND sf_formula_sample_price AND
# sf_formula_video_url — measured with wp-cli, all three keys, one row.
TIERS = [("US$3.88", "10-99", "pieces"),
         ("US$3.58", "100-999", "pieces"),
         ("US$3.28", "≥1,000", "pieces")]
SAMPLE = "US$50.00"
VIDEO_ID = "jNQXAC9IVRw"
TITLE = "Joint Support Soft Chews"
PREFILL = "I would like to request a sample of %s (%s per sample)." % (TITLE, SAMPLE)

RESULTS = []


def ab(*a, timeout=180):
    p = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip()


def ev(js):
    """agent-browser prints a JSON string literal; decode twice."""
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


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + ("  | " + str(detail) if detail else ""))


def open_at(path, w=1440, h=900):
    ab("open", BASE + path)
    time.sleep(2.4)
    for _ in range(3):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, h: innerHeight})")
        if isinstance(got, dict) and got.get("w") == w:
            return
        time.sleep(0.7)
    raise SystemExit("viewport did not take on %s: %r" % (path, got))


SERVED = """(() => {
  const links = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href);
  const theme = links.find(h => h.includes('sinofresh-theme')) || '';
  const body = document.body.innerHTML;
  return { path: location.pathname, title: document.title, theme,
           pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
           v70: theme.includes('ver=2.10.70'),
           cfg: /config\\.js\\?ver=1\\.3\\.0/.test(body),
           gal: /formula-gallery\\.js\\?ver=2\\.2\\.0/.test(body),
           h1: document.querySelectorAll('h1').length };
})()"""

HERO = """(() => {
  const hero = document.querySelector('.sf-formula-hero');
  return { actions: document.querySelectorAll('.sf-formula-hero__actions').length,
           solid: document.querySelectorAll('.sf-formula-hero__actions .sf-formula__cta').length,
           build: document.querySelectorAll('.sf-formula-hero__build').length,
           title: !!document.querySelector('.sf-formula-hero__title'),
           meta: !!document.querySelector('.sf-formula-hero__meta'),
           card: !!document.querySelector('.sf-fcard'),
           js: (() => { const r = document.querySelector('[data-sf-config]');
                        return r ? r.classList.contains('sf-fdetail-config--js') : null; })() };
})()"""

LADDER = """(() => {
  const g = document.querySelector('[data-sf-config-group="pricing"]');
  if (!g) return { found: false };
  const grid = g.querySelector('.sf-fdetail-config__tiers');
  const cards = Array.from(g.querySelectorAll('.sf-fdetail-config__opt.sf-tier'));
  const R = e => { const b = e.getBoundingClientRect();
                   return { t: +b.top.toFixed(1), l: +b.left.toFixed(1),
                            w: +b.width.toFixed(1), r: +b.right.toFixed(1),
                            b: +b.bottom.toFixed(1), h: +b.height.toFixed(1) }; };
  const hint = g.querySelector('.sf-fdetail-config__hint');
  const meta = g.querySelector('.sf-fdetail-config__meta');
  const sample = document.querySelector('.sf-fdetail-config__sample');
  return {
    found: true,
    label: (g.querySelector('.sf-fdetail-config__label') || {}).textContent,
    groupDisplay: getComputedStyle(g).display,
    gridDisplay: getComputedStyle(grid).display,
    gridCols: getComputedStyle(grid).gridTemplateColumns,
    gridBox: R(grid),
    nCards: cards.length,
    cards: cards.map(c => {
      const inp = c.querySelector('input');
      const dot = c.querySelector('.sf-tier__dot');
      return { display: getComputedStyle(c).display, box: R(c),
               childOrder: Array.from(c.children).map(e => e.className),
               price: (c.querySelector('.sf-tier__price') || {}).textContent,
               range: (c.querySelector('.sf-tier__range') || {}).textContent,
               unit:  (c.querySelector('.sf-tier__unit')  || {}).textContent,
               priceBox: R(c.querySelector('.sf-tier__price')),
               rangeBox: R(c.querySelector('.sf-tier__range')),
               unitBox:  R(c.querySelector('.sf-tier__unit')),
               dot: !!dot, dotBox: dot ? R(dot) : null,
               type: inp ? inp.type : null, name: inp ? inp.name : null,
               value: inp ? inp.value : null, checked: inp ? inp.checked : null,
               isOn: c.classList.contains('is-on') }; }),
    metaText: meta ? meta.textContent : null,
    metaDisplay: meta ? getComputedStyle(meta).display : null,
    hintText: hint ? hint.textContent : null,
    hintDisplay: hint ? getComputedStyle(hint).display : null,
    sample: sample ? (() => {
      const cta = sample.querySelector('.sf-fdetail-config__sample-cta');
      const last = cards.length ? cards[cards.length - 1] : null;
      return { label: (sample.querySelector('.sf-fdetail-config__sample-label') || {}).textContent,
               price: (sample.querySelector('.sf-fdetail-config__sample-price') || {}).textContent,
               icon: !!sample.querySelector('.sf-fdetail-config__sample-icon'),
               ctaText: cta ? cta.textContent : null,
               ctaHref: cta ? cta.getAttribute('href') : null,
               ctaSample: cta ? cta.getAttribute('data-sf-inquiry-sample') : null,
               ctaOpen: cta ? cta.hasAttribute('data-sf-inquiry-open') : null,
               afterCards: last ? ((last.compareDocumentPosition(sample) &
                                    Node.DOCUMENT_POSITION_FOLLOWING) > 0) : null,
               wrap: getComputedStyle(sample).flexWrap,
               priceBox: R(sample.querySelector('.sf-fdetail-config__sample-price')),
               ctaBox: cta ? R(cta) : null };
    })() : null };
})()"""

CTA_ROW = """(() => {
  const c = Array.from(document.querySelectorAll('.sf-fdetail2__cta'));
  const bad = Array.from(document.querySelectorAll('a'))
    .filter(a => /Request Sample/.test(a.textContent)).length;
  const html = document.body.innerHTML;
  const rs = html.match(/Request Sample/g) || [];
  const inComment = rs.length > 0 && /<!--[^>]{0,4000}Request Sample[^>]{0,4000}-->/.test(html);
  return { n: c.length,
           items: c.map(a => ({ t: a.textContent.trim(), h: a.getAttribute('href'),
                                open: a.hasAttribute('data-sf-inquiry-open') })),
           anchorRequestSample: bad, rsOccurrences: rs.length, rsOnlyInComment: inComment };
})()"""

VIDEO = """(() => {
  const v = document.querySelector('.sf-gallery__slide--video');
  const tabs = Array.from(document.querySelectorAll('.sf-gallery__tab'));
  const slides = Array.from(document.querySelectorAll('.sf-gallery__slide'));
  return { tabs: tabs.map(t => t.textContent.trim()),
           videoTab: !!document.querySelector('.sf-gallery__tab[data-sf-gallery-tab="video"]'),
           videoTabText: (document.querySelector('.sf-gallery__tab[data-sf-gallery-tab="video"]') || {}).textContent,
           videoSlide: !!v, vid: v ? v.getAttribute('data-video-id') : null,
           hidden: v ? v.hasAttribute('hidden') : null,
           poster: v && v.querySelector('img') ? v.querySelector('img').getAttribute('src') : null,
           nSlides: slides.length,
           slot: v ? v.getAttribute('data-slot') : null,
           playBtn: v ? !!v.querySelector('.sf-gallery__play') : null };
})()"""

# The three card states after one click, and the dot's own paint. Green is
# rgb(90,183,53) — the brand colour these pages already use; the unchecked
# border is rgb(199,208,203). Asserting the PAINT is what proves the dot
# follows the input: the class alone would also be true of a dot with no rule.
TIER_CLICK = """(() => {
  const g = document.querySelector('[data-sf-config-group="pricing"]');
  const cards = Array.from(g.querySelectorAll('.sf-fdetail-config__opt.sf-tier'));
  cards[1].querySelector('input').click();
  const paint = c => { const s = getComputedStyle(c.querySelector('.sf-tier__dot'));
                       return { bc: s.borderTopColor, bg: s.backgroundColor, box: s.boxShadow }; };
  const sum = document.querySelector('[data-sf-config-summary]');
  return { checked: cards.map(c => c.querySelector('input').checked),
           isOn: cards.map(c => c.classList.contains('is-on')),
           paint: cards.map(paint),
           summary: sum ? sum.textContent : null,
           summaryHidden: sum ? sum.hasAttribute('hidden') : null };
})()"""

# The reveal is deliberately two-step: inquiry.js sets `hidden = false` and then
# adds `is-open` inside a requestAnimationFrame, because a transition needs a
# start value to animate from. Reading `is-open` in the same tick as the click
# therefore measures the wrong instant and reports a dialog that did open as
# closed — measured 2026-09-23, and it is the assertion that was wrong, not the
# page. So the open is probed twice: synchronously, then a round trip later.
SAMPLE_OPEN = """(() => {
  const cta = document.querySelector('.sf-fdetail-config__sample-cta');
  const modal = document.querySelector('.sf-inquiry-modal');
  const ta = modal ? modal.querySelector('textarea[name="message"]') : null;
  const before = ta ? ta.value : null;
  cta.click();
  return { before, hidden: modal.hidden, isOpen: modal.classList.contains('is-open'),
           value: ta ? ta.value : null, path: location.pathname };
})()"""

SAMPLE_STATE = """(() => {
  const modal = document.querySelector('.sf-inquiry-modal');
  const ta = modal ? modal.querySelector('textarea[name="message"]') : null;
  return { hidden: modal.hidden, isOpen: modal.classList.contains('is-open'),
           value: ta ? ta.value : null, path: location.pathname,
           locked: document.body.classList.contains('sf-config-lock') };
})()"""

SAMPLE_REST = """(() => {
  const cta = document.querySelector('.sf-fdetail-config__sample-cta');
  const modal = document.querySelector('.sf-inquiry-modal');
  const ta = modal ? modal.querySelector('textarea[name="message"]') : null;
  const close = modal.querySelector('.sf-inquiry-modal__close');
  cta.click();   // the script's own write must not re-trigger
  const r2 = { value: ta ? ta.value : null };
  ta.value = 'MY OWN TEXT';   // a visitor's own words are never clobbered
  close.click();
  const r3 = { hidden: modal.hidden };
  cta.click();
  const r4 = { value: ta ? ta.value : null, hidden: modal.hidden };
  close.click();
  return { r2, r3, r4, closed: modal.hidden };
})()"""

FOLD = """(() => {
  const list = document.querySelector('.sf-fdetail-config__list');
  const fold = document.querySelector('.sf-fdetail-config__fold');
  const g = document.querySelector('[data-sf-config-group="pricing"]');
  const openBtn = document.querySelector('.sf-fdetail-config__open');
  const before = { folded: list.classList.contains('sf-config-folded'),
                   text: fold.textContent, btnDisplay: getComputedStyle(fold).display,
                   pricingDisplay: getComputedStyle(g).display,
                   openBtnDisplay: openBtn ? getComputedStyle(openBtn).display : null,
                   scroll: document.documentElement.scrollWidth, inner: innerWidth };
  fold.click();
  const R = e => { const b = e.getBoundingClientRect();
                   return { t: +b.top.toFixed(1), l: +b.left.toFixed(1),
                            w: +b.width.toFixed(1), r: +b.right.toFixed(1),
                            b: +b.bottom.toFixed(1) }; };
  const cards = Array.from(g.querySelectorAll('.sf-fdetail-config__opt.sf-tier'));
  const grid = g.querySelector('.sf-fdetail-config__tiers');
  const sample = document.querySelector('.sf-fdetail-config__sample');
  const sc = sample ? sample.querySelector('.sf-fdetail-config__sample-cta') : null;
  const sp = sample ? sample.querySelector('.sf-fdetail-config__sample-price') : null;
  return { before,
           after: { folded: list.classList.contains('sf-config-folded'), text: fold.textContent,
                    pricingDisplay: getComputedStyle(g).display,
                    gridCols: getComputedStyle(grid).gridTemplateColumns,
                    gridBox: R(grid),
                    cards: cards.map(c => ({ box: R(c),
                        price: (c.querySelector('.sf-tier__price') || {}).textContent,
                        priceFs: getComputedStyle(c.querySelector('.sf-tier__price')).fontSize,
                        priceBox: R(c.querySelector('.sf-tier__price')),
                        rangeBox: R(c.querySelector('.sf-tier__range')),
                        unitBox: R(c.querySelector('.sf-tier__unit')),
                        dotBox: R(c.querySelector('.sf-tier__dot')), })),
                    sampleWrap: sample ? getComputedStyle(sample).flexWrap : null,
                    ctaMarginLeft: sc ? getComputedStyle(sc).marginLeft : null,
                    rowBox: sample ? R(sample) : null,
                    parentRight: sample ? R(sample.parentNode).r : null,
                    spBox: sp ? R(sp) : null, scBox: sc ? R(sc) : null,
                    labelBox: sample ? R(sample.querySelector('.sf-fdetail-config__sample-label')) : null,
                    scroll: document.documentElement.scrollWidth, inner: innerWidth } };
})()"""

# The sample row's wrap is a SAFETY, not a promise about a particular phone:
# the four items need ~293.7px (icon 16 + 3 gaps of 7 + label 80.5 + price 64.5
# + button 111.7), so at 375-414 the row is wide enough and everything stays on
# one line, while at 360 and below the button drops to its own line — and lands
# at the row's own left edge because the media query zeroes its margin-left.
# Measured across 1440/414/390/375/360/320 on 2026-09-23. Asserting the wrap at
# 375 alone would be asserting a layout that is not supposed to happen there.
ROW = """(() => {
  const R = e => { const b = e.getBoundingClientRect();
    return { t:+b.top.toFixed(1), l:+b.left.toFixed(1), r:+b.right.toFixed(1),
             b:+b.bottom.toFixed(1), w:+b.width.toFixed(1) }; };
  const s = document.querySelector('.sf-fdetail-config__sample');
  const cta = s.querySelector('.sf-fdetail-config__sample-cta');
  const sp  = s.querySelector('.sf-fdetail-config__sample-price');
  const grid = document.querySelector('.sf-fdetail-config__tiers');
  return { vw: innerWidth, inner: innerWidth, scroll: document.documentElement.scrollWidth,
           wrap: getComputedStyle(s).flexWrap, ml: getComputedStyle(cta).marginLeft,
           row: R(s), cta: R(cta), sp: R(sp), grid: R(grid),
           parentRight: R(s.parentNode).r,
           gridCols: getComputedStyle(grid).gridTemplateColumns,
           cardTops: Array.from(document.querySelectorAll('.sf-tier'))
             .map(c => +c.getBoundingClientRect().top.toFixed(1)),
           ctaOnOwnLine: R(cta).t >= R(sp).b - 1 };
})()"""


def served(path, page):
    s = ev(SERVED)
    ok = (s.get("path") == path and s.get("pre") and s.get("v70")
          and s.get("cfg") and s.get("gal") and s.get("h1") == 1)
    check("preflight candidate served (%s)" % page, ok, s)
    return s


def quiet_hero(tag):
    h = ev(HERO)
    check("%s: the hero carries no action row at all" % tag,
          h.get("actions") == 0 and h.get("solid") == 0 and h.get("build") == 0, h)
    check("%s: the hero still carries the record's identity" % tag,
          h.get("title") and h.get("meta") and h.get("card") is True,
          {"title": h.get("title"), "meta": h.get("meta"), "card": h.get("card")})
    return h


def ladder_values(ld, tag):
    got = [(c.get("price"), c.get("range"), c.get("unit")) for c in ld["cards"]]
    check("%s: the three breaks render price / range / unit as declared" % tag,
          got == TIERS, got)


def ladder_cards(ld, tag):
    cards = ld["cards"]
    grid = ld["gridBox"]
    check("%s: the ladder is a grid of three tracks, one card each" % tag,
          ld.get("gridDisplay") == "grid" and ld.get("nCards") == 3
          and len(ld.get("gridCols", "").split()) == 3
          and all(c.get("display") == "grid" for c in cards),
          {"display": ld.get("gridDisplay"), "cols": ld.get("gridCols"),
           "cards": [c.get("display") for c in cards]})
    tops = [c["box"]["t"] for c in cards]
    bots = [c["box"]["b"] for c in cards]
    check("%s: the three cards sit on one row (tops and bottoms agree)" % tag,
          max(tops) - min(tops) <= 1.0 and max(bots) - min(bots) <= 1.0,
          {"tops": tops, "bottoms": bots})
    check("%s: no card runs past the ladder's own box" % tag,
          all(c["box"]["l"] >= grid["l"] - 1 and c["box"]["r"] <= grid["r"] + 1 for c in cards),
          {"grid": [grid["l"], grid["r"]],
           "rows": [[c["box"]["l"], c["box"]["r"]] for c in cards]})


def ladder_stack(ld, tag, tol=0.5):
    """Inside one card the three lines stack in reading order, above the dot."""
    bad = []
    for i, c in enumerate(ld["cards"]):
        p, r, u, d = c["priceBox"], c["rangeBox"], c["unitBox"], c["dotBox"]
        if not (c["box"]["t"] - tol <= p["t"] and p["b"] <= r["t"] + tol
                and r["b"] <= u["t"] + tol and u["b"] <= d["t"] + tol
                and d["b"] <= c["box"]["b"] + tol):
            bad.append({"i": i, "card": [c["box"]["t"], c["box"]["b"]],
                        "price": [p["t"], p["b"]], "range": [r["t"], r["b"]],
                        "unit": [u["t"], u["b"]], "dot": [d["t"], d["b"]]})
    check("%s: inside each card the price, the range, the unit and the dot stack in that order" % tag,
          not bad, bad)
    order = [c["childOrder"] for c in ld["cards"]]
    want = ["sf-fdetail-config__input", "sf-tier__price", "sf-tier__range",
            "sf-tier__unit", "sf-tier__dot"]
    check("%s: and the card's DOM order is input / price / range / unit / dot" % tag,
          all(o == want for o in order), order)


def ladder_radios(ld, tag):
    cards = ld["cards"]
    vals = [c.get("value") for c in cards]
    names = set(c.get("name") for c in cards)
    check("%s: each card is a real radio, one name, distinct values, nothing picked yet" % tag,
          all(c.get("type") == "radio" for c in cards) and len(names) == 1
          and names == {"sf-config-pricing"} and len(set(vals)) == 3
          and all(c.get("checked") is False for c in cards),
          {"types": [c.get("type") for c in cards], "names": sorted(names), "values": vals})
    check("%s: every card carries its own dot" % tag,
          all(c.get("dot") for c in cards) and ld["nCards"] == 3,
          [c.get("dot") for c in cards])


def main():
    ab("close", "--all")
    time.sleep(1)
    # The origin has to exist before `set headers` can be scoped to it. This
    # first open lands on the 401 page on purpose; the reload below is what
    # carries both the preflight header and the Basic credential.
    ab("open", BASE + EN)
    time.sleep(2)
    ab("set", "headers", json.dumps({"X-SF-Preflight": "1",
                                     "Authorization": "Basic " + B64}))
    time.sleep(0.5)
    ab("reload")
    time.sleep(2.5)

    # =========================== the English record =======================
    served(EN, "EN")
    quiet_hero("EN")

    ld = ev(LADDER)
    check("EN: the record's tiers render as the ladder, not as pills",
          ld.get("found") and ld.get("label") == "Quantity & Pricing", ld.get("label"))
    ladder_cards(ld, "EN")
    ladder_values(ld, "EN")
    ladder_stack(ld, "EN")
    ladder_radios(ld, "EN")

    # Task 11, both halves: the static echoes go under --js, and the markup
    # still carries them for the visitor who never gets the script.
    check("EN: the value echo and the hint are both hidden under --js (task 11)",
          ld.get("metaDisplay") == "none" and ld.get("hintDisplay") == "none",
          {"meta": ld.get("metaDisplay"), "hint": ld.get("hintDisplay")})
    check("EN: ...but the echo is still in the markup, in full",
          ld.get("metaText") == "10-99 — US$3.88 / unit · 100-999 — US$3.58 / unit · ≥1,000 — US$3.28 / unit",
          ld.get("metaText"))

    sm = ld.get("sample") or {}
    check("EN: the sample row is there, after the breaks, priced and linked",
          sm.get("label") == "Sample price" and sm.get("price") == SAMPLE
          and sm.get("icon") and sm.get("ctaText") == "Get Sample"
          and sm.get("ctaHref") == "/contact/#quote" and sm.get("ctaOpen") is True
          and sm.get("ctaSample") == SAMPLE and sm.get("afterCards") is True, sm)

    tc = ev(TIER_CLICK)
    check("EN: clicking the middle break checks it, and only it",
          tc.get("checked") == [False, True, False] and tc.get("isOn") == [False, True, False],
          {"checked": tc.get("checked"), "isOn": tc.get("isOn")})
    p = tc.get("paint") or []
    check("EN: the chosen break's dot turns brand green, the others do not",
          len(p) == 3 and p[1].get("bg") == "rgb(90, 183, 53)"
          and p[1].get("bc") == "rgb(90, 183, 53)" and "inset" in p[1].get("box", "")
          and p[0].get("bg") == "rgb(255, 255, 255)" and p[2].get("bg") == "rgb(255, 255, 255)",
          p)
    check("EN: the live summary reads the chosen break",
          tc.get("summary") == "Quantity & Pricing: 100-999" and tc.get("summaryHidden") is False,
          [tc.get("summary"), tc.get("summaryHidden")])

    o1 = ev(SAMPLE_OPEN)
    check("EN: the sample button opens the dialog and does not navigate",
          o1["hidden"] is False and o1["path"] == EN, o1)
    o2 = ev(SAMPLE_STATE)
    check("EN: the dialog then gets its is-open class on the next frame",
          o2["hidden"] is False and o2["isOpen"] is True and o2["path"] == EN
          and o1["isOpen"] is False, {"sync": o1.get("isOpen"), "next": o2.get("isOpen")})
    check("EN: the dialog's message is prefilled with the record and the fee",
          o1["before"] == "" and o2["value"] == PREFILL,
          {"before": o1["before"], "got": o2["value"], "want": PREFILL})
    sr = ev(SAMPLE_REST)
    check("EN: the script's own sentence is not written twice on a second click",
          sr["r2"]["value"] == PREFILL, sr["r2"]["value"])
    check("EN: the dialog closes again, and a visitor's own words are never clobbered",
          sr["r3"]["hidden"] is True and sr["r4"]["value"] == "MY OWN TEXT"
          and sr["r4"]["hidden"] is False and sr["closed"] is True,
          {"close": sr["r3"], "reopen": sr["r4"], "final": sr["closed"]})

    cta = ev(CTA_ROW)
    check("EN: the right column's foot is one Send Inquiry, dialog-wired",
          cta.get("n") == 1 and cta["items"][0]["t"] == "Send Inquiry"
          and cta["items"][0]["h"] == "/contact/#quote"
          and cta["items"][0]["open"] is True, cta.get("items"))
    check("EN: no link on the page reads Request Sample any more",
          cta.get("anchorRequestSample") == 0
          and cta.get("rsOccurrences") == 1 and cta.get("rsOnlyInComment") is True,
          {"anchors": cta.get("anchorRequestSample"), "occurrences": cta.get("rsOccurrences"),
           "onlyInComment": cta.get("rsOnlyInComment")})

    v = ev(VIDEO)
    check("EN: the media band grows a Video tab, and only this record has one",
          v.get("videoTab") is True and v.get("videoTabText") == "Video"
          and v.get("tabs") == ["Photos", "Video"], v.get("tabs"))
    check("EN: the video frame is a hidden facade with the poster for that id",
          v.get("videoSlide") is True and v.get("vid") == VIDEO_ID and v.get("hidden") is True
          and v.get("poster") == "https://i.ytimg.com/vi/%s/hqdefault.jpg" % VIDEO_ID
          and v.get("playBtn") is True and v.get("slot") == "2" and v.get("nSlides") == 5,
          {"vid": v.get("vid"), "poster": v.get("poster"), "slot": v.get("slot"),
           "slides": v.get("nSlides"), "hidden": v.get("hidden")})

    # =========================== the translated twin ======================
    open_at(ZH)
    served(ZH, "ZH")
    quiet_hero("ZH")
    ld = ev(LADDER)
    ladder_values(ld, "ZH")
    ladder_cards(ld, "ZH")
    sm = ld.get("sample") or {}
    check("ZH: the sample row keeps its price; the button keeps its own language prefix",
          sm.get("price") == SAMPLE and sm.get("ctaSample") == SAMPLE
          and sm.get("ctaHref") == "/zh/contact/#quote", sm)
    cta = ev(CTA_ROW)
    check("ZH: the right-column button points at the record's own language",
          cta.get("n") == 1 and cta["items"][0]["t"] == "Send Inquiry"
          and cta["items"][0]["h"] == "/zh/contact/#quote"
          and cta["anchorRequestSample"] == 0, cta.get("items"))
    v = ev(VIDEO)
    check("ZH: the translated twin carries the same video frame",
          v.get("videoTab") is True and v.get("vid") == VIDEO_ID, {"tabs": v.get("tabs"), "vid": v.get("vid")})

    # ==================== a record with no tiers and no video =============
    open_at(OTHER)
    served(OTHER, "other")
    quiet_hero("other")
    ld = ev(LADDER)
    check("other: a record with no price tiers has no ladder and no sample row",
          ld.get("found") is False, ld)
    cta = ev(CTA_ROW)
    check("other: the right-column button is the same Send Inquiry",
          cta.get("n") == 1 and cta["items"][0]["t"] == "Send Inquiry"
          and cta["items"][0]["h"] == "/contact/#quote"
          and cta["items"][0]["open"] is True, cta.get("items"))
    v = ev(VIDEO)
    check("other: with no sf_formula_video_url the band stays a lone [Photos]",
          v.get("videoTab") is False and v.get("videoSlide") is False
          and v.get("tabs") == ["Photos"], v.get("tabs"))

    # ============================ the phone ==============================
    open_at(EN, 375, 812)
    served(EN, "EN@375")
    f = ev(FOLD)
    b = f["before"]
    check("375: the list starts folded, behind one button, and the ladder is with the rest",
          b.get("folded") is True and b.get("text") == "View all specs ▾"
          and b.get("btnDisplay") == "inline-flex" and b.get("pricingDisplay") == "none"
          and b.get("openBtnDisplay") == "none",
          b)
    check("375: nothing overflows the viewport while folded",
          b.get("scroll") <= b.get("inner") + 1, [b.get("scroll"), b.get("inner")])
    a = f["after"]
    check("375: unfolding reveals the record's groups",
          a.get("folded") is False and a.get("text") == "Show fewer specs ▴"
          and a.get("pricingDisplay") == "block",
          {"folded": a.get("folded"), "text": a.get("text"), "pricing": a.get("pricingDisplay")})
    check("375: the ladder keeps its three columns — the comparison IS the point",
          len(a.get("gridCols", "").split()) == 3
          and all(c["box"]["t"] == a["cards"][0]["box"]["t"] for c in a["cards"]),
          {"cols": a.get("gridCols"), "tops": [c["box"]["t"] for c in a["cards"]]})
    check("375: the cards tighten and the price steps down to 16px",
          all(c.get("priceFs") == "16px" for c in a["cards"]),
          [c.get("priceFs") for c in a["cards"]])
    bad = []
    for i, c in enumerate(a["cards"]):
        if not (c["box"]["t"] <= c["priceBox"]["t"] and c["priceBox"]["b"] <= c["rangeBox"]["t"] + 0.5
                and c["rangeBox"]["b"] <= c["unitBox"]["t"] + 0.5
                and c["unitBox"]["b"] <= c["dotBox"]["t"] + 0.5
                and c["dotBox"]["b"] <= c["box"]["b"] + 0.5):
            bad.append(i)
    check("375: and each card still stacks price / range / unit / dot inside itself",
          not bad, {"bad": bad, "cards": [{k: v for k, v in c.items() if k.endswith("Box")}
                                          for c in a["cards"]]})
    r = ev(ROW)
    check("375: the sample row's wrap is live, and at this width the row still fits on one line",
          r.get("wrap") == "wrap" and r.get("ml") == "0px"
          and r["ctaOnOwnLine"] is False
          and r["cta"]["r"] <= r["row"]["r"] + 1
          and r["sp"]["r"] + 2 < r["cta"]["l"], r)
    check("375: and it stays inside its column instead of overhanging it",
          r["row"]["r"] <= r["parentRight"] + 1 and r["scroll"] <= r["inner"] + 1,
          {"row": r["row"]["r"], "parent": r["parentRight"],
           "scroll": r["scroll"], "inner": r["inner"]})
    check("375: and the unfolded page still does not overflow sideways",
          r.get("scroll") <= r.get("inner") + 1, [r.get("scroll"), r.get("inner")])

    # One step narrower the same row runs out of room, and the wrap the media
    # query declares is what has to catch it: the button drops to its own line
    # and starts at the row's left edge, not pushed right by the desktop
    # `margin-left: auto`. Without this half, "wrap: wrap" would be a rule
    # nobody ever saw fire.
    open_at(EN, 360, 780)
    served(EN, "EN@360")
    ev("""(() => { const l = document.querySelector('.sf-fdetail-config__list');
                   const b = document.querySelector('.sf-fdetail-config__fold');
                   if (l && l.classList.contains('sf-config-folded') && b) b.click();
                   return true; })()""")
    time.sleep(0.4)
    r = ev(ROW)
    check("360: the sample row runs out of room and the button wraps to its own line",
          r["ctaOnOwnLine"] is True and r["cta"]["t"] >= r["sp"]["b"] - 1, r)
    check("360: ...starting at the row's own left edge, the desktop margin having been zeroed",
          r.get("ml") == "0px" and r["cta"]["l"] <= r["row"]["l"] + 1, r)
    check("360: and nothing overflows, in the row or on the page",
          r["cta"]["r"] <= r["row"]["r"] + 1 and r["row"]["r"] <= r["parentRight"] + 1
          and r["scroll"] <= r["inner"] + 1,
          {"cta": r["cta"]["r"], "row": r["row"]["r"], "parent": r["parentRight"],
           "scroll": r["scroll"], "inner": r["inner"]})
    check("360: the ladder holds its three columns even here",
          len(r.get("gridCols", "").split()) == 3
          and len(set(r.get("cardTops") or [])) == 1, [r.get("gridCols"), r.get("cardTops")])

    errs = ab("errors")
    check("0 page errors", not errs.strip(), errs[:200])
    ab("close")

    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n%d/%d checks passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("FAILED:")
        for n in bad:
            print("  - " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
