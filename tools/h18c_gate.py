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

By design NOT changed by H18c: the admin bundle stayed 1.1.0 and no tile size
moved. (It moved to 1.2.0 in the later batch H19, which fixed the gallery
picker's `multiple` value; that number is kept current here because --source
asserts it.) --source asserts the rest of that "unchanged" promise too,
because "unchanged" is exactly what this batch promised.

One thing DID move after deployment: the front-end version, 2.10.88 -> 2.10.89.
The batch shipped without bumping it, which was wrong — style.css had changed,
and the origin serves CSS as `max-age=31536000, immutable` while the CDN keys
on the full URL including `?ver=`. So the edge kept handing out the old bytes
and browsers would not revalidate for a year. Changing the version is the only
thing that reaches both layers, so the follow-up bumped it. See
docs/h18c-fix-execution-report-2026-09-30.md §3 ⑤-b.

The geometry half of the acceptance is not here: --live asserts the CAP in
real theme code, while the rendered rail is measured by tools/h18c_geometry.js
(21 records at 1440 for drift, then 1101/1200/1240/1440 with seven tiles).

Usage:  h18c_gate.py [--source | --live]
"""
import json
import os
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
# Overridable so the same live assertions can be pointed at production:
#   H18C_WP_ROOT=/var/www/zxpet-v2 \
#   H18C_THEME_DIR=/var/www/zxpet-v2/wp-content/themes/sinofresh-theme \
#     h18c_gate.py --live
WP_ROOT = os.environ.get("H18C_WP_ROOT", "/var/www/dev.zxpet.com/public")
THEME_DIR = os.environ.get("H18C_THEME_DIR", "/var/www/dev.zxpet.com/site-repo/sinofresh-theme")
VERSION = "2.10.89"
ADMIN_JS_VER = "1.2.0"      # 1.1.0 under H18c; H19 fixed the picker, not H18c

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
    check(f"H18c: the front-end version is {VERSION} (the cache follow-up bumped it)",
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
    /* $own_csv / $video_url of NULL means "do not touch this key"; the empty
       STRING means "force it empty". Without that distinction a case meant to
       test "no own photos" silently reads whatever the record really has, and
       the expectation then depends on the site's data instead of on the code.
       This is the trap the production run hit: record 158 carries a video and
       (since ops started filling) its own photos too.

       $GLOBALS, not a `use` capture: wp eval runs this outside the global
       scope, and a closure that cannot see its own config returns null for
       every case — the trap that makes all combinations look identical. */
    $GLOBALS['h18c_pid'] = (int) $pid;
    $GLOBALS['h18c_own'] = $own_csv;
    $GLOBALS['h18c_vid'] = $video_url;
    $cb = function ($value, $post_id, $meta_key, $single) {
        if ((int) $post_id !== (int) $GLOBALS['h18c_pid']) { return $value; }
        if ($meta_key === 'sf_formula_gallery_ids' && $GLOBALS['h18c_own'] !== null) {
            $v = (string) $GLOBALS['h18c_own'];
            return $single ? $v : ($v === '' ? array() : array($v));
        }
        if ($meta_key === 'sf_formula_video_url' && $GLOBALS['h18c_vid'] !== null) {
            $v = (string) $GLOBALS['h18c_vid'];
            return $single ? $v : ($v === '' ? array() : array($v));
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
                 'names' => $names, 'rb_own' => $rb_own, 'rb_vid' => $rb_vid,
                 /* reported so the gate can prove the probe measured the record
                    it meant to — an array passed where an id belongs casts to 1
                    and quietly measures post 1 instead. */
                 'pid_used' => (int) $pid);
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
/* array(pid, NULL|own csv, NULL|video url). NULL = leave the record's own meta
   alone; '' = force that key empty. */
$cases = array(
    'baseline (no own, no video)' => array($plain_id, '', ''),
    'own 2'      => array($plain_id, $csv(2), ''),
    'own 3'      => array($plain_id, $csv(3), ''),
    'own 4'      => array($plain_id, $csv(4), ''),
    'own 6'      => array($plain_id, $csv(6), ''),
    'own 7'      => array($plain_id, $csv(7), ''),
    'own 9'      => array($plain_id, $csv(9), ''),
    'video only' => array($plain_id, '', $YT),
    'video + 3 own' => array($plain_id, $csv(3), $YT),
    'video + 7 own' => array($plain_id, $csv(7), $YT),
    'video + 9 own' => array($plain_id, $csv(9), $YT),
);
foreach ($cases as $label => $c) {
    $st = h18c_state('soft-chews', $c[0], $c[1], $c[2]);
    $st['forced_own'] = ($c[1] === null) ? 'untouched' : (($c[1] === '') ? 'empty' : count(explode(',', $c[1])));
    $st['forced_video'] = ($c[2] === null) ? 'untouched' : (($c[2] === '') ? 'empty' : 'set');
    $st['inject_own_csv'] = (string) $c[1];
    $st['inject_video_url'] = (string) $c[2];
    $out['cases'][$label] = $st;
}

/* The record as ops actually left it — no injection at all. Reported, not
   asserted: its composition is data, and ops is filling these right now.

   $vid_id, NOT $withvid: passing the get_posts() ARRAY here silently becomes
   (int) array = 1, and the probe then measures post 1 — a record with no video
   — which reads as "the video vanished". It did exactly that on the first run
   of this shape. */
$real = h18c_state('soft-chews', $vid_id, null, null);
$real['forced_own'] = 'untouched';
$real['forced_video'] = 'untouched';
$real['inject_own_csv'] = '';
$real['inject_video_url'] = '';
$out['cases']['real record untouched'] = $real;
$out['real_untouched_names'] = $real['names'];

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


def walk(facility: int, own: int, video: int):
    """The documented rule, written out a second time on purpose.

    Candidates are ranked strongest-first — head, own photos, video, facility —
    and then walked: a photo is skipped once seven have been taken, a video
    never spends a photo slot, and the list stops at eight frames. Re-deriving
    the expectation here (rather than hard-coding numbers) keeps the gate
    honest on a site whose facility band is not three frames deep, and the
    facility depth is READ OFF the baseline case instead of assumed."""
    merged = ['head'] + ['photo'] * own + (['video'] if video else []) + ['facility'] * facility
    kept, photos = [], 0
    for c in merged:
        if c != 'video':
            if photos >= PHOTO_CAP:
                continue
            photos += 1
        kept.append(c)
        if len(kept) >= FRAME_CAP:
            break
    return (len(kept), photos, sum(1 for c in kept if c == 'video'))


# label -> (own photos forced, video forced)
FORCED = {
    "baseline (no own, no video)": (0, 0),
    "own 2":     (2, 0),
    "own 3":     (3, 0),
    "own 4":     (4, 0),
    "own 6":     (6, 0),
    "own 7":     (7, 0),
    "own 9":     (9, 0),
    "video only":   (0, 1),
    "video + 3 own": (3, 1),
    "video + 7 own": (7, 1),
    "video + 9 own": (9, 1),
}


def frame_fingerprint() -> str:
    """count + md5 of every meta row whose key mentions sf_formula_frame.

    'The probe wrote nothing' cannot be asserted as 'no such rows exist' — ops
    fills these slots from wp-admin, so on a live site the rows are supposed to
    be there. What must hold is that the count and the bytes are the same
    before and after the probe."""
    return ssh("cd %s && wp db query \"SELECT CONCAT(COUNT(*), ' ', "
               "COALESCE(MD5(GROUP_CONCAT(CONCAT_WS(':', meta_id, post_id, meta_key, meta_value) "
               "ORDER BY meta_id SEPARATOR '|')), 'empty')) "
               "FROM wp_postmeta WHERE meta_key LIKE '%%sf_formula_frame%%'\" --allow-root\n"
               % WP_ROOT).strip().splitlines()[-1].strip()


def live_gate():
    print(f"== live: the ceiling, against the real theme function ({WP_ROOT}) ==")
    rows_before = frame_fingerprint()
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

    # the facility depth, read off the baseline rather than assumed
    base = d["cases"].get("baseline (no own, no video)", {})
    facility = base.get("frames", 0) - 1
    print(f"  (facility band depth observed on this site: {facility} frames)")
    check("live: the baseline case is a clean four-frame record (head + the whole facility band)",
          base.get("frames") == 4 and base.get("photos") == 4 and base.get("videos") == 0, base)

    for label, (own, video) in FORCED.items():
        c = d["cases"].get(label)
        if c is None:
            check(f"live [{label}]: case ran", False, "missing from the probe output")
            continue
        ef, ep, ev = walk(facility, own, video)
        check(f"live [{label}]: {ef} frames / {ep} photos / {ev} video",
              c["frames"] == ef and c["photos"] == ep and c["videos"] == ev,
              f"got {c['frames']}/{c['photos']}/{c['videos']} (facility depth {facility}) :: {' | '.join(c['names'])}")

    # The untouched record: printed, invariant-only. Its composition is ops's
    # data, which is changing under us — the exact counts above are the ones
    # that pin the rule, because their inputs are forced.
    real = d["cases"].get("real record untouched", {})
    print(f"  (untouched record as ops left it: pid {real.get('pid_used')} :: "
          f"{real.get('frames')} frames :: {' | '.join(real.get('names', []))})")
    check("live: the untouched case measured the record it was told to",
          real.get("pid_used") == d["withvid"],
          f"pid_used={real.get('pid_used')} expected={d['withvid']}")
    check("live: the untouched record still obeys both ceilings",
          real.get("photos", 99) <= PHOTO_CAP and real.get("frames", 99) <= FRAME_CAP,
          real)
    check("live: every measured case reports the pid it ran against",
          all(c.get("pid_used") for c in d["cases"].values() if c.get("pid_used") is not None),
          {l: c.get("pid_used") for l, c in d["cases"].items() if not c.get("pid_used")})

    # Self-proof that the injection was live rather than inert. Only the cases
    # that INJECTED are asserted: a case with no injection reads the record's
    # own meta, so "no injection => empty" would be a claim about the data.
    injected_own = {l: c for l, c in d["cases"].items() if c["forced_own"] not in ("untouched", "empty")}
    injected_vid = {l: c for l, c in d["cases"].items() if c["forced_video"] == "set"}
    check("live: every injected gallery-ids value reads back byte-for-byte",
          len(injected_own) == 9 and all(c["rb_own"] == c["inject_own_csv"] for c in injected_own.values()),
          {"own": len(injected_own), "video": len(injected_vid),
           "mismatches": {l: (c["rb_own"][:24], c["inject_own_csv"][:24]) for l, c in injected_own.items()
                          if c["rb_own"] != c["inject_own_csv"]}})
    check("live: the forced-empty cases really read back empty",
          all(c["rb_own"] == "" for c in d["cases"].values() if c["forced_own"] == "empty"),
          {"empty cases": [l for l, c in d["cases"].items() if c["forced_own"] == "empty"],
           "values": {l: c["rb_own"][:24] for l, c in d["cases"].items() if c["forced_own"] == "empty"}})
    check("live: every injected video URL reads back byte-for-byte",
          len(injected_vid) == 4 and all(c["rb_vid"] == c["inject_video_url"] for c in injected_vid.values()),
          {"video cases": len(injected_vid),
           "mismatches": {l: (c["rb_vid"][:40], c["inject_video_url"][:40]) for l, c in injected_vid.items()
                          if c["rb_vid"] != c["inject_video_url"]}})

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

    # "The probe wrote nothing" as an equality, not as an absence: ops fills
    # these slots from wp-admin, so on a live site the rows are supposed to be
    # there and asserting 0 rows would go red on a correct site (it did, on
    # production, where two records already carry all three slots).
    rows_after = frame_fingerprint()
    check("live: the probe left every sf_formula_frame% row byte-identical",
          rows_before == rows_after, f"before [{rows_before}] after [{rows_after}]")
    print(f"  (sf_formula_frame% rows on this site: {rows_before})")

    # the stylesheet the dev tree actually has on disk (that is what the theme
    # serves: the docroot's theme dir is a symlink into site-repo). The
    # over-HTTP byte identity is asserted by tools/h18c_geometry.js, which reads
    # the link tag, fetches that exact URL and records its md5.
    print("\n== live: the stylesheet on the tree behind the site ==")
    sheet = ssh("cd %s && " % THEME_DIR +
                "md5sum style.css && "
                "grep -c 'nth-child(7)' style.css && "
                "grep -m1 '^Version:' style.css")
    lines = [l.strip() for l in sheet.strip().splitlines() if l.strip()]
    check("live: the deployed stylesheet carries the seventh-tile rule exactly once",
          len(lines) >= 2 and lines[1] == "1", lines)
    check("live: the deployed stylesheet is byte-identical to the workspace file",
          bool(lines) and lines[0].split()[0] == _md5_local(CSS), f"remote={lines[:1]} local={_md5_local(CSS)}")
    check(f"live: the deployed stylesheet still declares {VERSION}",
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
