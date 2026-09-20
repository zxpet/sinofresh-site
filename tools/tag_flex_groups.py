#!/usr/bin/env python3
"""Tag the flex-layout groups whose layout class WP does not emit on this
template, so the theme stylesheet can reproduce the intended flex behaviour
deterministically:
  - CTA check rows (justifyContent: left)            -> .sf-row
  - article cover-image slots (4/3, centered)        -> .sf-slot sf-slot--cover
"""
import json
import re

PATH = "templates/front-page.html"
s = open(PATH, encoding="utf-8").read()

OPEN = re.compile(r"<!-- wp:group (?P<a>\{[^>]*\}) -->\s*<(?P<tag>div) class=\"(?P<c>[^\"]*)\"(?P<r>[^>]*)>")
stats = {"row": 0, "cover": 0}


def fix(m):
    a = json.loads(m.group("a"))
    lay = a.get("layout", {})
    if lay.get("type") != "flex" or a.get("className"):
        return m.group(0)
    if lay.get("justifyContent") == "left":
        a["className"] = "sf-row"
        stats["row"] += 1
    elif lay.get("justifyContent") == "center" and "aspectRatio" in json.dumps(a.get("style", {}), separators=(",", ":")):
        a["className"] = "sf-slot sf-slot--cover"
        stats["cover"] += 1
    else:
        return m.group(0)
    cls = m.group("c").split() + a["className"].split()
    return ('<!-- wp:group ' + json.dumps(a, separators=(",", ":"), ensure_ascii=False)
            + ' --><' + m.group("tag") + ' class="' + " ".join(cls) + '"' + m.group("r") + ">")


s = OPEN.sub(fix, s)
open(PATH, "w", encoding="utf-8").write(s)
print(stats)
