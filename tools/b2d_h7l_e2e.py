#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7l E2E — the ladder heads the column, and the cert chips are cards.

Target: the PREFLIGHT copy (2.10.73). Dev still serves 2.10.72 for this batch
(the pull is a separate, user-authorised step), so the candidate exists on the
box only as `sinofresh-theme-preflight`, behind the `X-SF-preflight: 1` header.

`--live` drops the header and drives dev's own 2.10.72. The two meanings of that
run are different for the two halves of this batch, and both are wanted:

  * 待办25 and 待办4 are NEW, so their checks must be RED on live — that is the
    run that proves this script can fail.
  * 待办1 and 待办2 were already true on live when the batch opened. Their
    checks therefore PASS on live, and that is the evidence for the report: the
    user's "Custom quantity" screenshot was a deploy-lag artifact, not a defect
    waiting to be fixed. A `--live` run that reddened these two would mean the
    script was reading something other than the artifact it names.

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the one
`set headers` call.

What each assertion is anchored to
----------------------------------
待办1  the three breaks, read three ways that fail independently: the option's
       own visible text (`sf-tier__range`), the radio group's values, and the
       dialog's reprint of the ladder — plus the absence claim, `Custom
       quantity`, asserted on `innerText` rather than on the raw bytes, because
       the placeholder only matters where a visitor could read it.

待办2  the column's foot: the text, the attribute, and the href that has to work
       with the script absent — and then a real click that must open the dialog,
       read TWICE, because the open flag is set inside a requestAnimationFrame
       and a same-tick read reports "did not open" for a dialog that is opening.

待办25 the ladder's address, in two independent currencies: DOM order (document
       position) and geometry (its own top against Flavor's), because a CSS
       `order` or a float could satisfy one without the other. The brief says to
       move it and keep the style, so the style is measured too — and it is
       measured on the TWO elements it actually lives on, not on one element
       guessed from its name: the ladder's price is 17px/700 and has been since
       H7i wrote it, while the "32px 加粗" the brief names is the column's own
       h1 above it. An earlier version of this check asserted 32px on
       `.sf-tier__price` and went red against a correct product.

待办4  the six cards, measured rather than read: the surface, the hairline, the
       radius and the padding from computed style; the 40px icon against the
       card's own centre line; the column count from the badges' DISTINCT lefts
       and tops rather than from `grid-template-columns` alone; and the band's
       height, reported at all three widths because the height is the thing the
       brief accepted a change in.
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
HOME = "/"

RANGES = ["10-99", "100-999", "\u22651,000"]
PRICES = ["US$3.88", "US$3.58", "US$3.28"]
CHIP_NAMES = ['FDA Registered', 'cGMP Compliant', 'ISO 9001 Certified',
              'FSSC 22000 Certified', 'HACCP Certified', 'BRC Certified']

# The brief's 待办4 numbers, as the browser reports them back.
CARD_BG = "rgb(243, 246, 244)"      # #F3F6F4 Mist
CARD_LINE = "rgb(220, 226, 223)"    # #DCE2DF Line
CARD_RADIUS = "8px"
CARD_PAD = "16px"
ICON_PX = 40.0
CARD_GAP = "16px"

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


def served(path, why, live=False):
    """Which artifact answered, asserted BEFORE anything is asserted about it."""
    v = "2.10.72" if live else "2.10.73"
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, title: document.title, theme,
               pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
               ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               h1: document.querySelectorAll('h1').length };
    })()""")
    want_pre = not live
    ok = (isinstance(s, dict) and s.get("ver") == v and s.get("h1") == 1
          and (s.get("pre") is True) == want_pre)
    check("the %s theme answered (%s)  [%s]" % (v, path, why), ok, s)
    return s


# ------------------------------------------------------------------ probes

# 待办1 + 待办2 + 待办25 in one read, so the three claims are all taken from
# the same rendered state rather than from three moments a re-render could
# separate.
DETAIL_PROBE = """(() => {
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             l: +r.left.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
  const cs = e => getComputedStyle(e);
  const q = (s, r) => (r || document).querySelector(s);
  const qa = (s, r) => Array.from((r || document).querySelectorAll(s));
  const g = q('[data-sf-config-group="pricing"]');
  const gf = q('[data-sf-config-group="flavor"]');
  const intro = q('.sf-fdetail2__intro');
  const cta = q('a.sf-fdetail2__cta');
  const list = q('.sf-fdetail-config__list');
  const groups = qa('.sf-fdetail-config__group');
  const tiers = g ? qa('.sf-tier', g) : [];
  const opts = g ? qa('.sf-fdetail-config__input', g) : [];
  const rangeBox = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             color: cs(e).color, display: cs(e).display, vis: cs(e).visibility,
             op: cs(e).opacity }; };
  const pos = e => e ? Array.from(document.querySelectorAll('*')).indexOf(e) : -1;
  const priceEl = tiers.length ? q('.sf-tier__price', tiers[0]) : null;
  return {
    path: location.pathname,
    // --- 待办25: where the group is ---
    domIntro: pos(intro), domPricing: pos(g), domFlavor: pos(gf),
    topIntro: intro ? R(intro).t : null,
    topPricing: g ? R(g).t : null,
    topFlavor: gf ? R(gf).t : null,
    sideTop: q('.sf-fdetail2__side') ? R(q('.sf-fdetail2__side')).t : null,
    // the style the brief says to keep
    rowCols: g && q('.sf-fdetail-config__tiers', g)
             ? cs(q('.sf-fdetail-config__tiers', g)).gridTemplateColumns : null,
    cols: tiers.length ? cs(q('.sf-fdetail-config__tiers', g)).gridTemplateColumns.split(' ').length : null,
    tierCount: tiers.length,
    // --- 待办1: the three breaks, three ways ---
    ranges: tiers.map(t => q('.sf-tier__range', t).textContent.trim()),
    prices: tiers.map(t => q('.sf-tier__price', t).textContent.trim()),
    units: tiers.map(t => q('.sf-tier__unit', t).textContent.trim()),
    rangePaint: tiers.map(t => rangeBox(q('.sf-tier__range', t))),
    priceSize: priceEl ? cs(priceEl).fontSize : null,
    priceWeight: priceEl ? cs(priceEl).fontWeight : null,
    // The brief for 待办25 says to KEEP the style, and spells it "三档横排、
    // 32px 加粗". The three-in-a-row is the ladder; the 32px bold is not the
    // ladder's price (that has been 17px/700 since H7i wrote it) — it is the
    // column's own h1, `.sf-fdetail2__title`, sitting directly above the ladder
    // and moved by nothing in this batch. Both are read, because the claim is
    // that the move disturbs neither.
    titleSize: q('.sf-fdetail2__title') ? cs(q('.sf-fdetail2__title')).fontSize : null,
    titleWeight: q('.sf-fdetail2__title') ? cs(q('.sf-fdetail2__title')).fontWeight : null,
    titleText: q('.sf-fdetail2__title') ? q('.sf-fdetail2__title').textContent.trim() : null,
    radioNames: Array.from(new Set(opts.map(o => o.name))),
    radioValues: opts.map(o => o.value),
    checked: opts.filter(o => o.checked).length,
    metaLine: g && q('.sf-fdetail-config__meta', g)
              ? q('.sf-fdetail-config__meta', g).textContent.trim() : null,
    samplePrice: g && q('.sf-fdetail-config__sample-price', g)
                 ? q('.sf-fdetail-config__sample-price', g).textContent.trim() : null,
    customQty: document.body.innerText.indexOf('Custom quantity') >= 0,
    // --- 待办2: the column's foot ---
    ctaTag: cta ? cta.tagName.toLowerCase() : null,
    ctaText: cta ? cta.textContent.trim() : null,
    ctaHref: cta ? cta.getAttribute('href') : null,
    ctaOpen: cta ? cta.hasAttribute('data-sf-inquiry-open') : null,
    ctaBox: cta ? R(cta) : null,
    requestSample: document.body.innerText.indexOf('Request Sample') >= 0,
    // --- the fold, which is where the move has a second-order effect ---
    folded: list ? list.classList.contains('sf-config-folded') : null,
    groupNames: groups.map(x => x.getAttribute('data-sf-config-group')),
    groupDisplays: groups.map(x => cs(x).display),
    foldBtn: q('.sf-fdetail-config__fold')
             ? { text: q('.sf-fdetail-config__fold').textContent.trim(),
                 display: cs(q('.sf-fdetail-config__fold')).display } : null,
  };
})()"""

MODAL_NOW = """(() => {
  const m = document.querySelector('.sf-inquiry-modal');
  const rows = Array.from(document.querySelectorAll('.sf-inquiry-modal__term'))
    .map((t, i) => [t.textContent.trim(),
                    (document.querySelectorAll('.sf-inquiry-modal__value')[i] || {}).textContent]);
  const qty = rows.find(r => /Quantity/i.test(r[0]));
  return { exists: !!m, hidden: m ? m.hidden : null,
           isOpen: m ? m.classList.contains('is-open') : null,
           ariaHidden: m ? m.getAttribute('aria-hidden') : null,
           qty: qty ? qty[1] : null, rows: rows.length };
})()"""

# 待办4 — the band, measured. The column count comes from DISTINCT lefts, not
# from the declaration: a grid whose children all wrapped into one column has
# the same `grid-template-columns` as one that filled three.
STRIP_PROBE = """(() => {
  const R = e => { const r = e.getBoundingClientRect();
    return { w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             l: +r.left.toFixed(1), t: +r.top.toFixed(1), r: +r.right.toFixed(1),
             b: +r.bottom.toFixed(1) }; };
  const cs = e => getComputedStyle(e);
  const strip = document.querySelector('.sf-certstrip');
  const row = strip ? strip.querySelector('.sf-certstrip__row') : null;
  const cards = strip ? Array.from(strip.querySelectorAll('.sf-certstrip__badge')) : [];
  const one = cards[0];
  const oneIcon = one ? one.querySelector('.sf-certstrip__icon') : null;
  const oneName = one ? one.querySelector('.sf-certstrip__name') : null;
  const lede = strip ? strip.querySelector('.sf-certstrip__lede') : null;
  const more = strip ? strip.querySelector('.sf-certstrip__more a') : null;
  const uniq = a => Array.from(new Set(a.map(v => Math.round(v))));
  const section = strip ? strip.closest('section') : null;
  return {
    count: cards.length,
    names: cards.map(c => (c.querySelector('.sf-certstrip__name') || {}).textContent),
    iconCount: strip ? strip.querySelectorAll('.sf-certstrip__icon').length : 0,
    rowGap: row ? cs(row).gap : null,
    rowCols: row ? cs(row).gridTemplateColumns : null,
    lefts: uniq(cards.map(c => R(c).l)),
    tops: uniq(cards.map(c => R(c).t)),
    cardBg: one ? cs(one).backgroundColor : null,
    cardBorderW: one ? cs(one).borderTopWidth : null,
    cardBorderC: one ? cs(one).borderTopColor : null,
    cardRadius: one ? cs(one).borderRadius : null,
    cardPad: one ? cs(one).padding : null,
    cardBox: one ? R(one) : null,
    iconBox: oneIcon ? R(oneIcon) : null,
    iconW: oneIcon ? cs(oneIcon).width : null,
    iconH: oneIcon ? cs(oneIcon).height : null,
    iconLeftOfName: (oneIcon && oneName) ? R(oneIcon).r <= R(oneName).l : null,
    nameBox: oneName ? R(oneName) : null,
    nameLines: (oneIcon && oneName)
               ? Math.round(R(oneName).h / parseFloat(cs(oneName).lineHeight)) : null,
    nameSize: oneName ? cs(oneName).fontSize : null,
    nameIsTwoLines: (oneIcon && oneName)
                    ? Math.round(R(oneName).h / parseFloat(cs(oneName).lineHeight)) <= 2 : null,
    lede: lede ? { text: lede.textContent.trim(), align: cs(lede).textAlign,
                   box: R(lede) } : null,
    more: more ? { text: more.textContent.trim(), box: R(more) } : null,
    stripBox: strip ? R(strip) : null,
    sectionPad: section ? cs(section).paddingTop : null,
  };
})()"""


def strip_checks(tag, s):
    check("待办4 six cards, not twelve chips  [%s]" % tag,
          s.get("count") == 6 and s.get("iconCount") == 6, s)
    check("待办4 the names survive verbatim  [%s]" % tag,
          s.get("names") == CHIP_NAMES, s.get("names"))
    check("待办4 the card surface is Mist, hairline, 8px, 16px  [%s]" % tag,
          s.get("cardBg") == CARD_BG and s.get("cardBorderW") == "1px"
          and s.get("cardBorderC") == CARD_LINE and s.get("cardRadius") == CARD_RADIUS
          and s.get("cardPad") == CARD_PAD,
          {k: s.get(k) for k in ("cardBg", "cardBorderW", "cardBorderC",
                                 "cardRadius", "cardPad")})
    check("待办4 the icon is 40x40 and left of the text  [%s]" % tag,
          s.get("iconW") == "40px" and s.get("iconH") == "40px"
          and s.get("iconLeftOfName") is True
          and abs(s["iconBox"]["h"] - ICON_PX) < 0.6,
          {k: s.get(k) for k in ("iconW", "iconH", "iconLeftOfName")})
    check("待办4 the text runs to at most two lines  [%s]" % tag,
          s.get("nameIsTwoLines") is True, {"lines": s.get("nameLines"),
                                           "size": s.get("nameSize")})
    check("待办4 the chips sit on a 16px gutter  [%s]" % tag,
          s.get("rowGap") == CARD_GAP, s.get("rowGap"))
    check("待办4 the lede and the link are still there  [%s]" % tag,
          bool(s.get("lede")) and "Certified to the standards" in (s["lede"]["text"] or "")
          and bool(s.get("more")) and "View all certifications" in (s["more"]["text"] or ""),
          {"lede": s.get("lede"), "more": s.get("more")})
    check("待办4 the band stays in its 32px section  [%s]" % tag,
          s.get("sectionPad") == "32px", s.get("sectionPad"))


def main():
    live = "--live" in sys.argv

    # ---------------------------------------------------------- detail page
    session(live)
    open_at(DETAIL, 1440)
    served(DETAIL, "item 1/2/3", live)
    d = ev(DETAIL_PROBE)

    # 待办1 — three ways, plus the absence claim the report was about.
    check("待办1 the ladder holds exactly three breaks",
          d.get("tierCount") == 3, d.get("tierCount"))
    check("待办1 the three ranges read as the brief writes them",
          d.get("ranges") == RANGES, d.get("ranges"))
    check("待办1 the three prices ride with them",
          d.get("prices") == PRICES, d.get("prices"))
    check("待办1 the breaks are PAINTED, not merely present",
          all(r["display"] != "none" and r["vis"] != "hidden" and r["op"] != "0"
              and r["w"] > 20 and r["h"] > 6 for r in d.get("rangePaint") or [])
          and len(d.get("rangePaint") or []) == 3,
          d.get("rangePaint"))
    check("待办1 the radio group carries the same three values",
          d.get("radioNames") == ["sf-config-pricing"] and d.get("radioValues") == RANGES,
          {"names": d.get("radioNames"), "values": d.get("radioValues")})
    check("待办1 the echo line spells all three out",
          all(r in (d.get("metaLine") or "") for r in RANGES), d.get("metaLine"))
    check("待办1 no row falls back to the placeholder",
          d.get("customQty") is False, d.get("customQty"))
    check("待办1 the sample row is untouched",
          d.get("samplePrice") == "US$50.00", d.get("samplePrice"))

    # 待办25 — the address, in DOM order and in geometry, plus the kept style.
    check("待办25 the ladder follows the intro in document order",
          0 <= d.get("domIntro") < d.get("domPricing"), 
          {"intro": d.get("domIntro"), "pricing": d.get("domPricing")})
    check("待办25 ...and precedes Flavor",
          d.get("domPricing") < d.get("domFlavor"),
          {"pricing": d.get("domPricing"), "flavor": d.get("domFlavor")})
    check("待办25 ...and it is above it on screen, under the intro",
          d.get("topIntro") < d.get("topPricing") < d.get("topFlavor"),
          {"intro": d.get("topIntro"), "pricing": d.get("topPricing"),
           "flavor": d.get("topFlavor")})
    check("待办25 the ladder keeps its three-column card row",
          d.get("cols") == 3, {"cols": d.get("cols"), "css": d.get("rowCols")})
    # The brief's "32px 加粗" belongs to the column's h1, not to the ladder's
    # price. Asserting it on `.sf-tier__price` — the first element with "price"
    # in its name — was the mis-fingered version of this check: it went red on a
    # product that was correct, because the element it named has been 17px since
    # H7i introduced it and the batch is forbidden to touch its style anyway.
    # Split into the two elements that actually carry the claim, and keep both
    # numbers visible in the log so the next reader can see which is which.
    check("待办25 the column's 32px bold title survives the move",
          d.get("titleSize") == "32px" and d.get("titleWeight") in ("700", "bold"),
          {"size": d.get("titleSize"), "weight": d.get("titleWeight"),
           "text": d.get("titleText")})
    check("待办25 ...and the ladder's own price keeps the voice H7i gave it",
          d.get("priceSize") == "17px" and d.get("priceWeight") in ("700", "bold"),
          {"size": d.get("priceSize"), "weight": d.get("priceWeight")})

    # 待办2 — the button, then a real click.
    check("待办2 the column's foot is a Send Inquiry link",
          d.get("ctaTag") == "a" and d.get("ctaText") == "Send Inquiry"
          and d.get("ctaOpen") is True,
          {"tag": d.get("ctaTag"), "text": d.get("ctaText"), "open": d.get("ctaOpen")})
    check("待办2 ...whose no-script destination is the quote anchor",
          (d.get("ctaHref") or "").endswith("/contact/#quote"), d.get("ctaHref"))
    check("待办2 ...and no Request Sample text is served anywhere",
          d.get("requestSample") is False, d.get("requestSample"))
    check("待办2 ...and it is on screen, not clipped away",
          (d.get("ctaBox") or {}).get("w", 0) > 60 and (d.get("ctaBox") or {}).get("h", 0) > 20,
          d.get("ctaBox"))

    ev("document.querySelector('a.sf-fdetail2__cta').click(); 'clicked'")
    now = ev(MODAL_NOW)                       # same tick: the flag is not set yet
    time.sleep(0.8)
    then = ev(MODAL_NOW)                      # after a round trip: it is
    check("待办2 the click opens the inquiry dialog",
          then.get("exists") is True and then.get("hidden") is False
          and then.get("isOpen") is True,
          {"same_tick": now, "after": then})
    check("待办2 ...and the dialog reprints the three breaks",
          all(r in (then.get("qty") or "") for r in RANGES), then.get("qty"))
    ev("(() => { const b = document.querySelector('.sf-inquiry-modal__close');"
       "if (b) b.click(); return 'closed'; })()")
    time.sleep(0.4)

    # ------------------------------------------------- the fold, on the phone
    open_at(DETAIL, 375)
    ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } catch (e) {}"
       "return 'cleared'; })()")
    ab("reload")
    time.sleep(2.5)
    served(DETAIL, "the fold at 375", live)
    f = ev(DETAIL_PROBE)
    want = dict(zip(f.get("groupNames") or [], f.get("groupDisplays") or []))
    check("待办25 the collapsed phone summary still shows the ladder",
          f.get("folded") is True and want.get("pricing") != "none",
          {"folded": f.get("folded"), "displays": want})
    check("待办25 ...because the fold is positional: groups 4+ are the ones hidden",
          all(want.get(g) != "none" for g in ("flavor", "weight"))
          and all(want.get(g) == "none" for g in ("pack", "shape", "container")),
          want)
    check("待办25 the fold control is still a control on the phone",
          bool(f.get("foldBtn")) and f["foldBtn"].get("display") != "none",
          f.get("foldBtn"))
    check("待办1 the three breaks are painted at 375 too",
          f.get("ranges") == RANGES
          and all(r["display"] != "none" and r["w"] > 20
                  for r in f.get("rangePaint") or []),
          f.get("rangePaint"))
    # The same two numbers, read on the phone: the ladder steps down to 16px at
    # <=480 and the title to its own phone size — and both steps are the ones
    # the batch inherited, not ones it made.
    check("待办25 the ladder's phone step is still the inherited 16px",
          f.get("priceSize") == "16px" and f.get("priceWeight") in ("700", "bold"),
          {"size": f.get("priceSize"), "weight": f.get("priceWeight")})
    check("待办25 the column title keeps its 26px phone step",
          f.get("titleSize") == "26px", {"size": f.get("titleSize")})

    # ------------------------------------------------------- the cert band
    open_at(HOME, 1440)
    served(HOME, "待办4 at 1440", live)
    s1440 = ev(STRIP_PROBE)
    strip_checks("1440", s1440)
    check("待办4 three columns at 1440",
          len(s1440.get("lefts") or []) == 3 and len(s1440.get("tops") or []) == 2,
          {"lefts": len(s1440.get("lefts") or []), "tops": len(s1440.get("tops") or [])})
    check("待办4 the icon is on the card's centre line",
          abs((s1440["iconBox"]["t"] + s1440["iconBox"]["h"] / 2)
              - (s1440["cardBox"]["t"] + s1440["cardBox"]["h"] / 2)) <= 1.0,
          {"icon_cy": s1440["iconBox"]["t"] + s1440["iconBox"]["h"] / 2,
           "card_cy": s1440["cardBox"]["t"] + s1440["cardBox"]["h"] / 2})
    print("       measured band height @1440 : %.1f px (was ~155)"
          % s1440["stripBox"]["h"])
    check("待办4 the band stays a band, not a page  [1440]",
          s1440["stripBox"]["h"] <= 340, s1440["stripBox"])

    open_at(HOME, 768)
    served(HOME, "待办4 at 768", live)
    s768 = ev(STRIP_PROBE)
    strip_checks("768", s768)
    check("待办4 two columns at 768",
          len(s768.get("lefts") or []) == 2 and len(s768.get("tops") or []) == 3,
          {"lefts": len(s768.get("lefts") or []), "tops": len(s768.get("tops") or [])})
    print("       measured band height @768  : %.1f px" % s768["stripBox"]["h"])

    open_at(HOME, 375)
    served(HOME, "待办4 at 375", live)
    s375 = ev(STRIP_PROBE)
    check("待办4 two columns at 375, not one",
          len(s375.get("lefts") or []) == 2 and len(s375.get("tops") or []) == 3,
          {"lefts": len(s375.get("lefts") or []), "tops": len(s375.get("tops") or [])})
    check("待办4 ...with the icon and the padding stepped down, not the columns",
          s375.get("iconW") == "32px" and s375.get("cardPad") == "12px"
          and s375.get("rowGap") == "12px",
          {k: s375.get(k) for k in ("iconW", "cardPad", "rowGap")})
    check("待办4 the cards keep the surface at 375",
          s375.get("cardBg") == CARD_BG and s375.get("cardRadius") == CARD_RADIUS,
          {k: s375.get(k) for k in ("cardBg", "cardRadius")})
    print("       measured band height @375  : %.1f px" % s375["stripBox"]["h"])
    check("待办4 the phone band does not stack six cards  [375]",
          s375["stripBox"]["h"] <= 420, s375["stripBox"])

    # ------------------------------------------------------------ zh twin
    open_at(DETAIL_ZH, 1440)
    served(DETAIL_ZH, "the zh twin", live)
    z = ev(DETAIL_PROBE)
    check("待办1 the zh twin prints the same three breaks",
          z.get("ranges") == RANGES and z.get("customQty") is False, z.get("ranges"))
    check("待办25 the zh twin puts the ladder first as well",
          0 <= z.get("domIntro") < z.get("domPricing") < z.get("domFlavor"),
          {"intro": z.get("domIntro"), "pricing": z.get("domPricing"),
           "flavor": z.get("domFlavor")})
    check("待办25 the zh twin's title is the same 32px bold",
          z.get("titleSize") == "32px" and z.get("titleWeight") in ("700", "bold"),
          {"size": z.get("titleSize"), "weight": z.get("titleWeight"),
           "text": z.get("titleText")})
    check("待办2 the zh twin's button is the same button",
          z.get("ctaText") == "Send Inquiry" and z.get("ctaOpen") is True
          and (z.get("ctaHref") or "").endswith("/zh/contact/#quote"),
          {"text": z.get("ctaText"), "href": z.get("ctaHref")})

    # --------------------------------------------------------------- summary
    bad = [r for r in RESULTS if not r[1]]
    print("\n%s  batch H7l E2E  (%d checks, %d failed)  [%s]"
          % ("PASS" if not bad else "FAIL", len(RESULTS), len(bad),
             "LIVE 2.10.72" if live else "PREFLIGHT 2.10.73"))
    if bad:
        for n, _, det in bad:
            print("   FAIL %s  | %s" % (n, det[:200]))
    out = {"live": live, "checks": [{"name": n, "ok": o, "detail": d}
                                    for n, o, d in RESULTS],
           "ok": not bad, "total": len(RESULTS), "failed": len(bad)}
    path = "/tmp/h7l-e2e-%s.json" % ("live" if live else "pre")
    json.dump(out, open(path, "w"), indent=1)
    print("  json -> %s" % path)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
