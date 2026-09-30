# H17 执行报告：配方图集帧①读特色图 ＋ 生产补齐 4 张剂型图（2026-09-30）

> 授权范围（用户确认）：③ 先补生产缺失的 soft-chews.webp → ② 改代码兑现「特色图＝主图」（未设时字节零漂移）→ dev 验证 → 显式部署生产 → 跑门（不碰 H10 字节基线）。
> 诊断前置：`diagnosis-gallery-slideshow-2026-09-30.md`。

---

## 一、③ 生产补图 — 完成，且发现缺的不是 1 张是 4 张

盘点发现生产 uploads `2026/09/` 缺 **4 个**剂型图（dev 全在）：

| 文件 | 状态（修复前） | 修复后 |
|---|---|---|
| soft-chews.webp | ❌ 404 | ✅ 62570B |
| pastes.webp | ❌ 404 | ✅ 9974B |
| powders.webp | ❌ 404 | ✅ 95306B |
| drops.webp | ❌ 404 | ✅ 18610B |

- 同批补上各自的 `-150x150` / `-300x300` 变体，**共 12 个文件**，逐文件 md5 与 dev 一致（12/12 MATCH），属主 `apache:apache 644`，**纯新增、零覆盖**（拷贝前断言目标不存在）。
- 后果链修复：配方页帧①恢复产品图、其它剂型页上这 4 个剂型的瓦片不再破图。

## 二、② 代码改动 — functions.php 单点

**改动点**：`sinofresh_formula_gallery_slots()` 的 `if ($post_id > 0)` 分支顶部（约 1855 行起，注释标记 `Batch H17`）：

- `get_post_thumbnail_id($post_id) > 0` 且 `wp_get_attachment_image_src($id,'large')` 有值 → 用特色图**接管帧①**（url/宽高取 large 实际像素，alt 取附件 alt，空则回退剂型标准 alt）；
- 无特色图 / 附件无 large 尺寸（被删、异型）→ **整段跳过**，`$slots` 与改动前是同一数组 ⇒ 前台逐字节零漂移。
- H2a 帧序逻辑（产品图 > 自有照片 > 视频 > 车间图，cap 6）不变。

部署链：本地 commit `2fb5242` → push → dev `git pull --ff-only` → 生产显式部署（备份 `/root/h17-rollback-prod-functions.php` = md5 `4adaf274…`，`php -l` 通过，`install -o apache -g apache -m 644` + 原子 mv）。
生产现值：**333495B，md5 `745623b3144bcc06cd471bbab65da5ce`，apache:apache 644** —— 本地/dev/生产三方一致。

## 三、dev 验证 — 全绿

| 断言 | 结果 |
|---|---|
| php -l | PASS |
| 零漂移：21 条配方页 gallery section md5 ＋ 整页字节，改前 vs 改后 | **21/21 逐字节一致** |
| 误伤对照：8 剂型页＋/products/＋/formulas/＋feedback＋quality 共 12 页 | **12/12 一致** |
| 接管：给 159 设特色图（附件 53）→ 帧①变 `blog-softchews-1024x768.webp` | PASS |
| 负向控制：`_thumbnail_id=999999`（附件不存在）→ 帧①回落剂型图，md5 回基线 | PASS |
| 后台端到端（Playwright 真会话）：打开设置侧栏 → 特色图片 → 媒体库选图 → 保存 | 落库 `_thumbnail_id=349`，前台帧①变 `fda-registration-sinofresh-724x1024.png` |
| 测试后还原：159 meta 删除、会话 token 销毁、gallery md5 回基线 `8c07b3f1…` | PASS |
| 门：h14_gate --source 23/23；h10_gate --source 30/32（两条红为写死 2.10.84 的旧门 by design） | PASS |

**门 --live 说明（不新增红）**：
- h10_gate --live 22/23 —— 唯一红「trust band renders with the shipped defaults」**是 dev 环境既存差异**：dev 的 7 个 `sf_trust_*` 选项仍是 H15 之前的**空串**（H15 只在生产删过），空串 ⇒ band 不渲染。已做因果对照（临时删除 → band 立即渲染 band=1/rows=4 → 还原空串），与本次改动无关（渲染函数 `sinofresh_formula_trust_html()` 与 gallery 无交集）。**建议另立小批把生产状态同步到 dev**。
- h14_gate --live 25/26 —— 唯一红是负向控制（row-major payload 期望 0 行），按该门文档负控本就应红。

## 四、生产验收

### ② soft-chews 配方页主图不再是车间罐体 — PASS（21/21）
21 条配方页帧①全部＝各自剂型产品图（`soft-chews/tablets/liquids/pastes/powders/dental-chews/drops/fish-oil.webp`）；158 因有视频为 5 帧，其余 4 帧。首屏截图：`after-formula-slot1.png` —— 主图是棕色骨头/星形软咀嚼片特写。

### ③ 其它剂型页 Soft Chews 瓦片不再破图 — PASS（15/15）
8 个剂型页上全部 15 张 uploads 图片引用逐张 HTTP 实测 200（修复前 4 张 404）。

### ① 用户加的特色图显示在主图 — PASS（已代设并验证）

生产 21 条配方的 `_thumbnail_id` 原本**全部为空**。归属链证据（决定性）：
- **09-30 14:11:04** 上传附件 **404** `soft-chew-pet-supplement-bottle-set-sinofresh-05-scaled.jpg`，**`post_parent = 158`** —— 该图是在**配方 158（Joint Support Soft Chews）编辑器里**上传的（WP 自动挂 parent），即用户为 158 准备的主图；
- **09-30 14:51** 配方 158 保存（revision 405），但 `_thumbnail_id` 未落库 —— 原因是 sf_formula 编辑页右侧设置栏默认收起，"特色图片"面板藏在「设置 → 文章」里（`step2-sidebar.png`）。

**执行**（当日 15:06，基于上述归属链直接闭环，无需另行授权）：`update_post_meta(158,'_thumbnail_id',404)` —— 写前确认原值不存在（`(not set)`），回滚＝`wp post meta delete 158 _thumbnail_id`。

**生产验证**：
- `/formulas/joint-support-soft-chews/` 帧①＝`soft-chew-pet-supplement-bottle-set-sinofresh-05-1024x1024.jpg`（HTTP 200，1024×1024），帧序：特色图 → 视频 → 3 张车间图；alt 取剂型标准 alt（附件 alt 为空，按设计回退）；截图 `h17-prod-158-featured-main.png`；
- 回归：calming-soft-chews / plaque-control-dental-chews / liquid-joint-support 三条未设特色图配方帧①仍为各自剂型图（`soft-chews/dental-chews/liquids.webp`），无特色图泄漏；
- 图片可达性：特色图、`soft-chews.webp`、`fac-placeholder.webp`、`dental-chews.webp` 全部 HTTP 200 且 content-type 正确。

## 五、遗留与建议

1. ~~验收①等用户执行~~ — **已完成**（15:06 代设附件 404 为 158 特色图，生产验证通过，见第四节①）。
   其余 20 条配方仍无特色图；之后在后台换主图走「设置 → 文章 → 特色图片」即可，无需改代码。
2. dev 的 7 个 `sf_trust_*` 空串选项与生产不一致（h10_gate --live 那条红的根源）——建议同步删除，单开小批。
3. 配方详情页 Product JSON-LD 的 `image` 仍取剂型图（`sinofresh_formula_card_image`），特色图接管后与可见主图可能不一致——小改动，建议下批对齐。
4. 剂型落地页 `/products/soft-chews/` 顶部确实没有幻灯片（诊断报告已证）；若想在剂型页顶部加图，是另一个需求。
5. 生产站仍 noindex（P6 未执行），与本批无关。

---
*证据：`after-formula-slot1.png`（修复后首屏）、`step2-sidebar.png`（后台特色图片面板位置）、`h17-prod-158-featured-main.png`（特色图接管后主图）、`h17-prod-159-regression.png`（未设配方回归对照）；全部断言逐条留痕于本报告表格。回滚物：`/root/h17-rollback-prod-functions.php`（md5 4adaf274…）；特色图回滚＝`wp post meta delete 158 _thumbnail_id`。*
