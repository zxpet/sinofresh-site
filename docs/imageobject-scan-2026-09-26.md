# ImageObject 结构化数据只读扫描报告（2026-09-26 17:00）

> 结论：**全站没有一张内容图带 ImageObject 结构化数据**，Google 图片元数据要求（图片许可/版权标注）**不满足**。方案见文末，等确认再实施。

## 1. 全站检索结果

关键词 `ImageObject` / `contentUrl` / `creditText` / `copyrightNotice` / `license` 在主题源码（functions.php / inc/ / templates/ / parts/ / assets/js/）全量 grep：

- 唯一命中：**functions.php:7161** —— Article schema 的 `publisher.logo`，形态＝`ImageObject { url }`（只有 url 一个字段）。
- `contentUrl`、`creditText`、`copyrightNotice`、`license`、`creator`：**零命中**。

## 2. 实际输出（dev live 实测五页，浏览器 UA）

| 页面 | ld+json 块数 | 图片相关字段 | 形态 |
|---|---|---|---|
| 首页 / | 2 | Organization/logo | 纯 URL 字符串 |
| /about/ | 2 | Organization/logo | 纯 URL 字符串 |
| /formulas/joint-support-soft-chews/ | 6 | Product/image ＋ Organization/logo | 纯 URL 字符串 |
| /test-article/（文章） | 3 | Article/image ＋ **Article/publisher/logo（唯一 ImageObject，仅 url）** | URL ＋ ImageObject{url} |
| /case-study-us-brand-owner-soft-chews/ | 3 | 同上 | 同上 |

- **渲染方式：纯服务端**。10 个 JSON-LD 生成器全部在 functions.php，`wp_head` / 渲染期 PHP echo，零 JS 注入（行号：ItemList 1587、FAQPage 5406/5495、HowTo 5432、BreadcrumbList 5790、Product 6854/6958、Organization 7035、Article 7137、Service 7437）。
- **Google 要求判定：不满足**。Google 图片元数据（Licensable 标记）要求 `contentUrl`（必填）＋ `creator`/`creditText`/`copyrightNotice`/`license` 至少其一。现状所有内容图连 ImageObject 都不是（只是 URL 字符串）；唯一 ImageObject 还是 logo，且缺 contentUrl。（注：logo 本身不需要这类元数据，真正缺的是文章/产品内容图。）

## 3. 生成器与数据源（不是单一生成器，四路来源）

| 用途 | 位置 | 图片数据源 |
|---|---|---|
| formula 详情页 Product.image | `sinofresh_formula_card_image()` functions.php:685 | 按 slug **glob uploads 文件名** `{slug}.webp`，新上传优先——**没有 attachment ID，无任何元数据可读** |
| 剂型页 Product.image | functions.php ~6821 | 模板解析＋文件名推断，同样无 attachment ID |
| 文章 Article.image | functions.php ~7125 | `get_the_post_thumbnail_url()`——**有 attachment ID**，可读媒体库 caption/description |
| Organization/Article logo | functions.php ~7030 / ~7158 | `custom_logo` theme mod → attachment |

**加字段的改动点**：Article 生成器一处即可把 `image` 从字符串升级为 ImageObject（attachment ID 在手，媒体库字段可直接读）；两个 Product 生成器的图是文件名推断的，要先给图落媒体库（或建 slug→ID 映射）才有元数据可读。

## 4. 方案（待确认）

**方案 A（推荐，小步）**：只升级文章页 Article.image 为 ImageObject——`contentUrl`（特色图全尺寸 URL）＋ `copyrightNotice: "© Shandong SINO FRESH Pet Food Co., Ltd."` ＋ `license`（写死站点版权说明页 URL 或官方版权声明 URL）。版权主体**代码写死**（全站图均为公司自制/自有，WP 核心媒体库本无 credit/license 字段，逐图维护不现实）；个别特殊来源图以后可用自定义 meta 覆盖。改动一处＋一个门，字节影响仅文章页。

**方案 B（彻底，联动 H12 图片方案）**：抽统一 helper `sf_image_object($attachment_id)`，Article＋两个 Product 一起升级。前提＝产品图先入媒体库拿到 attachment ID（H12 的图片方案机制已就位、库还空，正好衔接），改动面和门的影响都大一号。

**预期收益说明**：这类标记影响的是 Google 图片结果里的「可许可（Licensable）」徽章与版权信息展示，对关键词排名无直接加分——如果目的是版权保护声明/品牌形象，值得做；如果期待 SEO 排名提升，收益有限。
