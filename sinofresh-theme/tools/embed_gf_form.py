#!/usr/bin/env python3
"""Replace Inquiry Form placeholder group with Gravity Forms block reference (atomic, line-based)."""

PATH = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates/front-page.html"
GF_BLOCK = '<!-- wp:gravityforms/form {"formId":"2","title":false,"description":false,"ajax":true} /-->'

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Locate via placeholder text, then walk up to the nearest enclosing group comment
texts = [i for i, l in enumerate(lines) if "表单嵌入区 / Form goes here" in l]
assert len(texts) == 1, f"expected 1 placeholder text, got {len(texts)}"
start = None
for i in range(texts[0], -1, -1):
    if lines[i].startswith("<!-- wp:group {"):
        start = i
        break
assert start is not None, "enclosing group comment not found"
assert '"minHeight":"400px"' in lines[start], f"group at line {start+1} is not the 400px placeholder: {lines[start]!r}"

# Its closing tag: first '<!-- /wp:group -->' after start (group contains no nested groups)
end = None
for i in range(start + 1, len(lines)):
    if lines[i].strip() == "<!-- /wp:group -->":
        end = i
        break
assert end is not None, "closing group tag not found"

# Safety: ensure the range contains the placeholder texts and no other groups
seg = "".join(lines[start:end])
assert "表单嵌入区 / Form goes here" in seg, "placeholder text not inside range"
assert "下一步安装 Gravity Forms 后嵌入实际表单" in seg, "note text not inside range"
assert "<!-- wp:group " not in "".join(lines[start + 1:end]), "unexpected nested group inside placeholder range"

new_lines = lines[:start] + [GF_BLOCK + "\n"] + lines[end + 1:]

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Verification
with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()
checks = {
    "GF block": content.count(GF_BLOCK),
    "old placeholder text": content.count("表单嵌入区 / Form goes here"),
    "old note text": content.count("下一步安装 Gravity Forms 后嵌入实际表单"),
    "old minHeight 400px": content.count("min-height:400px"),
    "white card kept": content.count('has-card-white-background-color has-background" style="border-radius:8px;padding-top:var(--wp--preset--spacing--40)'),
    "H2 title intact": content.count("Ready to Launch Your Product?"),
    "trust items intact": sum(content.count(t) for t in ["24-hour response on business days", "Formula and branding stay confidential", "Small trial orders welcome"]),
    "wp:group balance": content.count("<!-- wp:group ") - content.count("<!-- /wp:group -->"),
    "wp:columns balance": content.count("<!-- wp:columns ") - content.count("<!-- /wp:columns -->"),
    "wp:paragraph balance": content.count("<!-- wp:paragraph ") - content.count("<!-- /wp:paragraph -->"),
    "footer comment": content.count('<!-- wp:group {"tagName":"footer"'),
}
for k, v in checks.items():
    print(f"{k}: {v}")
print("total lines:", len(new_lines))
