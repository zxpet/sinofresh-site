#!/usr/bin/env python3
"""
inquiry_throttle_gate.py — the per-IP throttle on POST /sinofresh/v1/inquiry.

Modes:
  --source     static assertions on the workspace copy
  --preflight  behavioural assertions against the preflight copy on dev
               (sync functions.php to sinofresh-theme-preflight FIRST, then
               fetch with X-SF-Preflight: 1)
  --live       the same behavioural assertions against the live theme
               (run AFTER the pull)

Behavioural contract proven (all modes 2-3):
  S1  source: throttle present, 429, 60s TTL, IP source, slot taken
      before wp_mail, placed after the cheap checks
  B1  a honeypot-rejected request burns NO slot (the next valid request
      still passes the throttle)
  B2  a valid request passes; an immediate second one answers 429 with
      code sf_inquiry_rate (old code cannot produce this — the status
      code itself proves which copy served)
  B3  after the 60s window the same IP can submit again (normal users
      are not permanently locked out)

Mail hygiene: the gate swaps sf_contact_email to a sink address on an
invalid TLD for the duration (try/finally restore) so no gate run mails
sales@zxpet.com. The transient slot is taken before wp_mail either way,
so the assertions do not depend on send success.

Runtime: ~70 s in behavioural modes (one 62 s sleep for the TTL window).
The gate deletes its own throttle transients before starting, and the
transient self-expires — no state is left behind.
"""

import argparse
import base64
import json
import re
import socket
import subprocess
import sys
import time
import urllib.request

# The gate must speak from ONE address. This machine is dual-stack and the
# route flaps between IPv6 and the VPN's IPv4 exit across requests — two
# client IPs means two throttle buckets, and the same-IP assertions see the
# wrong bucket. Forcing AF_INET keeps every request in one bucket.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(host, port, *args, **kwargs):
    # getaddrinfo(host, port, family=0, type=0, ...) — family is the first
    # optional argument, positionally (socket.create_connection passes it)
    kwargs.pop("family", None)
    if args:
        return _orig_getaddrinfo(host, port, socket.AF_INET, *args[1:], **kwargs)
    return _orig_getaddrinfo(host, port, family=socket.AF_INET, **kwargs)


socket.getaddrinfo = _ipv4_only

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
THEME = ROOT + "/sinofresh-theme"
HOST = "https://dev.zxpet.com"
SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SINK = "sf-gate-sink@example.invalid"   # invalid TLD: wp_mail accepts, nothing real is delivered

TTL = 60
SLEEP = TTL + 2

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
    req = urllib.request.Request(HOST + path, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("User-Agent", UA)
    if preflight:
        req.add_header("X-SF-Preflight", "1")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    req.add_header("Accept-Encoding", "identity")
    try:
        with urllib.request.build_opener().open(req, data=data, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def wp(*args):
    """One wp-cli call on dev. Args are shell-quoted, so eval code with
    parens/braces survives the trip."""
    quoted = " ".join("'" + a.replace("'", "'\\''") + "'" for a in args)
    cmd = ["ssh", SERVER, "cd %s && wp %s --allow-root" % (WP_ROOT, quoted)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError("wp %s failed: %s" % (" ".join(args), out.stderr[-400:]))
    return out.stdout.strip()


def clear_throttle_transients():
    """Delete every sf_inq_rl_ transient so the run starts from a clean
    bucket regardless of what ran before. The PHP goes over as a file
    (wp eval quoting does not survive two shells). Rows are non-autoload
    options with a timeout row each; the WordPress object cache is absent
    on dev, so a direct delete is final."""
    php = ("<?php\n"
           "global $wpdb;\n"
           "$like = '%sf_inq_rl_%';\n"
           "$wpdb->query($wpdb->prepare(\n"
           "    \"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s\",\n"
           "    $like, $like));\n")
    tmp = "/tmp/sf-rl-clear.php"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(php)
    subprocess.run(["scp", "-q", tmp, SERVER + ":/tmp/sf-rl-clear.php"],
                   check=True, timeout=30)
    wp("eval-file", "/tmp/sf-rl-clear.php")
    wp("eval", "unlink('/tmp/sf-rl-clear.php');")


VALID = {"website": "", "ts": 0, "name": "Throttle Gate", "email": "gate@example.com",
         "company": "", "country": "", "message": "gate", "source": "throttle-gate", "formula": 158}


def post(body, preflight):
    ts = int(time.time() * 1000) - 5000          # opened "5s ago": past the time-on-form check
    payload = dict(body, ts=ts if body.get("ts", 0) == 0 else body["ts"])
    return fetch("/wp-json/sinofresh/v1/inquiry", preflight=preflight,
                 method="POST", payload=payload)


def behavioural(tag, preflight):
    print("== %s — throttle behaviour ==" % tag)
    clear_throttle_transients()
    original = wp("option", "get", "sf_contact_email")
    swapped = False
    try:
        if original != SINK:
            wp("option", "update", "sf_contact_email", SINK)
            swapped = True
        check("sf_contact_email parked on the gate sink",
              wp("option", "get", "sf_contact_email") == SINK)

        # B1: garbage does not burn a slot
        spam = dict(VALID, website="http://spam.example")
        st1, b1 = post(spam, preflight)
        check("honeypot request rejected 400 (sf_inquiry_spam)",
              st1 == 400 and "sf_inquiry_spam" in b1, (st1, b1[:120]))

        # B2: valid passes, immediate repeat is 429
        st2, b2 = post(dict(VALID), preflight)
        check("first valid request passes the throttle (200 or 500-from-mail, NOT 429)",
              st2 in (200, 500) and "sf_inquiry_rate" not in b2, (st2, b2[:160]))
        st3, b3 = post(dict(VALID), preflight)
        check("second request within 60s answers 429 sf_inquiry_rate",
              st3 == 429 and "sf_inquiry_rate" in b3, (st3, b3[:160]))

        # B3: after the window the same IP is free again
        print("  ..   sleeping %ds for the TTL window" % SLEEP)
        time.sleep(SLEEP)
        st4, b4 = post(dict(VALID), preflight)
        check("after the 60s window the same IP can submit again (NOT 429)",
              st4 in (200, 500) and "sf_inquiry_rate" not in b4, (st4, b4[:160]))
    finally:
        if swapped:
            wp("option", "update", "sf_contact_email", original)
        got = wp("option", "get", "sf_contact_email")
        check("sf_contact_email restored to %s" % original, got == original, got)
        clear_throttle_transients()


def source_mode():
    fn_raw = read("functions.php")
    # code assertions read the comment-stripped body
    fn = re.sub(r'/\*.*?\*/', '', fn_raw, flags=re.S)
    fn = re.sub(r'(?m)^\s*\*.*$', '', fn)
    fn = re.sub(r'(?m)^\s*//.*$', '', fn)

    print("== S1 functions.php — the per-IP throttle ==")
    check("transient bucket key sf_inq_rl_ exists",
          "sf_inq_rl_" in fn)
    check("the bucket is an md5 of the client IP helper",
          "md5(sinofresh_inquiry_client_ip())" in fn)
    check("the IP helper prefers CF-Connecting-IP and falls back to REMOTE_ADDR",
          "HTTP_CF_CONNECTING_IP" in fn and "REMOTE_ADDR" in fn
          and "function sinofresh_inquiry_client_ip()" in fn)
    check("the over-limit answer is WP_Error ... status 429 with its own code",
          re.search(r"WP_Error\('sf_inquiry_rate'.*?'status' => 429\)", fn, re.S) is not None)
    check("the slot is a 60-second transient",
          re.search(r"set_transient\(\$rl_key, 1, 60\)", fn) is not None)
    m_throttle, m_mail = fn.find("get_transient($rl_key)"), fn.find("wp_mail($to")
    check("the slot is taken BEFORE wp_mail (a send failure cannot be hammered)",
          0 < m_throttle < m_mail, (m_throttle, m_mail))
    m_email = fn.find("sf_inquiry_email")
    check("the throttle sits AFTER the field checks (garbage never burns a slot)",
          m_email != -1 and m_email < fn.find("set_transient($rl_key"), (m_email,))
    check("no other endpoint shares the bucket key",
          fn.count("sf_inq_rl_") == 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.source:
        source_mode()
    if args.preflight:
        behavioural("preflight", True)
    if args.live:
        behavioural("live", False)
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
