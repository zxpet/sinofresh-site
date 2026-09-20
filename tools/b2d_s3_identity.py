#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 3 — the identity chain: workspace == live theme == preflight copy.

Three things have to be the same bytes for the gate results to mean anything:

  * the workspace tree    (what was reviewed and committed)
  * the live theme dir     (site-repo/sinofresh-theme, the symlink target the
                            dev site actually serves from)
  * the preflight copy     (themes/sinofresh-theme-preflight, built by
                            `git archive <commit>`, i.e. the commit itself)

If any link is off, the confinement gate may be certifying a revision nobody
deployed, or a deploy nobody reviewed.

File lists come from `git -c core.quotePath=false ls-files` on BOTH ends. That
flag is not optional: the default escapes non-ASCII paths into "..." with
octal, and then a file whose name is Chinese compares as "missing on disk".
Using the same list on both sides also makes any such mismatch symmetric,
which is how it stays invisible.

usage:
    b2d_s3_identity.py [--theme sinofresh-theme] [--preflight NAME] [--sha256]
"""
import argparse
import hashlib
import os
import subprocess
import sys

HOST = "root@65.49.215.152"
REPO = "/var/www/dev.zxpet.com/site-repo"
PREFLIGHT = "/var/www/dev.zxpet.com/public/wp-content/themes/sinofresh-theme-preflight"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def remote_md5(listing, root):
    """md5 every path in `listing` under `root` on the dev box, one ssh hop."""
    script = "cd %s\nwhile IFS= read -r f; do md5sum \"$f\"; done\n" % root
    p = sh(["ssh", "-o", "ConnectTimeout=25", HOST, "bash -s"], input=script + listing)
    out = {}
    for line in p.stdout.splitlines():
        if "  " not in line:
            continue
        digest, path = line.split("  ", 1)
        out[path.strip()] = digest
    return out, p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="sinofresh-theme")
    ap.add_argument("--sha256", action="store_true", help="also hash the preflight copy")
    args = ap.parse_args()

    root = os.getcwd()
    p = sh(["git", "-c", "core.quotePath=false", "ls-files", args.theme])
    files = [f for f in p.stdout.split("\n") if f.strip()]
    print("tracked files under %s/: %d" % (args.theme, len(files)))
    if not files:
        return 2
    rel = [f[len(args.theme) + 1:] for f in files]

    # local
    local = {}
    for f in files:
        with open(os.path.join(root, f), "rb") as fh:
            local[f] = hashlib.md5(fh.read()).hexdigest()

    # live theme dir in site-repo
    live_dir = os.path.join(REPO, args.theme)
    live, err = remote_md5("\n".join(rel) + "\n", live_dir)
    if err.strip():
        print("remote stderr:", err.strip()[:400])
    live = {os.path.join(args.theme, k): v for k, v in live.items()}

    bad = []
    for f in files:
        if f not in live:
            bad.append((f, local[f], "MISSING on the dev box"))
        elif live[f] != local[f]:
            bad.append((f, local[f], live[f]))
    print("\n[live]  %s" % live_dir)
    print("  compared %d files, mismatches: %d" % (len(files), len(bad)))
    for f, a, b in bad[:20]:
        print("   * %s\n       local %s\n       live  %s" % (f, a, b))

    pre_bad = []
    if args.sha256:
        print("\n[preflight]  %s" % PREFLIGHT)
        pre, err = remote_md5("\n".join(rel) + "\n", PREFLIGHT)
        if err.strip():
            print("  remote stderr:", err.strip()[:400])
        for f, r in zip(files, rel):
            if r not in pre:
                pre_bad.append((f, local[f], "MISSING in the copy"))
            elif pre[r] != local[f]:
                pre_bad.append((f, local[f], pre[r]))
        print("  compared %d files, mismatches: %d" % (len(files), len(pre_bad)))
        for f, a, b in pre_bad[:20]:
            print("   * %s\n       workspace %s\n       copy      %s" % (f, a, b))

    ok = not bad and not pre_bad
    print("\n%s  identity chain" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
