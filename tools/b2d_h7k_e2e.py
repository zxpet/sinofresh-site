#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7k E2E — the still links, the badge, the strip, the columns, the table.

Target: the PREFLIGHT copy (2.10.72), not the live dev theme. Dev still serves
2.10.69 (batches B/C/D are push-only), so the candidate exists on the box only
as `sinofresh-theme-preflight`, behind the `X-SF-Preflight: 1` header. Every
page re-asserts WHICH artifact served it before asserting anything about it:
the 401 page answers `location.pathname == "/"` with zero stylesheet links, and
every other query on it returns 0/false — a shape that reads exactly like "the
new markup never rendered".

`--live` drops the preflight header and drives dev's own 2.10.69, where every
claim below must FAIL. That is the run that proves this script can be red; a
green `--live` run would mean the checks are reading something other than the
artifact they name.

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the same
`set headers` call.

What each assertion is anchored to
----------------------------------
待办14  the still as a LINK, proven three ways that fail independently: the
        anchor is the figure's only child and the image is its only child
        (structure), the href equals the card's own title href (target), and
        `elementFromPoint` at the image's centre returns the anchor followed by
        a real click that lands on the formula page (hit test). Plus the paint
        claim that makes the link invisible: `display: block` on the anchor, so
        the figure and the image measure the same height — an inline anchor
        adds a line box under the image and the two numbers drift apart.

待办17  the badge, which renders NOWHERE on this data set because no record
        carries the value — and is therefore exercised by INJECTING one into a
        live card and reading the paint back. A feature that ships invisible
        and is never painted by any test is a feature nobody has seen work.
        The three colours are asserted as the exact rgb triples, and the WCAG
        ratio of the label against each is computed in-page and required to
        clear 4.5:1 — the numbers the stylesheet's comment records are checked
        here rather than trusted.

待办18  the strip, as geometry: two rows of three at 1440 and three of two at
        768/375, read from the chips' own distinct `top` values rather than
        from `grid-template-columns` alone. The band's height is asserted under
        a bound, and the section's 32px padding is compared against the other
        `sf-section--large` sections on the same page — which must still be at
        48px, because the claim is "one section moved", not "padding moved".

待办19  two columns, proven by geometry at both ends: at 1440 the two share a
        top and differ in left; at 375 the second one's top is below the first
        one's bottom AND the section is no taller than the sum of the two — the
        50% claim, measured.

待办22  the table against its own heading. The claim is not "width: 100%" but
        "the table's two ends land on the heading's two ends", so the numbers
        compared are the two elements' rects, and the CSS is read as well to
        say the 720px cap is gone (`max-width: none`) rather than merely
        outgrown.
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

STRIP = ['FDA Registered', 'cGMP Compliant', 'ISO 9001 Certified',
         'FSSC 22000 Certified', 'HACCP Certified', 'BRC Certified']

# 待办17's three colours, as the stylesheet writes them.
BADGES = {'best-seller': 'rgb(138, 109, 31)',      # #8A6D1F
          'hot':         'rgb(179, 38, 30)',       # #B3261E
          'new':         'rgb(31, 92, 153)'}       # #1F5C99

RESULTS = []


def ab(*a, timeout=180):
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
    print(("PASS " if ok else "FAIL ") + name + ("  | " + str(detail)[:300] if detail else ""))


def session(live=False):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE if live else PF)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def open_at(path, w, h=900):
    ab("open", BASE + path)
    time.sleep(2.0)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.75)
        got = ev("JSON.stringify({w: innerWidth})")
        if isinstance(got, dict) and got.get("w") == w:
            return
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def served(path, why):
    """Which artifact answered, asserted BEFORE anything is asserted about it."""
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, title: document.title, theme,
               pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
               v72: theme.includes('ver=2.10.72'),
               h1: document.querySelectorAll('h1').length };
    })()""")
    check("preflight 2.10.72 served (%s)  [%s]" % (path, why),
          isinstance(s, dict) and s.get("pre") is True and s.get("v72") is True
          and s.get("h1") == 1, s)
    return s


# ------------------------------------------------------------------ probes

CARDS = """(() => {
  const figs = Array.from(document.querySelectorAll('figure.sf-fcard__media'));
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(2), h: +r.height.toFixed(2),
             l: +r.left.toFixed(2), t: +r.top.toFixed(2) }; };
  const cards = figs.map(f => {
    const a = f.querySelector(':scope > a.sf-fcard__imagelink');
    const card = f.closest('article.sf-fcard');
    const title = card ? card.querySelector('.sf-fcard__name a') : null;
    // Falls back to the figure's own image, so a run against a build with no
    // link in it reports FAILs instead of crashing on a missing box. A test
    // that dies on the very state it exists to detect reports nothing.
    const img = (a ? a.querySelector(':scope > img') : null) || f.querySelector(':scope > img');
    return { href: a ? a.getAttribute('href') : null,
             label: a ? a.getAttribute('aria-label') : null,
             anchors: f.querySelectorAll(':scope > a.sf-fcard__imagelink').length,
             kids: Array.from(f.children).map(c => c.tagName.toLowerCase() + '.' +
                                                   (c.className || '').split(' ')[0]),
             imgChildren: a ? a.children.length : -1,
             imgTag: img ? img.tagName.toLowerCase() : null,
             titleHref: title ? title.getAttribute('href') : null,
             titleText: title ? title.textContent.trim() : null,
             badgeInLink: a ? a.querySelectorAll('.sf-fcard__badge').length : -1,
             bareImgs: f.querySelectorAll(':scope > img').length,
             disp: a ? getComputedStyle(a).display : null,
             alt: img ? img.getAttribute('alt') : null,
             box: R(f), imgBox: img ? R(img) : null, aBox: a ? R(a) : null };
  });
  let items = 0;
  const walk = n => { if (!n || typeof n !== 'object') return;
    if (Array.isArray(n)) { n.forEach(walk); return; }
    if (n.numberOfItems !== undefined) items += n.numberOfItems;
    Object.values(n).forEach(walk); };
  Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
    .forEach(s => { try { walk(JSON.parse(s.textContent)); } catch (e) {} });
  return { n: figs.length, items, cards };
})()"""

# 待办17 — the badge is painted onto a live card and read back. The WCAG ratio
# is computed in the page from the two painted colours, so it grades what the
# browser resolved (var() and all) rather than what the stylesheet intended.
BADGE = """(slug) => {
  const f = document.querySelector('figure.sf-fcard__media');
  if (!f) return { present: false };
  f.querySelectorAll('.sf-fcard__badge').forEach(e => e.remove());
  const a = f.querySelector('a.sf-fcard__imagelink');
  const before = a ? a.getAttribute('aria-label') : null;
  const s = document.createElement('span');
  s.className = 'sf-fcard__badge' + (slug ? ' sf-fcard__badge--' + slug : '');
  s.textContent = 'Hot';
  f.appendChild(s);
  const probe = document.createElement('span');
  probe.style.background = 'var(--wp--preset--color--primary)';
  probe.style.color = 'var(--wp--preset--color--card-white)';
  document.body.appendChild(probe);
  const prim = getComputedStyle(probe).backgroundColor;
  const card = getComputedStyle(probe).color;
  probe.remove();
  const cs = getComputedStyle(s), r = s.getBoundingClientRect(), fr = f.getBoundingClientRect();
  const lin = c => { const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number)
      .map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const ratio = (x, y) => { const a = lin(x), b = lin(y);
    return +(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05))).toFixed(2); };
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hit = document.elementFromPoint(cx, cy);
  return { present: true, slug: slug,
           position: cs.position, top: cs.top, right: cs.right, zIndex: cs.zIndex,
           background: cs.backgroundColor, color: cs.color, fontSize: cs.fontSize,
           weight: cs.fontWeight, transform: cs.textTransform, radius: cs.borderTopLeftRadius,
           w: +r.width.toFixed(1), h: +r.height.toFixed(1),
           gapTop: +(r.top - fr.top).toFixed(1), gapRight: +(fr.right - r.right).toFixed(1),
           inside: r.left >= fr.left - 1 && r.right <= fr.right + 1,
           hitSelf: hit === s, hitTag: hit ? hit.tagName.toLowerCase() : null,
           ratio: ratio(cs.color, cs.backgroundColor),
           primary: prim, cardWhite: card,
           labelBefore: before,
           labelAfter: a ? a.getAttribute('aria-label') : null,
           inFigure: f.querySelectorAll(':scope > .sf-fcard__badge').length,
           freeSpace: f.querySelectorAll(':scope > a.sf-fcard__imagelink').length,
           sw: document.documentElement.scrollWidth, iw: innerWidth };
}"""

BAND = """(() => {
  const b = document.querySelector('.sf-certstrip');
  if (!b) return { present: false };
  const cs = e => getComputedStyle(e);
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             l: +r.left.toFixed(1), t: +r.top.toFixed(1) }; };
  const lede = b.querySelector('.sf-certstrip__lede');
  const row = b.querySelector('.sf-certstrip__row');
  const chips = Array.from(b.querySelectorAll('.sf-certstrip__badge'));
  const more = b.querySelector('.sf-certstrip__more a');
  const sec = b.closest('section');
  return { present: true, vw: innerWidth,
    lede: lede ? lede.textContent.trim() : null,
    ledeSize: lede ? cs(lede).fontSize : null,
    ledeAlign: lede ? cs(lede).textAlign : null,
    tag: row.tagName.toLowerCase(), role: row.getAttribute('role'),
    cols: row ? cs(row).gridTemplateColumns : null,
    rowGap: row ? cs(row).rowGap : null, colGap: row ? cs(row).columnGap : null,
    n: chips.length,
    names: chips.map(c => (c.querySelector('.sf-certstrip__name') || {}).textContent),
    nameSize: chips.length ? cs(chips[0].querySelector('.sf-certstrip__name')).fontSize : null,
    tops: [...new Set(chips.map(c => Math.round(c.getBoundingClientRect().top)))].length,
    lefts: [...new Set(chips.map(c => Math.round(c.getBoundingClientRect().left)))].length,
    icons: chips.map(c => { const s = c.querySelector('svg');
      const r = s.getBoundingClientRect();
      return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
               cls: s.getAttribute('class'), aria: s.getAttribute('aria-hidden'),
               role: s.getAttribute('role'), focusable: s.getAttribute('focusable'),
               circles: s.querySelectorAll('circle').length,
               paths: s.querySelectorAll('path').length,
               texts: s.querySelectorAll('text').length,
               colour: cs(s).color, fill: cs(s).fill }; }),
    moreHref: more ? more.getAttribute('href') : null,
    moreColour: more ? cs(more).color : null,
    moreSize: more ? cs(more).fontSize : null,
    secBox: R(sec), secPad: cs(sec).paddingTop + ' / ' + cs(sec).paddingBottom,
    // The strip's OWN box, because the section it lives in is not the band: it
    // also holds the testing bar and the outline button, and this batch touched
    // neither. Measured at 1440 — strip 155.4, bar 87.3, buttons 48, section
    // 414.7 — so a bound asserted on the section is a bound on two strangers.
    stripBox: R(b),
    afterStrip: Array.from(sec.children).map(x => x.tagName.toLowerCase() + '.' +
                 (x.className || '').toString().split(' ').slice(0, 2).join('.')
                 + '=' + R(x).h),
    others: Array.from(document.querySelectorAll('section.sf-section--large'))
              .filter(s => !s.querySelector('.sf-certstrip')).length,
    otherPad: [...new Set(Array.from(document.querySelectorAll('section.sf-section--large'))
              .filter(s => !s.querySelector('.sf-certstrip'))
              .map(s => cs(s).paddingTop + ' / ' + cs(s).paddingBottom))],
    // WHICH other section is not at 48px, and whether a rule that predates this
    // batch already gives it 32px. The `Insights / Latest Articles` section does
    // not take its padding from the markup at all: at `(min-width: 769px)` the
    // stylesheet's `.sf-section:has(.sf-slot--cover)` rule wins it at 32px, and
    // it did so before this batch existed. So the claim is not "every other
    // section is 48px" — that was never true — but "the only section not at
    // 48px is the one that rule already covers".
    otherSections: Array.from(document.querySelectorAll('section.sf-section--large'))
              .filter(s => !s.querySelector('.sf-certstrip'))
              .map(s => ({ pad: cs(s).paddingTop + ' / ' + cs(s).paddingBottom,
                           text: (s.textContent || '').trim().slice(0, 24),
                           pre32: s.matches('.sf-section:has(.sf-slot--cover)') })),
    cards: document.querySelectorAll('.sf-certgrid, .sf-certcard').length,
    h2s: Array.from(document.querySelectorAll('h2, h3'))
           .map(h => h.textContent.trim()).filter(t => /Certification/i.test(t)),
    sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""

PREP = """(() => {
  const c = document.querySelector('.wp-block-columns.sf-prepare');
  if (!c) return { present: false };
  const cs = e => getComputedStyle(e);
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             l: +r.left.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
  const cols = Array.from(c.children).filter(e => e.classList.contains('wp-block-column'));
  const sec = c.closest('section');
  const h2 = c.previousElementSibling;
  return { present: true, vw: innerWidth, secH: +sec.getBoundingClientRect().height.toFixed(1),
    n: cols.length, counts: cols.map(k => k.querySelectorAll(':scope > p').length),
    texts: Array.from(c.querySelectorAll('p')).map(p => p.textContent.trim()),
    boxes: cols.map(R), dir: cs(c).flexDirection, wrap: cs(c).flexWrap,
    // The 50% claim, measurable without a second capture: two columns share one
    // row, so the block is as tall as its TALLEST column; stacked, it would be
    // as tall as their SUM. Also the block's own box, because the section's
    // height is heading + gap + block + padding — the first version of that
    // check compared the section against a column plus a guessed 160px and
    // failed a correct build by 15px, the guess having left out the heading.
    block: R(c), sumCols: +cols.reduce((a, k) => a + R(k).h, 0).toFixed(1),
    h2Box: h2 ? R(h2) : null,
    h2: h2 && h2.tagName === 'H2' ? h2.textContent.trim() : null,
    h2First: h2 ? R(h2).l : null, colFirst: cols.length ? R(cols[0]).l : null,
    sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""

KF = """(() => {
  const t = document.querySelector('table.sf-keyfacts');
  if (!t) return { present: false };
  const cs = e => getComputedStyle(e);
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), l: +r.left.toFixed(1), r: +r.right.toFixed(1) }; };
  let h = t.previousElementSibling;
  while (h && !/^H[1-6]$/.test(h.tagName)) h = h.previousElementSibling;
  return { present: true, vw: innerWidth, table: R(t), head: h ? R(h) : null,
    headText: h ? h.textContent.trim() : null,
    // The heading's OWN cap, so the claim can be "the table is under the cap the
    // heading is under" instead of naming a pixel value the theme could change.
    headMaxWidth: h ? cs(h).maxWidth : null,
    maxWidth: cs(t).maxWidth, marginLeft: cs(t).marginLeft, marginRight: cs(t).marginRight,
    rows: t.querySelectorAll('tbody tr').length,
    sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""


def want(name):
    return name in ONLY or not ONLY


ONLY = set()


# ================================================================== sections

def s_cards():
    """待办14 — the still is a link, and the link is the record's own."""
    for path, expect_n in (('/products/drops/', 2), ('/formulas/', 21),
                           ('/formulas/joint-support-soft-chews/', 3),
                           ('/zh/products/drops/', 2)):
        open_at(path, 1440)
        served(path, 'cards')
        d = ev(CARDS)
        cards = d.get("cards") or []
        check("%s: every card still carries its figure and its still" % path,
              d.get("n") == expect_n and len(cards) == expect_n,
              {"figures": d.get("n"), "want": expect_n})
        check("%s: each figure holds exactly one link and the image is INSIDE it" % path,
              bool(cards) and all(c["anchors"] == 1 and c["imgTag"] == "img"
                                  and c["imgChildren"] == 1 and c["bareImgs"] == 0
                                  for c in cards),
              [{"a": c["anchors"], "kids": c["kids"], "bare": c["bareImgs"]}
               for c in cards][:3])
        check("%s: and the badge stays a SIBLING of the still, never inside the link" % path,
              bool(cards) and all(c["badgeInLink"] == 0 for c in cards),
              [c["badgeInLink"] for c in cards][:5])
        # The target: the link and the title are the same route. Two anchors to
        # one page is the point; two anchors to different pages is the defect.
        check("%s: the image link points where the card title points" % path,
              bool(cards) and all(c["href"] and c["href"] == c["titleHref"] for c in cards),
              [(c["href"], c["titleHref"]) for c in cards if c["href"] != c["titleHref"]][:3])
        # The accessible name: it says where it goes, and it is not the alt text.
        check("%s: and it says where it goes — 'View the <name> formula'" % path,
              bool(cards) and all(c["label"] == "View the %s formula" % c["titleText"]
                                  for c in cards),
              [(c["label"], c["titleText"]) for c in cards
               if c["label"] != "View the %s formula" % c["titleText"]][:3])
        check("%s: the label is not the photograph's own description" % path,
              bool(cards) and all(c["label"] and c["alt"] and c["alt"] not in c["label"]
                                  for c in cards),
              [(c["label"], c["alt"]) for c in cards][:2])
        # The paint that makes the link invisible: a block anchor, so the figure
        # and the image measure the same box. An inline anchor leaves a line box
        # under the image and the two heights stop agreeing.
        check("%s: the link is a block, so it adds no line box under the image" % path,
              bool(cards) and all(c["disp"] == "block" for c in cards))
        check("%s: measured — the figure, the link and the image are one height" % path,
              bool(cards) and all(c["imgBox"] and c["aBox"]
                  and abs(c["box"]["h"] - c["imgBox"]["h"]) <= 1
                  and abs(c["aBox"]["h"] - c["imgBox"]["h"]) <= 1 for c in cards),
              [(c["box"]["h"], (c["aBox"] or {}).get("h"), (c["imgBox"] or {}).get("h"))
               for c in cards][:3])
        # ...and the count is corroborated by the page's own published number.
        check("%s: the links number exactly what the page's ItemList publishes" % path,
              d.get("n") == d.get("items"),
              {"links": d.get("n"), "itemList": d.get("items")})

    # The hit test, on the archive: the image is really clickable, and clicking
    # it lands on the formula the card is about.
    open_at('/formulas/', 1440)
    served('/formulas/', 'cards: hit test')
    ab("scroll", "down", "1200")
    time.sleep(1.2)
    hit = ev("""(() => {
      const a = document.querySelector('a.sf-fcard__imagelink[href$="/formulas/ear-care-drops/"]');
      if (!a) return { found: false };
      a.scrollIntoView({block: 'center'});
      const r = a.getBoundingClientRect();
      const x = r.left + r.width / 2, y = r.top + r.height / 2;
      const e = document.elementFromPoint(x, y);
      const near = e && e.closest ? e.closest('a') : null;
      return { found: true, x: +x.toFixed(0), y: +y.toFixed(0),
               hitIsAnchor: e === a, hitTag: e ? e.tagName.toLowerCase() : null,
               inLink: a.contains(e), nearestHref: near ? near.getAttribute('href') : null,
               href: a.getAttribute('href'),
               complete: (a.querySelector('img') || {}).complete };
    })()""")
    # The claim is "clicking the still follows the card's own link", not "the hit
    # IS the anchor". `elementFromPoint` returns the `<img>`, which is INSIDE the
    # anchor: the first version of this check demanded the anchor itself and
    # reported FAIL on a correct build, while the very same build passed whenever
    # the image had not loaded yet and the point fell through to the anchor — a
    # check whose verdict depended on image timing. What has to hold is that the
    # point is inside the link AND the nearest anchor is the card's own route.
    check("/formulas/: the centre of the still hit-tests inside the still's own link",
          hit.get("found") is True and hit.get("inLink") is True
          and hit.get("nearestHref") == hit.get("href")
          and hit.get("complete") is True, hit)
    if hit.get("found") is True:
        ab("click", 'a.sf-fcard__imagelink[href$="/formulas/ear-care-drops/"]')
        time.sleep(2.5)
        after = ev("JSON.stringify({p: location.pathname})")
        check("/formulas/: clicking the still lands on the formula it belongs to",
              isinstance(after, dict) and after.get("p") == "/formulas/ear-care-drops/", after)


def badge_at(slug):
    """Inject one badge onto a live card and read the paint back. No `%`-format:
    the probe is an arrow function, and the slug is its argument."""
    return ev("(%s)('%s')" % (BADGE, slug))


def s_badge():
    """待办17 — the badge is painted by injection, and its colours are measured."""
    open_at('/products/drops/', 1440)
    served('/products/drops/', 'badge')
    n_figs = (ev(CARDS).get("n") or 0)
    n_badges = ev("document.querySelectorAll('.sf-fcard__badge').length")
    check("待办17: no record carries a badge yet, so none renders — 0 on the page",
          n_figs == 2 and n_badges == 0, {"figures": n_figs, "badges": n_badges})
    base = badge_at("")
    check("待办17: injected, the badge is an absolute overlay 12px from the top-right",
          base.get("position") == "absolute" and base.get("top") == "12px"
          and base.get("right") == "12px" and base.get("zIndex") == "2"
          and base.get("gapTop") == 12 and base.get("gapRight") == 12
          and base.get("inside") is True, base)
    check("待办17: with no modifier it falls back to the palette's primary, not to nothing",
          base.get("background") == base.get("primary")
          and base.get("background") != "rgba(0, 0, 0, 0)", base)
    check("待办17: the label is legible on it — 11px, bold, uppercased",
          base.get("fontSize") == "11px" and base.get("weight") == "700"
          and base.get("transform") == "uppercase", base)
    check("待办17: the badge paints ABOVE the still — it hit-tests to itself",
          base.get("hitSelf") is True, {"hit": base.get("hitTag"), "z": base.get("zIndex")})
    # K7, proven rather than commented: the badge is a sibling, so its label
    # cannot become part of the link's accessible name.
    check("待办17: and it is not inside the link — the link's name is unchanged",
          bool(base.get("labelBefore"))
          and base.get("labelAfter") == base.get("labelBefore")
          and "Hot" not in (base.get("labelAfter") or ""), base)
    check("待办17: the still is still the figure's only link",
          base.get("freeSpace") == 1 and base.get("inFigure") == 1, base)
    for slug, rgb in BADGES.items():
        r = badge_at(slug)
        check("待办17: the %s badge paints %s" % (slug, rgb),
              r.get("background") == rgb, {"got": r.get("background"), "want": rgb})
        check("待办17: ...and its label clears AA on that ground (ratio %.2f)" % (r.get("ratio") or 0),
              (r.get("ratio") or 0) >= 4.5,
              {"ratio": r.get("ratio"), "colour": r.get("color"), "bg": r.get("background")})
    inline = ev("""(() => {
      const f = document.querySelector('figure.sf-fcard__media');
      const s = document.createElement('span');
      s.className = 'sf-fcard__badge sf-fcard__badge--new sf-fcard__badge--inline';
      s.textContent = 'New'; f.appendChild(s);
      const cs = getComputedStyle(s);
      const out = { position: cs.position, alignSelf: cs.alignSelf, marginBottom: cs.marginBottom,
                    background: cs.backgroundColor };
      s.remove(); return out; })()""")
    check("待办17: the no-still placement is static and shrink-wrapped, not an overlay",
          inline.get("position") == "static" and inline.get("alignSelf") == "flex-start"
          and inline.get("background") == BADGES["new"], inline)


def s_band(lang='en'):
    """待办18 — the strip, its geometry, and the section it left behind."""
    path = '/zh/' if lang == 'zh' else '/'
    open_at(path, 1440)
    served(path, 'band')
    d = ev(BAND)
    check("%s: the six cards are gone and the six chips are here" % path,
          d.get("present") is True and d.get("n") == 6 and d.get("cards") == 0, d)
    check("%s: the chips keep the six names, in order, verbatim" % path,
          d.get("names") == STRIP, {"got": d.get("names")})
    check("%s: and the heading the band used to carry is gone" % path,
          d.get("h2s") == [], {"h2s": d.get("h2s")})
    check("%s: it leads with the sentence the brief asked for" % path,
          (d.get("lede") or "").startswith("Certified to the standards global pet brands trust"),
          d.get("lede"))
    check("%s: the lede is one centred line at 17px" % path,
          d.get("ledeSize") == "17px" and d.get("ledeAlign") == "center", d)
    check("%s: the row is a real list of six items, 3 x 2 at 1440" % path,
          d.get("tag") == "ul" and d.get("role") == "list"
          and d.get("tops") == 2 and d.get("lefts") == 3,
          {"tops": d.get("tops"), "lefts": d.get("lefts"), "cols": d.get("cols")})
    icons = d.get("icons") or []
    check("%s: every chip carries the seal's drawing, copied — 2 circles and the ribbon" % path,
          len(icons) == 6 and all(i["circles"] == 2 and i["paths"] == 1 for i in icons),
          icons[:2])
    check("%s: ...shrunk to 32px and stripped of the lettering and the role" % path,
          len(icons) == 6 and all(i["w"] == 32 and i["h"] == 32 and i["texts"] == 0
                                  and i["aria"] == "true" and i["role"] is None for i in icons),
          icons[:2])
    check("%s: ...and it paints, in the palette's primary" % path,
          len(icons) == 6 and all(i["colour"] and i["colour"] != "rgba(0, 0, 0, 0)"
                                  for i in icons),
          [i["colour"] for i in icons][:3])
    # The brief's height is the BAND's height. The section is 414.7px because it
    # carries the strip (155.4) plus the testing bar (87.3) and the outline
    # button (48) this batch never touched — so the first version of this check,
    # asserted on the section, could not have passed on any correct build.
    check("%s: the strip is the height the brief asked for — <= 180px" % path,
          (d.get("stripBox") or {}).get("h", 9999) <= 180,
          {"strip": d.get("stripBox"), "section": d.get("secBox"),
           "sectionChildren": d.get("afterStrip")})
    check("%s: the strip asks for 32px, and the only other large section off 48px "
          "is the one a pre-existing rule already covers" % path,
          d.get("secPad") == "32px / 32px"
          and bool(d.get("otherSections"))
          and all(o["pad"] == "48px / 48px" or o["pre32"] for o in d.get("otherSections"))
          and any(o["pre32"] for o in d.get("otherSections")),
          {"strip": d.get("secPad"),
           "off48": [o for o in (d.get("otherSections") or [])
                     if o["pad"] != "48px / 48px"]})
    check("%s: the link to the full page is a link, in the brand green" % path,
          d.get("moreHref") == ("/zh/quality/#certifications" if lang == "zh"
                                else "/quality/#certifications")
          and d.get("moreColour") == "rgb(90, 183, 53)", d)
    check("%s: and the strip does not make the page scroll sideways" % path,
          (d.get("sw") or 0) <= (d.get("iw") or 0) + 1,
          {"scroll": d.get("sw"), "inner": d.get("iw")})
    for w, rows, lefts in ((768, 3, 2), (375, 3, 2)):
        open_at(path, w)
        served(path, 'band@%d' % w)
        r = ev(BAND)
        check("%s@%d: the strip becomes two columns of three, not one column of six"
              % (path, w),
              r.get("tops") == rows and r.get("lefts") == lefts,
              {"tops": r.get("tops"), "lefts": r.get("lefts"), "cols": r.get("cols")})
        check("%s@%d: ...and the chips still fit the viewport" % (path, w),
              (r.get("sw") or 0) <= (r.get("iw") or 0) + 1,
              {"scroll": r.get("sw"), "inner": r.get("iw")})


def s_prepare():
    """待办19 — two columns, and the height the brief says it saves."""
    open_at('/factory-tour/', 1440)
    served('/factory-tour/', 'prepare')
    d = ev(PREP)
    boxes = d.get("boxes") or []
    check("/factory-tour/: the checklist is a columns block of two, 3 and 2",
          d.get("present") is True and d.get("n") == 2 and d.get("counts") == [3, 2], d)
    check("/factory-tour/: and it sits under the heading it belongs to",
          d.get("h2") == "What to Prepare"
          and abs((d.get("h2First") or 0) - (d.get("colFirst") or -9)) <= 1, d)
    # The five items verbatim, in order — not "the first one starts with". Each
    # paragraph is written `&#10003; Your company name and target market`, so the
    # marker is stripped before comparing; the first version asserted
    # `startswith('Your company name')` against the raw text and failed a correct
    # build because the string begins with the tick.
    check("/factory-tour/: the five items are the page's own, unchanged and in order",
          [t.lstrip("\u2713 ").strip() for t in (d.get("texts") or [])] == [
              "Your company name and target market", "Interested dosage forms",
              "Any specific compliance requirements", "Preferred tour date and time",
              "If on-site, your travel schedule"],
          d.get("texts"))
    check("/factory-tour/: at 1440 the two columns stand side by side",
          len(boxes) == 2 and abs(boxes[0]["t"] - boxes[1]["t"]) <= 2
          and boxes[1]["l"] > boxes[0]["l"],
          boxes)
    # The 50%-shorter claim, stated as the mechanism rather than a bound on the
    # section: one row means the block is as tall as its tallest column, where
    # stacking would make it as tall as their sum. Measured 124.8 against a
    # sum of 249.6.
    check("/factory-tour/: ...and the two share one row, so the block is one column tall",
          len(boxes) == 2
          and abs((d.get("block") or {}).get("h", -9) - max(b["h"] for b in boxes)) <= 1
          and (d.get("sumCols") or 0) > (d.get("block") or {}).get("h", 0) + 20,
          {"block": (d.get("block") or {}).get("h"), "cols": [b["h"] for b in boxes],
           "sum": d.get("sumCols"), "secH": d.get("secH")})
    open_at('/factory-tour/', 375)
    served('/factory-tour/', 'prepare@375')
    r = ev(PREP)
    boxes = r.get("boxes") or []
    check("375: the two columns stack, one above the other",
          len(boxes) == 2 and boxes[1]["t"] >= boxes[0]["b"] - 2
          and abs(boxes[0]["w"] - boxes[1]["w"]) <= 2, boxes)
    # Against the page's CONTENT column, not the viewport: at 375 the gutter is
    # 38px a side, so the content column is 299px. The first version compared the
    # columns to `innerWidth` — 375 — and failed a correct build by 76px.
    check("375: ...and each takes the full width of the content column",
          len(boxes) == 2 and (r.get("h2Box") or {}).get("w") is not None
          and all(abs(b["w"] - r["h2Box"]["w"]) <= 2 for b in boxes),
          {"w": [b["w"] for b in boxes], "contentW": (r.get("h2Box") or {}).get("w"),
           "viewport": r.get("iw")})
    check("375: ...without the page scrolling sideways",
          (r.get("sw") or 0) <= (r.get("iw") or 0) + 1,
          {"scroll": r.get("sw"), "inner": r.get("iw")})


def s_keyfacts():
    """待办22 — the table against its own heading."""
    open_at('/services/', 1440)
    served('/services/', 'keyfacts')
    d = ev(KF)
    t, h = d.get("table") or {}, d.get("head") or {}
    check("/services/: the Key Facts table spans the column its heading spans",
          d.get("present") is True and abs(t.get("w", 0) - h.get("w", -9)) <= 2,
          {"table": t.get("w"), "heading": h.get("w"), "head": d.get("headText")})
    check("/services/: ...and their two ends line up, left and right",
          abs(t.get("l", -9) - h.get("l", 0)) <= 2 and abs(t.get("r", -9) - h.get("r", 0)) <= 2,
          {"table": [t.get("l"), t.get("r")], "heading": [h.get("l"), h.get("r")]})
    # `max-width: none` was the batch's first answer and it satisfies "the 720px
    # cap is gone" while breaking the claim the brief actually made: the section
    # is an `is-layout-constrained` group, so the heading is capped at the
    # content size (1200px) and centred, and `none` let the table fill the whole
    # 1364px content box — 82px past the heading on each side. So the check is
    # "the same cap as the heading" and explicitly not `none`.
    check("/services/: the table is under the cap its heading is under, not merely outgrown",
          d.get("maxWidth") == d.get("headMaxWidth")
          and d.get("maxWidth") not in ("none", None, "720px"),
          {"tableMaxWidth": d.get("maxWidth"), "headMaxWidth": d.get("headMaxWidth"),
           "ml": d.get("marginLeft"), "mr": d.get("marginRight")})
    open_at('/services/', 375)
    served('/services/', 'keyfacts@375')
    r = ev(KF)
    check("375: the table fits the phone instead of forcing a sideways scroll",
          (r.get("sw") or 0) <= (r.get("iw") or 0) + 1,
          {"scroll": r.get("sw"), "inner": r.get("iw"), "rows": r.get("rows")})


def main():
    global ONLY
    args = sys.argv[1:]
    live = "--live" in args
    if "--only" in args:
        ONLY = set(args[args.index("--only") + 1].split(","))
    session(live=live)
    try:
        if want("cards"):
            s_cards()
        if want("badge"):
            s_badge()
        if want("band"):
            s_band("en")
            s_band("zh")
        if want("prepare"):
            s_prepare()
        if want("keyfacts"):
            s_keyfacts()
        errs = ab("errors")
        check("0 page errors", not errs.strip(), errs[:200])
    finally:
        ab("close")
    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n%s%s: %d/%d checks passed"
          % ("LIVE (2.10.69) — this run MUST be red. " if live else "", "H7k",
             len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("FAILED:")
        for n in bad:
            print("  - " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
