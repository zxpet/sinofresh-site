#!/usr/bin/env python3
"""Batch H10 gate — spec-sheet facts (sf_param_*), grouped spec sheet,
Factory & Trust band, and the sf_form_facts option that replaced the eight
templates' hard-coded .sf-facts-mini bands.

Modes:
  --source      static assertions on the workspace files
  --preflight   behavioural assertions against the preflight theme copy
  --live        the same assertions against the live theme (run after pull)

The load-bearing assertion is P1: with the option unset, the band the block
renderer builds must be BYTE-IDENTICAL to the band the eight templates
shipped (git HEAD). The defaults are those template strings character for
character precisely so this can be asserted, not hoped for.
"""

import argparse
import base64
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
THEME = REPO + "/sinofresh-theme"
SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
HOST = "dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CJK = re.compile(r"[\u4e00-\u9fff]")
FORMS = ["soft-chews", "tablets", "dental-chews", "fish-oil",
         "liquids", "pastes", "powders", "drops"]

# This machine flaps between IPv6 and the VPN's IPv4 exit across requests,
# which splits "same IP" assertions across two buckets — force IPv4 (sec1).
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(host, port, *args, **kwargs):
    # callers pass family either positionally (socket.create_connection: 0,
    # SOCK_STREAM) or as a keyword; drop whichever, then pin AF_INET.
    kwargs.pop("family", None)
    if args:
        args = (socket.AF_INET,) + args[1:]
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    return _orig_getaddrinfo(host, port, socket.AF_INET, **kwargs)


socket.getaddrinfo = _ipv4_only

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (("  << " + str(detail)) if (detail and not ok) else ""))


def summary():
    bad = [n for n, ok in RESULTS if not ok]
    print("\n%d/%d passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print("FAILED:")
        for n in bad:
            print("  - " + n)
    return 1 if bad else 0


def read(path):
    with open(THEME + "/" + path, encoding="utf-8") as f:
        return f.read()


def strip_php_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return text


def fetch(path, preflight=False):
    url = "https://%s%s%s" % (HOST, path, ("?sfh10=" + str(int(time.time() * 1000))) if "?" not in path else "&sfh10=" + str(int(time.time() * 1000)))
    req = urllib.request.Request(url)
    req.add_header("Authorization", AUTH)
    req.add_header("User-Agent", UA)
    req.add_header("Accept-Encoding", "identity")
    if preflight:
        req.add_header("X-SF-Preflight", "1")
    for attempt in range(3):
        try:
            with urllib.request.build_opener().open(req, timeout=40) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 2:
                time.sleep(3)
                continue
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:
            if attempt < 2:
                time.sleep(3)
                continue
            raise


def wp(*args):
    cmd = ["ssh", SERVER,
           "cd %s && wp %s --allow-root" % (WP_ROOT, " ".join("'%s'" % a for a in args))]
    out = subprocess.run(cmd, capture_output=True, timeout=90)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode()[-400:])
    return out.stdout.decode().strip()


def git_head_band(form):
    out = subprocess.run(["git", "-C", REPO, "show",
                          "HEAD:sinofresh-theme/templates/page-%s.html" % form],
                         capture_output=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode()[-200:])
    m = re.search(r'(<section class="sf-facts-mini">.*?</section>)', out.stdout.decode(), re.S)
    return m.group(1) if m else ""


def served_band(html):
    m = re.search(r'(<section class="sf-facts-mini">.*?</section>)', html, re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- source mode

def source_mode():
    fn_raw = read("functions.php")
    fn = strip_php_comments(fn_raw)
    admin = read("inc/formula-admin.php")
    css = read("style.css")

    print("== S1 functions.php — the sf_form_facts source swap ==")
    check("sf_form_facts_defaults carries all eight dosage forms",
          all(("'%s'" % f) in fn for f in FORMS))
    check("sf_form_facts_value reads the sf_form_facts option with default fallback",
          "get_option('sf_form_facts', null)" in fn)
    check("spec_cell maps the four data-labels",
          all(k in fn for k in ["'MOQ'               => 'moq'",
                                "'Lead time'         => 'lead'",
                                "'Certifications'    => 'certs'",
                                "'Packaging formats' => 'packaging'"]))
    check("the template-regex reader is gone (single source, no second path)",
          '<section class=\\"sf-facts-mini\\">' not in fn
          and "preg_match('/<section class=" not in fn)
    check("render_block swaps the [SF_FACTS_MINI slug] marker",
          "SF_FACTS_MINI" in fn and "add_filter('render_block'" in fn)
    check("the band builder routes Certifications through the Site Settings chain",
          "sf_formula_certifications_value($form)" in fn)
    check("spec sheet renders the three named groups",
          all(t in fn for t in ["Core Parameters", "Product Specifications", "Packaging & Logistics"]))
    check("trust band is its own section",
          "sf-fdetail-trust" in fn and "sinofresh_formula_trust_html()" in fn)
    check("trust defaults: three factory-tour facts + 24h response, three blank",
          all(k in fn for k in ["sf_trust_factory_size", "sf_trust_cleanroom", "sf_trust_capacity",
                                "sf_trust_export_markets", "sf_trust_ontime",
                                "sf_trust_response", "sf_trust_reorder"])
          and "'15,000㎡'" in fn and "Within 24 hours" in fn)
    check("trust reader: never-saved shows default, stored empty hides the row",
          "get_option($key, null)" in fn and "return trim((string) $stored)" in fn)
    check("spec sheet reads the sf_param_* keys",
          fn.count("sf_param_") >= 13)
    check("version bumped to 2.10.83 in the enqueue",
          "'2.10.83'" in fn and "'2.10.82'" not in fn)
    check("no CJK survives comment-stripping in functions.php",
          CJK.search(fn) is None, CJK.findall(fn)[:5])
    check("style.css header bumped to 2.10.83",
          "Version: 2.10.83" in css)

    print("== S2 formula-admin.php — Spec Sheet group + settings pages ==")
    check("'specsheet' group registered", "'specsheet' => array('title' => 'Spec Sheet'" in admin)
    check("14 sf_param_* fields registered in the specsheet group",
          admin.count("'group' => 'specsheet'") == 14)
    check("the fields carry Chinese hints (admin-only by construction)",
          CJK.search(admin) is not None)
    check("the five configurator keys carry the 158 test-residue annotation",
          admin.count("疑似测试残留") == 5)
    check("sf_form_facts registered with an array sanitiser",
          "register_setting('sf_site_settings', 'sf_form_facts'" in admin)
    check("seven trust options registered without default-forcing",
          "foreach (array_keys(sf_trust_defaults()) as $key)" in admin
          and "'sanitize_callback' => 'sanitize_text_field'" in admin)
    check("Dosage Form Facts submenu page registered",
          "'sf-form-facts', 'sf_render_form_facts_page'" in admin)
    check("meta registration covers the sf_param_* keys",
          all(("'sf_param_%s'" % k) in admin for k in
              ["sample_policy", "inactive_ingredients", "calorie", "adequacy",
               "compliance_markets", "label_language", "label_items", "customizable",
               "private_label", "payment_terms", "primary_packaging",
               "gross_net_weight", "container_load", "storage"]))

    print("== S3 templates — marker in, static band out ==")
    for f in FORMS:
        t = read("templates/page-%s.html" % f)
        check("page-%s.html carries the marker and no static band" % f,
              ("[SF_FACTS_MINI %s]" % f) in t and '<section class="sf-facts-mini">' not in t)


# ------------------------------------------------------------ behaviour modes

def detail_url_of(post_id):
    slug = wp("eval", "echo get_post_field(\"post_name\", %d);" % int(post_id)).strip()
    return "/formulas/%s/" % slug


def one_post_of_form(form):
    php = ("$ids = get_posts(array(\"post_type\" => \"sf_formula\", \"numberposts\" => 1, "
           "\"fields\" => \"ids\", \"orderby\" => \"ID\", \"order\" => \"ASC\", \"tax_query\" => array("
           "array(\"taxonomy\" => \"sf_formula_form\", \"field\" => \"slug\", \"terms\" => \"%s\")))); "
           "echo $ids ? $ids[0] : \"\";" % form)
    return wp("eval", php).strip()


def head_certs_value(band):
    m = re.search(r'data-label="Certifications"[^>]*>(.*?)</span>', band, re.S)
    return m.group(1) if m else ""


def sheet_certs_from(html):
    """The Certifications row the detail page's spec sheet prints — the Site
    Settings line, the chain the dynamic band follows by design."""
    m = re.search(r'Certifications</dt><dd class="sf-fdetail-specs__value">([^<]+)</dd>', html)
    return m.group(1) if m else ""


def behaviour_mode(preflight):
    label = "PREFLIGHT" if preflight else "LIVE"
    print("== %s P1 — band byte-identity (option unset vs git HEAD) ==" % label)
    # make sure the option is absent so the shipped defaults stand
    wp("option", "delete", "sf_form_facts")
    # The three sf_form_facts rows must equal HEAD byte for byte. The
    # Certifications row is the exception BY DESIGN: the dynamic band follows
    # the Site Settings line (the chain the spec sheet already used), and the
    # template hardcode is stale where the two disagree. Measure the site's
    # line from the LIVE detail page and substitute it into the expectation;
    # any residual divergence is then a pure code failure.
    pid = wp("post", "list", "--post_type=sf_formula", "--posts_per_page=1",
             "--field=ID").splitlines()[0].strip()
    s_live, live_html = fetch(detail_url_of(int(pid)), False)
    site_certs = sheet_certs_from(live_html)
    head0 = git_head_band(FORMS[0])
    if site_certs and head_certs_value(head0) != site_certs:
        print("  NOTE pre-existing divergence: template hardcode %r vs Site Settings line %r"
              " — the dynamic band follows Site Settings (single source)."
              % (head_certs_value(head0), site_certs))
    for f in FORMS:
        status, html = fetch("/products/%s/" % f, preflight)
        got = served_band(html)
        want = git_head_band(f)
        want = re.sub(r'(data-label="Certifications"[^>]*>).*?(</span>)',
                      lambda m: m.group(1) + site_certs + m.group(2), want, flags=re.S)
        check("/products/%s/ band byte-identical to HEAD (certs = Site Settings line)" % f,
              status == 200 and got != "" and got == want,
              "status=%s equal=%s" % (status, got == want))
        time.sleep(1.3)

    print("== %s P2 — detail page: groups, trust band, no CJK, empty-means-absent ==" % label)
    detail = detail_url_of(int(pid))
    status, html = fetch(detail, preflight)
    check("detail page served (%s)" % detail, status == 200)
    check("three group headings render",
          all(t in html for t in ["Core Parameters", "Product Specifications", "Packaging &amp; Logistics"]))
    check("trust band renders with the shipped defaults",
          "sf-fdetail-trust" in html and "Factory &amp; Trust" in html
          and "15,000㎡" in html and "ISO 8" in html and "30+ countries" in html
          and "Within 24 hours" in html)
    check("trust band hides the three blank facts",
          "Annual Capacity" not in html and "On-time Delivery" not in html
          and "Reorder Rate" not in html)
    check("front-end HTML has zero CJK ideographs",
          CJK.search(html) is None, CJK.findall(html)[:5])
    check("unfilled sf_param_* rows stay absent (empty-means-absent)",
          "Inactive Ingredients" not in html and "Payment Terms" not in html)
    check("right-column params band still renders",
          'sf-fdetail2__params' in html)
    time.sleep(1.3)

    print("== %s P3 — JSON-LD additionalProperty zero drift ==" % label)
    props = {}
    for pf in (False, True):
        s, h = fetch(detail, pf)
        m = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S)
        blocks = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S)
        found = None
        for b in blocks:
            try:
                data = json.loads(b)
            except Exception:
                continue
            graph = data.get("@graph", [data]) if isinstance(data, dict) else []
            for node in graph:
                if isinstance(node, dict) and node.get("@type") in ("Product", "IndividualProduct"):
                    ap = node.get("additionalProperty")
                    if ap:
                        found = ap
        props[pf] = found
        time.sleep(1.3)
    check("Product schema additionalProperty identical live vs preflight",
          props[False] is not None and props[False] == props[True],
          "live=%s preflight=%s" % (props[False], props[True]))

    print("== %s P4 — option override: one row edits all surfaces ==" % label)
    new_moq = "from 42 units (gate probe)"
    payload = json.dumps({"tablets": {"moq": new_moq}})
    wp("option", "update", "sf_form_facts", "--format=json", payload)
    try:
        s, html = fetch("/products/tablets/", preflight)
        check("dosage page band follows the option", new_moq in html)
        time.sleep(1.3)
        tid = one_post_of_form("tablets")
        if tid:
            tdetail = detail_url_of(int(tid))
            s, th = fetch(tdetail, preflight)
            check("detail hero/spec sheet follows the option (single read function)",
                  new_moq in th)
            time.sleep(1.3)
        else:
            check("detail hero follows the option (no tablets record to test)", False,
                  "no tablets record found")
    finally:
        wp("option", "delete", "sf_form_facts")
    s, html = fetch("/products/tablets/", preflight)
    want = git_head_band("tablets")
    want = re.sub(r'(data-label="Certifications"[^>]*>).*?(</span>)',
                  lambda m: m.group(1) + site_certs + m.group(2), want, flags=re.S)
    check("option deleted: band back to the HEAD bytes",
          served_band(html) == want)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.source:
        source_mode()
    elif args.preflight:
        behaviour_mode(preflight=True)
    elif args.live:
        behaviour_mode(preflight=False)
    else:
        ap.error("pick --source / --preflight / --live")
    sys.exit(summary())


if __name__ == "__main__":
    main()
