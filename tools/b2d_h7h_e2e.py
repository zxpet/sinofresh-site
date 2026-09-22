#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7h E2E — three viewports (375 / 768 / 1440) against the preflight copy.

Session discipline (measured 2026-09-23, see user memory):
  close --all -> set headers {custom + Basic, ONE call} -> open -> set viewport -> eval.
The headers carry the Basic credentials, because `set credentials` and
`set headers` rebuild the browser context and the later one erases the former.

Every page asserts WHICH artifact served it before asserting anything about it:
the stylesheet link must name the preflight directory and ver=2.10.69.
"""
import base64
import json
import subprocess
import sys
import time

AUTH = base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
HEADERS = json.dumps({"X-SF-Preflight": "1", "Authorization": "Basic " + AUTH})
DETAIL = "https://dev.zxpet.com/formulas/calming-soft-chews/"
# The fold wants a page with MORE than three groups, or "3 of 3 visible" passes
# vacuously. soft-chews carries six.
FOLDY = "https://dev.zxpet.com/formulas/joint-support-soft-chews/"
RESULTS = []


def ab(*a, timeout=90):
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


def open_at(w, h, url=DETAIL):
    ab("open", url)
    time.sleep(2.5)
    # `set viewport` flakes right after an open (observed once: silent no-op,
    # innerWidth still 1280). Retry until the browser CONFIRMS the size.
    for attempt in range(3):
        out = ab("set", "viewport", str(w), str(h))
        time.sleep(1.0)
        got = ev("JSON.stringify({w: innerWidth, h: innerHeight})")
        if isinstance(got, dict) and got.get("w") == w and got.get("h") == h:
            return
        time.sleep(1.0)
    raise SystemExit("viewport did not take: wanted %sx%s, got %r (out=%r)"
                     % (w, h, got, out))


def served():
    """The page is the preflight candidate, not live, not a 401 sheet."""
    return ev("""(() => {
  const link = Array.from(document.querySelectorAll('link[rel=stylesheet]'))
    .map(l => l.href).find(h => h.includes('sinofresh')) || '';
  return { path: location.pathname, title: document.title,
           preflight: link.includes('-preflight') && link.includes('ver=2.10.69'),
           cfg: /config\\.js\\?ver=1\\.2\\.0/.test(document.body.innerHTML),
           gal: /formula-gallery\\.js\\?ver=2\\.2\\.0/.test(document.body.innerHTML) };
})()""")


FS = """(() => {
  const g = sel => { const el = document.querySelector(sel);
    return el ? getComputedStyle(el).fontSize : null; };
  return {
    label: g('.sf-fdetail-config__label'),
    opt: g('.sf-fdetail-config__opt'),
    meta: g('.sf-fdetail-config__meta'),
    intro: g('.sf-fdetail2__intro'),
    herometa: g('.sf-formula-hero__meta'),
    faq: g('.sf-faq details p'),
    specval: g('.sf-fdetail-specs__value'),
    cta: g('.sf-formula__cta'),
    title: g('.sf-fdetail2__title')
  };
})()"""


def num(px):
    try:
        return float(str(px).replace("px", ""))
    except Exception:
        return None


def run_375():
    print("\n===== 375x812 (phone) =====")
    open_at(375, 812)
    s = served()
    check("served = preflight candidate", s.get("preflight") and s.get("cfg") and s.get("gal"), s)

    fs = ev(FS)
    check("config label >= 14px", num(fs["label"]) >= 14, fs["label"])
    check("option text >= 16px", num(fs["opt"]) >= 16, fs["opt"])
    check("value preview / intro >= 16px",
          num(fs["intro"]) >= 16 and num(fs["herometa"]) >= 16,
          "intro=%s hero=%s" % (fs["intro"], fs["herometa"]))
    check("FAQ answer >= 16px", num(fs["faq"]) >= 16, fs["faq"])
    check("spec value >= 16px", num(fs["specval"]) >= 16, fs["specval"])
    check("CTA >= 16px", num(fs["cta"]) >= 16, fs["cta"])

    # ---- fold: 3 of the groups visible, the rest behind the button -------
    open_at(375, 812, FOLDY)
    fold = ev("""(() => {
  const list = document.querySelector('.sf-fdetail-config__list');
  const btn = document.querySelector('.sf-fdetail-config__fold');
  const groups = Array.from(list.querySelectorAll('.sf-fdetail-config__group'));
  const vis = () => groups.filter(g => getComputedStyle(g).display !== 'none').length;
  return { btn: !!btn, before: vis(), total: groups.length,
           folded: list.classList.contains('sf-config-folded') };
})()""")
    check("fold button exists, 3 of %s groups visible" % fold.get("total"),
          fold.get("btn") and fold.get("before") == 3 and fold.get("folded")
          and fold.get("total", 0) > 3, fold)

    ev("document.querySelector('.sf-fdetail-config__fold').click()")
    time.sleep(0.4)
    after = ev("""(() => {
  const list = document.querySelector('.sf-fdetail-config__list');
  return { vis: list.querySelectorAll('.sf-fdetail-config__group')
    .length - Array.from(list.querySelectorAll('.sf-fdetail-config__group'))
      .filter(g => getComputedStyle(g).display === 'none').length,
    expanded: !list.classList.contains('sf-config-folded'),
    stored: (() => { try { return sessionStorage.getItem('sf-config-fold'); }
                     catch (e) { return null; } })() };
})()""")
    check("expand shows all groups + state kept",
          after.get("vis") == fold.get("total") and after.get("expanded")
          and after.get("stored") == "open", after)

    # persistence: reload keeps it expanded
    ab("reload")
    time.sleep(2.5)
    kept = ev("""(() => {
  const list = document.querySelector('.sf-fdetail-config__list');
  const vis = Array.from(list.querySelectorAll('.sf-fdetail-config__group'))
    .filter(g => getComputedStyle(g).display !== 'none').length;
  return { vis, expanded: !list.classList.contains('sf-config-folded') };
})()""")
    check("unfolded state survives a reload", kept.get("expanded") and kept.get("vis") == fold.get("total"), kept)
    # stay unfolded: the 3-column and dot checks below need every group visible

    # ---- 3-column image pickers at 80px ---------------------------------
    grid = ev("""(() => {
  const opts = document.querySelector('[data-sf-config-group="shape"] .sf-fdetail-config__options');
  const cs = getComputedStyle(opts);
  const img = opts.querySelector('.sf-fdetail-config__img');
  const b = img.getBoundingClientRect();
  return { cols: cs.gridTemplateColumns.split(' ').length,
           img: [Math.round(b.width), Math.round(b.height)],
           gap: cs.columnGap };
})()""")
    check("shape picker is 3 columns, 80px tile, 8px gap",
          grid.get("cols") == 3 and grid.get("img") == [80, 80] and num(grid.get("gap")) <= 8, grid)

    # strip hidden, dots shown and in sync — the count is the photo count
    gal = ev("""(() => {
  const strip = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const dots = Array.from(document.querySelectorAll('.sf-gallery__dot'));
  const active = dots.findIndex(d => d.classList.contains('is-active'));
  const photos = document.querySelectorAll('.sf-gallery__slide:not(.sf-gallery__slide--video)').length;
  return { strip: strip ? getComputedStyle(strip).display : null,
           n: dots.length, photos, active };
})()""")
    check("strip hidden, %s dots (= photos) shown, first active" % gal.get("n"),
          gal.get("strip") == "none" and gal.get("n") == gal.get("photos")
          and gal.get("active") == 0, gal)

    # swipe: a synthetic horizontal pointer drag on the stage
    sw = ev("""(() => new Promise(res => {
  const stage = document.querySelector('.sf-gallery__stage');
  const b = stage.getBoundingClientRect();
  const y = b.y + b.height / 2;
  /* buttons: 1 is load-bearing — the handler ignores moves with no button
     held, and a synthetic PointerEvent defaults to buttons = 0. */
  const opts = { bubbles: true, pointerId: 7, isPrimary: true, pointerType: 'touch', buttons: 1 };
  stage.dispatchEvent(new PointerEvent('pointerdown',
    Object.assign({ clientX: b.x + b.width * 0.8, clientY: y }, opts)));
  let x = b.x + b.width * 0.8;
  const step = () => {
    x -= b.width * 0.12;
    stage.dispatchEvent(new PointerEvent('pointermove',
      Object.assign({ clientX: x, clientY: y }, opts)));
    if (x > b.x + b.width * 0.2) requestAnimationFrame(step);
    else {
      stage.dispatchEvent(new PointerEvent('pointerup',
        Object.assign({ clientX: x, clientY: y, buttons: 0 }, opts)));
      setTimeout(() => {
        const dots = Array.from(document.querySelectorAll('.sf-gallery__dot'));
        res({ active: dots.findIndex(d => d.classList.contains('is-active')) });
      }, 400);
    }
  };
  requestAnimationFrame(step);
}))()""")
    check("a horizontal drag moves to photo 2", sw.get("active") == 1, sw)

    # ---- bottom bar -------------------------------------------------------
    bar = ev("""(() => {
  const stack = document.querySelector('.sf-float-stack');
  const cs = getComputedStyle(stack);
  const b = stack.getBoundingClientRect();
  const banner = document.querySelector('.sf-cookie-banner');
  const bannerUp = banner && getComputedStyle(banner).display !== 'none';
  const btn = k => { const el = document.querySelector('.sf-float-btn--' + k);
    return el ? getComputedStyle(el).display : 'absent'; };
  const inq = document.querySelector('.sf-float-btn--inquiry');
  return { pos: cs.position, row: cs.flexDirection,
           w: Math.round(b.width), bottom: Math.round(innerHeight - b.bottom),
           bannerUp,
           email: btn('email'), top: btn('top'),
           whatsapp: btn('whatsapp'), inquiry_hidden: inq ? inq.hasAttribute('hidden') : null,
           body_pad: getComputedStyle(document.body).paddingBottom };
})()""")
    check("bottom bar: fixed, full width, row, at the viewport bottom (or lifted by the banner)",
          bar.get("pos") == "fixed" and bar.get("row") == "row"
          and bar.get("w") == 375
          and (bar.get("bottom") == 0 or (bar.get("bannerUp") and bar.get("bottom") >= 200)),
          bar)
    check("email + back-to-top withdrawn, WhatsApp visible",
          bar.get("email") == "none" and bar.get("top") == "none"
          and bar.get("whatsapp") not in ("none", "absent"), bar)
    check("inquiry waits hidden at the top of the page",
          bar.get("inquiry_hidden") is True, bar)
    check("body gains the bar's height", num(bar.get("body_pad")) >= 70, bar.get("body_pad"))

    ev("document.querySelector('.sf-fdetail-specs').scrollIntoView({block:'center'})")
    time.sleep(1.6)
    inq = ev("""(() => {
  const el = document.querySelector('.sf-float-btn--inquiry');
  if (!el) return { present: false };
  const b = el.getBoundingClientRect();
  const hit = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
  return { present: true, hidden: el.hasAttribute('hidden'),
           disp: getComputedStyle(el).display,
           hittable: !!hit && (hit === el || el.contains(hit)) };
})()""")
    check("inquiry joins the bar past the parameter band",
          inq.get("present") and not inq.get("hidden")
          and inq.get("disp") != "none" and inq.get("hittable"), inq)

    # hint hidden at the phone width
    hint = ev("(() => { const h = document.querySelector('.sf-fdetail-config__hint');"
              " return h ? getComputedStyle(h).display : 'absent'; })()")
    check('"Choose one or more" hint hidden', hint in ("none", "absent"), hint)

    # ---- 0 JS errors ------------------------------------------------------
    errs = ab("errors")
    check("0 page errors", not errs.strip(), errs[:120])


def run_768():
    print("\n===== 768x1024 (tablet: unchanged) =====")
    open_at(768, 1024)
    s = served()
    check("served = preflight candidate", s.get("preflight"), s)
    t = ev("""(() => {
  const g = sel => { const el = document.querySelector(sel);
    return el ? getComputedStyle(el) : null; };
  const open_btn = g('.sf-fdetail-config__open');
  const list = g('.sf-fdetail-config__list');
  const strip = g('.sf-fdetail2__media .sf-gallery__thumbs');
  const dots = document.querySelector('.sf-fdetail2__media .sf-gallery__dots');
  const stack = document.querySelector('.sf-float-stack');
  const scs = getComputedStyle(stack);
  const email = document.querySelector('.sf-float-btn--email');
  return { drawer_btn: open_btn ? open_btn.display : 'absent',
           list_disp: list ? list.display : null,
           list_pos: list ? list.position : null,
           strip: strip ? strip.display : null,
           dots: dots ? getComputedStyle(dots).display : 'absent',
           fold: g('.sf-fdetail-config__fold') ? g('.sf-fdetail-config__fold').display : 'absent',
           stack_dir: scs.flexDirection, stack_pos: scs.position,
           email: email ? getComputedStyle(email).display : 'absent' };
})()""")
    check("tablet keeps the drawer button", t.get("drawer_btn") not in ("none", "absent"), t)
    check("tablet keeps the list hidden behind it (--js)",
          t.get("list_disp") == "none", t.get("list_disp"))
    check("tablet keeps the thumbnail strip, no dots, no fold button",
          t.get("strip") not in ("none", None) and t.get("dots") in ("none", "absent")
          and t.get("fold") in ("none", "absent"), t)
    check("tablet keeps the floating circles, not the bar",
          t.get("stack_dir") == "column" and t.get("stack_pos") == "fixed"
          and t.get("email") not in ("none", "absent"), t)
    errs = ab("errors")
    check("0 page errors", not errs.strip(), errs[:120])


def run_1440():
    print("\n===== 1440x900 (desktop: unchanged) =====")
    open_at(1440, 900)
    s = served()
    check("served = preflight candidate", s.get("preflight"), s)
    d = ev("""(() => {
  const g = sel => { const el = document.querySelector(sel);
    return el ? getComputedStyle(el) : null; };
  const title = g('.sf-fdetail2__title');
  const h1 = document.querySelector('h1.sf-fdetail2__title');
  const stack = document.querySelector('.sf-float-stack');
  const scs = getComputedStyle(stack);
  const groups = Array.from(document.querySelectorAll('.sf-fdetail-config__group'));
  const visible = groups.filter(x => getComputedStyle(x).display !== 'none').length;
  const strip = g('.sf-fdetail2__media .sf-gallery__thumbs');
  const dots = document.querySelector('.sf-fdetail2__media .sf-gallery__dots');
  return { title: title ? title.fontSize : null, h1: !!h1,
           stack_dir: scs.flexDirection, email: (() => {
             const el = document.querySelector('.sf-float-btn--email');
             return el ? getComputedStyle(el).display : 'absent'; })(),
           drawer: g('.sf-fdetail-config__open') ? g('.sf-fdetail-config__open').display : 'absent',
           fold: g('.sf-fdetail-config__fold') ? g('.sf-fdetail-config__fold').display : 'absent',
           groups: groups.length, visible,
           strip: strip ? strip.display : null,
           dots: dots ? getComputedStyle(dots).display : 'absent' };
})()""")
    check("desktop h1 in the right column, 32px title",
          d.get("h1") and num(d.get("title")) == 32, d.get("title"))
    check("desktop shows all groups inline, no drawer, no fold button",
          d.get("drawer") in ("none", "absent") and d.get("fold") in ("none", "absent")
          and d.get("visible") == d.get("groups") and d.get("groups", 0) >= 3, d)
    check("desktop keeps the strip, no dots, circles, not a bar",
          d.get("strip") not in ("none", None) and d.get("dots") in ("none", "absent")
          and d.get("stack_dir") == "column"
          and d.get("email") not in ("none", "absent"), d)
    errs = ab("errors")
    check("0 page errors", not errs.strip(), errs[:120])


def main():
    ab("close", "--all")
    time.sleep(1)
    ab("set", "headers", HEADERS)
    run_375()
    run_768()
    run_1440()
    ab("close")
    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n%d/%d checks passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
