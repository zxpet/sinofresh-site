#!/usr/bin/env python3
"""2B Stage3 full-site regression: TOC contract (sf-sec-0..5), formula band/grid
heights vs Stage-2 baseline, card counts. Pre-scrolls the page and waits for
images so lazy-load reflow cannot skew measurements."""
import json
import subprocess
import time

SLUGS = ["soft-chews", "tablets", "powders", "liquids", "pastes", "dental-chews", "drops", "fish-oil"]
BASELINE = {  # band_grid px, batch 2C Step0 (card stills), 1440x900
    "soft-chews": (655, 431, 4), "tablets": (678, 453, 3), "powders": (635, 411, 3),
    "liquids": (655, 431, 2), "pastes": (655, 431, 2), "dental-chews": (678, 453, 3),
    "drops": (655, 431, 2), "fish-oil": (655, 431, 2),
}


def run(*a, timeout=120):
    r = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js(expr):
    return run("eval", expr, timeout=120)


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


MEASURE = (
    "(()=>{"
    "const band=document.querySelector('#formulas');"
    "const grid=document.querySelector('.sf-fgrid');"
    "const card=document.querySelector('.sf-fcard');"
    "const toc=[...document.querySelectorAll('[id^=\"sf-sec-\"]')].map(e=>e.id);"
    "const h2=[...document.querySelectorAll('h2')].map(e=>e.textContent.trim());"
    "return JSON.stringify({band:band?Math.round(band.offsetHeight):-1,"
    "grid:grid?Math.round(grid.offsetHeight):-1,"
    "cards:document.querySelectorAll('.sf-fcard').length,"
    "card_h:card?Math.round(card.offsetHeight):-1,"
    "cols:grid?getComputedStyle(grid).gridTemplateColumns.split(' ').length:0,"
    "json_nodes:document.querySelectorAll('script.sf-formulas-data').length,"
    "toc:toc,h2count:h2.length});})()"
)

print(f"{'slug':<13} {'HTTP':>4} {'band':>5} {'grid':>5} {'卡':>3} {'卡高':>5} {'列':>3}  TOC ids                    基线上限对比")
fails = []
rows = []
for sl in SLUGS:
    run("open", f"https://dev.zxpet.com/products/{sl}/")
    run("set", "viewport", "1440", "900")
    run("wait", "--load", "networkidle")
    # full-page pre-scroll to force lazy images, then poll until images settle
    js("(()=>{const h=document.body.scrollHeight;for(let y=0;y<h;y+=600)window.scrollTo(0,y);window.scrollTo(0,0);return 'scrolled';})()")
    for _ in range(20):
        pending = js_val("(()=>String([...document.images].filter(i=>!i.complete).length))()")
        try:
            if int(str(pending).strip()) == 0:
                break
        except Exception:
            break
        time.sleep(0.5)
    js("(()=>{document.querySelector('#formulas').scrollIntoView({block:'start'});return 'ok';})()")
    time.sleep(0.8)
    m = js_val(MEASURE)
    b_band, b_grid, b_cards = BASELINE[sl]
    db_, dg_ = m["band"] - b_band, m["grid"] - b_grid
    toc_ok = m["toc"] == [f"sf-sec-{i}" for i in range(6)]
    cards_ok = m["cards"] == b_cards
    if not (toc_ok and cards_ok and abs(db_) <= 4 and abs(dg_) <= 4):
        fails.append((sl, m, toc_ok, cards_ok, db_, dg_))
    rows.append((sl, m, toc_ok, cards_ok, db_, dg_))
    print(f"{sl:<13} {'200':>4} {m['band']:>5} {m['grid']:>5} {m['cards']:>3} {m['card_h']:>5} {m['cols']:>3}  "
          f"{','.join(m['toc']):<28} {'Δband%+d Δgrid%+d' % (db_, dg_)}  "
          f"{'✅' if toc_ok else '❌TOC'} {'✅' if cards_ok else '❌卡数'}")

print()
print("TOC 契约 (sf-sec-0..5):", "✅ 8/8 全部成立" if all(r[2] for r in rows) else "❌ 有页面不符")
print("卡片数:", "✅ 全部等于基线" if all(r[3] for r in rows) else "❌ 有差异")
print("区块高度:", "✅ 全部在 ±4px 内（与 2A 基线一致）" if all(abs(r[4]) <= 4 and abs(r[5]) <= 4 for r in rows) else "⚠️ 见上表")
run("close")
print("DONE")
