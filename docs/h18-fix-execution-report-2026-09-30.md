# H18 执行报告 — 配方图集帧②③④ 改为每条配方独立槽位（B1+F2）

日期：2026-09-30
状态：**已上线生产，五条验收全绿**
提交：`cf0c493`（dev `git pull --ff-only` 同步）
生产回滚备份：`/root/_h18_rollback_20260930-081349/`

---

## 1. 一句话

帧②③④ 从「主题硬编码、全站共用」改为 **每条配方自己的三个单图槽**
（`sf_formula_frame2_id / _frame3_id / _frame4_id`，Media 组 Frame 2/3/4），
**位置锁定、不队列填充**；槽位留空回落该位置的车间图，页面恒 ≥4 帧。

## 2. 实施范围（7 处，与确认单一致）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `functions.php` | `sinofresh_formula_gallery_slots()` 帧序规则：`$frame_slots` 按 1/2/3 键映射 → `$slots[$offset]`（位置锁定）；陈旧 ID 回落；docblock 注明位置锁定契约 |
| 2 | `functions.php` | 帧②③④尺寸标注注释（1100×733 vs 800×600 纵横比差异不是缺陷，1:1 stage + object-fit:cover 下零布局影响） |
| 3 | `inc/formula-admin.php` | meta 注册三键 + `sf_formula_gallery_ids` 描述改准（CSV，原误写 JSON array） |
| 4 | `inc/formula-admin.php` | 字段规格三条 `type=image`（media 组）+ `case 'image'` 渲染分支（hidden id / 预览 / Choose / Remove） |
| 5 | `inc/formula-admin.php` | `case 'image'` 保存分支（`absint`，空值删键不落 `'0'`） |
| 6 | `inc/formula-admin.php` | `sf-mb-tables` 资产版本 1.0.0 → **1.1.0**（前台保持 2.10.88 不 bump） |
| 7 | `assets/admin/sf-mb-tables.js` | 单图选择器 `singleFrameFor()`（single-select + image library）+ add/clear 委托处理 |

## 3. 验收结果

### ① dev 零漂移 — PASS
改前基线 `/tmp/h18-before.json` vs 改后 `/tmp/h18-after.json`：**21/21 条配方页逐字节相同，drifted: NONE**；改后复抓 `h18-after2.json` 仍 21/21。
基线：158 五帧（含视频），其余 20 条四帧。

### ② 设槽后帧序正确、车间图按序补位 — PASS（dev 真实函数 + 真实 meta）
- `T1 frame2=A`：`soft-chews | A | fac-packaging | fac-line`（只动帧②）
- `T3 frame4=B`：`soft-chews | fac-placeholder | fac-packaging | B`（**只动帧④，②③各自保持工厂默认 = 位置锁定证据**）
- 负控 `frame2=999999`（陈旧 ID）：回落 `fac-placeholder`，带不缩短
- 158 五帧组：`soft-chews | VIDEO | slot2 | fac-packaging | fac-line`
- 每步 readback 自证；测后 meta 全清、全库 `sf_formula_frame%` 计数 0

前台 HTTP 端到端：`/formulas/calming-soft-chews/` 基线 md5 `8c07b3f1…` → 设 frame2=53 → `508e5fde…` → 删 meta → **还原 `8c07b3f1…`（逐字节）**。

真实保存处理器（真 nonce + `do_action('save_post_sf_formula')`）：设值/清空/脏输入（`53abc`、`-7`）三组全对，清空即删键。

### ③ h18_gate.py — PASS（含双向负对照）
`tools/h18_gate.py`（沿用 H13/H14 结构：`check()` + PASS/FAIL + `--source`/`--live`）：
- `--source`：**26/26**（7 处改动点全覆盖：帧序位置锁定语义、meta 注册、字段规格/渲染/保存、1.1.0、CSV 描述、尺寸注释、前台版本不 bump）
- `--live`：**8/8**（零漂移 / 只动帧② / 位置锁定 / 陈旧 ID 回落 / 复原 / 无残留行）
- **source 负对照**：跑在 `b40ce44`（pre-H18）源码上 → **20 FAIL**（6 条是 H18 本就不改的版本断言，PASS 正确）
- **live 负对照**：dev 临时换回 pre-H18 `functions.php`（php -l 通过，跑完 `git checkout` 还原 + md5 核对）→ E1/E2 **红**、E0/E3/复原/残留**绿**，与门 docstring 预测一致

### ④ 显式部署生产 — PASS
生产 `/var/www/zxpet-v2`（真实目录非软链）：
- 回滚备份 `/root/_h18_rollback_20260930-081349/`（三文件，md5=改前 H17 版）
- `php -l` 两 PHP 文件通过；`node --check` JS 通过（本地）
- `install` 暂存 → 原子 `mv` → `apache:apache` / `644` → 无 `.h18new` 残留
- 三方 md5 一致：`functions.php a47345b7…`、`inc/formula-admin.php 6f47d728…`、`sf-mb-tables.js 506cb28c…`

**生产只读探针**（`get_post_metadata` 过滤器内存注入，**零 DB 写**，`frame_meta_rows=0` 自证）：
- E0 四帧 = 基线；注入 frame2=96 / frame3=104 / frame4=999999 → `[soft-chews | 96图 | 104图 | fac-line]`（②③各就各位、陈旧 ID 回落）✓
- 三键 `registered_meta_key_exists` 全 1；`sf_formula_mb_fields()` 三条 image 规格 ✓

**生产前台 HTTP**：`https://www.zxpet.com/formulas/calming-soft-chews/` → 200，gallery section 2298B，4 帧 slots 1-4 = `soft-chews / fac-placeholder / fac-packaging / fac-line` ✓

### ⑤ 截图 — PASS（docs/h18-shots/）
- `a-admin-media-frames.png` — 后台 Media 盒：Gallery images + **Frame 2/3/4**（各自中文 hint + Choose image）+ YouTube URL + Card badge
- `b-front-all-empty.png` — 前台三槽全空：四帧（主图 + 3 车间图）
- `c-front-frame2-override.png` — 设 frame2 后：第②帧换成本记录自己的图，①③④不变
- `d-front-slot-cleared.png` — 清空后：与 b 逐字节同帧序（复原）

脚本 `tools/h18_shots.py` 12/12 断言通过（含登录守卫、markup 断言、meta 清理）。
（备注：WP 6.x 后台把元框面板折叠成 ~79px 条，脚本里先撑开 `.edit-post-meta-boxes-main__liner` 再元素级截图——后续批次截图可直接复用这个做法。）

## 4. 不新增红核对（「旧门红 by design」判据）

兄弟门在 pre-H18 与 post-H18 dev 树上各跑一遍 `--live`，红集合**完全一致**：

| 门 | post-H18 | pre-H18 | 判定 |
|----|----------|---------|------|
| h9 | 4 FAIL | 同 4 FAIL | 既有（记录数据/规格表 meta） |
| h10 | 1 FAIL | 同 1 FAIL | 既有（dev `sf_trust_*` 空串，H15 只修了生产） |
| h11 | 4 FAIL | 同 4 FAIL | 既有（dev 状态 + Form 12 sink 断言） |
| h12 | 4 FAIL | 同 4 FAIL | 既有（4 页零漂移基线滞后） |
| h13 | 12/12 绿 | — | 无红 |
| h14 | 1 FAIL | 同 1 FAIL | 既有（负控断言） |

`--source` 半场的版本字面量红（h9 要 2.10.82 / h10 要 2.10.84 / h12 要 2.10.86）在 H18 前后相同——本批**前台版本不 bump**，属既有红。无任何工具断言 `sf-mb-tables` 版本号，1.0.0→1.1.0 不新增红。

## 5. 遗留 / 备注

- **生产尚未设任何槽位**：21 条记录的三个新 meta 全空 = 全站仍显示工厂车间图（by design，等运营逐条填）。
- 顺带修两处均落地：`gallery_ids` 描述改准（CSV）；帧②③④尺寸差异已**明确标注**（注释写清是真实像素、1:1 stage 下零布局影响，统一纵横比 = 重拍素材，不在标记层修）。
- H18 遗留待办（不在本批范围）：配方页 Product JSON-LD `image` 仍取剂型图（H17 遗留，functions.php `:7013` 附近）。
- dev 的 7 个 `sf_trust_*` 空串仍未同步（既有红，与 H18 无关）。

## 6. 关键文件

- `sinofresh-theme/functions.php`（帧序规则 + 尺寸注释）
- `sinofresh-theme/inc/formula-admin.php`（注册/规格/渲染/保存/1.1.0）
- `sinofresh-theme/assets/admin/sf-mb-tables.js`（单图选择器）
- `tools/h18_gate.py`、`tools/h18_capture.py`、`tools/h18_shots.py`
- `docs/scan-formula-gallery-per-record-2026-09-30.md`（扫帧报告）
- `docs/h18-shots/*.png`（4 张证据）
