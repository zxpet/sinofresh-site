#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 1 — pre-flight scaffold on the dev box (install / remove).

The pre-flight contract this project settled on, and the reason each piece
exists:

  * the theme under test is installed as its OWN theme directory
    (wp-content/themes/sinofresh-theme-preflight/), so enqueued asset URLs
    resolve to the copy's style.css and JS. A `theme_root` filter alone is
    enough to verify PHP, but it leaves every asset pointing at the live
    theme — a CSS/JS change would then be "verified" against the live bytes.
  * the switch is a request header (X-SF-Preflight: 1), not a query
    parameter, so nothing is echoed into the page and compared.
  * the copy comes from `git -C <repo> archive <commit> sinofresh-theme`
    piped into tar, i.e. it is exactly the commit, with no working-tree
    state and no .git.
  * teardown removes the copy, the mu-plugin and the diagnostic log, then
    the caller re-reads the live baseline to prove nothing leaked.

    python3 tools/b2d_s1_preflight.py install <commit>
    python3 tools/b2d_s1_preflight.py remove
    python3 tools/b2d_s1_preflight.py status

NOTE — pass the FULL 40-character sha. Measured 2026-09-21 on the dev box:
`git rev-parse HEAD` and `git cat-file -t HEAD` work, but the same repo refuses
an abbreviated sha ("fatal: Not a valid object name dcfc4d3") even though the
object is present and packed. An install with the 7-char form therefore fails
with a git error that looks like the commit is missing, and the tar step then
reports "This does not look like a tar archive" — a misleading pair of
messages for what is only a short-sha lookup failure. `git log --oneline`
still prints the short form, so it is easy to paste it back in by mistake.
"""

import os
import shlex
import subprocess
import sys

HOST = "root@65.49.215.152"
PUB = "/var/www/dev.zxpet.com/public"
REPO = "/var/www/dev.zxpet.com/site-repo"
PRE = PUB + "/wp-content/themes/sinofresh-theme-preflight"
MU = PUB + "/wp-content/mu-plugins/zz-sf-preflight.php"
MULOG = PUB + "/wp-content/mu-plugins/zz-sf-preflight.log"
HERE = os.path.dirname(os.path.abspath(__file__))
MU_SRC = os.path.join(HERE, "b2d_s1_preflight_mu.php")


def ssh(script, check=True):
    """Run a shell script on the dev box with `bash -s` (stdin)."""
    p = subprocess.run(["ssh", "-o", "ConnectTimeout=25", HOST, "bash -s"],
                       input=script, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, end="", file=sys.stderr)
    if check and p.returncode != 0:
        raise SystemExit("remote command failed (%d)" % p.returncode)
    return p.returncode


def install(commit):
    assert commit and len(commit) >= 7, "need a commit-ish"
    if len(commit) < 40:
        # Not pedantry: abbreviated lookups fail on this box (see the module
        # docstring), and the failure surfaces as a tar error three steps later.
        raise SystemExit("pass the full 40-char sha; abbreviated lookups fail on "
                         "the dev box (got %r)" % commit)
    if not os.path.exists(MU_SRC):
        raise SystemExit("missing %s" % MU_SRC)
    # 1. upload the gate (scp, so the file's bytes are the repo's bytes)
    subprocess.run(["scp", "-q", MU_SRC, HOST + ":" + MU + ".tmp"], check=True)
    # 2. build the copy theme from the commit and arm the gate
    #
    # The commit check MUST be an `if ! …; then exit; fi`, not `check && echo`.
    # Measured 2026-09-22, and it cost the pre-flight copy: under `set -e` a
    # failing left operand of `&&` does NOT stop the script (the exception is
    # exactly "a command in a && list that is not the last one"), so the script
    # sailed past the failed `git cat-file -e`, ran `rm -rf {PRE}`, and then
    # died on the empty tar — leaving the theme directory present but EMPTY.
    # The site then 301s every sf_formula URL to the home page, because the CPT
    # the theme registers no longer exists. Distinguishing "install failed" from
    # "install succeeded and emptied the copy" is the whole point of this guard.
    ssh(f"""set -euo pipefail
if ! git -C {REPO} cat-file -e {shlex.quote(commit)}^{{commit}} 2>/dev/null; then
  echo "FATAL: commit {commit} is not in {REPO} — run a fetch first" >&2
  rm -f {MU}.tmp
  exit 4
fi
echo "commit {commit} present"
rm -rf {PRE}
mkdir -p {PRE}
git -C {REPO} archive {shlex.quote(commit)} sinofresh-theme | tar -x -C {PRE} --strip-components=1
[ -f {PRE}/functions.php ] || {{ echo "FATAL: extraction left no functions.php" >&2; exit 5; }}
[ -f {PRE}/style.css ] || {{ echo "FATAL: extraction left no style.css" >&2; exit 5; }}
mv {MU}.tmp {MU}
# Rotate, do not delete: the A-pass log is the only proof the gate fired for
# the baseline commit, and an install for the B pass used to wipe it.
[ -f {MULOG} ] && mv {MULOG} {MULOG}.prev || true
chown -R apache:apache {PRE} {MU}
chmod 644 {MU}
echo "--- installed ---"
git -C {REPO} log --oneline -1 {shlex.quote(commit)}
ls -ld {PRE}
grep -c "SF_PREFLIGHT_THEME" {MU}
sha256sum {PRE}/functions.php {PRE}/style.css
""")


def remove():
    ssh(f"""set -euo pipefail
# guarded: only ever removes the pre-flight dir, never a theme directory
case "{PRE}" in
  */themes/sinofresh-theme-preflight) rm -rf {PRE} ;;
  *) echo "REFUSING to remove {PRE}" >&2; exit 3 ;;
esac
echo "--- preflight log ({MULOG}) ---"
wc -l {MULOG} {MULOG}.prev 2>/dev/null || true
rm -f {MU} {MULOG} {MULOG}.prev
echo "--- removed; residual scan ---"
ls -d {PRE} 2>/dev/null && echo "THEME STILL THERE" || echo "theme dir gone"
ls {MU} 2>/dev/null && echo "MU STILL THERE" || echo "mu-plugin gone"
ls {MULOG} 2>/dev/null && echo "LOG STILL THERE" || echo "log gone"
ls -1 {PUB}/wp-content/mu-plugins/
""")


def status():
    ssh(f"""ls -ld {PRE} 2>/dev/null || echo "no preflight theme"
ls -l {MU} 2>/dev/null || echo "no preflight mu-plugin"
wc -l {MULOG} 2>/dev/null || echo "no preflight log"
ls -1 {PUB}/wp-content/mu-plugins/
""")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        install(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "remove":
        remove()
    elif cmd == "status":
        status()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
