#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次 2B 阶段 1.2d/1.3 对账：渲染 HTML 反抽 21 条 deep-equal + ItemList 比对 + 21 详情页(含 zh)核验。"""
import json, re, sys, urllib.request, ssl

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
BASE = "https://dev.zxpet.com"
DATA = json.load(open("/Users/meng/WorkBuddy/sinofresh外贸网站建设/_migration/cpt-2b/formulas.json", encoding="utf-8"))
RECS = DATA["records"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) sf-reconcile"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def unesc(s):
    return (s.replace("&amp;", "&").replace("&middot;", "·").replace("&nbsp;", " ")
             .replace("&mdash;", "—").replace("&#8217;", "’"))

SECTION_RE = re.compile(r'<section id="formulas"[^>]*>(.*?)</section>', re.S)
ITEM_RE = re.compile(r'<details class="sf-formula__item">(.*?)</details>', re.S)
NAME_RE = re.compile(r'<span class="sf-formula__name">(.*?)</span>', re.S)
USE_RE = re.compile(r'<span class="sf-formula__use">(.*?)</span>', re.S)
VALUE_RE = re.compile(r'<h4 class="sf-formula__label">(.*?)</h4>\s*<p class="sf-formula__value">(.*?)</p>', re.S)
LDLIST_RE = re.compile(r'<script type="application/ld\+json">(\{"@context".*?"ItemList".*?\})</script>', re.S)
LABELS = ["Ingredients", "Guaranteed Analysis", "Standard Specs"]

fail = 0
# ── 1) 8 剂型页渲染反抽 deep-equal ──
for slug in dict.fromkeys(r["dosage_slug"] for r in RECS):
    st, html = get(f"{BASE}/products/{slug}/")
    if st != 200:
        print(f"⛔ {slug}: 剂型页 HTTP {st}"); fail += 1; continue
    body = SECTION_RE.search(html)
    if not body:
        print(f"⛔ {slug}: 渲染 HTML 无 section#formulas"); fail += 1; continue
    items = ITEM_RE.findall(body.group(1))
    recs = [r for r in RECS if r["dosage_slug"] == slug]
    if len(items) != len(recs):
        print(f"⛔ {slug}: 渲染 {len(items)} ≠ 迁移 {len(recs)}"); fail += 1; continue
    for i, (it, r) in enumerate(zip(items, recs), 1):
        labels = {unesc(l.strip()): unesc(v.strip()) for l, v in VALUE_RE.findall(it)}
        got = {
            "name": unesc(NAME_RE.search(it).group(1).strip()),
            "use": unesc(USE_RE.search(it).group(1).strip()),
            "ingredients": labels.get("Ingredients"),
            "analysis": labels.get("Guaranteed Analysis"),
            "specs": labels.get("Standard Specs"),
        }
        want = {"name": r["name"], "use": r["use_label"], "ingredients": r["ingredients"],
                "analysis": r["analysis"], "specs": r["specs"]}
        if got != want:
            print(f"⛔ {slug}#{i}: 渲染与迁移不一致\n  got={got}\n  want={want}"); fail += 1
    # ItemList 比对
    ld = LDLIST_RE.search(body.group(1))
    if ld:
        names_ld = [e["name"] for e in json.loads(unesc(ld.group(1)))["itemListElement"]]
        names_rec = [r["name"] for r in recs]
        if names_ld != names_rec:
            print(f"⛔ {slug}: ItemList {names_ld} ≠ 迁移 {names_rec}"); fail += 1
    else:
        print(f"⛔ {slug}: 渲染缺 ItemList"); fail += 1
    print(f"✅ {slug}: {len(recs)} 条渲染=迁移=ItemList")

# ── 2) 21 个详情页（en + zh）──
for r in RECS:
    slug = r["name"].lower().replace(" & ", "-").replace(" ", "-")
    # post_name 由 sanitize_title 计算（& → -），服务端已生成；直接按 name 推导不可靠 → 交给服务端清单
    pass
# 从服务端拿真实 post_name 清单更稳：
import subprocess
out = subprocess.run(
    ["ssh", "-p", "22", "root@65.49.215.152",
     'cd /var/www/dev.zxpet.com/public && wp post list --post_type=sf_formula --post_status=publish '
     '--fields=ID,post_name,post_title --allow-root'],
    capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[1:]
server_rows = {}
for line in out:
    parts = line.split("\t")
    server_rows[parts[2]] = parts[1]  # title -> post_name

for r in RECS:
    pname = server_rows.get(r["name"])
    if not pname:
        print(f"⛔ {r['name']}: 服务端无此 post_name"); fail += 1; continue
    st, html = get(f"{BASE}/formulas/{pname}/")
    title_ok = f">{r['name']}<" in html or r["name"] in html
    st_zh, _ = get(f"{BASE}/zh/formulas/{pname}/")
    ok = st == 200 and st_zh == 200 and title_ok
    if not ok:
        print(f"⛔ {r['name']}: en={st} zh={st_zh} title_ok={title_ok}"); fail += 1
    else:
        print(f"✅ /formulas/{pname}/ 200 (zh 200)")

print("=" * 40)
print("对账结果:", "✅ 全部通过" if fail == 0 else f"❌ {fail} 处失败")
sys.exit(0 if fail == 0 else 1)
