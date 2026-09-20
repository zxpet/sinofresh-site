#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banner forensics 2/3 — WHEN does the consent banner leave?

Writes docs/b2d-step3-shots/_banner-timeline.txt.

First probe: with a fresh session the banner is fully visible and its accept
button is topmost at 1440 / 375 / 1280, measured 2.0s after load. Then, 0.4s
later, the banner reads display:none — and real_click() had not clicked it
(returned False). So something else hides it, and the fixed 2.5s settle in the
S3 goto() can therefore land on either side of that transition. That would
explain the "x=0 y=0" warnings appearing only on the *later* navigations.

Sample the banner on a timeline instead of guessing, and note scrollY too:
scrollIntoView() inside real_click() is a candidate trigger.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2d_s2_browser as H  # noqa: E402

PAGE = "/formulas/joint-support-soft-chews/"

SAMPLE = """JSON.stringify((function(){
  var b=document.querySelector('.sf-cookie-banner');
  var a=document.querySelector('.sf-cookie-banner__btn--accept');
  if(!b) return {gone:true, scrollY:Math.round(scrollY)};
  var r=b.getBoundingClientRect(), ra=a?a.getBoundingClientRect():null;
  return {display:getComputedStyle(b).display, h:Math.round(r.height),
          btnH:ra?Math.round(ra.height):null, top:Math.round(r.top),
          scrollY:Math.round(scrollY)};
})())"""

lines = []
H.ab("set", "credentials", H.USER, H.PASS)
H.ab("set", "viewport", "1280", "900")
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")

t0 = time.time()
for i in range(40):                       # 40 x 250ms = 10s
    m = H.ev(SAMPLE) or {}
    lines.append("  t=%5.2fs  display=%-7s h=%-4s btnH=%-4s top=%-5s scrollY=%s"
                 % (time.time() - t0, m.get("display"), m.get("h"),
                    m.get("btnH"), m.get("top"), m.get("scrollY")))
    if m.get("display") == "none":
        break
    time.sleep(0.25)

# Did a scroll alone hide it? Scroll by hand and re-sample.
H.ev("window.scrollTo(0, 400)")
time.sleep(0.5)
lines.append("  after a manual window.scrollTo(0,400): %s" % H.ev(SAMPLE))
H.ev("window.scrollTo(0, 0)")
time.sleep(0.5)
lines.append("  after scrolling back to 0:              %s" % H.ev(SAMPLE))

# And does reload bring it back or is the state persisted?
H.ab("open", H.BASE + PAGE)
H.ab("wait", "--load", "domcontentloaded")
time.sleep(2.0)
lines.append("  fresh reload, 2.0s in:                  %s" % H.ev(SAMPLE))

H.ab("close")
text = "\n".join(lines)
print(text)
p = os.path.join(H.ROOT, "docs", "b2d-step3-shots", "_banner-timeline.txt")
with open(p, "w", encoding="utf-8") as fh:
    fh.write(text + "\n")
print("written:", p)
