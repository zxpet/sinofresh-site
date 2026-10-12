#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 h24b_audit_notifs.php 的 JSON 产出「表单通知：字段 ↔ 占位符 ↔ 渲染值」对照表文档。

输入：/tmp/na-<fid>.json（每个表单**独立进程**跑出来的，避免 FF 静态缓存污染）
输出：docs/form-notification-fields-2026-10-12.md
"""
import json
import os
import sys

FORMS = [8, 9, 10, 11, 12]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "form-notification-fields-2026-10-12.md")
GEN_AT = "2026-10-12"
FIXED_AT = "2026-10-12"

TITLES = {
    8: ("Get a Quote", "报价询盘（网站主表单）"),
    9: ("Request a Sample", "样品申请"),
    10: ("Book a Factory Tour", "工厂参观预约"),
    11: ("Request COA", "合规文件（COA）索取"),
    12: ("Feedback", "反馈"),
}

data = {}
for fid in FORMS:
    p = "/tmp/na-%d.json" % fid
    if not os.path.isfile(p):
        print("缺少 %s" % p)
        sys.exit(1)
    data[fid] = json.load(open(p, encoding="utf-8"))["forms"][0]

lines = []
w = lines.append

w("# 表单通知「字段 ↔ 占位符 ↔ 渲染值」对照表")
w("")
w("> 站点：生产 www.zxpet.com ｜ 生成日期：%s ｜ 生成工具：`tools/h24b_audit_notifs.php` + `tools/h24b_build_field_map.py`" % GEN_AT)
w("> ")
w("> **数据来源**：直接读 `wp_fluentform_forms.form_fields` 与 `wp_fluentform_form_meta(meta_key=notifications)`，只读。")
w("> **渲染值**用**构造样本**跑 FF 自己的 `ShortCodeParser`（邮件分支 `isHtml=true`），**不含任何真实客户数据**；")
w("> 样本中 `«公司名»` 这类尖括号值 = 该字段的标签占位符，代表「这里会填访客输入的内容」。")
w("> ")
w("> ⚠️ 逐表单独立进程执行 —— FF 把字段定义缓存在静态属性里，同一进程连续渲染多个表单会串（见文末「踩坑」）。")
w("")
w("---")
w("")

# ---------------------------------------------------------------- 总览
w("## 0. 总览")
w("")
w("| 表单 | form_id | 字段数 | 通知 feed | 自动回复状态 |")
w("|---|---|---|---|---|")
for fid in FORMS:
    fm = data[fid]
    auto = [f for f in fm["feeds"] if "Auto Reply" in f["name"]]
    if auto:
        a = auto[0]
        state = "**开启**" if a["enabled"] else "已停用"
    else:
        state = "无此 feed"
    w("| %s | %d | %d | %s | %s |"
      % (fm["title"], fid, len(fm["fields"]),
         " / ".join(f["name"] for f in fm["feeds"]), state))
w("")
w("> 管理员通知一律发往 `sales@zxpet.com`；自动回复发往来访者填的邮箱。")
w("")
w("---")
w("")

# ---------------------------------------------------------------- 逐表单
for fid in FORMS:
    fm = data[fid]
    title, zh = TITLES.get(fid, (fm["title"], ""))
    w("## %d. form %d — %s（%s）" % (FORMS.index(fid) + 1, fid, title, zh))
    w("")

    # 字段清单
    w("### 字段清单（`{inputs.<key>}` 可用）")
    w("")
    w("| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |")
    w("|---|---|---|---|---|")
    for i, f in enumerate(fm["fields"], 1):
        w("| %d | `%s` | `%s` | %s | %d |" % (i, f["key"], f["element"], f["label"] or "（无标签）", len(f["opts"])))
    w("")

    # 每个 feed
    for fd in fm["feeds"]:
        en = fd["enabled"]
        en_txt = "启用" if en else "**已停用**"
        w("### %s — meta_id %d" % (fd["name"], fd["meta_id"]))
        w("")
        w("- 收件人：`%s`　·　状态：%s" % (fd["to"], en_txt))
        w("")
        w("**主题**")
        w("")
        w("```text")
        w(fd["subject_raw"])
        w("-- 渲染后 --")
        w(fd["subject_rendered"])
        w("```")
        w("")
        w("**正文模板**（原文；`<br />` 即换行）")
        w("")
        w("```html")
        for l in fd["message_raw"].split("<br />"):
            w(l.rstrip())
        w("```")
        w("")
        w("**正文渲染**（构造样本 → 邮件实际形态）")
        w("")
        w("```text")
        for l in fd["message_rendered"].split("\n"):
            w(l.rstrip())
        w("```")
        w("")
        if fd["lines"]:
            w("**占位符映射**")
            w("")
            w("| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |")
            w("|---|---|---|---|---|")
            for l in fd["lines"]:
                ph = ("{inputs.%s.value}" % l["key"]) if l["has_value"] else ("{inputs.%s}" % l["key"])
                elem = l["element"] or "**不存在**"
                lab = l["label"] or "—"
                ok = "✅" if (l["element"] and not (l["element"].find("checkbox") >= 0 and not l["has_value"])) else "⚠️"
                w("| %s | `%s` | %s | `%s` | %s |" % (l["prefix"][:38], ph, lab, elem, ok))
            w("")
        if fd["issues"]:
            w("**本次普查发现的问题**")
            w("")
            for i in fd["issues"]:
                w("- ⚠️ " + i)
            w("")
        else:
            w("✅ 未发现问题。")
            w("")
    w("---")
    w("")

# ---------------------------------------------------------------- 修复记录
w("## 5. 本次修复的 5 处「Privacy Consent」行（%s）" % FIXED_AT)
w("")
w("5 个表单的管理员通知里，这一行**全部是坏的**，三种坏法：")
w("")
w("| 表单 | feed | 改前 | 改后 | 症状 |")
w("|---|---|---|---|---|")
rows = [
    (8, 39, "`Privacy Consent: {inputs.company_name_1}`", "`Privacy Consent: {inputs.privacy_consent_11.value}`", "显示成公司名（本批单独修）"),
    (9, 45, "`Privacy Consent: {inputs.company_name_1}`", "`Privacy Consent: {inputs.privacy_consent_12.value}`", "显示成公司名"),
    (10, 51, "`Privacy Consent: {inputs.company_name_1}`", "`Privacy Consent: {inputs.privacy_consent_14.value}`", "显示成公司名"),
    (11, 57, "`Privacy Consent: {inputs.privacy_consent_9.i_agree_to_the_privacy_policy_9_1}`", "`Privacy Consent: {inputs.privacy_consent_9.value}`", "**完全空白**（孤儿 key）"),
    (12, 63, "`Privacy Consent: {inputs.privacy_consent_5.i_agree_to_the_privacy_policy_5_1}`", "`Privacy Consent: {inputs.privacy_consent_5.value}`", "**完全空白**（孤儿 key）"),
]
for r in rows:
    w("| form %d | meta_id %d | %s | %s | %s |" % r)
w("")
w("修复工具：`tools/h24b_fix_privacy_line.php`（自动发现隐私字段 / 逐表单备份 / 一条命令回滚）")
w("")

# ---------------------------------------------------------------- 同批另两项变更
w("## 6. 同批完成的另两项变更（%s）" % FIXED_AT)
w("")
w("### 6.1 自动回复（Auto Reply）全部停用")
w("")
w("form 8 在 H24 防护上线时已停用，本批把 **form 9 / 10 / 11 一并停用**（form 12 本就没有此 feed）：")
w("")
w("| 表单 | Auto Reply feed | 收件人 | 改前 | 改后 |")
w("|---|---|---|---|---|")
w("| form 8 | meta_id 40 | `{inputs.email_3}` | 已停用 | — |")
w("| form 9 | meta_id 46 | `{inputs.email_3}` | 启用 | **已停用** |")
w("| form 10 | meta_id 52 | `{inputs.email_4}` | 启用 | **已停用** |")
w("| form 11 | meta_id 58 | `{inputs.email_3}` | 启用 | **已停用** |")
w("")
w("判定依据（源码级）：`GlobalNotificationManager::getEnabledFeeds()` 里")
w("`ArrayHelper::isTrue($feed, 'enabled')` 是**唯一**发送开关；写成 `false` 即停用。")
w("用 FF 自己的这个函数实测：5 个管理员通知（39/45/51/57/63）仍然发送，4 个 Auto Reply（40/46/52/58）全部不再发送。")
w("")
w("修复工具：`tools/h24b_autoreply_toggle.php`（status / disable / restore，逐 feed 备份整行原始值）。")
w("**恢复时机**：等防护稳定 ≥1 周后 4 个一起恢复，恢复时统一加「仅非 spam 触发」守卫。")
w("")
w("### 6.2 form 11「Document Type」占位符补 `.value`")
w("")
w("| 表单 | feed | 改前 | 改后 | 症状 |")
w("|---|---|---|---|---|")
w("| form 11 | meta_id 57 | `Document Type: {inputs.document_type_7}` | `Document Type: {inputs.document_type_7.value}` | HTML 邮件里被包成 `<ul><li>` 多行列表 |")
w("")
w("实测（同一份构造数据 × 两个渲染分支）：**裸用 + 数组 + `isHtml=true` → `<ul><li>`**；")
w("`.value` 在**全部场景**（字符串 / 单元素数组 / 多元素数组 × 两个分支）都是**内联单行**，")
w("多选时输出 `COA Sample, MSDS`（逗号连接，不会出现 `Array`）。")
w("")
w("修复工具：`tools/h24b_fix_checkbox_value.php`（通用：自动发现所有 checkbox/radio 字段，批量规范化，逐 feed 备份）。")
w("")

# ---------------------------------------------------------------- 注意事项
w("## 7. 以后改模板的注意事项")
w("")
w("1. **复选框/单选框一定要加 `.value`**：`{inputs.privacy_consent_11}` 在邮件分支会被渲染成 `<ul><li>…</li></ul>`（多行列表），")
w("   而 `{inputs.privacy_consent_11.value}` 直接输出**内联单行**文本（多选时逗号连接，如 `COA Sample, MSDS`）。")
w("   其余字段（text/email/select/textarea）加不加都一样。")
w("2. **只能用 `{inputs.<字段key>}`**：字段 key 形如 `company_name_1`（`{元素名}_{index}`）。")
w("   不要用「选项级」key（例：`privacy_consent_9.i_agree_to_the_privacy_policy_9_1`）—— FF 解析不到，**渲染为空**。")
w("3. **复制模板要整段检查**：本批 5 处坏法就是「复制 form 8 的通知、只改了字段却没改占位符」造成的。")
w("4. **改完必须核对**：在 FF 表单编辑器里点「预览通知」，或跑 `tools/h24b_audit_notifs.php`（R1/R2/R3 三类校验会自动报）。")
w("5. **索引不会重排**：删除中间字段后，已有字段的 `_index` 不变；但**新增**字段会用新索引，务必回模板核对。")
w("")
w("### 踩坑：FF 的字段定义有静态缓存")
w("")
w("`FormFieldsParser` 把字段定义缓存在静态属性里。同一个 PHP 进程里连续渲染多个表单时，")
w("后一个表单会复用前一个的字段定义 —— 实测 form 9 只渲染出 form 8 也有的那几个字段，其余全空，")
w("**看起来像模板坏了，其实是工具的问题**。所以普查脚本必须**逐表单独立进程**跑"
  "（`SF_H24B_FORM=<id>`），别在一个 `wp eval-file` 里循环所有表单。")
w("")
w("---")
w("")
w("*本文档由脚本生成，请勿手改 —— 要更新就跑 `tools/h24b_build_field_map.py`。*")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("WROTE %s (%d bytes, %d lines)" % (OUT, os.path.getsize(OUT), len(lines)))
