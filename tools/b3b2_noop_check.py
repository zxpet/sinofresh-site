#!/usr/bin/env python3
"""Batch 3b-2 — the pages this batch must not have touched.

The batch edits two rules in style.css. Nothing else in the theme changes, so
every page that does not render `.sf-fdetail-specs` and does not carry the
floating switcher-over-banner pair should come back byte-identical from the live
theme and the preflight theme once the two things that are ALLOWED to differ are
masked:

  * the stylesheet URL and its version token — the candidate is one version
    ahead by design, and the theme directory it is served from differs by design
  * nothing else: the mask is deliberately narrow, so a difference anywhere in
    the markup shows up as a difference in the comparison

The theme's own NAME has to be folded too, and in both of the shapes WordPress
writes it: `themes/sinofresh-theme-preflight/` inside an asset URL, and
`wp-theme-sinofresh-theme-preflight` inside the body class. Folding only the
path form is what made this check fail on its first run — 150 bytes per page,
all of it the ten extra characters of `-preflight` written fifteen times. The
fold is to the base name, not to a wildcard, so an asset re-pointed at some
other theme still shows up as a difference.

Usage:  python3 tools/b3b2_noop_check.py [--json OUT]
"""

import argparse
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.request

AUTH = 'Basic ' + base64.b64encode(b'sfdev:VkEws18Kl5V1qp3TpZ6s').decode()
BASE = 'https://dev.zxpet.com'

# Pages with no spec sheet and no dosage-form configurator. /quality/ carries the
# COA band, which this batch does not touch; /about/ is prose and cards.
PAGES = ['/about/', '/quality/', '/contact/', '/zh/about/']

VER = re.compile(r'\?ver=[0-9a-fA-F.]+')
THEME = re.compile(r'themes/sinofresh-theme(?:-preflight)?/')
# Cloudflare's email obfuscation re-encodes the same address with a fresh key on
# every response, so two fetches of one page differ in the ciphertext and in
# nothing else. Measured on this batch's first comparison run: same length,
# different hex, same address.
CFMAIL = re.compile(r'(/cdn-cgi/l/email-protection#)[0-9a-f]+|(data-cfemail=")[0-9a-f]+')
# Gravity Forms stamps its hidden fields with a per-render token. Only the two
# pages that carry a form differ — the same two pages, in the same place, in
# both runs — so this is the plugin's nonce and not the stylesheet's doing.
GFVAL = re.compile(r"(<input[^>]*gform_hidden[^>]*value=')[^']*(')")


def fetch(path, preflight, tries=3):
    hdrs = {'Authorization': AUTH, 'User-Agent': 'sf-b3b2-noop/1'}
    if preflight:
        hdrs['X-SF-Preflight'] = '1'
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers=hdrs)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            last = 'HTTP %d' % e.code
        except Exception as e:                                   # noqa: BLE001
            last = type(e).__name__
        time.sleep(2.0)
    return '__FAILED__:%s' % last


def mask(text):
    t = THEME.sub('themes/THEME/', text)                          # asset URLs
    t = t.replace('sinofresh-theme-preflight', 'sinofresh-theme')  # body class
    t = CFMAIL.sub(lambda m: (m.group(1) or m.group(2)) + 'X', t)  # per-request key
    t = GFVAL.sub(lambda m: m.group(1) + 'X' + m.group(2), t)      # per-render nonce
    return VER.sub('?ver=X', t)


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return -1 if len(a) == len(b) else n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='/tmp/b3b2-noop.json')
    # The verdict line names the batch it clears. It was hard-coded to 3b-2 and
    # then reused for 3b-3, which would have printed the wrong batch over a
    # correct result — the same "assertion pointing at the wrong object" that
    # this project keeps having to unpick.
    ap.add_argument('--label', default='(batch unstated)')
    args = ap.parse_args()

    out, ok = [], True
    for path in PAGES:
        live = fetch(path, False)
        time.sleep(1.4)
        cand = fetch(path, True)
        time.sleep(1.4)
        if live.startswith('__FAILED__') or cand.startswith('__FAILED__'):
            ok = False
            rows = {'path': path, 'ok': False,
                    'detail': 'fetch failed: %s / %s' % (live[:40], cand[:40])}
        else:
            ml, mc = mask(live), mask(cand)
            same = ml == mc
            i = first_diff(ml, mc)
            rows = {'path': path, 'ok': same, 'live_bytes': len(live),
                    'cand_bytes': len(cand), 'masked_equal': same,
                    'first_diff': i,
                    'context_live': None if same else ml[max(0, i - 90):i + 90],
                    'context_cand': None if same else mc[max(0, i - 90):i + 90],
                    # Provenance, not decoration: if the header had silently
                    # failed, both sides would be the live theme and "identical"
                    # would be the most misleading possible pass.
                    'cand_is_preflight': 'sinofresh-theme-preflight' in cand,
                    'live_is_live': 'sinofresh-theme-preflight' not in live}
            if not (rows['cand_is_preflight'] and rows['live_is_live']):
                rows['ok'] = False
                rows['detail'] = ('provenance failed: cand_is_preflight=%s live_is_live=%s'
                                  % (rows['cand_is_preflight'], rows['live_is_live']))
            ok &= rows['ok']
        out.append(rows)
        print('  %-16s live=%s cand=%s  masked_equal=%s  %s'
              % (rows['path'], rows.get('live_bytes'), rows.get('cand_bytes'),
                 rows.get('masked_equal'), '' if rows['ok'] else '*** DIFF ***'))
        if not rows['ok'] and rows.get('context_live'):
            print('     live: %s' % ' '.join(rows['context_live'].split())[:150])
            print('     cand: %s' % ' '.join(rows['context_cand'].split())[:150])

    print('\n%s  %s no-touch check (%d pages)'
          % ('PASS' if ok else 'FAIL', args.label, len(PAGES)))
    json.dump({'ok': ok, 'rows': out}, open(args.json, 'w'), indent=1, ensure_ascii=False)
    print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
