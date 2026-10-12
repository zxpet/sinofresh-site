#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b 离线断言：核对 FluentSMTP 日志里某封真实邮件的正文

用途：真通知已经发出后，不必再发一封来做断言 —— 把日志里的 body 取出来离线复验即可。

取 body（服务器侧）：
  wp eval 'echo base64_encode($GLOBALS["wpdb"]->get_var($GLOBALS["wpdb"]->prepare(
      "SELECT body FROM wp_fsmpt_email_logs WHERE id=%d", <ID>)));' --allow-root > /tmp/mail.b64

用法：
  python3 h24b_notif_body_check.py /tmp/mail.b64 "H24B Notif Verify (TEST)"
"""
import base64
import html as htmlmod
import re
import sys

CONSENT = "I agree to the Privacy Policy"


def html_to_text(s):
    s = re.sub(r'(?i)<br[^>]*>', "\n", s)
    s = re.sub(r'(?i)</(p|div|tr|li|h[1-6]|table|td|th)[^>]*>', "\n", s)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmlmod.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n\s*\n+', "\n", s)
    return s.strip()


def main():
    if len(sys.argv) < 2:
        print("用法: h24b_notif_body_check.py <body.b64> [company]")
        return 2
    company = sys.argv[2] if len(sys.argv) > 2 else ""
    with open(sys.argv[1], "rb") as f:
        b64 = f.read().strip()
    text = html_to_text(base64.b64decode(b64).decode("utf-8", "replace"))

    print("---- 邮件正文（纯文本）----")
    for ln in text.split("\n"):
        if ln.strip():
            print("  | " + ln)
    print("--------------------------\n")

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    consent_line = next((l for l in lines if l.startswith("Privacy Consent")), "")
    company_line = next((l for l in lines if l.startswith("Company")), "")

    fails = []

    def ck(name, ok, detail=""):
        print(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    ck("★ Privacy Consent 行 = 勾选值（内联单行）",
       consent_line == "Privacy Consent: " + CONSENT, consent_line or "(未找到该行)")
    ck("★ 该行不显示公司名",
       bool(company) and not (consent_line.endswith(company) or (company and company in consent_line)),
       consent_line)
    ck("该行未被 <ul>/<li> 包裹（无列表残留）",
       "<ul" not in consent_line and "<li" not in consent_line, consent_line)
    if company:
        ck("Company 行仍正常显示公司名", company in company_line, company_line)
    ck("六行字段齐全", all(any(l.startswith(p) for l in lines)
                       for p in ("Company", "Contact", "Email", "Country",
                                 "Interested Dosage Form", "Notes")),
       " / ".join(l.split(":")[0] for l in lines[:10]))

    print("\n===== %s =====" % ("ALL PASS" if not fails else ("FAILED: " + ", ".join(fails))))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
