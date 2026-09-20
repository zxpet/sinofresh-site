# 批次 2C · 第 0 步（卡片加图）基线记录

测于 2026-09-20，dev.zxpet.com，agent-browser / Chromium，全页预滚动 + 等待 `document.images.complete`。

原始数据：`tools/_b2s0_measure_{before,after}_{1440,375}.json`；重抓：`python3 tools/b2s0_measure.py after 1440 all`

## 桌面 1440×900

| 剂型页 | 卡数 | 改前 band/grid (px) | 改后 band/grid (px) | Δgrid | 媒体框 | 卡宽 |
|---|---|---|---|---|---|---|
| Soft Chews | 4 | 445/221 | 655/431 | +210 | 280x210 (4:3 cover) | 282 |
| Tablets | 3 | 468/243 | 678/453 | +210 | 280x210 (4:3 cover) | 282 |
| Powders | 3 | 425/201 | 635/411 | +210 | 280x210 (4:3 cover) | 282 |
| Liquids | 2 | 445/221 | 655/431 | +210 | 280x210 (4:3 cover) | 282 |
| Pastes | 2 | 445/221 | 655/431 | +210 | 280x210 (4:3 cover) | 282 |
| Dental Chews | 3 | 468/243 | 678/453 | +210 | 280x210 (4:3 cover) | 282 |
| Drops | 2 | 445/221 | 655/431 | +210 | 280x210 (4:3 cover) | 282 |
| Fish Oil | 2 | 445/221 | 655/431 | +210 | 280x210 (4:3 cover) | 282 |

合计 21 张卡片；Δgrid = 媒体框高 210px（282×3/4≈211.5，边框内 280×210）。

## 移动 375×812（改后）

| 剂型页 | 卡数 | band | grid | 卡高 | 媒体框 |
|---|---|---|---|---|---|
| Soft Chews | 4 | 2032 | 1822 | 444 | 297x223 |
| Tablets | 3 | 1572 | 1363 | 444 | 297x223 |
| Powders | 3 | 1512 | 1302 | 423 | 297x223 |
| Liquids | 2 | 1113 | 903 | 444 | 297x223 |
| Pastes | 2 | 1113 | 903 | 444 | 297x223 |
| Dental Chews | 3 | 1572 | 1363 | 444 | 297x223 |
| Drops | 2 | 1113 | 903 | 444 | 297x223 |
| Fish Oil | 2 | 1113 | 903 | 444 | 297x223 |

单列布局不变（gap 16）；媒体框 297×223，同 4:3。

## 关键事实

- `.sf-fgrid` 宽 1200px（全站内容容器宽），4 列 × 282px + 3×24px gap —— **卡片宽 282px，不是 brief 预估的 360–390px**；要达到 360–390px 需容器 ~1560–1650px，需另行决策是否放宽容器。
- 图片源：`uploads/2026/09/{form-slug}.webp`（8 张均 720×720 正方形），CSS `aspect-ratio:4/3` + `object-fit:cover` 裁剪，`loading=lazy`。
- 同页 4 张卡复用同一张剂型图（预期占位行为）；8 个 form slug 与文件名逐一对应。
- 改前基线（2B Step2 末）：band/grid 见上表「改前」列（soft-chews 445/221 等）。
