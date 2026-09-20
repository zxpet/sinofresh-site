#!/usr/bin/env python3
"""Insert PDF summary button + optional email row under the summary card's
Submit button in the 8 dosage page templates. Re-run safe."""
import sys, os

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme"
PAGES = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]

ANCHOR = '<button type="button" class="configurator__submit">Submit This Configuration</button>'
INSERT = (
    '\n'
    '<button type="button" class="configurator__pdf">Download PDF Summary</button>\n'
    '<div class="configurator__pdf-mail" hidden>'
    '<input type="email" class="configurator__pdf-mail-input" placeholder="Email me a copy" '
    'aria-label="Email me a copy">'
    '<button type="button" class="configurator__pdf-mail-send">Send</button></div>'
)

fail = False
for p in PAGES:
    fp = os.path.join(ROOT, "templates", f"page-{p}.html")
    src = open(fp, encoding="utf-8").read()
    n = src.count(ANCHOR)
    if "configurator__pdf" in src:
        print(f"[skip] page-{p}.html: already inserted")
        continue
    if n != 1:
        print(f"[FAIL] page-{p}.html: {n} anchors (expect 1)")
        fail = True
        continue
    out = src.replace(ANCHOR, ANCHOR + INSERT, 1)
    open(fp, "w", encoding="utf-8").write(out)
    print(f"[ok] page-{p}.html: inserted PDF button + email row")

sys.exit(1 if fail else 0)
