#!/usr/bin/env python3
"""b3j gate — GF removal + FF hooks live checks.

Run:  python3 tools/b3j_gf_removal_check.py [--live]
Exit code 0 = all assertions green.

Sections:
  S1 static  — repo: zero GF code in the live theme, FF hooks in place
  S2 live    — dev.zxpet.com: pages serve FF forms, WA hint, no GF markup
  S3 live    — REST article-feedback: valid vote stored, invalid vote 400
  S4 server  — plugin gone, options clean, backup in place
"""
import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

THEME = pathlib.Path(__file__).resolve().parent.parent / "sinofresh-theme"
BASE = "https://dev.zxpet.com"
AUTH = "sfdev:VkEws18Kl5V1qp3TpZ6s"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_results = []


def check(name, ok, detail=None):
    _results.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f"  | {detail}" if detail and not ok else ""))
    return ok


def fetch(path, data=None, want_json=False):
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", "Basic " + base64.b64encode(AUTH.encode()).decode())
    req.add_header("User-Agent", UA)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
        req.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req, body, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def ssh(*cmd):
    p = subprocess.run(["ssh", "root@65.49.215.152", "cd /var/www/dev.zxpet.com/public && " + " ".join(cmd)],
                       capture_output=True, text=True, timeout=120)
    return p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also run live/server sections")
    args = ap.parse_args()

    # ---------- S1 static ----------
    print("--- S1 static (repo) ---")
    fn = (THEME / "functions.php").read_text(encoding="utf-8")
    check("S1.1 functions.php: zero executable GF code (gform_ / GFAPI / rg_gforms / GFFormDisplay)",
          not re.search(r"gform_|GFAPI|rg_gforms|GFFormDisplay|gform_update_meta", fn))
    check("S1.2 functions.php: FF confirmation hook in place",
          "fluentform/form_submission_confirmation" in fn)
    check("S1.3 functions.php: FF submission_inserted hook in place",
          "fluentform/submission_inserted" in fn)
    check("S1.4 functions.php: FF button render filter in place (WA hint)",
          "fluentform/rendering_field_html_button" in fn)
    check("S1.5 functions.php: lead tracking listens for FF success event",
          "fluentform_submission_success" in fn)
    check("S1.6 functions.php: feedback endpoint writes FF row (wpFluent insert)",
          "table('fluentform_submissions')->insertGetId" in fn)
    check("S1.7 cert-modal.js: zero GF references (gform / gf_submitting / jQuery postback)",
          not re.search(r"gform|gf_submitting|gform_confirmation_loaded",
                        (THEME / "assets" / "js" / "cert-modal.js").read_text(encoding="utf-8")))
    js = (THEME / "assets" / "js" / "cert-modal.js").read_text(encoding="utf-8")
    for needle in ("fluentform_11", "certificate_10", "fluentform_submission_success",
                   "sf-cert-result", "ff-message-success"):
        check(f"S1.8 cert-modal.js: {needle} present", needle in js)
    check("S1.9 functions.php: cert-modal cache-buster bumped to 1.3.0",
          "cert-modal.js', array(), '1.3.0'" in fn)
    templates = list((THEME / "templates").glob("*.html"))
    gf_tpl = [t.name for t in templates if "gravityforms" in t.read_text(encoding="utf-8")]
    check("S1.10 templates: zero gravityforms blocks", not gf_tpl, str(gf_tpl))

    if not args.live:
        ok = all(_results)
        print(f"\nb3j static gate: {sum(_results)}/{len(_results)} " + ("GREEN" if ok else "RED"))
        sys.exit(0 if ok else 1)

    # ---------- S2 live pages ----------
    print("--- S2 live pages ---")
    time.sleep(0.5)
    st, home = fetch("/")
    check("S2.1 / is 200", st == 200, str(st))
    h = home.decode("utf-8", "replace")
    check("S2.2 / renders FF form (frm-fluent-form)", "frm-fluent-form" in h)
    check("S2.3 / WA hint rendered", "sf-gf-wa-hint" in h)
    check("S2.4 / zero GF markup (gform/gravityforms)", not re.search(r"gform|gravityforms", h))
    time.sleep(0.5)
    st, qual = fetch("/quality/")
    check("S2.5 /quality/ is 200", st == 200, str(st))
    q = qual.decode("utf-8", "replace")
    check("S2.6 /quality/ cert hidden field in place", "certificate_10" in q)
    check("S2.7 /quality/ cert modal present", "sf-certmodal" in q)
    check("S2.8 /quality/ zero GF markup", not re.search(r"gform|gravityforms", q))
    time.sleep(0.5)
    st, contact = fetch("/contact/")
    check("S2.9 /contact/ is 200 and renders FF form", st == 200 and "frm-fluent-form" in contact.decode("utf-8", "replace"))
    check("S2.10 /contact/ WA hint present (form 8 page)",
          "sf-gf-wa-hint" in contact.decode("utf-8", "replace"))
    time.sleep(0.5)
    st, tour = fetch("/factory-tour/")
    t = tour.decode("utf-8", "replace")
    check("S2.11 /factory-tour/ renders form 10 and no form 8",
          st == 200 and "fluentform_10" in t and "fluentform_8" not in t)
    check("S2.12 /factory-tour/ no WA hint (negative control)",
          "sf-gf-wa-hint" not in t)

    # ---------- S3 REST ----------
    print("--- S3 REST article-feedback ---")
    time.sleep(0.5)
    st, body = fetch("/wp-json/sinofresh/v1/article-feedback", data={"vote": "up"})
    check("S3.1 valid vote -> 200 {ok:true}", st == 200 and json.loads(body).get("ok") is True,
          f"{st} {body[:80]}")
    time.sleep(0.5)
    st, body = fetch("/wp-json/sinofresh/v1/article-feedback", data={"vote": "sideways"})
    check("S3.2 invalid vote -> 400", st == 400, str(st))

    # ---------- S4 server ----------
    print("--- S4 server (wp-cli) ---")
    out = ssh("wp plugin list --field=name --allow-root")
    check("S4.1 gravityforms plugin deleted", "gravityforms" not in out.split())
    out = ssh("wp db query \"SELECT COUNT(*) AS c FROM wp_options WHERE option_name LIKE '%gform%' OR option_name LIKE '%gravityforms%'\" --allow-root")
    check("S4.2 zero GF options left (fake key rg_gforms_key included)",
          re.search(r"\b0\b", out.split("c")[-1] if "c" in out else out) is not None, out[:120])
    out = ssh("wp db search gpltimes --all-tables --allow-root 2>/dev/null")
    check("S4.3 zero gpltimes (pirate feed) anywhere in DB", "gpltimes" not in out, out[:120])
    out = ssh("test -s /root/gf-tables-backup-20260925.sql && echo present")
    check("S4.4 GF tables backup exists (/root/gf-tables-backup-20260925.sql)", "present" in out)
    out = ssh("wp eval \"echo function_exists('wpFluent') ? 'ff-active' : 'ff-missing';\" --allow-root")
    check("S4.5 Fluent Forms active", "ff-active" in out)

    ok = all(_results)
    print(f"\nb3j gate: {sum(_results)}/{len(_results)} " + ("GREEN" if ok else "RED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
