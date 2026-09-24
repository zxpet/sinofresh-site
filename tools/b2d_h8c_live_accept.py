#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8c — browser acceptance on the install the pull landed on.

The service-side pass reads bytes; this reads behaviour. It runs with NO
preflight header, against the docroot dev actually answers from, and covers the
five interactive things the brief names plus the whole-card link the batch is
about. It is the same "what is on the wire" idea one level down: a stylesheet can
contain `position: sticky` and never show it, and an anchor can be in the markup
while the card around it is not clickable.

Five mechanics this file is careful about, each of which has cost this project
real time:

  * `mouse move` needs INTEGER coordinates. A float leaves the pointer where it
    was, so `mouse down` lands at (0,0) on the header, and the tool reports no
    error at all — it looks exactly like "the card is not clickable".
  * the card's centre, not `click <selector>`: the selector click aims at the
    anchor's own middle, so it would pass on a card whose overlay had vanished.
  * `open` drops custom headers and `set credentials` and `set headers` erase
    each other, so the session is built as open -> set headers(Auth) -> reload.
  * a navigated page is not a loaded page: every navigation is followed by a
    readiness gate (readyState + title + at least one stylesheet).
  * on a phone the site's own floating buttons and cookie banner hang over the
    lower part of the card. Every non-link point is therefore classified as the
    link, as one of those layers, or as `other:` — and `other:` must be empty.

    ~/.workbuddy/binaries/python/envs/default/bin/python tools/b2d_h8c_live_accept.py
"""
import base64
import json
import os
import subprocess
import sys
import time

from PIL import Image

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
LIVE = json.dumps({"Authorization": AUTH})

OUT = "docs/batchH8c-deploy-shots"
TMP = "_backup/_h8c_accept_tmp"
EXPECT_VER = "2.10.81"

OVERVIEW = "/services/"
CHEWS = "/formulas/joint-support-soft-chews/"
POWDER = "/formulas/probiotic-powder/"
OEM = "/services/oem/"

# (route, the page's own h1, the heading the overview's card carries)
# Three strings, not two: the card says "OEM — You Bring the Formula" and the
# page it opens is titled "OEM Manufacturing — You Bring the Formula", and a
# single list used for both would pass on whichever of the two it was written
# from while saying nothing about the other.
ROUTES = [("/services/oem/", "OEM Manufacturing \u2014 You Bring the Formula",
           "OEM \u2014 You Bring the Formula"),
          ("/services/odm/", "ODM Development \u2014 We Develop From Your Idea",
           "ODM \u2014 We Develop From Your Idea"),
          ("/services/contract-manufacturing/",
           "Contract Manufacturing \u2014 You Own the IP",
           "Contract Manufacturing \u2014 You Own the IP"),
          ("/services/private-label/",
           "Private Label \u2014 Pick From Our Proven Formulas",
           "Private Label \u2014 Pick From Our Proven Formulas")]

CARD = ".sf-card--roomy"
MEDIA = ".sf-fdetail2__media"
PARAMS = ".sf-fdetail2__params"
LIST = ".sf-fdetail-config__list"
FOLD = ".sf-fdetail-config__fold"
THUMBS = ".sf-gallery__thumbs"

ROWS = []
FRAMES = []
WIDTH = {"now": 1440, "height": 1000}


def ab(*a, timeout=300):
    return subprocess.run(["agent-browser", *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def ev(js):
    raw = ab("eval", js)
    if not raw:
        return None
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


def check(label, ok, detail=None):
    ROWS.append({"label": label, "ok": bool(ok), "detail": detail or {}})
    print("%-5s %s" % ("ok" if ok else "FAIL", label))
    if detail:
        print("      %s" % json.dumps(detail, ensure_ascii=False)[:250])


def wait_ready(tries=25):
    for _ in range(tries):
        st = ev("JSON.stringify({rs: document.readyState, t: document.title,"
                " n: document.querySelectorAll('link[rel=stylesheet]').length})")
        if (isinstance(st, dict) and st.get("rs") == "complete"
                and st.get("n", 0) > 0 and st.get("t")):
            return True
        time.sleep(0.8)
    return False


def session():
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE)
    time.sleep(0.6)
    ab("reload")
    wait_ready()


def serve():
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]'))
        .map(x => x.href);
      const t = l.find(h => h.includes('sinofresh-theme')) || '';
      return { dir: (t.match(/themes\\/([a-z-]+)\\//) || [])[1] || null,
               ver: (t.match(/ver=([0-9.]+)/) || [])[1] || null,
               path: location.pathname, title: document.title }; })()""")


def at(path, w, h=1000, settle=1.6):
    ab("open", BASE + path)
    time.sleep(settle)
    ab("set", "headers", LIVE)
    time.sleep(0.4)
    ab("reload")
    wait_ready()
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, p: location.pathname})")
        if isinstance(got, dict) and got.get("w") == w:
            break
        time.sleep(0.5)
    else:
        raise SystemExit("viewport %d did not take on %s" % (w, path))
    WIDTH["now"], WIDTH["height"] = w, h
    # The cookie banner is a fixed layer that sits over the card by design; the
    # hit test classifies it, and the frames hide it so the card is legible.
    ev("(() => { let n = 0; document.querySelectorAll('.sf-cookie-banner')"
       ".forEach(e => { e.style.display = 'none'; n++; }); return n; })()")
    return serve()


def prescroll():
    info = ev("JSON.stringify({h: document.documentElement.scrollHeight})") or {}
    y, total = 0, info.get("h") or 0
    while y < total:
        ab("eval", "window.scrollTo(0, %d)" % y)
        time.sleep(0.3)
        y += 700
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(1.0)


# --------------------------------------------------------------- measurements
GRID_JS = """(() => {
  const cards = Array.from(document.querySelectorAll('.sf-card--roomy'));
  const c = cards[__I__];
  if (!c) return {absent: true, n: cards.length};
  c.scrollIntoView({block: 'center'});
  const r = c.getBoundingClientRect();
  const a = c.querySelector('a.sf-card__title-link');
  const cls = e => {
    if (!e) return 'none';
    if (e === a || (a && (a.contains(e) || e.contains(a)))) return 'link';
    if (e.closest && e.closest('.sf-float, .sf-float-stack, [class*="sf-float-btn"],'
        + ' .sf-cookie-banner')) return 'layer';
    return 'other:' + e.tagName + '.' + String(e.className || '').slice(0, 40);
  };
  const NX = 7, NY = 5, mx = r.width * 0.06, my = r.height * 0.06, names = [];
  for (let iy = 0; iy < NY; iy++) for (let ix = 0; ix < NX; ix++) {
    const x = r.left + mx + (r.width - 2 * mx) * ix / (NX - 1);
    const y = r.top + my + (r.height - 2 * my) * iy / (NY - 1);
    names.push(cls(document.elementFromPoint(x, y)));
  }
  const mid = names[2 * NX + 3];
  return { absent: false, n: cards.length, names: names, centre_class: mid,
           nLink: names.filter(v => v === 'link').length,
           layers: names.filter(v => v === 'layer').length,
           others: names.filter(v => v.startsWith('other:')),
           title: a ? a.textContent.replace(/\\s+/g, ' ').trim() : null,
           centre: [Math.round(r.left + r.width / 2),
                    Math.round(r.top + r.height / 2)],
           rect: {w: +r.width.toFixed(1), h: +r.height.toFixed(1)},
           vw: innerWidth, vh: innerHeight };
})()"""

CARDS_JS = """(() => Array.from(document.querySelectorAll('.sf-card--roomy')).map(c => {
  const a = c.querySelector('a.sf-card__title-link');
  return { href: a ? a.getAttribute('href') : null,
           text: a ? a.textContent.replace(/\\s+/g, ' ').trim() : null,
           anchors: c.querySelectorAll('a').length,
           focusables: c.querySelectorAll('a, button, input, select, textarea')
                        .length };
}))()"""

STICKY_JS = """(() => {
  const m = document.querySelector('.sf-fdetail2__media');
  const p = document.querySelector('.sf-fdetail2__params');
  if (!m) return {absent: true};
  const cs = getComputedStyle(m);
  return { absent: false, position: cs.position, top: cs.top,
           mediaTop: +m.getBoundingClientRect().top.toFixed(1),
           paramsTop: p ? +p.getBoundingClientRect().top.toFixed(1) : null,
           scrollY: Math.round(scrollY) };
})()"""

FLAVOR_JS = """(() => {
  const g = document.querySelector('[data-sf-config-group="flavor"]');
  if (!g) return {absent: true};
  const radios = Array.from(g.querySelectorAll('input[type=radio]'));
  const boxes = Array.from(g.querySelectorAll('input[type=checkbox]'));
  const cust = g.querySelector('[data-sf-config-custom-for="flavor"]');
  const inp = g.querySelector('[data-sf-config-custom-input="flavor"]');
  const sum = document.querySelector('[data-sf-config-summary]');
  return { absent: false, name: radios.length ? radios[0].name : null,
           radios: radios.length, checkboxes: boxes.length,
           values: radios.map(r => r.value),
           checked: radios.filter(r => r.checked).map(r => r.value),
           custom_hidden_attr: cust ? cust.hasAttribute('hidden') : null,
           custom_painted: cust ? (cust.offsetParent !== null) : null,
           input_value: inp ? inp.value : null,
           summary: sum ? sum.textContent.replace(/\\s+/g, ' ').trim() : null };
})()"""

FOLD_JS = """(() => {
  const list = document.querySelector('.sf-fdetail-config__list');
  const fold = document.querySelector('.sf-fdetail-config__fold');
  if (!list || !fold) return {absent: !list ? 'list' : 'fold'};
  const groups = Array.from(list.querySelectorAll('.sf-fdetail-config__group'));
  return { absent: false,
           folded_class: list.classList.contains('sf-config-folded'),
           fold_text: fold.textContent.trim(),
           aria_expanded: fold.getAttribute('aria-expanded'),
           fold_painted: fold.offsetParent !== null,
           groups: groups.length,
           painted: groups.filter(g => getComputedStyle(g).display !== 'none').length,
           hidden: groups.filter(g => getComputedStyle(g).display === 'none').length,
           labels: groups.map(g => {const l = g.querySelector('.sf-fdetail-config__label');
                                    return l ? l.textContent.trim() : '?';}) };
})()"""

THUMBS_JS = """(() => {
  const t = document.querySelector('.sf-gallery__thumbs');
  if (!t) return {absent: true};
  const cs = getComputedStyle(t);
  return { absent: false, overflow_x: cs.overflowX, snap: cs.scrollSnapType,
           scrollWidth: t.scrollWidth, clientWidth: t.clientWidth,
           swipeable: t.scrollWidth > t.clientWidth + 8,
           tiles: t.querySelectorAll('.sf-gallery__thumb').length };
})()"""

DOTS_JS = """(() => {
  const strip = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const dots = document.querySelector('.sf-fdetail2__media .sf-gallery__dots');
  const btns = dots ? Array.from(dots.querySelectorAll('.sf-gallery__dot')) : [];
  return { strip_display: strip ? getComputedStyle(strip).display : null,
           dots_display: dots ? getComputedStyle(dots).display : null,
           dots: btns.length }; })()"""

SLIDES_JS = """(() => Array.from(document.querySelectorAll('.sf-gallery__slide'))
  .map(x => ({ id: x.id, off: x.classList.contains('sf-gallery__slide--off'),
               hidden: x.getAttribute('aria-hidden') })))()"""

VIS_JS = """(() => {
  const all = Array.from(document.querySelectorAll('.sf-gallery__slide'));
  return { showing: all.filter(x => !x.classList.contains('sf-gallery__slide--off'))
                         .map(x => x.id),
           photos: all.filter(x => !x.classList.contains('sf-gallery__slide--video'))
                      .map(x => x.id) }; })()"""

GROUPS_JS = """(() => {
  const groups = Array.from(document.querySelectorAll('.sf-fdetail-config__group'));
  return { labels: groups.map(g => {const l = g.querySelector('.sf-fdetail-config__label');
                                    return l ? l.textContent.trim() : '?';}),
           keys: groups.map(g => g.getAttribute('data-sf-config-group')),
           options: Object.fromEntries(groups.map(g => [
             g.getAttribute('data-sf-config-group'),
             Array.from(g.querySelectorAll('input[type=radio]')).map(i => i.value)])) };
})()"""

PAGE_JS = """(() => {
  const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : null;
  const q = s => Array.from(document.querySelectorAll(s));
  const ld = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
    .map(s => { try { return JSON.parse(s.textContent); } catch (e) { return null; } })
    .filter(Boolean);
  const svc = ld.find(b => b['@type'] === 'Service');
  const bc = ld.find(b => b['@type'] === 'BreadcrumbList');
  const faq = ld.find(b => b['@type'] === 'FAQPage');
  return { path: location.pathname, title: document.title,
           h1: t(document.querySelector('h1')),
           h2: q('h2').map(t),
           d3: !!document.querySelector('.sf-breadcrumb--d3'),
           crumb_current: t(document.querySelector('.sf-breadcrumb__crumb--current')),
           terms: q('table.sf-keyfacts tr').length,
           faq: q('details.sf-faq__item').length,
           rail: q('nav.sf-toc .sf-toc__label').map(t),
           rail_targets: q('.sf-toc-target').length,
           service: svc ? svc.name : null,
           faq_q: faq ? (faq.mainEntity || []).map(x => x.name) : null,
           bc_last: bc ? ((bc.itemListElement || []).slice(-1)[0] || {}).name : null,
           overflow: document.documentElement.scrollWidth - innerWidth };
})()"""


def shot(name, selector, pad=10):
    """Full-page capture cropped by the element's ABSOLUTE page rect."""
    r = ev("""(() => { const e = document.querySelector(%s); if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()"""
           % json.dumps(selector))
    if not r:
        FRAMES.append((name, 0, 0, 0, False))
        print("FAIL %-34s no element %s" % (name, selector))
        return False
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        FRAMES.append((name, 0, 0, 0, False))
        print("FAIL %-34s the capture wrote nothing" % name)
        return False
    img = Image.open(full)
    sx = img.width / float(r["docW"] or 1)
    sy = img.height / float(r["docH"] or 1)
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pad) * sy)),
           min(img.width, int((r["x"] + r["w"] + pad) * sx)),
           min(img.height, int((r["y"] + r["h"] + pad) * sy)))
    return save(name, img.crop(box))


def save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    ok = len(cols) >= 9
    crop.save(os.path.join(OUT, name + ".png"))
    FRAMES.append((name, crop.width, crop.height, len(cols), ok))
    print("%s %-34s %4dx%-4d colours=%d" % ("ok  " if ok else "FLAT", name,
                                            crop.width, crop.height, len(cols)))
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    session()

    # ==================================================== 1. /services/ cards
    print("\n===== /services/ @1440 — the four cards are the links =====")
    at(OVERVIEW, 1440)
    got = serve()
    check("the overview is served by the live theme at %s" % EXPECT_VER,
          got and got.get("dir") == "sinofresh-theme"
          and got.get("ver") == EXPECT_VER, got)
    prescroll()

    cards = ev(CARDS_JS)
    check("/services/ draws four cards, each with one anchor",
          isinstance(cards, list) and len(cards) == 4
          and all(c.get("href") and c.get("anchors") == 1 for c in cards),
          cards)
    check("...and each heading links to its own route, in order",
          isinstance(cards, list)
          and [c["href"] for c in cards] == [r[0] for r in ROUTES]
          and [c["text"] for c in cards] == [r[2] for r in ROUTES],
          [c.get("href") for c in cards] if isinstance(cards, list) else cards)
    shot("live-services-cards-1440", CARD)

    for i in range(4):
        g = ev(GRID_JS.replace("__I__", str(i)))
        if not isinstance(g, dict) or g.get("absent"):
            check("card %d: the hit test ran" % (i + 1), False, g)
            continue
        check("card %d: its own centre is the link" % (i + 1),
              g.get("centre_class") == "link",
              {"centre": g.get("centre_class"), "grid": g.get("names")})
        check("card %d: every point inside is the link or a site fixed layer"
              % (i + 1),
              not g.get("others") and g.get("nLink", 0) >= 0.6 * 35,
              {"link": g.get("nLink"), "of 35": True, "layers": g.get("layers"),
               "unattributable": g.get("others")})

    for i, (path, h1, card) in enumerate(ROUTES):
        h = ev(GRID_JS.replace("__I__", str(i)))
        if not isinstance(h, dict) or not h.get("centre"):
            check("card %d: could be scrolled to" % (i + 1), False, h)
            continue
        x, y = h["centre"][0], h["centre"][1]
        where = ev("""(() => { const c = document.querySelectorAll('.sf-card--roomy')[__I__];
          const a = c.querySelector('a.sf-card__title-link'); const r = c.getBoundingClientRect();
          const x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
          return {x: x, y: y, onlink: document.elementFromPoint(x, y) === a}; })()"""
                     .replace("__I__", str(i)))
        if not (isinstance(where, dict) and where.get("onlink")):
            check("card %d: the point to click is on the link" % (i + 1),
                  False, where)
            continue
        ab("mouse", "move", str(int(where["x"])), str(int(where["y"])))
        time.sleep(0.35)
        again = ev("""(() => { const c = document.querySelectorAll('.sf-card--roomy')[__I__];
          const a = c.querySelector('a.sf-card__title-link'); const r = c.getBoundingClientRect();
          return document.elementFromPoint(Math.round(r.left + r.width / 2),
                   Math.round(r.top + r.height / 2)) === a; })()"""
                   .replace("__I__", str(i)))
        if not again:
            check("card %d: still on the link after the move" % (i + 1), False, {})
            continue
        ab("mouse", "down", "left")
        time.sleep(0.15)
        ab("mouse", "up", "left")
        time.sleep(2.0)
        wait_ready()
        landed = ev("JSON.stringify({p: location.pathname, t: document.title})")
        check("clicking the MIDDLE of card %d lands on %s" % (i + 1, path),
              isinstance(landed, dict) and landed.get("p") == path, landed)
        if i == 0 and isinstance(landed, dict) and landed.get("p") == path:
            shot("live-card-click-landed-oem", "h1")
        at(OVERVIEW, 1440)

    # ============================================ 2. the four detail pages
    print("\n===== a detail page in full =====")
    at(OEM, 1440)
    oem = ev(PAGE_JS)
    check("%s renders as its own page" % OEM,
          isinstance(oem, dict) and oem.get("h1") == ROUTES[0][1]
          and oem.get("d3") and oem.get("terms") == 6 and oem.get("faq") == 3,
          {"h1": (oem or {}).get("h1"), "d3": (oem or {}).get("d3"),
           "terms rows": (oem or {}).get("terms"),
           "faq": (oem or {}).get("faq")})
    check("...its rail lists its own five sections, built by script",
          isinstance(oem, dict) and len(oem.get("rail") or []) == 5
          and oem.get("rail_targets") == 5
          and oem.get("rail") == oem.get("h2"),
          {"rail": (oem or {}).get("rail"), "h2": (oem or {}).get("h2")})
    check("...and its Service node names it",
          isinstance(oem, dict) and oem.get("service") == ROUTES[0][1],
          {"service": (oem or {}).get("service"),
           "breadcrumb": (oem or {}).get("bc_last")})
    check("...with no horizontal overflow at 1440", (oem or {}).get("overflow") == 0,
          {"overflow": (oem or {}).get("overflow")})
    shot("live-oem-top-1440", "h1")

    # ============================================ 3. sticky main image
    print("\n===== the main image keeps the reader's place =====")
    at(CHEWS, 1440)
    prescroll()
    a = ev(STICKY_JS)
    ab("eval", "window.scrollTo(0, 900)")
    time.sleep(1.0)
    b = ev(STICKY_JS)
    check("the media column is a sticky element with top: 100px",
          isinstance(a, dict) and a.get("position") == "sticky"
          and a.get("top") == "100px", a)
    check("...and after scrolling 900px it is still 100px from the top",
          isinstance(b, dict) and b.get("scrollY") == 900
          and b.get("mediaTop") is not None and 95 <= b["mediaTop"] <= 105,
          b)
    check("...while the parameters column has scrolled away by ~800px",
          isinstance(a, dict) and isinstance(b, dict)
          and a.get("paramsTop") is not None and b.get("paramsTop") is not None
          and (a["paramsTop"] - b["paramsTop"]) > 700,
          {"paramsTop before": (a or {}).get("paramsTop"),
           "after": (b or {}).get("paramsTop")})
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(0.8)
    shot("live-sticky-before-1440", ".sf-fdetail2__inner", pad=6)
    ab("eval", "window.scrollTo(0, 900)")
    time.sleep(1.0)
    shot("live-sticky-after-1440", ".sf-fdetail2__inner", pad=6)
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(0.8)

    # ============================================ 4. flavour + custom box
    print("\n===== Flavor is one answer, with a Custom box =====")
    f = ev(FLAVOR_JS)
    check("the Flavor group offers radios only, one of them Custom",
          isinstance(f, dict) and f.get("absent") is False
          and f.get("checkboxes") == 0 and (f.get("radios") or 0) >= 2
          and (f.get("values") or [])[-1] == "Custom"
          and f.get("checked") == [] and f.get("custom_hidden_attr") is True,
          f)
    ab("eval", """document.querySelector('[data-sf-config-group="flavor"] """
       """ input[value="Beef"]').click()""")
    time.sleep(0.5)
    f2 = ev(FLAVOR_JS)
    check("...so picking one is the only answer that holds", 
          isinstance(f2, dict) and f2.get("checked") == ["Beef"]
          and len(f2.get("checked")) == 1, {"checked": (f2 or {}).get("checked")})
    ab("eval", """document.querySelector('[data-sf-config-group="flavor"] """
       """ input[value="Custom"]').click()""")
    time.sleep(0.6)
    f3 = ev(FLAVOR_JS)
    check("...and picking Custom reveals the text box", 
          isinstance(f3, dict) and f3.get("checked") == ["Custom"]
          and f3.get("custom_painted") is True
          and f3.get("custom_hidden_attr") is False,
          {"checked": (f3 or {}).get("checked"),
           "painted": (f3 or {}).get("custom_painted")})
    ab("fill", '[data-sf-config-custom-input="flavor"]', "Smoked Bacon")
    time.sleep(0.6)
    f4 = ev(FLAVOR_JS)
    check("...and what is typed in it is what the page keeps",
          isinstance(f4, dict) and f4.get("input_value") == "Smoked Bacon"
          and f4.get("checked") == ["Custom"],
          {"typed": (f4 or {}).get("input_value"),
           "checked": (f4 or {}).get("checked"),
           "summary line": (f4 or {}).get("summary")})
    shot("live-flavor-custom-1440", ".sf-fdetail-config", pad=6)

    # ============================================ 5. shelf life from the pool
    print("\n===== shelf life comes from the record, not the specs text =====")
    shelf = ev("""(() => {
      const rows = Array.from(document.querySelectorAll('.sf-fdetail-specs__row'));
      const hit = rows.find(r => {
        const t = r.querySelector('.sf-fdetail-specs__term');
        return t && t.textContent.trim() === 'Shelf Life'; });
      const v = hit ? hit.querySelector('.sf-fdetail-specs__value') : null;
      const specs = (document.body.textContent.match(/18 months shelf life/g) || []).length;
      return { absent: !hit, value: v ? v.textContent.trim() : null,
               specs_copies: specs }; })()""")
    check("the specs sheet prints 24 months while the specs text says 18",
          isinstance(shelf, dict) and shelf.get("value") == "24 months"
          and shelf.get("specs_copies", 0) > 0,
          {"Shelf Life row prints": (shelf or {}).get("value"),
           "copies of '18 months shelf life'": (shelf or {}).get("specs_copies"),
           "so 24 can only have come from the record's pool": True})
    shot("live-shelf-life-1440", ".sf-fdetail-specs", pad=6)

    # ============================================ 6. the phone: fold + strip
    print("\n===== @375 — the fold and the swipeable strip =====")
    at(CHEWS, 375, 812)
    # The expanded state is remembered for the session, so clear it first:
    # otherwise a page whose visitor unfolded earlier would never look folded
    # and this check would be reading the visitor's choice, not the default.
    ev("sessionStorage.clear()")
    at(CHEWS, 375, 812)
    prescroll()
    fo = ev(FOLD_JS)
    check("the configurator starts folded, keeping four groups in view",
          isinstance(fo, dict) and fo.get("folded_class") is True
          and fo.get("painted") == 4 and fo.get("hidden") == 2,
          {"painted": (fo or {}).get("painted"), "hidden": (fo or {}).get("hidden"),
           "labels": (fo or {}).get("labels")})
    check("...and the fold button is drawn, closed",
          isinstance(fo, dict) and fo.get("fold_painted") is True
          and fo.get("aria_expanded") == "false",
          {"text": (fo or {}).get("fold_text"),
           "aria-expanded": (fo or {}).get("aria_expanded")})
    ab("scrollintoview", FOLD)
    time.sleep(0.5)
    ab("click", FOLD)
    time.sleep(0.8)
    fo2 = ev(FOLD_JS)
    check("...and pressing it shows every group",
          isinstance(fo2, dict) and fo2.get("folded_class") is False
          and fo2.get("hidden") == 0 and fo2.get("painted") == fo2.get("groups")
          and fo2.get("aria_expanded") == "true",
          {"painted": (fo2 or {}).get("painted"),
           "text": (fo2 or {}).get("fold_text")})
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(0.8)
    shot("live-fold-expanded-375", ".sf-fdetail-config", pad=6)
    ab("scrollintoview", FOLD)
    time.sleep(0.5)
    ab("click", FOLD)
    time.sleep(0.8)
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(0.8)
    shot("live-fold-collapsed-375", ".sf-fdetail-config", pad=6)

    # The strip is a row at 481-768 and a scroll box wherever it is a row; at
    # <=480 the theme hides it on purpose and hands the phone to the dots, so
    # measuring the scroll box at 375 would be measuring `display: none` — a
    # green check or a red one, either way about the wrong element.
    at(CHEWS, 600, 900)
    th = ev(THUMBS_JS)
    moved = ev("""(() => { const t = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
      if (!t) return null; const before = t.scrollLeft;
      t.scrollLeft = t.scrollWidth; const after = t.scrollLeft;
      t.scrollLeft = before; return {before: before, after: after}; })()""")
    # What is asserted is the CAPABILITY, not that this page needed it: every
    # formula record on the site carries four photos today, and four 84px tiles
    # plus gaps come to 372px inside a 524px column — so the strip is a scroll
    # box that does not have to scroll yet. The stylesheet's own comment says
    # the overflow it was built for starts at six frames. Asserting "it
    # overflows" would therefore be asserting something about the data, and it
    # would go red on a correct site.
    check("where the strip is a row it is a snap-scrolling box",
          isinstance(th, dict) and th.get("overflow_x") == "auto"
          and "x mandatory" in (th.get("snap") or ""),
          {"overflow-x": (th or {}).get("overflow_x"),
           "scroll-snap-type": (th or {}).get("snap"),
           "tiles": (th or {}).get("tiles"),
           "scrollWidth/clientWidth": [(th or {}).get("scrollWidth"),
                                       (th or {}).get("clientWidth")],
           "note": "4 photos do not fill the box, so it does not overflow today",
           "scrollLeft max reachable": (moved or {}).get("after")})
    shot("live-thumbs-scroll-600", ".sf-gallery", pad=6)

    at(CHEWS, 375, 812)
    d0 = ev(DOTS_JS)
    check("on the phone the strip gives way to dots, as the phone pass intends",
          isinstance(d0, dict) and d0.get("strip_display") == "none"
          and d0.get("dots_display") == "flex" and (d0.get("dots") or 0) >= 4,
          d0)
    # The dot's own `aria-controls` names the frame it must open. Comparing
    # positions instead would compare an index into the PHOTOS with an index
    # into the SLIDES — and a record whose first frame is the video makes those
    # two lists disagree by one, which is exactly what the first run of this
    # check reported as a failure.
    dot = ev("""(() => { const d = document.querySelectorAll(
      '.sf-fdetail2__media .sf-gallery__dots .sf-gallery__dot')[1];
      return d ? d.getAttribute('aria-controls') : null; })()""")
    ev("""(() => { const d = document.querySelectorAll(
      '.sf-fdetail2__media .sf-gallery__dots .sf-gallery__dot')[1];
      if (d) d.click(); return !!d; })()""")
    time.sleep(0.8)
    d1 = ev(SLIDES_JS)
    showing = [x["id"] for x in (d1 or []) if not x.get("off")]
    check("...and a dot opens the frame it names",
          isinstance(dot, str) and showing == [dot] and len(d1 or []) == 5,
          {"dot aria-controls": dot, "showing": showing,
           "all frames": [x.get("id") for x in (d1 or [])]})
    shot("live-phone-dots-375", ".sf-gallery", pad=6)

    # ---- and the swipe itself -------------------------------------------
    # Driven by a SYNTHESISED pointer sequence, and named that way, because the
    # browser tooling cannot hold a button across a move: `mouse down left`
    # followed by `mouse move` delivers the pointermove (buttons = 1) and then
    # drops the `mouse up` entirely — no pointerup reaches the page, or even the
    # document. Measured, three variants, all dropped. The handler's own logic is
    # what matters here (a 40px floor, an axis lock, and a direction), and a
    # synthesised sequence exercises all three; what it does not prove is the
    # browser's event synthesis, which is not this site's code either way.
    vis = ev(VIS_JS)
    ev("""(() => { const e = document.querySelector('.sf-gallery__stage');
      if (e) e.scrollIntoView({block: 'center'}); return !!e; })()""")
    time.sleep(0.9)
    sw = ev("""(() => {
      const s = document.querySelector('.sf-gallery__stage');
      if (!s) return {absent: true};
      const r = s.getBoundingClientRect();
      const x0 = Math.round(r.left + r.width / 2);
      const y = Math.round(r.top + r.height / 2);
      const x1 = x0 - 90;
      const mk = (t, x, buttons, button) => new PointerEvent(t, {
        bubbles: true, cancelable: true, composed: true, pointerId: 1,
        pointerType: 'mouse', isPrimary: true, clientX: x, clientY: y,
        buttons: buttons, button: button });
      s.dispatchEvent(mk('pointerdown', x0, 1, 0));
      s.dispatchEvent(mk('pointermove', x1, 1, -1));
      s.dispatchEvent(mk('pointerup', x1, 0, 0));
      return {x0: x0, x1: x1, y: y, moved: x0 - x1}; })()""")
    time.sleep(0.9)
    after = ev(VIS_JS)
    photos = (after or {}).get("photos") or []
    before_id = (vis or {}).get("showing") or []
    want = None
    if before_id and before_id[0] in photos:
        want = photos[(photos.index(before_id[0]) + 1) % len(photos)]
    check("a 90px left drag across the stage turns to the next photo "
          "(synthesised pointer sequence)", 
          want is not None and (after or {}).get("showing") == [want],
          {"before": before_id, "after": (after or {}).get("showing"),
           "wanted": want, "photos": photos, "drag": sw})
    shot("live-swipe-after-375", ".sf-gallery", pad=6)

    # and the floor is real: a drag under the 40px threshold must NOT turn it.
    keep = (after or {}).get("showing")
    ev("""(() => {
      const s = document.querySelector('.sf-gallery__stage');
      const r = s.getBoundingClientRect();
      const x0 = Math.round(r.left + r.width / 2);
      const y = Math.round(r.top + r.height / 2);
      const mk = (t, x, buttons, button) => new PointerEvent(t, {
        bubbles: true, cancelable: true, composed: true, pointerId: 1,
        pointerType: 'mouse', isPrimary: true, clientX: x, clientY: y,
        buttons: buttons, button: button });
      s.dispatchEvent(mk('pointerdown', x0, 1, 0));
      s.dispatchEvent(mk('pointermove', x0 - 20, 1, -1));
      s.dispatchEvent(mk('pointerup', x0 - 20, 0, 0));
      return 1; })()""")
    time.sleep(0.8)
    short = ev(VIS_JS)
    check("...while a 20px drag is treated as a mis-tap and changes nothing",
          (short or {}).get("showing") == keep,
          {"before": keep, "after": (short or {}).get("showing")})

    # ============================================ 7. the dosage-form split
    print("\n===== the pool follows the dosage form =====")
    at(POWDER, 1440)
    prescroll()
    pg = ev(GROUPS_JS)
    check("the powder page has no group called Shape",
          isinstance(pg, dict) and "Shape" not in (pg.get("labels") or [])
          and "Appearance" in (pg.get("labels") or []),
          {"labels": (pg or {}).get("labels")})
    check("...its appearance answers come from the powder pool",
          isinstance(pg, dict)
          and all(x in (pg.get("options", {}).get("shape") or [])
                  for x in ("Fine Powder", "Granules", "Microencapsulated"))
          and not ({"Bone", "Paw"} & set(pg.get("options", {}).get("shape") or [])),
          {"shape options": (pg or {}).get("options", {}).get("shape")})
    check("...and Container Type is a packaging format",
          isinstance(pg, dict)
          and all(x in (pg.get("options", {}).get("container") or [])
                  for x in ("Jar", "Foil Pouch", "Stand-up Pouch")),
          {"container options": (pg or {}).get("options", {}).get("container")})
    shot("live-powder-appearance-1440", ".sf-fdetail-config", pad=6)

    at(POWDER, 375, 812)
    prescroll()
    mo = ev("""(() => ({overflow: document.documentElement.scrollWidth - innerWidth,
                        vw: innerWidth}))()""")
    check("the powder page does not overflow the phone viewport",
          isinstance(mo, dict) and mo.get("overflow") == 0, mo)

    ab("close", "--all")
    ok = all(r["ok"] for r in ROWS)
    flat = [f for f in FRAMES if not f[4]]
    print("\n%s  browser acceptance: %d/%d checks, %d frames (%d flat)"
          % ("PASS" if ok and not flat else "FAIL",
             sum(1 for r in ROWS if r["ok"]), len(ROWS), len(FRAMES), len(flat)))
    for r in ROWS:
        if not r["ok"]:
            print("   FAILED  %s  %s" % (r["label"], json.dumps(r["detail"])[:180]))
    for f in flat:
        print("   FLAT    %s" % f[0])
    json.dump({"rows": ROWS, "frames": [
        {"name": n, "w": w, "h": h, "colours": c, "ok": o}
        for n, w, h, c, o in FRAMES]},
        open("_backup/h8c-live-accept.json", "w"), ensure_ascii=False, indent=1)
    return 0 if (ok and not flat) else 1


if __name__ == "__main__":
    sys.exit(main())
