#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step 3 — remove the Step-2 gallery band from the eight dosage pages.

The Step-2 band is a pure insertion (git says +10 / -0 on every page), so the
strongest possible proof of removal is not a mask or a screenshot: it is
`git diff cfbd5e4 -- templates/page-*.html` being EMPTY. This tool does the
byte surgery and then asserts exactly that, by comparing the rewritten file
against `git show cfbd5e4:<path>` rather than trusting its own arithmetic.

The bytes removed are the ones Step 2 inserted, taken from that tool's own
builder (`b2d_s2_apply.build`) so the two can never drift apart:

    LEAD_IN + build(slug)   ->   LEAD_IN

where LEAD_IN is the hero group's close plus one blank line. Deleting the
block therefore reproduces the pre-Step-2 bytes including the whitespace
junction, which is the part that is easy to get wrong by hand.

Usage:
    python3 tools/b2d_s3_revert.py --check     # dry run
    python3 tools/b2d_s3_revert.py --apply     # rewrites the eight files
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from b2d_s2_apply import LEAD_IN, SLUGS, build, template_path  # noqa: E402

ROOT = os.path.dirname(HERE)
BASELINE = "cfbd5e4"


def baseline_bytes(slug):
    """The pre-Step-2 file straight out of git — the oracle, not a copy."""
    rel = "sinofresh-theme/templates/page-%s.html" % slug
    p = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (BASELINE, rel)],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit("git show failed for %s: %s" % (rel, p.stderr.decode()))
    return p.stdout


def main(apply):
    ok = True
    for slug in SLUGS:
        path = template_path(slug)
        with open(path, "rb") as fh:
            cur = fh.read()

        needle = LEAD_IN.encode() + build(slug).encode()
        hits = cur.count(needle)
        if hits != 1:
            print("FAIL %-14s band occurs %d times, expected 1" % (slug, hits))
            ok = False
            continue

        new = cur.replace(needle, LEAD_IN.encode(), 1)
        delta = len(cur) - len(new)

        base = baseline_bytes(slug)
        same = (new == base)
        print("%-14s removed=%4d B   bytes==%s %s" % (
            slug, delta, BASELINE, "YES" if same else "NO <<<"))
        if not same:
            ok = False
            # show where they first differ, to make the failure actionable
            n = min(len(new), len(base))
            i = next((k for k in range(n) if new[k] != base[k]), n)
            print("    first difference at byte %d" % i)
            print("    new : %r" % new[max(0, i - 40):i + 40])
            print("    base: %r" % base[max(0, i - 40):i + 40])
            continue

        if apply:
            with open(path, "wb") as fh:
                fh.write(new)

    print("\n%s" % ("PASS  all eight pages return to %s byte for byte" % BASELINE
                    if ok else "FAIL  see above"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if cmd not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    sys.exit(main(cmd == "--apply"))
