#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8c E2E — the four cooperation models, driven in a real browser.

Target: the PREFLIGHT copy (2.10.76). Dev still serves 2.10.73 for this batch
(the pull is a separate, user-authorised step), so the candidate exists on the
box only as `sinofresh-theme-preflight`, behind the `X-SF-Preflight: 1` header.

`--live` drops the header and drives dev's own 2.10.73. The four pages exist in
the shared database either way, so on live the four ROUTES resolve — and render
the theme's generic fallback, because the live theme has neither the four
templates nor the two mechanisms. That is the shape of the live run: the routes
answer 200 and carry none of the payload. Every model claim must be RED there,
and the four overview cards must not be links. That is the run that proves this
script can fail.

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the one
`set headers` call. Note that `open` clears custom headers, so every `open_at`
re-sets them.

What only a browser can decide
------------------------------
The gate proves the four routes carry the right BYTES. Two of this batch's
claims are not about bytes at all:

  the whole card is the link   The card's <a> sits inside the <h3> and is about
                               as wide as its own text. It covers the card only
                               through `.sf-card__title-link::after{inset:0}`.
                               A capture cannot see a pseudo-element, so this is
                               asserted the only way that means anything: a hit
                               test at five points inside the card, and then a
                               REAL mouse click at the card's centre — not at
                               the link's own centre, which would pass whether
                               or not the overlay exists.

  the rail is built per page   The four slugs had to be added to toc-nav's
                               whitelist. The gate can only see that the script
                               is enqueued; whether it built a rail, and how many
                               stops it has, needs the script to have run.

Every expected value here is transcribed from the templates by hand and is
deliberately NOT imported from the gate: a script that reads its expectations
out of the gate agrees with any mistake the gate made, and the whole point of
the pair is that they are two separate readings of the same product.
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

PRE_VER = "2.10.76"
LIVE_VER = "2.10.73"

OVERVIEW = "/services/"

# path, breadcrumb's current crumb, the page's own h1, the overview card's <h3>.
# In the order the four cards are drawn — that order is itself a claim (no card
# may be pointed at a neighbour's page while all four hrefs are still present),
# and it is asserted against the card wall rather than assumed.
MODELS = [
    ("/services/oem/", "OEM Manufacturing",
     "OEM Manufacturing \u2014 You Bring the Formula",
     "OEM \u2014 You Bring the Formula"),
    ("/services/odm/", "ODM Development",
     "ODM Development \u2014 We Develop From Your Idea",
     "ODM \u2014 We Develop From Your Idea"),
    ("/services/contract-manufacturing/", "Contract Manufacturing",
     "Contract Manufacturing \u2014 You Own the IP",
     "Contract Manufacturing \u2014 You Own the IP"),
    ("/services/private-label/", "Private Label",
     "Private Label \u2014 Pick From Our Proven Formulas",
     "Private Label \u2014 Pick From Our Proven Formulas"),
]

# The commercial-terms rows the four detail pages repeat from the overview.
# Read off the RENDERED page by hand, not off the gate: the table has a
# header row plus these five, and a claim written as "eight rows" (which is what
# the briefing note said) would be green on nothing.
TERMS = ["MOQ", "Sampling", "Lead Time", "Payment", "Trade Terms"]

RESULTS = []
CURRENT = {"live": False, "ready": True}


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
          + ("  | " + str(detail)[:340] if detail else ""))


def session(live=False):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE if live else PF)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def wait_ready(tries=25):
    """A page that has NAVIGATED is not a page that has LOADED.

    `open` and `reload` both return before the document is parsed, and a run
    that reads too early sees `document.title === ''` with an empty <head>, no
    stylesheet and `h1 === 0` — which reads as "the theme is not there" and is
    indistinguishable from a broken deployment. The gate is about readiness and
    not about content, so it also requires a title and at least one stylesheet:
    it must not be able to pass by accident on a 401 page.
    """
    for _ in range(tries):
        st = ev("JSON.stringify({rs: document.readyState, t: document.title,"
                " n: document.querySelectorAll('link[rel=stylesheet]').length})")
        if (isinstance(st, dict) and st.get("rs") == "complete"
                and st.get("n", 0) > 0 and st.get("t")):
            CURRENT["ready"] = True
            return True
        time.sleep(0.8)
    CURRENT["ready"] = False
    return False


def open_at(path, w=1440, h=1000):
    """Navigate and re-assert the custom header. `open` drops it (measured), so
    anything that navigates after the session was set up must come through
    here — otherwise the run silently drives the 401 page and reads all zeroes,
    which looks exactly like a broken selector."""
    ab("open", BASE + path)
    time.sleep(1.6)
    ab("set", "headers", LIVE if CURRENT["live"] else PF)
    time.sleep(0.4)
    ab("reload")
    wait_ready()
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth})")
        if isinstance(got, dict) and got.get("w") == w:
            return
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def served(path, why, live=False):
    """Which artifact answered, asserted BEFORE anything is asserted about it."""
    want = LIVE_VER if live else PRE_VER
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, title: document.title, theme,
               pre: theme.includes('-preflight'),
               ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               h1: document.querySelectorAll('h1').length };
    })()""")
    ok = (isinstance(s, dict) and s.get("ver") == want and s.get("pre") is (not live)
          and CURRENT.get("ready") is not False)
    check("the %s theme answered (%s)  [%s]" % (want, path, why), ok,
          dict(s, ready=CURRENT.get("ready")) if isinstance(s, dict) else s)
    return s


# ------------------------------------------------------------------ probes

CARD_JS = """(() => {
  const cards = Array.from(document.querySelectorAll('.sf-card--roomy'));
  return cards.map((c, i) => {
    const a = c.querySelector('a.sf-card__title-link');
    const h3 = c.querySelector('h3');
    const r = c.getBoundingClientRect();
    const af = a ? getComputedStyle(a, '::after') : null;
    return {
      i,
      title: h3 ? h3.textContent.replace(/\\s+/g, ' ').trim() : null,
      href: a ? a.getAttribute('href') : null,
      linkText: a ? a.textContent.replace(/\\s+/g, ' ').trim() : null,
      linksInCard: c.querySelectorAll('a[href]').length,
      focusable: c.querySelectorAll('a[href],button,input,select,textarea,[tabindex]').length,
      after: af ? {position: af.position, top: af.top, left: af.left,
                   right: af.right, bottom: af.bottom, z: af.zIndex} : null,
      // The ::after overlay is only actionable if its own stacking context is
      // above the card's other content; a capture shows neither.
      covers: af ? (af.position === 'absolute' && af.top === '0px'
                    && af.left === '0px') : null,
      box: {x: +r.x.toFixed(1), y: +r.y.toFixed(1),
            w: +r.width.toFixed(1), h: +r.height.toFixed(1)},
      n: cards.length,
    };
  });
})()"""

# A 7x5 grid inside the card, inset 6% from each edge, each point classified by
# what `elementFromPoint` answers. The corners themselves are left out because a
# card with a border radius clips its own corner pixels and a corner test would
# report a radius as a hole.
#
# Three classifications, not two, because on a phone the site's own fixed
# overlays hang over the lower part of whatever is scrolled under them: the
# floating action buttons, and the cookie banner while it is still up. Both are
# real occlusions of the card — and neither is this batch's, and neither is the
# link failing to cover the card. Collapsing them into "not the link" would
# either fail the batch for something it did not do, or (if the test only looked
# at the centre) hide a real overlap behind a green line. So every non-link
# point has to be attributable, and 'other:' is the name for a point that is
# not — that is the reading that would catch a stray element stealing the tap.
HIT_JS = """(() => {
  const cards = Array.from(document.querySelectorAll('.sf-card--roomy'));
  const c = cards[%d];
  if (!c) return {absent: true, n: cards.length};
  c.scrollIntoView({block: 'center'});
  const r = c.getBoundingClientRect();
  const a = c.querySelector('a.sf-card__title-link');
  const cls = e => {
    if (!e) return 'none';
    if (e === a || (a && (a.contains(e) || e.contains(a)))) return 'link';
    if (e.closest && e.closest('.sf-float, .sf-float-stack, [class*="sf-float-btn"]')) return 'float';
    if (e.closest && e.closest('.sf-cookie-banner')) return 'cookie';
    return 'other:' + e.tagName + '.' + String(e.className || '').slice(0, 40);
  };
  const NX = 7, NY = 5, mx = r.width * 0.06, my = r.height * 0.06;
  const grid = [], names = [];
  for (let iy = 0; iy < NY; iy++) {
    for (let ix = 0; ix < NX; ix++) {
      const x = r.left + mx + (r.width - 2 * mx) * ix / (NX - 1);
      const y = r.top + my + (r.height - 2 * my) * iy / (NY - 1);
      grid.push([x, y]);
      names.push(cls(document.elementFromPoint(x, y)));
    }
  }
  return {absent: false, n: cards.length, names,
          nLink: names.filter(v => v === 'link').length, total: NX * NY,
          others: names.filter(v => v.indexOf('other:') === 0),
          floats: names.filter(v => v === 'float').length,
          cookies: names.filter(v => v === 'cookie').length,
          centre: [Math.round(r.left + r.width / 2),
                   Math.round(r.top + r.height / 2)],
          rect: {x: +r.x.toFixed(1), y: +r.y.toFixed(1),
                 w: +r.width.toFixed(1), h: +r.height.toFixed(1)},
          vw: innerWidth, vh: innerHeight};
})()"""

HIT_ONE = """(() => {
  const c = Array.from(document.querySelectorAll('.sf-card--roomy'))[%d];
  const a = c ? c.querySelector('a.sf-card__title-link') : null;
  const r = c ? c.getBoundingClientRect() : null;
  const x = r ? Math.round(r.left + r.width / 2) : -1;
  const y = r ? Math.round(r.top + r.height / 2) : -1;
  const e = document.elementFromPoint(x, y);
  return {x, y, onLink: e === a,
          got: e ? (e.tagName + '.' + String(e.className || '')).slice(0, 48) : 'none'};
})()"""

PAGE_JS = """(() => {
  const q = s => Array.from(document.querySelectorAll(s));
  const t = e => (e ? e.textContent.replace(/\\s+/g, ' ').trim() : null);
  const crumb = document.querySelector('.sf-breadcrumb');
  const cur = document.querySelector('.sf-breadcrumb__current');
  const table = document.querySelector('table.sf-keyfacts');
  const rows = table ? q('tr', table).length : 0;
  const terms = table ? Array.from(table.querySelectorAll('tr td:first-child'))
                          .map(x => x.textContent.trim()) : [];
  const ld = q('script[type="application/ld+json"]').map(s => {
    try { return JSON.parse(s.textContent); } catch (e) { return {bad: true}; }
  });
  const flat = [];
  ld.forEach(b => Array.isArray(b) ? b.forEach(x => flat.push(x))
                                   : flat.push(b));
  const svc = flat.find(b => b && b['@type'] === 'Service');
  const faq = flat.find(b => b && b['@type'] === 'FAQPage');
  const bc = flat.find(b => b && b['@type'] === 'BreadcrumbList');
  // `.sf-faq__item`, not `details`: the footer carries a <details> of its own
  // (`sf-footcol`), so a bare `details` count would read four and the FAQ claim
  // would be measuring the footer.
  const de = q('details.sf-faq__item');
  return {
    title: document.title,
    h1: q('h1').map(t),
    h2: q('h2').map(t),
    crumbLevels: crumb ? crumb.querySelectorAll('.sf-breadcrumb__crumb').length : 0,
    crumbCurrent: t(cur),
    crumbMid: (() => { const m = document.querySelector('.sf-breadcrumb__crumb--mid');
                       return m ? {text: t(m), href: m.getAttribute('href')} : null; })(),
    d3: !!document.querySelector('.sf-breadcrumb--d3'),
    d2: !!document.querySelector('.sf-breadcrumb--d2'),
    keyfacts: !!table, rowCount: rows, terms,
    faqN: de.length,
    faqOpen: de.filter(x => x.hasAttribute('open')).length,
    faqSummary: q('details.sf-faq__item > summary').length,
    faqOther: q('details:not(.sf-faq__item)').length,
    service: svc ? svc.name : null,
    faqQ: faq ? (faq.mainEntity || []).map(x => x.name) : null,
    bcLevels: bc ? (bc.itemListElement || []).length : 0,
    bcLast: bc ? ((bc.itemListElement || [])[2] || {}).name : null,
    rail: document.querySelectorAll('nav.sf-toc li').length,
    railItems: q('nav.sf-toc .sf-toc__label').map(t),
    railTargets: document.querySelectorAll('.sf-toc-target').length,
    railHidden: (() => { const n = document.querySelector('nav.sf-toc');
                         return n ? n.classList.contains('sf-toc--hidden') : null; })(),
    tocScript: !!Array.from(document.querySelectorAll('script[src]'))
                   .find(s => s.src.includes('toc-nav.js')),
    // A page wider than its viewport is the classic symptom of a band that
    // escaped the gutter. clientWidth and not innerWidth: innerWidth counts the
    // scrollbar, which makes the difference read as a fraction of a pixel off.
    overflow: document.documentElement.scrollWidth
              - document.documentElement.clientWidth,
    vw: innerWidth, vh: innerHeight,
    path: location.pathname,
  };
})()"""


# ------------------------------------------------------------------ the run

def run(live=False):
    CURRENT["live"] = live
    print("=" * 78)
    print("batch H8c E2E  --  %s" % ("LIVE 2.10.73" if live else "PREFLIGHT 2.10.76"))
    print("=" * 78)

    session(live)

    # ------------------------------------------- the overview's card wall
    print("\n===== 1440x1000 — the overview, where the four cards are =====")
    open_at(OVERVIEW)
    served(OVERVIEW, "the overview, unchanged by this batch", live)
    cards = ev(CARD_JS)

    check("the overview draws exactly the four cooperation cards",
          isinstance(cards, list) and len(cards) == 4,
          {"n": len(cards) if isinstance(cards, list) else cards})
    if not isinstance(cards, list) or len(cards) != 4:
        print("  (the card wall is not the expected shape; later card claims "
              "are reported against what is there)")
        cards = cards if isinstance(cards, list) else []

    # The overview's own body, before anything the batch touched: the four pages
    # repeat this table, so the page it is repeated FROM has to still be itself
    # on both sides of the pull.
    op = ev(PAGE_JS)
    check("the overview is still the overview it was before the batch",
          isinstance(op, dict) and op.get("terms") == TERMS
          and op.get("d2") is True and op.get("d3") is False
          and isinstance(op.get("h2"), list) and len(op["h2"]) == 6,
          {"terms": (op or {}).get("terms"), "d2": (op or {}).get("d2"),
           "d3": (op or {}).get("d3"), "h2": (op or {}).get("h2")})

    for i, m in enumerate(MODELS):
        want_title = m[3]
        c = cards[i] if i < len(cards) else {}
        check("card %d is '%s'" % (i + 1, want_title),
              c.get("title") == want_title,
              {"got": c.get("title"), "want": want_title})
        if live:
            check("...and on live it is not a link, because the batch is not there",
                  c.get("href") is None and c.get("linksInCard") == 0,
                  {"href": c.get("href"), "linksInCard": c.get("linksInCard")})
        else:
            check("...and its heading links to its own page",
                  c.get("href") == m[0] and c.get("linkText") == want_title,
                  {"href": c.get("href"), "linkText": c.get("linkText"), "want": m[0]})
            check("...and the card carries one tab stop, not a separate link per word",
                  c.get("focusable") == 1 and c.get("linksInCard") == 1,
                  {"focusable": c.get("focusable"), "linksInCard": c.get("linksInCard")})
            check("...and the link's overlay is an absolutely placed inset-0 box",
                  c.get("covers") is True, c.get("after"))

    if not live:
        # ---------------------------------------------------- the hit test
        print("\n===== 1440x1000 — is the whole card the link? =====")
        for i, m in enumerate(MODELS):
            h = ev(HIT_JS % i)
            if not isinstance(h, dict) or h.get("absent"):
                check("card %d: the grid hit test ran" % (i + 1), False, h)
                continue
            check("card %d: all %d points inside the card hit the link"
                  % (i + 1, h.get("total")),
                  h.get("nLink") == h.get("total") and not h.get("others"),
                  {"link": h.get("nLink"), "total": h.get("total"),
                   "float": h.get("floats"), "other": h.get("others"),
                   "rect": h.get("rect"), "vw": h.get("vw")})
            check("...and the card sits fully inside the viewport it was scrolled to",
                  h.get("rect", {}).get("w", 0) > 200
                  and h.get("rect", {}).get("y", -1) >= 0
                  and h.get("rect", {}).get("y", 0)
                  + h.get("rect", {}).get("h", 0) <= h.get("vh", 0) + 1,
                  {"rect": h.get("rect"), "vh": h.get("vh")})

        # -------------------------------------------------- the real click
        # Driven through mouse move/down/up at the CARD's centre, not through
        # `click <selector>`: the selector click would aim at the <a>'s own
        # centre — the middle of the link text — and would then pass on a card
        # whose overlay was missing entirely.
        #
        # Coordinates are ROUNDED and the button is named. Measured on this box:
        # a fractional coordinate ("499.6") makes the press land at (0,0) — the
        # page header — and the click is then recorded at a point nobody asked
        # for, with no error from the tool. `mouse down` without a button also
        # works, but naming it costs nothing and removes the ambiguity.
        print("\n===== 1440x1000 — clicking the middle of each card =====")
        for i, m in enumerate(MODELS):
            h = ev(HIT_JS % i)
            if not isinstance(h, dict) or h.get("absent"):
                check("card %d: the card could be scrolled to" % (i + 1), False, h)
                continue
            v = ev(HIT_ONE % i)
            if not (isinstance(v, dict) and v.get("onLink")):
                check("card %d: the point to be clicked is on the link" % (i + 1),
                      False, v)
                continue
            ab("mouse", "move", str(v["x"]), str(v["y"]))
            time.sleep(0.3)
            again = ev(HIT_ONE % i)
            if not (isinstance(again, dict) and again.get("onLink")):
                check("card %d: the point is still on the link after the move"
                      % (i + 1), False, again)
                continue
            ab("mouse", "down", "left")
            time.sleep(0.15)
            ab("mouse", "up", "left")
            time.sleep(2.2)
            wait_ready()
            got = ev("JSON.stringify({p: location.pathname, t: document.title})")
            check("card %d: clicking its middle lands on %s" % (i + 1, m[0]),
                  isinstance(got, dict) and got.get("p") == m[0], got)
            open_at(OVERVIEW)

    # ------------------------------------------------------ the four pages
    print("\n===== 1440x1000 — the four detail pages =====")
    seen = {}
    for path, crumb, h1, _card in MODELS:
        print("\n----- %s -----" % path)
        open_at(path)
        s = served(path, "detail page: %s" % crumb, live)
        p = ev(PAGE_JS)
        if not isinstance(p, dict):
            check("%s: the page could be read" % path, False, p)
            continue

        if live:
            # On live the route resolves and the theme's generic page answers.
            check("%s: on live the route resolves but carries none of the payload"
                  % path,
                  p.get("d3") is False and p.get("keyfacts") is False
                  and p.get("service") is None and p.get("rail") == 0,
                  {"d3": p.get("d3"), "keyfacts": p.get("keyfacts"),
                   "service": p.get("service"), "rail": p.get("rail"),
                   "crumbLevels": p.get("crumbLevels")})
            seen[path] = p.get("h1")
            continue

        check("%s: the h1 is this page's own and there is exactly one" % path,
              p.get("h1") == [h1], {"got": p.get("h1"), "want": [h1]})
        check("%s: the breadcrumb has three levels and ends here" % path,
              p.get("d3") and p.get("crumbLevels") == 3
              and p.get("crumbCurrent") == crumb,
              {"levels": p.get("crumbLevels"), "current": p.get("crumbCurrent")})
        check("%s: and its middle level is the overview" % path,
              (p.get("crumbMid") or {}).get("href") == "/services/",
              p.get("crumbMid"))
        check("%s: five h2 sections, so the rail has something to point at" % path,
              len(p.get("h2") or []) == 5, {"h2": p.get("h2")})
        check("%s: three FAQ pairs, exactly the first one open" % path,
              p.get("faqN") == 3 and p.get("faqSummary") == 3
              and p.get("faqOpen") == 1,
              {"items": p.get("faqN"), "summaries": p.get("faqSummary"),
               "open": p.get("faqOpen"), "otherDetails": p.get("faqOther")})
        check("%s: the commercial-terms table, with the overview's own rows" % path,
              p.get("keyfacts") is True and p.get("terms") == TERMS,
              {"rows": p.get("rowCount"), "terms": p.get("terms")})
        # The rail lists the page's own headings: the labels ARE the h2 texts,
        # so "it built a rail" and "it built the right one" are the same reading.
        check("%s: the js-built rail lists this page's five sections, by their own "
              "words" % path,
              p.get("tocScript") and p.get("rail") == 5
              and p.get("railTargets") == 5 and p.get("railItems") == p.get("h2"),
              {"rail": p.get("rail"), "targets": p.get("railTargets"),
               "items": p.get("railItems"), "h2": p.get("h2")})
        # The rail hides itself above the fold; that it comes back is the half
        # that says the handler is bound to this page at all.
        ab("eval", "scrollTo(0, 800)")
        time.sleep(0.9)
        st = ev("JSON.stringify({h: (document.querySelector('nav.sf-toc')||{}).className,"
                " y: scrollY})")
        check("%s: ...and it un-hides itself once the page is scrolled" % path,
              isinstance(st, dict) and "sf-toc--hidden" not in (st.get("h") or ""),
              st)
        ab("eval", "scrollTo(0, 0)")
        time.sleep(0.4)
        check("%s: no band escaped the gutter" % path,
              isinstance(p.get("overflow"), int) and p.get("overflow") <= 1,
              {"scrollWidth - innerWidth": p.get("overflow"), "vw": p.get("vw")})

        check("%s: one Service node named after the h1, one three-level breadcrumb, "
              "one FAQPage" % path,
              p.get("service") == h1 and p.get("bcLevels") == 3
              and p.get("bcLast") == crumb and len(p.get("faqQ") or []) == 3,
              {"service": p.get("service"), "bcLevels": p.get("bcLevels"),
               "bcLast": p.get("bcLast"), "faqQ": p.get("faqQ")})
        seen[path] = p.get("h1")

    if not live:
        check("the four pages are four different documents, not one re-titled",
              len(set(json.dumps(v) for v in seen.values())) == 4, seen)

    # ------------------------------------------------------------- the phone
    print("\n===== 375x812 — the card wall on a phone =====")
    open_at(OVERVIEW, 375, 812)
    served(OVERVIEW, "the phone pass: the overview", live)
    oc = ev(PAGE_JS)
    check("the phone overview does not overflow sideways",
          isinstance(oc.get("overflow"), int) and oc.get("overflow") <= 1,
          {"scrollWidth - innerWidth": oc.get("overflow"), "vw": oc.get("vw")})
    cards = ev(CARD_JS)
    if not live and isinstance(cards, list) and len(cards) == 4:
        ys = [c["box"]["y"] for c in cards]
        check("the four cards stack in one column, in the documented order",
              ys == sorted(ys)
              and len(set(round(c["box"]["w"]) for c in cards)) == 1
              and cards[0]["box"]["w"] > 290,
              {"ys": ys, "widths": [c["box"]["w"] for c in cards]})
        # The card's centre is the tap target, and on a phone the site's own
        # fixed overlays hang over the lower part of whatever scrolls under
        # them. Both halves are asserted: the link owns the middle, and every
        # point inside the card that is NOT the link is one of those overlays —
        # never an unrelated element stealing the tap.
        for i, m in enumerate(MODELS):
            h = ev(HIT_JS % i)
            if not isinstance(h, dict) or h.get("absent"):
                check("phone: card %d's grid hit test ran" % (i + 1), False, h)
                continue
            check("phone: card %d's own centre is the link" % (i + 1),
                  h.get("names") and h["names"][2 * 7 + 3] == "link",
                  {"centre": h.get("names")[2 * 7 + 3] if h.get("names") else None,
                   "names": h.get("names")})
            blocked = (h.get("floats", 0) + h.get("cookies", 0))
            check("phone: card %d is the link everywhere the site's own fixed "
                  "overlays are not over it" % (i + 1),
                  not h.get("others")
                  and h.get("nLink", 0) + blocked == h.get("total", 0),
                  {"link": h.get("nLink"), "total": h.get("total"),
                   "floatButtons": h.get("floats"),
                   "cookieBanner": h.get("cookies"), "others": h.get("others")})
    elif live and isinstance(cards, list):
        check("phone: on live none of the four is a link",
              all(c.get("linksInCard") == 0 for c in cards),
              [c.get("linksInCard") for c in cards])

    print("\n===== 375x812 — a detail page on a phone =====")
    open_at(MODELS[2][0], 375, 812)
    served(MODELS[2][0], "the phone pass: the longest model name", live)
    p = ev(PAGE_JS)
    if live:
        check("phone: on live the detail page carries none of the payload",
              p.get("d3") is False and p.get("keyfacts") is False, 
              {"d3": p.get("d3"), "keyfacts": p.get("keyfacts")})
    else:
        check("phone: the h1 is the model's own and nothing is clipped off-screen",
              p.get("h1") == [MODELS[2][2]]
              and isinstance(p.get("overflow"), int) and p.get("overflow") <= 1,
              {"h1": p.get("h1"), "overflow": p.get("overflow")})
        check("phone: the terms table is still there, and still the same five rows",
              p.get("keyfacts") is True and p.get("terms") == TERMS,
              {"terms": p.get("terms")})
        check("phone: the rail is rebuilt for the phone as well",
              p.get("rail") == 5 and p.get("railTargets") == 5,
              {"rail": p.get("rail"), "targets": p.get("railTargets")})

    # --------------------------------------------------------------- summary
    bad = [r for r in RESULTS if not r[1]]
    print("\n%s  batch H8c E2E  (%d checks, %d failed)  [%s]"
          % ("PASS" if not bad else "FAIL", len(RESULTS), len(bad),
             "LIVE 2.10.73" if live else "PREFLIGHT 2.10.76"))
    if bad:
        for n, _, det in bad:
            print("   FAIL %s  | %s" % (n, det[:200]))
    out = {"live": live, "checks": [{"name": n, "ok": o, "detail": d}
                                    for n, o, d in RESULTS],
           "ok": not bad, "total": len(RESULTS), "failed": len(bad)}
    path = "/tmp/h8c-e2e-%s.json" % ("live" if live else "pre")
    json.dump(out, open(path, "w"), indent=1)
    print("  json -> %s" % path)
    return 0 if not bad else 1


def main():
    return run(live="--live" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
