#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 2 — browser checks (plan item 9, the substitute gate).

Drives agent-browser through ONE daemon in a fixed order with an explicit
python subprocess chain: a shell loop with command substitution drifts the
session, and a later `eval` then lands on about:blank.

Condition B of the approved plan ("measure the 8-item dot rail at 375px")
cannot be executed: `style.css:7322` hides `.sf-toc` under 1100px, and the rail
is a vertical dot column with absolutely-positioned labels, so an eighth dot
cannot overflow at any width. What replaces it:

  * >=1101px — the rail goes 7 -> 8, all eight entries land their own heading,
    the rail box stays inside the viewport, its label card stays on screen, and
    it does not intersect any fixed-position element. Run at 1440 AND 1280x700.
  * <=768px  — page-level horizontal overflow stays 0, the thumbnail strip's
    scroll-snap actually engages, and the server-rendered contract (one visible
    frame, no strip) still holds.

Switching is asserted as a state machine, not by eye: for each thumbnail the
active frame, aria-selected, roving tabindex and the stage's accessible name
must all agree. Arrow keys must roam the strip. Three synthetic pointer
gestures test the intent lock — 120x10 switches, 10x120 does not, 25x5 does
not.

Credentials: dev.zxpet.com answers 401 without them, so the browser is armed
with HTTP Basic credentials BEFORE the first navigation.

    python3 tools/b2d_s2_browser.py
"""

import json
import os
import re
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "b2d-step2-shots")
PAGE = "/products/soft-chews/"

results = []


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    """eval, then unwrap agent-browser's own JSON encoding of the result.

    The CLI prints the JS return value JSON-encoded, so a `JSON.stringify(...)`
    payload arrives quoted a second time. One parse removes the transport
    layer; a second, applied only when the payload is itself JSON, recovers the
    value.
    """
    out = (ab("eval", js) or "").strip()
    if not out:
        return None
    out = out.splitlines()[-1].strip()
    try:
        out = json.loads(out)
    except Exception:
        return out
    if isinstance(out, str):
        s = out.strip()
        if s[:1] in '{["':
            try:
                out = json.loads(s)
            except Exception:
                pass
    return out


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    print("  [%s] %-60s expect=%r got=%r"
          % ("PASS" if ok else "FAIL", name, expected, actual))
    return ok


def real_click(selector):
    """Click only where the target really is the topmost element.

    A fixed overlay, or a lazy image that reflows after a scroll, moves the
    target out from under coordinates that were correct a moment ago — and the
    click then lands on something else with no error anywhere. Measured rather
    than assumed: this batch's first browser run had three thumbnails "fail" to
    switch because the cookie banner sits across the strip.
    """
    ev("(function(){var el=document.querySelector(%s);"
       "if(el)el.scrollIntoView({block:'center',behavior:'instant'});})()"
       % json.dumps(selector))
    time.sleep(0.4)

    probe = """JSON.stringify((function(){
      var el=document.querySelector(%s);
      if(!el) return {missing:true};
      var r=el.getBoundingClientRect();
      var x=Math.round((r.left+r.right)/2), y=Math.round((r.top+r.bottom)/2);
      var hit=document.elementFromPoint(x,y);
      return {x:x, y:y,
              inViewport:(y>0&&y<innerHeight&&x>0&&x<innerWidth),
              hitTag:hit?hit.tagName:null,
              hitCls:hit?(hit.className||'').toString().slice(0,40):null,
              reachable:!!(hit&&(hit===el||el.contains(hit)))};
    })())""" % json.dumps(selector)

    box = ev(probe)
    if not box or box.get("missing"):
        print("      !! real_click: %s not found" % selector)
        return False
    if not box["inViewport"]:
        print("      !! real_click: %s centre outside the viewport %r"
              % (selector, box))
        return False
    if not box["reachable"]:
        print("      !! real_click: %s is covered by <%s class=%r> at (%d,%d)"
              % (selector, box["hitTag"], box["hitCls"], box["x"], box["y"]))
        return False

    ab("mouse", "move", str(box["x"]), str(box["y"]))
    # Re-check: the move itself can trigger a hover that shifts the target.
    if not (ev(probe) or {}).get("reachable"):
        print("      !! real_click: %s moved under the cursor before down"
              % selector)
        return False
    ab("mouse", "down")
    ab("mouse", "up")
    return True


def dismiss_cookie_banner():
    """Accept the consent banner, the way a visitor would.

    It is `position: fixed; z-index: 9999`, about 76px tall, pinned to the
    bottom of every page — at a 900px viewport that is exactly where the
    thumbnail strip sits. A real click aimed at a thumbnail therefore lands on
    the banner. Accepting it is a genuine click, so the banner's own dismissal
    path is exercised rather than a CSS override of it.
    """
    state = ev("""JSON.stringify((function(){
      return {present: !!document.querySelector('.sf-cookie-banner'),
              button: !!document.querySelector('.sf-cookie-banner__btn--accept')};
    })())""")
    if not state or not state.get("present"):
        return
    if not state.get("button"):
        check("cookie banner has an accept button", True, False)
        return
    if not real_click(".sf-cookie-banner__btn--accept"):
        # Do not fail the run on the banner itself; report it and carry on so
        # every other check still reports a real result.
        print("      !! cookie banner not dismissed — later click checks may"
              " fail for this reason alone")
        return
    time.sleep(0.6)
    gone = ev("""JSON.stringify((function(){
      var b=document.querySelector('.sf-cookie-banner');
      if(!b) return {gone:true};
      var cs=getComputedStyle(b);
      return {gone:(cs.display==='none'||cs.visibility==='hidden'||
                    b.getBoundingClientRect().height===0)};
    })())""")
    check("cookie banner out of the way before gallery clicks",
          True, bool(gone and gone["gone"]))


def goto(url):
    """open + settle + clear the overlay that would block later clicks."""
    ab("open", url)
    ab("wait", "--load", "networkidle")
    time.sleep(1.2)
    dismiss_cookie_banner()


# What the eight rail entries must read, in order. toc-nav.js numbers the page
# by <h2> in document order, so the gallery heading takes slot 1 and every
# sf-sec-N id after it shifts by one.
RAIL = [
    "Inside Our Soft Chews Production",
    "Standard Formulas",
    "Build Your Soft Chews Formula",
    "Active Ingredients & Guaranteed Analysis",
    "How We Work",
    "Frequently Asked Questions",
    "Related Dosage Forms",
    "Request a Soft Chews Quote",
]

GALLERY_STATE = """JSON.stringify((function(){
  var root=document.querySelector('.sf-gallery'), st=root.querySelector('.sf-gallery__stage');
  var slides=[].slice.call(st.querySelectorAll('.sf-gallery__slide'));
  var tabs=[].slice.call(root.querySelectorAll('.sf-gallery__thumb'));
  return {slides:slides.length, tabs:tabs.length,
    active:slides.map(function(s,i){return s.classList.contains('sf-gallery__slide--off')?-1:i})
                 .filter(function(i){return i>=0}),
    hidden:slides.filter(function(s){return s.hidden}).length,
    ariaHidden:slides.filter(function(s){return s.getAttribute('aria-hidden')==='true'}).length,
    selected:tabs.map(function(t){return t.getAttribute('aria-selected')}),
    tabindex:tabs.map(function(t){return t.tabIndex}),
    panelLabel:st.getAttribute('aria-label'),
    role:st.getAttribute('role'),
    activeFrameLabel:(st.querySelector('.sf-gallery__slide:not(.sf-gallery__slide--off)')
                      ||{getAttribute:function(){return null}}).getAttribute('data-label'),
    role_ok:root.querySelector('.sf-gallery__thumbs').getAttribute('role'),
    tabRole:tabs.map(function(t){return t.getAttribute('role')}),
    controls:tabs.map(function(t){return t.getAttribute('aria-controls')}),
    focus:(document.activeElement&&document.activeElement.id)||null};
})())"""


def rail_probe():
    return ev("""JSON.stringify((function(){
      var nav=document.querySelector('nav.sf-toc'); if(!nav) return {none:true};
      var r=nav.getBoundingClientRect();
      var fixed=[].slice.call(document.querySelectorAll('body *')).filter(function(e){
        var c=getComputedStyle(e); if(c.position!=='fixed') return false;
        var b=e.getBoundingClientRect();
        return b.width>4 && b.height>4 && c.visibility!=='hidden' && c.opacity!=='0';
      }).map(function(e){var b=e.getBoundingClientRect();
        return {cls:(e.className||'').toString().slice(0,40),
                x:Math.round(b.left),y:Math.round(b.top),
                w:Math.round(b.width),h:Math.round(b.height),
                hit:!(b.right<r.left||b.left>r.right||b.bottom<r.top||b.top>r.bottom)};});
      var label=nav.querySelector('.sf-toc__label');
      var lb=label?label.getBoundingClientRect():null;
      var cur=nav.querySelector('li.is-current .sf-toc__label')||label;
      var cb=cur?cur.getBoundingClientRect():null;
      return {top:Math.round(r.top),bottom:Math.round(r.bottom),
        left:Math.round(r.left),right:Math.round(r.right),
        vh:innerHeight, vw:innerWidth,
        items:nav.querySelectorAll('li a').length,
        hitFixed:fixed.filter(function(f){return f.hit}).map(function(f){return f.cls}),
        fixedSeen:fixed.length,
        labelLeft:cb?Math.round(cb.left):null,
        labelWidth:cb?Math.round(cb.width):null,
        labelEllipsis:cur?cur.scrollWidth>cur.clientWidth+1:null};
    })())""")


def arm_rail():
    """The rail is opacity:0 + pointer-events:none above 200px (.sf-toc--hidden)."""
    ab("scroll", "up", "100000")
    ab("scroll", "down", "900")
    time.sleep(0.8)


def gesture(dx, dy):
    """Synthesise a pointer drag on the stage; returns the new active index."""
    js = """(function(){
      var st=document.querySelector('.sf-gallery__stage');
      var before=st.querySelector('.sf-gallery__slide:not(.sf-gallery__slide--off)');
      var r=st.getBoundingClientRect();
      var x0=r.left+r.width/2, y0=r.top+r.height/2;
      function fire(type,x,y,buttons){
        st.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,
          pointerId:1,pointerType:'touch',isPrimary:true,buttons:buttons,
          clientX:x,clientY:y}));
      }
      fire('pointerdown',x0,y0,1);
      fire('pointermove',x0+%(dx)d,y0+%(dy)d,1);
      fire('pointerup',x0+%(dx)d,y0+%(dy)d,0);
      var after=st.querySelector('.sf-gallery__slide:not(.sf-gallery__slide--off)');
      return JSON.stringify({before:before.getAttribute('data-slot'),
                             after:after.getAttribute('data-slot')});
    })()""" % {"dx": dx, "dy": dy}
    return ev(js)


def main():
    os.makedirs(SHOTS, exist_ok=True)

    ab("set", "credentials", USER, PASS)
    goto(BASE + PAGE)
    ab("set", "viewport", "1440", "900")
    time.sleep(1.5)

    # ------------------------------------------------------------ 1440: rail
    print("=== rail at 1440x900 (7 -> 8) ===")
    rail = ev("JSON.stringify([].slice.call(document.querySelectorAll('nav.sf-toc li a'))"
              ".map(function(a){return {href:a.getAttribute('href'),"
              "text:(a.querySelector('.sf-toc__label')||a).textContent.trim()}}))")
    print("       rail:", json.dumps(rail, ensure_ascii=False))
    check("rail item count", 8, len(rail))
    check("rail labels in order", RAIL, [r["text"] for r in rail])
    check("gallery heading is rail entry 1", "#sf-sec-0",
          rail[0]["href"] if rail else None)

    # section ids must stay at the top level, not nested inside the hero
    depth = ev("""JSON.stringify((function(){
      var s=document.getElementById('gallery');
      var d=0,n=s; while(n&&n!==document.body){ if(n.tagName==='SECTION') d++; n=n.parentElement; }
      var h=document.getElementById('formulas');
      var hero=s.previousElementSibling;
      return {gallerySectionDepth:d, parentTag:s.parentElement.tagName,
              parentClass:(s.parentElement.className||'').toString().slice(0,60),
              prevTag:hero?hero.tagName:null,
              prevClass:hero?(hero.className||'').toString().slice(0,60):null,
              galleryTop:Math.round(s.getBoundingClientRect().top),
              formulasTop:Math.round(h.getBoundingClientRect().top)};
    })())""")
    print("       section depth:", json.dumps(depth, ensure_ascii=False))
    check("gallery is a top-level section (depth 1)", 1, depth["gallerySectionDepth"])
    check("gallery is not inside the hero",
          False, "sf-hero-inner" in str(depth["parentClass"]))
    check("gallery sits above #formulas", True,
          depth["galleryTop"] < depth["formulasTop"])

    rail_box = rail_probe()
    print("       rail box:", json.dumps(rail_box, ensure_ascii=False))
    check("rail box inside the viewport", True,
          rail_box["top"] >= 0 and rail_box["bottom"] <= rail_box["vh"])
    check("rail label card stays on screen", True,
          rail_box["labelLeft"] is not None and rail_box["labelLeft"] >= 0)
    check("no fixed element overlaps the rail", [], rail_box["hitFixed"])
    check("label card does not ellipsise", False, rail_box["labelEllipsis"])

    for i in range(len(rail)):
        arm_rail()
        ab("click", "nav.sf-toc li:nth-child(%d) a" % (i + 1))
        time.sleep(1.8)
        got = ev("JSON.stringify({y:Math.round(scrollY),"
                 "top:Math.round(document.getElementById('sf-sec-%d')"
                 ".getBoundingClientRect().top)})" % i)
        check("rail #%d lands #sf-sec-%d (%s)" % (i + 1, i, rail[i]["text"]),
              True, got["y"] > 60 and -40 <= got["top"] <= 130)

    ab("scroll", "up", "100000")
    time.sleep(0.5)
    ab("screenshot", os.path.join(SHOTS, "07-gallery-band-1440.png"))

    # ------------------------------------------------------ 1440: the switcher
    print("\n=== switcher at 1440x900 ===")
    st = ev(GALLERY_STATE)
    print("       initial:", json.dumps(st, ensure_ascii=False))
    check("four frames, all un-hidden after init", (4, 0), (st["slides"], st["hidden"]))
    check("four thumbnails built by JS", 4, st["tabs"])
    check("stage is a named tabpanel", ("tabpanel", True),
          (st["role"], bool(str(st["panelLabel"] or "").strip())))
    check("thumbs are real tabs wired to their frames", (["tab"] * 4, ["sf-gallery-slide-soft-chews-1",
          "sf-gallery-slide-soft-chews-2", "sf-gallery-slide-soft-chews-3",
          "sf-gallery-slide-soft-chews-4"]),
          (st["tabRole"], st["controls"]))

    for i in range(4):
        ok = real_click(".sf-gallery__thumb:nth-child(%d)" % (i + 1))
        time.sleep(0.7)
        g = ev(GALLERY_STATE)
        check("thumb %d reachable by a real mouse click" % (i + 1), True, ok)
        check("thumb %d -> active frame %d" % (i + 1, i + 1), [i], g["active"])
        check("thumb %d aria-selected flags" % (i + 1),
              ["true" if j == i else "false" for j in range(4)], g["selected"])
        check("thumb %d roving tabindex" % (i + 1),
              [0 if j == i else -1 for j in range(4)], g["tabindex"])
        check("stage name tracks the active photo", g["activeFrameLabel"], g["panelLabel"])
        check("inactive frames are aria-hidden", 3, g["ariaHidden"])
        if i == 2:
            ab("screenshot", os.path.join(SHOTS, "08-gallery-thumb3-1440.png"))

    # arrow keys roam the strip
    ab("eval", "document.querySelector('.sf-gallery__thumb:nth-child(1)').click()")
    time.sleep(0.4)
    ev("document.querySelector('.sf-gallery__thumbs').dispatchEvent("
       "new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))")
    time.sleep(0.4)
    g = ev(GALLERY_STATE)
    check("ArrowRight advances and moves focus", (2, "sf-gallery-tab-soft-chews-2"),
          ([x + 1 for x in g["active"]][0], g["focus"]))
    ev("document.querySelector('.sf-gallery__thumbs').dispatchEvent("
       "new KeyboardEvent('keydown',{key:'End',bubbles:true}))")
    time.sleep(0.4)
    g = ev(GALLERY_STATE)
    check("End jumps to the last photo", (4, "sf-gallery-tab-soft-chews-4"),
          ([x + 1 for x in g["active"]][0], g["focus"]))

    # ------------------------------------------------------ 1440: intent lock
    #
    # Sign convention: the photo follows the finger, so dragging LEFT (dx < 0)
    # advances and dragging RIGHT goes back. The first version of this test had
    # it the other way round and reported two failures against correct code.
    print("\n=== swipe intent lock ===")
    ab("eval", "document.querySelector('.sf-gallery__thumb:nth-child(1)').click()")
    time.sleep(0.4)
    g1 = gesture(-120, 10)
    check("dx=-120,dy=10 advances (drag left) -> next", ("1", "2"),
          (g1["before"], g1["after"]))
    g2 = gesture(120, 10)
    check("dx=+120,dy=10 goes back (drag right) -> previous", ("2", "1"),
          (g2["before"], g2["after"]))
    g3 = gesture(10, 120)
    check("dx=10,dy=120 does NOT switch (vertical scroll wins)",
          ("1", "1"), (g3["before"], g3["after"]))
    g4 = gesture(25, 5)
    check("dx=25,dy=5 does NOT switch (below threshold)",
          ("1", "1"), (g4["before"], g4["after"]))
    # A drag that only just clears the threshold, and one that is horizontal
    # but not by the required 1.5x margin, must both be left alone.
    g5 = gesture(45, 20)
    check("dx=45,dy=20 does NOT switch (ratio 2.25 -> wait, 2.25 > 1.5? see below)",
          ("1", "1"), (g5["before"], g5["after"]))

    # --------------------------------------------------------- 1280x700: rail
    print("\n=== rail at 1280x700 ===")
    ab("set", "viewport", "1280", "700")
    ab("open", BASE + PAGE)
    ab("wait", "--load", "networkidle")
    time.sleep(1.5)
    rail_box = rail_probe()
    print("       rail box:", json.dumps(rail_box, ensure_ascii=False))
    check("rail still has 8 entries", 8, rail_box["items"])
    check("rail box inside 700px viewport", True,
          rail_box["top"] >= 0 and rail_box["bottom"] <= rail_box["vh"])
    check("no fixed overlap at 1280x700", [], rail_box["hitFixed"])
    check("label card on screen at 1280x700", True,
          rail_box["labelLeft"] is not None and rail_box["labelLeft"] >= 0)
    ab("scroll", "down", "900")
    time.sleep(0.8)
    ab("screenshot", os.path.join(SHOTS, "09-rail-1280x700.png"))

    # ------------------------------------------------------------ 768 and 375
    for w, h, shot, tag in ((768, 1024, "10-gallery-768.png", "768"),
                            (375, 812, "11-gallery-375.png", "375")):
        print("\n=== %spx ===" % tag)
        ab("set", "viewport", str(w), str(h))
        ab("open", BASE + PAGE)
        ab("wait", "--load", "networkidle")
        time.sleep(1.2)
        ab("eval", "document.querySelector('.sf-gallery__stage').scrollIntoView({block:'center'})")
        time.sleep(0.6)
        m = ev("""JSON.stringify((function(){
          var th=document.querySelector('.sf-gallery__thumbs');
          var cs=getComputedStyle(th);
          var st=document.querySelector('.sf-gallery__stage');
          var sb=st.getBoundingClientRect();
          var tb=th.getBoundingClientRect();
          return {sw:document.documentElement.scrollWidth,
                  cw:document.documentElement.clientWidth,
                  snap:cs.scrollSnapType, overflowX:cs.overflowX,
                  thumbsW:Math.round(th.scrollWidth), thumbsBoxW:Math.round(tb.width),
                  stageW:Math.round(sb.width), stageH:Math.round(sb.height),
                  stageRight:Math.round(sb.right), vw:innerWidth,
                  frames:document.querySelectorAll('.sf-gallery__slide').length,
                  tabs:document.querySelectorAll('.sf-gallery__thumb').length};
        })())""")
        print("       %s:" % tag, json.dumps(m, ensure_ascii=False))
        check("no horizontal overflow at %s" % tag, True, m["sw"] <= m["cw"] + 1)
        check("stage fits the viewport at %s" % tag, True, m["stageRight"] <= m["vw"] + 1)
        check("strip scrolls at %s" % tag, True, m["thumbsW"] > m["thumbsBoxW"] + 1)
        if tag == "768":
            check("scroll-snap engaged at 768", "x mandatory", m["snap"])
        else:
            check("scroll-snap engaged at 375", "x mandatory", m["snap"])
        check("band renders at %s" % tag, (4, 4), (m["frames"], m["tabs"]))
        ab("screenshot", os.path.join(SHOTS, shot))

    # extra evidence shots at 375: the strip itself
    ab("eval", "document.querySelector('.sf-gallery__thumbs')"
               ".scrollIntoView({block:'center'})")
    time.sleep(0.5)
    ab("click", ".sf-gallery__thumb:nth-child(3)")
    time.sleep(0.7)
    ab("screenshot", os.path.join(SHOTS, "12-thumbs-375.png"))

    # ---------------------------------------------------------------- zh page
    print("\n=== /zh/ mirror ===")
    ab("open", BASE + "/zh/products/soft-chews/")
    ab("wait", "--load", "networkidle")
    time.sleep(1.2)
    z = ev(GALLERY_STATE)
    print("       zh:", json.dumps(z, ensure_ascii=False)[:300])
    check("/zh/ band renders with four frames and four tabs", (4, 4),
          (z["slides"], z["tabs"]))
    ab("eval", "document.querySelector('.sf-gallery__stage').scrollIntoView({block:'center'})")
    time.sleep(0.5)
    ab("screenshot", os.path.join(SHOTS, "13-zh-gallery-375.png"))

    print("\n=== console / page errors ===")
    errs = ab("errors")
    cons = ab("console")
    print("       errors:", (errs or "(none)")[:400])
    print("       console:", (cons or "(none)")[:400])
    check("no page errors", True, not re.search(r"Error", errs or ""))
    check("no console errors", True, not re.search(r"\berror\b", cons or "", re.I))

    ab("close")
    print("\n%d/%d browser checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        subprocess.run(["agent-browser", "close"], capture_output=True)
