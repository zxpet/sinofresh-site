#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7g E2E — the Shape picker, against the LIVE dev site (2.10.69).

This one runs on the served site, not the preflight copy: batch A pulled
e8f0172..5db481d into dev, so the same pass is both the H7g E2E the order asks
for and the post-pull acceptance check.

Session discipline (measured; see user memory):
  close --all -> set credentials (Basic) -> open -> set viewport -> eval.
`set credentials` and `set headers` rebuild the browser context and the later
one erases the former, so a LIVE target uses credentials alone — no custom
header, which also means the theme link must NOT say `-preflight`.

Every page asserts WHICH artifact served it before asserting anything about it.
"""
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
# one page per dosage form that carries the picker
PAGES = [
    ("soft-chews", "/formulas/joint-support-soft-chews/"),
    ("liquids", "/formulas/liquid-joint-support/"),
    ("tablets", "/formulas/multivitamin-tablets/"),
    ("dental", "/formulas/plaque-control-dental-chews/"),
]
SHAPES = 8
CONTAINERS = 7
# The H7g ruling makes Shape constant and Container record-driven, and the two
# halves want different assertions. functions.php says it outright: "Container
# waits for the record's own meta before it renders"; Shape "does not wait".
# The dev DB has sf_formula_container on post 158 alone, so the expectation is
# declared per page and the container rule is asserted BOTH ways (present with
# seven options where the record has one, absent where it has none) — a
# one-sided assertion would pass on a page that lost the group.
EXPECT = {
    "soft-chews": (SHAPES, CONTAINERS, "Round"),
    "liquids": (SHAPES, None, None),
    "tablets": (SHAPES, None, None),
    "dental": (SHAPES, None, None),
}
RESULTS = []


def ab(*a, timeout=120):
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


def open_at(url, w=1440, h=900):
    ab("open", url)
    time.sleep(2.2)
    for _ in range(3):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, h: innerHeight})")
        if isinstance(got, dict) and got.get("w") == w:
            return
        time.sleep(0.8)
    raise SystemExit("viewport did not take on %s: %r" % (url, got))


SERVED = """(() => {
  const links = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href);
  const theme = links.find(h => h.includes('sinofresh-theme')) || '';
  const body = document.body.innerHTML;
  return { path: location.pathname, title: document.title,
           live: theme.includes('/sinofresh-theme/') && !theme.includes('-preflight'),
           ver: theme.includes('ver=2.10.69'),
           cfg: /config\\.js\\?ver=1\\.2\\.0/.test(body),
           gal: /formula-gallery\\.js\\?ver=2\\.2\\.0/.test(body),
           h1: document.querySelectorAll('h1').length };
})()"""

STRUCT = """(() => {
  const root = document.querySelector('[data-sf-config]');
  if (!root) return { root: false };
  const groups = Array.from(root.querySelectorAll('.sf-fdetail-config__group'));
  const byKey = k => root.querySelector('[data-sf-config-group="' + k + '"]');
  const info = k => {
    const g = byKey(k);
    if (!g) return null;
    const opts = Array.from(g.querySelectorAll('.sf-fdetail-config__opt'));
    const inputs = opts.map(o => o.querySelector('input'));
    return { n: opts.length,
             type: inputs[0] ? inputs[0].type : null,
             values: inputs.map(i => i && i.value),
             named: opts.filter(o => o.querySelector('.sf-fdetail-config__empty-label')).length,
             label: (g.querySelector('.sf-fdetail-config__label') || {}).textContent,
             meta: (g.querySelector('.sf-fdetail-config__meta') || {}).textContent };
  };
  const order = groups.map(g => g.getAttribute('data-sf-config-group'));
  return { root: true, order, total: groups.length,
           shape: info('shape'), container: info('container'),
           shapeIdx: order.indexOf('shape'), containerIdx: order.indexOf('container') };
})()"""

INTERACT = """(() => {
  const g = document.querySelector('[data-sf-config-group="shape"]');
  const opts = Array.from(g.querySelectorAll('.sf-fdetail-config__opt'));
  const stage = document.querySelector('.sf-gallery__stage');
  const preview = document.querySelector('.sf-gallery__preview');
  const main = document.querySelector('.sf-gallery__slide:not([hidden]) img');
  const photo = main ? main.getAttribute('src') : null;
  const states = () => opts.map(o => o.querySelector('input').checked);
  const pre = { hidden: preview ? preview.hasAttribute('hidden') : null,
                display: preview ? getComputedStyle(preview).display : null,
                photo };
  opts[0].click();
  const afterFirst = { states: states(), photo: main ? main.getAttribute('src') : null,
                       hidden: preview ? preview.hasAttribute('hidden') : null };
  opts[1].click();
  const afterSecond = { states: states(), photo: main ? main.getAttribute('src') : null,
                        hidden: preview ? preview.hasAttribute('hidden') : null };
  const empty = opts.every(o => o.querySelector('.sf-fdetail-config__img--empty'));
  return { empty, pre, afterFirst, afterSecond,
           stage: !!stage };
})()"""

STAGECLICK = """(() => {
  const strip = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const btn = (strip && strip.querySelector('a,button')) || document.querySelector('.sf-gallery__thumb');
  if (btn) btn.click();
  const preview = document.querySelector('.sf-gallery__preview');
  return { clicked: !!btn, hidden: preview ? preview.hasAttribute('hidden') : null };
})()"""

FOOTER = """(() => {
  const foot = document.querySelector('footer') || document.body;
  const tel = Array.from(foot.querySelectorAll('a[href^="tel:"]')).map(a => a.getAttribute('href'));
  const wa = Array.from(foot.querySelectorAll('a[href*="wa.me"]')).map(a => a.getAttribute('href'));
  const stack = document.querySelector('.sf-float-stack');
  const fwa = stack ? stack.querySelector('.sf-float-btn--whatsapp') : null;
  const inq = stack ? stack.querySelector('.sf-float-btn--inquiry') : null;
  return { tel, wa, floatWa: fwa ? fwa.getAttribute('href') : null,
           inqHref: inq ? inq.getAttribute('href') : null,
           inqFlag: inq ? inq.hasAttribute('data-sf-inquiry-open') : null,
           anyTelOnPage: Array.from(document.querySelectorAll('a[href^="tel:"]'))
             .map(a => a.getAttribute('href')) };
})()"""


def main():
    ab("close", "--all")
    time.sleep(1)
    ab("set", "credentials", USER, PASS)

    # ---- structure on four dosage forms ---------------------------------
    for slug, path in PAGES:
        open_at(BASE + path)
        s = ev(SERVED)
        check("live artifact served (%s)" % slug,
              s.get("live") and s.get("ver") and s.get("cfg") and s.get("gal") and s.get("h1") == 1, s)
        st = ev(STRUCT)
        want_shape, want_container, want_own = EXPECT[slug]
        shape = st.get("shape") or {}
        container = st.get("container")
        # half one: Shape is constant — the ruling — and a real radio group
        check("%s: Shape is there, %d options, radio, distinct values" % (slug, want_shape),
              st.get("root") and shape.get("n") == want_shape and shape.get("type") == "radio"
              and len(set(shape.get("values") or [])) == want_shape
              and shape.get("label") == "Shape" and st.get("shapeIdx") != -1,
              {"order": st.get("order"), "n": shape.get("n"), "type": shape.get("type"),
               "label": shape.get("label")})
        # half two: Container follows the record, either way
        if want_container is None:
            check("%s: no sf_formula_container on the record, so no Container group" % slug,
                  container is None and st.get("containerIdx") == -1, st.get("order"))
        else:
            check("%s: the record ships in %s, so Container shows with its 7" % (slug, want_own),
                  container and container.get("n") == want_container
                  and container.get("label") == "Container Type"
                  and container.get("meta") == want_own
                  and st.get("shapeIdx") < st.get("containerIdx"),
                  {"n": container.get("n") if container else None,
                   "meta": container.get("meta") if container else None,
                   "idx": [st.get("shapeIdx"), st.get("containerIdx")]})

    # ---- the picker with an empty library: selection moves, the photo does not
    open_at(BASE + "/formulas/joint-support-soft-chews/")
    it = ev(INTERACT)
    check("shape slots are all empty placeholders (library un-uploaded)",
          it.get("empty") is True, it.get("empty"))
    check("clicking a shape checks it, and only it",
          it["afterFirst"]["states"][0] is True
          and sum(1 for x in it["afterFirst"]["states"] if x) == 1
          and it["afterSecond"]["states"][1] is True
          and sum(1 for x in it["afterSecond"]["states"] if x) == 1, it["afterSecond"]["states"])
    check("an empty slot does NOT take over the main photo",
          it["afterFirst"]["photo"] == it["pre"]["photo"]
          and it["afterSecond"]["photo"] == it["pre"]["photo"], it["pre"]["photo"])
    check("the preview layer stays hidden for an empty slot",
          it["pre"]["hidden"] is True and it["afterFirst"]["hidden"] is True
          and it["afterSecond"]["hidden"] is True,
          {"pre": it["pre"]["hidden"], "a1": it["afterFirst"]["hidden"], "a2": it["afterSecond"]["hidden"]})
    sc = ev(STAGECLICK)
    check("a stage click keeps the preview layer hidden", sc.get("hidden") is True, sc)

    # ---- footer + float stack (H7g's second half) ------------------------
    f = ev(FOOTER)
    check("no landline tel: link anywhere on the detail page", f.get("anyTelOnPage") == [], f.get("anyTelOnPage"))
    check("the float WhatsApp button reads the footer's own number",
          f.get("floatWa") and f.get("wa") and f["floatWa"] in f["wa"], {"float": f.get("floatWa"), "footer": f.get("wa")})
    check("the float inquiry button keeps /contact/#quote + the open flag",
          f.get("inqHref") == "/contact/#quote" and f.get("inqFlag") is True, [f.get("inqHref"), f.get("inqFlag")])

    # ---- the phone keeps the picker in the DOM ---------------------------
    open_at(BASE + "/formulas/joint-support-soft-chews/", 375, 812)
    st = ev(STRUCT)
    check("375: the shape group is still rendered (8 options)",
          st.get("shape") and st["shape"]["n"] == SHAPES, st["shape"]["n"] if st.get("shape") else None)

    errs = ab("errors")
    check("0 page errors", not errs.strip(), errs[:160])
    ab("close")

    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n%d/%d checks passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
