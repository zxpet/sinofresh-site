#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 6 — screenshots of the LIVE site after the pull.

    python3 tools/b2c_s2s6_live_shots.py [--shots DIR]

No gate header anywhere: this is the shipped theme. Captures the first usable
state of /formulas/, the filter after a real click, the mobile rail, a dosage
page carrying the new entry link, and the Products dropdown with the item that
was added in the Site Editor.
"""

import argparse
import os
import subprocess
import sys

BASE = "https://dev.zxpet.com"
SESSION = "sfs6live"


def run(*args, timeout=240):
    out = subprocess.run(["agent-browser", *args, "--session", SESSION],
                         capture_output=True, text=True, timeout=timeout)
    return out.stdout.strip(), out.stderr.strip()


def shot(path):
    run("screenshot", path)
    ok = os.path.exists(path) and os.path.getsize(path) > 1000
    print(f"  [{'PASS' if ok else 'FAIL'}] {os.path.basename(path)} "
          f"({os.path.getsize(path) if os.path.exists(path) else 0} B)")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sinofresh-theme", "screenshots", "batch2c-step2-formulas-live"))
    args = ap.parse_args()
    os.makedirs(args.shots, exist_ok=True)
    ok = []

    try:
        run("open", f"{BASE}/formulas/")
        run("wait", "--load", "networkidle")
        run("set", "viewport", "1440", "900")
        run("open", f"{BASE}/formulas/")
        run("wait", "--load", "networkidle")
        ok.append(shot(os.path.join(args.shots, "01-live-desktop-formulas.png")))

        run("click", '.sf-fchip[data-sf-form="soft-chews"]')
        ok.append(shot(os.path.join(args.shots, "02-live-desktop-filtered-soft-chews.png")))

        run("set", "viewport", "375", "812")
        run("open", f"{BASE}/formulas/")
        run("wait", "--load", "networkidle")
        run("eval", "window.scrollTo(0, document.querySelector('.sf-fchips-wrap').getBoundingClientRect().top + window.scrollY - 120)")
        ok.append(shot(os.path.join(args.shots, "03-live-mobile375-chips-rail.png")))

        run("set", "viewport", "1440", "900")
        run("open", f"{BASE}/products/soft-chews/")
        run("wait", "--load", "networkidle")
        run("eval", "document.querySelector('section#formulas .sf-explore__btn[href=\"/formulas/\"]')"
                    ".scrollIntoView({block:'center'})")
        ok.append(shot(os.path.join(args.shots, "04-live-desktop-dosage-entry-link.png")))

        run("eval", "window.scrollTo(0,0)")
        run("eval", "document.querySelector('.wp-block-navigation-submenu__toggle,"
                    " .wp-block-navigation-submenu > a,"
                    " .wp-block-navigation-submenu > button')?.click()")
        ok.append(shot(os.path.join(args.shots, "05-live-nav-products-dropdown.png")))
    finally:
        run("close", "--all")

    print(f"\n{'PASS' if all(ok) else 'FAIL'}  {sum(ok)}/{len(ok)} screenshots")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
