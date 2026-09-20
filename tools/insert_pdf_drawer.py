#!/usr/bin/env python3
"""Insert PDF button + email row into the mobile drawer (before
.configurator__drawer-actions) in the 8 dosage page templates. Re-run safe."""
import sys, os

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme"
PAGES = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]

ANCHOR = '<div class="configurator__drawer-actions">'
INSERT = (
    '<button type="button" class="configurator__pdf">Download PDF Summary</button>\n'
    '<div class="configurator__pdf-mail" hidden>'
    '<input type="email" class="configurator__pdf-mail-input" placeholder="Email me a copy" '
    'aria-label="Email me a copy">'
    '<button type="button" class="configurator__pdf-mail-send">Send</button></div>\n'
)

fail = False
for p in PAGES:
    fp = os.path.join(ROOT, "templates", f"page-{p}.html")
    src = open(fp, encoding="utf-8").read()
    n = src.count(ANCHOR)
    if src.count("configurator__drawer-actions") != 1 or "drawer" not in src:
        print(f"[FAIL] page-{p}.html: drawer anchor missing")
        fail = True
        continue
    # already has a pdf button inside the drawer? (check text right before anchor)
    idx = src.find(ANCHOR)
    before = src[max(0, idx - 400): idx]
    if 'configurator__pdf' in before:
        print(f"[skip] page-{p}.html: drawer already has PDF button")
        continue
    if n != 1:
        print(f"[FAIL] page-{p}.html: {n} drawer anchors")
        fail = True
        continue
    out = src.replace(ANCHOR, INSERT + ANCHOR, 1)
    open(fp, "w", encoding="utf-8").write(out)
    print(f"[ok] page-{p}.html: drawer PDF button inserted")

sys.exit(1 if fail else 0)
