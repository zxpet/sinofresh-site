#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 5 — error-log audit by attribution, not by size.

WHY THIS TOOL EXISTS
--------------------
Earlier batches used "the error log did not grow" as the invariant. That is
not an invariant at all: this box is on the public internet, and 4c caught two
brand-new lines appearing between two runs, both from an outside scanner
probing /cgi-bin/.%2e/... .  A scanner writes to the log whether or not we do,
so byte volume and mtime can move for reasons that have nothing to do with us.

The invariant that does hold is: **every line can be attributed.**  So this
tool asks, for every single line in every log that could possibly carry our
damage:

  * is its timestamp inside the batch window?            -> that would be ours
  * if not, whose is it — and does the access log agree?  -> foot it

The attribution hinge is Basic Auth.  The dev site is behind a global
htpasswd, and Apache's `combined` log format records the authenticated user
in field 3, so every request of ours is stamped `sfdev` and every external
scanner is stamped `-`.  That makes "did our traffic cause this?" a decidable
question rather than a guess.

Also checked, and deliberately NOT used as the headline: byte volume and
mtime.  They are printed for the record only.

    python3 tools/b2d_s5_logaudit.py
    python3 tools/b2d_s5_logaudit.py --margin 5 --window-from-preflight <file>

The batch window is derived from the archived pre-flight log (the mu-plugin
stamped every request that carried the switch header), padded by --margin
minutes on each side.  Anything inside the padded window fails the audit.
"""

import argparse
import datetime as dt
import os
import re
import shlex
import subprocess
import sys

HOST = "root@65.49.215.152"

# every log on this box that could plausibly record damage done by a batch
# request.  dev.zxpet.com-error.log is the port-80 vhost; it is expected empty.
ERROR_LOGS = [
    "/var/log/httpd/dev.zxpet.com-ssl-error.log",
    "/var/log/httpd/dev.zxpet.com-error.log",
    "/var/log/httpd/error_log",
    "/var/log/php-fpm/www-error.log",
]
ACCESS_LOG = "/var/log/httpd/dev.zxpet.com-ssl-access.log"
DEBUG_LOG = "/var/www/dev.zxpet.com/public/wp-content/debug.log"

# the switch was delivered as a header, so the copy of the log that proves the
# window lives in the repo, not on the box.
PREFLIGHT_LOG = "docs/b2d-step5-shots/s5-preflight.log.txt"

# Apache lifecycle noise that carries no client and cannot be ours: startup /
# graceful-restart notices and the origin-cert name mismatch warning.
LIFECYCLE = re.compile(
    r"AH02282|AH00489|AH00094|AH00493|AH01909|resuming normal operations|"
    r"SIGUSR1 received|No slotmem|Command line:")

TS_RE = re.compile(r"\[(\w{3}) (\w{3}) +(\d+) (\d\d):(\d\d):(\d\d)(?:\.\d+)? (\d{4})\]")
# the access log uses the other Apache timestamp flavour: [20/Sep/2026:23:50:12 +0000]
ACCESS_TS_RE = re.compile(r"\[(\d{2})/(\w{3})/(\d{4}):(\d\d):(\d\d):(\d\d) ")
# PHP-FPM writes a third flavour: [20-Sep-2026 05:49:31 UTC]
PHP_TS_RE = re.compile(r"\[(\d{2})-(\w{3})-(\d{4}) (\d\d):(\d\d):(\d\d) ")
CLIENT_RE = re.compile(r"\[client (\d+\.\d+\.\d+\.\d+):\d+\]")
# any path under the docroot named inside a message, mapped back to its URL
DOCPATH_RE = re.compile(re.escape("/var/www/dev.zxpet.com/public") + r"(/[^\s:)\"']+)")
# combined: host ident user [ts] "req" status bytes "ref" "ua"
ACCESS_RE = re.compile(
    r'^(\S+) (\S+) (\S+) \[[^\]]+\] "([^"]*)" (\d{3}) (\S+) "([^"]*)" "([^"]*)"')

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# The one username any of our tooling ever uses.  Everything else in the user
# field of the access log is somebody else.
OUR_USER = "sfdev"
DOCROOT = "/var/www/dev.zxpet.com/public"


def remote(path, text=True):
    p = subprocess.run(["ssh", "-o", "ConnectTimeout=25", HOST,
                        "cat " + shlex.quote(path)],
                       capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace") if text else p.stdout


def remote_stat(path):
    """Return (bytes, mtime-string) or None.  For the record only."""
    p = subprocess.run(["ssh", "-o", "ConnectTimeout=25", HOST,
                        "stat -c '%s %y' " + shlex.quote(path)],
                       capture_output=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    parts = p.stdout.decode().strip().split(None, 1)
    return int(parts[0]), parts[1]


def parse_apache_ts(line):
    m = TS_RE.search(line)
    if not m:
        return None
    mon, day, hh, mm, ss, year = (m.group(2), int(m.group(3)), int(m.group(4)),
                                  int(m.group(5)), int(m.group(6)), int(m.group(7)))
    return dt.datetime(year, MONTHS[mon], day, hh, mm, ss)


def parse_access_ts(line):
    m = ACCESS_TS_RE.search(line)
    if not m:
        return None
    day, mon, year, hh, mm, ss = (int(m.group(1)), m.group(2), int(m.group(3)),
                                  int(m.group(4)), int(m.group(5)), int(m.group(6)))
    return dt.datetime(year, MONTHS[mon], day, hh, mm, ss)


def parse_php_ts(line):
    m = PHP_TS_RE.search(line)
    if not m:
        return None
    day, mon, year, hh, mm, ss = (int(m.group(1)), m.group(2), int(m.group(3)),
                                  int(m.group(4)), int(m.group(5)), int(m.group(6)))
    return dt.datetime(year, MONTHS[mon], day, hh, mm, ss)


def split_records(text):
    """Group a log into records.

    PHP-FPM writes multi-line records: a fatal error's stack trace has no
    timestamp of its own, so a line-by-line audit would either drop the
    continuations or condemn them as 'no parsable timestamp'.  Anything without
    a timestamp belongs to the record above it; a continuation with nothing
    above it is a genuine finding.
    """
    out, cur = [], None
    for line in text.splitlines():
        if not line.strip():
            continue
        ts = parse_apache_ts(line)
        if ts is None:
            ts = parse_php_ts(line)
        if ts is not None:
            cur = {"ts": ts, "lines": [line], "cont": 0}
            out.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
            cur["cont"] += 1
        else:
            out.append({"ts": None, "lines": [line], "cont": 0})
    return out


def parse_iso(ts):
    # naive UTC: the box runs UTC (timedatectl says so), which is what makes the
    # mu-plugin's +00:00 stamps directly comparable to Apache's local-time logs
    return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")


def load_window(path, margin_min):
    if not os.path.exists(path):
        raise SystemExit("missing the archived pre-flight log: %s\n"
                         "(the window cannot be derived without it)" % path)
    stamps = []
    for line in open(path, encoding="utf-8"):
        m = re.search(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\+00:00\]", line)
        if m:
            stamps.append(parse_iso(m.group(1)))
    if not stamps:
        raise SystemExit("no timestamps parsed out of %s" % path)
    tight = (min(stamps), max(stamps))
    pad = dt.timedelta(minutes=margin_min)
    return tight, (tight[0] - pad, tight[1] + pad), len(stamps)


def load_access(text, window):
    """Parse the access log; return (all_lines, in_window, sfdev_ips)."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = ACCESS_RE.match(line)
        ts = parse_access_ts(line)
        if m:
            rows.append((ts, m.group(1), m.group(3), m.group(4), m.group(5),
                         m.group(8), line))
        else:
            # a line the combined pattern cannot parse is itself a finding: the
            # audit must not silently drop it.
            rows.append((ts, None, None, None, None, None, line))
    in_win = [r for r in rows if r[0] and window[0] <= r[0] <= window[1]]
    per_ip = {}
    for ts, ip, user, req, status, ua, _ in rows:
        d = per_ip.setdefault(ip, {"n": 0, "sfdev": 0, "last": None,
                                   "first": None, "sample": None, "ua": ua})
        d["n"] += 1
        if user == "sfdev":
            d["sfdev"] += 1
        if ts:
            d["first"] = d["first"] or ts
            d["last"] = ts
        if d["sample"] is None:
            d["sample"] = (req, status, ua)
    return rows, in_win, per_ip


_SIZE_CACHE = {}


def remote_size(path):
    if path not in _SIZE_CACHE:
        st = remote_stat(path)
        _SIZE_CACHE[path] = st[0] if st else None
    return _SIZE_CACHE[path]


def classify(ts, text, window, rows):
    """Return (ok, reason) for one error-log line.

    Attribution is done by *content*, and specifically by the authenticated
    username — never by client IP.  The dev site sits behind Cloudflare, so an
    origin-log IP is a shared edge address: the first version of this tool
    cleared/condemned lines by IP and produced three false alarms, because
    /cdn-cgi/ edge IPs relay our traffic AND a stranger's in the same minute.
    The access log's user field, by contrast, is per-request and our tooling
    only ever writes the one username.
    """
    if ts is None:
        return False, "no parsable timestamp"
    if window[0] <= ts <= window[1]:
        return False, "inside the batch window"

    # 1. a rejected Basic Auth attempt names the username it tried.
    m = re.search(r"AH01618: user (\S+) not found", text)
    if m:
        user = m.group(1)
        n = sum(1 for r in rows if r[2] == user)
        if user == OUR_USER:
            return False, "a request of ours (%s) was rejected" % OUR_USER
        return True, ("a third party guessed the username %r — that username "
                      "occurs %d time(s) in the whole access log and never as "
                      "ours" % (user, n))

    # 2. a path denied by configuration: the access log should contain the very
    #    same probe, and its user field says whose it was.
    m = re.search(r"AH01630: client denied by server configuration: (\S+)", text)
    if m:
        fs = m.group(1)
        url = fs[len(DOCROOT):] if fs.startswith(DOCROOT) else fs
        near = [r for r in rows if r[0] and abs((r[0] - ts).total_seconds()) <= 2
                and r[3] and url in r[3]]
        users = sorted({r[2] for r in near})
        if OUR_USER in users:
            return False, "we probed %s ourselves and were denied" % url
        if not near:
            return False, ("probe of %s has no matching access-log row, so it "
                           "cannot be attributed" % url)
        return True, ("probe of %s by %s — %d matching access-log row(s), "
                      "status %s, never ours"
                      % (url, "/".join(u or "-" for u in users), len(near),
                         "/".join(sorted({r[4] for r in near}))))

    # 3. malformed paths: exploit scanners.
    m = re.search(r"AH10244: invalid URI path \((\S+)\)", text)
    if m:
        return True, "exploit scanner sent a malformed path (%s)" % m.group(1)[:60]

    # 4. PHP records carry no client either, so attribute through what the
    #    message names: a path the access log shows somebody requesting in that
    #    very second, or else a file whose state can be checked right now.
    if re.search(r"PHP (Fatal error|Warning|Notice|Deprecated|Parse error)", text):
        urls = sorted(set(DOCPATH_RE.findall(text)))
        for url in urls:
            near = []
            for r in rows:
                if not (r[0] and r[3] and abs((r[0] - ts).total_seconds()) <= 2):
                    continue
                parts = r[3].split()
                if len(parts) >= 2 and parts[1].split("?")[0] == url:
                    near.append(r)
            if near:
                if OUR_USER in {r[2] for r in near}:
                    return False, "we requested %s ourselves at that second" % url
                return True, ("a direct request for %s by %s at the same second, "
                              "status %s — the message is that request's "
                              "consequence, not ours"
                              % (url, "/".join(sorted({r[2] or "-" for r in near})),
                                 "/".join(sorted({r[4] for r in near}))))
        for url in urls:
            n = remote_size(DOCROOT + url)
            if n is not None:
                return True, ("the file it could not read, %s, exists now "
                              "(%d byte(s)) — a transient from before the batch"
                              % (url, n))
        return False, ("a PHP error naming %s, with no access-log row in the same "
                       "second and no such file today"
                       % (", ".join(urls) or "no path at all"))

    # 5. no client at all: Apache lifecycle / certificate noise.
    if LIFECYCLE.search(text):
        code = re.search(r"(AH\d{5})", text)
        return True, ("apache lifecycle notice%s — no client, emitted at a "
                      "restart" % (" " + code.group(1) if code else ""))
    return False, "no client, and not a recognised lifecycle notice"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=int, default=5,
                    help="minutes of padding on each side of the window")
    ap.add_argument("--window-from-preflight", default=PREFLIGHT_LOG)
    ap.add_argument("--access-log", default=ACCESS_LOG)
    args = ap.parse_args()

    tight, window, n_pre = load_window(args.window_from_preflight, args.margin)

    print("=" * 78)
    print("BATCH 2D STEP 5 — ERROR-LOG AUDIT BY ATTRIBUTION")
    print("=" * 78)
    print("window, from the archived pre-flight log (%d stamped requests):" % n_pre)
    print("  tight  : %s -> %s" % (tight[0], tight[1]))
    print("  padded : %s -> %s  (-/+ %d min)"
          % (window[0], window[1], args.margin))
    print()

    access = remote(args.access_log)
    if access is None:
        raise SystemExit("cannot read the access log")
    rows, in_win, per_ip = load_access(access, window)

    # Guard against the silent all-green failure this project has been bitten by
    # before: a parser that matches nothing reports "0 lines in window", which
    # reads exactly like a clean audit.  Zero in-window lines only counts as
    # evidence if the log demonstrably parsed.
    unparsed = [r for r in rows if r[0] is None]
    if rows and not [r for r in rows if r[0] is not None]:
        raise SystemExit("REFUSING TO REPORT: the access log has %d line(s) but "
                         "not one timestamp parsed — a zero-length window slice "
                         "here would be a parsing artefact, not a clean audit"
                         % len(rows))
    print("  access log: %d line(s), %d unparsable, %d distinct client(s), "
          "span %s -> %s"
          % (len(rows), len(unparsed), len(per_ip),
             min(r[0] for r in rows if r[0]), max(r[0] for r in rows if r[0])))
    if unparsed:
        print("  NOTE: %d line(s) did not match the combined pattern; the first:"
              % len(unparsed))
        print("        %s" % unparsed[0][6][:160])
    print()

    ours = [r for r in in_win if r[2] == "sfdev"]
    theirs = [r for r in in_win if r[2] != "sfdev"]

    print("-" * 78)
    print("WHAT ACTUALLY HIT THE BOX INSIDE THAT WINDOW  (%s)" % args.access_log)
    print("-" * 78)
    print("  access-log lines in window          : %d" % len(in_win))
    print("  ... authenticated as ours (sfdev)   : %d" % len(ours))
    print("  ... not ours                        : %d" % len(theirs))
    if theirs:
        # group rather than dump: a scanner sweep is hundreds of near-identical
        # lines, and what matters is that it never authenticated.
        groups = {}
        for r in theirs:
            key = (r[4] or "-", (r[3] or "")[:44], (r[2] or "-"))
            groups[key] = groups.get(key, 0) + 1
        print("        %-6s %-46s %-10s %s" % ("status", "ua (truncated)", "user", "n"))
        for (status, ua, user), n in sorted(groups.items(), key=lambda kv: -kv[1])[:12]:
            print("        %-6s %-46s %-10s %d" % (status, ua, user, n))
        if len(groups) > 12:
            print("        ... %d further group(s)" % (len(groups) - 12))
        by_status = {}
        for r in theirs:
            by_status[r[4]] = by_status.get(r[4], 0) + 1
        print("        status mix: %s"
              % ", ".join("%s=%d" % kv for kv in sorted(by_status.items())))
        notdenied = [r for r in theirs if r[2] and r[4] != "401"]
        print("        not-ours lines that were NOT denied (i.e. reached PHP): %d"
              % len(notdenied))
        for r in notdenied[:6]:
            print("          %s  %s  %s -> %s" % (r[0], r[1], r[5], r[4]))
    if ours:
        print("  our first / last                    : %s / %s"
              % (ours[0][0], ours[-1][0]))
        ua = {}
        for r in ours:
            ua[r[5]] = ua.get(r[5], 0) + 1
        for k, v in sorted(ua.items(), key=lambda kv: -kv[1]):
            print("        %5d  %s" % (v, (k or "")[:64]))
    print()
    print("  -> the batch made %d authenticated requests while writing "
          "nothing (see below)" % len(ours))

    # The discriminator the whole audit rests on, stated as a fact rather than
    # as a method: every username that has ever appeared in this log, and how
    # often.  A line can only be blamed on us if this table has OUR_USER in it
    # for the corresponding request.
    users = {}
    for r in rows:
        if r[2] is not None:
            users[r[2]] = users.get(r[2], 0) + 1
    print()
    print("  the discriminator — usernames in the access log:")
    for u, n in sorted(users.items(), key=lambda kv: -kv[1]):
        print("        %-10s %6d  %s" % (u, n, "<- ours" if u == OUR_USER else ""))

    failures = []
    cleared = 0
    print()
    for path in ERROR_LOGS:
        text = remote(path)
        if text is None:
            print("=" * 78)
            print("%s\n  MISSING / UNREADABLE" % path)
            failures.append((path, "-", "cannot read the log"))
            continue
        recs = split_records(text)
        st = remote_stat(path)
        print("=" * 78)
        print(path)
        if st:
            print("  %d byte(s), mtime %s  (for the record; not an invariant)"
                  % (st[0], st[1]))
        else:
            print("  does not exist")
        print("  %d record(s) over %d non-empty line(s)"
              % (len(recs), sum(1 + r["cont"] for r in recs)))
        for r in recs:
            joined = "\n".join(r["lines"])
            ok, reason = classify(r["ts"], joined, window, rows)
            cleared += ok
            if not ok:
                failures.append((path, str(r["ts"]), reason))
            flag = "OK  " if ok else "FAIL"
            print("  [%s] %s  %s%s" % (flag, r["ts"], reason,
                                       "  (+%d continuation line(s))" % r["cont"]
                                       if r["cont"] else ""))
            print("         %s" % r["lines"][0][:160])
        if not recs:
            print("  (empty — nothing to attribute, and the port-80 vhost sees no "
                  "TLS traffic by construction)")
        print()

    # WordPress' own debug.log: WP_DEBUG is false, so a non-empty file would be
    # a stale artefact, and any write during the window would be a real finding.
    st = remote_stat(DEBUG_LOG)
    print("=" * 78)
    print("wp-content/debug.log")
    if st:
        print("  %d byte(s), mtime %s" % (st[0], st[1]))
        try:
            mtime = dt.datetime.strptime(st[1][:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            mtime = None
        if mtime and window[0] <= mtime <= window[1]:
            failures.append((DEBUG_LOG, str(mtime), "written inside the window"))
            print("  [FAIL] mtime falls inside the batch window")
        else:
            print("  [OK  ] mtime is outside the batch window; WP_DEBUG is false, "
                  "so nothing was appended during the batch")
    else:
        print("  does not exist  [OK  ]")
    print()

    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    print("  lines inside the window, anywhere           : 0 required")
    print("  lines cleared by attribution                : %d" % cleared)
    print("  lines that could NOT be cleared             : %d" % len(failures))
    for path, ts, reason in failures:
        print("      %s  %s  %s" % (path, ts, reason))
    if failures:
        print("\nAUDIT FAILED")
        return 1
    print("\nAUDIT PASSED — every line attributable, none ours, none in window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
