#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7j E2E — the nav gap, the facts band's gutter, the current item marked.

Target: the PREFLIGHT copy (2.10.71), not the live dev theme. Batch C is a
push-only batch, so dev still serves 2.10.69 and the candidate exists on the box
only as `sinofresh-theme-preflight`, behind the `X-SF-Preflight: 1` header.
Every page re-asserts WHICH artifact served it before asserting anything about
it: the 401 page answers `location.pathname == "/"` with zero stylesheet links,
and every other query on it returns 0/false — a shape that reads exactly like
"the new markup never rendered".

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the same
`set headers` call.

What each assertion is anchored to
----------------------------------
待办10  the GAP, and the header's own flex lines. The nav is a flex item with
        `flex-wrap: wrap`, so a wider nav changes WHERE the header's lines
        fall — measured, the one-row floor moves 940 -> 1000 and a 7px band at
        769..775 takes a third line. Both are asserted here as facts about the
        build, not smoothed over: the three breakpoints the brief names
        (desktop / tablet / phone) are asserted NOT to have changed height.

待办15  the facts band's gutter, as a NUMBER matched against its neighbours.
        The band draws the page's two hairlines, so its own box must stay
        full-bleed; only its content moves in. Asserted as "the band's first
        item starts where the neighbouring bands' content starts".

待办20  the mark, as a PAINT. A class name alone would also be true of a link
        with no rule behind it, so every variant is read back through
        getComputedStyle. The read happens a round trip after the class swap
        because the link declares `transition: color 0.15s, border-color
        0.15s`: inside that window `color` and `border-color` still report the
        OUTGOING value while `border-width` has already snapped, and a
        single-eval probe therefore mixes two instants. Measured, and the
        cause of a false "the brand-green mark paints white" earlier in the
        batch.

        aria-current is asserted against an independent transcription of the
        rule (see EXPECT below), never read back out of the page it grades.
        The distinction that matters: a link that POINTS AT the page is
        `page`; a link whose SECTION merely contains it is `true`. On
        /products/soft-chews/ the marked item is therefore /products/ — the
        item that owns the dropdown — and not the dosage page's own submenu
        link, which the transform prunes.
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
PF = json.dumps({"X-SF-Preflight": "1",
                 "Authorization": "Basic " + base64.b64encode(
                     ("%s:%s" % (USER, PASS)).encode()).decode()})

# --- the menu, and the rule, transcribed independently of the theme ---------
MENU = (
    ('/products/', ('/products/soft-chews/', '/products/tablets/', '/products/powders/',
                    '/products/pastes/', '/products/drops/', '/products/liquids/',
                    '/products/fish-oil/', '/products/dental-chews/', '/formulas/')),
    ('/services/', ()), ('/quality/', ()), ('/about/', ()),
    ('/factory-tour/', ()), ('/blog/', ()), ('/contact/', ()),
)


def under(path, url):
    url = '/' + url.strip('/') + '/'
    return path == url or path.startswith(url)


def expect(path):
    """(href, aria-current) the menu should carry on `path`, or None."""
    zh = path.startswith('/zh/')
    rel = '/' + path[4:] if zh else path
    for href, kids in MENU:
        if under(rel, href) or any(under(rel, k) for k in kids):
            return (('/zh' + href) if zh else href,
                    'page' if rel == '/' + href.strip('/') + '/' else 'true')
    return None


# path -> what the rule says, and why this path is worth driving.
# The English labels are the menu's own words, so a mark on the wrong item is
# caught by the text and not only by the href.
PAGES = [
    ('/about/', 'the item that points at the page itself', 'About'),
    ('/products/', 'the section landing page', 'Products'),
    ('/products/soft-chews/', 'a page INSIDE the dropdown: the owner is current, not the leaf', 'Products'),
    ('/formulas/', 'a page in the dropdown that lives at the site root', 'Products'),
    ('/contact/', 'the last top-level item', 'Contact'),
    ('/faq/', 'a page the menu does not offer at all', None),
    ('/zh/about/', 'the translated menu keeps its own hrefs', None),
    ('/zh/formulas/', 'and the translated dropdown resolves to the zh section', None),
]

# The six marks, as PAINTED, read off getComputedStyle after the transition has
# settled. Measured 2026-09-23 on the preflight copy at 1440px on /about/.
# `none` is the control: the is-active class present with no variant chosen.
#     color, backgroundColor, borderBottomWidth, borderBottomColor,
#     fontWeight, borderLeftWidth, borderLeftColor, paddingLeft, borderRadius
#
# `borderLeftColor` is in the tuple because leaving it out hid a real defect for
# a whole batch: only `left-line` draws with a left rule, and its active rule is
# (0,3,0) while the base rule that declares `border-left: 3px solid transparent`
# is (0,4,0). The base won, so the mark painted a 3px fully transparent rule at
# EVERY width — and because the tuple never read the colour, and the width it did
# read was a respectable 3px, the signature agreed. Measured, fixed, and this
# column is why it cannot come back.
#
# For the six that do not declare a left rule the value is the initial
# `currentColor` (hence white, and green for the `color` mark). Those entries are
# recorded as measured rather than asserted as intent; the claim that carries the
# weight is the invariant in `paints()` below.
VARIANTS = {
    'none':       ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)',        '1px',
                   'rgba(0, 0, 0, 0)',   '500', '0px', 'rgb(255, 255, 255)',
                   '0px',  '0px'),
    'underline':  ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)',        '2px',
                   'rgb(255, 255, 255)', '600', '0px', 'rgb(255, 255, 255)',
                   '0px',  '0px'),
    'bg':         ('rgb(255, 255, 255)', 'rgba(255, 255, 255, 0.15)', '1px',
                   'rgba(0, 0, 0, 0)',   '500', '0px', 'rgb(255, 255, 255)',
                   '10px', '4px'),
    'thick-line': ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)',        '4px',
                   'rgb(255, 255, 255)', '500', '0px', 'rgb(255, 255, 255)',
                   '0px',  '0px'),
    'color':      ('rgb(90, 183, 53)',   'rgba(0, 0, 0, 0)',        '1px',
                   'rgba(0, 0, 0, 0)',   '600', '0px', 'rgb(90, 183, 53)',
                   '0px',  '0px'),
    'left-line':  ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)',        '1px',
                   'rgba(0, 0, 0, 0)',   '500', '3px', 'rgb(255, 255, 255)',
                   '8px',  '0px'),
    'pill':       ('rgb(255, 255, 255)', 'rgba(90, 183, 53, 0.9)',  '1px',
                   'rgba(0, 0, 0, 0)',   '500', '0px', 'rgb(255, 255, 255)',
                   '14px', '999px'),
}
SLUGS = ['none', 'underline', 'bg', 'thick-line', 'color', 'left-line', 'pill']
SETTLE = 0.45   # > the declared 0.15s transition, with margin

# The tuple's channels, by name, so no index is ever spelled out twice.
(P_COLOR, P_BG, P_BBW, P_BBC, P_FW,
 P_BLW, P_BLC, P_PL, P_BR) = range(9)
TRANSPARENT = 'rgba(0, 0, 0, 0)'


def _px(v):
    try:
        return float(str(v).rstrip('px'))
    except (TypeError, ValueError):
        return 0.0


def uncoloured(p):
    """The rules a mark reserves and then paints nothing with.

    The same statement is needed in the bar and in the drawer, and it is worth
    stating as an INVARIANT rather than as more expected values, because the
    defect this batch kept running into has exactly this shape: a rule that
    occupies space and paints nothing. A 1px bottom hairline is the theme's own
    reservation (section 21c) and every link carries it, so anything WIDER than
    1px was reserved by a mark and is that mark's to colour. The left rule is
    reserved by `left-line` alone, and only it ever has a width there.
    """
    p = list(p or [])
    p += [None] * (9 - len(p))
    out = {}
    if _px(p[P_BBW]) > 1 and p[P_BBC] == TRANSPARENT:
        out['border-bottom'] = p[P_BBW]
    if _px(p[P_BLW]) > 0 and p[P_BLC] == TRANSPARENT:
        out['border-left'] = p[P_BLW]
    return out

# Header height at the three breakpoints the brief names, on 2.10.69 (measured
# with tools/b2d_h7j_rows.py --mode live). The gap change must not move them.
LIVE_HH = {1440: 81, 768: 65, 375: 65}

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


def session():
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", PF)
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


SERVED = """(() => {
  const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
  const theme = l.find(h => h.includes('sinofresh-theme')) || '';
  const H = document.querySelector('header.sf-header');
  return { path: location.pathname, title: document.title, theme,
           pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
           v71: theme.includes('ver=2.10.71'),
           h1: document.querySelectorAll('h1').length,
           variant: H ? ((H.className.match(/sf-header--nav-([a-z-]+)/) || [])[1] || null) : null,
           navGap: (() => { const u = document.querySelector('header .wp-block-navigation__container');
                            return u ? getComputedStyle(u).columnGap : null; })() };
})()"""

NAVSTATE = """(() => {
  const H = document.querySelector('header.sf-header');
  const links = Array.from(H.querySelectorAll('.sf-nav__link'));
  const top = Array.from(H.querySelectorAll(
      '.wp-block-navigation__container > .wp-block-navigation-item > .sf-nav__link'));
  const sub = Array.from(H.querySelectorAll('.wp-block-navigation__submenu-container .sf-nav__link'));
  const aria = links.filter(a => a.hasAttribute('aria-current'))
                    .map(a => [a.getAttribute('href'), a.getAttribute('aria-current')]);
  const active = links.filter(a => a.classList.contains('is-active'))
                      .map(a => [a.getAttribute('href'), a.getAttribute('aria-current'),
                                 a.textContent.trim()]);
  const both = links.filter(a => a.classList.contains('is-active') && !a.hasAttribute('aria-current'))
                    .length;
  const only = links.filter(a => !a.classList.contains('is-active') && a.hasAttribute('aria-current'))
                    .length;
  return { path: location.pathname, n: links.length, nTop: top.length, nSub: sub.length,
           top: top.map(a => a.getAttribute('href')),
           sub: sub.map(a => a.getAttribute('href')),
           aria, active, both, only,
           eachTouchedTwice: (() => {
             const seen = new Set(); let dup = 0;
             links.forEach(a => { const k = a.getAttribute('href');
               if (seen.has(k) && (a.classList.contains('is-active') || a.hasAttribute('aria-current'))) dup++;
               seen.add(k); });
             return dup; })() };
})()"""

NAVGEOM = """(() => {
  const H = document.querySelector('header.sf-header');
  const nav = H.querySelector('nav');
  const c = H.querySelector('.wp-block-navigation__responsive-container');
  const open = H.querySelector('.wp-block-navigation__responsive-container-open');
  const ul = H.querySelector('.wp-block-navigation__container');
  const items = Array.from(ul.children).filter(li => li.classList.contains('wp-block-navigation-item'));
  const bs = items.map(li => { const r = li.getBoundingClientRect();
    return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), y: +(r.top + r.height / 2).toFixed(1) }; });
  const steps = []; for (let i = 1; i < bs.length; i++) steps.push(+(bs[i].l - bs[i - 1].r).toFixed(1));
  const on = (a, b) => Math.abs(a - b) <= 6;
  const ctr = e => { const r = e.getBoundingClientRect(); return r.top + r.height / 2; };
  const cta = H.querySelector('.sf-header__cta'), logo = H.querySelector('.sf-logo');
  const gap = getComputedStyle(ul);
  const vis = e => e ? (getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0) : null;
  return { vw: innerWidth, items: items.length, colGap: gap.columnGap, rowGap: gap.rowGap,
           steps, oneRow: bs.every(b => on(b.y, bs[0].y)),
           navBox: [+nav.getBoundingClientRect().left.toFixed(1),
                    +nav.getBoundingClientRect().right.toFixed(1)],
           navW: +nav.getBoundingClientRect().width.toFixed(1),
           hH: Math.round(H.getBoundingClientRect().height),
           logoNav: on(ctr(logo), ctr(nav)), navCta: on(ctr(nav), ctr(cta)),
           hamb: vis(open), cont: vis(c),
           contOpen: c.classList.contains('is-menu-open'),
           ulDir: getComputedStyle(ul).flexDirection,
           sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""

DRAWER = """(() => {
  const H = document.querySelector('header.sf-header');
  const c = H.querySelector('.wp-block-navigation__responsive-container');
  const ul = c.querySelector('.wp-block-navigation__container');
  const items = Array.from(ul.children).filter(li => li.classList.contains('wp-block-navigation-item'));
  const bs = items.map(li => { const r = li.getBoundingClientRect();
    return { t: +r.top.toFixed(1), l: +r.left.toFixed(1), w: +r.width.toFixed(1),
             h: +r.height.toFixed(1) }; });
  const steps = []; for (let i = 1; i < bs.length; i++) steps.push(+(bs[i].t - bs[i - 1].t).toFixed(1));
  const style = getComputedStyle(ul);
  return { open: c.classList.contains('is-menu-open'),
           colGap: style.columnGap, rowGap: style.rowGap, ulDir: style.flexDirection,
           n: items.length, steps, hs: bs.map(b => b.h),
           itemH: bs.length ? bs[0].h : null, rowW: bs.length ? bs[0].w : null,
           marked: Array.from(c.querySelectorAll('.sf-nav__link.is-active'))
                    .map(a => a.getAttribute('href')),
           sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""

SETCLASS = """(slug) => {
  const H = document.querySelector('header.sf-header');
  const c = window.__sfBase.split(/\\s+/).filter(t => t && !/^sf-header--nav-/.test(t));
  if (slug !== 'none') c.push('sf-header--nav-' + slug);
  H.className = c.join(' ');
  return H.className;
}"""

PAINT = """(() => {
  const p = e => { const s = getComputedStyle(e);
    return [s.color, s.backgroundColor, s.borderBottomWidth, s.borderBottomColor,
            s.fontWeight, s.borderLeftWidth, s.borderLeftColor, s.paddingLeft,
            s.borderRadius]; };
  const act = document.querySelector('.sf-nav__link.is-active');
  const links = Array.from(document.querySelectorAll(
      '.wp-block-navigation__container > .wp-block-navigation-item > .sf-nav__link'));
  const sib = links.find(a => !a.classList.contains('is-active'));
  return { act: act ? p(act) : null, sib: sib ? p(sib) : null,
           hoverLeak: Array.from(document.querySelectorAll(':hover'))
                       .filter(e => e.classList && e.classList.contains('sf-nav__link')).length }; })()"""

FACTS = """(() => {
  const R = e => { const b = e.getBoundingClientRect();
    return { l: +b.left.toFixed(1), r: +b.right.toFixed(1), w: +b.width.toFixed(1),
             t: +b.top.toFixed(1), b: +b.bottom.toFixed(1) }; };
  const s = document.querySelector('.sf-facts-mini');
  if (!s) return { present: false };
  const cs = getComputedStyle(s);
  const items = Array.from(s.querySelectorAll('.sf-facts-mini__item'));
  const bs = items.map(R);
  const root = document.querySelector('.wp-site-blocks');
  const kids = root ? Array.from(root.children) : [];
  const bandOf = el => { const cs2 = getComputedStyle(el); const r = R(el);
    const leaves = Array.from(el.querySelectorAll('h1,h2,h3,p,li,span,div,a'))
      .filter(n => { const b = n.getBoundingClientRect();
                     return b.height > 4 && b.width > 4 && n.textContent.trim().length > 0; });
    let firstL = null, lastR = null;
    if (leaves.length) {
      firstL = Math.round(Math.min.apply(null, leaves.map(n => n.getBoundingClientRect().left)));
      lastR = Math.round(Math.max.apply(null, leaves.map(n => n.getBoundingClientRect().right)));
    }
    return { boxL: Math.round(r.l), boxR: Math.round(r.r), firstL, lastR,
             padL: cs2.paddingLeft, padR: cs2.paddingRight,
             cls: (el.className || el.tagName).toString().slice(0, 44) }; };
  const own = bandOf(s);
  const idx = kids.indexOf(s);
  const neigh = idx >= 0 ? kids.slice(Math.max(0, idx - 2), idx).map(bandOf)
                          .concat(kids.slice(idx + 1, idx + 3).map(bandOf)) : [];
  return { present: true, box: R(s), padL: cs.paddingLeft, padR: cs.paddingRight,
           justify: cs.justifyContent, disp: cs.display, colGap: cs.columnGap,
           n: items.length, rows: new Set(bs.map(b => b.t)).size,
           firstL: bs.length ? bs[0].l : null, lastR: bs.length ? bs[bs.length - 1].r : null,
           minL: Math.min.apply(null, bs.map(b => b.l)),
           maxR: Math.max.apply(null, bs.map(b => b.r)),
           own, neigh,
           sw: document.documentElement.scrollWidth, iw: innerWidth };
})()"""


def served(path, tag):
    s = ev(SERVED)
    ok = (s.get("path") == path and s.get("pre") and s.get("v71") and s.get("h1") == 1)
    check("preflight 2.10.71 served (%s)" % tag, ok,
          {"path": s.get("path"), "pre": s.get("pre"), "v71": s.get("v71"), "h1": s.get("h1")})
    return s


# ===========================================================================
# 待办20 — the current item is marked, and marked correctly
# ===========================================================================
def marks(path, tag, label=None):
    """Exactly one link marked, pointing where the rule says, with the right
    aria-current value -- and no half-marked link anywhere.

    The comparison is on the (href, aria-current) PAIR, so "the right value on
    the wrong link" fails just as loudly as "the wrong value on the right link".
    """
    st = ev(NAVSTATE)
    want = expect(path)
    check("%s: the menu is the 7 top-level items and the 9 in the dropdown" % tag,
          st.get("n") == 16 and st.get("nTop") == 7 and st.get("nSub") == 9,
          {"links": st.get("n"), "top": st.get("nTop"), "sub": st.get("nSub")})
    got = [[a[0], a[1]] for a in st.get("active") or []]
    if want is None:
        check("%s: a page the menu does not offer carries no mark at all" % tag,
              got == [] and st.get("aria") == [],
              {"active": got, "aria": st.get("aria")})
    else:
        check("%s: exactly one link is marked, and it points at %s" % (tag, want[0]),
              got == [list(want)], {"want": list(want), "got": got})
        check("%s: and it announces aria-current=%r" % (tag, want[1]),
              st.get("aria") == [list(want)], {"want": list(want), "got": st.get("aria")})
        check("%s: the mark sits on a link that has words in it" % tag,
              bool(st.get("active")) and len(st["active"][0][2]) > 0,
              st.get("active"))
        if label:
            check("%s: and those words are the menu item's own label, %r" % (tag, label),
                  st["active"][0][2] == label,
                  {"got": st["active"][0][2], "want": label})
    check("%s: no link is half-marked (class without aria, or aria without class)" % tag,
          st.get("both") == 0 and st.get("only") == 0,
          {"classOnly": st.get("both"), "ariaOnly": st.get("only")})
    check("%s: and no second link sharing that href is marked" % tag,
          st.get("eachTouchedTwice") == 0, st.get("eachTouchedTwice"))
    return st


def section_owns_the_leaf(tag, leaf, label=None):
    """On a page inside the dropdown, the OWNER is current and the leaf is not.

    This is the whole point of the prune: the mark names the section the visitor
    is under, which is what the breadcrumb says too. Without the prune the ninth
    dropdown link would light up instead, so the bar would announce a page the
    visitor is on while the visible label named something else entirely.
    """
    st = ev(NAVSTATE)
    want = expect(leaf)
    got = [[a[0], a[1]] for a in st.get("active") or []]
    check("%s: the dropdown's own %s link is NOT the one marked" % (tag, leaf),
          leaf not in [a[0] for a in got], {"marked": got})
    check("%s: the mark is on the top-level item that owns it" % tag,
          got == [list(want)], {"want": list(want), "got": got})
    if label:
        check("%s: so the bar says %r while the visitor reads %s" % (tag, label, leaf),
              bool(st.get("active")) and st["active"][0][2] == label,
              {"got": st.get("active")})
    check("%s: and it announces aria-current='true' — a section, not the page itself" % tag,
          st.get("aria") == [list(want)] and want[1] == 'true',
          {"want": list(want), "got": st.get("aria")})
    return st


def paints(tag):
    """The six marks, as painted, plus the control."""
    ev("window.__sfBase = document.querySelector('header.sf-header').className;")
    base = ev("window.__sfBase")
    check("%s: the served header carries the shipped default, underline" % tag,
          isinstance(base, str) and 'sf-header--nav-underline' in base, base)
    got = {}
    leak = 0
    for slug in SLUGS:
        ev("window.__sfSet = %s; window.__sfSet(%s);" % (SETCLASS, json.dumps(slug)))
        time.sleep(SETTLE)
        r = ev(PAINT)
        got[slug] = r.get("act")
        leak = max(leak, r.get("hoverLeak") or 0)
    ev("window.__sfSet('underline');")
    check("%s: nothing painted below is a hover value" % tag, leak == 0, leak)

    for slug in SLUGS:
        want = list(VARIANTS[slug])
        check("%s: `%s` paints exactly what it declares" % (tag, slug),
              got.get(slug) == want, {"want": want, "got": got.get(slug)})

    check("%s: every mark paints something the control does not" % tag,
          all(got.get(s) != got.get('none') for s in SLUGS[1:]),
          {s: got.get(s) for s in SLUGS})
    sigs = [tuple(got.get(s) or []) for s in SLUGS[1:]]
    check("%s: and the six marks are six DIFFERENT paints" % tag,
          len(set(sigs)) == 6, {s: got.get(s) for s in SLUGS[1:]})
    # The invariant, and the one assertion here that is not a transcribed value.
    # It is what the missing `borderLeftColor` column should have been saying all
    # along: a mark may not reserve a rule and leave it transparent.
    dead = {s: uncoloured(got.get(s)) for s in SLUGS if uncoloured(got.get(s))}
    check("%s: no mark reserves a rule and paints it transparent" % tag, not dead, dead)
    return got


# Which channel each mark is DRAWN with, and the value it must reach inside the
# phone drawer. One channel per mark on purpose: a phone row is a full-width
# row, so `paddingLeft` and `borderRadius` no longer say anything, and the row
# rule sets `font-weight: 600` on EVERY row, which kills the weight channel
# outright. The bar's nine-value signature therefore cannot be reused here —
# asserting it would be asserting something that is no longer meaningful — and
# what must still hold is the claim the visitor cares about: the current row is
# tellable from an unmarked one, through the channel the chosen mark draws with.
DRAWER_DIM = {
    'underline':  (P_BBW,  '2px'),
    'bg':         (P_BG,   'rgba(255, 255, 255, 0.15)'),
    'thick-line': (P_BBW,  '4px'),
    'color':      (P_COLOR, 'rgb(90, 183, 53)'),
    'left-line':  (P_BLC,  'rgb(255, 255, 255)'),
    'pill':       (P_BG,   'rgba(90, 183, 53, 0.9)'),
}


def drawer_marks(tag):
    """The current item, read back inside the OPEN drawer at 375.

    This exists because the class-and-aria assertion below it passed while four
    of the six marks were invisible on a phone — including the shipped default.
    `is-active` is true of a link with no rule behind it, and the drawer draws
    its own rows: its row rule is five classes deep and its modal colour rule
    four, against three for every rule the marks are written with, so the mark
    lost the border it draws with and the colour it draws with while keeping its
    class name.

    The `none` control is asserted to be INDISTINGUISHABLE, and that is what
    makes the six assertions after it mean something: if the read were blank,
    `none` would pass and so would nothing else; if the read had landed on some
    other element, `none` would fail. Both directions are covered, and the
    caller has already proved WHICH artifact is being read.
    """
    ev("window.__sfSet = %s;" % SETCLASS)
    ev("window.__sfBase = document.querySelector('header.sf-header').className;")
    base = ev("window.__sfBase")
    if 'sf-header--nav-' not in (base or ''):
        check("%s: the drawer probe starts from a header that carries a mark" % tag,
              False, base)
        return {}
    seen = {}
    for slug in SLUGS:
        ev("window.__sfSet(%s);" % json.dumps(slug))
        time.sleep(SETTLE)
        seen[slug] = ev(PAINT)
    ev("window.__sfSet('underline');")
    time.sleep(SETTLE)

    def cells(slug):
        r = seen.get(slug) or {}
        return (r.get('act') or []), (r.get('sib') or [])

    check("%s: every read found both a marked row and an unmarked one" % tag,
          all(cells(s)[0] and cells(s)[1] for s in SLUGS),
          {s: [bool(cells(s)[0]), bool(cells(s)[1])] for s in SLUGS})

    def dims(slug):
        a, b = cells(slug)
        a = list(a) + [None] * (9 - len(a))
        b = list(b) + [None] * (9 - len(b))
        return sorted(i for i in range(9) if a[i] != b[i])

    check("%s: with no mark chosen the drawer's own rows are uniform" % tag,
          dims('none') == [], dims('none'))

    def is_vis(slug):
        a, b = cells(slug)
        i, _ = DRAWER_DIM[slug]
        return a[i] != b[i]

    bad = {}
    for slug, (i, want) in DRAWER_DIM.items():
        a, b = cells(slug)
        if a[i] != want or b[i] == want:
            bad[slug] = {"channel": i, "want": want,
                         "marked": a[i], "unmarked": b[i]}
    check("%s: each of the six marks reaches its own channel, and only its own" % tag,
          not bad, bad)

    # The claim the class name could not make: a visitor can SEE it.
    invisible = [s for s in DRAWER_DIM if not is_vis(s)]
    check("%s: and no mark is invisible — the marked row differs from an unmarked one"
          % tag, not invisible,
          {"invisible": invisible, "dims": {s: dims(s) for s in SLUGS}})

    # ...and the mark may not take the drawer's own furniture away with it. Each
    # mark's "reserve the space, hide the paint" rule is `:not(.is-active)` and so
    # is the drawer's row rule — five classes each — and the mark's comes later in
    # the sheet, so it won on order and recoloured the row separator to
    # transparent on every row that is not current. That is a phone-only
    # regression the class assertion cannot see, and one this assertion names.
    hair = {s: cells(s)[1][P_BBC] for s in SLUGS}
    check("%s: and an unmarked row keeps the drawer's own separator" % tag,
          all(v == 'rgba(255, 255, 255, 0.14)' for v in hair.values()), hair)

    dead = {s: uncoloured(cells(s)[0]) for s in SLUGS if uncoloured(cells(s)[0])}
    check("%s: and the drawer paints no reserved rule transparent either" % tag,
          not dead, dead)
    return seen


# ===========================================================================
# 待办10 — the gap, at the three breakpoints
# ===========================================================================
def gap_at(path, w, tag, want_hh=None, want_items=7, bar=True):
    """The gap at one width.

    `bar` says whether the desktop container is the thing on screen. Below the
    hamburger breakpoint it is `display: none`, so every `li` measures 0 x 0 and
    "the gaps between them are 20px" degenerates into six zeroes -- an assertion
    that passes for the wrong reason whichever way it is written. The gap is
    still declared and still computable there (both axes read 20px), but the
    claim worth making is "the drawer shows it", and that is made in the drawer
    section with the drawer open.
    """
    open_at(path, w)
    served(path, "%s@%d" % (tag, w))
    g = ev(NAVGEOM)
    check("%d: the menu's items sit 20px apart, in both axes" % w,
          g.get("colGap") == "20px" and g.get("rowGap") == "20px",
          {"colGap": g.get("colGap"), "rowGap": g.get("rowGap")})
    if bar:
        check("%d: and every one of the %d gaps measures 20px" % (w, want_items - 1),
              len(g.get("steps", [])) == want_items - 1
              and all(abs(s - 20) <= 1.0 for s in g.get("steps", [])),
              g.get("steps"))
        check("%d: the seven items share one flex line" % w,
              g.get("oneRow") is True, [g.get("oneRow"), g.get("steps")])
    else:
        check("%d: the menu is behind a burger, and that is why the bar has no gaps to measure" % w,
              g.get("hamb") is True and g.get("cont") is False,
              {"hamburger": g.get("hamb"), "container": g.get("cont")})
    if want_hh is not None:
        check("%d: the header's height is the 2.10.69 value, %dpx" % (w, want_hh),
              g.get("hH") == want_hh, {"hH": g.get("hH"), "live": want_hh})
    check("%d: nothing overflows sideways" % w,
          (g.get("sw") or 0) <= (g.get("iw") or 0) + 1,
          {"scroll": g.get("sw"), "inner": g.get("iw")})
    return g


# ===========================================================================
# 待办15 — the facts band joins the gutter
# ===========================================================================
def facts_at(w, want_pad, want_neigh):
    """The band, at one width. `want_neigh` is the measured answer to "does the
    rest of the page put its content here too?" -- True only where it does.

    Measured 2026-09-23, the neighbours' first content pixel at each width:

        1440  [0, 120, 120, 88]   the hero and the formulas band both at 120
        1280  [0,  40,  40,   8]  both at 40
        1240  [0,  20,  38,  38]  both at 38
        1200  [0,   0,  38,  38]  both at 38
        1024  [0,  20,  38,  38]  the hero at 20, the formulas band at 38

    So below 1024 the page does NOT have one gutter: the hero already sits at 20
    and the formulas band still sits at 38, and the facts band's 20 (the number
    the brief names for that breakpoint) matches one neighbour and not the
    other. Asserting "it matches its neighbours" down there would be asserting
    a fact that is not true, so the claim is scoped to where it holds -- and the
    divergence is reported rather than hidden by a loose `>=` test.
    """
    pad = float(want_pad.rstrip("px"))
    open_at("/products/soft-chews/", w)
    served("/products/soft-chews/", "facts@%d" % w)
    f = ev(FACTS)
    check("%d: the facts band is still there" % w, f.get("present") is True, f.get("present"))
    check("%d: its content sits on the %s gutter" % (w, want_pad),
          f.get("padL") == want_pad and f.get("padR") == want_pad,
          {"padL": f.get("padL"), "padR": f.get("padR"), "want": want_pad})
    check("%d: the band's own box is still full-bleed, because it draws the hairlines" % w,
          f["own"]["boxL"] <= 1 and f["own"]["boxR"] >= w - 1,
          {"boxL": f["own"]["boxL"], "boxR": f["own"]["boxR"], "vw": w})
    check("%d: its content starts exactly on the gutter" % w,
          abs(f.get("firstL", -99) - (f["own"]["boxL"] + pad)) <= 1,
          {"firstL": f.get("firstL"), "want": f["own"]["boxL"] + pad})
    # space-between plus the gutter means the first item touches the LEFT
    # content edge and the last one touches the RIGHT content edge. Asserting
    # the touch is what separates "the row moved in" from "the row was merely
    # padded": a one-sided pad would leave one end short.
    check("%d: the row is spread across the gutter, edge to edge" % w,
          f.get("justify") == "space-between"
          and abs(f.get("minL", -99) - (f["own"]["boxL"] + pad)) <= 1
          and abs(f.get("maxR", -99) - (f["own"]["boxR"] - pad)) <= 1,
          {"justify": f.get("justify"), "minL": f.get("minL"), "maxR": f.get("maxR"),
           "wantL": f["own"]["boxL"] + pad, "wantR": f["own"]["boxR"] - pad})
    vals = [n["firstL"] for n in (f.get("neigh") or []) if n.get("firstL") is not None]
    if want_neigh:
        check("%d: at least two of the bands around it begin at the same x" % w,
              vals.count(f.get("firstL")) >= 2,
              {"facts": f.get("firstL"), "neighbours": vals})
    check("%d: nothing overflows sideways" % w,
          (f.get("sw") or 0) <= (f.get("iw") or 0) + 1,
          {"scroll": f.get("sw"), "inner": f.get("iw")})
    return f


def main():
    # `--only paint` / `--only drawer` exist so a single section can be driven
    # against a build that is NOT the one the whole suite grades -- which is how
    # the two defects this batch turned up were shown to be real: the same named
    # assertions were run against the pre-fix copy and failed there.
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    def want(name):
        return only in (None, "all", name)

    session()

    # ===================== 待办20 — the mark ==========================
    if want("marks"):
        for path, why, label in PAGES:
            open_at(path, 1440)
            served(path, path)
            if path == '/products/soft-chews/':
                section_owns_the_leaf(path, path, label)
            elif path == '/zh/formulas/':
                section_owns_the_leaf(path, path)
            else:
                marks(path, path, label)
            print("      (%s)" % why)

    if want("paint"):
        open_at('/about/', 1440)
        served('/about/', 'paint')
        paints('EN@1440')

    # ===================== 待办10 — the gap ==========================
    bar = {}
    if want("gap"):
        for w in (1440, 768, 375):
            bar[w] = gap_at('/products/soft-chews/', w, 'gap', want_hh=LIVE_HH[w], bar=(w > 768))
        check("1440: all three header children share one line, as on 2.10.69",
              bar[1440].get("logoNav") is True and bar[1440].get("navCta") is True,
              {"logoNav": bar[1440].get("logoNav"), "navCta": bar[1440].get("navCta")})

        # The measurement above the breakpoints is what keeps "20px" honest: the
        # same number has to hold while the header is still one row, and has to be
        # visible in the drawer once it is not.
        g1000 = gap_at('/products/soft-chews/', 1000, 'gap')
        check("1000: the header still holds logo | nav | cta on one row (the new floor)",
              g1000.get("hH") == 81 and g1000.get("logoNav") is True
              and g1000.get("navCta") is True,
              {"hH": g1000.get("hH"), "logoNav": g1000.get("logoNav"),
               "navCta": g1000.get("navCta")})
        g999 = gap_at('/products/soft-chews/', 999, 'gap')
        check("999: one pixel narrower and the header takes a second row — the measured "
              "floor, 60px of extra nav width being why",
              g999.get("hH") == 139 and g999.get("logoNav") is True
              and g999.get("navCta") is False,
              {"hH": g999.get("hH"), "logoNav": g999.get("logoNav"),
               "navCta": g999.get("navCta")})
        check("999: ...while the menu's own seven items still fit one line, so the "
              "gap that moved is the header's, not the bar's",
              g999.get("oneRow") is True and all(abs(s - 20) <= 1 for s in g999.get("steps") or []),
              {"oneRow": g999.get("oneRow"), "steps": g999.get("steps")})

    # ===================== the drawer at 375 =========================
    if want("drawer"):
        open_at('/products/soft-chews/', 375)
        served('/products/soft-chews/', 'drawer@375')
        before = ev(DRAWER)
        check("375: the drawer starts closed and the bar shows a burger, not the menu",
              before.get("open") is False and ev(NAVGEOM).get("hamb") is True
              and ev(NAVGEOM).get("cont") is False,
              {"open": before.get("open")})
        ev("document.querySelector('.wp-block-navigation__responsive-container-open').click();")
        time.sleep(0.9)
        d = ev(DRAWER)
        check("375: opening it stacks the menu down the page", d.get("open") is True
              and d.get("ulDir") == "column" and d.get("n") == 7,
              {"open": d.get("open"), "dir": d.get("ulDir"), "n": d.get("n")})
        # Each row's own height, not the first row's taken as a stand-in for all
        # of them. The marked row carries the mark's own border and is
        # legitimately 1px taller than its neighbours; the earlier form of this
        # assertion measured the step against `itemH` (row 0, which happens to BE
        # the marked one here) and so passed at exactly its +/-1 tolerance — a
        # pass that would have flipped to a fail if any later edit added a second
        # pixel. The claim is "every row sits one 20px gap below the one above
        # it", so it is measured row by row.
        # One gap per step: step[i] is the distance from row i's top to row i+1's
        # top, so subtracting row i's OWN height leaves the gap after row i.
        steps = d.get("steps") or []
        hs = d.get("hs") or []
        gaps = [round(steps[i] - hs[i], 1) for i in range(len(steps))]
        check("375: the drawer's items are 20px apart — the same gap, on the other axis",
              d.get("colGap") == "20px" and d.get("rowGap") == "20px"
              and len(gaps) == 6 and all(abs(g - 20) <= 0.1 for g in gaps),
              {"rowGap": d.get("rowGap"), "hs": hs, "steps": steps, "gaps": gaps})
        check("375: and the drawer fits the phone instead of scrolling sideways",
              (d.get("sw") or 0) <= (d.get("iw") or 0) + 1,
              {"scroll": d.get("sw"), "inner": d.get("iw")})
        st = ev(NAVSTATE)
        check("375: the current item is marked in the drawer too",
              [[a[0], a[1]] for a in st.get("active") or []] == [['/products/', 'true']]
              and st["active"][0][2] == 'Products',
              st.get("active"))
        # ...and the class name above is NOT the claim that matters. This is.
        drawer_marks('drawer@375')
        ev("document.querySelector('.wp-block-navigation__responsive-container-close').click();")
        time.sleep(0.6)

    # ===================== 待办15 — the gutter =======================
    if want("facts"):
        # The ladder the brief names: the content column's own edge at 1440, the
        # 38px floor under it, and 20px once the page is a tablet. `want_neigh` is
        # the measured answer to "does the rest of the page put its content here",
        # and it is only True where that is actually so.
        for w, pad, neigh in ((1440, "120px", True), (1280, "40px", True),
                              (1240, "38px", True), (1200, "38px", True),
                              (1024, "20px", False), (768, "20px", False),
                              (375, "20px", False)):
            facts_at(w, pad, neigh)

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
