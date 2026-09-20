#!/usr/bin/env python3
"""2B Stage3 verification: readFormula() dual-path AFTER legacy DOM removal.

Path 1 (JSON present): real .sf-formulas-data node -> click PDF -> capture
        request body -> sections must deep-equal the page's own JSON values.
Path 2 (JSON removed): delete the node -> click PDF -> by design returns
        {name, sections: []} (no legacy DOM to fall back to) -> must NOT throw,
        request must still carry the name so the PDF can still be produced.

Captured request bodies are written to /tmp so the caller can re-POST them and
validate the real PDF with pypdf (agent-browser fetch is stubbed to 500 so the
capture is deterministic).

Drives agent-browser via subprocess, sequentially (avoids shell-loop drift).
"""
import json
import subprocess
import time

PAGE = "https://dev.zxpet.com/products/soft-chews/"
FORMULA_KEY = "sinofresh_formula_soft-chews"

records = json.load(open("/tmp/sc-live.json"))
TARGET = records[0]["name"]                              # "Joint Support Soft Chews"
EXPECT = {s["label"]: s["value"] for s in records[0]["sections"]}
LABELS = ["Ingredients", "Guaranteed Analysis", "Standard Specs"]


def run(*args, timeout=90):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js(expr):
    return run("eval", expr, timeout=90)


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


results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


print("== 0. open page ==")
print(run("open", PAGE))
run("set", "viewport", "1440", "900")
run("wait", "--load", "networkidle")
run("wait", "1500")

# JS error hooks (must be installed before we act)
js(
    "(()=>{window.__errs=window.__errs||[];"
    "window.addEventListener('error',e=>window.__errs.push('error: '+e.message));"
    "window.addEventListener('unhandledrejection',e=>window.__errs.push('rej: '+String(e.reason)));"
    "return 'hooked';})()"
)

print("== 1. sanity: real JSON node + script version ==")
sanity = js_val(
    "(()=>{const src=[...document.scripts].map(s=>s.src).find(s=>s.includes('configurator.js'))||'';"
    "const n=document.querySelectorAll('script.sf-formulas-data').length;"
    "let cnt=0;try{cnt=JSON.parse(document.querySelector('script.sf-formulas-data').textContent).length;}catch(e){cnt=-1;}"
    "return JSON.stringify({ver:(src.match(/ver=([0-9.]+)/)||[])[1]||'',nodes:n,records:cnt});})()"
)
print("   ", sanity)
check("真实 .sf-formulas-data 节点存在且 1 个", sanity.get("nodes") == 1, f"nodes={sanity.get('nodes')}")
check("JSON 记录数 = 4（soft-chews）", sanity.get("records") == 4, f"records={sanity.get('records')}")
check("configurator.js 版本 = 2.3", sanity.get("ver") == "2.3", f"ver={sanity.get('ver')}")

print("== 2. install fetch capture (stubbed 500) + set sessionStorage ==")
js(
    "(()=>{window.__cap=[];const of=window.fetch;window.__of=of;"
    "window.fetch=function(u,o){window.__cap.push({url:String(u),body:(o&&o.body)||null});"
    "return Promise.resolve(new Response(JSON.stringify({error:'captured'}),{status:500,headers:{'Content-Type':'application/json'}}));};"
    "sessionStorage.setItem(" + json.dumps(FORMULA_KEY) + "," + json.dumps(TARGET) + ");"
    "return 'ready';})()"
)
print("   sessionStorage:", js("(()=>sessionStorage.getItem('" + FORMULA_KEY + "'))()"))

print("== 3. fill configurator (first non-Custom option per group) ==")
print("   ", js(
    "(()=>{const gs=[...document.querySelectorAll('[data-group]')].filter(g=>g.querySelector('.configurator__item'));"
    "const picked=[];gs.forEach(g=>{const opts=[...g.querySelectorAll('.configurator__item')];"
    "const o=opts.find(x=>x.getAttribute('data-value')!=='Custom')||opts[0];o.click();"
    "picked.push(g.getAttribute('data-group')+'='+o.getAttribute('data-value'));});"
    "return picked.join(' | ');})()"
))

print("== 4. PATH 1: click PDF with JSON node present ==")
print("   ", js("(()=>{const b=document.querySelector('.configurator__pdf');if(!b)return 'NO_BUTTON';b.click();return 'clicked';})()"))
time.sleep(2.0)
cap1 = js_val("(()=>JSON.stringify(window.__cap||[]))()")
if isinstance(cap1, list) and cap1:
    body1 = json.loads(cap1[0]["body"])
    json.dump(body1, open("/tmp/sf-real-body.json", "w"), ensure_ascii=False)
    f1 = body1.get("formula") or {}
    got = {s["label"]: s["value"] for s in (f1.get("sections") or [])}
    check("路径1 名称命中 JSON 记录", f1.get("name") == TARGET, f"name={f1.get('name')!r}")
    check("路径1 sections 三个 label 齐全", [s["label"] for s in (f1.get("sections") or [])] == LABELS)
    check("路径1 三字段值与页面 JSON 逐字符一致", got == EXPECT,
          "全部一致" if got == EXPECT else f"差异值: {[k for k in EXPECT if got.get(k) != EXPECT[k]]}")
else:
    check("路径1 捕获到 fetch 请求", False, str(cap1)[:200])

print("== 5. PATH 2: remove JSON node -> click PDF ==")
print("   ", js("(()=>{document.querySelectorAll('script.sf-formulas-data').forEach(n=>n.remove());"
               "window.__cap=[];return 'nodes now: '+document.querySelectorAll('script.sf-formulas-data').length;})()"))
print("   ", js("(()=>{const b=document.querySelector('.configurator__pdf');b.click();return 'clicked';})()"))
time.sleep(2.0)
cap2 = js_val("(()=>JSON.stringify(window.__cap||[]))()")
if isinstance(cap2, list) and cap2:
    body2 = json.loads(cap2[0]["body"])
    json.dump(body2, open("/tmp/sf-empty-body.json", "w"), ensure_ascii=False)
    f2 = body2.get("formula") or {}
    check("路径2 仍发出请求（未因缺 JSON 中断）", True, f"url={(cap2[0].get('url') or '')[-40:]}")
    check("路径2 按设计返回空 sections",
          f2.get("name") == TARGET and f2.get("sections") == [],
          json.dumps(f2, ensure_ascii=False))
else:
    check("路径2 捕获到 fetch 请求", False, str(cap2)[:200])

print("== 6. JS error check ==")
errs = js_val("(()=>JSON.stringify(window.__errs||[]))()")
print("   errors:", errs)
check("页面无未捕获 JS 错误", errs == [], str(errs)[:200])

run("close")
print("\n=== SUMMARY ===")
for n, ok, d in results:
    print(f"{'✅' if ok else '❌'} {n}")
print(f"TOTAL {sum(1 for _, ok, _ in results if ok)}/{len(results)} PASS")
