#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b 截图 PII 打码 —— 按「占位比例」定位矩形，覆盖含个人数据的单元格。

约定与既有纪律一致（运维手册同款）：**数据单元格整体 ███**，不遮挡表头/菜单/操作按钮，
保留「这是哪个页面、哪个功能」的证据价值，只抹掉人能读出的个人数据。

坐标基准：每张图我都在浏览器里看过原始渲染，比例值 = 目标像素 / 该视图的宽高。
因此同一份比例表在 1x / 2x 截图上都成立，不必关心 PNG 的真实分辨率。

用法：python3 tools/h24b_redact_shots.py            # 就地打码（幂等：已打码会再盖一层）
"""
import os
import sys

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (x0, y0, x1, y1) 均为占整图宽高的比例
RECTS = {
    # 列表页：整块覆盖表格卡片（含列头）——数据单元格整体 ███ 的可靠做法。
    # 真正的证据是「状态总览条 / 下拉筛选值 / 分页 Total」，这些都在卡片外，保留。
    "05-entries-explicit-filters.png": [(0.1296, 0.3440, 0.9583, 0.4427)],
    "07-entries-spam.png": [(0.1296, 0.3440, 0.9583, 0.8280)],
    "07-entries-all.png": [(0.1296, 0.3440, 0.9583, 0.8280)],
    # 单条详情：字段值 + 用户 IP + 提交日志里的第三方邮箱
    # ⚠️ 这张是 fullPage（1440x1601），高宽比与视口图不同，比例必须按 PNG 实际像素算。
    "06-entry-detail.png": [
        (0.1389, 0.1836, 0.7014, 0.2061),   # Company Name 值
        (0.1389, 0.2286, 0.7014, 0.2498),   # Contact Person 值
        (0.1389, 0.2705, 0.7014, 0.2936),   # Email 值
        (0.1389, 0.3142, 0.7014, 0.3354),   # Country 值
        (0.1389, 0.3480, 0.7014, 0.3750),   # Interested Dosage Form 值
        (0.1389, 0.3910, 0.7014, 0.4372),   # Notes 值
        (0.7986, 0.1961, 0.8958, 0.2211),   # Submission Info → 用户 IP
        (0.1354, 0.6833, 0.4500, 0.7083),   # 提交日志 → broadcast 给第三方的邮箱
    ],
    # FluentSMTP 日志：第三方收件人（自动回复的真实收件人）
    "08-smtp-logs.png": [(0.490, 0.2813, 0.650, 0.6547)],
}

# dev 侧：dev 是从生产种子过来的，**同样含真实客户数据**（实测 06 里有 251817465@qq.com）。
# 列表页整块覆盖表格卡片；详情页整块覆盖「表单输入数据」卡体 + 提交日志里的邮箱行。
RECTS_DEV = {
    "04-entries-default-unread.png": [(0.1296, 0.3440, 0.9583, 0.5600)],
    "05-entries-explicit-filters.png": [(0.1296, 0.3440, 0.9583, 0.4427)],
    "07-entries-spam.png": [(0.1296, 0.3440, 0.9583, 0.8280)],
    "07-entries-all.png": [(0.1296, 0.3440, 0.9583, 0.5600)],
    "06-entry-detail.png": [
        (0.128, 0.1550, 0.720, 0.5780),   # 「表单输入数据」卡体（字段值 + 标签一起盖）
        (0.135, 0.7900, 0.460, 0.9100),   # 提交日志：broadcast 给第三方/客户的两行邮箱
    ],
}

FILL = (128, 128, 128)   # 中性灰，与手册打码风格一致


def main():
    shots = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "docs", "h24b-shots-prod")
    table = RECTS
    if os.path.basename(os.path.normpath(shots)).endswith("-dev"):
        table = {**RECTS, **RECTS_DEV}
    total = 0
    for name, rects in sorted(table.items()):
        p = os.path.join(shots, name)
        if not os.path.isfile(p):
            print("  跳过（不存在）: %s" % name)
            continue
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        w, h = im.size
        for (fx0, fy0, fx1, fy1) in rects:
            d.rectangle([round(fx0 * w), round(fy0 * h), round(fx1 * w), round(fy1 * h)], fill=FILL)
        im.save(p, "PNG")
        total += len(rects)
        print("  打码 %s  (%d 处, %dx%d)" % (name, len(rects), w, h))
    print("完成：共 %d 处" % total)


if __name__ == "__main__":
    main()
