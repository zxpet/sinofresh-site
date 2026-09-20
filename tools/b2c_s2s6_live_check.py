#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 6 — the acceptance run AFTER the first cloud pull.

    python3 tools/b2c_s2s6_live_check.py          # run ON the dev box

Unlike b2c_s2_preflight_check.py this talks to the site with NO gate header:
this is the shipped theme answering real requests. Everything the pre-flight
verified is re-verified here, plus the two things only a real pull can show —
that the eight dosage pages carry the new entry link on the live site, and that
their cards are untouched.

Exit code = number of failures.
"""

import html
import json
import re
import subprocess
import sys
import urllib.request

BASE = "https://dev.zxpet.com"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WP_PATH = "/var/www/dev.zxpet.com/public"
THEME = "/var/www/dev.zxpet.com/site-repo/sinofresh-theme"
FORMS = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]
CARDS_PER_FORM = {"soft-chews": 4, "tablets": 3, "powders": 3, "dental-chews": 3,
                  "pastes": 2, "drops": 2, "liquids": 2, "fish-oil": 2}
LINK = '<a class="sf-explore__btn" href="/formulas/">Browse All Formulas →</a>'

results = []


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name:<54} expect={expected!r} got={actual!r}")


def fetch(path):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA)) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def status_of(path):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(BASE + path, headers=UA)) as resp:
            return resp.status, resp.headers.get("Location") or ""
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Location") or ""


def db_card_order():
    sql = ("SELECT post_title FROM wp_posts WHERE post_type='sf_formula' "
           "AND post_status='publish' ORDER BY menu_order ASC, post_title ASC;")
    out = subprocess.run(
        ["wp", "db", "query", sql, f"--path={WP_PATH}", "--allow-root", "--skip-column-names"],
        capture_output=True, text=True, check=True).stdout
    return [html.unescape(line) for line in out.splitlines() if line.strip()]


print("=== 1) /formulas/ — live ===")
code, page = fetch("/formulas/")
check("HTTP status", 200, code)
cards = re.findall(r'<article class="sf-fcard" data-sf-form="([^"]*)"', page)
check("cards (.sf-fcard)", 21, len(cards))
chips = re.findall(r'<button type="button" class="sf-fchip[^"]*" data-sf-form="([^"]*)"', page)
check("chips", 9, len(chips))
check("chip order (All + 8 forms)", ["all"] + FORMS, chips)
check("data-formula on K1", 21, len(re.findall(r'data-formula="', page)))
check("data-form on K1", 21, page.count('data-form="'))
used = {}
for f in cards:
    used[f] = used.get(f, 0) + 1
check("cards per form", CARDS_PER_FORM, used)
check("{{ residue", 0, page.count("{{"))
check("[sf_ residue", 0, page.count("[sf_"))
check("hero count line", "21 formulas",
      re.search(r'sf-archive-count[^>]*>([^<]*)<', page).group(1).strip()
      if "sf-archive-count" in page else "missing")
check("sf-js marker", 1, page.count("classList.add('sf-js')"))
check("formulas.js enqueued", 1, len(re.findall(r'assets/js/formulas\.js\?ver=', page)))
check("formula-filter.js enqueued", 1, len(re.findall(r'assets/js/formula-filter\.js\?ver=', page)))
check("style.css version", ["2.10.44"], sorted(set(re.findall(r'style\.css\?ver=([0-9.]+)', page))))
check("status line count span", 21, int(re.search(r'<span class="sf-fchips-count">(\d+)</span>', page).group(1)))
check("status line role=status", 1, page.count('class="sf-fchips-status" role="status"'))

print("=== 2) card order vs database ===")
names = [html.unescape(m) for m in re.findall(
    r'<h3 class="sf-fcard__name">(?:<a [^>]*>)?(.*?)(?:</a>)?</h3>', page)]
db = db_card_order()
check("rendered count", 21, len(names))
check("rendered order == DB (menu_order ASC, title ASC)", True, names == db)
if names != db:
    for i, (a, b) in enumerate(zip(names, db)):
        if a != b:
            print(f"       first difference at #{i + 1}: rendered={a!r} db={b!r}")
            break

print("=== 3) JSON-LD ===")
blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
types, itemlist = [], None
for b in blocks:
    try:
        data = json.loads(b)
    except Exception as err:
        print(f"       !! unparseable JSON-LD: {err}")
        types.append("PARSE-ERROR")
        continue
    types.append(data.get("@type"))
    if data.get("@type") == "ItemList":
        itemlist = data
check("block types (set)", ["BreadcrumbList", "ItemList", "Organization"], sorted(types))
positions = [i.get("position") for i in (itemlist or {}).get("itemListElement", [])]
check("ItemList entries", 21, len(positions or []))
check("ItemList positions 1..21", list(range(1, 22)), positions)
crumbs = next((json.loads(b) for b in blocks if '"BreadcrumbList"' in b), {})
crumb_names = [i.get("name") for i in crumbs.get("itemListElement", [])]
visible = [html.unescape(v).strip() for v in re.findall(
    r'class="sf-breadcrumb__crumb[^"]*"[^>]*>([^<]+)<', page)]
check("BreadcrumbList == visible crumb", visible, crumb_names)
check("BreadcrumbList has 2 items", 2, len(crumb_names))

print("=== 4) redirects / status codes ===")
for path, want in [("/formulas/page/2/", 301), ("/formulas/page/3/", 301),
                   ("/formulas/page/4/", 404), ("/zh/formulas/page/2/", 301),
                   ("/zh/formulas/", 200), ("/formulas/", 200)]:
    got, loc = status_of(path)
    check(f"{path}", want, got, got == want)
    if got in (301, 302):
        print(f"          -> {loc}")
    if path == "/zh/formulas/page/2/" and got == 301:
        ok = loc.count("/zh/") == 1 and "/zh/zh/" not in loc
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] "
              f"{'zh redirect keeps exactly one /zh/ prefix':<54} -> {loc}")

print("=== 5) eight dosage pages — the new entry link, live ===")
for form in FORMS:
    code, body = fetch(f"/products/{form}/")
    targets = re.findall(r'<a class="sf-explore__btn" href="([^"]*)">', body)
    n = body.count('<article class="sf-fcard"')
    check(f"/products/{form}/  {n} cards", (["/formulas/", "/products/"], CARDS_PER_FORM[form], 200),
          (sorted(targets), n, code),
          sorted(targets) == ["/formulas/", "/products/"] and n == CARDS_PER_FORM[form] and code == 200)
    check(f"/products/{form}/  link markup", 1, body.count(LINK))
    vals = set(re.findall(r'class="sf-formula__cta" data-formula="[^"]*" data-form="([^"]*)"', body))
    cardforms = set(re.findall(r'<article class="sf-fcard" data-sf-form="([^"]*)"', body))
    check(f"/products/{form}/  data-form values", ({form}, {form}), (vals, cardforms))

print("=== 6) detail page: related grid data-form ===")
detail = re.search(r'<h3 class="sf-fcard__name"><a href="' + re.escape(BASE) +
                   r'/formulas/([a-z0-9-]+)/"', page).group(1)
code, body = fetch(f"/formulas/{detail}/")
vals = re.findall(r'class="sf-formula__cta" data-formula="[^"]*" data-form="([^"]*)"', body)
print(f"  /formulas/{detail}/ — {len(vals)} K1 buttons, form(s)={sorted(set(vals))}")
check("K1 buttons present", True, len(vals) > 0)
check("one single data-form value", 1, len(set(vals)))
check("value is a known form", True, set(vals) <= set(FORMS))

print("=== 7) shipped assets ===")
css = open(f"{THEME}/style.css", encoding="utf-8").read()
js = open(f"{THEME}/assets/js/formula-filter.js", encoding="utf-8").read()
check("CSS 37c hides filtered cards", True, ".sf-fcard.is-sf-off {\n\tdisplay: none;\n}" in css)
check("CSS no-JS guard", True, "html:not(.sf-js) .sf-fchips-wrap {\n\tdisplay: none;\n}" in css)
check("CSS 36a rail covers .sf-fchips", True, ".sf-blog-chips,\n\t.sf-fchips {" in css)
check("CSS header version", "Version: 2.10.44", css.splitlines()[4].strip())
check("JS has no framework", True, "import " not in js and "require(" not in js)
check("JS early-returns without the bar", True, "if (!bar) {" in js)
check("JS toggles the class, never the hidden attr", True,
      "classList.toggle('is-sf-off'" in js and "setAttribute('hidden'" not in js)
served_css = fetch("/wp-content/themes/sinofresh-theme/style.css?ver=2.10.44")[1]
served_js = fetch("/wp-content/themes/sinofresh-theme/assets/js/formula-filter.js?ver=1.0.0")
check("served CSS carries 37c", True, ".sf-fcard.is-sf-off" in served_css)
check("served JS 200 + is the filter", 200, served_js[0])
check("served JS content", True, "sf-fchips" in served_js[1])

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(len(results) - sum(results))
