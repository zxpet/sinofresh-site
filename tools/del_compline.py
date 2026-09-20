#!/usr/bin/env python3
"""Task1: remove Compliance one-liner (sf-compline block) from 8 dosage page templates,
plus the orphan .sf-compline rules in style.css. Re-run safe (exits cleanly when absent)."""
import re, sys, os

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme"
PAGES = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]

BLOCK_RE = re.compile(
    r"<!-- Block \d+: Compliance & Quality -->\n"
    r"<!-- wp:group \{\"tagName\":\"section\",\"className\":\"sf-compline\".*?"
    r"<!-- /wp:group -->\n\n",
    re.DOTALL,
)

fail = False
for p in PAGES:
    fp = os.path.join(ROOT, "templates", f"page-{p}.html")
    src = open(fp, encoding="utf-8").read()
    matches = BLOCK_RE.findall(src)
    if len(matches) == 0:
        print(f"[skip] page-{p}.html: already removed")
        continue
    if len(matches) != 1:
        print(f"[FAIL] page-{p}.html: {len(matches)} matches (expect 1)")
        fail = True
        continue
    out = BLOCK_RE.sub("", src, count=1)
    # sanity: block comment balance unchanged delta (we removed 1 open + 1 close)
    opens = out.count("-- wp:group")
    closes = out.count("-- /wp:group")
    if opens != closes:
        print(f"[FAIL] page-{p}.html: comment imbalance {opens}/{closes}")
        fail = True
        continue
    if "sf-compline" in out:
        print(f"[FAIL] page-{p}.html: sf-compline residue")
        fail = True
        continue
    open(fp, "w", encoding="utf-8").write(out)
    print(f"[ok] page-{p}.html: removed compline block ({len(src)-len(out)} bytes)")

# style.css: remove orphan rules
css_fp = os.path.join(ROOT, "style.css")
css = open(css_fp, encoding="utf-8").read()
CSS_BLOCK = (
    "/* Compliance line: hairline above the single row to keep band rhythm */\n"
    ".sf-compline {\n"
    "\tborder-top: 1px solid var(--wp--preset--color--border-light);\n"
    "}\n"
    ".sf-compline p a {\n"
    "\tcolor: var(--wp--preset--color--primary);\n"
    "\tfont-weight: 600;\n"
    "}\n"
)
if CSS_BLOCK in css:
    css = css.replace(CSS_BLOCK, "", 1)
    if "sf-compline" in css:
        print("[FAIL] style.css: sf-compline residue after edit")
        fail = True
    else:
        open(css_fp, "w", encoding="utf-8").write(css)
        print("[ok] style.css: removed .sf-compline rules")
elif "sf-compline" not in css:
    print("[skip] style.css: already clean")
else:
    print("[FAIL] style.css: sf-compline present but pattern mismatch — manual fix needed")
    fail = True

sys.exit(1 if fail else 0)
