"""Dump the block skeleton of a WP block-theme template.

Block comments in serialized templates look like:
    <!-- wp:group {"a":1} -->      opening
    <!-- wp:template-part {"a":1} /-->   self-closing
    <!-- /wp:group -->            closing
There is NO namespace slash in the serialized name (unlike the PHP form core/group).
"""
import re
import sys

OPEN = re.compile(r"<!-- (wp:[a-z0-9-]+)(?: (\{.*?\}))? */?-->|<!-- /(wp:[a-z0-9-]+) *-->")
GROUP_TOK = re.compile(r"<!-- wp:group(?: (\{.*?\}))? *-->|<!-- /wp:group *-->")


def top_level_spans(s, name="group"):
    """Spans of top-level (depth 0) blocks of the given type."""
    depth = 0
    out = []
    for m in GROUP_TOK.finditer(s):
        if m.group(0).startswith("<!-- /"):
            depth -= 1
        else:
            if depth == 0:
                out.append((m.start(), m.group(1) or ""))
            depth += 1
    spans = []
    for i, (pos, attrs) in enumerate(out):
        end = out[i + 1][0] if i + 1 < len(out) else len(s)
        spans.append((pos, end, attrs))
    return spans


def skeleton(body, max_depth=3, hide=(("wp:paragraph", 1),)):
    lines = []
    depth = 0
    for m in OPEN.finditer(body):
        if m.group(3):  # closing
            depth -= 1
            continue
        name = m.group(1)
        attrs = m.group(2) or ""
        if depth > max_depth:
            depth += 1
            continue
        skip = any(name == n and depth > d for n, d in hide)
        if skip:
            depth += 1
            continue
        bits = []
        bg = re.search(r'"backgroundColor":"([^"]*)"', attrs)
        cl = re.search(r'"className":"([^"]*)"', attrs)
        rad = re.search(r'"radius":"([^"]*)"', attrs)
        pad = re.search(r'"padding":\{"top":"([^"]*)"', attrs)
        for label, val in (("bg", bg), (".", cl), ("r", rad), ("pad", pad)):
            if val:
                bits.append(label + "=" + val.group(1))
        lines.append("  " * depth + name.replace("wp:", "") + ("  [" + ", ".join(bits) + "]" if bits else ""))
        depth += 1
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "templates/front-page.html"
    s = open(path, encoding="utf-8").read()
    spans = top_level_spans(s)
    only = [int(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else None
    print("top-level groups:", len(spans))
    for i, (a, b, attrs) in enumerate(spans):
        if only and i not in only:
            continue
        h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", s[a:b], re.S)
        title = re.sub(r"<[^>]+>", "", h2[0]).strip() if h2 else "(no h2)"
        print("\n" + "=" * 68)
        print(f"### [{i}] {title}    lines={s[a:b].count(chr(10))}")
        print(skeleton(s[a:b]))
