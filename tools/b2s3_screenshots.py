#!/usr/bin/env python3
"""2B Stage3 Step3 delivery screenshots:
 - wp-admin sf_formula list (read-only login via short-lived auth cookies)
 - 8 dosage pages formula card grid (desktop 1440)
 - soft-chews + liquids mobile 375
Pre-scrolls + waits for images before each shot (lazy-load reflow safety).
"""
import json
import os
import re
import subprocess
import time

OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch2b-stage3"
os.makedirs(OUT, exist_ok=True)

ck = dict(l.split("=", 1) for l in open("/tmp/sf-cookies.txt").read().strip().splitlines() if "=" in l)
HASH = ck["COOKIEHASH"]
COOKIES = {
    f"wordpress_logged_in_{HASH}": ck["logged_in"],
    f"wordpress_{HASH}": ck["auth"],
    f"wordpress_sec_{HASH}": ck["secure_auth"],
}


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
    js("(()=>{const h=document.body.scrollHeight;for(let y=0;y<h;y+=700)window.scrollTo(0,y);window.scrollTo(0,0);return 'ok';})()")
    for _ in range(20):
        p = js_val("(()=>String([...document.images].filter(i=>!i.complete).length))()")
        try:
            if int(str(p).strip()) == 0:
                break
        except Exception:
            break
        time.sleep(0.5)
    time.sleep(0.6)


print("== A. wp-admin formulas list ==")
run("open", "https://dev.zxpet.com/")
run("set", "viewport", "1440", "900")
for name, val in COOKIES.items():
    js(f"(()=>{{document.cookie={json.dumps(name)}+'='+encodeURIComponent({json.dumps(val)})+'; path=/; max-age=1800';return 'set';}})()")
print("   已注入 cookie 数:", len(COOKIES))
run("open", "https://dev.zxpet.com/wp-admin/edit.php?post_type=sf_formula&post_status=publish")
run("wait", "--load", "networkidle")
time.sleep(1.5)
adm = js_val(
    "(()=>{const b=document.body.className;"
    "const rows=document.querySelectorAll('#the-list tr').length;"
    "const cnt=document.querySelector('.subsubsub .publish a, .subsubsub li.publish a');"
    "return JSON.stringify({loggedin:b.indexOf('wp-admin')>-1, rows:rows,"
    "pub:(cnt?cnt.textContent.trim():''),"
    "title:document.title, loginform:!!document.querySelector('#loginform')});})()"
)
print("   ", adm)
if adm.get("rows"):
    print(f"   ROWS={adm['rows']}  发布计数文案={adm.get('pub')!r}")
    js("(()=>{const t=document.querySelector('#wpadminbar');if(t)t.style.display='none';return 'ok';})()")
    run("screenshot", f"{OUT}/s3-admin-formula-list.png")
    print("   ✅ 后台列表截图:", f"{OUT}/s3-admin-formula-list.png")
else:
    print("   ❌ 未进入后台（loginform=%s, title=%s）" % (adm.get("loginform"), adm.get("title")))

print("== B. 8 页网格 桌面 1440 ==")
SLUGS = ["soft-chews", "tablets", "powders", "liquids", "pastes", "dental-chews", "drops", "fish-oil"]
run("set", "viewport", "1440", "900")
for sl in SLUGS:
    run("open", f"https://dev.zxpet.com/products/{sl}/")
    run("wait", "--load", "networkidle")
    settle()
    js("(()=>{document.querySelector('#formulas').scrollIntoView({block:'start'});window.scrollBy(0,-70);return 'ok';})()")
    time.sleep(0.7)
    run("screenshot", f"{OUT}/s3-grid-{sl}-desktop.png")
    print(f"   ✅ {sl} desktop")

print("== C. 移动 375（soft-chews + liquids）==")
run("set", "viewport", "375", "812")
for sl in ["soft-chews", "liquids"]:
    run("open", f"https://dev.zxpet.com/products/{sl}/")
    run("wait", "--load", "networkidle")
    settle()
    js("(()=>{document.querySelector('#formulas').scrollIntoView({block:'start'});window.scrollBy(0,-57);return 'ok';})()")
    time.sleep(0.7)
    run("screenshot", f"{OUT}/s3-grid-{sl}-mobile.png")
    print(f"   ✅ {sl} mobile")

run("close")
print("FILES:")
for f in sorted(os.listdir(OUT)):
    print("  ", f, os.path.getsize(os.path.join(OUT, f)), "B")
print("DONE")
