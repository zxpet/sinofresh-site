# H17 执行 — 配方图集帧①读特色图 ＋ 生产补齐 4 张剂型图（已上线）

> 2026-09-30 ｜ 诊断：`docs/diagnosis-gallery-slideshow-2026-09-30.md` ｜ 详报：`docs/h17-fix-execution-report-2026-09-30.md`

## 一句话

「幻灯片图改不了」的根因＝**后台承诺"主图用特色图片面板"，但前台从未读过特色图**（帧①固定按剂型 slug 取 uploads 的 `<剂型>.webp`）。本批：①生产补齐**4 张**缺失剂型图（不止 soft-chews）；②`sinofresh_formula_gallery_slots()` 单点改造——特色图有值接管帧①、无值整段跳过（**字节零漂移**）；③dev 21/21 零漂移＋接管＋负控＋后台真会话端到端全绿后显式部署生产，**21/21 配方页主图恢复产品图、8 剂型页 15/15 图片引用全 200**。

## 关键改动与部署

- 唯一文件 `sinofresh-theme/functions.php`：md5 `4adaf274…`（331822B）→ **`745623b3…`（333495B）**，本地/dev/生产三方一致；git `2dbbfa9` → **`2fb5242`**（已 push，dev 已 ff）。未 bump 版本。
- 生产显式部署：备份 `/root/h17-rollback-prod-functions.php` → `php -l` → `install apache:apache 644` → 原子 `mv`。
- 生产补图：`uploads/2026/09/` 补 soft-chews / pastes / powders / drops 四剂型的原图＋150/300 变体共 **12 个文件**，逐文件 md5 与 dev 一致，纯新增零覆盖。

## 生产验收（三条全绿）

| # | 标准 | 结果 |
|---|---|---|
| ② | soft-chews 配方页主图不再是车间罐体 | ✅ 21/21 配方页帧①＝剂型产品图（158 有视频为 5 帧，其余 4 帧）；首屏截图 `after-formula-slot1.png` |
| ③ | 其它剂型页 Soft Chews 瓦片不再破图 | ✅ 8 剂型页 15 张 uploads 图片引用逐张 200（修复前 4 张 404） |
| ① | 用户加的特色图显示在主图 | ✅ **当日 15:06 已闭环**：附件 404 的 `post_parent=158`（在 158 编辑器里上传，归属链决定性）→ `update_post_meta(158,'_thumbnail_id',404)` → 生产帧①＝`soft-chew-…-05-1024x1024.jpg`（200，截图 `h17-prod-158-featured-main.png`）；未设特色图的配方帧①无泄漏（回归截图 `h17-prod-159-regression.png`） |

## 途中发现

- **特色图面板藏得深**：sf_formula 编辑页右侧设置栏默认收起，"特色图片"在「设置→文章」里（截图 `step2-sidebar.png`）——这就是用户"加了图没生效"的直接原因（图传到了媒体库但没设成特色图）。
- **dev 与生产的 `sf_trust_*` 不一致**：dev 仍留着 H15 之前的 7 个空串选项 ⇒ Factory & Trust 在 dev 不渲染（h10_gate --live 唯一红）。因果已对照证实，dev 已还原原状；建议另立小批同步。
- h14_gate --live 25/26（唯一红是 by-design 负控）；h10_gate --source 30/32（两条红为写死 2.10.84 的旧门）。

## 遗留

① 其余 20 条配方仍无特色图；后台换主图走「设置 → 文章 → 特色图片」，无需改代码。② 配方页 Product JSON-LD 的 `image` 仍取剂型图，与接管后的可见主图可能不一致，建议下批对齐。③ dev `sf_trust_*` 同步。④ 生产站仍 noindex（P6 未执行）。
