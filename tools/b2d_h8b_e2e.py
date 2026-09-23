#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8b E2E — Shape and Container Type, driven in a real browser.

Target: the PREFLIGHT copy (2.10.75). Dev still serves 2.10.73 for this batch
(the pull is a separate, user-authorised step), so the candidate exists on the
box only as `sinofresh-theme-preflight`, behind the `X-SF-Preflight: 1` header.

`--live` drops the header and drives dev's own 2.10.73. Every item of this batch
is NEW, so all of them must be RED on live — that is the run that proves this
script can fail, and it is the reason the two runs are reported separately.

Session recipe (measured 2026-09-23): close --all -> open <url> ->
set headers {X-SF-Preflight, Authorization} -> reload. `set credentials` is
deliberately not used: it and `set headers` each rebuild the context and the
later one erases the former, so the Basic credential rides inside the one
`set headers` call. Note that `open` clears custom headers, so every `open_at`
re-sets them.

Why the expected values are a THIRD transcription
-------------------------------------------------
POOLS below is transcribed by hand from inc/formula-pools.php, exactly as the
gate's H8B_POOLS is, and the two are deliberately not shared: a script that
imports its expectations from the gate would agree with any mistake the gate
made, and the whole point of the pair is that they are separate readings of the
same product. The gate's `source` pass is what requires both to match the PHP.

Why the assertions are keyed BY DOSAGE FORM and not shared
----------------------------------------------------------
This is the failure this project has shipped five times: one set of "correct"
values reused across variants that do not share them. Here the eight forms have
eight different shape pools (8 / 5 / 6 / 4 / 4 / 4 / 4 / 4 entries) and eight
different packaging pools, and the group's own TITLE is not even the same word
on all of them — Soft Chews, Tablets and Dental Chews say "Shape", Pastes says
"Texture", Powders, Drops and Liquids say "Appearance", Fish Oil says "Form".
Every assertion below therefore names the page it is about and the pool that
page must draw. A single expected list would have been satisfied by the eight
soft-chew shapes on a powder as long as some other page was short by the same
number — which is precisely the defect the batch exists to fix.

What each assertion is anchored to, and what it refuses to be anchored to
-----------------------------------------------------------------------
the reach   The old defect had two directions and the page only showed one of
            them. `nOpts` is not enough: the claim is the exact LIST, in order,
            because "the page offers Bone" and "the page offers the eight
            soft-chew shapes" are different findings and the second is the bug.

the title   Read from `__label` in the group's own row, and from the option
            list's `aria-label`, on the same page: two carriers of one name, and
            reading only the first would pass a page whose picker is announced
            to a screen reader under the old name.

the group   That Container Type RENDERS AT ALL is the other half. It used to
            wait for the record to own a value, so it was on one page in
            twenty-one. The claim is that it is on every detail page, and that
            it comes AFTER the shape group (measured as document order, not as
            "the last child": post 158 carries a price ladder and a flavor row
            after it in some layouts, so "last" would be a by-name guess).

the record  post 158 stores the retired library's "Round", which is in no
            packaging pool. The meta line must still print the record's own
            word — `sinofresh_container_label()` falls back to the raw value —
            while the options come from the pool. Both halves are asserted on
            that one page, because "the value is gone" and "the value moved" are
            different findings and only the second is acceptable.

the box     The Custom answer must be LAST in its group and must open a box
            whose `aria-label` names the group it belongs to. Batch H8a built
            that machinery; this batch is what feeds it a different vocabulary,
            so the naming is asserted per form rather than once.
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

PRE_VER = "2.10.75"
LIVE_VER = "2.10.73"

# page -> (dosage form the spec sheet must state, shape-pool title,
#          shape pool in order, packaging pool in order)
POOLS = {
    "calming-soft-chews": (
        "Soft Chews", "Shape",
        ["Bone", "Round", "Square", "Heart", "Star", "Paw", "Cylinder", "Custom"],
        ["Aluminum Stand-up Pouch", "Aluminum Foil Pouch with Zipper", "Plastic Bottle",
         "Jar", "Blister Pack", "Box + Foil", "Custom"]),
    "calcium-phosphorus-tablets": (
        "Tablets", "Shape",
        ["Round", "Oval", "Square", "Bone", "Custom"],
        ["Plastic Bottle", "Jar", "Blister Pack", "Foil Pouch", "Custom"]),
    "natural-cleaning-dental-sticks": (
        "Dental Chews", "Shape",
        ["Bone", "Stick", "Round", "Spiral", "Toothbrush", "Custom"],
        ["Foil Pouch", "Stand-up Pouch", "Box", "Custom"]),
    "hairball-remedy-paste": (
        "Pastes", "Texture",
        ["Smooth Paste", "Thick Paste", "Squeezable Gel", "Custom"],
        ["Plastic Tube", "Metal Tube", "Aluminum Tube", "Custom"]),
    "bladder-support-powder": (
        "Powders", "Appearance",
        ["Fine Powder", "Granules", "Microencapsulated", "Custom"],
        ["Jar", "Foil Pouch", "Stand-up Pouch", "Custom"]),
    "ear-care-drops": (
        "Drops", "Appearance",
        ["Clear", "Light Yellow", "Amber", "Custom"],
        ["Dropper Bottle", "Glass Bottle", "Plastic Bottle", "Custom"]),
    "liquid-joint-support": (
        "Liquids", "Appearance",
        ["Clear", "Light Color", "Suspension", "Custom"],
        ["Plastic Bottle", "Glass Bottle", "Bottle with Cup", "Custom"]),
    "pure-fish-oil-blend": (
        "Fish Oil", "Form",
        ["Softgel", "Liquid Oil", "Pump Bottle", "Custom"],
        ["Plastic Bottle", "Glass Bottle", "Pump Bottle", "Custom"]),
}

# The one shape name that must never reach a page whose form does not own it.
SOFT_UNIQUE = ["Heart", "Star", "Paw", "Cylinder"]

RECORD = "joint-support-soft-chews"     # post 158 — the one record with a container
RECORD_ZH = "zh/formulas/joint-support-soft-chews"

RESULTS = []
SEEN = {}        # form -> the shape option values that page drew


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


CURRENT = {"live": False, "ready": True}


def wait_ready(tries=25):
    """A page that has NAVIGATED is not a page that has LOADED.

    `open` and `reload` both return before the document is parsed, and a run
    that reads too early sees `document.title === ''` with an empty <head>, no
    `<link rel=stylesheet>` and `h1 === 0` — which reads as "the theme is not
    there" and is indistinguishable from a broken deployment. The measured
    symptom was exactly that: the phone pass of this script, which reloads one
    extra time, reported `theme: ''` on two pages whose `location.pathname` was
    right.

    The gate is deliberately about readiness and not about content: it must not
    be able to pass by accident on a 401 page, so it also requires a title and
    at least one stylesheet to be present. Failing it is reported as its own
    finding rather than left to make every later assertion a false FAIL.
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


def open_at(path, w=1440, h=1000, fresh_fold=False):
    """Navigate and re-assert the custom header. `open` drops it (measured), so
    anything that navigates after the session was set up must come through
    here — otherwise the run silently drives the 401 page and reads all zeroes,
    which looks exactly like a broken selector."""
    ab("open", BASE + path)
    time.sleep(1.6)
    ab("set", "headers", PF if CURRENT["live"] is False else LIVE)
    time.sleep(0.4)
    ab("reload")
    wait_ready()
    if fresh_fold and w <= 480:
        # The fold remembers itself per session; a run that unfolded it earlier
        # would start this one unfolded and read a folded page as a pass.
        ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } "
           "catch (e) {} return 1; })()")
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


CURRENT = {"live": False}


def served(path, why, live=False, with_config=True):
    """Which artifact answered, asserted BEFORE anything is asserted about it."""
    want = LIVE_VER if live else PRE_VER
    want_cfg = "1.3.0" if live else "1.4.0"
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const scripts = Array.from(document.querySelectorAll('script[src]')).map(x => x.src);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      const cfg = scripts.find(h => h.includes('config.js')) || '';
      return { path: location.pathname, title: document.title, theme, cfg,
               pre: theme.includes('-preflight'),
               ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               cfgVer: (cfg.match(/ver=([0-9.]+)/) || [])[1] || null,
               h1: document.querySelectorAll('h1').length,
               form: (() => {
                 const dd = Array.from(document.querySelectorAll('.sf-fdetail-specs__value'))
                   .map(x => x.textContent.trim());
                 const dt = Array.from(document.querySelectorAll('.sf-fdetail-specs__term'))
                   .map(x => x.textContent.trim());
                 const i = dt.indexOf('Dosage Form');
                 return i < 0 ? null : dd[i];
               })() };
    })()""")
    ok = (isinstance(s, dict) and s.get("ver") == want and s.get("h1") == 1
          and s.get("pre") is (not live) and CURRENT.get("ready") is not False)
    if with_config:
        # config.js is enqueued on the pages that carry a configurator and
        # nowhere else, so the claim is made only where it can be true.
        ok = ok and s.get("cfgVer") == want_cfg
    check("the %s theme answered (%s)  [%s]" % (want, path, why), ok,
          dict(s, ready=CURRENT.get("ready")) if isinstance(s, dict) else s)
    return s


# ------------------------------------------------------------------ probes

GROUPS = """(() => {
  const root = document.querySelector('[data-sf-config]');
  if (!root) return {absent: true};
  const qa = (s, r) => Array.from((r || root).querySelectorAll(s));
  const q = (s, r) => (r || root).querySelector(s);
  const groups = qa('.sf-fdetail-config__group');
  const y = e => { const b = e.getBoundingClientRect();
    return +(b.top + window.scrollY).toFixed(1); };
  const info = groups.map(g => {
    const key = g.getAttribute('data-sf-config-group');
    const row = g.querySelector('.sf-fdetail-config__row');
    const lab = row ? row.querySelector('.sf-fdetail-config__label') : null;
    const meta = row ? row.querySelector('.sf-fdetail-config__meta') : null;
    const list = g.querySelector('.sf-fdetail-config__options');
    const inputs = qa('.sf-fdetail-config__input', g);
    const opts = qa('.sf-fdetail-config__opt', g);
    const picks = qa('.sf-fdetail-config__opt[data-sf-config-custom]', g);
    const cb = g.querySelector('[data-sf-config-custom-for]');
    const cbi = cb ? cb.querySelector('input') : null;
    return {
      key,
      label: lab ? lab.textContent.trim() : null,
      meta: meta ? meta.textContent.trim() : null,
      listLabel: list ? list.getAttribute('aria-label') : null,
      values: inputs.map(i => i.value),
      nOpts: opts.length,
      types: Array.from(new Set(inputs.map(i => i.type))).sort(),
      nChecked: inputs.filter(i => i.checked).length,
      nPick: picks.length,
      pickLast: picks.length ? (opts.indexOf(picks[0]) === opts.length - 1) : null,
      pickLabel: (picks[0] ? (picks[0].querySelector('.sf-fdetail-config__empty-label')
                 || picks[0].querySelector('.sf-fdetail-config__text')
                 || {}).textContent : null) || null,
      boxIn: !!cb, boxHidden: cb ? !!cb.hidden : null,
      boxFor: cb ? cb.getAttribute('data-sf-config-custom-for') : null,
      boxLabel: cbi ? cbi.getAttribute('aria-label') : null,
      boxParentIsGroup: cb ? (cb.parentNode === g) : null,
      disp: getComputedStyle(g).display,
      h: +g.getBoundingClientRect().height.toFixed(1),
      y: y(g),
    };
  });
  const by = {};
  info.forEach(x => { by[x.key] = x; });
  const fold = document.querySelector('.sf-fdetail-config__fold');
  const list = document.querySelector('.sf-fdetail-config__list');
  return {absent: false, keys: info.map(x => x.key), groups: info, by,
          folded: list ? list.classList.contains('sf-config-folded') : null,
          foldDisplay: fold ? getComputedStyle(fold).display : 'absent',
          foldWords: fold ? fold.textContent.trim() : null};
})()"""


def shape_groups(gp):
    """The (shape, container) pair of one page, or a reason they are missing."""
    by = gp.get("by") or {}
    return by.get("shape"), by.get("container")


def same_list(got, want):
    return isinstance(got, list) and got == want


# ------------------------------------------------------------------ the run

def run(live=False):
    CURRENT["live"] = live
    print("=" * 78)
    print("batch H8b E2E  --  %s" % ("LIVE 2.10.73" if live else "PREFLIGHT 2.10.75"))
    print("=" * 78)

    session(live)

    # ------------------------------------------------- every dosage form, one by one
    for slug, (form, title, shapes, packs) in POOLS.items():
        path = "/formulas/%s/" % slug
        print("\n===== %s  (%s) =====" % (form, path))
        open_at(path)
        s = served(path, "dosage form: %s" % form, live)
        check("%s the page states the dosage form it is about" % form,
              s.get("form") == form, {"spec": s.get("form"), "want": form})
        gp = ev(GROUPS)
        sh, co = shape_groups(gp)

        check("%s the group is titled the way its pool is" % form,
              sh is not None and sh.get("label") == title
              and sh.get("listLabel") == title,
              {"label": (sh or {}).get("label"), "listLabel": (sh or {}).get("listLabel"),
               "want": title})
        check("%s the picker offers exactly the %d shapes its form has, in order"
              % (form, len(shapes)),
              sh is not None and same_list(sh.get("values"), shapes),
              {"got": (sh or {}).get("values"), "want": shapes})
        check("%s ...as radios, none pre-ticked, and none of another form's"
              % form,
              sh is not None and sh.get("types") == ["radio"]
              and sh.get("nChecked") == 0
              and not (set(sh.get("values") or []) - set(shapes)),
              {"types": (sh or {}).get("types"),
               "checked": (sh or {}).get("nChecked")})

        check("%s Container Type renders and offers its packaging pool in order" % form,
              co is not None and co.get("label") == "Container Type"
              and co.get("listLabel") == "Container Type"
              and same_list(co.get("values"), packs),
              {"label": (co or {}).get("label"), "got": (co or {}).get("values"),
               "want": packs})
        check("%s ...after the shape group, not above it" % form,
              sh is not None and co is not None and sh.get("y") < co.get("y"),
              {"shapeY": (sh or {}).get("y"), "containerY": (co or {}).get("y")})

        check("%s both groups end on their own Custom pick, each with its box" % form,
              sh is not None and co is not None
              and sh.get("nPick") == 1 and sh.get("pickLast") is True
              and sh.get("boxFor") == "shape" and sh.get("boxParentIsGroup") is True
              and co.get("nPick") == 1 and co.get("pickLast") is True
              and co.get("boxFor") == "container" and co.get("boxParentIsGroup") is True,
              {"shape": {k: (sh or {}).get(k) for k in ("nPick", "pickLast", "boxFor")},
               "container": {k: (co or {}).get(k)
                             for k in ("nPick", "pickLast", "boxFor")}})

        check("%s the Custom pick says Custom and its box is named for its group" % form,
              sh is not None and co is not None
              and (sh.get("pickLabel") or "").strip() == "Custom"
              and (co.get("pickLabel") or "").strip() == "Custom"
              and sh.get("boxLabel") == "Your own %s" % title
              and co.get("boxLabel") == "Your own Container Type",
              {"shapeWords": (sh or {}).get("pickLabel"),
               "shapeBox": (sh or {}).get("boxLabel"),
               "containerBox": (co or {}).get("boxLabel")})

        hidden = [x["key"] for x in (gp.get("groups") or [])
                  if x.get("disp") == "none" or x.get("h", 0) <= 0]
        # A group can be in the DOM and drawn nowhere. The parameter column is
        # a list, so an upstream rule that hid a row would leave every count
        # above intact: "present" and "on screen" are two claims.
        check("%s every group it has is drawn at desktop width" % form,
              not hidden,
              {"hidden": hidden,
               "heights": [x.get("h") for x in (gp.get("groups") or [])]})

        SEEN[form] = sh.get("values") if sh else None

    # ------------------------------------------------- and read across the eight
    # No single page can make this claim, and it is the one the whole batch is
    # about: eight forms, eight different pools, rather than one list drawn
    # eight times with a different title on top.
    lists = [tuple(v or []) for v in SEEN.values()]
    check("the eight forms draw eight different shape pools",
          len(SEEN) == 8 and len(set(lists)) == 8,
          {f: len(v or []) for f, v in SEEN.items()})
    owners = {v: [f for f, vals in SEEN.items() if v in (vals or [])]
              for v in SOFT_UNIQUE}
    check("...and the four names only soft chews own appear on no other form",
          all(o == ["Soft Chews"] for o in owners.values()), owners)

    # ------------------------------------------------------- the record (post 158)
    print("\n===== the record: post 158, the one page that stored a container =====")
    path = "/formulas/%s/" % RECORD
    open_at(path)
    served(path, "the record's own word", live)
    gp = ev(GROUPS)
    sh, co = shape_groups(gp)
    check("the record keeps the retired slug it stores, beside the new pool",
          co is not None and co.get("meta") == "Round"
          and same_list(co.get("values"), POOLS["calming-soft-chews"][3]),
          {"meta": (co or {}).get("meta"), "nOpts": (co or {}).get("nOpts")})
    check("...and its ladder is still a group of its own, untouched",
          "pricing" in (gp.get("keys") or []),
          {"keys": gp.get("keys")})
    check("...and its shape pool is the soft chews', not a second one",
          sh is not None and same_list(sh.get("values"), POOLS["calming-soft-chews"][2]),
          {"got": (sh or {}).get("values")})

    # ------------------------------------------------------------- the zh twin
    print("\n===== the zh twin =====")
    path = "/%s/" % RECORD_ZH
    open_at(path)
    served(path, "the zh twin", live)
    gp = ev(GROUPS)
    sh, co = shape_groups(gp)
    check("the zh twin draws the same two pools as its English original",
          sh is not None and co is not None
          and same_list(sh.get("values"), POOLS["calming-soft-chews"][2])
          and same_list(co.get("values"), POOLS["calming-soft-chews"][3]),
          {"shape": len((sh or {}).get("values") or []),
           "container": len((co or {}).get("values") or [])})

    # ------------------------------------------------------- and off the detail pages
    print("\n===== a page that has no configurator =====")
    path = "/about/"
    open_at(path)
    served(path, "the negative: a page the batch must not touch", live, with_config=False)
    gp = ev(GROUPS)
    check("a page with no configurator gained no container group",
          gp.get("absent") is True,
          {"absent": gp.get("absent"), "keys": gp.get("keys")})

    # ------------------------------------------------------------- the phone
    # The fold cuts at the fifth group (H7l). The batch adds the container group
    # to forty pages, so "did it push a page across that cut" is a question the
    # desktop pass cannot ask: there everything is drawn.
    print("\n===== 375x812 — the fold, and whether the batch created a hidden group =====")
    path = "/formulas/calcium-phosphorus-tablets/"
    open_at(path, 375, 812, fresh_fold=True)
    served(path, "the phone pass: a page the batch added a group to", live)
    gp = ev(GROUPS)
    vis = [x["key"] for x in (gp.get("groups") or []) if x.get("disp") != "none"]
    check("the batch's fourth group is drawn while folded, because the cut is at five",
          gp.get("keys") == ["weight", "pack", "shape", "container"] and vis == gp.get("keys"),
          {"keys": gp.get("keys"), "visible": vis, "folded": gp.get("folded"),
           "fold": gp.get("foldWords")})

    print("\n===== 375x812 — the record, where the cut does bite =====")
    path = "/formulas/%s/" % RECORD
    open_at(path, 375, 812, fresh_fold=True)
    served(path, "the phone pass: the record", live)
    gp = ev(GROUPS)
    vis = [x["key"] for x in (gp.get("groups") or []) if x.get("disp") != "none"]
    check("the record still folds to the four H7l kept, the container behind them",
          gp.get("folded") is True
          and vis == ["pricing", "flavor", "weight", "pack"],
          {"visible": vis, "folded": gp.get("folded")})
    ab("scrollintoview", ".sf-fdetail-config__fold")
    time.sleep(0.6)
    ab("click", ".sf-fdetail-config__fold")
    time.sleep(1.0)
    gp2 = ev(GROUPS)
    vis2 = [x["key"] for x in (gp2.get("groups") or []) if x.get("disp") != "none"]
    check("...and unfolding it puts the container group on screen",
          vis2 == gp2.get("keys") and "container" in vis2, {"visible": vis2})

    # --------------------------------------------------------------- summary
    bad = [r for r in RESULTS if not r[1]]
    print("\n%s  batch H8b E2E  (%d checks, %d failed)  [%s]"
          % ("PASS" if not bad else "FAIL", len(RESULTS), len(bad),
             "LIVE 2.10.73" if live else "PREFLIGHT 2.10.75"))
    if bad:
        for n, _, det in bad:
            print("   FAIL %s  | %s" % (n, det[:200]))
    out = {"live": live, "checks": [{"name": n, "ok": o, "detail": d}
                                    for n, o, d in RESULTS],
           "ok": not bad, "total": len(RESULTS), "failed": len(bad)}
    path = "/tmp/h8b-e2e-%s.json" % ("live" if live else "pre")
    json.dump(out, open(path, "w"), indent=1)
    print("  json -> %s" % path)
    return 0 if not bad else 1


def main():
    return run(live="--live" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
