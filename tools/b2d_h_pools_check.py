#!/usr/bin/env python3
"""Batch H1 pool check — inc/formula-pools.php vs the configurator markup.

The pools were transcribed by hand from the eight dosage templates, so a
typo is a silent data corruption waiting for the front end. This script
re-extracts every group's data-value set from the templates and compares it,
verbatim and in order, with what the PHP file returns. Exit 1 on any drift.
"""

import json
import re
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(ROOT, 'sinofresh-theme')
PHP = os.environ.get('SF_PHP', os.path.expanduser(
    '~/Library/Application Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php'))

# batch-H1 dimension -> configurator data-group per dosage form
MAP = {
    'soft-chews':    {'shape': 'shape', 'weights': 'weight', 'counts': 'count', 'flavors': 'flavor', 'colors': 'color', 'packaging': 'packaging'},
    'tablets':       {'shape': 'shape', 'weights': 'weight', 'counts': 'count', 'flavors': 'flavor', 'colors': 'color', 'packaging': 'packaging'},
    'dental-chews':  {'shape': 'shape', 'weights': 'weight_per_piece', 'counts': 'count', 'flavors': 'flavor', 'colors': 'color', 'packaging': 'packaging'},
    'pastes':        {'shape': 'texture', 'weights': 'tube_weight', 'counts': 'tube_weight', 'flavors': 'flavor', 'colors': 'color', 'packaging': 'packaging'},
    'powders':       {'shape': 'appearance', 'weights': 'serving_size', 'counts': 'net_weight', 'flavors': 'flavor', 'colors': 'color', 'packaging': 'packaging'},
    'drops':         {'shape': 'appearance', 'weights': 'bottle_size', 'counts': 'bottle_size', 'flavors': 'flavor', 'colors': None, 'packaging': 'packaging'},
    'liquids':       {'shape': 'appearance', 'weights': 'serving_size', 'counts': 'bottle_size', 'flavors': 'flavor', 'colors': None, 'packaging': 'packaging'},
    'fish-oil':      {'shape': 'form', 'weights': 'omega3_per_unit', 'counts': 'count', 'flavors': 'source', 'colors': None, 'packaging': 'packaging'},
}

PROBE = r'''<?php
/* The pools file calls WP helpers on entry; outside WordPress they are
   identity stubs — the forms arrive as slugs already. */
if (!function_exists('sanitize_title')) { function sanitize_title($t) { return $t; } }
if (!function_exists('get_option')) { function get_option($k, $d = false) { return $d; } }
require $argv[1];
$out = array();
foreach (array('soft-chews','tablets','dental-chews','pastes','powders','drops','liquids','fish-oil') as $form) {
    foreach (array('shape','weights','counts','flavors','colors','packaging') as $dim) {
        $out[$form][$dim] = sf_formula_field_pool($form, $dim);
    }
}
echo json_encode($out, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
'''


def tpl_groups(template_path):
    """data-group blocks in the option area (first occurrence of each)."""
    s = open(template_path, encoding='utf-8').read()
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'data-group="([a-z0-9_]+)"', s)]
    seen, out = set(), {}
    for idx, (pos, group) in enumerate(marks):
        if group in seen:
            continue
        seen.add(group)
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(s)
        vals = re.findall(r'data-value="([^"]*)"', s[pos:end])
        vals = [v.replace('&amp;', '&') for v in vals]
        out[group] = vals
    return out


def main():
    probe = '/tmp/sf_pools_probe.php'
    open(probe, 'w', encoding='utf-8').write(PROBE)
    res = subprocess.run([PHP, probe, os.path.join(THEME, 'inc', 'formula-pools.php')],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print('php probe failed:', res.stderr[:400])
        return 1
    php = json.loads(res.stdout)
    bad = 0
    for form, dims in MAP.items():
        groups = tpl_groups(os.path.join(THEME, 'templates', 'page-%s.html' % form))
        for dim, group in dims.items():
            want = groups.get(group, []) if group else []
            got = php[form][dim]
            if want != got:
                bad += 1
                print('DRIFT %s.%s (configurator group %r)' % (form, dim, group))
                print('  template:', want)
                print('  pools   :', got)
    print('checked 8 forms x 6 dims against the configurator markup:', 'OK' if bad == 0 else '%d DRIFT(S)' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
