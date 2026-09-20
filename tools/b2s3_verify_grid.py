#!/usr/bin/env python3
"""2B Stage3 Step2 verification: card grid layout + toast + screenshots."""
import subprocess
import time

PAGE = "https://dev.zxpet.com/products/soft-chews/"


def run(*args, timeout=90):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js(expr):
    return run("eval", expr, timeout=60)


print("== 1. desktop 1440 ==")
print(run("open", PAGE))
run("set", "viewport", "1440", "900")
run("wait", "--load", "networkidle")
# 全页预滚动逼懒加载 → 等图片
run("eval", "(()=>{window.scrollTo(0,document.body.scrollHeight);return 'scrolled';})()")
time.sleep(2)
run("eval", "(()=>window.scrollTo(0,0))()")
time.sleep(1)

print("== 2. grid 几何 ==")
print(js(
    "(()=>{const g=document.querySelector('.sf-fgrid');if(!g)return 'NO_GRID';"
    "const cs=getComputedStyle(g);const cards=[...g.querySelectorAll('.sf-fcard')];"
    "const heights=cards.map(c=>Math.round(c.getBoundingClientRect().height));"
    "const r=g.getBoundingClientRect();"
    "return JSON.stringify({cols:cs.gridTemplateColumns.split(' ').length,gap:cs.gap,"
    "cardCount:cards.length,cardHeights:heights,gridWidth:Math.round(r.width)});})()"
))

print("== 3. toast 链路（点击 Reference this formula）==")
print(js(
    "(()=>{const b=document.querySelector('.sf-formula__cta');if(!b)return 'NO_CTA';"
    "b.click();return 'clicked:'+b.getAttribute('data-formula');})()"
))
time.sleep(1)
print(js(
    "(()=>{const t=document.querySelector('.sf-toast');"
    "return JSON.stringify({exists:!!t,visible:t?t.classList.contains('is-visible'):false,"
    "text:t?t.textContent.trim():'',ss:sessionStorage.getItem('sinofresh_formula_soft-chews')});})()"
))

print("== 4. 桌面截图（formulas 区块视口）==")
run("eval", "(()=>{const el=document.querySelector('#formulas');el.scrollIntoView();return 'ok';})()")
time.sleep(1)
print(run("screenshot", "/tmp/s3-grid-desktop.png"))

print("== 5. mobile 375 ==")
run("set", "viewport", "375", "812")
time.sleep(1)
run("eval", "(()=>{const el=document.querySelector('#formulas');el.scrollIntoView();return 'ok';})()")
time.sleep(1)
print(js(
    "(()=>{const g=document.querySelector('.sf-fgrid');const cs=getComputedStyle(g);"
    "return JSON.stringify({cols:cs.gridTemplateColumns.split(' ').length,gap:cs.gap});})()"
))
print(run("screenshot", "/tmp/s3-grid-mobile.png"))

run("close")
print("DONE")
