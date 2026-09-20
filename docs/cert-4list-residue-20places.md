> ⚠️ **本清单已被取代**（2026-09-17 15:50 任务 7 精确审计）：原 20 处混入了 `_backup/` 归档命中，且部分已在其他批次修掉。以 `docs/about-prelaunch-todo.md` 第二节的 22 处活模板清单为准。

# 全站 4 认证残留清单（第二批待处理，2026-09-17 存档）

口径基准（About 页任务 1 已统一）：完整 6 认证 = **FDA, cGMP, ISO 9001, FSSC 22000, HACCP, and BRC**。

实测共 **20 处**（此前工作日志误记 18，以此为准），分两类：

- **A 类 · 徽章条**（10 处）：`FDA · cGMP · ISO 9001 · FSSC 22000`（分隔符有 `·`、`&middot;`、`&#183;` 三种写法）
  目标：`FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC`
- **B 类 · 正文列表**（10 处）：`FDA, cGMP, ISO 9001, FSSC 22000`
  目标：`FDA, cGMP, ISO 9001, FSSC 22000, HACCP, and BRC`（注意句中连接词 and 的位置）

| # | 文件 | 行 | 类 | 当前文本 |
|---|---|---|---|---|
| 1 | templates/page-soft-chews.html | 20 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 2 | templates/page-soft-chews.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 3 | templates/page-tablets.html | 20 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 4 | templates/page-tablets.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 5 | templates/page-powders.html | 20 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 6 | templates/page-powders.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 7 | templates/page-pastes.html | 20 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 8 | templates/page-pastes.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 9 | templates/page-liquids.html | 20 | A | FDA &middot; cGMP &middot; ISO 9001 &middot; FSSC 22000 |
| 10 | templates/page-liquids.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 11 | templates/page-drops.html | 20 | A | FDA &middot; cGMP &middot; ISO 9001 &middot; FSSC 22000 |
| 12 | templates/page-drops.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 13 | templates/page-fish-oil.html | 20 | A | FDA &middot; cGMP &middot; ISO 9001 &middot; FSSC 22000 |
| 14 | templates/page-fish-oil.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 15 | templates/page-dental-chews.html | 20 | A | FDA &middot; cGMP &middot; ISO 9001 &middot; FSSC 22000 |
| 16 | templates/page-dental-chews.html | 66 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 17 | templates/page-quality.html | 15 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 18 | templates/page-factory-tour.html | 15 | A | FDA · cGMP · ISO 9001 · FSSC 22000 |
| 19 | templates/page-services.html | 12 | B | FDA, cGMP, ISO 9001, FSSC 22000 |
| 20 | templates/page-services.html | 15 | A | FDA &#183; cGMP &#183; ISO 9001 &#183; FSSC 22000 |

## 处理注意事项（第二批开工时看）

1. 行号以 2026-09-17 源码为准，后续批次若动过这些文件需重新定位（grep 模式见下）。
2. 徽章条分隔符三种写法（`·` / `&middot;` / `&#183;`）需按各文件现状保留原风格，只追加两项。
3. B 类正文注意上下文语法：有的句子是 "...certifications are obtained"，追加后需通读一遍该句。
4. 顶栏徽章条（parts/header 相关）与页脚简介已是 6 认证，不在本清单内，勿重复添加。
5. 批量替换后核查命令：
   ```bash
   grep -rnE 'FSSC 22000(?!,?\s*(HACCP|and BRC))' templates/ parts/ -P
   ```
   预期零命中（FSSC 22000 后面不再直接跟句尾/分隔符）。
