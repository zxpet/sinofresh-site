# 批次 1 · 步骤 1 —— 回滚配置器折叠（撤销阶段 2A）

**日期** 2026-09-20 · **源** `sinofresh-theme` · **目标** `sinofresh.local` · **状态** ✅ 完成并核验

---

## 1. 结论

配置器已恢复**默认展开**，8 页桌面/移动全部一致。阶段 2A 的折叠痕迹——模板 `<details>` 包裹、`sf-explore` 外移、`configurator.css` 折叠段落、`style.css` 的 27m 追加——**全部清除**，两个 CSS 的 md5 精确回到阶段 1 验证基线的 pre-md5。

Lead time 措辞 `after packaging is ready`（用户决策 ⑥）**有意保留**，未随折叠一起回滚。

---

## 2. 为什么不能直接 `cp` 覆盖

阶段 2A 在同一批改动里捆了**两件方向不同的事**：

| | 内容 | 处置 |
|---|---|---|
| (a) | 8 模板外包 `<details class="configurator__fold">` + `sf-explore` 移出配置器 + `configurator__fold-*` CSS + style.css 27m 追加 | **回滚** |
| (b) | 8 模板 Lead time `after packaging ready` → `after packaging is ready` | **保留**（用户决策 ⑥） |

所以流程是 **「恢复 + 重放」**：从 `_backup/batch1-stage2-20260920-093741/` 取备份内容 → 只重放 (b) → **全部断言通过才写盘**（断言失败则磁盘不动）。

---

## 3. 改动文件（10）

| 文件 | md5 前 → 后 |
|---|---|
| `templates/page-soft-chews.html` | `d2a845d7…` → `adcb6f0c…` |
| `templates/page-tablets.html` | `a7bdda3f…` → `6d14965c…` |
| `templates/page-powders.html` | `c74f93a5…` → `b08d2b05…` |
| `templates/page-pastes.html` | `81beaf60…` → `9ced3b21…` |
| `templates/page-drops.html` | `7ee7dc60…` → `9a9a409c…` |
| `templates/page-liquids.html` | `89015437…` → `ef0fc635…` |
| `templates/page-fish-oil.html` | `07bf33b0…` → `6f2bfee2…` |
| `templates/page-dental-chews.html` | `e53431dd…` → `a9e7c6b5…` |
| `assets/css/configurator.css` | `df40d063…` → **`75091298a6edf7cbe63b594b87e14b86`**（= pre-md5） |
| `style.css` | `e11b25f8…` → **`db80b6533ce316f2c8046bbcdfcc50a6`**（= pre-md5） |

`functions.php`、`assets/js/formulas.js` **未变动**（阶段 2B 未执行，与备份一致）。

---

## 4. 写盘前断言（全绿）

- 8 模板中 `configurator__fold` / `__fold-head` / `__fold-body` / `__fold-icon` / `__fold-desc` 残留 **0**
- `configurator__explore-row` / `__explore-col` 残留 **0**；`<div class="sf-explore">` 唯一
- `sf-explore` 回到 `.configurator__options **内部**（位置判据 `options < sf-explore < summary-col`，8/8 通过）
- 区块对计数 == 备份（`wp:heading{textAlign:center}`、`wp:paragraph{center/secondary}`、`</summary>`、`<details>`）
- **阶段 2A 足迹**：当前 `<details>` 计数 = 备份 **+1**（8/8 页成立）
- 每模板相对备份**恰好 1 行差异**（即措辞那一行）
- `configurator.css` / `style.css` 内容 md5 == pre-md5

---

## 5. 核验矩阵

| # | 核验项 | 结果 |
|---|---|---|
| 1 | 桌面配置器默认可见 | ✅ 8/8 `foldExists=False`、`checkVisibility={contentVisibilityAuto,opacity,visibility}=True`、`sectionChildren=[h2, p, svg, div.configurator]` |
| 2 | 8 页一致 | ✅ 桌面 1440 / 平板 900 / 移动 375 三视口，`section#configurator` 段高 **Δ=0**（8/8×3） |
| 3 | 几何零回归（480 键） | ✅ 仅 7 处 `top` ±1px（tablet 视口）；**A/A 自检**（同字节代码采两次）噪声 = 3 处**同类** → 噪声地板 ≥1px，`h`/`w`/`left`/`display`/`position`/margin/padding **全等** |
| 4 | 全站掩码 sha256 | ✅ **11 页逐字节全同**；8 剂型页「基线 + 措辞替换」**逐字节 == 当前**；字节差 **+24 B = 8 × 3 B** |
| 5 | 19 页 HTTP | ✅ **19/19 = 200**，PHP 错误签名 0 |
| 6 | 源码 = Local | ✅ `cmp -s` 10/10；`diff -rq` **Files differ = 0**（`Only in SRC` 全为非部署资产：docs/tools/_backup/screenshots/.DS_Store） |
| 7 | `grep -rn "/ -->"` | ✅ **0**（templates / *.php / assets，html+php+css+js 各 0） |
| 8 | 移动端不溢出 | ✅ `overflowX = 0`（8/8） |

---

## 6. 自校准证据（方法可信性）

- **抓页方式**：`pages_s1/liquids.html` 中 `sf-sec-` 计数 **0** → 基线是**服务端 HTML**（无 JS 注入），可用 `curl` 复现。
- **方法匹配验证**：本轮 curl 抓的 11 个非剂型页——含带表单/nonce 的 `home` / `contact` / `faq` / `services` / `feedback`——**掩码后逐字节等于基线**，反证抓法与掩码口径一致。
- **掩码**：在 `t22_render_cmp.py` 基础上**补齐两个已知盲区** `nonce=<10hex>`（wp-statistics）与 `config_nonce":"<10hex>"`（GF 表单页），并加 `"nonce":"<hex>"`；基线与本轮套**同一套掩码**，故可比。时间上基线与本轮同处 UTC 00:00–12:00 一个 12h tick 内。

---

## 7. 产物与脚本

| 类型 | 路径 |
|---|---|
| 安全快照（回滚**前**的折叠态，10 文件） | `_backup/batch1-s2-rollback-20260920-100545/` |
| 回滚 + 断言脚本（可重跑，幂等） | `tools/_b1r_step1_rollback.py` |
| 几何探针（Δ0 证据） | `tools/_b1r_step1_geo.js` → `/tmp/b1/step1/geo.json`、`geo2.json`（A/A） |
| 截图脚本 | `tools/_b1r_step1_shots.js` → `/tmp/b1/step1/shots/`（23 张） |
| 全站掩码比对器（强化掩码） | `tools/_b1r_step1_render_cmp.py` → `/tmp/b1/step1/render_cmp.json` |
| 基线参照（只读） | `/tmp/b1/s2/before.json`（阶段 1 展开态）、`/tmp/b1/pages_s1/`（阶段 1 页面） |

**顺带清理**：回滚脚本被中断那次留下的重复快照 `_backup/batch1-s2-rollback-20260920-100522` 已删除（三闸核验：白名单逐文件列举 / md5 1:1 对应 / 删除集合 ≡ 保留集合均通过）。

---

## 8. 留给步骤 6 的措辞清单

| 位置 | 现状 | 动作 |
|---|---|---|
| `templates/page-{8 剂型}.html` | 已 `after packaging is ready` | **不动**（本轮已确认保留） |
| `templates/page-faq.html:48` | `7–15 working days after packaging ready.` | → `… is ready.` |
| `templates/page-services.html:126` | `7&#8211;15 working days after packaging ready` | → `… is ready` |
| `style.css:1913`（表格布局注释） | 注释里引用旧措辞 | 同步为 `is ready`（注释，零风险） |
| `docs/*.md`（历史报告） | 旧措辞 | **不改**（归档性质，`grep` 假阳性） |

---

## 9. 下一步

**步骤 2：Hero 极简（方案 A）** —— 删 4 张轮播 → 单栏居中 ~330px，按钮压到 2 个（`Browse Standard Formulas` 主 / `Build Custom Formula` 次），移除 `Request a Quote`。等待确认后执行。
