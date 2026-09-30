#!/usr/bin/env python3
"""Batch H18 — capture the gallery section of every formula page.

Used twice around the deploy: once on the pre-change dev tree (baseline) and
once after the pull (candidate). Zero drift means the two maps are equal for
every record whose three new slots are empty — which, on the day of the
deploy, is every record.

The section is matched with `<section id="gallery" ...>...</section>`, not a
greedy div run: the first cut matched `</div></div></div>` and swallowed the
whole rest of the page (125436B page -> 37522B "section").

Usage:  h18_capture.py <out.json> [base_url]
"""
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def slugs() -> list:
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", SERVER,
         f"cd {WP_ROOT} && wp post list --post_type=sf_formula --post_status=publish "
         "--field=post_name --orderby=ID --order=ASC --allow-root"],
        capture_output=True, text=True, timeout=120).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def fetch(url: str) -> str:
    import base64
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASS}".encode()).decode(),
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def gallery_segment(html: str) -> str:
    m = re.search(r'<section id="gallery"[\s\S]*?</section>', html)
    return m.group(0) if m else ""


def frame_names(seg: str) -> list:
    out = []
    for tag in re.findall(r"<img[^>]*>", seg):
        src = re.search(r'\ssrc="([^"]*)"', tag)
        if src:
            out.append(src.group(1).split("/")[-1])
    return out


def main():
    out_path = Path(sys.argv[1])
    base = sys.argv[2] if len(sys.argv) > 2 else "https://dev.zxpet.com"
    data = {}
    for s in slugs():
        seg = gallery_segment(fetch(f"{base}/formulas/{s}/"))
        data[s] = {
            "bytes": len(seg),
            "md5": hashlib.md5(seg.encode()).hexdigest() if seg else "",
            "frames": frame_names(seg),
        }
        print(f"{s:34s} bytes={data[s]['bytes']:6d} md5={data[s]['md5'][:16]} n={len(data[s]['frames'])}")
    out_path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {out_path} ({len(data)} records)")


if __name__ == "__main__":
    main()
