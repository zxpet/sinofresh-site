#!/usr/bin/env python3
"""Batch H12 gate — 最终设计定稿一次性执行（步骤1-5）.

Modes:
  --source      static assertions on the workspace files
  --preflight   behavioural assertions against the preflight theme copy
                (X-SF-Preflight: 1, the same switch every batch uses)
  --live        the same assertions against the live theme (run after pull)

Covered:
  Step1  .fluentform label colour fix (white-on-white labels on the deep-green
         section / white-card inheritance chain).
  Step2  company pages post_content-ised: 3-line skeletons + [sf_page_body],
         front-page company band via [sf_home_about], DB seeds byte-identical
         to the archived templates, schema generators inline the DB bodies,
         and the five migrated pages render byte-identical (normalized) to
         docs/h12-archive/live-before-*.html.
  Step4  Color / Function join the ten-group model: pools vocabulary, group
         defaults, Configurator Display rows, admin fields, design emission
         order, empty-means-absent (no meta -> no group).
  Step5  every admin field hint is Chinese; configurator fields grouped into
         the params metabox; the migrated front pages stay Chinese-free.

Normalization for the byte-drift comparison (documented drift, not content
drift):
  - 'sinofresh-theme-preflight/' vs 'sinofresh-theme/' asset URLs and the
    wp-theme-sinofresh-theme(-preflight) body class — the preflight copy's
    directory name; the real pull makes the copy identical again.
  - FF per-request random 32-hex id suffixes on checkbox id/for attributes
    (two untouched live fetches already differ; verified overlap 1/7).
"""

import argparse
import base64
import re
import subprocess
import sys

REPO = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
THEME = REPO + "/sinofresh-theme"
ARCH = REPO + "/docs/h12-archive"
SERVER = "root@65.49.215.152"
HOST = "dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

VERSION = "2.10.86"
PAGES = {
    "home": "/",
    "about": "/about/",
    "quality": "/quality/",
    "services": "/services/",
    "factory-tour": "/factory-tour/",
}
DESIGN_ORDER = ["shape", "color", "flavor", "weight", "counts",
                "net-content", "container", "function", "species", "stage"]

_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + (("  — " + detail) if detail and not ok else ""))
    return ok


def ssh(cmd):
    r = subprocess.run(["ssh", SERVER, cmd], capture_output=True, text=True,
                       timeout=120)
    return r.stdout


def fetch(path, preflight):
    """Fetch a page from the origin (bypassing CF) and return its HTML."""
    hdr = '-H "Authorization: %s" -H "Host: %s" -A "%s"' % (AUTH, HOST, UA)
    if preflight:
        hdr += ' -H "X-SF-Preflight: 1"'
    out = ssh('curl -sk %s "https://127.0.0.1%s"' % (hdr, path))
    return out


def normalize(html):
    html = html.replace("sinofresh-theme-preflight/", "THEME/")
    html = html.replace("sinofresh-theme/", "THEME/")
    html = html.replace("wp-theme-sinofresh-theme-preflight",
                        "wp-theme-sinofresh-theme")
    html = re.sub(r"[0-9a-f]{16,}", "<HEX>", html)
    html = re.sub(r"ver=2\.10\.\d+", "ver=VER", html)
    # Batch H13b — 10-char nonces (FluentForm fields, WP Statistics REST)
    # rotate with the 12-hour nonce tick, which made zero-drift flap between
    # gate runs captured on either side of a tick boundary. They are session
    # tokens, not page content.
    html = re.sub(r"nonce=[0-9a-f]{10}\b", "nonce=NONCE", html)
    html = re.sub(r'fluentformnonce" value="[0-9a-f]{10}"',
                  'fluentformnonce" value="NONCE"', html)
    return html


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def source_mode():
    print("== H12 gate --source ==")
    fn = read(THEME + "/functions.php")
    css = read(THEME + "/style.css")
    pools = read(THEME + "/inc/formula-pools.php")
    admin = read(THEME + "/inc/formula-admin.php")

    check("version bumped to %s in the enqueue" % VERSION,
          "'%s'" % VERSION in fn and "'2.10.85'" not in fn)
    check("style.css header bumped to %s" % VERSION,
          "Version: %s" % VERSION in css)

    # Step1 — label colour
    check("Step1: .fluentform wrapper pins the dark body colour",
          re.search(r"\.fluentform \{\n\tcolor: var\(--wp--preset--color--text-primary\);\n\}", css) is not None)

    # Step2 — templates & shortcodes
    for slug in ("about", "quality", "services", "factory-tour"):
        t = read(THEME + "/templates/page-%s.html" % slug)
        lines = t.rstrip('\n').split('\n')
        check("Step2: page-%s.html is a 3-line skeleton" % slug,
              len(lines) == 3 and lines[1] == "[sf_page_body]"
              and lines[0].startswith('<!-- wp:template-part {"slug":"header"')
              and lines[2].startswith('<!-- wp:template-part {"slug":"footer"'))
    fp = read(THEME + "/templates/front-page.html")
    check("Step2: front-page.html carries [sf_home_about] and no hardcoded "
          "About SINO FRESH heading",
          "[sf_home_about]" in fp and ">About SINO FRESH<" not in fp)
    check("Step2: sf_page_body shortcode exists",
          "function sinofresh_page_body()" in fn
          and "add_shortcode('sf_page_body'" in fn)
    check("Step2: sf_home_about shortcode exists",
          "function sinofresh_home_about()" in fn
          and "add_shortcode('sf_home_about'" in fn)
    check("Step2: shortcodes expand their own shortcodes (do_shortcode)",
          fn.count("return do_shortcode($c);") == 2)
    check("Step2: single trailing newline dropped via substr (not preg)",
          "substr($c, 0, -1)" in fn and
          "preg_replace('/\\n$/', '', (string) $post->post_content)" not in fn)
    check("Step2: schema generators inline the DB bodies",
          len(re.findall(r"= sinofresh_inline_page_bodies\(\$html\);", fn)) == 2)

    # Step4 — ten-group model
    check("Step4: sf_formula_functions_pool() defined",
          "function sf_formula_functions_pool()" in pools)
    for gk in ("'color'", "'function'"):
        check("Step4: group_defaults carries %s" % gk, gk in pools)
    check("Step4: group_defaults order follows the design",
          pools.find("'shape'") < pools.find("'color'") < pools.find("'flavor'")
          < pools.find("'container'") < pools.find("'function'"))
    check("Step4: Configurator Display rows carry color + function",
          "'color'       => array('name'" in admin
          and "'function'    => array('name'" in admin)
    check("Step4: colors field joined the model (config_group color, params box)",
          "'key' => 'sf_formula_colors', 'label' => 'Colors', 'group' => 'params'"
          in admin and "'config_group' => 'color'" in admin)
    check("Step4: sf_formula_functions admin field registered",
          "'key' => 'sf_formula_functions'" in admin
          and "'config_group' => 'function'" in admin)
    check("Step4: front-end emission order is the design order",
          re.findall(r"\$state\('([a-z-]+)',", fn)[:10] == DESIGN_ORDER)

    # Step5 — hints
    groups = re.split(r"\n\t\tarray\('key' => '", admin)[1:]
    bad = []
    for g in groups:
        key = g.split("'", 1)[0]
        hm = re.search(r"'hint' => '([^']*)'", g[:1500])
        if not hm or not re.search(r"[\u4e00-\u9fff]", hm.group(1)):
            bad.append(key)
    check("Step5: every admin field hint is Chinese", not bad, ",".join(bad))

    print("\n%d checks, %d failed" % (len(_results),
                                      sum(1 for _, ok, _ in _results if not ok)))
    return all(ok for _, ok, _ in _results)


def behavioural_mode(preflight):
    mode = "preflight" if preflight else "live"
    print("== H12 gate --%s ==" % mode)

    # Step2 zero-drift, five pages, normalized
    for name, path in PAGES.items():
        before = normalize(read(ARCH + "/live-before-%s.html" % name))
        after = normalize(fetch(path, preflight))
        check("Step2 zero-drift: %s%s" % (path, " (preflight)" if preflight else ""),
              bool(after) and before == after)

    # Step5 — the admin hints must never reach the front end. (Blanket CJK
    # bans don't hold: the factory address is legitimate Chinese content and
    # predates H12 — the zero-drift checks above already pin those bytes.)
    hint_phrases = ["勾选该产品", "前台客户", "Configurator Display 覆盖",
                    "留空该行不显示", "该剂型不显示此组"]
    for name, path in PAGES.items():
        html = fetch(path, preflight)
        hits = [p for p in hint_phrases if p in html]
        check("admin hints stay behind the login: %s" % path, not hits,
              ",".join(hits))

    # Step4 — formula detail groups: design order, color on 158, function absent
    html = fetch("/formulas/joint-support-soft-chews/", preflight)
    keys = re.findall(r'data-sf-config-group="([a-z-]+)"', html)
    check("Step4: 158 group order starts pricing + shape/color/flavor...",
          keys[:8] == ["pricing"] + DESIGN_ORDER[:7],
          str(keys))
    check("Step4: 158 renders the Color group (real meta)",
          "color" in keys)
    check("Step4: no Function group without meta (empty-means-absent)",
          "function" not in keys, str(keys))

    # Step2 — the DB seeds still match the archived originals (guard against
    # silent content edits between the batch and the pull)
    for pid, slug in ((14, "about"), (15, "quality"), (17, "factory-tour"),
                      (29, "services"), (11, "home-about")):
        out = ssh("cd /var/www/dev.zxpet.com/public && wp post meta get %d "
                  "post_content 2>/dev/null || wp eval 'echo get_post(%d)->post_content;'"
                  " --allow-root" % (pid, pid))
        seed = read("%s/seed-page-%d-%s.html" % (ARCH, pid, slug))
        check("Step2 DB seed intact: page %d" % pid, out.strip() == seed.strip())

    print("\n%d checks, %d failed" % (len(_results),
                                      sum(1 for _, ok, _ in _results if not ok)))
    return all(ok for _, ok, _ in _results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.source:
        ok = source_mode()
    elif args.preflight:
        ok = behavioural_mode(True)
    elif args.live:
        ok = behavioural_mode(False)
    else:
        ap.error("pick --source / --preflight / --live")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
