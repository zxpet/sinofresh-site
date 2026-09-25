#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H9 override probe — proves the Configurator Display plumbing AND the
"tick N, the page shows N (+Custom)" model end to end, WITHOUT the admin UI.

Mechanism: the admin metabox persists its rows into ONE meta key
(sf_formula_groups_config) and the checkboxes into the group metas; writing
those metas directly (with backup + restore) is the same round-trip the editor
does, minus the browser. Every fetch carries X-SF-Preflight: 1 so the
candidate theme serves the page; dev's live 2.10.81 is untouched.

All writes are on post 158 (dev sandbox), backup-first, restored before exit.
"""

import base64
import json
import re
import subprocess
import sys
import time
import urllib.request

HOST = "https://dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
POST = 158

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


def ssh(script):
    r = subprocess.run(["ssh", "root@65.49.215.152", "cd /var/www/dev.zxpet.com/public && wp eval-file /tmp/h9_probe_step.php --allow-root"],
                       input=script, text=True, capture_output=True)
    return r.stdout + r.stderr


def set_metas(kv):
    """kv: dict meta_key -> value ('' = delete). Runs via a step file so the
    quoting never passes through two shells."""
    body = "<?php\n"
    for k, v in kv.items():
        if v == "":
            body += "delete_post_meta(%d, %s);\n" % (POST, json.dumps(k))
        else:
            body += "update_post_meta(%d, %s, %s);\n" % (POST, json.dumps(k), json.dumps(v))
    body += "echo 'STEP-OK';\n"
    with open("/tmp/h9_probe_step.php", "w") as fh:
        fh.write(body)
    push = subprocess.run(["scp", "-q", "/tmp/h9_probe_step.php",
                           "root@65.49.215.152:/tmp/h9_probe_step.php"],
                          capture_output=True, text=True)
    if push.returncode != 0:
        return "SCP-FAIL " + push.stderr
    return ssh("")


def fetch158():
    time.sleep(1.3)
    req = urllib.request.Request(HOST + "/formulas/joint-support-soft-chews/")
    req.add_header("Authorization", AUTH)
    req.add_header("User-Agent", UA)
    req.add_header("X-SF-Preflight", "1")
    req.add_header("Accept-Encoding", "identity")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def group_names(doc):
    return re.findall(r'data-sf-config-group="([^"]+)"', doc)


def options_of(doc, key):
    m = re.search(r'data-sf-config-group="%s">.*?(?=data-sf-config-group="|'
                  r'class="sf-fdetail-config__summary")' % re.escape(key), doc, re.S)
    if not m:
        return None
    return re.findall(r'name="sf-config-[^"]*" value="([^"]*)"', m.group(0))


def label_of(doc, key):
    m = re.search(r'data-sf-config-group="%s">.*?sf-fdetail-config__label">([^<]*)<'
                  % re.escape(key), doc, re.S)
    return m.group(1) if m else None


print("== P0 backup ==")
out = set_metas({"__probe_backup__": ""})  # warm the pipe; real backup below
backup_script = """<?php
$post_id = 158;
$keys = array('sf_formula_groups_config','sf_formula_flavors','sf_formula_weight','sf_formula_shape','sf_formula_container');
$out = array('post_id' => $post_id);
foreach ($keys as $k) { $out[$k] = get_post_meta($post_id, $k, true); }
file_put_contents('/tmp/h9-probe-backup.json', wp_json_encode($out));
echo 'BACKUP-OK ' . filesize('/tmp/h9-probe-backup.json');
"""
with open("/tmp/h9_probe_step.php", "w") as fh:
    fh.write(backup_script)
push = subprocess.run(["scp", "-q", "/tmp/h9_probe_step.php",
                       "root@65.49.215.152:/tmp/h9_probe_step.php"],
                      capture_output=True, text=True)
out = ssh("")
check("meta backup written to /tmp/h9-probe-backup.json", "BACKUP-OK" in out, out)

try:
    print("== P1 label override + show flag (Configurator Display) ==")
    cfg = json.dumps({
        "flavor": {"label": "Taste"},
        "container": {"show": False},
        "shape": {"label": "Look"},
    }, ensure_ascii=False)
    out = set_metas({"sf_formula_groups_config": cfg})
    check("groups_config written", "STEP-OK" in out, out)
    doc = fetch158()
    check("flavor group now titled 'Taste' (same name the admin shows)",
          label_of(doc, "flavor") == "Taste", label_of(doc, "flavor"))
    check("shape group now titled 'Look'", label_of(doc, "shape") == "Look",
          label_of(doc, "shape"))
    check("container group hidden by the switch", "container" not in group_names(doc),
          group_names(doc))
    check("the hidden group left no husk in the HTML",
          'data-sf-config-group="container"' not in doc)

    print("== P2 tick 3, the page shows 3 + Custom ==")
    out = set_metas({"sf_formula_shape": '["Bone","Round","Square"]'})
    check("shape meta written", "STEP-OK" in out, out)
    doc = fetch158()
    got = options_of(doc, "shape")
    check("shape options are exactly the ticked three + one Custom",
          got == ["Bone", "Round", "Square", "Custom"], got)

    print("== P3 restore ==")
    out = set_metas({"sf_formula_groups_config": "", "sf_formula_shape": "Bone"})
    doc = fetch158()
    check("flavor label back to pool default 'Flavor'",
          label_of(doc, "flavor") == "Flavor", label_of(doc, "flavor"))
    check("container group back", "container" in group_names(doc))
    check("shape back to the single Bone + Custom",
          options_of(doc, "shape") == ["Bone", "Custom"], options_of(doc, "shape"))
finally:
    print("== P4 restore safety (idempotent) ==")
    out = set_metas({"sf_formula_groups_config": "", "sf_formula_shape": "Bone"})
    check("restore step executed", "STEP-OK" in out, out)

print()
if FAILED:
    print("RESULT  %d ok, %d FAIL" % (PASSED, len(FAILED)))
    for n, d in FAILED:
        print("  FAIL %s  %s" % (n, d))
    sys.exit(1)
print("RESULT  %d/%d PASS" % (PASSED, PASSED))
