#!/usr/bin/env python3
"""Batch H18 gate — per-record gallery frames 2/3/4.

What H18 changed (2026-09-30): the three facility positions (frames 2, 3, 4)
of every formula gallery were stock photos baked into the theme, identical
on all 21 records and changeable only by a code edit. H18 gave each record
three single-image slots — sf_formula_frame2_id / _frame3_id / _frame4_id —
rendered in the admin Media box as "Frame 2 / Frame 3 / Frame 4".

The contract this gate pins down:

  * POSITION-LOCKED, NOT QUEUE-FILLED. A set slot replaces the photograph at
    ITS OWN index. An empty slot keeps that index's stock photo. So "Frame 3"
    means the same picture on every record, whatever else is filled — filling
    frame 2 must not slide frame 3's fallback. This is the one property a
    naive "take the next unused photo" implementation would get wrong, and the
    one the live half asserts with a frame-4-only write.
  * A STALE ID NEVER SHORTENS THE BAND. An attachment that no longer resolves
    (deleted, non-image mime, no 'large' rendition) falls back to the stock
    photo, exactly as a blank slot does — the band is never fewer than the
    four frames it has always had.
  * BYTE-COMPATIBLE WHEN UNUSED. All three slots empty => the slot list is the
    very array it was, so the 21 records that have filled nothing render
    identically. The cross-run proof is tools/h18_capture.py's 21/21
    byte-identical capture; the in-run proof is this gate's E0 == E0_after
    pair, which also shows the probe put the record back.

Modes:
  --source   static assertions on the workspace files (all 7 change sites)
  --live     behavioral assertions on the dev tree, using REAL theme code and
             REAL post meta, with the record snapshotted and restored.

Negative control: run --live against the pre-H18 dev tree. E1/E2/E3 must come
back red (the takeover does nothing there) while E0 stays green — that is what
proves the live half can see the feature it was written for. A red --live run
taken before the pull is expected; do not "fix" it.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "sinofresh-theme"
FUNCTIONS = THEME / "functions.php"
ADMIN = THEME / "inc" / "formula-admin.php"
JS = THEME / "assets" / "admin" / "sf-mb-tables.js"
CSS = THEME / "style.css"

SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
VERSION = "2.10.88"        # front end: deliberately NOT bumped by H18
ADMIN_JS_VER = "1.1.0"     # admin asset: bumped 1.0.0 -> 1.1.0 by H18

# the four dosage-level frames a soft-chews record falls back to, in order
BASE_FRAMES = ["soft-chews.webp", "fac-placeholder.webp",
               "fac-packaging.webp", "fac-line.webp"]

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


# --------------------------------------------------------------------------
# --source
# --------------------------------------------------------------------------
def source_gate():
    func = read(FUNCTIONS)
    admin = read(ADMIN)
    js = read(JS)
    css = read(CSS)

    # --- 1. front-end frame rule (functions.php) ---------------------------
    reads = re.findall(
        r"get_post_meta\(\$post_id, 'sf_formula_frame([234])_id', true\)", func)
    check("H18: all three frame slots are read from post meta",
          sorted(reads) == ["2", "3", "4"], f"found {reads}")

    check("H18: slot map is keyed 1/2/3 — position, not append order",
          bool(re.search(
              r"\$frame_slots = array\(\s*"
              r"1 => \(int\) get_post_meta\(\$post_id, 'sf_formula_frame2_id', true\),\s*"
              r"2 => \(int\) get_post_meta\(\$post_id, 'sf_formula_frame3_id', true\),\s*"
              r"3 => \(int\) get_post_meta\(\$post_id, 'sf_formula_frame4_id', true\),",
              func)))

    check("H18: takeover writes to the slot's OWN index (position lock)",
          "$slots[$offset] = array(" in func)

    check("H18: blank and stale slots both fall through, never drop the frame",
          "if ($frame_id <= 0) {" in func and "if (!$src) {" in func)

    def before(a, b, text):
        # ordering assertion that fails cleanly (rather than raising) when a
        # pre-H18 tree is handed to --source as a negative control
        if a not in text or b not in text:
            return False
        return text.index(a) < text.index(b)

    check("H18: takeover loop runs before the own-photo rebuild",
          before("$frame_slots = array(", "$own = array();", func))

    check("H18: docblock states the position-locked contract",
          "Position-locked, never queue-filled" in func)

    check("H18: docblock says an all-empty record is byte-for-byte unchanged",
          "byte-for-byte the record it was before this batch" in func)

    check("H18: facility frame size note present (why 1.50 vs 1.33 is fine)",
          "aspect ratios differ" in func and "1100x733" in func
          and "object-fit:cover" in func)

    # --- 2. admin meta registration (formula-admin.php) --------------------
    for key, frame in (("sf_formula_frame2_id", "2"),
                       ("sf_formula_frame3_id", "3"),
                       ("sf_formula_frame4_id", "4")):
        check(f"H18: '{key}' registered with a description",
              f"'{key}'" in admin and f"overriding gallery frame {frame}" in admin)

    check("H18: gallery_ids description corrected to CSV (was 'JSON array')",
          "'Gallery photos: comma-separated attachment IDs (CSV)." in admin)

    # --- 3. field specs, render branch, save branch ------------------------
    specs = re.findall(
        r"'key' => 'sf_formula_frame([234])_id', 'label' => 'Frame [234]', "
        r"'group' => 'media', 'type' => 'image'", admin)
    check("H18: three Frame 2/3/4 field specs are type=image in the media group",
          sorted(specs) == ["2", "3", "4"], f"found {specs}")

    check("H18: render branch emits hidden id + preview + add + clear",
          'class="sf-mb__image-id"' in admin
          and "sf-mb__image-add" in admin and "sf-mb__image-clear" in admin)

    check("H18: save branch absints the id and deletes on empty",
          bool(re.search(r"\$id = absint\(wp_unslash\(\$_POST\[\$key\] \?\? ''\)\)", admin))
          and "sf_mb_store($post_id, $key, $id > 0 ? (string) $id : '');" in admin)

    check("H18: exactly two case 'image' branches (render + save)",
          len(re.findall(r"case 'image':", admin)) == 2,
          f"found {len(re.findall(r'case .image.:', admin))}")

    # --- 4. admin asset version bump ---------------------------------------
    check(f"H18: sf-mb-tables enqueued at {ADMIN_JS_VER}",
          f"'/assets/admin/sf-mb-tables.js', array(), '{ADMIN_JS_VER}'" in admin)

    # --- 5. front-end version deliberately untouched ------------------------
    check(f"H18: front-end version stays {VERSION} (style.css)",
          f"Version: {VERSION}" in css)
    check(f"H18: front-end enqueue stays {VERSION}",
          f"get_stylesheet_uri(), array(), '{VERSION}')" in func)

    # --- 6. admin JS picker ------------------------------------------------
    check("H18: single-image picker defined", "function singleFrameFor(" in js)
    check("H18: picker is single-select, image-only library",
          "multiple: false" in js and "type: 'image'" in js)
    check("H18: add + clear delegated handlers present",
          "closest('.sf-mb__image-add')" in js
          and "closest('.sf-mb__image-clear')" in js)
    check("H18: JS header advertises the third job",
          "Three jobs" in js and "batch H18" in js)

    # --- 7. no stray placeholders ------------------------------------------
    for label, text in (("functions", func), ("admin", admin), ("js", js)):
        check(f"no CHANGEME/FIXME leftovers in {label}",
              "CHANGEME" not in text and "FIXME" not in text)

    print(f"\n--source: {PASS} passed, {FAIL} failed")
    return FAIL


# --------------------------------------------------------------------------
# --live
# --------------------------------------------------------------------------
def ssh(script: str, timeout: int = 180) -> str:
    return subprocess.run(
        ["ssh", SERVER, "bash -s"],
        input=script, capture_output=True, text=True, timeout=timeout,
    ).stdout


LIVE_PHP = r"""
<?php
/* Batch H18 live probe — real theme code, real post meta, full restore.
   The record is snapshotted before the first write and put back afterwards;
   delete-then-readd (never blind add_post_meta) so a pre-existing key cannot
   grow a duplicate row. */
$slug = 'soft-chews';
$probe_name = 'calming-soft-chews';

function h18_names($slug, $pid) {
    $names = array();
    foreach (sinofresh_formula_gallery_slots($slug, $pid) as $s) {
        if (!empty($s['video_id'])) { $names[] = 'VIDEO'; continue; }
        $names[] = ($s['file'] !== '') ? $s['file'] : basename(parse_url($s['url'], PHP_URL_PATH));
    }
    return $names;
}

$posts = get_posts(array('post_type' => 'sf_formula', 'name' => $probe_name,
    'numberposts' => 1, 'post_status' => 'publish'));
$pid = $posts ? (int) $posts[0]->ID : 0;

/* two attachments that actually resolve at 'large', and are not one of the
   stock facility stills (which would make a takeover test read as a fallback) */
$ids = get_posts(array('post_type' => 'attachment', 'post_mime_type' => 'image',
    'post_status' => 'inherit', 'numberposts' => 80, 'fields' => 'ids',
    'orderby' => 'ID', 'order' => 'ASC'));
$picked = array();
foreach ($ids as $aid) {
    $src = wp_get_attachment_image_src($aid, 'large');
    if (!$src) { continue; }
    $base = basename(parse_url($src[0], PHP_URL_PATH));
    if (strpos($base, 'fac-') === 0 || strpos($base, 'soft-chews') === 0) { continue; }
    $picked[] = array('id' => (int) $aid, 'base' => $base);
    if (count($picked) >= 2) { break; }
}

$keys = array('sf_formula_frame2_id', 'sf_formula_frame3_id', 'sf_formula_frame4_id');
$snap = array();
foreach ($keys as $k) {
    $snap[$k] = metadata_exists('post', $pid, $k) ? (string) get_post_meta($pid, $k, true) : null;
}

$o = array('pid' => $pid, 'picked' => $picked, 'snap' => $snap);

if ($pid > 0) {
    /* E0 — everything empty: the four dosage-level frames, unchanged */
    foreach ($keys as $k) { delete_post_meta($pid, $k); }
    $o['E0'] = h18_names($slug, $pid);

    /* E1 — frame 2 set: only position 2 moves */
    if (count($picked) >= 1) {
        update_post_meta($pid, 'sf_formula_frame2_id', $picked[0]['id']);
        $o['E1'] = h18_names($slug, $pid);
    }

    /* E2 — frame 4 set, frame 2 cleared: positions 2 and 3 must keep their
       OWN stock photos (fac-placeholder / fac-packaging). Queue-filling
       would have slid frame 3 to a different default here. */
    if (count($picked) >= 2) {
        delete_post_meta($pid, 'sf_formula_frame2_id');
        update_post_meta($pid, 'sf_formula_frame4_id', $picked[1]['id']);
        $o['E2'] = h18_names($slug, $pid);
    }

    /* E3 — a stale id falls back instead of dropping the frame */
    delete_post_meta($pid, 'sf_formula_frame2_id');
    delete_post_meta($pid, 'sf_formula_frame4_id');
    update_post_meta($pid, 'sf_formula_frame2_id', 999999);
    $o['E3'] = h18_names($slug, $pid);

    /* restore: delete every key, re-add only those that were there */
    foreach ($keys as $k) {
        delete_post_meta($pid, $k);
        if ($snap[$k] !== null) { add_post_meta($pid, $k, $snap[$k]); }
    }
    $o['E0_after'] = h18_names($slug, $pid);
}

global $wpdb;
$o['leftover'] = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_frame%'");

echo 'RESULT ' . json_encode($o) . "\n";
"""


def live_gate():
    shell = (
        "cd " + WP_ROOT + "\n"
        "V=$(grep -m1 '^Version:' wp-content/themes/sinofresh-theme/style.css | awk '{print $2}')\n"
        'echo "THEME_VERSION=$V"\n'
        "cat > /tmp/h18-eval.php <<'PHP'\n"
        + LIVE_PHP +
        "\nPHP\n"
        "wp eval-file /tmp/h18-eval.php --allow-root\n"
        "rm -f /tmp/h18-eval.php\n"
    )
    out = ssh(shell)
    ver, result = "", None
    for line in out.splitlines():
        if line.startswith("THEME_VERSION="):
            ver = line.split("=", 1)[1].strip()
        if line.startswith("RESULT "):
            try:
                result = json.loads(line[len("RESULT "):])
            except Exception:
                result = None

    check(f"live: dev theme version is {VERSION}", ver == VERSION, f"got {ver!r}")
    if not result:
        check("live: probe produced a RESULT line", False, "no RESULT line")
        print(f"\n--live aborted. raw output:\n{out}")
        return FAIL

    pid = result.get("pid", 0)
    picked = result.get("picked", [])
    check("live: probe found the published sf_formula to test on", pid > 0,
          f"pid={pid}")
    if pid <= 0:
        print(f"\n--live aborted. raw output:\n{out}")
        return FAIL

    e0 = result.get("E0", [])
    check("live: all slots empty == the four dosage frames (zero drift)",
          e0 == BASE_FRAMES, f"got {e0}")

    if len(picked) >= 1:
        b0 = picked[0]["base"]
        e1 = result.get("E1", [])
        check("live: frame 2 set -> only position 2 changes",
              e1 == [BASE_FRAMES[0], b0, BASE_FRAMES[2], BASE_FRAMES[3]],
              f"got {e1} want frame2={b0}")
    else:
        check("live: an attachment was available for the frame-2 test", False,
              "none found")

    if len(picked) >= 2:
        b1 = picked[1]["base"]
        e2 = result.get("E2", [])
        check("live: frame 4 set -> frames 2/3 keep THEIR OWN stock photos "
              "(position lock, not queue fill)",
              e2 == [BASE_FRAMES[0], BASE_FRAMES[1], BASE_FRAMES[2], b1],
              f"got {e2} want frame4={b1}")
    else:
        check("live: two attachments were available for the position-lock test",
              False, "need 2")

    e3 = result.get("E3", [])
    check("live: stale attachment id falls back to the stock photo",
          e3 == BASE_FRAMES, f"got {e3}")

    e0b = result.get("E0_after", [])
    check("live: probe put the record back (post-run render == pre-run)",
          e0b == e0, f"got {e0b} want {e0}")

    snap = result.get("snap", {})
    want_leftover = sum(1 for v in snap.values() if v is not None)
    check("live: no sf_formula_frame% rows left beyond the snapshot",
          result.get("leftover", -1) == want_leftover,
          f"leftover={result.get('leftover')} want {want_leftover}")

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
