#!/usr/bin/env python3
"""2B Stage2 verification: readFormula() JSON path vs legacy DOM fallback.
Drives agent-browser via subprocess (per user convention: sequential Python
driver avoids shell-loop session drift)."""
import json
import subprocess
import sys

PAGE = "https://dev.zxpet.com/products/soft-chews/"
FORMULA_KEY = "sinofresh_formula_soft-chews"
TARGET = "Joint Support Soft Chews"

payload = json.load(open("/tmp/sf-inject.json"))
payload_json = json.dumps(payload, ensure_ascii=False).replace("'", "&#39;")


def run(*args, timeout=60):
    r = subprocess.run(
        ["agent-browser", *args], capture_output=True, text=True, timeout=timeout
    )
    if r.returncode != 0 and r.stderr:
        print("STDERR:", r.stderr[:300])
    return (r.stdout + r.stderr).strip()


def js(expr):
    return run("eval", expr, timeout=60)


print("== 1. open page ==")
print(run("open", PAGE))
run("set", "viewport", "1440", "900")
run("wait", "--load", "networkidle") if run("wait", "--load", "networkidle") else None

print("== 2. sanity: configurator.js ver + FORMULA_KEY slug ==")
print(js(
    "(()=>{const s=[...document.scripts].map(x=>x.src).find(x=>x.includes('configurator.js'));"
    "return JSON.stringify({src:s});})()"
))

print("== 3. inject fetch interceptor + sessionStorage + JSON node (JSON path) ==")
print(js(
    "(()=>{"
    "window.__cap=[];"
    "const of=window.fetch;"
    "window.fetch=function(u,o){window.__cap.push({url:String(u),body:o&&o.body?o.body:null});"
    "return Promise.resolve(new Response(JSON.stringify({error:'captured'}),{status:500,headers:{'Content-Type':'application/json'}}));};"
    "sessionStorage.setItem('" + FORMULA_KEY + "'," + json.dumps(TARGET) + ");"
    "const n=document.createElement('script');n.type='application/json';n.className='sf-formulas-data';"
    "n.textContent=" + json.dumps(payload_json) + ";"
    "document.body.appendChild(n);"
    "return 'injected:'+document.querySelectorAll('script.sf-formulas-data').length;})()"
))

print("== 3.5 fill configurator: pick first non-Custom option per group ==")
print(js(
    "(()=>{const gs=[...document.querySelectorAll('[data-group].configurator__group,[data-group]')]"
    ".filter(g=>g.querySelector('.configurator__item'));"
    "const picked=[];gs.forEach(g=>{"
    "const opts=[...g.querySelectorAll('.configurator__item')];"
    "const opt=opts.find(o=>o.getAttribute('data-value')!=='Custom')||opts[0];"
    "opt.click();picked.push(g.getAttribute('data-group')+'='+opt.getAttribute('data-value'));});"
    "return 'picked:'+picked.join('|');})()"
))

print("== 4. click PDF button (JSON path expected) ==")
print(js(
    "(()=>{const b=document.querySelector('.configurator__pdf');"
    "if(!b)return 'NO_BUTTON';b.click();return 'clicked';})()"
))
import time
time.sleep(1.5)
cap = js("(()=>JSON.stringify(window.__cap||[]))()")
cap_data = json.loads(cap) if cap.startswith("[") or cap.startswith("{") or cap.startswith("\"") else []
try:
    cap_list = json.loads(json.loads(cap)) if cap.startswith("\"") else json.loads(cap)
except Exception:
    cap_list = []
if cap_list:
    body = json.loads(cap_list[0]["body"])
    f = body.get("formula")
    exp = next(p for p in payload if p["name"] == TARGET)
    ok_json = (
        f and f["name"] == TARGET
        and len(f["sections"]) == 3
        and [s["label"] for s in f["sections"]] == ["Ingredients", "Guaranteed Analysis", "Standard Specs"]
        and f["sections"][0]["value"] == exp["sections"][0]["value"]
        and f["sections"][2]["value"] == exp["sections"][2]["value"]
    )
    print("JSON路径 capture:", json.dumps(f, ensure_ascii=False)[:220])
    print("JSON路径判定:", "✅ PASS" if ok_json else "❌ FAIL")
else:
    print("❌ 未捕获到 fetch 请求:", cap[:200])

print("== 5. remove JSON node -> legacy DOM fallback path ==")
print(js(
    "(()=>{document.querySelectorAll('script.sf-formulas-data').forEach(n=>n.remove());"
    "window.__cap=[];return 'removed';})()"
))
print(js(
    "(()=>{const b=document.querySelector('.configurator__pdf');b.click();return 'clicked';})()"
))
time.sleep(1.5)
cap2 = js("(()=>JSON.stringify(window.__cap||[]))()")
try:
    cap2_list = json.loads(json.loads(cap2)) if cap2.startswith("\"") else json.loads(cap2)
except Exception:
    cap2_list = []
if cap2_list:
    f2 = json.loads(cap2_list[0]["body"]).get("formula")
    ok_fb = (
        f2 and f2["name"] == TARGET
        and len(f2["sections"]) == 3
        and [s["label"] for s in f2["sections"]] == ["Ingredients", "Guaranteed Analysis", "Standard Specs"]
    )
    print("回落路径 capture:", json.dumps(f2, ensure_ascii=False)[:220])
    print("回落路径判定:", "✅ PASS" if ok_fb else "❌ FAIL")
else:
    print("❌ 回落路径未捕获:", cap2[:200])

print("== 6. negative case: unknown formula name -> empty sections ==")
print(js(
    "(()=>{sessionStorage.setItem('" + FORMULA_KEY + "','No Such Formula XYZ');"
    "window.__cap=[];document.querySelector('.configurator__pdf').click();return 'clicked';})()"
))
time.sleep(1.2)
cap3 = js("(()=>JSON.stringify(window.__cap||[]))()")
try:
    cap3_list = json.loads(json.loads(cap3)) if cap3.startswith("\"") else json.loads(cap3)
    f3 = json.loads(cap3_list[0]["body"]).get("formula")
    print("空结果 capture:", json.dumps(f3, ensure_ascii=False))
    print("空结果判定:", "✅ PASS" if f3 == {"name": "No Such Formula XYZ", "sections": []} else "❌ FAIL")
except Exception as e:
    print("❌ 空结果核验异常:", cap3[:200], e)

print("== 7. restore sessionStorage + cleanup, JS error check ==")
print(js(
    "(()=>{sessionStorage.removeItem('" + FORMULA_KEY + "');"
    "return 'cleaned';})()"
))
errs = js("(()=>JSON.stringify(window.__jsErrors||[]))()")
print("页面JS错误:", errs or "无记录钩子(未注入)")

run("close")
print("DONE")
