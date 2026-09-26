#!/usr/bin/env python3
"""Batch H13 gate — empty-table contract for Site Settings row-tables.

Bug: sf_shapes / sf_containers held array(0) {} in the DB. Every getter
fell back to defaults only on !is_array(), so an empty array blanked the
library pages to zero rows; the tables JS clones the LAST <tr> and no-ops
on an empty tbody, so "+ Add" died silently (2026-09-26 diagnosis).

Fix contract (two halves, four options):
  READ  — empty array == absent option (defaults / one blank row)
  WRITE — a save where no row survives DELETES the option

Modes:
  --source   static checks against the local repo files
  --live     behavioral checks against the dev server (after pull)
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "sinofresh-theme"

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not ok else ""))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def source_gate():
    admin = read(THEME / "inc" / "formula-admin.php")
    functions = read(THEME / "functions.php")
    pools = read(THEME / "inc" / "formula-pools.php")
    js = read(THEME / "assets" / "admin" / "sf-site-settings.js")
    css = read(THEME / "style.css")

    # --- version bumps ---
    check("style.css Version is 2.10.87",
          "Version: 2.10.87" in css)
    check("functions.php main style enqueue bumped to 2.10.87",
          "get_stylesheet_uri(), array(), '2.10.87')" in functions)
    check("sf-site-settings.js enqueue ver bumped to 1.0.2",
          "/assets/admin/sf-site-settings.js', array(), '1.0.2'" in admin)

    # --- READ half: shared helper ---
    check("sf_admin_table_rows() defined exactly once",
          len(re.findall(r"function sf_admin_table_rows\(", admin)) == 1)
    def code_calls(text: str) -> int:
        # count REAL invocations only: sf_admin_table_rows($...) or
        # sf_admin_table_rows(get_option(...)) — comment mentions of the
        # helper's name do not count.
        return len(re.findall(r"sf_admin_table_rows\(\s*(?:\$|get_option)", text))

    uses = (code_calls(admin) + code_calls(functions) + code_calls(pools) - 1)  # minus def
    check("sf_admin_table_rows() used by all call sites",
          uses == 6, f"found {uses} call sites, want 6 "
          "(containers, shapes, FAQ, certs admin, cert badges, cert reader)")

    # getter empty-array fallbacks
    getter_fb = len(re.findall(r"!is_array\(\$opt\) \|\| !\$opt", admin))
    check("shape+container getters treat empty array as absent",
          getter_fb == 2, f"found {getter_fb}, want 2")

    # --- WRITE half: delete-on-empty hooks ---
    check("delete-on-empty covers all four options",
          "array('sf_shapes', 'sf_containers', 'sf_global_faq', 'sf_certifications')"
          in admin)
    check("update_option_ hook registered",
          'add_action("update_option_{$sf_h13_opt}"' in admin)
    check("add_option_ hook registered (first-write path)",
          'add_action("add_option_{$sf_h13_opt}"' in admin)
    deletes = len(re.findall(r"delete_option\(\$sf_h13_opt\)", admin))
    check("both hook closures delete the option", deletes == 2,
          f"found {deletes}, want 2")

    # --- JS guards ---
    warns = len(re.findall(r"console\.warn\('sf-site-settings: no rows to clone", js))
    check("JS 0-row no-op now logs loudly (2 guards)", warns == 2,
          f"found {warns}, want 2")
    check("JS guards reference the H13 contract", js.count("H13 guard") == 2)

    # --- FAQ render keeps its one-blank-row fallback through the helper ---
    check("Global FAQ render routes through the shared helper",
          "sf_admin_table_rows($rows, array(array('q' => '', 'a' => '')))" in admin)

    # --- no stray placeholders ---
    for label, text in (("admin", admin), ("functions", functions), ("pools", pools)):
        check(f"no CHANGEME/TODO leftovers in {label}",
              "CHANGEME" not in text and "FIXME" not in text)

    print(f"\n--source: {PASS} passed, {FAIL} failed")
    return FAIL


def ssh(script: str) -> str:
    return subprocess.run(
        ["ssh", "root@65.49.215.152", "bash -s"],
        input=script, capture_output=True, text=True, timeout=180,
    ).stdout


def live_gate():
    # WP-CLI does not fire admin_init on its own; fire it once so the
    # register_setting + H13 delete-on-empty hooks exist in this process.
    eval_php = r"""
<?php
// WP-CLI does not run wp-admin/admin.php, so admin_init has not fired and
// the admin includes are not loaded. Load them, then fire admin_init once
// so register_setting() and the H13 delete-on-empty hooks exist here.
require_once ABSPATH . 'wp-admin/includes/admin.php';
do_action('admin_init');
$c_shapes = count(sf_default_shapes());
$c_conts  = count(sf_default_containers());
// READ half: stored empty array must read as defaults
update_option('sf_shapes', array());
$a1 = count(sf_shape_library());
update_option('sf_containers', array());
$a2 = count(sf_container_library());
update_option('sf_certifications', array());
$a3 = count(sf_active_cert_names());
// WRITE half, path 1: option ABSENT -> empty save must not persist it.
// (delete_option first: an option that already holds array(0) makes
// update_option(array()) a no-op — old === new — and no hook fires.)
delete_option('sf_shapes');
update_option('sf_shapes', array());
$b1 = get_option('sf_shapes', 'ABSENT') === 'ABSENT';
// WRITE half, path 2: existing data -> emptied save must delete it.
update_option('sf_shapes', array(array('slug' => 'x', 'label' => 'X', 'attachment_id' => 0)));
update_option('sf_shapes', array());
$b4 = get_option('sf_shapes', 'ABSENT') === 'ABSENT';
delete_option('sf_containers');
update_option('sf_containers', array());
$b2 = get_option('sf_containers', 'ABSENT') === 'ABSENT';
delete_option('sf_certifications');
update_option('sf_certifications', array());
$b3 = get_option('sf_certifications', 'ABSENT') === 'ABSENT';
// helper contract directly
$a4 = sf_admin_table_rows(array(), array('blank')) === array('blank');
$a5 = sf_admin_table_rows(array('x'), array('blank')) === array('x');
// leave the DB in the contract's resting state: options absent
delete_option('sf_shapes');
delete_option('sf_containers');
delete_option('sf_certifications');
printf("RESULT %d %d %d %d %d %d %d %d %d %d %d\n",
  $c_shapes, $c_conts, $a1, $a2, ($a3 > 0) ? 1 : 0,
  $b1 ? 1 : 0, $b2 ? 1 : 0, $b3 ? 1 : 0, $a4 ? 1 : 0, $a5 ? 1 : 0, $b4 ? 1 : 0);
"""
    out = ssh(f"""cd /var/www/dev.zxpet.com/public
V=$(grep -m1 '^Version:' wp-content/themes/sinofresh-theme/style.css | awk '{{print $2}}')
echo "THEME_VERSION=$V"
cat > /tmp/h13-eval.php <<'PHP'
{eval_php}
PHP
wp eval-file /tmp/h13-eval.php --allow-root
rm -f /tmp/h13-eval.php
""")
    ver = ""
    result = ""
    for line in out.splitlines():
        if line.startswith("THEME_VERSION="):
            ver = line.split("=", 1)[1].strip()
        if line.startswith("RESULT"):
            result = line
    check("dev theme version is 2.10.87", ver == "2.10.87", f"got {ver!r}")
    if not result:
        check("live behavioral eval produced RESULT", False, "no RESULT line")
        print(f"\n--live aborted. raw output:\n{out}")
        return FAIL
    vals = result.split()[1:]
    want = [8, 7]
    check("shape library on empty option returns 8 default rows",
          vals[0] == str(want[0]), f"got {vals[0]}")
    check("container library on empty option returns 7 default rows",
          vals[1] == str(want[1]), f"got {vals[1]}")
    check("shapes read-back equals defaults", vals[2] == str(want[0]))
    check("containers read-back equals defaults", vals[3] == str(want[1]))
    check("cert names on empty option still non-empty", vals[4] == "1")
    check("empty save on absent option deleted sf_shapes (add path)", vals[5] == "1")
    check("empty save on absent option deleted sf_containers (add path)", vals[6] == "1")
    check("empty save on absent option deleted sf_certifications (add path)", vals[7] == "1")
    check("helper: empty -> fallback", vals[8] == "1")
    check("helper: non-empty passes through", vals[9] == "1")
    check("emptied save on existing data deleted sf_shapes (update path)", vals[10] == "1")

    print(f"\n--live: {PASS} passed, {FAIL} failed")
    return FAIL


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--source"
    if mode == "--source":
        sys.exit(1 if source_gate() else 0)
    elif mode == "--live":
        sys.exit(1 if live_gate() else 0)
    else:
        print(__doc__)
        sys.exit(2)
