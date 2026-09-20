#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banner forensics 1/3 — what is the consent banner doing at each viewport?

Evidence for the `dismiss_cookie_banner` rewrite in b2d_s2_browser.py. Writes
docs/b2d-step3-shots/_banner-probe.txt.

`dismiss_cookie_banner()` reported "centre outside the viewport, x=0 y=0" for
the accept button at 375px even though the same click succeeds at 1440px. A
zero rect means "no layout box", which is a different thing from "covered".
Measure it instead of guessing: geometry, computed display/visibility, and
whether the button is the topmost element at its own centre.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2d_s2_browser as H  # noqa: E402

PAGE = "/formulas/joint-support-soft-chews/"
OUT = []

PROBE = """JSON.stringify((function(){
  function box(sel){
    var el=document.querySelector(sel);
    if(!el) return {sel:sel, missing:true};
    var r=el.getBoundingClientRect(), cs=getComputedStyle(el);
    var x=Math.round((r.left+r.right)/2), y=Math.round((r.top+r.bottom)/2);
    var hit=document.elementFromPoint(x,y);
    return {sel:sel, w:Math.round(r.width), h:Math.round(r.height),
            top:Math.round(r.top), left:Math.round(r.left),
            display:cs.display, visibility:cs.visibility, opacity:cs.opacity,
            position:cs.position, zIndex:cs.zIndex,
            inViewport:(y>0&&y<innerHeight&&x>0&&x<innerWidth),
            hit: hit ? (hit.tagName+'.'+(hit.className||'').toString().slice(0,30)) : null,
            topmost: !!(hit && (hit===el || el.contains(hit) || el.contains(hit.parentNode)))};
  }
  return {vw:innerWidth, vh:innerHeight,
          banner:box('.sf-cookie-banner'),
          accept:box('.sf-cookie-banner__btn--accept'),
          topbar:box('.sf-topbar')};
})())"""


def measure(label, w, h):
    H.ab("set", "viewport", str(w), str(h))
    H.ab("open", H.BASE + PAGE)
    H.ab("wait", "--load", "domcontentloaded")
    import time
    time.sleep(2.0)
    m = H.ev(PROBE)
    OUT.append("%s  (%dx%d)\n%s\n" % (label, w, h, json.dumps(m, ensure_ascii=False, indent=2)))


H.ab("set", "credentials", H.USER, H.PASS)
measure("A. desktop, first load", 1440, 900)
measure("B. small, fresh load", 375, 667)
measure("C. desktop again, fresh load", 1280, 900)

# Now accept, then reload, and measure again: is the banner re-rendered in a
# collapsed "already resolved" state, which would give the accept button a zero
# rect and make real_click() report "centre outside the viewport, x=0 y=0"?
import time
clicked = H.real_click(".sf-cookie-banner__btn--accept")
time.sleep(0.8)
OUT.append("D. after accepting (clicked=%r), same load\n%s\n"
           % (clicked, json.dumps(H.ev(PROBE), ensure_ascii=False, indent=2)))

H.ab("set", "viewport", "1280", "900")
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")
time.sleep(2.5)
OUT.append("E. after accepting, RELOADED at 1280x900\n%s\n"
           % json.dumps(H.ev(PROBE), ensure_ascii=False, indent=2))
OUT.append("E. real_click on the accept button after reload: %r\n"
           % H.real_click(".sf-cookie-banner__btn--accept"))

H.ab("close")

text = "\n".join(OUT)
print(text)
p = os.path.join(H.ROOT, "docs", "b2d-step3-shots", "_banner-probe.txt")
with open(p, "w", encoding="utf-8") as fh:
    fh.write(text + "\n")
print("written:", p)
