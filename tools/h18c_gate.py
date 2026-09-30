#!/usr/bin/env python3
"""Batch H18c gate — the gallery's photo ceiling, and the seventh tile.

What H18c changed (2026-09-30):

  1. functions.php — the cap went from `array_slice(..., 0, 6)` to TWO
     ceilings: `$photo_cap = 7` on photo frames, plus `$frame_cap = 8` so a
     record that also has a video can keep seven photos AND the video. A plain
     slice to 8 does not work: seven own photos plus a video merge to
     head + 7 own + video + 3 facility, whose first eight entries are eight
     photos with the video cut off the end — the one shape the desktop rail
     cannot hold (eight 72px tiles = 640px against a 607px photo).
  2. functions.php — both docblocks rewritten to the measured rule.
  3. style.css — the desktop rail's gap drops 12px -> 8px, scoped with :has()
     to records that actually carry a seventh tile, so the 21 records on the
     site today (four tiles each) keep the pitch they have always had.

By design NOT changed: the front-end version stays 2.10.88, the admin bundle
stays 1.1.0, and no tile size moved. --source asserts that too, because
"unchanged" is exactly what this batch promised.

The geometry half of the acceptance is not here: --live asserts the CAP in
real theme code, while the rendered rail is measured by tools/h18c_geometry.js
(21 records at 1440 for drift, then 1101/1200/1240/1440 with seven tiles).

Usage:  h18c_gate.py [--source | --live]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "sinofresh-theme"
FUNCTIONS = THEME / "functions.php"
CSS = THEME / "style.css"
ADMIN = THEME / "inc" / "formula-admin.php"

SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
VERSION = "2.10.88"
ADMIN_JS_VER = "1.1.0"

PHOTO_CAP = 7
FRAME_CAP = 8
SEVEN_RAIL = 7 * 72 + 6 * 8 + 8   # 560px

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _md5_local(path: Path) -> str:
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# --source
# --------------------------------------------------------------------------
def _blank_comments(css: str) -> str:
    """Replace comment bodies with spaces so brace offsets stay valid."""
    out = list(css)
    for m in re.finditer(r"/\*.*?\*/", css, re.S):
        for i in range(m.start(), m.end()):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def _enclosing_media(css: str, index: int):
    """The @media whose block contains `index`, or None."""
    text = _blank_comments(css)
    for m in re.finditer(r"@media\s*\(([^)]*)\)", text):
        open_i = text.find("{", m.end())
        if open_i < 0:
            continue
        depth, close_i = 0, -1
        for j in range(open_i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    close_i = j
                    break
        if close_i > 0 and open_i < index < close_i:
            return m.group(1).strip()
    return None


def source_gate():
    func = read(FUNCTIONS)
    css = read(CSS)
    admin = read(ADMIN)

    # --- 1. the ceiling (functions.php) -----------------------------------
    check("H18c: the photo ceiling is 7",
          re.search(r"\$photo_cap\s*=\s*7\s*;", func) is not None)
    check("H18c: the frame ceiling is 8 (seven photos + the video)",
          re.search(r"\$frame_cap\s*=\s*8\s*;", func) is not None)
    check("H18c: the video is exempt from the photo cut, so it cannot be pushed out",
          "if (empty($candidate['video_id']))" in func)
    check("H18c: the cut counts PHOTOS, and skips rather than truncates",
          "if ($photos >= $photo_cap) {" in func and "continue;" in func)
    check("H18c: the frame ceiling ends the walk",
          "if (count($kept) >= $frame_cap) {" in func)
    check("H18c: the built list is what gets returned to $slots",
          "$slots = $kept;" in func)
    check("H18c: the old single ceiling is gone",
          not re.search(r"array_slice\(array_merge\(\$head, \$own, \$video, \$facility\), 0, (6|8)\)", func),
          "a plain slice is still in the file")
    check("H18c: the walk is strongest-first over head/own/video/facility",
          "array_merge($head, $own, $video, $facility)" in func)

    # --- 2. the prose (functions.php) -------------------------------------
    check("H18c: neither docblock still promises a six-frame cap",
          "cap is six frames" not in func and "the six-frame cap" not in func,
          "a six-frame cap is still described")
    check("H18c: the ceiling is spelled out as seven PHOTO frames",
          "SEVEN PHOTO FRAMES" in func)
    check("H18c: the comment cites the measurement that set the number",
          "h18c_gallery_capacity_probe.js" in func)
    check("H18c: the comment names the regression the loop prevents",
          "eight photos" in func.lower() and "video cut off the end" in func.lower())

    # --- 3. the stylesheet (style.css) ------------------------------------
    rule = r"\.sf-fdetail2__media \.sf-gallery__thumbs:has\(\.sf-gallery__thumb:nth-child\(7\)\)\s*\{\s*gap:\s*8px;"
    check("H18c: the eight-pixel gap rule exists", re.search(rule, css) is not None)
    hit = re.search(rule, css)
    media = _enclosing_media(css, hit.start()) if hit else None
    check("H18c: the rule lives in the min-width:1101 desktop rail block",
          media is not None and "min-width: 1101px" in media, f"enclosing media: {media}")
    check("H18c: the rule is NOT inside a max-width block (never fires on the row layout)",
          media is None or "max-width" not in media, f"enclosing media: {media}")
    check("H18c: the base rail gap is still 12px, so four-tile rails do not move",
          re.search(r"\.sf-gallery__thumbs \{\s*display: flex;\s*gap: 12px;", css) is not None)
    check("H18c: the 8px is scoped, not a second blanket gap rule",
          css.count("gap: 8px") == 1 or
          # 8px legitimately appears in dot/mobile rules; require exactly one in the rail
          len(re.findall(r"sf-gallery__thumbs[^{]*\{[^}]*gap:\s*8px", css)) == 1,
          f"rail rules declaring 8px: {re.findall(r'sf-gallery__thumbs[^{]*{[^}]*gap:', css)}")
    check("H18c: the desktop tile is still 72px (the ceiling moved, not the tile)",
          re.search(r"\.sf-fdetail2__media \.sf-gallery__thumb \{[^}]*width: 72px;", css) is not None)
    check("H18c: style.css is still brace-balanced",
          css.count("{") == css.count("}"))
    check(f"H18c: the front-end version is deliberately still {VERSION}",
          re.search(rf"^Version:\s*{re.escape(VERSION)}\s*$", css, re.M) is not None,
          "style.css header version moved")

    # --- 4. what this batch must NOT have touched -------------------------
    check(f"H18c: the admin bundle is still {ADMIN_JS_VER}",
          f"'/assets/admin/sf-mb-tables.js', array(), '{ADMIN_JS_VER}'" in admin)
    for key in ("sf_formula_frame2_id", "sf_formula_frame3_id", "sf_formula_frame4_id"):
        check(f"H18c: H18's {key} slot survives untouched", key in admin and key in func)

    print(f"\n--source: {PASS} passed, {FAIL} failed")
    return FAIL


# --------------------------------------------------------------------------
# --live
# --------------------------------------------------------------------------
def ssh(script: str, timeout: int = 240) -> str:
    return subprocess.run(
        ["ssh", SERVER, "bash -s"],
        input=script, capture_output=True, text=True, timeout=timeout,
    ).stdout


LIVE_PHP = r"""
<?php
/* Batch H18c live probe — READ ONLY.
   The ceiling is exercised against the REAL theme function: own photos and the
   video are injected through get_post_metadata in memory, so no row is written
   (frame_meta_rows is asserted 0 at the end). Every case reads the injected
   values back, so a filter that silently failed to attach cannot make all the
   columns look alike. */

function h18c_state($slug, $pid, $own_csv, $video_url) {
    /* $GLOBALS, not a `use` capture: wp eval runs this outside the global
       scope, and a closure that cannot see its own config returns null for
       every case — the trap that makes all combinations look identical. */
    $GLOBALS['h18c_pid'] = (int) $pid;
    $cb = function ($value, $post_id, $meta_key, $single) use ($own_csv, $video_url) {
        if ((int) $post_id !== (int) $GLOBALS['h18c_pid']) { return $value; }
        if ($meta_key === 'sf_formula_gallery_ids' && $own_csv !== '') {
            return $single ? $own_csv : array($own_csv);
        }
        if ($meta_key === 'sf_formula_video_url' && $video_url !== '') {
            return $single ? $video_url : array($video_url);
        }
        return $value;
    };
    add_filter('get_post_metadata', $cb, 10, 4);

    $photos = 0; $videos = 0; $names = array();
    foreach (sinofresh_formula_gallery_slots($slug, $pid) as $s) {
        if (!empty($s['video_id'])) { $videos++; $names[] = 'VIDEO'; continue; }
        $photos++;
        $names[] = ($s['file'] !== '') ? $s['file'] : basename(parse_url($s['url'], PHP_URL_PATH));
    }
    /* readback self-proof: did the filter actually take? */
    $rb_own = (string) get_post_meta($pid, 'sf_formula_gallery_ids', true);
    $rb_vid = (string) get_post_meta($pid, 'sf_formula_video_url', true);

    remove_filter('get_post_metadata', $cb, 10);
    return array('frames' => $photos + $videos, 'photos' => $photos, 'videos' => $videos,
                 'names' => $names, 'rb_own' => $rb_own, 'rb_vid' => $rb_vid);
}

/* attachments that really resolve at 'large' */
$ids = get_posts(array('post_type' => 'attachment', 'post_mime_type' => 'image',
    'post_status' => 'inherit', 'numberposts' => 90, 'fields' => 'ids',
    'orderby' => 'ID', 'order' => 'ASC'));
$good = array();
foreach ($ids as $aid) {
    if (wp_get_attachment_image_src($aid, 'large')) { $good[] = (int) $aid; }
    if (count($good) >= 9) { break; }
}
$csv = function ($n) use ($good) { return implode(',', array_slice($good, 0, $n)); };

$plain = get_posts(array('post_type' => 'sf_formula', 'name' => 'calming-soft-chews',
    'numberposts' => 1, 'post_status' => 'publish'));
$withvid = get_posts(array('post_type' => 'sf_formula', 'name' => 'joint-support-soft-chews',
    'numberposts' => 1, 'post_status' => 'publish'));
$plain_id = $plain ? (int) $plain[0]->ID : 0;
$vid_id   = $withvid ? (int) $withvid[0]->ID : 0;

$YT = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
$out = array('good' => count($good), 'plain' => $plain_id, 'withvid' => $vid_id, 'cases' => array());
$cases = array(
    'plain 0 own'        => array($plain_id, 0, $csv(0), ''),
    'plain 2 own'        => array($plain_id, 2, $csv(2), ''),
    'plain 3 own'        => array($plain_id, 3, $csv(3), ''),
    'plain 4 own'        => array($plain_id, 4, $csv(4), ''),
    'plain 6 own'        => array($plain_id, 6, $csv(6), ''),
    'plain 7 own'        => array($plain_id, 7, $csv(7), ''),
    'plain 9 own'        => array($plain_id, 9, $csv(9), ''),
    'video real'         => array($vid_id, 0, '', ''),
    'video + 3 own'      => array($vid_id, 3, $csv(3), $YT),
    'video + 7 own'      => array($vid_id, 7, $csv(7), $YT),
    'video + 9 own'      => array($vid_id, 9, $csv(9), $YT),
);
foreach ($cases as $label => $c) {
    $st = h18c_state('soft-chews', $c[0], $c[2], $c[3]);
    $st['inject_own'] = ($c[2] === '') ? 0 : count(explode(',', $c[2]));
    $st['inject_video'] = ($c[3] === '') ? 0 : 1;
    $st['inject_own_csv'] = $c[2];
    $st['inject_video_url'] = $c[3];
    $out['cases'][$label] = $st;
}

global $wpdb;
$out['frame_meta_rows'] = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_frame%'");
$out['gallery_meta_rows'] = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key = 'sf_formula_gallery_ids'");
echo 'RESULT ' . json_encode($out) . "\n";
"""

# label -> (frames, photos, videos)
EXPECT = {
    "plain 0 own":     (4, 4, 0),
    "plain 2 own":     (6, 6, 0),
    "plain 3 own":     (7, 7, 0),
    "plain 4 own":     (7, 7, 0),
    "plain 6 own":     (7, 7, 0),
    "plain 7 own":     (7, 7, 0),
    "plain 9 own":     (7, 7, 0),
    "video real":      (5, 4, 1),
    "video + 3 own":   (8, 7, 1),
    "video + 7 own":   (8, 7, 1),
    "video + 9 own":   (8, 7, 1),
}


def live_gate():
    print("== live: the ceiling, against the real theme function (dev) ==")
    script = (
        "cd %s\ncat > /tmp/h18c-live.php <<'PHPEOF'\n%s\nPHPEOF\n"
        "wp eval-file /tmp/h18c-live.php --allow-root\nrm -f /tmp/h18c-live.php\n" % (WP_ROOT, LIVE_PHP)
    )
    raw = ssh(script)
    m = re.search(r"RESULT (\{.*\})", raw)
    if not m:
        check("live probe produced a RESULT line", False, raw[-600:])
        print(f"\n--live: {PASS} passed, {FAIL} failed")
        return FAIL
    d = json.loads(m.group(1))

    check("live: the probe found a record without a video and one with",
          d["plain"] > 0 and d["withvid"] > 0, f"plain={d['plain']} withvid={d['withvid']}")
    check("live: at least nine attachments resolve at 'large' for the injection",
          d["good"] >= 9, f"found {d['good']}")

    for label, (ef, ep, ev) in EXPECT.items():
        c = d["cases"].get(label)
        if c is None:
            check(f"live [{label}]: case ran", False, "missing from the probe output")
            continue
        check(f"live [{label}]: {ef} frames / {ep} photos / {ev} video",
              c["frames"] == ef and c["photos"] == ep and c["videos"] == ev,
              f"got {c['frames']}/{c['photos']}/{c['videos']} :: {' | '.join(c['names'])}")

    # Self-proof that the injection was live rather than inert. Only the cases
    # that INJECTED are asserted: a case with no injection reads the record's
    # own meta, and on this site one record really does carry a video, so
    # "no injection => empty" would be a claim about the data, not the filter.
    injected_own = {l: c for l, c in d["cases"].items() if c["inject_own_csv"]}
    injected_vid = {l: c for l, c in d["cases"].items() if c["inject_video_url"]}
    check("live: every injected gallery-ids value reads back byte-for-byte",
          len(injected_own) == 9 and all(c["rb_own"] == c["inject_own_csv"] for c in injected_own.values()),
          {"cases injecting own photos": len(injected_own),
           "mismatches": {l: (c["rb_own"][:24], c["inject_own_csv"][:24]) for l, c in injected_own.items()
                          if c["rb_own"] != c["inject_own_csv"]}})
    check("live: every injected video URL reads back byte-for-byte",
          len(injected_vid) == 3 and all(c["rb_vid"] == c["inject_video_url"] for c in injected_vid.values()),
          {l: (c["rb_vid"][:40], c["inject_video_url"][:40]) for l, c in injected_vid.items()
           if c["rb_vid"] != c["inject_video_url"]})

    # the property the whole batch turns on
    check("live: no case ever exceeds seven photo frames",
          all(c["photos"] <= PHOTO_CAP for c in d["cases"].values()),
          {l: c["photos"] for l, c in d["cases"].items()})
    check("live: no case ever exceeds eight frames",
          all(c["frames"] <= FRAME_CAP for c in d["cases"].values()),
          {l: c["frames"] for l, c in d["cases"].items()})
    v7 = d["cases"].get("video + 7 own", {})
    check("live: seven photos AND a video keep the video (the old slice dropped it)",
          v7.get("frames") == 8 and v7.get("photos") == 7 and v7.get("videos") == 1
          and "VIDEO" in v7.get("names", []),
          v7)

    check("live: the probe wrote nothing — no sf_formula_frame% rows exist",
          d["frame_meta_rows"] == 0, f"{d['frame_meta_rows']} rows")

    # the stylesheet the dev tree actually has on disk (that is what the theme
    # serves: the docroot's theme dir is a symlink into site-repo). The
    # over-HTTP byte identity is asserted by tools/h18c_geometry.js, which reads
    # the link tag, fetches that exact URL and records its md5.
    print("\n== live: the stylesheet on the dev tree ==")
    sheet = ssh("cd /var/www/dev.zxpet.com/site-repo && "
                "md5sum sinofresh-theme/style.css && "
                "grep -c 'nth-child(7)' sinofresh-theme/style.css && "
                "grep -c 'gap: 8px' sinofresh-theme/style.css && "
                "grep -m1 '^Version:' sinofresh-theme/style.css")
    lines = [l.strip() for l in sheet.strip().splitlines() if l.strip()]
    check("live: the dev stylesheet carries the seventh-tile rule exactly once",
          len(lines) >= 2 and lines[1] == "1", lines)
    check("live: the dev stylesheet is byte-identical to the workspace file",
          bool(lines) and lines[0].split()[0] == _md5_local(CSS), f"dev={lines[:1]} local={_md5_local(CSS)}")
    check(f"live: the dev stylesheet still declares {VERSION}",
          any(l == f"Version: {VERSION}" for l in lines), lines)

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
