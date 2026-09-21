#!/usr/bin/env python3
"""Batch H1 apply — the eight small functions.php edits, the eight dosage
template subtitle edits, and byte-records for the six new files.

Every edit is self-proving in the batch C style: assert the anchor occurs
exactly once, splice, read back, undo, and demand the undo equal the
pre-batch bytes. Run with --check to only verify anchors; --apply to write
(against the real theme, or a candidate copy via --theme-dir).

The edits are the batch H1b touch points plus the two requires; everything
else lives in the new files (inc/formula-pools.php, inc/formula-admin.php,
assets/admin/*) whose bytes this script records rather than splices.
"""

import argparse
import hashlib
import os
import sys

# --- functions.php edits ----------------------------------------------------
# Each: (label, old, new). Undo = reverse swap. "old" must occur exactly once
# in the pre-batch file; "new" exactly once after the batch.

EDITS = [
    ('php/requires',
     "require get_template_directory() . '/inc/cert-download.php';\n",
     "require get_template_directory() . '/inc/cert-download.php';\n"
     "\n/* Batch H1 — the formula publishing form (admin) and its option pools.\n"
     "   Admin-only for now: nothing here renders a front-end byte. */\n"
     "require get_template_directory() . '/inc/formula-pools.php';\n"
     "require get_template_directory() . '/inc/formula-admin.php';\n"),

    ('php/token-line',
     "\t\t'{{sf-copyright-suffix}}' => esc_html(get_option('sf_copyright_suffix', $d['sf_copyright_suffix'])),\n",
     "\t\t'{{sf-copyright-suffix}}' => esc_html(get_option('sf_copyright_suffix', $d['sf_copyright_suffix'])),\n"
     "\t\t'{{sf-certifications-line}}' => esc_html(sf_certifications_line()),\n"),

    ('php/cert-sanitize',
     "\t\t\tfor ($i = 0; $i < 8; $i++) {\n"
     "\t\t\t\t$row = (isset($v[$i]) && is_array($v[$i])) ? $v[$i] : array();\n"
     "\t\t\t\t$out[$i] = array(\n"
     "\t\t\t\t\t'name'   => isset($row['name']) ? sanitize_text_field($row['name']) : '',\n"
     "\t\t\t\t\t'url'    => isset($row['url']) ? esc_url_raw($row['url']) : '',\n"
     "\t\t\t\t\t'active' => !empty($row['active']),\n"
     "\t\t\t\t);\n"
     "\t\t\t}\n"
     "\t\t\treturn $out;\n",
     "\t\t\t/* Batch H1: dynamic rows instead of eight fixed slots. Empty\n"
     "\t\t\t   rows collapse out; order is preserved for the badges, the\n"
     "\t\t\t   line token, the detail row and the schema. */\n"
     "\t\t\tforeach ((array) $v as $row) {\n"
     "\t\t\t\t$row = is_array($row) ? $row : array();\n"
     "\t\t\t\t$name = isset($row['name']) ? sanitize_text_field($row['name']) : '';\n"
     "\t\t\t\tif ($name === '') {\n"
     "\t\t\t\t\tcontinue;\n"
     "\t\t\t\t}\n"
     "\t\t\t\t$out[] = array(\n"
     "\t\t\t\t\t'name'   => $name,\n"
     "\t\t\t\t\t'url'    => isset($row['url']) ? esc_url_raw($row['url']) : '',\n"
     "\t\t\t\t\t'active' => !empty($row['active']),\n"
     "\t\t\t\t);\n"
     "\t\t\t}\n"
     "\t\t\treturn $out;\n"),

    ('php/cert-table',
     "\t\t\t\t<tbody>\n"
     "\t\t\t\t<?php for ($i = 0; $i < 8; $i++) :\n"
     "\t\t\t\t\t$c = isset($certs[$i]) && is_array($certs[$i]) ? $certs[$i] : array('name' => '', 'url' => '', 'active' => false); ?>\n"
     "\t\t\t\t<tr>\n"
     "\t\t\t\t\t<td><?php echo (int) ($i + 1); ?></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo $i; ?>][name]\" type=\"text\" class=\"regular-text\" value=\"<?php echo esc_attr($c['name']); ?>\"></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo $i; ?>][url]\" type=\"text\" class=\"regular-text\" value=\"<?php echo esc_attr($c['url']); ?>\"></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo $i; ?>][active]\" type=\"checkbox\" value=\"1\" <?php checked(!empty($c['active'])); ?>></td>\n"
     "\t\t\t\t</tr>\n"
     "\t\t\t\t<?php endfor; ?>\n"
     "\t\t\t\t</tbody>\n"
     "\t\t\t</table>\n",
     "\t\t\t\t<tbody>\n"
     "\t\t\t\t<?php foreach ($certs as $i => $c) :\n"
     "\t\t\t\t\t$c = is_array($c) ? $c : array('name' => '', 'url' => '', 'active' => false); ?>\n"
     "\t\t\t\t<tr>\n"
     "\t\t\t\t\t<td><?php echo (int) ($i + 1); ?></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo (int) $i; ?>][name]\" type=\"text\" class=\"regular-text\" value=\"<?php echo esc_attr($c['name']); ?>\"></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo (int) $i; ?>][url]\" type=\"text\" class=\"regular-text\" value=\"<?php echo esc_attr($c['url']); ?>\"></td>\n"
     "\t\t\t\t\t<td><input name=\"sf_certifications[<?php echo (int) $i; ?>][active]\" type=\"checkbox\" value=\"1\" <?php checked(!empty($c['active'])); ?>></td>\n"
     "\t\t\t\t\t<td><button type=\"button\" class=\"button-link sf-certs-del\">Remove</button></td>\n"
     "\t\t\t\t</tr>\n"
     "\t\t\t\t<?php endforeach; ?>\n"
     "\t\t\t\t</tbody>\n"
     "\t\t\t</table>\n"
     "\t\t\t<p><button type=\"button\" class=\"button\" id=\"sf-certs-add\">+ Add row</button></p>\n"),

    ('php/schema-credentials',
     "\t$schema['hasCredential'] = array(\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'FDA Registered',       'credentialCategory' => 'U.S. Food and Drug Administration'),\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'cGMP Compliant',       'credentialCategory' => 'Current Good Manufacturing Practice'),\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'ISO 9001 Certified',   'credentialCategory' => 'Quality Management System'),\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'FSSC 22000 Certified', 'credentialCategory' => 'GFSI Recognized Food Safety System'),\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'HACCP Certified',      'credentialCategory' => 'Hazard Analysis Critical Control Point'),\n"
     "\t\tarray('@type' => 'EducationalOccupationalCredential', 'name' => 'BRC Certified',        'credentialCategory' => 'British Retail Consortium'),\n"
     "\t);\n",
     "\t/* Batch H1: the same six credentials, now read from the Site Settings\n"
     "\t   certification rows (sf_cert_schema_credentials() keeps the exact\n"
     "\t   names and order this array shipped with, so the default option set\n"
     "\t   renders byte-identically). */\n"
     "\t$schema['hasCredential'] = sf_cert_schema_credentials();\n"),

    ('php/faq-certs',
     "\t$certs = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Certifications') : '';\n",
     "\t$certs = sf_formula_certifications_value($form_slug);\n"),

    ('php/factsheet-certs',
     "\t$certifications = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Certifications') : '';\n",
     "\t$certifications = sf_formula_certifications_value($form_slug);\n"),
]

# --- dosage page template edits ----------------------------------------------
# One per template: the hero subtitle's certification segment becomes the
# token. The default option set renders the identical string, so the page
# bytes do not move. The facts-mini Certifications row (the spec_cell data
# source) is deliberately NOT tokenised — spec_cell reads the template file,
# and a token there would poison it.
TPL_OLD = '8 dosage forms &middot; FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC &middot;'
TPL_NEW = '8 dosage forms &middot; {{sf-certifications-line}} &middot;'
DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews']

# --- new files whose bytes the gate records ----------------------------------
NEW_FILES = [
    'inc/formula-pools.php',
    'inc/formula-admin.php',
    'assets/admin/sf-mb.css',
    'assets/admin/sf-mb-tables.js',
    'assets/admin/sf-mb-precheck.js',
    'assets/admin/sf-site-settings.js',
]


def splice(text, old, new, label, problems, direction):
    n = text.count(old)
    if n != 1:
        problems.append('%s: %r occurs %d times in the %s side (want exactly 1)'
                        % (label, old[:60], n, direction))
        return None
    return text.replace(old, new, 1)


def hashes(theme):
    out = {}
    for rel in NEW_FILES:
        p = os.path.join(theme, rel)
        if not os.path.exists(p):
            out[rel] = '(missing)'
            continue
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        out[rel] = h
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--backup-dir')
    ap.add_argument('--theme-dir', help='apply against a candidate copy instead of the real theme')
    ap.add_argument('--hashes-out', help='write the new-file sha256 table here')
    args = ap.parse_args()
    if args.check == args.apply:
        print('pass exactly one of --check / --apply')
        return 2

    theme = args.theme_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sinofresh-theme')
    problems = []

    php_path = os.path.join(theme, 'functions.php')
    raw = open(php_path, encoding='utf-8').read()
    pre = raw

    if args.check:
        for label, old, _ in EDITS:
            n = raw.count(old)
            if n != 1:
                problems.append('%s: anchor occurs %d times (want exactly 1)' % (label, n))
        for slug in DOSAGE:
            p = os.path.join(theme, 'templates', 'page-%s.html' % slug)
            s = open(p, encoding='utf-8').read()
            if s.count(TPL_OLD) != 1:
                problems.append('tpl/%s: hero certification segment occurs %d times (want exactly 1)' % (slug, s.count(TPL_OLD)))
        for rel in NEW_FILES:
            if not os.path.exists(os.path.join(theme, rel)):
                problems.append('new file missing: %s' % rel)
        if problems:
            print('CHECK FAILED')
            for p in problems:
                print('  !!', p)
            return 1
        print('CHECK OK: %d php edits, %d templates, %d new files' % (len(EDITS), len(DOSAGE), len(NEW_FILES)))
        return 0

    # apply (+ undo proof), all in memory; nothing is written until it proves
    backup = {}
    edited_tpl = {}
    cur = raw
    for label, old, new in EDITS:
        cur = splice(cur, old, new, label, problems, 'pre-batch')
        if cur is None:
            break
    if not problems:
        for slug in DOSAGE:
            p = os.path.join(theme, 'templates', 'page-%s.html' % slug)
            s = open(p, encoding='utf-8').read()
            s2 = splice(s, TPL_OLD, TPL_NEW, 'tpl/%s' % slug, problems, 'pre-batch')
            if s2 is None:
                break
            backup['templates/page-%s.html' % slug] = s
            edited_tpl[slug] = s2
    if not problems:
        # undo everything in memory, demand the originals back
        undone = cur
        for label, old, new in reversed(EDITS):
            undone = splice(undone, new, old, label + '(undo)', problems, 'post-batch')
            if undone is None:
                break
        if undone is not None and undone != pre:
            problems.append('php undo does not reproduce the pre-batch bytes')
        if not problems:
            for slug in DOSAGE:
                s2 = edited_tpl[slug]
                s3 = splice(s2, TPL_NEW, TPL_OLD, 'tpl/%s(undo)' % slug, problems, 'post-batch')
                if s3 is None or s3 != backup['templates/page-%s.html' % slug]:
                    problems.append('tpl/%s undo mismatch' % slug)
                    break

    if problems:
        print('APPLY ABORTED — nothing written')
        for p in problems:
            print('  !!', p)
        return 1

    if args.backup_dir:
        os.makedirs(args.backup_dir, exist_ok=True)
        for rel, content in list(backup.items()):
            dst = os.path.join(args.backup_dir, rel.replace('/', '__'))
            open(dst, 'w', encoding='utf-8').write(content)
        open(os.path.join(args.backup_dir, 'functions.php'), 'w', encoding='utf-8').write(pre)

    # write for real
    open(php_path, 'w', encoding='utf-8').write(cur)
    for slug in DOSAGE:
        p = os.path.join(theme, 'templates', 'page-%s.html' % slug)
        open(p, 'w', encoding='utf-8').write(edited_tpl[slug])

    # read back and prove
    if open(php_path, encoding='utf-8').read() != cur:
        print('!! read-back mismatch on functions.php')
        return 1
    table = hashes(theme)
    if args.hashes_out:
        with open(args.hashes_out, 'w', encoding='utf-8') as fh:
            for rel, h in table.items():
                fh.write('%s  %s\n' % (h, rel))
    print('APPLIED: %d php edits + %d templates; new-file hashes:' % (len(EDITS), len(DOSAGE)))
    for rel, h in table.items():
        print('  %-34s %s' % (rel, h[:16]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
