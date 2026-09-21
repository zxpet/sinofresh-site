#!/usr/bin/env python3
"""Batch H2a Step 5 — read the candidate's rendered parameter rows for all 21
detail pages, so the operations checklist can state, per record, exactly which
rows exist today and which are waiting on data.

Read-only: one GET per page with X-SF-Preflight: 1 (the candidate copy).

usage: python3 tools/b2d_h2a_params_audit.py
writes _backup/b2d-h2a-baselines/params-audit.json
"""

import json
import os
import re
import subprocess
import sys

HOST = 'root@65.49.215.152'
# curl -u takes PLAIN user:pass — feeding it base64 makes it treat the string as
# a username and PROMPT for a password, which hangs the ssh until it is killed.
AUTH = 'sfdev:VkEws18Kl5V1qp3TpZ6s'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, '_backup', 'b2d-h2a-baselines')

SLUGS = [
    (158, 'soft-chews', 'joint-support-soft-chews'), (159, 'soft-chews', 'calming-soft-chews'),
    (160, 'soft-chews', 'digestive-soft-chews'), (161, 'soft-chews', 'skin-coat-soft-chews'),
    (162, 'tablets', 'joint-support-tablets'), (163, 'tablets', 'multivitamin-tablets'),
    (164, 'tablets', 'calcium-phosphorus-tablets'),
    (165, 'powders', 'probiotic-powder'), (166, 'powders', 'pumpkin-digestive-powder'),
    (167, 'powders', 'bladder-support-powder'),
    (168, 'pastes', 'hairball-remedy-paste'), (169, 'pastes', 'nutrition-paste'),
    (170, 'drops', 'ear-care-drops'), (171, 'drops', 'urinary-care-drops'),
    (172, 'liquids', 'liquid-joint-support'), (173, 'liquids', 'liquid-skin-coat'),
    (174, 'fish-oil', 'wild-alaskan-salmon-oil'), (175, 'fish-oil', 'pure-fish-oil-blend'),
    (176, 'dental-chews', 'plaque-control-dental-chews'), (177, 'dental-chews', 'oral-care-dental-sticks'),
    (178, 'dental-chews', 'natural-cleaning-dental-sticks'),
]


def fetch(slug):
    r = subprocess.run(
        'ssh %s %s' % (HOST, json.dumps(
            "curl -s -H 'X-SF-Preflight: 1' -u '%s' 'https://dev.zxpet.com/formulas/%s/'" % (AUTH, slug))),
        shell=True, capture_output=True, text=True)
    return r.stdout


def main():
    rows = []
    for pid, form, slug in SLUGS:
        url = 'https://dev.zxpet.com/formulas/%s/' % slug
        html = fetch(slug)
        if 'sf-fdetail2__params' not in html:
            print('%d %-13s !! no params block (len=%d)' % (pid, form, len(html)))
        m = re.search(r'<dl class="sf-fdetail2__params">(.*?)</dl>', html, re.S)
        labels = re.findall(r'<dt class="sf-fdetail2__term">(.*?)</dt>', m.group(1)) if m else []
        values = {}
        if m:
            vals = re.findall(r'<dd class="sf-fdetail2__value">(.*?)</dd>', m.group(1), re.S)
            for k, v in zip(labels, vals):
                v = re.sub(r'<[^>]+>', ' ', v)
                values[k] = ' '.join(v.split())[:120]
        rows.append({'id': pid, 'form': form, 'url': url, 'rows': len(labels),
                     'labels': labels, 'values': values})
        print('%d %-13s rows=%d  %s' % (pid, form, len(labels), ', '.join(labels)))
    json.dump(rows, open(os.path.join(BASE, 'params-audit.json'), 'w'), indent=2, ensure_ascii=False)
    print('\nwrote', os.path.join(BASE, 'params-audit.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
