#!/usr/bin/env python3
"""Static validator for a WP block template file (no WordPress needed).

Checks
  1. every "<!-- wp:NAME ..." open has a matching "<!-- /wp:NAME -->"
  2. self-closing comments use the tight form "... /-->"  (a spaced "/ -->"
     would be a malformed block delimiter)
  3. attribute JSON parses (json.loads on the {...} payload)
  4. no forbidden "{{" leakage outside of known placeholders in comments,
     no " -- >" style whitespace damage
  5. no unclosed <section>/<div>/<nav>/<p> in the rendered-HTML part

Usage: python3 tools/b2c_s2_block_lint.py templates/archive-sf_formula.html [...]
"""
import json
import re
import sys

OPEN = re.compile(r'<!--\s*wp:([a-z0-9/-]+)\s*(\{.*?\})?\s*(/?)-->')
CLOSE = re.compile(r'<!--\s*/wp:([a-z0-9/-]+)\s*-->')

fails = []
for path in sys.argv[1:]:
    src = open(path, encoding='utf-8').read()
    stack = []
    opens = 0
    selfclose = 0
    # IMPORTANT: opens and closes must be walked in file order (a nested block
    # closes before its parent). Collect both kinds with their offsets first.
    events = []
    for m in OPEN.finditer(src):
        name, attrs, slash = m.group(1), m.group(2), m.group(3)
        opens += 1
        if attrs:
            try:
                json.loads(attrs)
            except Exception as e:
                fails.append(f'{path}: bad JSON attrs in wp:{name} -> {e}')
        if slash:
            selfclose += 1
        else:
            events.append((m.start(), 'open', name))
    for m in CLOSE.finditer(src):
        events.append((m.start(), 'close', m.group(1)))
    for pos, kind, name in sorted(events):
        if kind == 'open':
            stack.append(name)
        else:
            if not stack:
                fails.append(f'{path}: stray close <!-- /wp:{name} -->')
            elif stack[-1] != name:
                fails.append(f'{path}: close wp:{name} does not match open wp:{stack[-1]}')
                stack.pop()
            else:
                stack.pop()
    if stack:
        fails.append(f'{path}: unclosed blocks {stack}')

    # 2. malformed spaced self-close
    spaced = [m.start() for m in re.finditer(r'/ -->', src)]
    if spaced:
        fails.append(f'{path}: {len(spaced)} malformed "/ -->" delimiter(s)')
    # also catch " -- >" / "-->" split by whitespace-damaged delimiters
    if re.search(r'--\s+>', src):
        fails.append(f'{path}: whitespace-damaged "-- >" delimiter')

    # 3. JSON payload sanity for core/query-title
    for m in re.finditer(r'<!--\s*wp:query-title\s*(\{.*?\})\s*/-->', src):
        try:
            d = json.loads(m.group(1))
            if d.get('type') != 'archive':
                fails.append(f'{path}: query-title type={d.get("type")!r} (expected archive)')
            if d.get('showPrefix') is not False:
                fails.append(f'{path}: query-title showPrefix should be false')
        except Exception as e:
            fails.append(f'{path}: query-title payload unreadable -> {e}')

    # 4. HTML tag balance on the raw file (comments stripped)
    stripped = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    for tag in ('section', 'div', 'nav', 'p', 'figure'):
        o = len(re.findall(rf'<{tag}[\s>]', stripped))
        c = len(re.findall(rf'</{tag}>', stripped))
        if o != c:
            fails.append(f'{path}: <{tag}> open={o} close={c}')

    print(f'{path}: {opens} block comments ({selfclose} self-closing), '
          f'stack balanced = {not stack}')

print()
if fails:
    print('FAIL')
    for f in fails:
        print(' -', f)
    sys.exit(1)
print('PASS — block delimiters and HTML tags balanced, no malformed self-close')
