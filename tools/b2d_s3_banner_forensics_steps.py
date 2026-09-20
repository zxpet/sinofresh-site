#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banner forensics 3/3 — which step inside real_click() collapses the banner?

Writes docs/b2d-step3-shots/_banner-steps.txt.

Evidence so far:
  * fresh session, 1280x900 — the banner is display:block h=76 for 17s, survives
    a manual scroll and a reload (probe 2).
  * in the same session, one call to real_click('.sf-cookie-banner__btn--accept')
    returned False and the banner read display:none afterwards, never coming back
    on reload (probe 1, sections D/E).

real_click() is: scrollIntoView -> sleep -> probe -> [mouse move] -> re-probe ->
down/up. Replicate it step by step, sampling the banner after each step, so the
transition is attributed to a named step instead of guessed at.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2d_s2_browser as H  # noqa: E402

PAGE = "/formulas/joint-support-soft-chews/"
SEL = ".sf-cookie-banner__btn--accept"

SAMPLE = """JSON.stringify((function(){
  var b=document.querySelector('.sf-cookie-banner');
  var a=document.querySelector(%s);
  if(!b) return {banner:'absent'};
  var r=b.getBoundingClientRect();
  var ra=a?a.getBoundingClientRect():null;
  var x=ra?Math.round((ra.left+ra.right)/2):-1, y=ra?Math.round((ra.top+ra.bottom)/2):-1;
  var hit=document.elementFromPoint(x,y);
  return {bannerDisplay:getComputedStyle(b).display, bannerH:Math.round(r.height),
          btnW:ra?Math.round(ra.width):null, btnH:ra?Math.round(ra.height):null,
          cx:x, cy:y, hit:hit?(hit.tagName+'.'+(hit.className||'').toString().slice(0,24)):null,
          reachable:!!(hit&&a&&(hit===a||a.contains(hit)))};
})())""" % json.dumps(SEL)

REACH = """JSON.stringify((function(){
  var el=document.querySelector(%s);
  if(!el) return {missing:true};
  var r=el.getBoundingClientRect();
  var x=Math.round((r.left+r.right)/2), y=Math.round((r.top+r.bottom)/2);
  var hit=document.elementFromPoint(x,y);
  return {x:x, y:y, inViewport:(y>0&&y<innerHeight&&x>0&&x<innerWidth),
          hitTag:hit?hit.tagName:null,
          reachable:!!(hit&&(hit===el||el.contains(hit)))};
})())""" % json.dumps(SEL)

lines = []


def note(label, payload):
    lines.append("  %-34s %s" % (label, json.dumps(payload, ensure_ascii=False)))


H.ab("set", "credentials", H.USER, H.PASS)
H.ab("set", "viewport", "1280", "900")
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")
time.sleep(2.5)
note("S0 freshly loaded, 2.5s", H.ev(SAMPLE))

H.ev("(function(){var el=document.querySelector(%s);"
     "if(el)el.scrollIntoView({block:'center',behavior:'instant'});})()" % json.dumps(SEL))
time.sleep(0.4)
note("S1 after scrollIntoView + 0.4s", H.ev(SAMPLE))
note("S1 reachability probe", H.ev(REACH))

box = H.ev(REACH) or {}
if box.get("reachable"):
    H.ab("mouse", "move", str(box["x"]), str(box["y"]))
    time.sleep(0.15)
    note("S2 after mouse move + 0.15s", H.ev(SAMPLE))
    note("S2 reachability probe", H.ev(REACH))
    H.ab("mouse", "down")
    H.ab("mouse", "up")
    time.sleep(0.8)
    note("S3 after mouse down/up + 0.8s", H.ev(SAMPLE))
else:
    note("skipped the mouse: not reachable", box)

# ---- the case the E2E actually hit: a LATER navigation, same session --------
lines.append("")
lines.append("  --- later navigation in the same session ---")
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")
time.sleep(2.5)
note("S4 reloaded, 2.5s", H.ev(SAMPLE))
lines.append("  S4 real_click returned %r" % H.real_click(SEL))
time.sleep(0.5)
note("S5 after real_click on the reload", H.ev(SAMPLE))

lines.append("")
lines.append("  --- does a fresh daemon reset it? ---")
H.ab("close")
H.ab("set", "credentials", H.USER, H.PASS)
H.ab("set", "viewport", "1280", "900")
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")
time.sleep(2.5)
note("S6 new session, 2.5s", H.ev(SAMPLE))

H.ab("close")
text = "\n".join(lines)
print(text)
p = os.path.join(H.ROOT, "docs", "b2d-step3-shots", "_banner-steps.txt")
with open(p, "w", encoding="utf-8") as fh:
    fh.write(text + "\n")
print("written:", p)
