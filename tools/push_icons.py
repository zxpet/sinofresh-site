#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push configurator icons to dosage pages (batch mode).
Usage: python3 push_icons.py tablets,powders,pastes,drops
Each page gets: hidden sprite (only used symbols) + icons/dots on buttons."""
import re, sys, json

THEME = "/Users/meng/Workbuddy/sinofresh外贸网站建设/sinofresh-theme"
LIB = json.load(open("/tmp/symbol_lib.json"))

PLUS = "#i-plus"
def dot(cls): return ("dot", cls)
def ic(sym): return ("icon", "#i-" + sym)

# ---- value mappings (keys are exact data-value strings incl. &amp;) ----
SHAPES_TAB = {"Round":ic("circle"),"Oval":ic("oval"),"Square":ic("square"),"Bone":ic("bone"),"Custom":ic("plus")}
FLAV_TAB = {"Chicken":ic("chicken"),"Beef":ic("beef"),"Cheese":ic("cheese"),"Liver":ic("liver"),"Unflavored":ic("circle-dashed"),"Custom":ic("plus")}
FN_TAB = {"Joint":ic("joint"),"Multivitamin":ic("pill"),"Skin & Coat":ic("coat"),"Digestive":ic("stomach"),"Urinary":ic("droplet"),"Immune":ic("shield-check")}
PACK_TAB = {"Plastic Bottle":ic("plastic-bottle"),"Jar":ic("jar"),"Blister Pack":ic("blister"),"Foil Pouch":ic("foil-pouch"),"Custom":ic("plus")}

APP_POW = {"Fine Powder":ic("fine-powder"),"Granules":ic("granules"),"Microencapsulated":ic("microcaps"),"Custom":ic("plus")}
FLAV_POW = {"Unflavored":ic("circle-dashed"),"Chicken":ic("chicken"),"Beef":ic("beef"),"Cheese":ic("cheese"),"Fish":ic("fish"),"Custom":ic("plus")}
FN_POW = {"Digestive &amp; Probiotics":ic("stomach"),"Joint":ic("joint"),"Skin & Coat":ic("coat"),"Immune":ic("shield-check"),"Multivitamin":ic("pill")}
PACK_POW = {"Jar":ic("jar"),"Foil Pouch":ic("foil-pouch"),"Stand-up Pouch":ic("stand-pouch"),"Custom":ic("plus")}

TEX_PAS = {"Smooth Paste":ic("smooth-paste"),"Thick Paste":ic("thick-paste"),"Squeezable Gel":ic("droplet")}
FLAV_PAS = {"Liver":ic("liver"),"Chicken":ic("chicken"),"Salmon":ic("fish"),"Unflavored":ic("circle-dashed"),"Cheese":ic("cheese"),"Custom":ic("plus")}
FN_PAS = {"Hairball":ic("hairball"),"Digestive":ic("stomach"),"Nutrition":ic("apple"),"Immune":ic("shield-check"),"Joint":ic("joint")}
PACK_PAS = {"Plastic Tube":ic("tube"),"Metal Tube":ic("tube"),"Aluminum Tube":ic("tube"),"Custom":ic("plus")}

FLAV_DRP = {"Unflavored":ic("circle-dashed"),"Chicken":ic("chicken"),"Beef":ic("beef"),"Fish":ic("fish"),"Mint":ic("leaf"),"Custom":ic("plus")}
FN_DRP = {"Calming":ic("moon"),"Oral Care":ic("tooth"),"Immune":ic("shield-check"),"Joint":ic("joint"),"Urinary":ic("droplet"),"Multivitamin":ic("pill")}
PACK_DRP = {"Dropper Bottle":ic("dropper-bottle"),"Glass Bottle":ic("glass-bottle"),"Plastic Bottle":ic("plastic-bottle"),"Custom":ic("plus")}

PAGES = {
"tablets": {
  "shape":SHAPES_TAB,
  "color":{"White":dot("white"),"Beige":dot("beige"),"Brown":dot("brown"),"Green":dot("green"),"Custom":ic("plus")},
  "flavor":FLAV_TAB, "functions":FN_TAB, "packaging":PACK_TAB,
},
"powders": {
  "appearance":APP_POW,
  "color":{"White":dot("white"),"Beige":dot("beige"),"Light Yellow":dot("light-yellow"),"Brown":dot("brown"),"Custom":ic("plus")},
  "flavor":FLAV_POW, "functions":FN_POW, "packaging":PACK_POW,
},
"pastes": {
  "texture":TEX_PAS,
  "color":{"Brown":dot("brown"),"Beige":dot("beige"),"Green":dot("green"),"Clear":dot("white"),"Custom":ic("plus")},
  "flavor":FLAV_PAS, "functions":FN_PAS, "packaging":PACK_PAS,
},
"drops": {
  "appearance":{"Clear":dot("white"),"Light Yellow":dot("light-yellow"),"Amber":dot("amber"),"Custom":ic("plus")},
  "flavor":FLAV_DRP, "functions":FN_DRP, "packaging":PACK_DRP,
},
"liquids": {
  "appearance":{"Clear":dot("white"),"Light Color":dot("light-color"),"Suspension":dot("suspension"),"Custom":ic("plus")},
  "flavor":{"Unflavored":ic("circle-dashed"),"Chicken":ic("chicken"),"Beef":ic("beef"),"Fish":ic("fish"),"Liver":ic("liver"),"Custom":ic("plus")},
  "functions":{"Multivitamin":ic("pill"),"Joint":ic("joint"),"Immune":ic("shield-check"),"Skin & Coat":ic("coat"),"Digestive":ic("stomach"),"Heart":ic("heart")},
  "packaging":{"Plastic Bottle":ic("plastic-bottle"),"Glass Bottle":ic("glass-bottle"),"Bottle with Cup":ic("bottle-cup"),"Custom":ic("plus")},
},
"fish-oil": {
  "form":{"Softgel":ic("pill"),"Liquid Oil":ic("droplet"),"Pump Bottle":ic("pump-bottle"),"Custom":ic("plus")},
  "source":{"Salmon":ic("fish"),"Sardine":ic("fish"),"Anchovy":ic("fish"),"Cod":ic("fish"),"Fish Blend":ic("fish-symbol"),"Custom":ic("plus")},
  "functions":{"Skin & Coat":ic("coat"),"Joint":ic("joint"),"Heart":ic("heart"),"Immune":ic("shield-check"),"Omega-3 Support":ic("droplets")},
  "packaging":{"Plastic Bottle":ic("plastic-bottle"),"Glass Bottle":ic("glass-bottle"),"Pump Bottle":ic("pump-bottle"),"Custom":ic("plus")},
},
"dental-chews": {
  "shape":{"Bone":ic("bone"),"Stick":ic("stick"),"Round":ic("circle"),"Spiral":ic("spiral"),"Toothbrush":ic("toothbrush"),"Custom":ic("plus")},
  "size":{"Small (5-10 lbs)":ic("size-s"),"Medium (10-25 lbs)":ic("size-m"),"Large (25-50 lbs)":ic("size-l"),"X-Large (50+ lbs)":ic("size-xl")},
  "color":{"Green":dot("green"),"Brown":dot("brown"),"Beige":dot("beige"),"Multi-color":dot("multi"),"Custom":ic("plus")},
  "flavor":{"Mint":ic("leaf"),"Chicken":ic("chicken"),"Beef":ic("beef"),"Cheese":ic("cheese"),"Seaweed":ic("seaweed"),"Unflavored":ic("circle-dashed"),"Custom":ic("plus")},
  "functions":{"Oral Hygiene":ic("tooth"),"Plaque Control":ic("sparkles"),"Fresh Breath":ic("wind"),"Chewing":ic("chewing")},
  "packaging":{"Foil Pouch":ic("foil-pouch"),"Stand-up Pouch":ic("stand-pouch"),"Box":ic("package"),"Custom":ic("plus")},
},
}

ICON_SVG = '<svg class="configurator__icon" aria-hidden="true"><use href="{h}"/></svg>'
DOT_SVG = '<span class="configurator__dot configurator__dot--{c}" aria-hidden="true"></span>'

def process(page):
    cfg = PAGES[page]
    if not cfg:
        print(f"[{page}] no mapping — skipped"); return
    path = f"{THEME}/templates/page-{page}.html"
    src = open(path, encoding="utf-8").read()
    if "configurator__sprite" in src:
        print(f"[{page}] sprite already present — skipped"); return

    # 1) sprite: collect used symbols
    used = set()
    for g, m in cfg.items():
        for v, spec in m.items():
            if spec[0] == "icon":
                used.add(spec[1][1:])
            elif g != "color" or v != "Custom":
                pass
    for v, spec in cfg.get("color", {}).items():
        if spec[0] == "icon": used.add(spec[1][1:])
    missing = used - set(LIB)
    if missing: sys.exit(f"[{page}] MISSING symbols: {missing}")
    symbols = "".join(LIB[u] for u in sorted(used))
    sprite = ('<svg class="configurator__sprite" aria-hidden="true" focusable="false" '
              'xmlns="http://www.w3.org/2000/svg">' + symbols + "</svg>")
    marker = '<div class="configurator">'
    assert marker in src, f"[{page}] no .configurator div"
    src = src.replace(marker, sprite + "\n" + marker, 1)

    # 2) transform buttons
    lines = src.split("\n")
    group = None
    n_icon = n_dot = unmapped = []
    n_icon = n_dot = 0; unmapped = []
    out = []
    for ln in lines:
        m = re.search(r'data-group="([a-z0-9_]+)"', ln)
        if m and "configurator__group" in ln:
            group = m.group(1)
        mb = re.match(r'(\s*<button type="button" class="configurator__item" data-value="([^"]+)">)(.*?)(</button>\s*)$', ln)
        if mb and group:
            head, val, text, tail = mb.groups()
            spec = cfg.get(group, {}).get(val)
            if spec is None:
                if group in cfg:
                    unmapped.append(f"{group}:{val}")
                out.append(ln); continue
            if spec[0] == "icon":
                icon = ICON_SVG.format(h=spec[1]); n_icon += 1
            else:
                icon = DOT_SVG.format(c=spec[1]); n_dot += 1
            out.append(head + icon + text + tail)
            continue
        out.append(ln)
    src = "\n".join(out)
    if unmapped:
        sys.exit(f"[{page}] UNMAPPED values: {unmapped}")
    open(path, "w", encoding="utf-8").write(src)
    print(f"[{page}] icons: {n_icon}, dots: {n_dot}")

for p in sys.argv[1].split(","):
    process(p.strip())
