#!/usr/bin/env python3
"""Fetch the 75 gated pages of dev.zxpet.com into a directory, one file per path.

Why a tool and not a shell loop: the site is behind Basic Auth, so a request
without credentials returns the same 401 page for every path — two runs would
then hash identical bytes and report "all green" while nothing was fetched.
This tool records the HTTP code next to every file, so that failure mode shows
up as 75 x 401 instead of silence.

Driving it from Python matters too: a zsh loop with command substitution drifts
between iterations (the browser/eval target silently changes), and 75 sequential
requests exceed the foreground timeout. Threads keep the order deterministic
while still finishing in one pass.

usage:
    b2d_s3_fetch.py --out DIR [--paths FILE] [--workers 8] [--header 'X-SF-Preflight: 1']

Credentials come from $SF_DEV_AUTH, falling back to the dev pair.

--header exists for the pre-flight gate. Pushing a commit is enough to arm it —
`git fetch` brings the objects without moving the working tree, so the live
theme keeps serving the old bytes while `git archive <sha>` builds the copy —
which means the candidate can be captured, gated and rejected without the dev
site ever having served it. The header used is recorded in MANIFEST.tsv: which
theme directory a capture came from is not visible in the bytes, and a
"preflight" capture that was really a live one would pass the same gates while
proving nothing.
"""
import argparse
import concurrent.futures
import hashlib
import os
import subprocess
import sys

DEFAULT_AUTH = "sfdev:VkEws18Kl5V1qp3TpZ6s"
HOST = "https://dev.zxpet.com"


def slug_for(path):
    """'/products/soft-chews/' -> 'products__soft-chews'. '/' -> 'root'."""
    s = path.strip("/").replace("/", "__")
    return s if s else "root"


def fetch(path, out_dir, auth, header=None):
    dest = os.path.join(out_dir, slug_for(path) + ".html")
    cmd = ["curl", "-s", "--max-time", "45", "-u", auth, "-o", dest, "-w", "%{http_code}"]
    if header:
        cmd[1:1] = ["-H", header]
    cmd.append(HOST + path)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    code = (proc.stdout or "").strip() or "000"
    body = b""
    if os.path.exists(dest):
        with open(dest, "rb") as fh:
            body = fh.read()
    return path, code, len(body), hashlib.sha256(body).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--paths", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "b2d_s3_paths.txt"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--header", default=None,
                    help="extra request header, e.g. 'X-SF-Preflight: 1'")
    args = ap.parse_args()

    auth = os.environ.get("SF_DEV_AUTH") or DEFAULT_AUTH
    with open(args.paths, encoding="utf-8") as fh:
        paths = [p.strip() for p in fh if p.strip()]

    os.makedirs(args.out, exist_ok=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(lambda p: fetch(p, args.out, auth, args.header), paths):
            rows.append(row)

    codes = {}
    for _, code, _, _ in rows:
        codes[code] = codes.get(code, 0) + 1
    print("fetched %d paths, http codes: %s" % (len(rows), codes))
    if args.header:
        print("request header: %s" % args.header)
    bad = [r for r in rows if r[1] != "200"]
    for path, code, size, _ in bad:
        print("  BAD %s %s (%d bytes)" % (code, path, size))

    with open(os.path.join(args.out, "MANIFEST.tsv"), "w", encoding="utf-8") as fh:
        fh.write("# header: %s\n" % (args.header or "(none — live render)"))
        fh.write("path\tcode\tbytes\tsha256\n")
        for path, code, size, digest in rows:
            fh.write("%s\t%s\t%d\t%s\n" % (path, code, size, digest))
    print("MANIFEST.tsv written to %s" % args.out)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
