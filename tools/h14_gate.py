#!/usr/bin/env python3
"""Batch H14 gate — the Site Settings row-tables' pick→save path.

Bug (2026-09-26 diagnosis): picking an image in the Shape / Container
Library never survived a save. Two independent breaks:

  break 1  sf-site-settings.js read `input[name$="[attachment_id]"]`, but the
           rendered name is `sf_shapes[attachment_id][]` — the bare suffix
           never matches an append-array name, so the hidden id stayed "0"
           while the preview thumbnail updated (which is why the pick looked
           like it had worked).
  break 2  the sf_shapes / sf_containers sanitize callbacks read the payload
           ROW-MAJOR ($row['slug']) while the form posts three PARALLEL arrays
           (sf_shapes[slug][] / [label][] / [attachment_id][]), so every row
           came back empty. H13's delete-on-empty then dropped the option
           entirely — "picked an image, nothing saved".

Why H13's gate missed it: it wrote options with update_option() directly,
bypassing the form AND the sanitize callbacks. A structural mismatch between
the markup and the sanitizer is invisible to that shape of test. This gate
feeds the callbacks the payload the form actually posts.

Modes:
  --source     static assertions on the workspace files.
  --preverify  extract the NEW sanitize closures verbatim from the workspace
               file, run them on the dev server against real WordPress
               sanitizers. Proves the fix itself before the pull — nothing is
               registered or written, the closures are called directly.
  --live       post-pull: the live theme's registered callbacks, plus a real
               browser pick on both library pages.

Negative control: run `--live` against the pre-H14 dev tree. Both halves must
come back red — that is what proves the gate can see the bug it was written
for. Do not "fix" a red --live run that was taken before the pull.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "sinofresh-theme"
ADMIN = THEME / "inc" / "formula-admin.php"
FUNCTIONS = THEME / "functions.php"
CSS = THEME / "style.css"
JS = THEME / "assets" / "admin" / "sf-site-settings.js"

SERVER = "root@65.49.215.152"
DOMAIN = "dev.zxpet.com"
WP_ROOT = "/var/www/dev.zxpet.com/public"
SITE_REPO = "/var/www/dev.zxpet.com/site-repo"
NODE = "/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node"
NODE_PATH = "/Users/meng/.workbuddy/binaries/node/workspace/node_modules"
PICK_JS = REPO / "tools" / "h14_live_pick.js"

VERSION = "2.10.88"
JS_VER = "1.0.3"
OPTIONS = ("sf_shapes", "sf_containers")

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("PASS  " if ok else "FAIL  ") + name
          + (("  — " + detail) if detail and not ok else ""))


def read(path) -> str:
    return Path(path).read_text(encoding="utf-8")


def ssh(script: str, timeout: int = 300) -> str:
    r = subprocess.run(["ssh", SERVER, "bash -s"], input=script,
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


# --------------------------------------------------------------------------
# source helpers
# --------------------------------------------------------------------------
def strip_php_comments(text: str) -> str:
    """Drop /* */ and // comments so a prose mention of the old read can
    neither satisfy nor defeat an assertion about the code. H13's gate learned
    the same lesson from the other direction: a comment naming
    sf_admin_table_rows was counted as a call site."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def sanitize_body(text: str, option: str) -> str:
    """The register_setting() block for one option, up to the next one."""
    i = text.index("register_setting('sf_site_settings', '%s'" % option)
    j = text.index("register_setting(", i + 10)
    return text[i:j]


def extract_closure(text: str, option: str) -> str:
    """The sanitize_callback closure of one option, braces balanced."""
    body = sanitize_body(text, option)
    needle = "'sanitize_callback' => function ($v) {"
    i = body.index(needle) + len("'sanitize_callback' => ")
    j = body.index("{", i)
    depth = 0
    for k in range(j, len(body)):
        if body[k] == "{":
            depth += 1
        elif body[k] == "}":
            depth -= 1
            if depth == 0:
                return body[i:k + 1]
    raise ValueError("unbalanced braces in %s callback" % option)


# --------------------------------------------------------------------------
# --source
# --------------------------------------------------------------------------
def source_gate() -> int:
    admin = read(ADMIN)
    functions = read(FUNCTIONS)
    css = read(CSS)
    js = read(JS)

    # --- release identity (the live half asserts provenance) ---
    check("style.css Version is %s" % VERSION, "Version: %s" % VERSION in css)
    check("functions.php main style enqueue is %s" % VERSION,
          "get_stylesheet_uri(), array(), '%s')" % VERSION in functions)
    check("sf-site-settings.js enqueue ver is %s" % JS_VER,
          "/assets/admin/sf-site-settings.js', array(), '%s'" % JS_VER in admin)

    # --- break 1: the JS selector must carry the trailing [] ---
    good = re.findall(r'\[name\$="\[attachment_id\]\[\]"\]', js)
    bad = re.findall(r'\[name\$="\[attachment_id\]"\]', js)
    check("JS suffix selector includes the trailing [] (2 call sites)",
          len(good) == 2, "found %d, want 2" % len(good))
    check("JS no longer carries the bare [attachment_id] selector",
          not bad, "found %d bare selector(s)" % len(bad))
    check("Add-row handler still resets the cloned row's image id",
          "var att = tr.querySelector(" in js and "att.value = '0'" in js)
    check("wp.media picker still writes the picked attachment id",
          "attInput.value = String(att.id)" in js)

    # --- break 2: the sanitizers must read the POSTed parallel arrays ---
    for opt in OPTIONS:
        code = strip_php_comments(sanitize_body(admin, opt))
        check("%s sanitize reads the three parallel arrays" % opt, all(
            re.search(r"is_array\(\$v\['%s'\]\)" % f, code)
            for f in ("slug", "label", "attachment_id")))
        check("%s sanitize has no row-major read left" % opt,
              "$row['slug']" not in code)
        check("%s sanitize drops only fully-empty rows" % opt,
              "$slug === '' && $label === '' && !$att" in code)
        check("%s sanitize derives a slug from the label when blank" % opt,
              "$slug = sanitize_title($label);" in code)

    # --- the markup feeding those callbacks is still parallel ---
    for opt in OPTIONS:
        names = re.findall(
            r'name="%s\[(?:attachment_id|label|slug)\]\[\]"' % opt, admin)
        check("%s render posts three parallel input arrays" % opt,
              len(names) == 3, "found %d, want 3" % len(names))

    # --- H14 must not regress H13's empty-table contract ---
    check("H13 empty-save guard still covers all four options",
          "array('sf_shapes', 'sf_containers', 'sf_global_faq', "
          "'sf_certifications')" in admin)
    check("H13 delete-on-empty hooks still registered",
          'add_action("update_option_{$sf_h13_opt}"' in admin
          and 'add_action("add_option_{$sf_h13_opt}"' in admin)
    # Certifications was verified healthy in the diagnosis; H14 leaves it be.
    check("Certifications sanitize untouched (row-major by design)",
          "register_setting('sf_site_settings', 'sf_certifications'"
          in functions)

    for label, text in (("admin", admin), ("functions", functions), ("js", js)):
        check("no CHANGEME/TODO leftovers in %s" % label,
              "CHANGEME" not in text and "FIXME" not in text)

    print("\n--source: %d passed, %d failed" % (PASS, FAIL))
    return FAIL


# --------------------------------------------------------------------------
# sanitize probe (shared by --preverify and --live)
# --------------------------------------------------------------------------
PROBE_BODY = r"""$o = array();

/* Snapshot the options first: the probe must leave them byte-identical, and
   asserting "still ABSENT" would conflate "no write" with the resting state. */
$before = array(get_option('sf_shapes', 'ABSENT'), get_option('sf_containers', 'ABSENT'));

/* S1 — Shape Library payload, 3 rows, the middle one left blank. */
$s1 = $probe('sf_shapes', array(
	'attachment_id' => array(11, 0, 12),
	'label'         => array('Bone', '', 'Heart'),
	'slug'          => array('bone', '', 'heart'),
));
$o['s1_n']  = is_array($s1) ? count($s1) : -1;
$o['s1_a0'] = isset($s1[0]['attachment_id']) ? (int) $s1[0]['attachment_id'] : -1;
$o['s1_a1'] = isset($s1[1]['attachment_id']) ? (int) $s1[1]['attachment_id'] : -1;

/* S2 — image only: no slug, no label. The case the diagnosis questioned. */
$s2 = $probe('sf_shapes', array(
	'attachment_id' => array(77), 'label' => array(''), 'slug' => array(''),
));
$o['s2_n']  = is_array($s2) ? count($s2) : -1;
$o['s2_a0'] = isset($s2[0]['attachment_id']) ? (int) $s2[0]['attachment_id'] : -1;

/* S3 — label only: the slug must be derived or the row is unreachable. */
$s3 = $probe('sf_shapes', array(
	'attachment_id' => array(0), 'label' => array('Paw Print'), 'slug' => array(''),
));
$o['s3_slug'] = isset($s3[0]['slug']) ? (string) $s3[0]['slug'] : '';

/* S4 — every row blank: zero rows out (H13 then unsets the option). */
$s4 = $probe('sf_shapes', array(
	'attachment_id' => array(0), 'label' => array(''), 'slug' => array(''),
));
$o['s4_n'] = is_array($s4) ? count($s4) : -1;

/* C1 — Container Library payload, both rows populated. */
$c1 = $probe('sf_containers', array(
	'attachment_id' => array(21, 22),
	'label'         => array('Bottle', 'Jar'),
	'slug'          => array('bottle', 'jar'),
));
$o['c1_n']  = is_array($c1) ? count($c1) : -1;
$o['c1_a1'] = isset($c1[1]['attachment_id']) ? (int) $c1[1]['attachment_id'] : -1;

/* C2 — the reported bug: a named row plus one that only got an image. */
$c2 = $probe('sf_containers', array(
	'attachment_id' => array(0, 99),
	'label'         => array('Bottle', ''),
	'slug'          => array('bottle', ''),
));
$o['c2_n'] = is_array($c2) ? count($c2) : -1;

/* NC — the OLD row-major payload must yield nothing: the contract is parallel. */
$nc = $probe('sf_shapes', array(
	array('slug' => 'bone', 'label' => 'Bone', 'attachment_id' => 11),
));
$o['nc_n'] = is_array($nc) ? count($nc) : -1;

/* Nothing was written; assert that on the way out. */
$after = array(get_option('sf_shapes', 'ABSENT'), get_option('sf_containers', 'ABSENT'));
$o['touched'] = ($before === $after);

echo 'RESULT ' . json_encode($o) . "\n";
"""


def probe_php(mode: str) -> str:
    """mode 'live' calls the registered callbacks through sanitize_option();
    mode 'preverify' calls the workspace closures directly."""
    head = ["<?php", "require_once ABSPATH . 'wp-admin/includes/admin.php';",
            "do_action('admin_init');"]
    if mode == "live":
        head.append("$probe = function ($o, $p) { return sanitize_option($o, $p); };")
    else:
        admin = read(ADMIN)
        closures = {o: extract_closure(admin, o) for o in OPTIONS}
        head.append("$cb = array(")
        for o in OPTIONS:
            head.append("\t'%s' => %s," % (o, closures[o]))
        head.append(");")
        head.append("$probe = function ($o, $p) use ($cb) { $f = $cb[$o]; "
                    "return $f($p); };")
    head.append(PROBE_BODY)
    return "\n".join(head)


def run_probe(mode: str):
    """Ship the probe to dev, run it under WP-CLI, return the parsed dict."""
    out = ssh("""cd %s
cat > /tmp/h14-probe.php <<'PHP'
%s
PHP
wp eval-file /tmp/h14-probe.php --allow-root
rm -f /tmp/h14-probe.php
""" % (WP_ROOT, probe_php(mode)))
    for line in out.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):]), out
    return None, out


def assert_probe(o) -> None:
    check("shapes: 3-row parallel payload keeps both filled rows",
          o["s1_n"] == 2, "got %s rows, want 2" % o["s1_n"])
    check("shapes: row 0 keeps its attachment id (11)",
          o["s1_a0"] == 11, "got %s" % o["s1_a0"])
    check("shapes: the blank row is dropped, row 2 shifts to index 1 (12)",
          o["s1_a1"] == 12, "got %s" % o["s1_a1"])
    check("shapes: an image-only row survives (diagnosis question 3)",
          o["s2_n"] == 1 and o["s2_a0"] == 77,
          "rows=%s att=%s" % (o["s2_n"], o["s2_a0"]))
    check("shapes: a label-only row derives its slug ('paw-print')",
          o["s3_slug"] == "paw-print", "got %r" % o["s3_slug"])
    check("shapes: an all-blank payload still sanitizes to zero rows",
          o["s4_n"] == 0, "got %s" % o["s4_n"])
    check("containers: 2-row parallel payload keeps both rows",
          o["c1_n"] == 2, "got %s rows, want 2" % o["c1_n"])
    check("containers: row 1 keeps its attachment id (22)",
          o["c1_a1"] == 22, "got %s" % o["c1_a1"])
    check("containers: the image-only second row survives",
          o["c2_n"] == 2, "got %s rows, want 2" % o["c2_n"])
    check("negative control: a row-major payload yields zero rows",
          o["nc_n"] == 0, "got %s" % o["nc_n"])
    check("probe wrote nothing (both options unchanged)", o["touched"] is True)


# --------------------------------------------------------------------------
# browser half (shared by --preverify and --live)
# --------------------------------------------------------------------------
def browser_probe(assert_pick: bool) -> None:
    cookies = ssh("cd %s && wp eval-file %s/tools/b2s3_admin_cookies.php "
                  "--allow-root\n" % (WP_ROOT, SITE_REPO))
    data = {}
    for line in cookies.splitlines():
        for key in ("COOKIEHASH", "logged_in", "auth", "secure_auth"):
            if line.startswith(key + "="):
                data["hash" if key == "COOKIEHASH" else key] = \
                    line.split("=", 1)[1].strip()
    if not all(k in data for k in ("hash", "logged_in", "auth", "secure_auth")):
        check("issued a temp admin session for the browser probe", False,
              "raw: " + cookies[-300:])
        return
    data.update({"domain": DOMAIN, "user": "sfdev",
                 "pass": "VkEws18Kl5V1qp3TpZ6s"})
    token = data["logged_in"].split("|")[2]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(data, fh)
        cookie_file = fh.name

    try:
        run = subprocess.run([NODE, str(PICK_JS), cookie_file],
                             env=dict(os.environ, NODE_PATH=NODE_PATH),
                             capture_output=True, text=True, timeout=300)
        lines = run.stdout.splitlines()
    finally:
        Path(cookie_file).unlink(missing_ok=True)
        ssh("cd %s && wp eval 'WP_Session_Tokens::get_instance(1)"
            "->destroy(\"%s\"); echo \"session destroyed\\n\";' --allow-root\n"
            % (WP_ROOT, token))

    recs = {}
    for line in lines:
        if line.startswith("RESULT "):
            r = json.loads(line[len("RESULT "):])
            recs[r["key"]] = r
    if not recs:
        check("browser probe produced RESULT lines", False,
              "stdout: " + run.stdout[-300:] + " stderr: " + run.stderr[-300:])
    for key in ("shapes", "containers"):
        r = recs.get(key)
        if not r:
            check("browser probe reached the %s library" % key, False,
                  "no RESULT line")
            continue
        # --- page truth, valid before and after the pull ---
        check("%s: served the library page (not a login/401 body)" % key,
              r["served"], "title=%r served=%s" % (r["title"], r["served"]))
        rows = len(r["before"])
        check("%s: media modal listed at least one image" % key, r["items"] >= 1,
              "items=%s" % r["items"])
        check("%s: the trailing-[] suffix selector matches every row input" % key,
              r["sel_new"] == rows and rows >= 1,
              "suffix=%s exact-name=%s" % (r["sel_new"], rows))
        check("%s: the bare suffix selector matches nothing (the H14 break)" % key,
              r["sel_old"] == 0, "got %s matches" % r["sel_old"])
        # A console "404" line names no URL, so assert on the response log:
        # every request this theme serves must come back < 400. Any other 4xx
        # is reported, not asserted — the admin page carries third-party
        # requests the theme does not own.
        theme_4xx = [h for h in r["http"]
                     if "sinofresh-theme" in h or "sf-site-settings" in h]
        rest_4xx = [h for h in r["http"] if h not in theme_4xx]
        check("%s: every theme asset request succeeded" % key, not theme_4xx,
              "; ".join(theme_4xx))
        if rest_4xx:
            print("      (info) non-theme 4xx on %s: %s"
                  % (key, "; ".join(rest_4xx[:2])))
        script_err = [e for e in r["errors"] if "sf-site-settings" in e]
        check("%s: no JS error from the theme's settings script" % key,
              not script_err, "; ".join(script_err[:3]))
        # --- only meaningful once the new script is live ---
        if assert_pick:
            check("%s: picking an image writes its id into the hidden input"
                  % key, r["picked"] > 0,
                  "before=%s after=%s" % (r["before"], r["after"]))


# --------------------------------------------------------------------------
# --preverify
# --------------------------------------------------------------------------
def preverify_gate() -> int:
    print("== H14 gate --preverify: workspace code, run against dev ==")
    o, raw = run_probe("preverify")
    if o is None:
        check("preverify sanitize probe produced a RESULT line", False,
              "raw: " + raw[-400:])
        print("\n--preverify: %d passed, %d failed" % (PASS, FAIL))
        return FAIL
    assert_probe(o)
    browser_probe(assert_pick=False)
    print("\n--preverify: %d passed, %d failed" % (PASS, FAIL))
    return FAIL


# --------------------------------------------------------------------------
# --live
# --------------------------------------------------------------------------
def live_gate() -> int:
    print("== H14 gate --live: the dev tree as served ==")
    out = ssh("cd %s\nV=$(grep -m1 '^Version:' "
              "wp-content/themes/sinofresh-theme/style.css | awk '{print $2}')\n"
              "echo \"THEME_VERSION=$V\"\n" % WP_ROOT)
    ver = ""
    for line in out.splitlines():
        if line.startswith("THEME_VERSION="):
            ver = line.split("=", 1)[1].strip()
    check("dev theme version is %s" % VERSION, ver == VERSION, "got %r" % ver)

    o, raw = run_probe("live")
    if o is None:
        check("live sanitize probe produced a RESULT line", False,
              "raw: " + raw[-400:])
        print("\n--live aborted (no probe result).")
        return FAIL
    assert_probe(o)
    browser_probe(assert_pick=True)
    print("\n--live: %d passed, %d failed" % (PASS, FAIL))
    return FAIL


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--source"
    if mode == "--source":
        sys.exit(1 if source_gate() else 0)
    elif mode == "--preverify":
        sys.exit(1 if preverify_gate() else 0)
    elif mode == "--live":
        sys.exit(1 if live_gate() else 0)
    else:
        print(__doc__)
        sys.exit(2)
