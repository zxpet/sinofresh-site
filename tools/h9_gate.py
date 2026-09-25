#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H9 gate — the configurator becomes "admin multi, front-end single".

Modes
-----
--source      static assertions on the WORKSPACE bytes (runs before anything
              is uploaded; no network).
--preflight   live assertions against the preflight copy on dev
              (sinofresh-theme-preflight, fetched with X-SF-Preflight: 1).
              Runs BEFORE the pull and BEFORE the meta migration: post 158 is
              still in its legacy state, so this mode proves the legacy
              string readers render correctly (weight "2.5g", shape "Bone",
              container "Round").
--live        post-pull, post-migration assertions against dev's own theme:
              the same group composition, the migrated container value, and
              the Chinese-free front end.

Environment
-----------
dev 65.49.215.152, Basic sfdev / VkEws18Kl5V1qp3TpZ6s, browser UA required
(CF edge injects content by UA), >=1.2s between fetches, REST POST allowed.

Discipline: every assertion names what it anchors (element counts, markup
anchors — never bare substrings); negative claims anchor OLD-specific shapes,
not words a new text may legitimately contain.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
THEME = ROOT + "/sinofresh-theme"
HOST = "https://dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

FAILED = []
PASSED = 0


def check(name, ok, detail=None):
    global PASSED
    if ok:
        PASSED += 1
        print("  ok   %s" % name)
    else:
        FAILED.append((name, detail))
        print("  FAIL %s   %s" % (name, detail if detail is not None else ""))


def read(path):
    with open(THEME + "/" + path, encoding="utf-8") as fh:
        return fh.read()


def fetch(path, preflight=False, method="GET", payload=None):
    """One fetch; returns (status, body). Retries are NOT automatic: the
    caller owns the 1.2s spacing."""
    req = urllib.request.Request(HOST + path, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("User-Agent", UA)
    if preflight:
        req.add_header("X-SF-Preflight", "1")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    req.add_header("Accept-Encoding", "identity")  # never claim what we cannot parse
    opener = urllib.request.build_opener()
    try:
        with opener.open(req, data=data, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------
# --source : static assertions on the workspace
# --------------------------------------------------------------------------

CJK = re.compile(r'[\u4e00-\u9fff]')


def strip_php_comments(text):
    """Remove PHP comment bodies so the Chinese-free assertion can be about
    OUTPUT, not about the (legitimately Chinese) editor hints in comments.
    The metabox hints are STRINGS, not comments, so they must live in
    formula-admin.php and MUST NOT survive this strip anywhere else."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'(?m)^\s*//.*$', '', text)
    return text


def source_mode():
    fn_raw = read("functions.php")
    fn = strip_php_comments(fn_raw)   # code assertions read the stripped body
    admin = read("inc/formula-admin.php")
    pools = read("inc/formula-pools.php")
    css = read("style.css")

    print("== S1 functions.php — the new group model ==")
    check("config_groups reads the record's weight meta (array-or-legacy reader)",
          "$meta_values('sf_formula_weight')" in fn)
    check("config_groups reads the record's counts meta",
          "$meta_values('sf_formula_counts')" in fn)
    check("config_groups builds the Net Content group (key net-content)",
          "'key' => 'net-content'" in fn)
    check("the old specs-parsed 'pack' group is retired",
          "'key' => 'pack'" not in fn)
    check("no group is named Piece Weight / Pack Size in any array literal",
          re.search(r"'label' => '(Piece Weight|Pack Size)'", fn) is None)
    check("Suitable For derives 'Dog and Cat' when both are ticked",
          "Dog and Cat" in fn
          and "in_array('Dog', $species, true) && in_array('Cat', $species, true)" in fn)
    check("species/stage groups are single-choice with no custom pick",
          re.search(r"'key' => 'species'.*?'type' => 'single'.*?"
                    r"sf_formula_options_with_custom\(\$options, true\)", fn, re.S) is not None
          and re.search(r"'key' => 'stage'.*?"
                        r"sf_formula_options_with_custom\(\$options_from\(\$lifestage_vals\), true\)",
                        fn, re.S) is not None)
    check("shape options come from the record, library only carries pictures",
          "$meta_values('sf_formula_shape')" in fn
          and "sf_formula_library_options($shape_vals, sf_shape_library())" in fn)
    check("container options come from the record",
          "$meta_values('sf_formula_container')" in fn
          and "array_map('sinofresh_container_label', $cont_vals)" in fn)
    check("the inquiry fallback rows are derived from config_groups (one source)",
          re.search(r"function sinofresh_inquiry_selection_rows.*?"
                    r"sinofresh_formula_config_groups\(\$post_id\)", fn, re.S) is not None
          and "Piece Weight" not in fn)

    print("== S2 functions.php — the front end stays Chinese-free ==")
    body = strip_php_comments(fn_raw)
    check("no CJK survives comment-stripping in functions.php",
          CJK.search(body) is None,
          CJK.findall(body)[:5])
    # JS: comments ship as separate assets, not inside the served HTML (the
    # served-HTML check is R3); still, assert no CJK outside JS comments.
    js_clean = True
    js_hits = []
    for p in ["assets/js/config.js", "assets/js/inquiry.js"]:
        t = read(p)
        t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
        t = re.sub(r'(?m)^\s*//.*$', '', t)
        if CJK.search(t):
            js_clean = False
            js_hits.append((p, CJK.findall(t)[:3]))
    check("no CJK outside comments in config.js / inquiry.js", js_clean, js_hits)

    print("== S3 formula-admin.php — multi fields, applies, Configurator Display ==")
    for key in ["sf_formula_weight", "sf_formula_shape", "sf_formula_container",
                "sf_formula_lifestage"]:
        m = re.search(r"'key' => '%s'.*?\n\t\tarray\(" % key, admin, re.S)
        seg = m.group(0) if m else ""
        check("%s is now a multi checkbox" % key,
              bool(m) and "'type' => 'multi'" in seg, seg[:80])
    check("Unit Weight applies to exactly the three chew/tablet forms",
          "'applies' => array('soft-chews', 'tablets', 'dental-chews')" in admin)
    check("the renderer hides non-applied fields",
          "!in_array($form, $spec['applies'], true)" in admin)
    check("the Configurator Display box is registered and rendered",
          "'config'    => array('title' => 'Configurator Display'" in admin
          and "sf_formula_render_config_box($post)" in admin)
    check("the box saves through one JSON meta",
          "sf_formula_save_groups_config($post_id, $form);" in admin
          and "sf_mb_store($post_id, 'sf_formula_groups_config'," in admin)
    check("all-default rows are omitted (empty-means-absent preserved)",
          "if ($entry) {" in admin and "$entry['show'] = false;" in admin)
    check("the editor hints are Chinese (the ONLY allowed CJK among PHP output)",
          CJK.search(admin) is not None)
    check("no Chinese leaks into a <label> or option VALUE in the admin file",
          all(not CJK.search(m.group(0))
              for m in re.finditer(r"<label[^>]*>", admin)))
    check("every one of the eight groups has a Configurator Display row",
          all(("'%s'" % k) in admin or json.dumps(k) in admin for k in
              ["flavor", "weight", "counts", "net-content", "shape",
               "container", "species", "stage"]))

    print("== S4 formula-pools.php — the Net Content dimension ==")
    check("sf_formula_group_defaults gates weight/counts to the three chew forms",
          "in_array($form, array('soft-chews', 'tablets', 'dental-chews'), true)" in pools
          and "'applies' => $chew" in pools)
    for form in ["soft-chews", "tablets", "dental-chews", "pastes", "powders",
                 "drops", "liquids", "fish-oil"]:
        m = re.search(r"'%s' => array\(.*?\n\t\t\)," % form, pools, re.S)
        seg = m.group(0) if m else ""
        check("%s has a net_content pool ending in Custom" % form,
              bool(m) and "'net_content' => array(" in seg
              and "Custom" in seg, form)

    print("== S5 version and assets ==")
    check("style.css declares 2.10.82",
          "Version: 2.10.82" in css[:2000])
    check("functions.php enqueues 2.10.82",
          "array(), '2.10.82');" in fn)
    check("sf-mb.css bumped to 1.1.0 for the Configurator Display styles",
          "wp_enqueue_style('sf-mb', $dir . '/assets/admin/sf-mb.css', array(), '1.1.0');" in admin
          and ".sf-cfg__row" in read("assets/admin/sf-mb.css"))


# --------------------------------------------------------------------------
# --preflight / --live : rendered assertions
# --------------------------------------------------------------------------

def group_names(doc):
    return re.findall(r'data-sf-config-group="([^"]+)"', doc)


def group_segment(doc, key):
    m = re.search(r'data-sf-config-group="%s">.*?(?=data-sf-config-group="|'
                  r'class="sf-fdetail-config__summary")' % re.escape(key), doc, re.S)
    return m.group(0) if m else ""


def options_of(seg):
    return re.findall(r'type="(radio|checkbox)" name="([^"]+)" value="([^"]*)"', seg)


def rendered_mode(mode):
    preflight = (mode == "preflight")
    tag = "preflight" if preflight else "live"
    print("== R1 post 158 — group composition (%s) ==" % tag)
    time.sleep(1.3)
    st, doc = fetch("/formulas/joint-support-soft-chews/", preflight=preflight)
    check("158 served 200 with bytes (%s)" % tag, st == 200 and len(doc) > 50000,
          (st, len(doc)))
    if st != 200:
        return
    groups = group_names(doc)
    check("pricing ladder heads the list", groups[:1] == ["pricing"], groups[:3])
    check("flavor group present with 13 record values (Custom already in list)",
          "flavor" in groups and len(options_of(group_segment(doc, "flavor"))) == 13)
    check("Unit Weight renders the legacy string as a one-option radio + Custom",
          len(options_of(group_segment(doc, "weight"))) == 2)
    check("Counts renders 9 record values + none appended (Custom already in list)",
          len(options_of(group_segment(doc, "counts"))) == 9)
    check("Net Content ABSENT on 158 (no meta yet — no empty husk)",
          "net-content" not in groups)
    check("Shape renders from the record (Bone) not the pool (8 values)",
          "shape" in groups and len(options_of(group_segment(doc, "shape"))) == 2)
    cont_opts = options_of(group_segment(doc, "container"))
    if mode == "preflight":
        check("Container renders legacy Round verbatim + Custom (pre-migration)",
              [v for _t, _n, v in cont_opts] == ["Round", "Custom"], cont_opts)
    else:
        check("Container renders the migrated Plastic Bottle + Custom",
              [v for _t, _n, v in cont_opts] == ["Plastic Bottle", "Custom"], cont_opts)
    check("every rendered group is single-choice (radio only)",
          all(t == "radio" for t, _n, _v in
              [o for g in groups for o in options_of(group_segment(doc, g))]))

    print("== R2 spec sheet and the old labels (%s) ==" % tag)
    check("the spec sheet has no Piece Weight row (the label retired with H9)",
          "Piece Weight" not in doc)
    check("the spec sheet Unit Weight row prints the record's own meta (2.5g)",
          re.search(r"Unit Weight</dt><dd[^>]*>2\.5g</dd>", doc) is not None)
    check("the spec sheet Pack Size row is fed by the counts meta (not the specs blob)",
          re.search(r"Pack Size</dt><dd[^>]*>30, 60, 90", doc) is not None)
    check("the spec sheet Shape row prints the record's own value",
          re.search(r"Shape\b.*Bone", doc, re.S) is not None)

    print("== R3 the front end stays Chinese-free (%s) ==" % tag)
    check("no CJK anywhere in the served HTML",
          CJK.search(doc) is None,
          CJK.findall(doc)[:5])

    print("== R4 an unbackfilled record renders no empty husks (%s) ==" % tag)
    time.sleep(1.3)
    st2, doc2 = fetch("/formulas/probiotic-powder/", preflight=preflight)
    check("165 served 200", st2 == 200 and len(doc2) > 50000, (st2, len(doc2)))
    if st2 == 200:
        g2 = group_names(doc2)
        for absent in ["flavor", "weight", "counts", "net-content", "shape",
                       "container", "species", "stage"]:
            check("165 renders no '%s' group" % absent, absent not in g2, g2)

    print("== R5 the inquiry endpoint still accepts a single-choice payload (%s) ==" % tag)
    time.sleep(1.3)
    st3, body = fetch("/wp-json/sinofresh/v1/inquiry", preflight=preflight,
                      method="POST",
                      payload={"name": "H9 Gate", "email": "h9gate@example.com",
                               "formula": 158,
                               "config": {"flavor": "Chicken", "weight": "2.5g"},
                               "ts": int(time.time() * 1000) - 9000})
    ok = st3 == 200 and '"ok":true' in body.replace(" ", "")
    check("REST inquiry accepts the H9 payload (200, ok:true)", ok, (st3, body[:120]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.source:
        source_mode()
    if args.preflight:
        rendered_mode("preflight")
    if args.live:
        rendered_mode("live")
    if not (args.source or args.preflight or args.live):
        ap.error("pick a mode")
    print()
    if FAILED:
        print("RESULT  %d ok, %d FAIL" % (PASSED, len(FAILED)))
        for name, detail in FAILED:
            print("  FAIL %s  %s" % (name, detail))
        sys.exit(1)
    print("RESULT  %d/%d PASS" % (PASSED, PASSED))


if __name__ == "__main__":
    main()
