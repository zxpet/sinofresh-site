# H18c 执行报告 — 图集照片帧上限 6→7（含视频时帧上限 8）＋ 竖列第七格

日期：2026-09-30
状态：**已上线生产，五条验收全绿**；部署后新发现「边缘/浏览器拿旧 CSS」**已于同日跟进修复**（bump `2.10.88 → 2.10.89`，见 §3 ⑤-b / ⑤-c）
提交：`12c114d` → `838a52a`（本批）→ `b630187`（报告补录）→ `82afc8c`（缓存跟进），dev 已 `git pull --ff-only` 同步
生产回滚备份：`/root/_h18c_rollback_20260930-111053/`（本批）、`/root/_h18c_bump_rollback_20260930-193747/`（bump）
扫描报告（前序，只读）：`docs/scan-gallery-rail-7th-thumb-2026-09-30.md`

---

## 1. 一句话

配方图集的**照片帧上限从 6 提到 7**，并新增第二个上限：**有视频的记录帧上限 8**（七张照片 + 视频）。
单纯把 `array_slice(…, 0, 8)` 是**错的**——七张自有照片 + 视频合并后前八项是八张照片、视频被切掉，
而八张 72px 磁贴 = 640px 对 607px 主图，正是桌面导轨唯一装不下的形状。
另外把竖列 gap 由 12px 收紧到 8px，**用 `:has()` 限定只对「有第七格」的记录生效**，
使站上现有 21 条（各 4 格）的间距逐像素不变。

## 2. 实施范围（3 处，与确认单一致）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `functions.php` H2a rebuild 块（`:2007` 附近） | `array_slice($slots, 0, 6)` → **双上限循环**：`$photo_cap = 7` 只数照片帧，`$frame_cap = 8` 数总帧；强弱序照片/视频/车间图依次入选，视频不占照片名额 |
| 2 | `functions.php` 两处 docblock（`:1773` 与 `:1870`） | 按**实测数字**改写上限依据：「七格 560px 落在主图内 / 八格 640px 外溢 / 导轨自约 1198px 起容得下七格」＋记录视频不花照片名额的原因 |
| 3 | `style.css`（`@media (min-width:1101px)` 块内） | `.sf-fdetail2__media .sf-gallery__thumbs:has(.sf-gallery__thumb:nth-child(7)) { gap: 8px; }`（**全文件唯一一处** `sf-gallery__thumbs:has(`） |

**显式不改**（本批承诺的一部分，门里有断言）：前台版本保持 **2.10.88**、后台 bundle 保持 **1.1.0**、磁贴尺寸 72px 未动、`formula-gallery.js` 与 `formula-admin.php` 零改动。

> 语义要点：**cap 数「帧」含视频，缩略图条只数「照片帧」**（`formula-gallery.js` 把视频做成独立的 `[Video]` 模式标签，`.sf-gallery__thumbs` 里一个 `<button class="sf-gallery__thumb">` 对应且仅对应一张照片）。这正是需要两个上限的原因。

### `:has()` 选择器为什么是干净的（已核实）

`.sf-gallery__thumbs` 的子元素由 JS 从 `photos.forEach` 逐个 append（`formula-gallery.js:116-139`），
`[Photos][Video]` 模式切换按钮是标记里既有的 `.sf-gallery__tab`、**不在这个 tablist 内**。
⇒ `:has(.sf-gallery__thumb:nth-child(7))` 严格等价于「照片磁贴 ≥ 7 格」，视频存在与否都不干扰。

## 3. 验收结果

### ① dev 零漂移 — PASS（21/21）

`tools/h18c_geometry.js` 对**全站 21 条**配方页在 1440 下实测：每一条都是
`tiles=4 / gap=12px / railH=332 / pitch=84` —— 与 H18c 之前逐项相同。
即 `:has()` 限缩生效，**七格规则一格都没落到现有记录头上**。
工具同时自证拿到的是新字节：served stylesheet `36b0a46db13d33ec07b6d7c5f35d8e45`（341375B，`?ver=2.10.88`）。

### ② 1101 / 1200 / 1240 / 1440 七张实测 — PASS（32/32 断言）

| 视口 | 主图（1:1 stage） | 七格导轨 | 余量 | 结论 |
|---|---|---|---|---|
| 1440 | 607.19 | 560 | **+47.19** | 完全容纳 |
| 1240 | 585.59 | 560 | **+25.59** | 完全容纳 |
| 1200 | 561.59 | 560 | **+1.59** | 临界，仍容纳 |
| 1101 | 502.19 | 560 | **−57.81** | 下探 57.81px（用户已确认接受） |

四档**全部**：`overflow-y: visible`、`scrollHeight == clientHeight`、**不裁剪、不出滚动条**；
1101 档导轨底 997.27 < 模式切换器顶 1013.27 ⇒ **不遮切换器**；`docH` 与四格时相同（撑高的是列，不是页面）。

> 为什么 1101 只有 502px 主图：band `.sf-fdetail2__inner` 上限 1200，`≥1101` 起 `72px minmax(0,1fr)` 网格；
> 1440 与 1280 同值即因该上限封顶。**临界点由 1238px 前移到约 1198px**（gap 12→8 的收益）。

### ③ 有视频的记录设满七张照片 — PASS（12/12）

`tools/h18c_real7_accept.js` 对**真实记录 158**（本就有视频）注入 7 个自传相册 id
（`sf_formula_gallery_ids = 53,96,102,104,106,108,110`）+ 保留视频，实测输出：

```
== 1. as shipped (video only) ==
  slides=5 tiles=4 gap=12px rail=332 :: soft-chews.webp | VIDEO | fac-placeholder.webp | fac-packaging.webp | fac-line.webp
== 2. seven own photos + the video ==
  slides=8 tiles=7 gap=8px rail=560 :: soft-chews.webp | blog-softchews-1024x768.webp |
    sino-fresh-logo-1-1024x127.png | powders.webp | tablets-e1790495031843.webp | drops.webp |
    fish-oil.webp | VIDEO
== 3. restore ==
  slides=5 tiles=4 gap=12px rail=332 :: （与 1 逐字节相同）
VERDICT: PASS — 12 passed, 0 failed
```

- **8 帧 = 7 照片帧 + 视频**；照片帧到顶（帧① `soft-chews.webp` 是剂型标准图，占掉一个照片名额，
  故注入的 7 个自有 id 中**第 7 个落在上限外**——这本身就是 cap 生效的证据，见 §6 实测表）
- **视频没被切掉**（老 `array_slice(…, 0, 8)` 在此形状下会给出「6 帧 / 6 照片 / 0 视频」）
- 断言含：视频幸存、视频保持声明位置、7 磁贴（视频不算缩略图）、第 7 格触发 8px gap、
  导轨恰好 560px 不滚不裁、1440 下七格含在主图内
- 快照 → 改 → 复原 → 复核：改后逐项与改前相同，写入的 meta 行已 `delete_post_meta()` 清除
- 截图：`docs/h18c-shots/j-158-real-7-photos-plus-video.png`

### ④ 门断言 — PASS（source 24/24 ｜ live dev 27/27 ｜ live 生产 27/27）

`tools/h18c_gate.py`（沿用 H13/H14/H18 结构：`check()` + PASS/FAIL + `--source`/`--live`）：

- `--source` **24/24**：双上限常量、`$frame_cap` 存在、视频不占照片名额的循环形状、
  两处 docblock 已改写、`:has()` 规则**恰好出现一次且位于 `min-width:1101px` 块内**
  （`_blank_comments()` + `_enclosing_media()` 做花括号解析，不做子串匹配）、前台 2.10.88 与后台 1.1.0 未变、H18 的 `frame4_id` 槽位幸存
- `--live` **27/27**（dev 与生产各一遍，生产用 `H18C_WP_ROOT` / `H18C_THEME_DIR` 参数化）：
  用**真实主题代码**跑构造用例 —— 七张照片无视频 ⇒ 7 帧；七张照片 + 视频 ⇒ 8 帧且视频在；
  强制空 ⇒ 回落；每个用例都断言 `pid_used` 就是它被指派的记录（防「把数组当 pid 传」那类静默错测）；
  注入值 readback 逐字节自证；前后 `frame_fingerprint()`（行数 + md5）相等 ⇒ **探针零写**
- **双向负对照**：
  - source 半场跑 pre-H18c 源码（`c6cf529`）→ **14 FAIL**（10 条 PASS 正是「本就不该变」的断言）
  - live 半场把 dev 临时换回 pre-H18c `functions.php` → **9 FAIL**，失败详情正好演示被修的回归：
    `video + 7 own` 在老代码下给出「6 帧 / 6 照片 / 0 视频」= 视频被切

### ⑤ 显式部署生产 — PASS

回滚备份 `/root/_h18c_rollback_20260930-111053/`（含 pre-H18c `functions.php` `a47345b7…` 与 `style.css` `0d69a338…`）
→ `php -l` → 原子 `install -m 644 -o apache -g apache` + `mv`。部署后**三方 md5 逐字节一致**：

| 文件 | workspace | dev | 生产 |
|---|---|---|---|
| `functions.php` | `bde32d555367232b4f5b725abef6d160` | 同 | 同 |
| `style.css` | `36b0a46db13d33ec07b6d7c5f35d8e45` | 同 | 同 |

无残留临时文件；服务器 `/tmp/h18c-*.php` 已清理。

### ⑤-b ⚠️ 部署后新发现：源站已更新，但**边缘/浏览器仍拿旧 CSS**（未修，待裁决）

验收 ⑤ 只核对了**磁盘上的文件**（ssh + md5），因此漏掉了一层缓存。按 HTTP 实测被服务的那一份：

| 取法 | last-modified | bytes | 含 `nth-child(7)` 规则 | cf-cache-status |
|---|---|---|---|---|
| 直接访问 `https://www.zxpet.com/…/style.css?ver=2.10.88` | **09-28 03:38** | 341088 | **否** | `HIT`（age ≈ 182623s ≈ 50.7h） |
| 同 URL 加 `&cb=<epoch>`（新 cache key） | 09-30 11:10 | 342067 | 是 | `MISS` |
| 绕 CF 直连源站 `curl -sk -H "Host: www.zxpet.com" https://127.0.0.1/…` | 09-30 11:10 | 342067 | **是**（md5 `36b0a46d…`） | — |

**成因**：本批按「前台版本不 bump」执行，URL 的 `?ver=2.10.88` 未变 ⇒ CF 边缘与浏览器都还用同一个 cache key。
而源站 Apache（`/etc/httpd/conf.d/zxpet-performance.conf:31`）对 `text/css` 发
`Cache-Control: public, max-age=31536000, immutable` ⇒ **浏览器会把这份字节留一年且不重验证**。

**影响**：**当天为零** —— 全站 21 条记录都只有 4 格，`:has()` 规则不参与。**但运营一旦发布一条 7 照片记录**，
该记录在 CF 边缘与回访访客那里会按旧的 12px 间距渲染（第 7 格多探出 22.41px @1200 —— 观感问题，不裁剪不报错）。
PHP 那一半（cap 7 / 帧 8）是服务端渲染，**不受影响、已生效**。

**注意**：单纯「purge CF 那一个 URL」**不够** —— 已经取过 `?ver=2.10.88` 的浏览器因为 `immutable` 一年内不会回源。
能同时覆盖边缘与浏览器的只有**换 URL**，即 bump 前台版本（`2.10.88 → 2.10.89`，约 6–8 处：主题 3 + 工具门 4–5）。

### ⑤-c 缓存跟进：前台版本 bump `2.10.88 → 2.10.89`（已上线，边缘已实测拉新）

用户拍板后执行。改动 8 处：

| 类型 | 文件 | 改动 |
|---|---|---|
| 主题 | `sinofresh-theme/style.css:5` | `Version: 2.10.88` → `2.10.89` |
| 主题 | `sinofresh-theme/functions.php:37` | 主样式 enqueue `'2.10.88'` → `'2.10.89'` |
| 主题 | `sinofresh-theme/inc/formula-admin.php:807` | 注释措辞（原写「前台保持 2.10.88」已不成立） |
| 工具 | `tools/h13_gate.py` | 2 条 source 版本断言 + 1 条 live 版本断言 → `2.10.89`（不同步则 pull 后必红） |
| 工具 | `tools/h14_gate.py` | `VERSION` 常量 → `2.10.89` |
| 工具 | `tools/h18_gate.py` | `VERSION` + 注释改准（H18 未 bump、本批跟进 bump） |
| 工具 | `tools/h18c_gate.py` | `VERSION` + docstring 记录这段因果 + 断言措辞 |
| 工具 | `tools/p2_preverify.py` | `EXPECT_THEME_VER`（该工具已知过时，一并保持诚实） |

**未动**（按 H14 先例）：`h9/h10/h12` 的陈旧版本钉（`2.10.82/84/86`，早已是红，不是本批引入）、
`b3b_local_check.py`（故意停旧版）。

**部署与实测**：

- 生产回滚备份 `/root/_h18c_bump_rollback_20260930-193747/`（pre-bump 三文件：`bde32d55…` / `36b0a46d…` / `6f47d728…`）
- `php -l` 通过 → 原子 `install -m 644 -o apache -g apache` + `mv` → 无残留
- 三方 md5 逐字节一致：`functions.php 13582d32…`（340179B）／`style.css a9a6fada…`（342067B）／`inc/formula-admin.php 62eb11a4…`
- **dev**：`git pull --ff-only`（→ `82afc8c`）后，页面已输出 `style.css?ver=2.10.89`，该 URL 回 342067B / md5 一致 / 含规则
- **生产边缘（决定性）**：带浏览器 UA 取生产配方页 ⇒ HTML 已输出 `?ver=2.10.89`；
  取该 CSS ⇒ `cf-cache-status: MISS`、`last-modified: 09-30 11:38`、342067B、md5 `a9a6fada…`、含 `nth-child(7)` 规则
  ⇒ **边缘与浏览器都换到新 URL 了，问题关闭**

**bump 后回归**：`h18c_gate --source` 24/24；`--live` dev 27/27、生产 27/27；`h13_gate --live` **12/12**（版本断言已同步）；
`h18_gate --live` 8/8；`h14_gate --live` 25/1（唯一红＝既有 row-major 负对照基线）⇒ **红集合未增**。
`h18c_geometry.js` 复跑 **32/32**（21 条记录仍 4 格 / 12px / 332px；served CSS md5 `a9a6fada…`）。

**顺带修掉一个自伤**：`h18c_geometry.js` 里的版本断言原本写作正则字面量 `/\?ver=2\.10\.88/`，
字符串里并不含 `2.10.88` 这个子串（而是 `2\.10\.88`）⇒ 我按 `grep "2.10.88"` 做的 bump 扫描**漏掉了它**，
第一次复跑几何验收因此在「版本」一条上红。已改为普通常量 `const VERSION = '2.10.89'` + `href.includes('?ver=' + VERSION)`，
今后 bump 能被普通 grep 命中。（扫描版本字面量的正确模式：`grep -rnE "2\\\\?\.?10\\\\?\.?8[0-9]"`。）

> 版本号变更只改了 `style.css` 第 5 行的一个数字，**CSS 规则与字节数（342067）不变** ⇒ 21 条记录的几何不受影响。
> ⚠️ `docs/h18c-geometry-evidence.json` 里的 `sheetBytes` **不是字节数**，是 JS 字符串 `.length`（UTF-16 码元，341375）；
> 真实字节数 342067 以部署 md5/`wc -c` 为准（已在脚本里加注说明）。

## 4. 不新增红（兄弟门复核）

H18c 之后对 dev 逐门复跑 `--live`，红集合与 H18 收尾记录**逐条相同**：

| 门 | H18c 后 --live | 既有基线 | 差异 |
|---|---|---|---|
| h9 | 4 FAIL | 4 | 0 |
| h10 | 1 FAIL（trust band） | 1 | 0 |
| h11 | 4 FAIL（3 group headings / trust band / Form 12 sink / subject） | 4 | 0 |
| h12 | 4 FAIL（`/`、`/quality/`、`/services/`、`/factory-tour/` Step2 零漂移基线滞后） | 4 | 0 |
| h13 | **12/12 全绿** | 全绿 | 0 |
| h14 | 1 FAIL（row-major 负对照 — got 1） | 1 | 0 |
| h18 | **8/8 全绿** | 全绿 | 0 |

归因：H18c 只动了两段 docblock、图集上限算术、一条 `:has()` CSS 规则，
**不触及**上述任何一条断言所覆盖的子系统（规格表 / trust band / 表单通知 / 静态页零漂移 / 形状字段保存）。
既有红与 dev 的 7 个 `sf_trust_*` 空串、运营记录数据、Form 12 已退役、4 页基线滞后有关，与 H18c 无关。

## 5. 顺带交付：部署后对照截图（自证规则）

`tools/h18c_rail_shots_post.js` → `docs/h18c-shots-post/`（9 张），每张都在日志里读出**渲染后**的 gap：

| 截图 | 磁贴 | gap | railH | stageH | 说明 |
|---|---|---|---|---|---|
| `post-1440-rail-as-shipped-4-tiles.png` | 4 | **12px** | 332 | 607.19 | 现状记录一条未动 —— `:has()` 限缩的证据 |
| `post-1440-rail-SIMULATED-7-tiles.png` | 7 | **8px** | 560 | 607.19 | 装得下 |
| `post-1440-rail-SIMULATED-8-tiles-pushed-down.png` | 8 | 8px | **640** | 607.19 | 外溢 32.81px ⇒ 这就是照片上限取 7 的理由 |
| `post-1240-rail-SIMULATED-7-tiles.png` | 7 | 8px | 560 | 585.59 | 容纳 |
| `post-1200-rail-SIMULATED-7-tiles.png` | 7 | 8px | 560 | 561.59 | 临界容纳 |
| `post-1101-rail-SIMULATED-7-tiles-dips.png` | 7 | 8px | 560 | 502.19 | 下探 57.81px，不裁剪 |
| `post-1024-row-SIMULATED-7-tiles-scrolls.png` | 7 | **12px** | 92 | 549.59 | 横滑条（`scrolls=true`），规则在 `≥1101` 块内故不生效 |
| `post-768-row-SIMULATED-7-tiles.png` | 7 | 12px | 92 | 692 | 横排全显 |
| `post-375-no-rail-dots.png` | 4 | — | 0 | 299 | 375 无条，仅圆点 |

> 扫描阶段的 `docs/h18c-shots/a..i` 是**改动前**（12px 间距）拍的，其中 `f-1200-…-overflows` 命名的正是改动要消除的状态；保留作「前」对照，新目录是同几何的「后」对照。

## 6. 回答：cap 提上去之后，用户实际能自己设几张照片？

**实测**（`tools/h18c_caps_probe.php`，走 `get_post_metadata` 过滤器内存注入 + `wp_get_attachment_image_src` 取真实大图 URL 逐条归类，
36 种形状，**零 DB 写**：`postmeta rows 187 -> 187，md5 IDENTICAL`）：

| 特色图 | 注入相册 id | 视频 | 照片帧 | 总帧 | 其中「你自己传的照片」 |
|---|---|---|---|---|---|
| 未设 | 0 → 6 | 否 | 4 → 7 | 4 → 7 | 0 → 6 |
| 未设 | 0 → 6 | **有** | 4 → 7 | 5 → **8** | 0 → 6 |
| **已设** | 0 → 6 | 否 | 5 → 7 | 5 → 7 | 1 → **7** |
| **已设** | 0 → 6 | **有** | 5 → 7 | 5 → **8** | 1 → **7** |
| 任意 | 7 / 8 / 9 | 任意 | **7（封顶）** | 7 或 8 | **最多 7** |

### 结论（三句话）

1. **照片帧上限是 7，帧①占其中一个名额** —— 帧① 是特色图；未设特色图时它回落成剂型标准图（`<form>.webp`），
   也就是说**不设特色图就白白丢掉一个照片位**。
2. ⇒ **「你自己传的照片」最多 7 张，前提是特色图也用你自己的图**（1 张特色图 + 6 张相册图）；
   **不设特色图则是 6 张**。相册字段 `sf_formula_gallery_ids` 的输入框不限个数，但连同帧① 只有**前 6 个**能上栏
   （注入 7 张时探针读到 `6/7`，第 7 张被裁）。
3. **视频不占照片名额**（这是本批双上限的收益）：有视频时照片仍是 7 张、总帧 8；
   老代码在这里会把视频切掉。

### H18 的三个槽位能再加多少？

**不能加，只能顶替。** `Frame 2/3/4` 落在 frame 2/3/4 这**三个车间图位**上（位置锁定，空槽回落车间图），
且它在强弱序里排在**自有照片之后** —— 也就是说「自有相册图先入选、槽位属 facility 尾部先被裁」。
因此：

| 路径 | 你能设几张自己的照片 | 说明 |
|---|---|---|
| 特色图 + 相册（`gallery_ids`） | **7** | 推荐；相册顺序 = 上栏顺序，可预期 |
| 特色图 + 三个槽位 | **4** | 1 + 3，且槽位会与车间图占同一位置 |
| 只在槽位里选、不设特色图 | **4**（其中 3 张是你的 + 剂型标准图） | 帧① 仍是剂型图 |

⇒ **要「后台逐个精确落位、且超过 7 张」需新增槽位（新批次）**；
在现有字段下，7 张是硬上限，且必须把特色图一起用上。

## 7. 遗留 / 下一步

- ⚠️ **【已完成】CSS 的第八格规则未到达访客**（§3 ⑤-b / ⑤-c）：源站已对而 CF 边缘 HIT 旧字节、浏览器因
  `max-age=31536000, immutable` 一年不回源 ⇒ 已 **bump 前台版本到 `2.10.89`**（8 处：主题 3 + 工具门 5），
  生产显式部署 + 边缘实测拉到新字节。**问题关闭**。（教训已入 `MEMORY.md`：改了 CSS/JS 必须 bump；验收必须走 HTTP 看
  `last-modified`/`content-length`/`cf-cache-status`，不能只看磁盘 md5。）
- **生产 21 条记录的三个 H18 槽仍大量为空**；运营已于 **2026-09-30 18:38** 开始填图 ——
  生产 158 现有 `sf_formula_frame2_id = 316`、`frame3_id = 321`、`frame4_id = 328`、`gallery_ids = 314`、
  `_thumbnail_id = 404`、有视频，渲染 6 帧（1 主图 + 2 自传 + VIDEO + 2 车间残留）；172 liquid-joint-support 也已有槽位。
  ⇒ 门的断言已按纪律改为**构造用例 + 不变量**（不关于运营数据），运营继续填图不会让门转红。
- **运营填图时的提醒（值得转达）**：帧① 是特色图，**不设特色图就白白丢掉一个照片位**（帧① 回落剂型标准图）⇒
  一条想放满 7 张自有照片的记录，必须**先把特色图设成自己的图，再在相册里选 6 张**。
- 配方页 Product JSON-LD `image` 仍取剂型图，不跟随帧①/槽位图（H17 遗留，建议下批对齐）。
- dev 的 7 个 `sf_trust_*` 仍是空串（H15 只修了生产）⇒ dev 不渲染 trust band，h10_gate --live 那条红即此，待同步。
- 1101–1197 档第 7 格「下探」（用户已确认接受）；若日后要消除，需回到「磁贴 72→64px」方案（动视觉规格，不建议轻动）。
- 工作区里有两处**与本批无关**的未提交改动：`docs/batch3b-live-accept-shots/la-flavor-en-1440.png` 与
  `…-custom-open-1440.png`（二进制被重写，疑似早前批次脚本重拍）；另有一批未跟踪的临时文件
  （`n0/n1/n2.html`、`tools/_h14_*.js|php|py`、`tools/_h9b_ui_check.py`）。均未纳入本批提交。

## 8. 文件清单

| 类型 | 路径 |
|---|---|
| 实现 | `sinofresh-theme/functions.php`（双上限 + 两处 docblock）、`sinofresh-theme/style.css`（`:has()` gap 8px） |
| 缓存跟进 | 同上两文件 + `sinofresh-theme/inc/formula-admin.php`（版本 → **2.10.89**）；门 `h13/h14/h18/h18c_gate.py` + `p2_preverify.py` 常量同步 |
| 门 | `tools/h18c_gate.py`（`--source` 24 / `--live` 27；环境变量 `H18C_WP_ROOT` / `H18C_THEME_DIR` 可指向生产） |
| 几何验收 | `tools/h18c_geometry.js`（21 条零漂移 + 四档七格 + 375），证据 `docs/h18c-geometry-evidence.json` |
| 真数据验收 | `tools/h18c_real7_accept.js`（158 七张 + 视频；快照/改/复原/复核） |
| 上限实测 | `tools/h18c_caps_probe.php`（36 种形状，`wp eval-file`，零 DB 写） |
| 截图（前） | `tools/h18c_gallery_capacity_probe.js`、`tools/h18c_rail_shots.js` → `docs/h18c-shots/`（10 张） |
| 截图（后） | `tools/h18c_rail_shots_post.js` → `docs/h18c-shots-post/`（9 张，渲染 gap 自证） |
| 报告 | `docs/scan-gallery-rail-7th-thumb-2026-09-30.md`（扫描）、本文件（执行） |
