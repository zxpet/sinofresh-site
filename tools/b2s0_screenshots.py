#!/usr/bin/env python3
"""Batch2C Step0 delivery screenshots: the #formulas band on soft-chews and
liquids, desktop 1440 + mobile 375.

Uses VIEWPORT screenshots, not element screenshots: agent-browser's element
capture clips the taller 2C band (the 2B-era #formulas element shot worked at
445px, but the +210px image band breaks it) and misplaces fixed overlays while
stitching. The band top is parked 70px under the sticky header, then the
viewport is shot as-is; mobile takes three successive offsets to cover the
~1800px grid. The cookie banner is dismissed the way a visitor would (Reject
Non-Essential) so the fixed banner cannot cover the card copy.
"""
import json
import os
import subprocess
import time

OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch2c-step0"
HOST = "https://dev.zxpet.com"
STICKY = 70
os.makedirs(OUT, exist_ok=True)


def run(*a, timeout=180):
    r = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js(expr):
    return run("eval", expr, timeout=180)


def js_val(expr):
    out = js(expr)
    for _ in range(3):
        try:
            v = json.loads(out)
        except Exception:
            break
        if isinstance(v, str):
            out = v
            continue
        return v
    return out


def settle():
    js("(()=>{const h=document.body.scrollHeight;"
       "for(let y=0;y<h;y+=700)window.scrollTo(0,y);window.scrollTo(0,0);return 'ok';})()")
    for _ in range(30):
        p = js_val("(()=>String([...document.images].filter(i=>!i.complete).length))()")
        try:
            if int(str(p).strip()) == 0:
                break
        except Exception:
            break
        time.sleep(0.5)
    time.sleep(0.8)


def park_band():
    """Scroll the band so its heading sits STICKY px under the viewport top."""
    js(f"(()=>{{const r=document.querySelector('#formulas').getBoundingClientRect();"
       f"window.scrollTo(0,window.scrollY+r.top-{STICKY});return 'ok';}})()")
    time.sleep(0.6)


def dismiss_cookie_banner():
    state = js("(()=>{const b=document.querySelector('.sf-cookie-banner__btn--reject');"
               "if(!b)return 'absent';b.click();return 'clicked';})()")
    if "clicked" in state:
        time.sleep(1.0)
        run("reload")
        run("wait", "--load", "networkidle")
        time.sleep(0.8)
        print("  cookie banner: dismissed + reloaded")


SHOTS = [
    # (page, width, height, offsets, suffix)
    ("soft-chews", "1440", "900", [0], ""),
    ("soft-chews", "375", "812", [0, 800, 1600], "-m1", "-m2", "-m3"),
    ("liquids", "1440", "900", [0], ""),
    ("liquids", "375", "812", [0, 800], "-m1", "-m2"),
]

for slug, w, h, offsets, *suffixes in SHOTS:
    print(f"== {slug} @{w}x{h} ==")
    run("open", f"{HOST}/products/{slug}/")
    run("set", "viewport", w, h)
    run("wait", "--load", "networkidle")
    dismiss_cookie_banner()
    settle()
    for i, off in enumerate(offsets):
        if off:
            js(f"(()=>{{const r=document.querySelector('#formulas').getBoundingClientRect();"
               f"window.scrollTo(0,window.scrollY+r.top-{STICKY}+{off});return 'ok';}})()")
            time.sleep(0.6)
        else:
            park_band()
        suffix = suffixes[i] if i < len(suffixes) else ""
        path = os.path.join(OUT, f"b2s0-{slug}-{w}{suffix}.png")
        run("screenshot", path)
        print(f"  {os.path.basename(path)}  {os.path.getsize(path)//1024}KB")

run("close")
print("DONE")
