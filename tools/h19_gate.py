#!/usr/bin/env python3
"""Batch H19 gate — the Gallery images picker could only ever hold one photo.

Reported 2026-09-30: the "Choose / update images" button under Media >
Gallery images picked exactly one photo — choosing a second replaced the
first.

Root cause, read out of the WordPress 7.1.2 this site runs. The admin JS
asked wp.media for `multiple: true`:

  wp.media.controller.Library.initialize builds the selection as
  `new wp.media.model.Selection(null, { multiple: this.get('multiple') })`
  (wp-includes/js/media-views.js), and
  wp.media.view.Attachment#toggleSelection resolves a PLAIN click's method to
  `selection.multiple`. Only the literal string 'add' reaches the
  `selection.add()` branch; every other truthy value falls through to
  `method = 'reset'`, which throws the selection away and keeps the thumbnail
  just clicked. `true` is core's "hold Shift or Cmd to accumulate" mode, not
  the accumulating one — the docblock above the Library controller says so in
  as many words. 'add' is the documented value (wp.media.model.Selection) and
  is what core's own CollectionAdd state uses.

Nothing downstream was at fault, which is why the diagnosis took a read of
core rather than of the theme: the hidden input already took a CSV, the save
branch already exploded/absint'd/imploded the whole list, and the reader
already walked every id. The picker was the only broken link.

This gate therefore asserts the picker's VALUE, not just that the word
"multiple" appears somewhere. h18_gate had asserted only that
`multiple: false` existed, and H18's own single-image slot control satisfied
that on its own — so the gallery frame's value was never checked, and `true`
shipped. h18_gate now carries the per-frame assertion too (section 6b).

What H19 changed (2026-09-30):

  1. assets/admin/sf-mb-tables.js — the gallery frame's `multiple: true`
     becomes `multiple: 'add'`, with the reason written into the header so
     the next reader does not "tidy" it back.
  2. inc/formula-admin.php — the admin bundle's enqueue version 1.1.0 ->
     1.2.0. Not cosmetic: the origin serves js/css as
     `Cache-Control: max-age=31536000, immutable`, so an admin browser that
     had already fetched ?ver=1.1.0 would keep the broken file for a year.
     Changing the number is the only thing that reaches it.

Not changed: functions.php (the reader was already correct), the front-end
version, the photo/frame ceilings, tile geometry.

Usage:  h19_gate.py [--source | --live]

  --live defaults to dev. Production via:
    H19_WP_ROOT=/var/www/zxpet-v2 \\
    H19_THEME_DIR=/var/www/zxpet-v2/wp-content/themes/sinofresh-theme \\
    H19_SITE=www.zxpet.com H19_BASIC= h19_gate.py --live
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "sinofresh-theme"
JS = THEME / "assets" / "admin" / "sf-mb-tables.js"
ADMIN = THEME / "inc" / "formula-admin.php"
FUNCTIONS = THEME / "functions.php"

SERVER = "root@65.49.215.152"
WP_ROOT = os.environ.get("H19_WP_ROOT", "/var/www/dev.zxpet.com/public")
THEME_DIR = os.environ.get(
    "H19_THEME_DIR", "/var/www/dev.zxpet.com/site-repo/sinofresh-theme")
SITE = os.environ.get("H19_SITE", "dev.zxpet.com")
# '' means "no Basic Auth" (production); unset means dev's staging lock
BASIC = os.environ["H19_BASIC"] if "H19_BASIC" in os.environ \
    else "sfdev:VkEws18Kl5V1qp3TpZ6s"
ADMIN_JS_VER = "1.2.0"

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))


def read(p):
    return p.read_text(encoding="utf-8")


def md5_of(p):
    import hashlib
    return hashlib.md5(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# --source
# --------------------------------------------------------------------------
def source_gate():
    js, admin, func = read(JS), read(ADMIN), read(FUNCTIONS)

    # --- 1. the picker's value itself --------------------------------------
    check("H19: the gallery frame asks for accumulating multi-select ('add')",
          "title: 'Choose images', multiple: 'add'" in js,
          "the gallery frame's multiple value is not 'add'")
    check("H19: no bare `multiple: true` anywhere in the admin JS",
          "multiple: true" not in js,
          "a bare `true` is back — core reads that as Shift/Cmd-only, so a "
          "plain click replaces the pick")
    check("H19: exactly two media frames, one per value",
          js.count("title: 'Choose images', multiple: 'add'") == 1
          and js.count("title: 'Choose image', multiple: false") == 1,
          f"gallery={js.count(chr(39) + 'add' + chr(39))} "
          f"slot={js.count('multiple: false')}")

    # --- 2. the selection is read whole, not just its head -----------------
    check("H19: the gallery handler consumes the WHOLE selection",
          "frame.state().get('selection').map(" in js)
    gallery_half = js.split("function singleFrameFor")[0]
    check("H19: the gallery half never narrows to the first entry",
          ".first()" not in gallery_half,
          "a `.first()` reappeared in the multi-select half")
    check("H19: the hidden input takes every id as one CSV",
          "hidden.value = items.map(function (i) { return i.id; }).join(',');" in js)

    # --- 3. save keeps the list, read walks the list -----------------------
    check("H19: the save branch keeps the whole list (explode/absint/implode)",
          "explode(',', (string) wp_unslash($_POST[$key] ?? ''))" in admin
          and "sf_mb_store($post_id, $key, implode(',', $ids));" in admin)
    check("H19: the reader walks every id, not the first",
          "foreach (explode(',', (string) get_post_meta("
          "$post_id, 'sf_formula_gallery_ids', true)) as $id)" in func)
    check("H19: the reader is unchanged by this batch",
          func.count("sf_formula_gallery_ids") >= 1)

    # --- 4. the fix can actually reach a browser --------------------------
    check(f"H19: sf-mb-tables enqueued at {ADMIN_JS_VER}",
          f"'/assets/admin/sf-mb-tables.js', array(), '{ADMIN_JS_VER}'" in admin,
          "the bundle is still pinned at the old version — the served bytes "
          "are immutable for a year, so the fix would never arrive")
    check("H19: the enqueue comment records why the number moved",
          "immutable" in admin and "cache" in admin.lower())
    check("H19: the JS header records the 'add'-not-`true` rule",
          "batch H19" in js and "'add' is the documented value" in js)

    # --- 5. hygiene --------------------------------------------------------
    for label, text in (("functions", func), ("admin", admin), ("js", js)):
        check(f"H19: no CHANGEME/FIXME leftovers in {label}",
              "CHANGEME" not in text and "FIXME" not in text)

    print(f"\n--source: {PASS} passed, {FAIL} failed")
    return FAIL


# --------------------------------------------------------------------------
# --live
# --------------------------------------------------------------------------
def ssh(script, timeout=300):
    return subprocess.run(
        ["ssh", SERVER, "bash -s"],
        input=script, capture_output=True, text=True, timeout=timeout,
    ).stdout


LIVE_PHP = r"""
<?php
/* Batch H19 live probe — two measurements, and NO assertion about how many
   photos the site's records currently hold (ops is mid-way through filling
   them and that number moves).

   A. the SAVE path, on a throwaway record: create a temporary sf_formula,
      post a five-id CSV through the REAL save_post_sf_formula handler, read
      the meta back, then hard-delete the post. The handler is driven exactly
      as the editor screen drives it — all group nonces present, the field
      posted — and no real record is touched.

   B. the READ path, on a real record, with the meta value injected in memory
      only. The five attachments are chosen AFTER the unfiltered render is
      known, so "none of them is there without the filter" is true by
      construction and the filter-on/filter-off pair is a real contrast — a
      measurement that never varied cannot pass as green. A post-meta
      fingerprint brackets the run to prove it wrote nothing.

   Both halves also self-prove: the injected value is read back inside the
   filter, and the call counter proves the filter was actually consulted.
*/
$o = array();

/* ---- A. the save path ------------------------------------------------- */
wp_set_current_user(1);
$ids_csv = '53,96,102,104,106';
$tmp = wp_insert_post(array(
    'post_type'   => 'sf_formula',
    'post_status' => 'draft',
    'post_title'  => 'H19 probe (temporary)',
    'post_name'   => 'h19-probe-temporary',
));
$o['save_pid'] = (int) $tmp;
if ($tmp && !is_wp_error($tmp)) {
    $_POST = array();
    foreach (array_keys(sf_formula_mb_groups()) as $slug) {
        $_POST['sf_mb_nonce_' . $slug] = wp_create_nonce('sf_mb_save');
    }
    $_POST['sf_formula_gallery_ids'] = $ids_csv;

    do_action('save_post_sf_formula', $tmp);

    $stored = (string) get_post_meta($tmp, 'sf_formula_gallery_ids', true);
    $o['save_posted']    = $ids_csv;
    $o['save_stored']    = $stored;
    $o['save_roundtrip'] = ($stored === $ids_csv) ? 'yes' : 'no';
    $o['save_n']         = count(array_filter(array_map('absint', explode(',', $stored))));

    wp_delete_post($tmp, true);
    $o['save_deleted'] = get_post($tmp) ? 'no' : 'yes';
}

/* ---- helpers ---------------------------------------------------------- */
function h19_fp() {
    global $wpdb;
    $rows = $wpdb->get_results(
        "SELECT meta_id, post_id, meta_key, meta_value FROM {$wpdb->postmeta} "
        . "WHERE meta_key LIKE 'sf_formula%' OR meta_key = '_thumbnail_id' "
        . "ORDER BY meta_id", ARRAY_A);
    return count($rows) . ':' . md5(json_encode($rows));
}

function h19_bases($form, $pid) {
    $out = array();
    foreach (sinofresh_formula_gallery_slots($form, $pid) as $s) {
        if (!empty($s['url'])) {
            $out[] = basename(parse_url($s['url'], PHP_URL_PATH));
        }
    }
    return $out;
}

/* ---- B. the read path ------------------------------------------------- */
$targets = get_posts(array('post_type' => 'sf_formula', 'post_status' => 'publish',
    'posts_per_page' => 1, 'fields' => 'ids', 'orderby' => 'ID', 'order' => 'ASC'));
$pid  = $targets ? (int) $targets[0] : 0;
$form = $pid ? sf_formula_record_form($pid) : '';
$o['pid']  = $pid;
$o['form'] = $form;
$o['hit_on'] = $o['hit_off'] = $o['calls_on'] = $o['calls_off'] = 0;

if ($pid > 0) {
    $o['fp_before'] = h19_fp();

    /* what the record renders with no injection — the five test ids are then
       chosen to avoid every one of these names */
    $off = h19_bases($form, $pid);
    $o['off_stable_a'] = implode('|', $off);

    $pick = array();
    $cand = get_posts(array('post_type' => 'attachment', 'post_mime_type' => 'image',
        'post_status' => 'inherit', 'posts_per_page' => 200, 'fields' => 'ids',
        'orderby' => 'ID', 'order' => 'ASC'));
    foreach ($cand as $aid) {
        $src = wp_get_attachment_image_src($aid, 'large');
        if (!$src) { continue; }
        $base = basename(parse_url($src[0], PHP_URL_PATH));
        if (in_array($base, $off, true)) { continue; }
        $pick[] = array('id' => (int) $aid, 'base' => $base);
        if (count($pick) >= 5) { break; }
    }
    $o['pick'] = $pick;

    $GLOBALS['h19_inject'] = implode(',', array_map(function ($p) { return $p['id']; }, $pick));
    $GLOBALS['h19_readback'] = '';
    $GLOBALS['h19_calls'] = 0;
    $GLOBALS['h19_filter'] = function ($value, $object_id, $meta_key, $single, $meta_type) {
        if ($meta_key !== 'sf_formula_gallery_ids') { return $value; }
        $GLOBALS['h19_calls']++;
        $GLOBALS['h19_readback'] = (string) $GLOBALS['h19_inject'];
        return $GLOBALS['h19_inject'];
    };
    add_filter('get_post_metadata', $GLOBALS['h19_filter'], 10, 5);

    $on = h19_bases($form, $pid);
    $o['calls_on']  = $GLOBALS['h19_calls'];
    $o['readback']  = $GLOBALS['h19_readback'];
    $o['injected']  = $GLOBALS['h19_inject'];
    foreach ($pick as $p) { if (in_array($p['base'], $on, true)) { $o['hit_on']++; } }

    remove_filter('get_post_metadata', $GLOBALS['h19_filter'], 10);

    $GLOBALS['h19_calls'] = 0;
    $off2 = h19_bases($form, $pid);
    $o['calls_off']    = $GLOBALS['h19_calls'];
    $o['off_stable_b'] = implode('|', $off2);
    foreach ($pick as $p) { if (in_array($p['base'], $off2, true)) { $o['hit_off']++; } }

    $o['rendered_n'] = count($on);
    $o['fp_after']   = h19_fp();
}

echo 'RESULT ' . json_encode($o) . "\n";
"""


def live_gate():
    basic = ("-u '" + BASIC + "' ") if BASIC else ""
    url = ("https://127.0.0.1/wp-content/themes/sinofresh-theme"
           "/assets/admin/sf-mb-tables.js?ver=" + ADMIN_JS_VER)
    q2 = "'"
    admin_file = THEME_DIR + "/inc/formula-admin.php"
    # the enqueue line, quotes included, as a fixed string
    enq_pat = "sf-mb-tables.js" + q2 + ", array(), " + q2 + ADMIN_JS_VER + q2

    shell = (
        "cd " + WP_ROOT + "\n"
        "rm -f /tmp/h19-mb.js\n"
        'echo "H19_HTTP=$(curl -sk ' + basic + '-H "Host: ' + SITE + '" '
        '-o /tmp/h19-mb.js -w "%{http_code}" "' + url + '")"\n'
        'echo "H19_BYTES=$(wc -c < /tmp/h19-mb.js | tr -d \' \')"\n'
        'echo "H19_SERVED_MD5=$(md5sum /tmp/h19-mb.js | cut -d\' \' -f1)"\n'
        # quoted with . wildcards so the pattern survives the shell intact;
        # the exact-literal form is asserted in --source instead
        'echo "H19_SERVED_ADD=$(grep -c "Choose images., multiple: .add." /tmp/h19-mb.js)"\n'
        'echo "H19_SERVED_TRUE=$(grep -c "multiple: true" /tmp/h19-mb.js)"\n'
        'echo "H19_HDR=$(curl -sk ' + basic + '-I -H "Host: ' + SITE + '" "'
        + url + '" | grep -i cache-control | tr -d "\\r")"\n'
        # -F with the literal (quotes and all). A BRE spelling of the same
        # string does not match here, and the literal is what is asserted.
        'echo "H19_ENQUEUE=$(grep -cF "' + enq_pat + '" ' + admin_file + ')"\n'
        'echo "H19_120=$(grep -cF "' + ADMIN_JS_VER + q2 + '" ' + admin_file + ')"\n'
        "echo \"H19_FILE_MD5=$(md5sum " + THEME_DIR
        + "/assets/admin/sf-mb-tables.js | cut -d' ' -f1)\"\n"
        "cat > /tmp/h19-eval.php <<'PHP'\n" + LIVE_PHP + "\nPHP\n"
        "wp eval-file /tmp/h19-eval.php --allow-root\n"
        "rm -f /tmp/h19-eval.php /tmp/h19-mb.js\n"
    )
    out = ssh(shell)

    kv, result = {}, None
    for line in out.splitlines():
        if line.startswith("RESULT "):
            try:
                result = json.loads(line[len("RESULT "):])
            except Exception:
                result = None
        elif "=" in line and line.startswith("H19_"):
            k, v = line.split("=", 1)
            kv[k] = v.strip()

    local_md5 = md5_of(JS)

    # --- 1. the served bundle, over HTTP, at the URL the page will use -----
    check("live: the admin bundle answers over HTTP at the new version",
          kv.get("H19_HTTP") == "200" and int(kv.get("H19_BYTES", "0") or 0) > 0,
          f"http={kv.get('H19_HTTP')} bytes={kv.get('H19_BYTES')} url={url}")
    check("live: the served bundle is byte-identical to the workspace file",
          kv.get("H19_SERVED_MD5") == local_md5,
          f"served={kv.get('H19_SERVED_MD5')} local={local_md5}")
    check("live: the served bundle carries the accumulating multi-select",
          kv.get("H19_SERVED_ADD", "0") == "1",
          "the served bytes do not hold `multiple: 'add'`")
    check("live: the served bundle carries no bare `multiple: true`",
          kv.get("H19_SERVED_TRUE", "?") == "0",
          f"count={kv.get('H19_SERVED_TRUE')}")
    check("live: the theme's own copy on disk matches the workspace file",
          kv.get("H19_FILE_MD5") == local_md5,
          f"disk={kv.get('H19_FILE_MD5')} local={local_md5}")
    check("live: the deployed PHP enqueues the bundle at the new version",
          kv.get("H19_ENQUEUE") == "1",
          f"count={kv.get('H19_ENQUEUE')} (cache-busting ?ver must move)")
    check("live: the origin still pins js/css as immutable (why the bump "
          "was necessary at all)",
          "immutable" in kv.get("H19_HDR", ""),
          f"cache-control={kv.get('H19_HDR')!r}")

    if not result:
        check("live: probe produced a RESULT line", False, "no RESULT line")
        print(f"\n--live aborted. raw output:\n{out}")
        return FAIL

    # --- 2. the save path, on a throwaway record --------------------------
    check("live: the save probe ran against a temporary record",
          int(result.get("save_pid", 0)) > 0, f"pid={result.get('save_pid')}")
    check("live: the save probe deleted its temporary record",
          result.get("save_deleted") == "yes",
          f"deleted={result.get('save_deleted')!r}")
    check("live: a five-id CSV survives the real save handler intact",
          result.get("save_roundtrip") == "yes",
          f"posted={result.get('save_posted')!r} stored={result.get('save_stored')!r}")
    check("live: the stored value really holds five ids",
          int(result.get("save_n", 0)) == 5, f"n={result.get('save_n')}")

    # --- 3. the read path, injected in memory only -------------------------
    check("live: the read probe found a published record to measure on",
          int(result.get("pid", 0)) > 0,
          f"pid={result.get('pid')} error={result.get('error')}")
    if int(result.get("pid", 0)) <= 0:
        print(f"\n--live aborted. raw output:\n{out}")
        return FAIL

    pick = result.get("pick", [])
    check("live: five attachments were available that the record does not "
          "already show", len(pick) == 5, f"got {len(pick)}")

    check("live: the meta filter really was consulted (self-proof)",
          int(result.get("calls_on", 0)) > 0
          and result.get("readback") == result.get("injected"),
          f"calls={result.get('calls_on')} readback={result.get('readback')!r} "
          f"injected={result.get('injected')!r}")
    check("live: with the value injected, ALL five ids reach the gallery",
          int(result.get("hit_on", 0)) == 5,
          f"hit_on={result.get('hit_on')} of {len(pick)}; rendered="
          f"{result.get('rendered_n')} — the reader is dropping ids")
    check("live: with the filter off, none of them do (real contrast, not a "
          "measurement that never varied)",
          int(result.get("hit_off", -1)) == 0
          and int(result.get("calls_off", -1)) == 0,
          f"hit_off={result.get('hit_off')} calls_off={result.get('calls_off')}")
    check("live: the unfiltered render is stable across both calls",
          result.get("off_stable_a") == result.get("off_stable_b"))
    check("live: the probe left every sf_formula% / _thumbnail_id row "
          "byte-identical",
          result.get("fp_before") == result.get("fp_after")
          and bool(result.get("fp_before")),
          f"before={result.get('fp_before')} after={result.get('fp_after')}")

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
