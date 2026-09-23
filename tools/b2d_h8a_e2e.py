#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8a E2E — the right column, six edits, driven in a real browser.

Target: the PREFLIGHT copy (2.10.74). Dev still serves 2.10.73 for this batch
(the pull is a separate, user-authorised step), so the candidate exists on the
box only as `sinofresh-theme-preflight`, behind the `X-SF-Preflight: 1` header.

`--live` drops the header and drives dev's own 2.10.73. Every item of this batch
is NEW, so all of them must be RED on live — that is the run that proves this
script can fail, and it is the reason the two runs are reported separately.

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the one
`set headers` call.

What each assertion is anchored to, and what it refuses to be anchored to
-----------------------------------------------------------------------
待办23  the sticky gallery, read as BEHAVIOUR and not as a declaration: the
       computed `position` and `top` say what the stylesheet asked for, and a
       scroll into the middle of the sticky range says whether the element
       actually stays. On a phone the same element must scroll away — a sticky
       column at 375 is exactly the failure mode the brief named.

待办26  the parameter list's own terms, in order. `Packaging` leaving is half
       the claim; the other half is that the row it duplicated still exists on
       the FORM page (`.sf-facts-mini`), because "the value is gone" and "the
       value moved" are different findings and the brief asked for the second.

待办27  the groups, read off the rendered controls: every group's hint, its
       input types, its Custom pick (and that the pick is LAST), its box (and
       that the box belongs to that group), and that the price list is the one
       group with neither. Then the Custom answer is TYPED IN, and the thing
       read back is what the visitor's submission would carry — the hidden
       `input[name=config]` and the dialog's own panel — because "{text}
       (custom)" is a claim about the payload, not about the box.

待办28  the fold, driven: which groups are visible while folded, the button's
       own words, the CTA's box while folded, and the round trip back. The
       no-JS path is asserted through the CSSOM — the fold rule's selector must
       name `.sf-fdetail-config--js` — because "there is no fold without the
       script" is a claim about a selector, and the script is always there when
       a browser is driving.
       The sliding row is read as geometry: one line of tiles, a row wider than
       its own box, and arrows that appear only when that is true.

待办29  the shelf life, read on BOTH carriers, with the value's own name absent
       from the cell — and the record's pool value (24 months) against the spec
       string the page still carries elsewhere (18 months). Reading only the
       first would pass a page that prints the spec value twice.
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PF = json.dumps({"X-SF-Preflight": "1", "Authorization": AUTH})
LIVE = json.dumps({"Authorization": AUTH})

DETAIL = "/formulas/joint-support-soft-chews/"
DETAIL_ZH = "/zh/formulas/joint-support-soft-chews/"
FORM = "/products/soft-chews/"

# The record's six groups, in the order the column renders them (H7l put the
# ladder first, H8a's fold cut then keeps four of them on a phone).
KEYS = ["pricing", "flavor", "weight", "pack", "shape", "container"]
FOLDED = ["pricing", "flavor", "weight", "pack"]

BOXED = ["flavor", "weight", "pack", "shape", "container"]

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
    print(("PASS " if ok else "FAIL ") + name + ("  | " + str(detail)[:340] if detail else ""))


def session(live=False):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE if live else PF)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def open_at(path, w, h=900, fresh_fold=True):
    ab("open", BASE + path)
    time.sleep(2.0)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.75)
        got = ev("JSON.stringify({w: innerWidth})")
        if isinstance(got, dict) and got.get("w") == w:
            break
        time.sleep(0.5)
    else:
        raise SystemExit("viewport %d did not take on %s" % (w, path))
    if fresh_fold and w <= 480:
        # The fold remembers itself per session; a run that unfolded earlier
        # would otherwise start this one unfolded and read as a product pass.
        ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } "
           "catch (e) {} return 1; })()")
        ab("reload")
        time.sleep(2.2)
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.6)


def served(path, why, live=False, with_config=True):
    """Which artifact answered, asserted BEFORE anything is asserted about it."""
    v = "2.10.73" if live else "2.10.74"
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const scripts = Array.from(document.querySelectorAll('script[src]')).map(x => x.src);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      const cfg = scripts.find(h => h.includes('config.js')) || '';
      return { path: location.pathname, title: document.title, theme, cfg,
               pre: theme.includes('-preflight'),
               ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               cfgVer: (cfg.match(/ver=([0-9.]+)/) || [])[1] || null,
               h1: document.querySelectorAll('h1').length };
    })()""")
    ok = (isinstance(s, dict) and s.get("ver") == v and s.get("h1") == 1
          and s.get("pre") is (not live))
    if not live and with_config:
        ok = ok and s.get("cfgVer") == "1.4.0"
    check("the %s theme answered (%s)  [%s]" % (v, path, why), ok, s)
    return s


# ------------------------------------------------------------------ probes

FOLD_RULE = """(() => {
  // The no-JS claim is a claim about a SELECTOR, so it is read from the CSSOM.
  //
  // Two mechanics, both of which cost a run to find:
  //   * recursion must be keyed on `r.media !== undefined`, NOT on `r.cssRules`
  //     being truthy. Under CSS Nesting every style rule carries an empty
  //     cssRules list, which is a truthy object, so the naive test swallows the
  //     whole sheet and finds nothing.
  //   * selectors come back NORMALISED: `nth-child(n + 5)` as written is
  //     `nth-child(n+5)` in selectorText.
  const sh = Array.from(document.styleSheets).find(s => s.href && s.href.includes('style.css'));
  if (!sh) return {none: 'no style.css'};
  let rs;
  try { rs = sh.cssRules; } catch (e) { return {none: 'blocked'}; }
  let found = null;
  const walk = (list, media) => {
    for (const r of Array.from(list)) {
      if (r.media !== undefined && r.cssRules) { walk(r.cssRules, r.conditionText || media); continue; }
      const sel = r.selectorText;
      if (sel && sel.indexOf('sf-config-folded') >= 0) {
        found = {sel: sel, media: media || null,
                 body: ((r.style && r.style.cssText) || '').replace(/\\s+/g, ' ').trim().slice(0, 120)};
      }
    }
  };
  walk(rs, null);
  return found;
})()"""

GROUPS = """(() => {
  const root = document.querySelector('[data-sf-config]');
  if (!root) return {absent: true};
  const qa = (s, r) => Array.from((r || root).querySelectorAll(s));
  const q = (s, r) => (r || root).querySelector(s);
  const list = q('.sf-fdetail-config__list');
  const groups = qa('.sf-fdetail-config__group', list || root);
  const box = e => { const b = e.getBoundingClientRect();
    return {w: +b.width.toFixed(1), h: +b.height.toFixed(1), t: +b.top.toFixed(1),
            l: +b.left.toFixed(1), b: +b.bottom.toFixed(1)}; };
  const info = groups.map(g => {
    const key = g.getAttribute('data-sf-config-group');
    const row = g.querySelector('.sf-fdetail-config__row');
    const hint = row ? row.querySelector('.sf-fdetail-config__hint') : null;
    const opts = qa('.sf-fdetail-config__opt', g);
    const inputs = qa('.sf-fdetail-config__input', g);
    const picks = qa('.sf-fdetail-config__opt[data-sf-config-custom]', g);
    const cb = g.querySelector('[data-sf-config-custom-for]');
    return {
      key,
      label: (row && row.querySelector('.sf-fdetail-config__label'))
             ? row.querySelector('.sf-fdetail-config__label').textContent.trim() : null,
      hint: hint ? hint.textContent.trim() : null,
      nOpts: opts.length,
      types: Array.from(new Set(inputs.map(i => i.type))).sort(),
      names: Array.from(new Set(inputs.map(i => i.name))),
      nChecked: inputs.filter(i => i.checked).length,
      nPick: picks.length,
      pickLast: picks.length ? (opts.indexOf(picks[0]) === opts.length - 1) : null,
      pickTag: picks.length ? picks[0].querySelector('input').type : null,
      pickValue: picks.length ? picks[0].querySelector('input').value : null,
      // The pick's WORDS live in two different carriers depending on the
      // group's style: a chip row puts them in `__text`, an image row in
      // `__empty-label`. Reading only the first would call four correct groups
      // mislabelled — the by-name guess this project has made four times.
      pickWords: picks.length
        ? ((picks[0].querySelector('.sf-fdetail-config__text')
            || picks[0].querySelector('.sf-fdetail-config__empty-label')
            || {}).textContent || null)
        : null,
      boxIn: !!cb, boxHidden: cb ? cb.hidden : null,
      boxFor: cb ? cb.getAttribute('data-sf-config-custom-for') : null,
      boxParentIsGroup: cb ? (cb.parentNode === g) : null,
      boxIsLast: cb ? (cb === g.lastElementChild) : null,
      // NOT "the box's previous sibling is the row": config.js wraps the row in
      // a rail, so on the two image groups the sibling is the rail. The claim
      // that survives the wrapper is the document ORDER of the two.
      rowBeforeBox: cb && row ? (row.compareDocumentPosition(cb) & 4) === 4 : null,
      visible: getComputedStyle(g).display !== 'none',
      nth: Array.from(g.parentNode.children).indexOf(g) + 1,
      box: box(g),
    };
  });
  const fold = q('.sf-fdetail-config__fold');
  const cta = document.querySelector('a.sf-fdetail2__cta');
  return {
    jsClass: root.classList.contains('sf-fdetail-config--js'),
    folded: list ? list.classList.contains('sf-config-folded') : null,
    listDisplay: list ? getComputedStyle(list).display : null,
    openBtn: (() => { const b = q('.sf-fdetail-config__open');
      return b ? getComputedStyle(b).display : 'absent'; })(),
    foldText: fold ? fold.textContent.trim() : null,
    foldDisplay: fold ? getComputedStyle(fold).display : 'absent',
    cta: cta ? {txt: cta.textContent.trim(), href: cta.getAttribute('href'),
                box: box(cta), display: getComputedStyle(cta).display,
                vis: getComputedStyle(cta).visibility} : null,
    groups: info,
  };
})()"""

SHAPE_ROW = """(() => {
  const g = document.querySelector('[data-sf-config-group="shape"]');
  if (!g) return {absent: true};
  const row = g.querySelector('.sf-fdetail-config__options');
  const tiles = Array.from(row.querySelectorAll('.sf-fdetail-config__opt'));
  const rail = g.querySelector('.sf-fdetail-config__rail');
  const arrows = Array.from(g.querySelectorAll('.sf-fdetail-config__arrow'));
  const cs = getComputedStyle(row);
  const w = e => +e.getBoundingClientRect().width.toFixed(1);
  const l = e => +e.getBoundingClientRect().left.toFixed(1);
  const t = e => +e.getBoundingClientRect().top.toFixed(1);
  return {
    flexWrap: cs.flexWrap, overflowX: cs.overflowX,
    clientW: +row.clientWidth.toFixed(1), scrollW: +row.scrollWidth.toFixed(1),
    scrollLeft: +row.scrollLeft.toFixed(1),
    scrollable: row.scrollWidth - row.clientWidth > 4,
    railInGroup: rail ? (rail.parentNode === g) : null,
    railScrolls: rail ? rail.classList.contains('sf-fdetail-config__rail--scrolls') : null,
    railWrapsRow: rail ? (row.parentNode === rail) : null,
    nTiles: tiles.length,
    distinctTops: Array.from(new Set(tiles.map(t))).length,
    distinctLefts: Array.from(new Set(tiles.map(l))).length,
    tileW: tiles.length ? w(tiles[0]) : null,
    perView: tiles.length ? +(row.clientWidth / w(tiles[0])).toFixed(2) : null,
    nArrows: arrows.length,
    // `display` on its own is not the claim: the arrows are absolutely
    // positioned, which BLOCKIFIES `inline-flex` into `flex`, so the used value
    // is not the one the stylesheet wrote. What is being claimed is that they
    // are painted and have a box — and the click below is what proves they are
    // pressable.
    arrowBox: arrows.map(a => { const r = a.getBoundingClientRect();
      return {d: getComputedStyle(a).display, w: +r.width.toFixed(1), h: +r.height.toFixed(1)}; }),
    nextDisabled: arrows.length > 1 ? arrows[1].disabled : null,
  };
})()"""

STICKY = """(() => {
  const m = document.querySelector('.sf-fdetail2__media');
  if (!m) return {absent: true};
  const inner = document.querySelector('.sf-fdetail2__inner');
  const cs = getComputedStyle(m);
  const box = () => { const r = m.getBoundingClientRect();
    return {t: +r.top.toFixed(1), b: +r.bottom.toFixed(1), h: +r.height.toFixed(1)}; };
  const pageTop = m.getBoundingClientRect().top + window.scrollY;
  const innerBottom = inner ? inner.getBoundingClientRect().bottom + window.scrollY : null;
  return {pos: cs.position, top: cs.top, alignSelf: cs.alignSelf,
          pageTop: +pageTop.toFixed(0), innerBottom: innerBottom === null ? null : +innerBottom.toFixed(0),
          mh: box().h, vh: innerHeight,
          parentOverflow: inner ? getComputedStyle(inner).overflow : null,
          rootOverflowX: getComputedStyle(document.documentElement).overflowX,
          bodyOverflowX: getComputedStyle(document.body).overflowX,
          at: box(),
          scrollMax: document.documentElement.scrollHeight - innerHeight};
})()"""


def sticky_scroll(spec):
    """Scroll into the MIDDLE of the sticky range and read the box back.

    The range is derived rather than guessed: the element can only stick while
    its containing block is still under it, so a scroll past `innerBottom - mh`
    would read "not 100" from a page that is behaving perfectly.
    """
    lo = spec["pageTop"] - 100 + 40
    hi = (spec["innerBottom"] or 0) - spec["mh"] - 100 - 40
    target = int(min(max((lo + hi) / 2.0, 40), spec["scrollMax"] - 10))
    ev("(() => { window.scrollTo(0, %d); return 1; })()" % target)
    time.sleep(1.0)
    got = ev("(() => { const m = document.querySelector('.sf-fdetail2__media'); "
             "const r = m.getBoundingClientRect(); "
             "return {t: +r.top.toFixed(1), y: Math.round(window.scrollY)}; })()")
    return target, got


PARAMS = """(() => {
  const dl = document.querySelector('.sf-fdetail2__params');
  if (!dl) return {absent: true};
  const terms = Array.from(dl.querySelectorAll('dt.sf-fdetail2__term')).map(d => d.textContent.trim());
  const vals = Array.from(dl.querySelectorAll('dd.sf-fdetail2__value')).map(d => d.textContent.trim());
  const rows = {};
  dl.querySelectorAll('dt.sf-fdetail2__term').forEach(dt => {
    const dd = dt.nextElementSibling;
    rows[dt.textContent.trim()] = dd ? dd.textContent.trim() : null;
  });
  const cells = Array.from(document.querySelectorAll('.sf-fdetail2__value, .sf-fdetail-specs__value'))
    .map(e => e.textContent.trim());
  const reads = cells.filter(t => /month/i.test(t));
  return {terms, rows, reads,
          rawShelf: rows['Shelf life'] || null,
          inputs: dl.querySelectorAll('input, select').length};
})()"""

FORMCELL = """(() => {
  const items = Array.from(document.querySelectorAll('.sf-facts-mini__item')).map(e => {
    const l = e.querySelector('.sf-facts-mini__label');
    const v = e.querySelector('.sf-facts-mini__value');
    return {label: l ? l.textContent.trim() : null,
            value: v ? v.textContent.trim() : null,
            dataLabel: v ? v.getAttribute('data-label') : null};
  });
  return {items};
})()"""

CARRIER = """(() => {
  const root = document.querySelector('[data-sf-config]');
  const box = root ? root.querySelector('[data-sf-config-custom-for="weight"]') : null;
  const input = root ? root.querySelector('[data-sf-config-custom-input="weight"]') : null;
  const summary = root ? root.querySelector('[data-sf-config-summary]') : null;
  const modal = document.querySelector('.sf-inquiry-modal');
  const carrier = modal ? modal.querySelector('input[name="config"]') : null;
  const panel = modal ? modal.querySelector('.sf-inquiry-modal__rows') : null;
  const tiers = Array.from(document.querySelectorAll('[data-sf-config-group="pricing"] .sf-tier'))
    .map(t => ({range: (t.querySelector('.sf-tier__range') || {}).textContent,
                price: (t.querySelector('.sf-tier__price') || {}).textContent,
                on: !!t.querySelector('input').checked}));
  return {
    boxHidden: box ? box.hidden : 'absent',
    boxDisplay: box ? getComputedStyle(box).display : 'absent',
    inputValue: input ? input.value : 'absent',
    focused: input ? (document.activeElement === input) : null,
    summaryHidden: summary ? summary.hidden : 'absent',
    summaryText: summary ? summary.textContent.trim() : 'absent',
    carrierValue: carrier ? carrier.value : 'absent',
    panelOwn: panel ? panel.dataset.sfOwn : undefined,
    panelText: panel ? panel.textContent.replace(/\\s+/g, ' ').trim().slice(0, 400) : 'absent',
    tiers,
  };
})()"""


def typed(text):
    return json.dumps(text)


def run(live=False):
    session(live)
    # ------------------------------------------------------------ desktop
    print("\n===== 1440x900 (desktop) =====")
    open_at(DETAIL, 1440)
    served(DETAIL, "the desktop pass", live)

    g = ev(GROUPS)
    if g.get("absent"):
        check("待办27 the parameter column is on the page", False, "no [data-sf-config]")
        g = {"groups": [], "cta": None}

    keys = [x["key"] for x in g.get("groups", [])]
    check("待办27 the column carries the record's six groups", keys == KEYS, keys)

    byk = {x["key"]: x for x in g.get("groups", [])}

    # 待办27 — one pick per group, and Custom is the last of them
    check("待办27 Flavor and Pack Size stop being multi-selects",
          byk.get("flavor", {}).get("types") == ["radio"]
          and byk.get("pack", {}).get("types") == ["radio"],
          {k: byk.get(k, {}).get("types") for k in ("flavor", "pack", "weight", "shape")})
    check("待办27 ...while every other group keeps the control it had",
          all(byk.get(k, {}).get("types") == ["radio"] for k in ("weight", "shape", "container")),
          {k: byk.get(k, {}).get("types") for k in ("weight", "shape", "container")})
    check("待办27 each group is one question with one name",
          all(len(byk.get(k, {}).get("names") or []) == 1 for k in KEYS),
          {k: byk.get(k, {}).get("names") for k in KEYS})
    check("待办27 the hint stops promising more than one",
          byk.get("flavor", {}).get("hint") == "Choose one"
          and byk.get("pack", {}).get("hint") not in ("Choose one or more", None),
          {k: byk.get(k, {}).get("hint") for k in ("flavor", "pack", "weight")})

    check("待办27 the five typable groups each end in a Custom pick",
          all(byk.get(k, {}).get("nPick") == 1 and byk.get(k, {}).get("pickLast") is True
              and byk.get(k, {}).get("pickWords") == "Custom" for k in BOXED),
          {k: (byk.get(k, {}).get("nPick"), byk.get(k, {}).get("pickLast"),
               byk.get(k, {}).get("pickWords")) for k in BOXED})
    check("待办27 ...and each of them carries a box of its own",
          all(byk.get(k, {}).get("boxIn") and byk.get(k, {}).get("boxHidden") is True
              and byk.get(k, {}).get("boxFor") == k
              and byk.get(k, {}).get("boxParentIsGroup") is True
              and byk.get(k, {}).get("boxIsLast") is True
              and byk.get(k, {}).get("rowBeforeBox") is True for k in BOXED),
          {k: (byk.get(k, {}).get("boxParentIsGroup"), byk.get(k, {}).get("boxIsLast"),
               byk.get(k, {}).get("rowBeforeBox")) for k in BOXED})
    check("待办27 the price list gets neither, because a price is not typed",
          byk.get("pricing", {}).get("nPick") == 0
          and byk.get("pricing", {}).get("boxIn") is False,
          {k: byk.get("pricing", {}).get(k) for k in ("nPick", "boxIn")})

    # 待办23 — the sticky gallery, as behaviour
    sk = ev(STICKY)
    check("待办23 the media column is declared sticky, 100px down, desktop only",
          sk.get("pos") == "sticky" and sk.get("top") == "100px"
          and sk.get("alignSelf") == "start",
          {k: sk.get(k) for k in ("pos", "top", "alignSelf")})
    check("待办23 ...and nothing between it and the root clips",
          sk.get("parentOverflow") in ("visible", "clip", None)
          and sk.get("rootOverflowX") == "clip",
          {k: sk.get(k) for k in ("parentOverflow", "rootOverflowX", "bodyOverflowX")})
    if not sk.get("absent") and sk.get("scrollMax", 0) > 200:
        tgt, got = sticky_scroll(sk)
        check("待办23 ...and it really stays at 100px while the page scrolls",
              abs(got.get("t", -999) - 100.0) <= 1.5,
              {"scrollY": got.get("y"), "target": tgt, "mediaTop": got.get("t")})
    else:
        check("待办23 ...and it really stays at 100px while the page scrolls", False,
              "page too short to test")

    # 待办26 + 待办29 — the parameter list
    p = ev(PARAMS)
    check("待办26 the Packaging row has left the parameter list",
          "Packaging" not in (p.get("terms") or []),
          p.get("terms"))
    check("待办26 ...and the row it duplicated is still the list's own three",
          p.get("terms") == ["Shelf life", "Certifications", "Lead time"], p.get("terms"))
    check("待办29 the shelf life prints the pool value, without its own name",
          p.get("rawShelf") == "24 months"
          and not any("shelf life" in (t or "").lower() for t in (p.get("reads") or [])),
          {"Shelf life": p.get("rawShelf"), "reads": p.get("reads")})
    check("待办29 ...and the visitor cannot pick a different one",
          p.get("inputs") == 0, {"inputs in the dl": p.get("inputs")})
    check("待办29 the spec sheet agrees with it",
          (p.get("reads") or []).count("24 months") == 2, p.get("reads"))

    # 待办28 — the sliding row, and the arrows that serve it
    sh = ev(SHAPE_ROW)
    check("待办28 the shape row is one line that slides",
          sh.get("distinctTops") == 1 and sh.get("flexWrap") == "nowrap"
          and sh.get("overflowX") == "auto",
          {k: sh.get(k) for k in ("distinctTops", "flexWrap", "overflowX")})
    check("待办28 ...wider than its own box, which is what makes it slide",
          sh.get("scrollable") is True,
          {k: sh.get(k) for k in ("clientW", "scrollW", "nTiles", "tileW")})
    check("待办28 ...and the rail is wrapped around it with the arrows painted",
          sh.get("railWrapsRow") is True and sh.get("railInGroup") is True
          and sh.get("railScrolls") is True and sh.get("nArrows") == 2
          and all(a.get("d") != "none" and a.get("w", 0) > 8 and a.get("h", 0) > 8
                  for a in (sh.get("arrowBox") or [])),
          {k: sh.get(k) for k in ("railWrapsRow", "railScrolls", "nArrows", "arrowBox")})
    check("待办28 ...the first arrow knows it is at the start",
          sh.get("nextDisabled") is False, {"nextDisabled": sh.get("nextDisabled")})

    # A REAL click on the next arrow, with a hit test first: the arrows are
    # absolute-positioned outside the row, and the page has to be scrolled to
    # them before a pointer event can land on one.
    if sh.get("nArrows") == 2:
        arrow = ('[data-sf-config-group="shape"] .sf-fdetail-config__arrow--next')
        ab("scrollintoview", arrow)
        time.sleep(0.8)
        hit = ev("""(() => { const a = document.querySelector(
            '[data-sf-config-group="shape"] .sf-fdetail-config__arrow--next');
          const r = a.getBoundingClientRect();
          const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return {same: at === a, tag: at ? at.className : null}; })()""")
        before = ev("""(() => +document.querySelector(
            '[data-sf-config-group="shape"] .sf-fdetail-config__options').scrollLeft.toFixed(1))()""")
        ab("click", arrow)
        time.sleep(1.2)
        after = ev("""(() => { const row = document.querySelector(
            '[data-sf-config-group="shape"] .sf-fdetail-config__options');
          return {x: +row.scrollLeft.toFixed(1),
                  prevOff: document.querySelector(
                    '[data-sf-config-group="shape"] .sf-fdetail-config__arrow--prev').disabled}; })()""")
        check("待办28 the next arrow is where the pointer lands, and it scrolls the row",
              hit.get("same") is True and isinstance(after, dict)
              and after.get("x", 0) > before + 20,
              {"hit": hit, "before": before, "after": after})
        check("待办28 ...and having scrolled, the previous arrow becomes usable",
              (after or {}).get("prevOff") is False, after)
    else:
        check("待办28 the next arrow is where the pointer lands, and it scrolls the row",
              False, "no arrows to click")

    # 待办28 — no fold on a desktop. The CLASS is on the list at every width
    # (config.js applies it unconditionally, and the button lives for the phone)
    # — what makes the desktop unfolded is that the rule that hides the tail is
    # scoped to <=480, so the claim is measured on the paint, not on the class.
    check("待办28 the desktop list is never folded",
          all(x["visible"] for x in g.get("groups", []))
          and g.get("foldDisplay") == "none",
          {"folded": g.get("folded"), "foldDisplay": g.get("foldDisplay"),
           "visible": [x["visible"] for x in g.get("groups", [])]})

    # 待办27 — the Custom answer, typed in and read back from the payload
    pick = '[data-sf-config-group="weight"] .sf-fdetail-config__opt[data-sf-config-custom] .sf-fdetail-config__input'
    tier = '[data-sf-config-group="pricing"] .sf-tier:nth-child(2) .sf-fdetail-config__input'
    ab("scrollintoview", '[data-sf-config-group="weight"]')
    time.sleep(0.6)
    ab("click", tier)
    time.sleep(0.5)
    ab("click", pick)
    time.sleep(0.4)
    # TWO-STAGE DISPLAY: the box is revealed inside the change handler, and the
    # focus moves in the same pass — a single same-tick read has been enough to
    # report "did not open" for a box that is opening.
    early = ev(CARRIER)
    time.sleep(1.0)
    c = ev(CARRIER)
    check("待办27 the Custom pick reveals its box",
          c.get("boxHidden") is False and c.get("boxDisplay") != "none",
          {k: c.get(k) for k in ("boxHidden", "boxDisplay")})
    check("待办27 ...and puts the caret in it, so the visitor types straight away",
          c.get("focused") is True, {"focused": c.get("focused"), "early": early.get("focused")})

    ab("fill", '[data-sf-config-custom-input="weight"]', "5 g chew")
    time.sleep(0.5)
    ab("press", "Tab")
    time.sleep(0.6)
    c = ev(CARRIER)
    check("待办27 the typed answer is what the submission carries, marked as custom",
          '"weight":"5 g chew (custom)"' in (c.get("carrierValue") or ""),
          c.get("carrierValue"))
    check("待办27 ...and the visitor sees the same words before sending",
          "5 g chew (custom)" in (c.get("summaryText") or ""),
          c.get("summaryText"))
    check("待办27 ...and the dialog's panel is the visitor's list, not the product's",
          "5 g chew (custom)" in (c.get("panelText") or ""),
          c.get("panelText"))
    check("待办27 the price carries no Custom: the chosen break is unchanged",
          any(t.get("on") for t in (c.get("tiers") or []))
          and not any("custom" in (t.get("range") or "").lower()
                      or "custom" in (t.get("price") or "").lower()
                      for t in (c.get("tiers") or [])),
          c.get("tiers"))

    # ------------------------------------------------------------- phone
    print("\n===== 375x812 (phone) =====")
    open_at(DETAIL, 375, 812)
    served(DETAIL, "the phone pass", live)
    g3 = ev(GROUPS)
    vis = [x["key"] for x in g3.get("groups", []) if x["visible"]]
    check("待办28 the phone fold keeps the ladder and the three the brief names",
          g3.get("folded") is True and vis == FOLDED,
          {"folded": g3.get("folded"), "visible": vis, "nth": [x["nth"] for x in g3.get("groups", [])]})
    check("待办28 ...and the button says what pressing it will do",
          g3.get("foldText") == "View all specs \u25be" and g3.get("foldDisplay") != "none",
          {"text": g3.get("foldText"), "display": g3.get("foldDisplay")})
    check("待办28 the CTA stays visible while the list is folded",
          (g3.get("cta") or {}).get("txt") == "Send Inquiry"
          and (g3.get("cta") or {}).get("box", {}).get("h", 0) > 20
          and (g3.get("cta") or {}).get("display") != "none"
          and (g3.get("cta") or {}).get("vis") == "visible",
          g3.get("cta"))

    ab("scrollintoview", ".sf-fdetail-config__fold")
    time.sleep(0.6)
    ab("click", ".sf-fdetail-config__fold")
    time.sleep(0.9)
    g3b = ev(GROUPS)
    vis2 = [x["key"] for x in g3b.get("groups", []) if x["visible"]]
    check("待办28 the button unfolds to every group",
          g3b.get("folded") is False and vis2 == KEYS
          and g3b.get("foldText") == "Show fewer specs \u25b4",
          {"folded": g3b.get("folded"), "visible": vis2, "text": g3b.get("foldText")})

    fr = ev(FOLD_RULE)
    check("待办28 the fold rule is the script's, phone-only, and it hides the tail",
          isinstance(fr, dict) and "sf-fdetail-config--js" in (fr.get("sel") or "")
          and "nth-child(n+5)" in (fr.get("sel") or "")
          and "480px" in (fr.get("media") or "")
          and "display: none" in (fr.get("body") or ""),
          fr)

    # 待办28 — the sliding row, probed while it is REACHABLE. Behind the fold on
    # a phone the shape row is `display: none`, so a zero-width tile here means
    # "the group is hidden", not "the row does not slide" — the check would have
    # reported the fold it had just proved.
    sh3 = ev(SHAPE_ROW)
    check("待办28 the shape row slides on a phone too, one and a half tiles at a time",
          sh3.get("distinctTops") == 1 and sh3.get("scrollable") is True
          and 1.3 <= (sh3.get("perView") or 0) <= 1.7,
          {k: sh3.get(k) for k in ("distinctTops", "scrollable", "perView", "tileW", "absent")})
    check("待办28 ...with the arrows out of the way, because a thumb has the row",
          sh3.get("nArrows") == 2
          and all(a.get("d") == "none" for a in (sh3.get("arrowBox") or [])),
          sh3.get("arrowBox"))

    # The button moves down when the list unfolds, so it has to be found again
    # before it can be pressed a second time. One click, not two: pressing it an
    # odd number of times would leave the list unfolded and read as the product
    # failing to fold back.
    ab("scrollintoview", ".sf-fdetail-config__fold")
    time.sleep(0.6)
    ab("click", ".sf-fdetail-config__fold")
    time.sleep(0.9)
    g3c = ev(GROUPS)
    vis3 = [x["key"] for x in g3c.get("groups", []) if x["visible"]]
    check("待办28 ...and folds it back, not just once",
          g3c.get("folded") is True and vis3 == FOLDED,
          {"folded": g3c.get("folded"), "visible": vis3})

    sk3 = ev(STICKY)
    check("待办23 the phone does not stick the gallery",
          sk3.get("pos") != "sticky", {k: sk3.get(k) for k in ("pos", "top")})

    # ------------------------------------------------------------ tablet
    print("\n===== 768x1024 (tablet) =====")
    open_at(DETAIL, 768, 1024)
    served(DETAIL, "the tablet pass", live)
    gt = ev(GROUPS)
    check("待办28 the tablet keeps the drawer, and the fold stays out of it",
          gt.get("openBtn") not in ("none", "absent") and gt.get("listDisplay") == "none"
          and gt.get("foldDisplay") in ("none", "absent"),
          {k: gt.get(k) for k in ("openBtn", "listDisplay", "foldDisplay")})

    # --------------------------------------------------------- the form page
    print("\n===== the form page (待办26's value source) =====")
    open_at(FORM, 1440)
    served(FORM, "待办26 source", live, with_config=False)
    fc = ev(FORMCELL)
    pack = [i for i in (fc.get("items") or []) if (i.get("dataLabel") or "") == "Packaging formats"]
    check("待办26 the form page still prints the packaging formats the row carried",
          len(pack) == 1 and len(pack[0].get("value") or "") > 20
          and "custom formats" in (pack[0].get("value") or ""),
          pack[:1])

    # ------------------------------------------------------------ zh twin
    print("\n===== the zh twin =====")
    open_at(DETAIL_ZH, 1440)
    served(DETAIL_ZH, "the zh twin", live)
    z = ev(GROUPS)
    zp = ev(PARAMS)
    zk = [x["key"] for x in z.get("groups", [])]
    zby = {x["key"]: x for x in z.get("groups", [])}
    check("待办26/29 the zh twin retires the row and prints the pool value too",
          zp.get("terms") == ["Shelf life", "Certifications", "Lead time"]
          and zp.get("rawShelf") == "24 months",
          {"terms": zp.get("terms"), "Shelf life": zp.get("rawShelf")})
    check("待办27 the zh twin offers the same five Custom answers",
          zk == KEYS and all(zby.get(k, {}).get("nPick") == 1
                             and zby.get(k, {}).get("pickLast") is True for k in BOXED),
          {k: zby.get(k, {}).get("nPick") for k in KEYS})

    # --------------------------------------------------------------- summary
    bad = [r for r in RESULTS if not r[1]]
    print("\n%s  batch H8a E2E  (%d checks, %d failed)  [%s]"
          % ("PASS" if not bad else "FAIL", len(RESULTS), len(bad),
             "LIVE 2.10.73" if live else "PREFLIGHT 2.10.74"))
    if bad:
        for n, _, det in bad:
            print("   FAIL %s  | %s" % (n, det[:200]))
    out = {"live": live, "checks": [{"name": n, "ok": o, "detail": d}
                                    for n, o, d in RESULTS],
           "ok": not bad, "total": len(RESULTS), "failed": len(bad)}
    path = "/tmp/h8a-e2e-%s.json" % ("live" if live else "pre")
    json.dump(out, open(path, "w"), indent=1)
    print("  json -> %s" % path)
    return 0 if not bad else 1


def main():
    return run(live="--live" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
