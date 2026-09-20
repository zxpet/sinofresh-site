#!/usr/bin/env python3
"""Batch 2 / stop 1 — homepage rhythm pass.

Per top-level section of templates/front-page.html:
  1. surface rhythm  : paper / mist alternating bands with explicit px padding
  2. alignment       : the approved left / centre list (display vs. informational)
  3. eyebrow labels  : 12px uppercase category label above each H2
  4. card system     : three treatments replacing the "white rounded box" reflex
                       - sf-tile   hairline tile (product grid)
                       - sf-card   hairline card (bordered box)
                       - sf-cell   ruled cell inside a gapless sf-panel
  5. slot compaction : shrinks the pending-asset placeholders

Only presentation attributes are touched. No block is added, removed or
reordered and no existing copy is rewritten. The eyebrow label is new copy but
was explicitly approved.

Every call passes skip_first=True: the first group opener inside a section span
IS that section, and several sections share the background colour of their own
cards — without the guard they would rewrite themselves.
"""
import datetime
import json
import re
import shutil
import sys

SP = re.compile(r"<!-- wp:group(?: (\{.*?\}))? *-->|<!-- /wp:group *-->")
OPEN_RE = re.compile(
    r'<!-- wp:group (?P<attrs>\{.*?\}) -->\s*<(?P<tag>div|section) class="(?P<cls>[^"]*)"(?P<rest>[^>]*)>'
)
COMMENT_RE = re.compile(r"<!-- wp:[a-z0-9/-]+(?: (\{.*?\}))? */?-->")
BG_TOKEN = re.compile(r"has-[a-z0-9-]+-background-color")
BORDER_TOKEN = re.compile(r"has-[a-z0-9-]+-border-color")

CARD_DROP_STYLE = ("background-color", "border-radius", "border-width", "border-color", "border-style", "padding")
CARD_DROP_ATTR = ("style.border.radius", "style.border.width", "style.border.color", "style.spacing.padding")


# ---------------------------------------------------------------- plumbing
def top_spans(text):
    depth = 0
    starts = []
    for m in SP.finditer(text):
        if m.group(0).startswith("<!-- /"):
            depth -= 1
        else:
            if depth == 0:
                starts.append(m.start())
            depth += 1
    starts.append(len(text))
    return [(starts[i], starts[i + 1]) for i in range(len(starts) - 1)]


def clean_style(style, drop):
    out = []
    for decl in style.split(";"):
        decl = decl.strip()
        if not decl:
            continue
        prop = decl.split(":")[0].strip()
        if any(prop == d or prop.startswith(d + "-") for d in drop):
            continue
        out.append(decl)
    return ";".join(out)


def del_path(obj, path):
    cur = obj
    keys = path.split(".")
    for k in keys[:-1]:
        if not isinstance(cur, dict) or k not in cur:
            return
        cur = cur[k]
    if isinstance(cur, dict):
        cur.pop(keys[-1], None)


def prune_empty(obj):
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            prune_empty(obj[k])
            if obj[k] in ({}, []) or obj[k] is None:
                obj.pop(k)
    return obj


def comment(name, attrs):
    if not attrs:
        return f"<!-- {name} -->"
    return "<!-- " + name + " " + json.dumps(attrs, separators=(",", ":"), ensure_ascii=False) + " -->"


def rewrite_card_opener(opener, new_class, drop_style=(), drop_attr=(), drop_bg=False, expect_bg=None):
    m = OPEN_RE.match(opener)
    if not m:
        raise AssertionError("opener did not match:\n" + opener[:160])
    attrs = json.loads(m.group("attrs"))
    bg = attrs.get("backgroundColor")
    if expect_bg and bg != expect_bg:
        raise AssertionError(f"expected bg={expect_bg}, found {bg}")
    if drop_bg:
        attrs.pop("backgroundColor", None)
    for path in drop_attr:
        del_path(attrs, path)
    if new_class:
        attrs["className"] = new_class
    prune_empty(attrs)

    toks = m.group("cls").split()
    if drop_bg:
        toks = [t for t in toks if not (BG_TOKEN.fullmatch(t) or t == "has-background")]
    if any(d.startswith("border") for d in drop_style):
        toks = [t for t in toks if t != "has-border-color" and not BORDER_TOKEN.fullmatch(t)]
    if new_class:
        toks.extend(new_class.split())
    rest = m.group("rest")
    if drop_style:
        def sub(mm):
            cleaned = clean_style(mm.group(1), drop_style)
            return f'style="{cleaned}"' if cleaned else ""
        rest = re.sub(r'\s*style="([^"]*)"', sub, rest)
    return f'{comment("wp:group", attrs)}<{m.group("tag")} class="{" ".join(toks)}"{rest}>'


def restyle_cards(body, match_bg, new_class, drop_bg=True, drop_style=CARD_DROP_STYLE,
                  drop_attr=CARD_DROP_ATTR, expect=None, require_padding=False):
    hits = []
    for idx, m in enumerate(OPEN_RE.finditer(body)):
        if idx == 0:          # the section itself
            continue
        op = m.group(0)
        attrs = json.loads(OPEN_RE.match(op).group("attrs"))
        if attrs.get("backgroundColor") != match_bg:
            continue
        if attrs.get("className"):
            continue
        if require_padding and "padding" not in json.dumps(attrs):
            continue
        hits.append((m.start(), m.end(), rewrite_card_opener(
            op, new_class, drop_style=drop_style, drop_attr=drop_attr, drop_bg=drop_bg, expect_bg=match_bg)))
    if expect is not None and len(hits) != expect:
        raise AssertionError(f"{new_class}: expected {expect} matches, got {len(hits)}")
    for a, b, new in reversed(hits):
        body = body[:a] + new + body[b:]
    return body, len(hits)


# ---------------------------------------------------------------- alignment
CENTER_RE = re.compile(r'<!-- (wp:(?:heading|paragraph)) (\{[^>]*?"(?:textAlign|align)":"center"[^>]*?\}) -->')


def strip_center(body):
    def fix(m):
        name, raw = m.group(1), m.group(2)
        remaining = re.sub(r',?"(?:textAlign|align)":"center"', "", raw)
        remaining = remaining.replace("{,", "{").replace(",}", "}")
        remaining = remaining.strip().rstrip(",").strip()
        return f"<!-- {name} -->" if remaining in ("", "{}") else f"<!-- {name} {remaining} -->"

    body = CENTER_RE.sub(fix, body)
    body = re.sub(r'(class="[^"]*?)\bhas-text-align-center ?', r"\1", body)
    body = re.sub(r'(class="[^"]*?)\s+"', r'\1"', body)
    body = re.sub(r'\s+class=""', "", body)
    return body


def unalign_right(body):
    def fix(m):
        raw = m.group(1)
        remaining = re.sub(r',?"align":"right"', "", raw)
        remaining = remaining.replace("{,", "{").replace(",}", "}").strip().rstrip(",").strip()
        return "<!-- wp:paragraph -->" if remaining in ("", "{}") else f"<!-- wp:paragraph {remaining} -->"

    body = re.sub(r'<!-- (wp:paragraph) (\{[^>]*?"align":"right"[^>]*?\}) -->', fix, body)
    body = re.sub(r'(class="[^"]*?)\bhas-text-align-right ?', r"\1", body)
    body = re.sub(r'(class="[^"]*?)\s+"', r'\1"', body)
    body = re.sub(r'\s+class=""', "", body)
    return body


def _centre_comment(tag, body):
    m = re.search(r'<!-- wp:' + tag + r' -->(\s*)<p class="([^"]*?)">', body) if tag == "paragraph" else None
    return m


def add_center(body):
    """Centre the section H2 and the intro paragraph that follows it."""
    n1 = 0
    m = re.search(r'<!-- wp:heading -->(\s*)<h2 class="wp-block-heading">', body)
    if m:
        body = (body[:m.start()] + '<!-- wp:heading {"textAlign":"center"} -->' + m.group(1)
                + '<h2 class="wp-block-heading has-text-align-center">' + body[m.end():])
        n1 = 1
    n2 = 0
    m = re.search(r'<!-- wp:paragraph (\{[^>]*?"textColor":"text-secondary"[^>]*?\}) -->(\s*)<p class="(has-text-secondary-color[^"]*)">', body)
    if m and '"align"' not in m.group(1):
        new = m.group(1)[:-1].rstrip()
        new = new + (',"align":"center"}' if '"spacing"' not in new else ',"align":"center"}')
        body = (body[:m.start()] + "<!-- wp:paragraph " + new + " -->" + m.group(2)
                + '<p class="has-text-align-center ' + m.group(3) + '">' + body[m.end():])
        n2 = 1
    return body, n1, n2


def insert_eyebrow(body, text, centred=False):
    m = re.search(r"<!-- wp:heading", body)
    if not m:
        raise AssertionError("no heading found for eyebrow")
    if centred:
        block = ('<!-- wp:paragraph {"align":"center","className":"sf-eyebrow"} -->\n'
                 f'<p class="has-text-align-center sf-eyebrow">{text}</p>\n<!-- /wp:paragraph -->\n')
    else:
        block = ('<!-- wp:paragraph {"className":"sf-eyebrow"} -->\n'
                 f'<p class="sf-eyebrow">{text}</p>\n<!-- /wp:paragraph -->\n')
    return body[:m.start()] + block + body[m.start():]


def set_section_shell(body, bg=None, pad=None, expect_bg=None):
    m = re.match(r"<!-- wp:group (\{.*?\}) -->\s*<(?:div|section)[^>]*>", body, re.S)
    if not m:
        raise AssertionError("section opener not found")
    attrs = json.loads(m.group(1))
    if expect_bg and attrs.get("backgroundColor") != expect_bg:
        raise AssertionError(f"section bg: expected {expect_bg}, got {attrs.get('backgroundColor')}")
    if bg:
        attrs["backgroundColor"] = bg
    if pad:
        top, bot = pad
        attrs.setdefault("style", {}).setdefault("spacing", {})["padding"] = {"top": f"{top}px", "bottom": f"{bot}px"}
    open_tag = re.search(r"<(?:div|section)[^>]*>", m.group(0)).group(0)
    if bg:
        open_tag = BG_TOKEN.sub(f"has-{bg}-background-color", open_tag)
    if pad:
        top, bot = pad

        def fix_style(mm):
            cleaned = clean_style(mm.group(1), ("padding",))
            kept = (cleaned + ";") if cleaned else ""
            return f'style="{kept}padding-top:{top}px;padding-bottom:{bot}px"'

        open_tag = re.sub(r'style="([^"]*)"', fix_style, open_tag)
    return comment("wp:group", attrs) + "\n" + open_tag + body[m.end():]


def audit(text, tag):
    problems = []
    for m in COMMENT_RE.finditer(text):
        if not m.group(1):
            continue
        try:
            json.loads(m.group(1))
        except Exception as e:
            problems.append(f"{tag}: bad JSON near {text[max(0, m.start() - 60):m.start() + 40]!r} -> {e}")
    if text.count("<!-- wp:group") != text.count("<!-- /wp:group -->"):
        problems.append(f"{tag}: unbalanced groups ({text.count('<!-- wp:group')} / {text.count('<!-- /wp:group -->')})")
    return problems


# ---------------------------------------------------------------- the plan
PAD_STD, PAD_HERO, PAD_STRIP = (48, 48), (56, 56), (40, 40)

PLAN = {
    0:  ("primary",    "left",   None,                PAD_HERO),
    1:  ("bg-light",   "left",   None,                PAD_STD),
    2:  ("card-white", "center", "Product range",     PAD_STD),
    3:  ("bg-light",   "left",   "Formula standards", PAD_STRIP),
    4:  ("card-white", "center", "Compliance",        PAD_STD),
    5:  ("bg-light",   "left",   "Quality system",    PAD_STD),
    6:  ("card-white", "left",   "Engagement types",  PAD_STD),
    7:  ("bg-light",   "center", "Partnership",       PAD_STD),
    8:  ("card-white", "left",   "Process",           PAD_STD),
    9:  ("bg-light",   "center", "Feedback",          PAD_STD),
    10: ("card-white", "left",   "Export footprint",  PAD_STD),
    11: ("bg-light",   "left",   "Company",           PAD_STD),
    12: ("card-white", "center", "Insights",          PAD_STD),
    13: ("bg-light",   "left",   "FAQ",               PAD_STD),
    14: ("primary",    "left",   "Next step",         PAD_HERO),
}


def swap(body, old, new, count=0, note=None):
    if old not in body:
        raise AssertionError(f"swap target missing: {note or old[:80]}")
    return body.replace(old, new) if count == 0 else body.replace(old, new, count)


def run(path):
    text = open(path, encoding="utf-8").read()
    spans = top_spans(text)
    if len(spans) != 15:
        raise SystemExit(f"expected 15 top-level sections, found {len(spans)}")

    shutil.copyfile(path, f"{path}.bak-{datetime.datetime.now():%H%M%S}")
    report = []
    out = []

    for i, (a, b) in enumerate(spans):
        raw = text[a:b]
        surface, align, eyebrow, pad = PLAN[i]
        body = set_section_shell(raw, bg=surface, pad=pad)

        # ---------------------------------------------------- card treatment
        if i == 2:
            body = strip_center(body)
            body = unalign_right(body)
            body, n = restyle_cards(body, "bg-light", "sf-tile", expect=8)
            report.append(("2  dosage tiles            ", n))
            body = swap(body,
                        '<!-- wp:image {"align":"center"} -->',
                        '<!-- wp:image {"align":"center","className":"sf-tile__media"} -->')
            body = swap(body, '<figure class="wp-block-image aligncenter">',
                        '<figure class="wp-block-image aligncenter sf-tile__media">')
            body, n1, n2 = add_center(body)
            report.append(("2  headline centred        ", n1 + n2))

        elif i == 3:
            body = strip_center(body)
            body = swap(body,
                        '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->',
                        '<!-- wp:columns {"className":"sf-strip","style":{"spacing":{"margin":{"top":"24px"}}}} -->')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                        '<div class="wp-block-columns sf-strip" style="margin-top:24px">')
            report.append(("3  compliance strip        ", "ok"))

        elif i == 4:
            body, n1, n2 = add_center(body)
            body, n3 = restyle_cards(body, "card-white", "sf-card", expect=4)
            body, n4 = restyle_cards(body, "bg-light", "sf-slot sf-slot--document",
                                     drop_style=("background-color", "border-radius", "padding"),
                                     drop_attr=("style.border.radius", "style.spacing.padding"), expect=4)
            report.append(("4  cert cards / slots      ", n3, n4, "centred", n1 + n2))

        elif i == 5:
            body = strip_center(body)
            body = swap(body,
                        '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->',
                        '<!-- wp:columns {"className":"sf-panel sf-panel--3","style":{"spacing":{"margin":{"top":"32px"}}}} -->')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--60)">',
                        '<div class="wp-block-columns sf-panel sf-panel--3" style="margin-top:32px">')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                        '<div class="wp-block-columns sf-panel sf-panel--3">')
            body = swap(body, '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->',
                        '<!-- wp:columns {"className":"sf-panel sf-panel--3"} -->')
            body, n1 = restyle_cards(body, "card-white", "sf-cell",
                                     drop_style=("background-color", "border-radius", "padding"),
                                     drop_attr=("style.border.radius", "style.spacing.padding"), expect=6)
            body, n2 = restyle_cards(body, "bg-light", "sf-slot sf-slot--photo",
                                     drop_style=("background-color", "border-radius", "padding"),
                                     drop_attr=("style.border.radius", "style.spacing.padding"), expect=6)
            report.append(("5  QC cells / photo slots  ", n1, n2))

        elif i == 6:
            body = strip_center(body)
            body, n = restyle_cards(body, "bg-light", "sf-card sf-card--roomy", expect=2)
            report.append(("6  OEM panels              ", n))

        elif i == 7:
            body = strip_center(body)
            body = swap(body, '"margin":{"top":"var:preset|spacing|60"}', '"margin":{"top":"32px"}')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--60)">',
                        '<div class="wp-block-columns" style="margin-top:32px">')
            body = swap(body, '"margin":{"top":"var:preset|spacing|40"}', '"margin":{"top":"20px"}')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                        '<div class="wp-block-columns" style="margin-top:20px">')
            body, n = restyle_cards(body, "card-white", "sf-card sf-card--roomy", expect=6)
            report.append(("7  cooperation cards       ", n))

        elif i == 8:
            body = strip_center(body)
            body = swap(body,
                        '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->',
                        '<!-- wp:columns {"className":"sf-panel sf-panel--4 sf-panel--bare","style":{"spacing":{"margin":{"top":"32px"}}}} -->')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--60)">',
                        '<div class="wp-block-columns sf-panel sf-panel--4 sf-panel--bare" style="margin-top:32px">')
            body = swap(body, '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->',
                        '<!-- wp:columns {"className":"sf-panel sf-panel--4 sf-panel--bare"} -->')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                        '<div class="wp-block-columns sf-panel sf-panel--4 sf-panel--bare">')
            body, n = restyle_cards(body, None, "sf-cell",
                                    drop_style=("padding",), drop_attr=("style.spacing.padding",),
                                    require_padding=True, expect=7)
            report.append(("8  process cells           ", n))

        elif i == 9:
            body = strip_center(body)
            body = swap(body, '"width":"96px","height":"96px"', '"width":"64px","height":"64px"')
            body = swap(body, 'width:96px;height:96px', 'width:64px;height:64px')
            body, n = restyle_cards(body, "card-white", "sf-card sf-card--quote",
                                    drop_bg=False, expect=6)
            report.append(("9  quote cards             ", n))

        elif i == 10:
            body = strip_center(body)
            body = swap(body,
                        '<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->',
                        '<!-- wp:columns {"className":"sf-panel sf-panel--4","style":{"spacing":{"margin":{"top":"24px"}}}} -->')
            body = swap(body, '<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                        '<div class="wp-block-columns sf-panel sf-panel--4" style="margin-top:24px">')
            body, n1 = restyle_cards(body, "card-white", "sf-cell", expect=4)
            body, n2 = restyle_cards(body, "bg-light", "sf-slot sf-slot--map",
                                     drop_style=("background-color", "border-radius", "min-height"),
                                     drop_attr=("style.border.radius", "style.dimensions.minHeight"), expect=1)
            report.append(("10 export cells / map slot ", n1, n2))

        elif i == 11:
            body, n = restyle_cards(body, "primary", "sf-slot sf-slot--video",
                                    drop_style=("border-radius", "min-height"),
                                    drop_attr=("style.border.radius", "style.dimensions.minHeight"), expect=1)
            report.append(("11 video slot              ", n))

        elif i == 12:
            body = strip_center(body)
            body, n1, n2 = add_center(body)
            body, n3 = restyle_cards(body, "card-white", "sf-card sf-card--flush",
                                     drop_style=("border-radius", "border-width", "border-color", "border-style"),
                                     drop_attr=("style.border.radius", "style.border.width", "style.border.color"),
                                     drop_bg=False, expect=3)
            report.append(("12 article cards           ", n3, "centred", n1 + n2))

        elif i == 13:
            body = strip_center(body)
            body = body.replace('"margin":{"top":"var:preset|spacing|30"}', '"margin":{"top":"0px"}')
            body = body.replace('style="margin-top:var(--wp--preset--spacing--30)"', 'style="margin-top:0px"')
            body = body.replace('"spacing":{"margin":{"top":"var:preset|spacing|60"}}', '"spacing":{"margin":{"top":"28px"}}')
            body = body.replace('style="margin-top:var(--wp--preset--spacing--60)"', 'style="margin-top:28px"')
            body = body.replace('"margin":{"bottom":"var:preset|spacing|30"}', '"margin":{"bottom":"16px"}')
            body = body.replace('margin-bottom:var(--wp--preset--spacing--30)', 'margin-bottom:16px')
            body = body.replace('<div class="wp-block-group" style="margin-top:28px">',
                                '<div class="wp-block-group sf-faq" style="margin-top:28px">')
            body = body.replace('{"style":{"spacing":{"margin":{"top":"28px"}}},"layout":{"type":"constrained","contentSize":"800px"}}',
                                '{"className":"sf-faq","style":{"spacing":{"margin":{"top":"28px"}}},"layout":{"type":"constrained","contentSize":"800px"}}')
            report.append(("13 FAQ rows compacted      ", "ok"))

        # ------------------------------------------------ alignment + label
        if align == "left":
            body = strip_center(body)
            if eyebrow:
                body = insert_eyebrow(body, eyebrow)
                report.append((f"{i:2} eyebrow  {eyebrow}", ""))
        elif align == "center":
            # display sections: re-centre H2 + intro (strip_center above removed it
            # where the card pass needed left-aligned tile copy)
            body, n1, n2 = add_center(body)
            if eyebrow:
                body = insert_eyebrow(body, eyebrow, centred=True)
            report.append((f"{i:2} eyebrow  {eyebrow} (centred)", n1 + n2))

        out.append(body)

    new = "".join(out)
    # radius: everything that still says 8px becomes the unified 6px
    new = new.replace('"radius":"8px"', '"radius":"6px"').replace("border-radius:8px", "border-radius:6px")

    problems = audit(new, "after") + audit(text, "before")
    if problems:
        print("\n".join(problems))
        raise SystemExit("audit failed — nothing written")
    for tag in ("<h1", "<h2", "<h3", "<a ", "wp:group", "wp:columns"):
        if new.count(tag) != text.count(tag):
            raise SystemExit(f"{tag} count changed: {text.count(tag)} -> {new.count(tag)}")
    if new.count("sf-eyebrow") != text.count("sf-eyebrow") + 26:
        raise SystemExit(f"expected 13 new eyebrow paragraphs, found {new.count('sf-eyebrow') - text.count('sf-eyebrow')}")

    open(path, "w", encoding="utf-8").write(new)
    print(f"written {path}: {len(text)} -> {len(new)} bytes, {text.count(chr(10))} -> {new.count(chr(10))} lines\n")
    for row in report:
        print("   ", *row)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "templates/front-page.html")
