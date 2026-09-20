#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step4 — before/after screenshots for the archive-breadcrumb prefix.

    python3 tools/b2c_s4_breadcrumb_shots.py [--shots DIR]

Two separate browser sessions on purpose:

  * `s4gate`  carries X-SF-Preflight: 1 -> renders the *preflight* copy, i.e.
              the fixed theme that is not deployed yet ("after").
  * `s4live`  carries no header -> renders the shipped theme ("before").

Order is deliberate: every gated visit happens before any ungated one. Cloudflare
keys its HTML cache by URL, so an ungated request must never run first (it would
leave a cached origin body behind that the gated request could then be served).

Each navigation carries its own unique ?sfcap= so the edge always hits the origin.
"""
import argparse
import os
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
GATED, LIVE = "s4gate", "s4live"


def run(session, *args, timeout=240):
    out = subprocess.run(["agent-browser", *args, "--session", session],
                         capture_output=True, text=True, timeout=timeout)
    return out.stdout.strip(), out.stderr.strip()


def shot(session, path):
    run(session, "screenshot", path)
    ok = os.path.exists(path) and os.path.getsize(path) > 1000
    print(f"  [{'PASS' if ok else 'FAIL'}] {os.path.basename(path)} "
          f"({os.path.getsize(path) if os.path.exists(path) else 0} B)")
    return ok


def buzz():
    return f"?sfcap=s{int(time.time() * 1000)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sinofresh-theme", "screenshots", "batch2c-step4-breadcrumb"))
    args = ap.parse_args()
    os.makedirs(args.shots, exist_ok=True)

    def out(name):
        return os.path.join(args.shots, name)

    ok = []
    try:
        # ---- session 1: gated ("after") -------------------------------------
        run(GATED, "open", BASE)
        run(GATED, "set", "headers", '{"X-SF-Preflight": "1"}')

        run(GATED, "set", "viewport", "1440", "900")
        run(GATED, "open", f"{BASE}/zh/formulas/{buzz()}")
        run(GATED, "wait", "--load", "load")
        run(GATED, "eval", "window.scrollTo(0,0)")
        ok.append(shot(GATED, out("02-after-zh-desktop-formulas.png")))

        run(GATED, "open", f"{BASE}/formulas/{buzz()}")
        run(GATED, "wait", "--load", "load")
        run(GATED, "eval", "window.scrollTo(0,0)")
        ok.append(shot(GATED, out("04-after-en-desktop-formulas.png")))

        run(GATED, "set", "viewport", "375", "812")
        run(GATED, "open", f"{BASE}/zh/formulas/{buzz()}")
        run(GATED, "wait", "--load", "load")
        run(GATED, "eval", "window.scrollTo(0,0)")
        ok.append(shot(GATED, out("06-after-zh-mobile375.png")))

        # ---- session 2: ungated ("before", still the shipped theme) ---------
        run(LIVE, "open", BASE)
        run(LIVE, "set", "viewport", "1440", "900")
        run(LIVE, "open", f"{BASE}/zh/formulas/{buzz()}")
        run(LIVE, "wait", "--load", "load")
        run(LIVE, "eval", "window.scrollTo(0,0)")
        ok.append(shot(LIVE, out("01-before-zh-desktop-formulas.png")))

        run(LIVE, "open", f"{BASE}/formulas/{buzz()}")
        run(LIVE, "wait", "--load", "load")
        run(LIVE, "eval", "window.scrollTo(0,0)")
        ok.append(shot(LIVE, out("03-before-en-desktop-formulas.png")))

        run(LIVE, "set", "viewport", "375", "812")
        run(LIVE, "open", f"{BASE}/zh/formulas/{buzz()}")
        run(LIVE, "wait", "--load", "load")
        run(LIVE, "eval", "window.scrollTo(0,0)")
        ok.append(shot(LIVE, out("05-before-zh-mobile375.png")))
    finally:
        for s in (GATED, LIVE):
            try:
                run(s, "close", "--all")
            except Exception:
                pass

    print(f"\n{'PASS' if all(ok) else 'FAIL'}  {sum(ok)}/{len(ok)} screenshots")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
