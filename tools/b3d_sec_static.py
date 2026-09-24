#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d -- static security pass over the theme's production code.

Scans only what ships and runs: theme PHP and the JS the pages enqueue.
`tools/` and `_backup/` are excluded -- the first is development scaffolding that
never reaches the docroot, the second is an archive; including either would bury
the real findings under a hundred hits that cannot execute.

The rules are grouped by the question each answers, and a rule reports file:line
with the source line so a hit can be judged rather than counted. Every group
prints its own total, including zero: "0 hits" is a result, and a rule that
silently finds nothing looks the same as a rule that is broken.
"""
import json
import os
import re
import sys

THEME = 'sinofresh-theme'
OUT = os.path.join('docs', 'site-survey-2026-09-24', 'security-static.json')
SKIP = {'_backup', 'node_modules', '.git', 'docs', 'screenshots', 'tools', 'vendor'}

# (group, label, compiled pattern, note)
RULES = [
    ('code-exec', 'eval()',
     r'\beval\s*\(', 'arbitrary code execution if any part is user-influenced'),
    ('code-exec', 'create_function()',
     r'\bcreate_function\s*\(', 'removed in PHP 8; also eval-equivalent'),
    ('code-exec', 'assert() with a string',
     r'\bassert\s*\(\s*[\'"]', 'string assert is eval in older PHP'),
    ('code-exec', 'extract()',
     r'\bextract\s*\(', 'variable injection into local scope'),
    ('shell', 'exec/system/passthru',
     r'\b(exec|system|passthru|shell_exec|popen|proc_open)\s*\(', 'shell execution'),
    ('shell', 'backtick shell',
     r'[^\\]`[^`\n]{4,}`', 'shell execution via backticks'),
    ('shell', 'preg_replace /e modifier',
     r'preg_replace\s*\([^)]*[\'"]/[a-z]*e[a-z]*[\'"]', 'eval via regex modifier'),
    ('file', 'include/require with a variable',
     r'\b(include|include_once|require|require_once)\s*\(?\s*\$', 'LFI if the path is user-influenced'),
    ('file', 'file read with a variable',
     r'\b(file_get_contents|file_put_contents|fopen|readfile|unlink|rename|copy)\s*\(\s*\$', 'path from a variable'),
    ('file', 'unserialize()',
     r'\bunserialize\s*\(', 'object injection when the payload is untrusted'),
    ('file', 'move_uploaded_file',
     r'\bmove_uploaded_file\s*\(', 'unsigned file write'),
    ('file', 'base64_decode',
     r'\bbase64_decode\s*\(', 'commonly hides a payload'),
    ('sql', 'query built by concatenation',
     r'\$wpdb\s*->\s*(query|get_results|get_var|get_row|get_col)\s*\(\s*[\'"].*\$',
     'unprepared SQL with a variable inside the string'),
    ('sql', 'query with a bare variable',
     r'\$wpdb\s*->\s*(query|get_results|get_var|get_row|get_col)\s*\(\s*\$',
     'SQL string assembled before the call -- check for prepare()'),
    ('sql', 'prepare with an interpolated placeholder',
     r'\$wpdb\s*->\s*prepare\s*\(\s*"[^"]*\$', 'placeholders must not be interpolated'),
    ('input', 'superglobal read',
     r'\$_(GET|POST|REQUEST|COOKIE|FILES|SERVER)\s*\[', 'input source'),
    ('input', 'php://input',
     r'php://input', 'raw input source'),
    ('rest', 'register_rest_route',
     r'register_rest_route\s*\(', 'check permission_callback on each'),
    ('rest', 'permission_callback __return_true',
     r'permission_callback\s*[\'"]?=>?\s*[\'"]?__return_true', 'publicly callable route'),
    ('rest', 'permission_callback is a variable/late',
     r'permission_callback', 'presence marker'),
    ('ajax', 'wp_ajax handler',
     r'add_action\s*\(\s*[\'"]wp_ajax', 'check nonce + capability inside'),
    ('ajax', 'admin_post handler',
     r'add_action\s*\(\s*[\'"]admin_post', 'check nonce + capability inside'),
    ('nonce', 'check_admin_referer / wp_verify_nonce',
     r'\b(check_admin_referer|check_ajax_referer|wp_verify_nonce)\s*\(', 'presence marker'),
    ('cap', 'current_user_can',
     r'\bcurrent_user_can\s*\(', 'presence marker'),
    ('out', 'echo of a bare variable',
     r'\b(echo|print)\s+\$[A-Za-z_]', 'escaping must be applied at the echo'),
    ('out', 'echo of a function call without esc_',
     r'\b(echo|print)\s+[A-Za-z_][A-Za-z0-9_]*(?:->|::)?[A-Za-z0-9_]*\s*\(', 'check the callee escapes'),
    ('out', 'printf with a variable',
     r'\b(printf|vprintf)\s*\(', 'escaping must be applied to the arguments'),
    ('out', 'esc_* usage',
     r'\b(esc_html|esc_attr|esc_url|esc_textarea|esc_js|wp_kses|wp_kses_post|sanitize_text_field|absint|intval)\b',
     'presence marker'),
    ('secret', 'credential-shaped literal',
     r'(?i)\b(api[_-]?key|secret|password|passwd|token|private[_-]?key|access[_-]?key)\b\s*[=:]\s*[\'"][^\'"\s]{8,}',
     'hardcoded secret'),
    ('secret', 'long base64/hex literal',
     r'[\'"][A-Za-z0-9+/]{40,}={0,2}[\'"]', 'possible embedded key'),
    ('secret', 'private IPv4 / localhost',
     r'\b(127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)\b', 'environment leakage'),
    ('js', 'innerHTML assignment',
     r'\.innerHTML\s*=', 'DOM injection if the value is not trusted'),
    ('js', 'document.write',
     r'document\.write\s*\(', 'DOM injection'),
    ('js', 'insertAdjacentHTML',
     r'insertAdjacentHTML\s*\(', 'DOM injection'),
    ('js', 'new Function / eval',
     r'(\bnew\s+Function\s*\(|\beval\s*\()', 'dynamic code'),
    ('js', 'fetch/XHR with a variable URL',
     r'\b(fetch|XMLHttpRequest|\.open)\s*\(\s*[A-Za-z_$]', 'untrusted target'),
    ('js', 'postMessage without origin check',
     r'postMessage\s*\(', 'check event.origin on the receiver'),
]

FILE_RE = re.compile(r'\.(php|js)$')


def collect():
    files = []
    for root, dirs, names in os.walk(THEME):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for n in names:
            if FILE_RE.search(n):
                files.append(os.path.join(root, n))
    return sorted(files)


def main():
    files = collect()
    results = {}
    totals = {}
    for group, label, pat, note in RULES:
        rx = re.compile(pat)
        hits = []
        for p in files:
            for i, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
                s = line.rstrip('\n')
                if rx.search(s):
                    hits.append({'file': p, 'line': i, 'code': s.strip()[:200]})
        key = '%s | %s' % (group, label)
        results[key] = {'group': group, 'label': label, 'note': note,
                        'count': len(hits), 'hits': hits}
        totals[group] = totals.get(group, 0) + len(hits)

    order = ['sql', 'input', 'rest', 'ajax', 'code-exec', 'shell', 'file', 'secret',
             'out', 'nonce', 'cap', 'js']
    print('=== files scanned: %d (theme production code, tools/_backup excluded) ===' % len(files))
    print('\n=== totals by group ===')
    for g in order:
        if g in totals:
            print('  %-10s %4d' % (g, totals[g]))
    print('\n=== per rule ===')
    for key, r in results.items():
        print('\n[%s] %s  ->  %d' % (r['group'], r['label'], r['count']))
        print('    %s' % r['note'])
        for h in r['hits'][:14]:
            print('    %s:%d  %s' % (h['file'], h['line'], h['code']))
        if r['count'] > 14:
            print('    ... %d more' % (r['count'] - 14))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump({'files': files, 'rules': results, 'totals': totals}, fh,
                  ensure_ascii=False, indent=1)
    print('\n-> %s' % OUT)


if __name__ == '__main__':
    main()
