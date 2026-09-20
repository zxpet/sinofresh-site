"""Inventory: which card-group openers occur inside which top-level section."""
import re
import sys
import collections

path = sys.argv[1] if len(sys.argv) > 1 else "templates/front-page.html"
s = open(path, encoding="utf-8").read()

TOK = re.compile(r"<!-- wp:group(?: (\{.*?\}))? *-->|<!-- /wp:group *-->")
OPEN2 = re.compile(r"<!-- wp:group(?: \{[^>]*?\})? -->\s*<(?:div|section)[^>]*>")


def spans(text):
    d = 0
    out = []
    for m in TOK.finditer(text):
        if m.group(0).startswith("<!-- /"):
            d -= 1
        else:
            if d == 0:
                out.append(m.start())
            d += 1
    out.append(len(text))
    return [(out[i], out[i + 1]) for i in range(len(out) - 1)]


def label(op):
    """Short human label for a group opener."""
    attrs = op.split("-->")[0]
    bits = []
    bg = re.search(r'"backgroundColor":"([^"]*)"', attrs)
    if bg:
        bits.append(bg.group(1))
    if "minHeight" in attrs:
        bits.append("minH" + re.search(r'"minHeight":"([^"]*)"', attrs).group(1).replace("px", ""))
    if '"width":"96px"' in attrs:
        bits.append("circle96")
    if "aspectRatio" in attrs:
        bits.append("ar" + re.search(r'"aspectRatio":"([^"]*)"', attrs).group(1))
    if '"flex"' in attrs:
        bits.append("flex")
    pad = re.findall(r'"padding":\{"top":"var:preset\|spacing\|(\d+)"', attrs)
    if pad:
        bits.append("pad" + pad[0])
    if "border-light" in attrs:
        bits.append("hairline")
    return "+".join(bits) or "plain"


for i, (a, b) in enumerate(spans(s)):
    body = s[a:b]
    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)
    title = re.sub(r"<[^>]+>", "", h2[0]).strip() if h2 else "(no h2)"
    c = collections.Counter(label(x) for x in OPEN2.findall(body))
    inner = {k: v for k, v in c.items() if k != "plain"}
    print(f"[{i:2}] {title[:46]:48} {dict(inner) if inner else '{}'}")
