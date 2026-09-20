#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 2.2/2.3 渲染零变化核验：19 页掩码后逐字节比对
掩码规则（显式、可复现）—— 仅归一 Gravity Forms 的**每请求变动量**，共两类：
  ① 加密隐藏域值：value='<长随机串>'  →  value='__MASKED__'
     判定：长度 >= 40 且属 base64 / url-safe 字符集
  ② 电话字段的国家选择器 DOM id 后缀（GF uniqid）：
     gform_phone_dropdown_<hex>  →  gform_phone_dropdown___MASKED__
     实测证据：连续两次抓取 factory-tour/services 页，唯二变动的就是这两类。
用法：python3 tools/t22_render_cmp.py <pages_dir> <out_json>
"""
import os, re, sys, json, hashlib

MASK_VAL = re.compile(r"value='[A-Za-z0-9+/=$]{40,}'")
REPL_VAL = "value='__MASKED__'"
MASK_UID = re.compile(r"gform_phone_dropdown_[0-9a-f]{8,}")
REPL_UID = "gform_phone_dropdown___MASKED__"

pages_dir = sys.argv[1]
out_json = sys.argv[2]

def masked_hash(p):
    raw = open(p, encoding='utf-8', errors='replace').read()
    n1 = len(MASK_VAL.findall(raw))
    n2 = len(MASK_UID.findall(raw))
    m = MASK_VAL.sub(REPL_VAL, raw)
    m = MASK_UID.sub(REPL_UID, m)
    return {
        'raw_bytes': len(raw.encode()),
        'masked_bytes': len(m.encode()),
        'mask_count': n1 + n2,
        'mask_val': n1,
        'mask_uid': n2,
        'sha256': hashlib.sha256(m.encode()).hexdigest(),
    }

res = {}
for fn in sorted(os.listdir(pages_dir)):
    if not fn.endswith('.html'):
        continue
    res[fn[:-5]] = masked_hash(os.path.join(pages_dir, fn))

json.dump(res, open(out_json, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
tot_r = sum(v['raw_bytes'] for v in res.values())
tot_m = sum(v['masked_bytes'] for v in res.values())
print(f'{len(res)} 页 | raw 合计 {tot_r:,} B | masked 合计 {tot_m:,} B | 掩码命中域 {sum(v["mask_count"] for v in res.values())} 个')
for k, v in res.items():
    print(f"  {k:<16} raw={v['raw_bytes']:>7,}  masked={v['masked_bytes']:>7,}  mask={v['mask_count']}  {v['sha256'][:16]}")
print('→', out_json)
