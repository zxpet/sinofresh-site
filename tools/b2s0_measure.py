#!/usr/bin/env python3
"""Batch 2C Step0: measure formula-card grid geometry on all 8 dosage pages.

Usage:  python3 tools/b2s0_measure.py before|after [width] [page...]

Writes tools/_b2s0_measure_<tag>.json  (raw per-page geometry) and prints a
one-line summary per page. Sequential agent-browser driving (shell loops drift
the session); images are polled for .complete before any measurement.
"""
import json
import os
import subprocess
import sys
import time

HOST = "https://dev.zxpet.com"
SLAVES = [
    "soft-chews", "tablets", "powders", "liquids",
    "pastes", "dental-chews", "drops", "fish-oil",
]

MEASURE_JS = (
    "(()=>{const g=document.querySelector('.sf-fgrid');"
    "if(!g)return JSON.stringify({grid:null});"
    "const band=document.getElementById('formulas');"
    "const cs=getComputedStyle(g);"
    "const cards=[...g.querySelectorAll('.sf-fcard')];"
    "const imgs=[...g.querySelectorAll('.sf-fcard__media img')];"
    "const all=[...document.images];"
    "return JSON.stringify({"
    "imgsDone:all.length>0&&all.every(i=>i.complete),"
    "imgsTotal:all.length,"
    "gridW:Math.round(g.getBoundingClientRect().width),"
    "gridH:Math.round(g.getBoundingClientRect().height),"
    "bandH:band?Math.round(band.getBoundingClientRect().height):null,"
    "bandTop:band?Math.round(band.getBoundingClientRect().top+window.scrollY):null,"
    "cols:cs.gridTemplateColumns.split(' ').length,"
    "gap:cs.gap,"
    "cardCount:cards.length,"
    "cardH:cards.map(c=>Math.round(c.getBoundingClientRect().height)),"
    "cardW:cards.map(c=>Math.round(c.getBoundingClientRect().width)),"
    "mediaCount:imgs.length,"
    "mediaBox:imgs.map(i=>{const r=i.getBoundingClientRect();"
    "return Math.round(r.width)+'x'+Math.round(r.height);}),"
    "mediaRatio:imgs.map(i=>{const r=i.getBoundingClientRect();"
    "return r.height?(r.width/r.height).toFixed(3):'0';}),"
    "mediaFit:imgs.map(i=>getComputedStyle(i).objectFit),"
    "imgSrc:imgs.map(i=>i.getAttribute('src')),"
    "docH:Math.round(document.documentElement.scrollHeight)"
    "});})()"
)


def run(*args, timeout=120):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js(expr):
    """agent-browser prints json.dumps(<returned value>) — a string result
    therefore arrives quoted and escaped, so decode twice."""
    out = run("eval", expr, timeout=90)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            v = json.loads(line)
        except Exception:
            continue
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                continue
        if isinstance(v, dict):
            return v
    return {"error": out[-400:]}


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "after"
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
    pages = sys.argv[3:] or SLAVES
    if pages == ["all"]:
        pages = SLAVES

    results = {}
    for slug in pages:
        url = f"{HOST}/products/{slug}/"
        run("open", url)
        run("set", "viewport", str(width), "900")
        run("wait", "--load", "networkidle")
        # full-page pre-scroll to force every lazy image, then wait for complete
        run("eval", "(()=>{window.scrollTo(0,document.body.scrollHeight);return 'scrolled';})()")
        for _ in range(40):
            st = js("(()=>({d:[...document.images].every(i=>i.complete),n:document.images.length}))()")
            if isinstance(st, dict) and st.get("d"):
                break
            time.sleep(0.25)
        run("eval", "(()=>{window.scrollTo(0,0);return 'top';})()")
        time.sleep(0.4)
        m = js(MEASURE_JS)
        m["slug"] = slug
        m["url"] = url
        m["viewport"] = f"{width}x900"
        results[slug] = m
        print(f"{slug:14s} cols={m.get('cols')} cards={m.get('cardCount')} "
              f"cardW={m.get('cardW')} cardH={m.get('cardH')} "
              f"grid={m.get('gridW')}x{m.get('gridH')} band={m.get('bandH')} "
              f"media={m.get('mediaCount')} {m.get('mediaBox')} "
              f"ratio={m.get('mediaRatio')} fit={m.get('mediaFit')}")
    run("close")

    out = os.path.join(os.path.dirname(__file__), f"_b2s0_measure_{tag}_{width}.json")
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
