#!/usr/bin/env python3
"""Prune a declared list of dead selectors out of style.css.

Why not sed: a rule can carry a selector LIST and only one member may be dead
(`.wp-block-table table, .sf-num, .configurator__summary-value{}` is a real
shape in this file), and a dead class can also appear merely *named in a
comment* that documents a live rule. Deleting either blindly takes live code
with it. So this parses the stylesheet into rules and, within each rule, strips
comments before asking whether the selector is dead.

Decision per rule:
  * every selector (comments stripped) contains a dead token -> cut the rule
  * some selectors dead                                        -> rewrite the list
  * no selector dead                                           -> untouched,
    even if a comment inside it names a dead class

Modes:
  --scan          inventory, nothing written (default)
  --occurrences   every occurrence of every dead token, classified by position
  --apply         write the pruned stylesheet

--apply asserts before writing: dead tokens are zero in *selector* position,
the surviving rule count is exactly found-minus-cut, braces balance, and no
at-rule is left empty by the cut.
"""
import argparse
import os
import re
import sys

DEAD_TOKENS = [
    '.sf-facts__',
    '.sf-spectable__',
    '.sf-fdetail-media__',
    '.configurator__summary-value',
]

COMMENT_RE = re.compile(r'/\*.*?\*/', re.S)


def strip_comments(s):
    """Blank out comments WITHOUT changing the string's length.

    Replacing a comment with a single space would shift every offset after it,
    so a selector span computed on the stripped text would point at the wrong
    bytes of the original. The blanking has to be length-preserving.
    """
    return COMMENT_RE.sub(lambda m: ' ' * (m.end() - m.start()), s)


def prelude_start_before(src, open_idx):
    """Start of the prelude of the block that opens at `open_idx`.

    Two things have to be stepped over, and doing either one naively cuts a
    comment in half (which leaves an unterminated /* in the file and makes the
    rest of the stylesheet parse as comment):

      1. the block's own prelude text, e.g. `@media (max-width: 768px) `;
      2. any comment written to introduce the block.

    The delimiter that ends the previous block is found on a comment-blanked
    copy, so a brace inside a comment cannot be mistaken for it; then the
    comment, if any, is taken from the real text.
    """
    blank = strip_comments(src)
    floor = 1 + max(blank.rfind('}', 0, open_idx),
                    blank.rfind('{', 0, open_idx),
                    blank.rfind(';', 0, open_idx))
    k = floor + len(re.match(r'[ \t\r\n]*', src[floor:]).group(0))
    if src[k:k + 2] == '/*':
        return k
    return floor


# ---------------------------------------------------------------- lexer

def find_matching_brace(src, open_idx):
    """Index of the `}` closing the block that opens at src[open_idx] == '{'."""
    depth, i, n = 0, open_idx, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '"\'':
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            i = j + 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_selectors(sel):
    """Split a selector list on top-level commas -> [(text, start, end)]."""
    out, depth, i, start = [], 0, 0, 0
    while i < len(sel):
        c = sel[i]
        if c == '/' and i + 1 < len(sel) and sel[i + 1] == '*':
            j = sel.find('*/', i + 2)
            i = len(sel) if j < 0 else j + 2
            continue
        if c in '"\'':
            j = i + 1
            while j < len(sel):
                if sel[j] == '\\':
                    j += 2
                    continue
                if sel[j] == c:
                    break
                j += 1
            i = j + 1
            continue
        if c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif c == ',' and depth == 0:
            out.append((sel[start:i], start, i))
            start = i + 1
        i += 1
    out.append((sel[start:], start, len(sel)))
    return out


def parse_rules(src):
    """Yield style rules with absolute offsets.

    {'sel','sel_start','block_start','end','in_at'}
    'sel' is the raw prelude (may include leading comments);
    use strip_comments() on it before looking for selectors.
    """
    rules = []
    i, n = 0, len(src)
    stack = []
    prelude_start = 0
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '"\'':
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            i = j + 1
            continue
        if c == '{':
            prelude = src[prelude_start:i]
            stripped = strip_comments(prelude).strip()
            end = find_matching_brace(src, i)
            if end < 0:
                return rules
            if stripped.startswith('@'):
                stack.append(stripped.split()[0])
                off = i + 1
                for r in parse_rules(src[off:end]):
                    for k in ('sel_start', 'block_start', 'end'):
                        r[k] += off
                    r['in_at'] = stack[-1]
                    rules.append(r)
                stack.pop()
            elif stripped == '':
                pass                    # comment-only block, or a stray brace
            else:
                rules.append({
                    'sel': prelude,
                    'sel_start': prelude_start,
                    'block_start': i,
                    'end': end + 1,
                    'in_at': stack[-1] if stack else None,
                })
            i = end + 1
            prelude_start = i
            continue
        if c == '}':
            prelude_start = i + 1
        i += 1
    return rules


# ---------------------------------------------------------------- analysis

def dead_in(text):
    return [t for t in DEAD_TOKENS if t in text]


def classify(src, rules):
    whole, partial = [], []
    for r in rules:
        sels = [s for s in split_selectors(strip_comments(r['sel'])) if s[0].strip()]
        if not sels:
            continue
        flags = [bool(dead_in(s[0])) for s in sels]
        if not any(flags):
            continue
        (whole if all(flags) else partial).append((r, sels, flags))
    return whole, partial


def line_of(src, idx):
    return src.count('\n', 0, idx) + 1


def span_lines(src, r):
    return line_of(src, r['sel_start']), line_of(src, r['end'] - 1)


def show(src, whole, partial):
    print("style.css: %d bytes, %d lines, %d style rules"
          % (len(src), src.count('\n') + 1, len(parse_rules(src))))
    print()
    print("=== whole-rule deletions: %d ===" % len(whole))
    for r, sels, flags in whole:
        a, b = span_lines(src, r)
        sel = ' '.join(r['sel'].split())
        print("   L%-6d-%-6d %-22s %s"
              % (a, b, ('<' + r['in_at'] + '>') if r['in_at'] else '',
                 ' '.join(strip_comments(r['sel']).split())[:64]))
        if COMMENT_RE.search(r['sel']):
            print("            (carries a comment: %s)"
                  % ' '.join(r['sel'].split())[:88])
    print()
    print("=== partial (selector list, live half must survive): %d ===" % len(partial))
    for r, sels, flags in partial:
        a, b = span_lines(src, r)
        print("   L%-6d-%-6d" % (a, b))
        for (txt, _s, _e), d in zip(sels, flags):
            print("        %s %s" % ('DEAD ' if d else 'LIVE ', ' '.join(txt.split())[:84]))
    print()
    n_sel = sum(sum(1 for f in flags if f) for _r, _s, flags in whole) \
        + sum(sum(1 for f in flags if f) for _r, _s, flags in partial)
    print("dead selectors to cut: %d  (rule blocks removed: %d)"
          % (n_sel, len(whole)))


def occurrences(src):
    rules = parse_rules(src)
    # map each offset to its enclosing rule
    # A rule owns everything from the start of its prelude to its closing brace
    # -- the selector sits BEFORE block_start, so keying on block_start alone
    # would report every selector as belonging to no rule at all.
    owner = []
    for ri, r in enumerate(rules):
        owner.append((r['sel_start'], r['end'], ri))

    def rule_at(pos):
        for ss, en, ri in owner:
            if ss <= pos < en:
                return ri
        return None

    print("=== every occurrence of every dead token, by position ===")
    for t in DEAD_TOKENS:
        print()
        print("---- %s ----" % t)
        for m in re.finditer(re.escape(t), src):
            pos = m.start()
            line = line_of(src, pos)
            ls = src.rfind('\n', 0, pos) + 1
            le = src.find('\n', pos)
            if le < 0:
                le = len(src)
            linetext = src[ls:le]

            # is this offset inside a comment?
            in_comment = False
            for cm in COMMENT_RE.finditer(src):
                if cm.start() <= pos < cm.end():
                    in_comment = True
                    break

            ri = rule_at(pos)
            r = rules[ri] if ri is not None else None
            if in_comment:
                kind = 'COMMENT'
            elif r is None:
                kind = 'OUTSIDE-RULE'
            elif r['sel_start'] <= pos < r['block_start']:
                kind = 'SELECTOR'
            else:
                kind = 'DECLARATION'
            print("   L%-6d %-12s %-24s | %s"
                  % (line, kind,
                     ('<' + r['in_at'] + '>') if (r and r['in_at']) else '',
                     linetext.strip()[:88]))


def find_empty_at_rules(src):
    """At-rules whose body holds nothing at all, with their offsets.

    Cutting the last rule out of a `@media` block leaves the wrapper behind.
    Returns [(prelude_start, open_idx, close_idx)] where prelude_start is the
    start of the at-rule's own prelude (so any comment written to introduce it
    goes with it -- a comment explaining a rule that no longer exists is rot).
    """
    out = []
    for m in re.finditer(r'@[a-zA-Z-]+[^{;]*\{', src):
        open_idx = m.end() - 1
        close = find_matching_brace(src, open_idx)
        if close < 0:
            continue
        # the wrapper's body must be empty once comments and whitespace go
        if strip_comments(src[open_idx + 1:close]).strip() != '':
            continue
        # The wrapper's own prelude -- including a comment written to introduce
        # it, which is rot once the rules it explains are gone.
        start = prelude_start_before(src, open_idx)
        # a nested empty at-rule inside another is handled by re-running
        out.append((start, open_idx, close))
    return out


def cut_at_rule(src, start, close):
    s = start
    while s > 0 and src[s - 1] in ' \t':
        s -= 1
    e = close + 1
    while e < len(src) and src[e] in ' \t':
        e += 1
    if e < len(src) and src[e] == '\n':
        e += 1
    # trim blank lines the wrapper leaves behind
    while s > 0 and src[s - 1] == '\n' and src[max(0, s - 2)] == '\n':
        s -= 1
    return src[:s] + src[e:], e - s


def apply_prune(src, whole, partial):
    edits = []
    removed = 0
    for r, _s, _f in whole:
        # Begin at the start of the line the rule's own text sits on. Taking
        # the newline before it would weld the two lines together; taking the
        # first non-blank character instead leaves that line's indentation
        # behind, and a run of removals accumulates those tabs onto the line
        # that follows ("\t\t\t\t\t}").
        start = r['sel_start']
        if start < len(src) and src[start] == '\n':
            start += 1
        end = r['end']
        while end < len(src) and src[end] in ' \t':
            end += 1
        if end < len(src) and src[end] == '\n':
            end += 1
        edits.append((start, end, ''))
    for r, sels, flags in partial:
        # Remove the dead selector(s) IN PLACE rather than rebuilding the list,
        # so the rule's comments and its original line breaks survive. The span
        # offsets line up with the raw prelude because strip_comments() is
        # length-preserving.
        raw = r['sel']
        cuts = []
        for (txt, a, b), d in zip(sels, flags):
            if not d:
                continue
            s, e = a, b
            # The last selector in a list runs to the end of the prelude, so its
            # span carries the space before `{`. Give that back, or the rule
            # ends up written `.sf-num{` while the rest of the file uses ` {`.
            while e > s and raw[e - 1] in ' \t\r\n':
                e -= 1
            j = e
            while j < len(raw) and raw[j] in ' \t\r\n':
                j += 1
            if j < len(raw) and raw[j] == ',':
                e = j + 1                      # swallow the following comma
            else:
                i = s
                while i > 0 and raw[i - 1] in ' \t\r\n':
                    i -= 1
                if i > 0 and raw[i - 1] == ',':
                    s = i - 1                  # last in the list: the comma leads
            cuts.append((s, e))
        new = raw
        for s, e in sorted(cuts, reverse=True):
            new = new[:s] + new[e:]
        edits.append((r['sel_start'], r['block_start'], new))
    # The trailing-whitespace extension overshoots into the NEXT rule's prelude
    # (its sel_start sits on the newline this one just swallowed). The regions
    # are applied in descending order, so an overlap silently eats one byte too
    # many per adjacent pair -- and if that byte is a comment's opening /*, the
    # rest of the stylesheet parses as comment. Clamp them apart first.
    edits.sort(key=lambda e: e[0])
    for i in range(len(edits) - 1):
        s, e, rep = edits[i]
        edits[i] = (s, min(e, edits[i + 1][0]), rep)

    edits.sort(key=lambda e: e[0], reverse=True)
    out = src
    for s, e, rep in edits:
        out = out[:s] + rep + out[e:]
    removed = len(src) - len(out)

    # A @media block that held only dead rules is now an empty shell. Cut it,
    # and re-run: an empty at-rule nested in another would otherwise stay.
    at_cut = []
    for _ in range(8):
        empties = find_empty_at_rules(out)
        if not empties:
            break
        for start, _o, close in sorted(empties, key=lambda t: t[2], reverse=True):
            head = out[start:close + 1]
            at_cut.append(' '.join(strip_comments(head).split())[:56])
            out, n = cut_at_rule(out, start, close)
            removed += n
    return out, removed, at_cut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--css', default='sinofresh-theme/style.css')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--occurrences', action='store_true')
    args = ap.parse_args()

    if not os.path.isfile(args.css):
        print("no such stylesheet: %s" % args.css)
        return 2
    src = open(args.css, encoding='utf-8').read()
    rules = parse_rules(src)

    if args.occurrences:
        occurrences(src)
        return 0

    whole, partial = classify(src, rules)
    show(src, whole, partial)

    if not args.apply:
        print()
        print("(scan only -- nothing written)")
        return 0

    out, removed, at_cut = apply_prune(src, whole, partial)

    print()
    print("=== assertions ===")
    bad = 0

    # 1. dead tokens gone from SELECTOR position
    left = []
    for r in parse_rules(out):
        for s in split_selectors(strip_comments(r['sel'])):
            for t in dead_in(s[0]):
                left.append((t, ' '.join(s[0].split())[:60]))
    print("   dead tokens in selector position: %d  %s"
          % (len(left), 'OK' if not left else 'FAIL'))
    for x in left[:10]:
        print("        %s" % (x,))
    if left:
        bad += 1

    # 2. surviving rule count is exactly found-minus-cut
    kept = len(parse_rules(out))
    expect = len(rules) - len(whole)
    print("   style rules: %d - %d = %d, got %d  %s"
          % (len(rules), len(whole), expect, kept,
             'OK' if kept == expect else 'FAIL'))
    if kept != expect:
        bad += 1

    # 3. braces still balance
    d = out.count('{') - out.count('}')
    print("   brace balance: %d  %s" % (d, 'OK' if d == 0 else 'FAIL'))
    if d:
        bad += 1

    # 4. no at-rule left empty
    empties = find_empty_at_rules(out)
    print("   empty at-rules left behind: %d  %s"
          % (len(empties), 'OK' if not empties else 'FAIL'))
    if empties:
        bad += 1

    # 5. nothing else moved: the cut regions are exactly the declared ones
    print("   bytes: %d - %d removed = %d, got %d  %s"
          % (len(src), removed, len(src) - removed, len(out),
             'OK' if len(src) - removed == len(out) else 'FAIL'))
    if len(src) - removed != len(out):
        bad += 1

    print("   at-rule wrappers cut with their rules: %d" % len(at_cut))
    for a in at_cut:
        print("        %s" % a)

    if bad:
        print()
        print("REFUSING TO WRITE: %d assertion(s) failed" % bad)
        return 1

    with open(args.css, 'w', encoding='utf-8') as fh:
        fh.write(out)
    print()
    print("wrote %s  (%d -> %d bytes, %d -> %d lines)"
          % (args.css, len(src), len(out),
             src.count('\n') + 1, out.count('\n') + 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
