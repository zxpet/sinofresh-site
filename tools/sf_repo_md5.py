#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Whole-repository md5 comparison: the workspace tree against the dev box.

The theme-scoped identity chain (b2d_s3_identity.py) answers "are the bytes that
were reviewed the bytes that are served". This answers the wider question the
batch reports have been stating by hand: every tracked file in the repository,
not just the theme, is the same on both ends.

Two traps this file exists to avoid, both of which produce a confident
"0 differences" that means nothing:

  * `git ls-files` escapes non-ASCII paths into "..." with octal by default
    (core.quotePath). Feed that list to a remote `md5sum` and every Chinese
    filename comes back "missing" — or, if the same broken list is used on both
    sides, comes back missing on both and cancels out. The list is built with
    `-c core.quotePath=false` here, and the non-ASCII paths are then counted and
    each one is checked to be present AND matched on both sides. "0 differences"
    is only reported as a pass alongside that count.

  * sorting on both ends and diffing them. macOS and Linux do not collate
    identically, which manufactures a page of ordering differences that look
    like content differences. The remote side returns raw `md5sum` output and
    all matching happens locally, in a dict.

    python3 tools/sf_repo_md5.py [--exclude PATH]... [--root DIR] [--json F]

A report that is written INSIDE the repository cannot be part of the set it
reports on. The content of such a file depends on the hashes it contains,
including its own — there is no stable value for it to settle on, and a run that
writes the report before hashing will hash a half-written file. Both were
observed: capturing the output with a shell redirect into a tracked path made
the tool report one mismatch, against the file it was writing. Pass the report
path to --exclude and the set becomes stable and reproducible.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HOST = "root@65.49.215.152"
REPO = "/var/www/dev.zxpet.com/site-repo"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--root", default=REPO, help="repository root on the dev box")
    ap.add_argument("--exclude", action="append", default=[],
                    help="tracked path to leave out of the comparison on BOTH "
                         "sides (repeatable) — required for the report itself")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    p = sh(["git", "-c", "core.quotePath=false", "ls-files", "-z"])
    tracked = [f for f in p.stdout.split("\0") if f]
    if not tracked:
        print("no tracked files — refusing to report a comparison of nothing")
        return 2

    unmatched = [e for e in args.exclude if e not in tracked]
    if unmatched:
        print("--exclude path(s) not tracked, so the exclusion would silently "
              "shrink nothing: %s" % ", ".join(unmatched))
        return 2
    files = [f for f in tracked if f not in args.exclude]

    weird = [f for f in files if "\n" in f]
    if weird:
        print("paths containing newlines cannot travel over this channel: %d" % len(weird))
        return 2

    local = {}
    missing_local = []
    for f in files:
        try:
            with open(f, "rb") as fh:
                local[f] = hashlib.md5(fh.read()).hexdigest()
        except OSError:
            missing_local.append(f)

    listing = "\n".join(files) + "\n"
    script = "cd %s\nwhile IFS= read -r f; do md5sum \"$f\"; done\n" % args.root
    r = sh(["ssh", "-o", "ConnectTimeout=25", args.host, "bash -s"], input=script + listing)
    remote = {}
    for line in r.stdout.splitlines():
        if "  " not in line:
            continue
        digest, path = line.split("  ", 1)
        remote[path.strip()] = digest

    nonascii = [f for f in files if not f.isascii()]
    bad = [f for f in files if f in local and remote.get(f) != local[f]]

    print("tracked files            : %d" % len(tracked))
    if args.exclude:
        print("excluded (both sides)    : %d  (%s)"
              % (len(args.exclude), ", ".join(args.exclude)))
    print("compared                 : %d" % len(files))
    print("hashed locally           : %d  (unreadable: %d)" % (len(local), len(missing_local)))
    print("hashed on the dev box    : %d" % len(remote))
    print("non-ASCII paths          : %d" % len(nonascii))
    for f in nonascii:
        state = "matched" if f in local and remote.get(f) == local[f] else "NOT MATCHED"
        print("   %-52s %s" % (f, state))
    print("mismatches               : %d" % len(bad))
    for f in bad[:20]:
        print("   * %s\n       local %s\n       live  %s" % (f, local.get(f), remote.get(f)))
    if len(local) != len(files) or len(remote) != len(files):
        print("\nFAIL — the two sides did not resolve the same number of files, so a "
              "'0 differences' result would be an artefact of parsing, not a pass")
        return 1
    ok = not bad and not missing_local and not r.stderr.strip()
    print("\n%s  %d files, %d mismatches" % ("PASS" if ok else "FAIL", len(files), len(bad)))
    if r.stderr.strip():
        print("remote stderr: %s" % r.stderr.strip()[:300])

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"files": len(files), "nonascii": len(nonascii),
                       "mismatches": bad, "stderr": r.stderr.strip()}, fh, indent=2)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
