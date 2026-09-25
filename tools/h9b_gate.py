#!/usr/bin/env python3
"""Batch H9b gate — Site Settings → Form Options, the single source for the
three shared Fluent Forms select lists (Country, Target Market, Interested
Dosage Form) that previously lived as 11 independent copies inside the FF
field definitions.

Modes:
  --source      static assertions on the workspace files
  --preflight   behavioural assertions against the preflight theme copy
  --live        the same assertions against the live theme (run after pull)

Load-bearing contract: with the sf_form_options option absent, every select
renders FF's own stored options — front-end bytes identical to pre-H9b.
P2 proves the edit-once-sync-everywhere claim with probe entries; P3 proves
the rollback (delete the option → byte-identical to P1).

State guard: if the option exists at the start of a behavioural run and
contains the probe marker, a previous run died before its finally — the
stale value is deleted, not backed up (the h11 "restored to sink" lesson).
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
PROBE = "GATE9B"

# form id → (probe page, selects expected on it)
PAGES = {
    8:  "/contact/",
    9:  "/services/",
    10: "/factory-tour/",
    11: "/quality/",
}

# This machine flaps between IPv6 and the VPN's IPv4 exit across requests,
# which can split assertions across two responses — force IPv4 (sec1).
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(host, port, *args, **kwargs):
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
    url = "https://%s%s?sfh9b=%d" % (HOST, path, int(time.time() * 1000))
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


def wp_php(code):
    subprocess.run(["ssh", SERVER, "cat > /tmp/h9b-snippet.php"],
                   input=code.encode(), check=True, timeout=30)
    out = wp("eval-file", "/tmp/h9b-snippet.php")
    # not `wp eval unlink(...)`: the nested quotes die in the two-shell hop
    subprocess.run(["ssh", SERVER, "rm -f /tmp/h9b-snippet.php"], timeout=30)
    return out


def get_option_raw():
    return wp_php(('<?php\n'
                   '$o = get_option("sf_form_options", null);\n'
                   'echo $o === null ? "__UNSET__" : json_encode($o);'))


def delete_option():
    return wp_php(('<?php\n'
                   'delete_option("sf_form_options"); echo "deleted";'))


def set_probe_option():
    return wp_php(('<?php\n'
                   'update_option("sf_form_options", array(\n'
                   '  "dosage_forms"   => "GATE9B Form\\nSoft Chews",\n'
                   '  "countries"      => "GATE9B Country\\nGermany",\n'
                   '  "target_markets" => "GATE9B Market\\nEU",\n'
                   ')); echo "set";'))


# FF renders the select's stored options; read them from the DB so P1
# compares rendered vs stored, not rendered vs a hand-typed list.
def stored_ff_options():
    out = wp_php(('<?php\n'
                  '$out = array();\n'
                  'foreach (array(8, 9, 10, 11) as $fid) {\n'
                  '  $form = wpFluent()->table("fluentform_forms")->find($fid);\n'
                  '  $fields = json_decode($form->form_fields, true);\n'
                  '  foreach ($fields["fields"] as $f) {\n'
                  '    if ($f["element"] !== "select") continue;\n'
                  '    $name = $f["attributes"]["name"];\n'
                  '    $key = null;\n'
                  '    if (strpos($name, "country_") === 0) $key = "countries";\n'
                  '    if (strpos($name, "target_market_") === 0) $key = "target_markets";\n'
                  '    if (strpos($name, "interested_dosage_form_") === 0) $key = "dosage_forms";\n'
                  '    if (!$key) continue;\n'
                  '    foreach ($f["settings"]["advanced_options"] as $o) {\n'
                  '      $out[$fid][$key][] = (isset($o["value"]) && $o["value"] !== "") ? $o["value"] : $o["label"];\n'
                  '    }\n'
                  '  }\n'
                  '}\n'
                  'echo json_encode($out);'))
    # PHP int keys become JSON *string* keys — normalise back to int or every
    # .get(fid) silently misses and the gate runs green with zero coverage.
    return {int(k): v for k, v in json.loads(out).items()}


def select_options(html, prefix):
    """All option values of the select whose field name starts with prefix."""
    vals = []
    for m in re.finditer(r'<select[^>]*name="%s[^"]*"[^>]*>(.*?)</select>' % re.escape(prefix), html, re.S):
        vals.extend(re.findall(r'<option[^>]*value="([^"]*)"', m.group(1)))
    return [v for v in vals if v != ""]


# ---------------------------------------------------------------- source mode

def source_mode():
    fn = strip_php_comments(read("functions.php"))
    admin = strip_php_comments(read("inc/formula-admin.php"))
    css = read("style.css")

    check("render filter is hooked (per-element select data)",
          "add_filter('fluentform/rendering_field_data_select'" in fn)
    check("prefix map covers the three shared lists",
          all(p in fn for p in ["'country_'", "'target_market_'", "'interested_dosage_form_'"]))
    check("empty list rewrites nothing (empty-means-absent fallback)",
          re.search(r"if\s*\(\s*\$list\s*\)\s*\{", fn) is not None)
    check("matching is by name prefix, not equality (FF suffixes are unstable)",
          "strpos($name, $prefix) === 0" in fn)

    check("sf_form_options registered on the settings group",
          "register_setting('sf_site_settings', 'sf_form_options'" in admin)
    check("sanitize drops unknown keys",
          "array_keys(sinofresh_form_options_defaults())" in admin)
    check("Form Options submenu page registered",
          "add_submenu_page('sf-site-settings', 'Form Options'" in admin)
    check("page renders the three textareas (one loop over three lists)",
          "sf_render_form_options_page" in admin
          and all(("'%s'" % k) in admin for k in ["dosage_forms", "countries", "target_markets"])
          and "sf_form_options[" in admin)
    check("defaults ship the shipped option text",
          "Soft Chews" in fn and "United States" in fn and "'US'" in fn)

    check("version bumped to 2.10.85 in the enqueue",
          "'2.10.85'" in fn and "'2.10.84'" not in fn)
    check("style.css header bumped to 2.10.85",
          "Version: 2.10.85" in css)
    return summary()


# ----------------------------------------------------------- behavioural mode

def behaviour_mode(preflight):
    tag = "preflight" if preflight else "live"

    raw = get_option_raw()
    if raw != "__UNSET__" and PROBE in raw:
        print("NOTE stale probe option from a killed run — deleting, not backing up")
        delete_option()
        raw = get_option_raw()
    had_option = raw != "__UNSET__"
    snapshot = None if not had_option else raw

    try:
        # P1 — default: option absent (or backed up) → selects render FF's own options.
        if had_option:
            delete_option()
            time.sleep(1)
        stored = stored_ff_options()
        baseline = {}
        for fid, path in PAGES.items():
            status, html = fetch(path, preflight=preflight)
            check("P1 [%s] form %d page served (%s)" % (tag, fid, path), status == 200)
            for key, prefix in (("countries", "country_"), ("target_markets", "target_market_"),
                                ("dosage_forms", "interested_dosage_form_")):
                if key not in stored.get(fid, {}):
                    continue
                got = select_options(html, prefix)
                baseline[(fid, key)] = got
                check("P1 [%s] form %d %s select = FF stored options (zero drift)"
                      % (tag, fid, key), got == stored[fid][key],
                      "got=%s want=%s" % (got, stored[fid][key]))

        # P2 — probe: one option edit reaches every form at once.
        set_probe_option()
        time.sleep(1)
        for fid, path in PAGES.items():
            status, html = fetch(path, preflight=preflight)
            check("P2 [%s] form %d page served" % (tag, fid), status == 200)
            check("P2 [%s] form %d Country list follows the option (probe first)"
                  % (tag, fid), select_options(html, "country_")[:1] == [PROBE + " Country"],
                  select_options(html, "country_")[:2])
            check("P2 [%s] form %d Dosage Form list follows the option"
                  % (tag, fid), select_options(html, "interested_dosage_form_")[:1] == [PROBE + " Form"],
                  select_options(html, "interested_dosage_form_")[:2])
            if "target_markets" in stored.get(fid, {}):
                check("P2 [%s] form %d Target Market list follows the option"
                      % (tag, fid), select_options(html, "target_market_")[:1] == [PROBE + " Market"],
                      select_options(html, "target_market_")[:2])
            check("P2 [%s] form %d old copies still render after the probe entry"
                  % (tag, fid), "Germany" in select_options(html, "country_")
                  or fid not in stored)

        # P3 — rollback: delete the option → back to the P1 bytes.
        delete_option()
        time.sleep(1)
        for fid, path in PAGES.items():
            status, html = fetch(path, preflight=preflight)
            for key, prefix in (("countries", "country_"), ("target_markets", "target_market_"),
                                ("dosage_forms", "interested_dosage_form_")):
                if (fid, key) not in baseline:
                    continue
                check("P3 [%s] form %d %s byte-identical after rollback"
                      % (tag, fid, key),
                      select_options(html, prefix) == baseline[(fid, key)],
                      select_options(html, prefix)[:3])
    finally:
        # Never leave probe state behind: restore what was there, or delete.
        if had_option and snapshot is not None:
            subprocess.run(["ssh", SERVER, "cat > /tmp/h9b-snap.json"],
                           input=snapshot.encode(), check=True, timeout=30)
            wp_php(('<?php\n'
                    '$snap = json_decode(file_get_contents("/tmp/h9b-snap.json"), true);\n'
                    'update_option("sf_form_options", $snap); unlink("/tmp/h9b-snap.json"); echo "restored";'))
        else:
            delete_option()
    return summary()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", action="store_true")
    g.add_argument("--preflight", action="store_true")
    g.add_argument("--live", action="store_true")
    a = ap.parse_args()
    if a.source:
        sys.exit(source_mode())
    sys.exit(behaviour_mode(preflight=a.preflight))
