#!/usr/bin/env python3
"""Viewport-sized review shots of the /formulas/ bar (pre-flight theme).

The full-page captures document the whole page; these close-ups are for
judging the filter bar and the first card row at real size, with the cookie
banner dismissed so it does not sit across the cards.
"""

import os
import subprocess
import sys

URL = "https://dev.zxpet.com/formulas/"
HEADERS = '{"X-SF-Preflight":"1"}'
SESSION = "sfshot"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "b2c-step2-shots")


def run(*args):
    return subprocess.run(["agent-browser", *args, "--session", SESSION],
                          capture_output=True, text=True).stdout.strip()


def dismiss_cookie():
    run("find", "text", "Accept All", "click")


def main():
    os.makedirs(OUT, exist_ok=True)
    run("open", URL, "--headers", HEADERS)
    run("wait", "--load", "networkidle")
    run("set", "viewport", "1440", "900")
    run("open", URL)
    run("wait", "--load", "networkidle")
    dismiss_cookie()
    run("screenshot", os.path.join(OUT, "review-desktop-viewport.png"))
    run("click", '.sf-fchip[data-sf-form="soft-chews"]')
    run("screenshot", os.path.join(OUT, "review-desktop-filtered-viewport.png"))
    run("click", '.sf-fchip[data-sf-form="all"]')

    run("set", "viewport", "375", "812")
    run("open", URL)
    run("wait", "--load", "networkidle")
    dismiss_cookie()
    run("eval", "document.querySelector('.sf-fchips').scrollIntoView({block:'center'}); 'ok'")
    run("screenshot", os.path.join(OUT, "review-mobile-chips.png"))
    run("click", '.sf-fchip[data-sf-form="dental-chews"]')
    run("eval", "document.querySelector('.sf-fgrid').scrollIntoView({block:'center'}); 'ok'")
    run("screenshot", os.path.join(OUT, "review-mobile-filtered.png"))
    run("close")
    print("shots written to", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
