# 诊断：剂型页「顶部幻灯片图改不了」（2026-09-30，只读扫描，未改任何代码/数据）

## 0. 一句话结论

**/products/soft-chews/ 顶部根本没有幻灯片**（截图+DOM 双证）。你看到的"幻灯片"是**配方详情页**（如 `/formulas/joint-support-soft-chews/`，面包屑显示 Products / Soft Chews / …）顶部的产品图集——它的主图**按剂型 slug 读 uploads 里的固定文件，从不读配方的特色图**；而后台表单的中文提示却写着"主图用特色图片面板设置"。**承诺的入口没有实现，这就是"加了图没生效"的根因。**

另发现一个并发问题：**生产 uploads 缺 `soft-chews.webp`**，导致每条 soft-chews 配方的主图帧被静默丢弃、其它剂型页上 Soft Chews 瓦片破图。

---

## 1. 先纠正前提：三处"幻灯片"，你在哪一页

| 页面 | 顶部有什么 | 有无幻灯片 | 证据 |
|---|---|---|---|
| `/products/soft-chews/`（剂型落地页） | 纯色 hero 带：面包屑 + H1 + 副标题 + 两按钮，**无任何图片** | ❌ 无 | 截图 `shot-prod-softchews.png`；DOM 中 `sf-hero-slider/sf-slide/sf-gallery` 全部 0 命中；加载的 JS 里也没有 hero-slider.js / formula-gallery.js |
| `/formulas/<slug>/`（**配方详情页**，21 条） | **主图 + 左侧缩略图条（Photos/Video 切换）** —— 就是你说的"幻灯片" | ✅ 有 | 截图 `shot-prod-formula.png`；DOM `sf-gallery` 23 处命中 |
| 首页 `/` | hero 轮播 4 帧 | ✅ 有（另一处） | `templates/front-page.html` 硬编码 `hero1-exterior/hero2-lab/hero3-line/hero4-warehouse.webp` |

用户看到配方详情页面包屑里的 **Products / Soft Chews**，把它记成"产品详情页 /products/soft-chews/"——实际 URL 是 `/formulas/joint-support-soft-chews/` 这类。

## 2. 配方详情页图集（"幻灯片"）的数据源

实现：`functions.php` 短码 `[sf_formula_gallery]`（`sinofresh_formula_gallery()`，约 1916 行起），由 `templates/single-sf_formula.html` 调用；`assets/js/formula-gallery.js` 负责缩略图条/Photos-Video 切换。**不在任何插件里，纯主题代码。**

帧序由 `sinofresh_formula_gallery_slots()`（约 1788 行）决定，"强者优先"排序后截到 6 帧：

| 帧 | 来源 | 类型 | 每条配方独立？ |
|---|---|---|---|
| ① 主图（产品图） | `sinofresh_formula_card_image($form)`：按**剂型 slug** 在 uploads 里 glob `<剂型>.webp`（如 `uploads/2026/09/soft-chews.webp`） | **B：写死的文件名约定**（按剂型，不按配方） | ❌ 同剂型所有配方共用同一张 |
| ②-④ 车间图 | `fac-placeholder.webp` / `fac-packaging.webp` / `fac-line.webp`，文件名硬编码 | A：固定文件 | ❌ 全站共用 |
| 配方自己的照片 | meta `sf_formula_gallery_ids`（后台 Media 组「Gallery images」字段） | C：媒体库 + 配置 | ✅ |
| 视频 | meta `sf_formula_video_url`（YouTube URL） | C | ✅ |

**四个选项里没有 D（特色图）——全主题 grep 证实**：`get_the_post_thumbnail` / `_thumbnail_id` 只有两处——① 博客文章的 Article JSON-LD（仅 `is_singular('post')`，与配方无关）；② 后台"缺失必填项"检查。**前台没有任何代码读 sf_formula 的特色图。**

## 3. 为什么"在配方特色图里加了图"没生效

- 后台 `inc/formula-admin.php:95`「Gallery images」字段的中文提示：**"主图不用这里设——用编辑器右侧的特色图片面板"**
- 同文件 684 行，phase-1 缺失项检查也把 `Featured image (main photo)` 列为缺失
- **但前台渲染层从未实现"特色图=主图"**——主图永远取剂型静态图

⇒ 后台的编辑指引与前台实现脱节，属于**真 bug**（文档性承诺未兑现）。另注：dev 上 21 条配方的 `_thumbnail_id` **全部为空**——你加的特色图要么没保存成功，要么是加在生产后台；但无论加在哪，现状都不会显示。

## 4. 并发发现：生产缺 `soft-chews.webp`（建议尽快补）

| 文件 | dev | 生产 |
|---|---|---|
| `uploads/2026/09/soft-chews.webp` | ✅ 200（62,570B，磁盘在） | ❌ **404** |
| `tablets.webp` / `dental-chews.webp` / `fac-*.webp` | ✅ | ✅ 200 |

生产上这张图缺失的连锁后果：
1. `sinofresh_formula_card_image('soft-chews')` glob 落空 → 帧①被静默丢弃 → **每条 soft-chews 配方详情页的主图直接显示车间图**（截图所见即此状态，主图是不锈钢罐车间而非产品）；
2. 其它剂型页（/products/tablets/ 等）"Explore more dosage forms"里 Soft Chews 瓦片破图；
3. 也解释了生产上 joint-support 配方的帧序是"视频 + 3 张车间图"。

## 5. 正确的替换入口（现状，不改代码能做到的）

| 想改什么 | 入口 | 是否要改代码 |
|---|---|---|
| 某条配方的补充照片（缩略图条里的第 2 张起） | 后台 → Formulas → 编辑该配方 → **Media 组 → Gallery images**（多选媒体库图） | 否 |
| 某条配方的视频 | 同上 → **YouTube URL** | 否 |
| **主图（帧①）** | ❌ 无后台入口。两条路：a) 上传同名 `<剂型>.webp` 覆盖 uploads 里的剂型图（**同剂型 21 条配方 + 剂型卡片全部跟着变**）；b) 改代码（见下） | 是/部分 |
| 首页 hero 轮播 4 帧 | `templates/front-page.html` 硬编码，需改模板 | 是 |

### 若要兑现"特色图=主图"的承诺（修复方案，供决策，未实施）

最小改动：在 `sinofresh_formula_gallery_slots()` 里，当 `get_post_thumbnail_id($post_id) > 0` 时用它替换/前插帧①。风险点：① 需要按"产品图 > 特色图？"定优先级；② 帧宽高声明要取 `wp_get_attachment_image_src(.., 'large')` 实际尺寸；③ 动 `functions.php` 会触碰 H10 字节基线，建议单开批次走 scan→方案→确认→实施。

## 6. 8 个剂型页：独立还是共用

- **剂型落地页本身没有幻灯片**；8 页各自的"Explore more"瓦片图**写死在各自模板文件**（`page-<slug>.html`），互不影响。注意生产上 `/products/soft-chews/` 渲染的是 **DB 副本（ID 396）**，其中 6 张瓦片已被换成媒体库新图（`wp-image-325/394/395/397/399/400`），仅 Dental Chews 仍是老 `dental-chews.webp`——这正是 H16b 报告里"用户真实编辑留在副本、待反向同步"的那部分。
- **配方详情页图集**：帧①按剂型共用（同剂型所有配方同一张），帧②-④全站共用，只有「Gallery images / YouTube URL」按配方独立。
- **首页 hero 轮播**：4 帧硬编码，与配方、剂型都无关。

## 7. 需要你确认的（确认后才进入修复批次）

1. 你加特色图操作的是**生产后台**还是 dev？（dev 上 21 条 `_thumbnail_id` 全空）
2. 修复方向选哪个：**A. 兑现特色图=主图**（改代码，后台现有指引成立）；**B. 不改代码**，改用「Gallery images」字段 + 补齐生产缺失的 `soft-chews.webp`（把后台提示文案改成与实际行为一致）；
3. 生产缺的 `soft-chews.webp` 是否直接从 dev scp 补上（62,570B，md5 可对齐）——这是独立于上面选择都该修的。

---
*证据文件：`shot-prod-softchews.png`（剂型落地页首屏）、`shot-prod-formula.png`（配方详情页首屏）；扫描方式：curl 抓 dev/prod HTML + 主题源码 grep + dev `wp eval`/`wp post meta` 实查 + Playwright 首屏截图。全程只读。*
