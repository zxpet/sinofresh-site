#!/usr/bin/env python3
"""Batch2C Step2 sub-items 3+4 — server-side pre-flight assertions.

Run ON the dev box against the header-gated pre-flight theme:

    python3 b2c_s2_preflight_check.py            # defaults below

Every check is one line: PASS/FAIL, the expectation and what was found. Exit
code is the number of failures, so the caller can gate on it.

Checks that need the database (card order) shell out to wp-cli on the same
box; everything else is a plain HTTP fetch.
"""

import html
import json
import re
import subprocess
import sys
import urllib.request

BASE = "https://dev.zxpet.com"
# A browser-like UA: Cloudflare answers Python-urllib with 403.
HEADER = {"X-SF-Preflight": "1", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                                             "Chrome/124.0 Safari/537.36"}
WP_PATH = "/var/www/dev.zxpet.com/public"

FORMS = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]

results = []


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {name:<52} expect={expected!r} got={actual!r}")


def fetch(path, header=True):
    req = urllib.request.Request(BASE + path, headers=HEADER if header else {})
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def status_of(path):
    """Status + Location WITHOUT following the redirect."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(BASE + path, headers=HEADER)) as resp:
            return resp.status, resp.headers.get("Location") or ""
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Location") or ""


def db_card_order():
    sql = ("SELECT post_title FROM wp_posts WHERE post_type='sf_formula' "
           "AND post_status='publish' ORDER BY menu_order ASC, post_title ASC;")
    out = subprocess.run(
        ["wp", "db", "query", sql, f"--path={WP_PATH}", "--allow-root", "--skip-column-names"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [html.unescape(line) for line in out.splitlines() if line.strip()]


print("=== 1) /formulas/ structure ===")
code, page = fetch("/formulas/")
check("HTTP status", 200, code)
cards = re.findall(r'<article class="sf-fcard" data-sf-form="([^"]*)"', page)
check("cards (.sf-fcard with data-sf-form)", 21, len(cards))
check("cards total (.sf-fcard)", 21, page.count('<article class="sf-fcard"'))
chips = re.findall(r'<button type="button" class="sf-fchip[^"]*" data-sf-form="([^"]*)"', page)
check("chips", 9, len(chips))
check("chip order (All + 8 forms)", ["all"] + FORMS, chips)
check("data-formula on K1", 21, len(re.findall(r'data-formula="', page)))
check("data-form on K1", 21, page.count('data-form="'))
forms_used = {}
for form in cards:
    forms_used[form] = forms_used.get(form, 0) + 1
check("cards per form", {f: 0 for f in FORMS} | {"soft-chews": 4, "tablets": 3, "powders": 3,
      "dental-chews": 3, "pastes": 2, "drops": 2, "liquids": 2, "fish-oil": 2}, forms_used)

print("=== 2) card order vs database ===")
names = [html.unescape(m) for m in re.findall(
    r'<h3 class="sf-fcard__name">(?:<a [^>]*>)?(.*?)(?:</a>)?</h3>', page)]
db = db_card_order()
check("rendered card count", 21, len(names))
check("rendered order == DB (menu_order ASC, title ASC)", True, names == db)
if names != db:
    for i, (a, b) in enumerate(zip(names, db)):
        if a != b:
            print(f"       first difference at #{i + 1}: rendered={a!r} db={b!r}")
            break

print("=== 3) enqueues, marker, versions, residue ===")
check("sf-js head marker", 1, page.count("classList.add('sf-js')"))
check("formulas.js enqueued", 1, len(re.findall(r'assets/js/formulas\.js\?ver=', page)))
check("formula-filter.js enqueued", 1, len(re.findall(r'assets/js/formula-filter\.js\?ver=', page)))
ver = re.findall(r'style\.css\?ver=([0-9.]+)', page)
check("style.css version", ["2.10.44"], sorted(set(ver)))
check("{{ residue", 0, page.count("{{"))
check("[sf_ residue", 0, page.count("[sf_"))
check("hero count line", "21 formulas", re.search(
    r'sf-archive-count[^>]*>([^<]*)<', page).group(1).strip() if "sf-archive-count" in page else "missing")
check("status line has count span", 21, int(re.search(
    r'<span class="sf-fchips-count">(\d+)</span>', page).group(1)) if "sf-fchips-count" in page else -1)
check("status line role=status", 1, page.count('class="sf-fchips-status" role="status"'))

print("=== 4) JSON-LD ===")
blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
types = []
itemlist = None
for block in blocks:
    try:
        data = json.loads(block)
    except Exception as err:
        print(f"       !! unparseable JSON-LD block: {err}")
        types.append("PARSE-ERROR")
        continue
    types.append(data.get("@type"))
    if data.get("@type") == "ItemList":
        itemlist = data
check("JSON-LD block types (set)", ["BreadcrumbList", "ItemList", "Organization"], sorted(types))
positions = [i.get("position") for i in (itemlist or {}).get("itemListElement", [])]
check("ItemList entries", 21, len(positions or []))
check("ItemList positions 1..21", list(range(1, 22)), positions)
crumbs = next((json.loads(b) for b in blocks if '"BreadcrumbList"' in b), {})
crumb_names = [i.get("name") for i in crumbs.get("itemListElement", [])]
visible = [html.unescape(v).strip() for v in re.findall(
    r'class="sf-breadcrumb__crumb[^"]*"[^>]*>([^<]+)<', page)]
check("BreadcrumbList items == visible crumb", visible, crumb_names)

print("=== 5) redirects / status codes ===")
for path, want in [("/formulas/page/2/", 301), ("/formulas/page/3/", 301),
                   ("/formulas/page/4/", 404), ("/zh/formulas/page/2/", 301),
                   ("/zh/formulas/", 200), ("/formulas/", 200)]:
    code, loc = status_of(path)
    check(f"{path}", want, code, code == want)
    if want == 301:
        print(f"          -> {loc}")

print("=== 6) dosage pages: data-form value unchanged ===")
for form in FORMS:
    code, body = fetch(f"/products/{form}/")
    vals = set(re.findall(r'class="sf-formula__cta" data-formula="[^"]*" data-form="([^"]*)"', body))
    cardforms = set(re.findall(r'<article class="sf-fcard" data-sf-form="([^"]*)"', body))
    n = body.count('<article class="sf-fcard"')
    check(f"/products/{form}/  ({n} cards)", ({form}, {form}, code), (vals, cardforms, code),
          vals == {form} and cardforms == {form} and code == 200)

print("=== 7) detail page: related grid data-form repaired ===")
# Take the slug from a card title link, not from any /formulas/… href — the
# head carries the post-type feed at /formulas/feed/.
detail = re.search(r'<h3 class="sf-fcard__name"><a href="' + re.escape(BASE) +
                   r'/formulas/([a-z0-9-]+)/"', page).group(1)
code, body = fetch(f"/formulas/{detail}/")
vals = re.findall(r'class="sf-formula__cta" data-formula="[^"]*" data-form="([^"]*)"', body)
print(f"  detail page: /formulas/{detail}/  ({len(vals)} K1 buttons, form(s)={sorted(set(vals))})")
check("K1 buttons present", True, len(vals) > 0)
check("all data-form values are one dosage form", 1, len(set(vals)))
check("value is not the formula slug", True, detail not in set(vals))
check("value is a known form", True, set(vals) <= set(FORMS))

print("=== 8) shipped CSS/JS content ===")
# Two assertions per asset: the file on disk (content) and the URL the page
# actually references (serving). The pre-flight copy is a real theme directory,
# so unlike a theme_root swap these URLs resolve to the new bytes.
PRE = "/var/www/dev.zxpet.com/public/wp-content/themes/sinofresh-theme-preflight"
css = open(f"{PRE}/style.css", encoding="utf-8").read()
js = open(f"{PRE}/assets/js/formula-filter.js", encoding="utf-8").read()
check("CSS 37c: .sf-fcard.is-sf-off hides", True,
      ".sf-fcard.is-sf-off {\n\tdisplay: none;\n}" in css)
check("CSS no-JS guard", True, "html:not(.sf-js) .sf-fchips-wrap {\n\tdisplay: none;\n}" in css)
check("CSS 36a rail covers .sf-fchips", True, ".sf-blog-chips,\n\t.sf-fchips {" in css)
check("CSS header version", "Version: 2.10.44", css.splitlines()[4].strip())
check("JS has no framework import", True, "import " not in js and "require(" not in js)
check("JS early-returns without the bar", True, "if (!bar) {" in js)
check("JS toggles the class, never the hidden attr", True,
      "classList.toggle('is-sf-off'" in js and "setAttribute('hidden'" not in js
      and "'.hidden'" not in js and '.hidden"' not in js)
served_css = fetch("/wp-content/themes/sinofresh-theme-preflight/style.css?ver=2.10.44")[1]
served_js = fetch("/wp-content/themes/sinofresh-theme-preflight/assets/js/formula-filter.js?ver=1.0.0")[1]
check("served CSS carries 37c", True, ".sf-fcard.is-sf-off" in served_css)
check("served JS is the filter script", True, "formula-filter.js" in served_js or
      "sf-fchips" in served_js)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(len(results) - sum(results))
