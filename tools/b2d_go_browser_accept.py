#!/usr/bin/env python3
"""Batch GO step 3 — dev 站浏览器验收（带凭据）。

顺序按 memory 铁律：close --all → set credentials → open → set viewport → reload → eval。
eval 返回 JSON 字符串字面量，要 json.loads 两次。
"""
import json, os, shutil, subprocess, sys, time

AB = "agent-browser"
AUTH = ("sfdev", "VkEws18Kl5V1qp3TpZ6s")
DETAIL = "https://dev.zxpet.com/formulas/joint-support-soft-chews/"
PRODUCTS = "https://dev.zxpet.com/products/soft-chews/"
SHOT_DIR = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/batchGO-shots"

results = []   # (name, ok, detail)

def run(*args, timeout=60):
    p = subprocess.run([AB, *args], capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def ab(*args, **kw):
    rc, out, err = run(*args, **kw)
    if rc != 0:
        raise RuntimeError(f"agent-browser {' '.join(args[:2])} rc={rc}: {err or out}")
    return out

def eval_json(js):
    """eval 返回 JSON 字符串字面量 → 解两次。"""
    raw = ab("eval", js)
    try:
        once = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(once, str):
        try:
            return json.loads(once)
        except json.JSONDecodeError:
            return once
    return once

def guard_page(url_part, step):
    """会话守卫：还在被服务的页面上（不在 about:blank / chrome-error）。"""
    loc = eval_json("location.href")
    ok = isinstance(loc, str) and url_part in loc
    results.append((f"[守卫] 会话仍在 {url_part}", ok, f"location.href={loc!r}"))
    return ok

def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)))

def shot(path):
    """视口截图：不带 selector（路径会被当 selector），拍默认帧后挪到目标。"""
    out = ab("screenshot")
    src = None
    for tok in out.replace("\n", " ").split():
        if tok.endswith(".png"):
            src = tok
            break
    if not src or not os.path.exists(src):
        raise RuntimeError(f"screenshot 未产出文件: {out!r}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.move(src, path)
    return path

# ---------- 会话启动 ----------
run("close", "--all")
time.sleep(1)
ab("set", "credentials", AUTH[0], AUTH[1])
ab("open", DETAIL)
ab("set", "viewport", "1440", "900")
ab("reload")
try:
    ab("wait", "--load", "networkidle", timeout=45)
except Exception:
    try:
        ab("wait", "--load", "load")
    except Exception:
        pass
time.sleep(2)

# ---------- 详情页 ----------
guard_page("/formulas/joint-support-soft-chews/", "detail")

r = eval_json("""(() => {
  const h1 = document.querySelector('h1.sf-fdetail2__title');
  const side = document.querySelector('.sf-fdetail2__side');
  const sideFirst = side ? side.firstElementChild : null;
  const rows = document.querySelectorAll('.sf-fdetail-specs__row').length;
  const basketEls = document.querySelectorAll('[class*="sf-basket"]').length;
  const basketJs = document.querySelectorAll('script[src*="basket.js"]').length;
  const floatBtn = document.querySelector('.sf-float-btn--inquiry');
  const fr = floatBtn ? floatBtn.getBoundingClientRect() : null;
  const h1r = h1 ? h1.getBoundingClientRect() : null;
  return {
    h1_present: !!h1, h1_text: h1 ? h1.textContent.trim().slice(0, 60) : null,
    h1_in_side: !!h1 && !!side && h1.closest('.sf-fdetail2__side') === side,
    side_first_is_h1: !!sideFirst && sideFirst === h1,
    h1_x: h1r ? Math.round(h1r.x) : null, h1_y: h1r ? Math.round(h1r.y) : null,
    viewport_w: window.innerWidth,
    spec_rows: rows,
    basket_els: basketEls, basket_js: basketJs,
    float_present: !!floatBtn,
    float_box: fr ? [Math.round(fr.x), Math.round(fr.y), Math.round(fr.width), Math.round(fr.height)] : null,
    header_count: document.querySelectorAll('h1').length
  };
})()""")
check("详情页：右栏 H1 存在", r.get("h1_present"), r.get("h1_text"))
check("详情页：H1 属于右栏容器且为第一个子元素", r.get("h1_in_side") and r.get("side_first_is_h1"), f"x={r.get('h1_x')} y={r.get('h1_y')} vw={r.get('viewport_w')}")
check("详情页：全页 h1 恰 1 个", r.get("header_count") == 1, f"count={r.get('header_count')}")
check("详情页：参数明细表 10 行", r.get("spec_rows") == 10, f"rows={r.get('spec_rows')}")
check("详情页：无 basket 图标/抽屉/脚本", r.get("basket_els") == 0 and r.get("basket_js") == 0, f"els={r.get('basket_els')} js={r.get('basket_js')}")
fb = r.get("float_box")
check("详情页：悬浮 Send Inquiry 在位且可见", r.get("float_present") and fb and fb[2] > 0 and fb[3] > 0, f"box={fb}")

# 测试值（用户自清，可能仍在）
TESTS = ["testsadasdfasf", "sdasdasdasdasd", "asdasdasdasdfgggffff", "saasd"]
leftover = [t for t in TESTS if t in (document_text := (eval_json("document.body.innerText") or ""))]
check("详情页：测试占位值已清（用户后台操作后）", len(leftover) == 0, f"仍在页面: {leftover}" if leftover else "全部已清")

shot(f"{SHOT_DIR}/go-01-detail-top.png")

# ---------- 产品页 ----------
ab("open", PRODUCTS)
ab("reload")
try:
    ab("wait", "--load", "networkidle", timeout=45)
except Exception:
    pass
time.sleep(2)
guard_page("/products/soft-chews/", "products")

r2 = eval_json("""(() => {
  const facts = document.querySelector('.sf-facts-mini');
  const items = facts ? Array.from(facts.children) : [];
  const boxes = items.map(el => { const b = el.getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; });
  const overlaps = boxes.some((a, i) => boxes.some((b, j) => j > i && !(a[0] + a[2] <= b[0] || b[0] + b[2] <= a[0] || a[1] + a[3] <= b[1] || b[1] + b[3] <= a[1])));
  const cards = Array.from(document.querySelectorAll('.sf-formula-card')).slice(0, 4);
  const cardInfo = cards.map(c => {
    const img = c.querySelector('img');
    if (!img) return { has_img: false };
    img.scrollIntoView({ block: 'center' });
    const b = img.getBoundingClientRect();
    const x = b.x + b.width / 2, y = b.y + b.height / 2;
    const hit = document.elementFromPoint(x, y);
    const anchor = img.closest('a');
    return { has_img: true, loaded: img.complete && img.naturalWidth > 0,
             clickable: !!anchor && (!!hit && (hit === anchor || anchor.contains(hit))) };
  });
  const basketEls = document.querySelectorAll('[class*="sf-basket"]').length;
  const floatBtn = !!document.querySelector('.sf-float-btn--inquiry');
  return { facts_present: !!facts, fact_count: items.length, fact_boxes: boxes,
           fact_overlap: overlaps, cards: cardInfo, basket_els: basketEls, float_present: floatBtn };
})()""")
check("产品页：facts-mini 存在且恰 4 项", r2.get("facts_present") and r2.get("fact_count") == 4, f"count={r2.get('fact_count')}")
check("产品页：facts-mini 4 项无重叠", r2.get("fact_overlap") is False, f"boxes={r2.get('fact_boxes')}")
cards = r2.get("cards") or []
for i, c in enumerate(cards, 1):
    check(f"产品页：卡片 {i} 图片已加载且可点击", c.get("has_img") and c.get("loaded") and c.get("clickable"), str(c))
check("产品页：无 basket 图标", r2.get("basket_els") == 0, f"els={r2.get('basket_els')}")
check("产品页：悬浮 Send Inquiry 在位", r2.get("float_present"), "")

shot(f"{SHOT_DIR}/go-02-products.png")

# ---------- JS 报错 ----------
rc, errs, _ = run("errors")
err_lines = [l for l in errs.splitlines() if l.strip()] if errs else []
check("两页 0 页面错误（page errors）", len(err_lines) == 0, f"{len(err_lines)} 条: {err_lines[:3]}")
rc2, cons, _ = run("console")
bad_console = [l for l in (cons or "").splitlines() if ("error" in l.lower() or "Uncaught" in l)]
check("两页 0 console error", len(bad_console) == 0, f"{len(bad_console)} 条: {bad_console[:3]}")

# ---------- 汇总 ----------
print("\n===== 验收结果 =====")
fails = 0
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    if not ok:
        fails += 1
    print(f"{mark}  {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n共 {len(results)} 项，FAIL {fails} 项")
sys.exit(1 if fails else 0)
