# Batch 2D · Step 2 — 图集区（主图 + 缩略图）现状扫描（只读，零改动）

> 扫描时间 2026-09-20 23:2x　·　目标：`/products/{8 slug}/` 的 8 个剂型页
> 本次**没有改动任何主题文件**；所有线上访问均带 `-u 'sfdev:…'`。
> 复现命令见文末。上一步（Step 1 活性成分+保证值表）的档案：`docs/batch2d-step1.md`

---

## 0. 本批边界（按你 22:0x 的四条拍板）

| # | 拍板 | 对本次扫描的约束 |
|---|---|---|
| 1 | 水印图可用作占位，**只验证几何/间距**；实拍替换＝上线阻塞项 | 本批不去水印、不做裁切规避 |
| 2 | 两张 placeholder 只用一张（我判断选哪张并给理由） | 选型理由见 §4.1 |
| 3 | **只做图集网格，不做灯箱**（灯箱独立排后续批次） | 灯箱相关（`.sf-lb` / 入队 / about.js·quality.js）本批**只盘不接** |
| 4 | 18 张实拍图 → 独立「上线前必做」清单 | ⚠ 见 §2.4：实测不是 18 张，是 **34 张** |

---

## 1. 【点1】8 个剂型页图集区现状

### 1.1 结论：**没有图集区，一张产品图都没有独立展示位**

实测线上 8 页（`<img>` 计数按元素出现次数）：

| slug | 渲染字节 | `<img>` 总数 | hero 内 `<img>` | `figure.sf-fcard__media` | `figure.sf-tile__media` | `<h2>` |
|---|---|---|---|---|---|---|
| soft-chews | 177 789 | 15 | **0** | 4 | 7 | 7 |
| tablets | 167 408 | 14 | **0** | 3 | 7 | 7 |
| powders | 165 819 | 14 | **0** | 3 | 7 | 7 |
| pastes | 162 323 | 13 | **0** | 2 | 7 | 7 |
| drops | 162 417 | 13 | **0** | 2 | 7 | 7 |
| liquids | 163 670 | 13 | **0** | 2 | 7 | 7 |
| fish-oil | 163 057 | 13 | **0** | 2 | 7 | 7 |
| dental-chews | 170 263 | 14 | **0** | 3 | 7 | 7 |

`<img>` 总数的构成（以 soft-chews 为例，实测 src 逐一列出）：

```
logo ×2                                      ← parts/header.html 与 footer
本页剂型图 ×4   soft-chews.webp              ← 公式卡内的配图槽（4 条配方重复同一张）
兄弟剂型图 ×7   tablets/powders/.../dental-chews.webp  ← 块 11「Related Dosage Forms」瓦片
语言旗 ×2       translatepress flags/en_US.svg, zh_CN.svg
```

### 1.2 三个关键事实

1. **hero 无图。** `<section class="wp-block-group sf-hero-inner">` 内 `<img>` ＝ 0（8/8 页）。
   hero 的底色来自 CSS：`style.css:1879  .sf-hero-inner { background-color: #2E6B54; }` —— **纯色带，没有任何背景图**
   （全表 `background-image: url(...)` 命中数 = **0**）。
2. **本页自己的剂型图只在两处出现**：
   - 公式卡配图槽 `figure.sf-fcard__media`（soft-chews 4 次、tablets/powders/dental-chews 3 次、其余 2 次）；
   - Product JSON-LD 的 `image` 字段（1 次，非 `<img>`）。
   → 也就是说：**该剂型唯一的产品图，被当成卡片的配图重复 N 次，从来没有独立的"图集/主图"展示位。**
3. **块 11 的 7 张瓦片不是本页图集**，是"其他 7 个剂型"的交叉销售瓦片（`className: sf-tile`，每张外面包 `<a href="/products/{other}/">`）。

### 1.3 页面骨架（8 页一致，逐字同构）

```
Block 2  Hero                 section.sf-hero-inner              （深绿 #2E6B54，无图）
Block 3  Standard Formulas    section#formulas.sf-formulas       （白，H2 + [sf_formula_grid]）
Block 4  Configurator         section#configurator               （白，H2 + 27KB wp:html）
Block 5  Spec table           section.sf-spectable               （白，无 H2）
   ── 2D-S1 新增 ──           section#actives.sf-actives         （白，[sf_formula_actives] → H2）
Block 9  How We Work          section.has-bg-light-background    （浅灰，H2）
Block 10 FAQ                  section > .sf-faq                  （白，H2）
Block 11 Related Dosage Forms section.has-bg-light-background    （浅灰，H2 + 7 瓦片）
Block 12 CTA Inquiry Form     section#inquiry-form               （深绿，H2 + GF 表单）
```

- 底色带：**只有 hero 与 inquiry-form 有 CSS/预设底色**；`.sf-formulas` / `.sf-spectable` / `.sf-actives` 都是白，
  **相邻白带已经是现状**（formulas→configurator→spectable→actives 四连白）。
- `<h2>` 渲染数 = **7**：模板内 6 个（Standard Formulas / Build Your … Formula / How We Work / FAQ / Related Dosage Forms /
  Request a … Quote）＋ 2D-S1 短代码产出的 1 个（Active Ingredients & Guaranteed Analysis）。
  ⇒ 这解释了第 1 批浏览器核验里"点轨 6→7"的观测。

---

## 2. 【点2】图片资源清单（含尺寸、格式、水印位置）

### 2.1 目录与总量

- 唯一目录 `/wp-content/uploads/2026/09/`
- 实测：**70 个 `.webp` + 1 个 `coa-sample.pdf`**；另有大量 macOS `._*` 影子文件（每个真实文件配一个 163 B 的影子，**必须过滤**）
- 格式：全部 **lossy WebP**（`VP8 ` 编码，非 VP8X/VP8L）

### 2.2 按用途分类（去重后，已剔除 `-150x150/-300x300/.../scaled` 等尺寸变体）

| 类别 | 张数 | 尺寸 | 对象 |
|---|---|---|---|
| **剂型产品图** | **8** | **720×720（1:1）** | dental-chews / drops / fish-oil / liquids / pastes / powders / soft-chews / tablets |
| 厂区 | 6 | 800×600（4:3） | fac-cleanroom / fac-lab / fac-line / fac-packaging / fac-retention / fac-warehouse |
| QC | 6 | 800×600 | qc-batching / qc-coa / qc-finished / qc-inprocess / qc-raw-material / qc-retention |
| 设备 | 3 | 800×600 | equip-aas / equip-gc / equip-hplc |
| 首页 hero | 4 | 1920×1080（16:9） | hero1-exterior / hero2-lab / hero3-line / hero4-warehouse |
| placeholder | 2 | **1100×733** / **800×600** | fac-placeholder / equip-placeholder |
| 其它 | 5 | 1200×900 / 800×1100 / 1920×1080 | blog-choose / blog-compliance / **blog-softchews** / coa-sample / video-cover |
| 头像·团队·证书·logo | 6 / 5 / 4 / 7 | 200×200 / 600×600 / 400×550 / 多尺寸 | avatar-* / team-* / cert-* / sino-fresh-logo-* |

**剂型图的尺寸变体（重要）**：

| slug | 基图字节 | 150×150 | 300×300 |
|---|---|---|---|
| soft-chews | 62 570 | ✓ | ✓ |
| tablets | 33 902 | ✓ | ✓ |
| powders | 95 306 | ✓ | ✓ |
| pastes | 9 974 | ✓ | ✓ |
| drops | 18 610 | ✓ | ✓ |
| fish-oil | 36 820 | ✓ | ✓ |
| **liquids** | 13 422 | **✗** | **✗** |
| **dental-chews** | 42 998 | **✗** | **✗** |

### 2.3 ⚠ 水印：实测位置（这是本批最重要的素材约束）

第 0 批已做蒙太奇取证（`docs/b2d-step0-shots/watermark-montage-18img.png`）。本轮我**逐张目视了 4 张关键图**，记录构图与水印位置：

| 文件 | 尺寸 | 我看到的画面 | 水印位置与形态 |
|---|---|---|---|
| `soft-chews.webp` | 720×720 | 棕色软咀嚼，星形/骨形/圆球，散落在浅灰台面，45° 俯视微距 | 右下角，**完整在画面内**；压在浅灰底色上，**低对比、四个里最不显眼** |
| `fac-placeholder.webp` | 1100×733（3:2） | GMP 洁净车间，正中大型不锈钢配液罐，右侧灌装线、左侧输送台，后方整排大窗，镜面环氧地坪；**一点透视、左右近对称** | 右下角，**完整在画面内、文字可读**；落在浅色地坪上 |
| `equip-placeholder.webp` | 800×600（4:3） | **同一场景、同一机位**的 4:3 裁切 | 右下角，**被画框切掉一半** —— 只剩 "AI" 与半个残字，**看起来像渲染瑕疵而不是水印** |
| `blog-softchews.webp` | 1200×900（4:3） | 琥珀色玻璃罐（空白牛皮纸标签）＋牛皮纸站立袋（开窗），内装骨形/圆形软咀嚼；木桌、纱窗柔光、麻绳道具 | 右下角，**被画框切掉一部分**（残留 "A"/"WO" 碎片） |
| `fac-packaging.webp` | 800×600（4:3） | 瓶装灌装/旋盖线，白色 HDPE **空白标签**瓶在输送带上，三名白衣+口罩+发帽操作工 | 右下角，被画框切掉一部分 |

**三条硬结论**：

1. **CSS 救不了水印**：多数水印在画面内部（不在最角落）。以 `hero3-line` 为例水印约在 `x≈1460/1920, y≈965/1080`（距右缘 ~24%、距下缘 ~11%）
   ⇒ 想靠 `object-fit: cover` 稳定裁掉，需要吃掉约 **30% 宽 × 20% 高**，构图直接崩。
2. **两张 placeholder 同场景**（同角度、同罐体布局）⇒ 同页并排＝重复图。**本批只用一张**（你已拍板）。
3. **"切边"比"完整"更难看**：`equip-placeholder` / `blog-softchews` / `fac-packaging` 的水印被画框切断，留下孤立残字，
   访客第一反应是"图坏了"；而完整水印虽更"明显是水印"，但至少是完整的图形元素。

### 2.4 ⚠ 关于「18 张」这个数字（需要更正）

第 0 批说的是「**抽查 18 个对象，零例外**」—— 那是**抽样数**（8 剂型图 + 2 placeholder + 8 厂区/QC 图），不是全库总数。

本轮全量实测：**带 AI 水印的实拍/渲染照片共 34 张**

```
8  剂型产品图      ← 最优先（就是产品本身，出现在产品页与公式卡）
6  厂区 fac-*
6  QC qc-*
3  设备 equip-*
4  首页 hero1-4
2  placeholder
5  其它（blog-choose / blog-compliance / blog-softchews / coa-sample / video-cover）
────────────────────────
34 张
```

（不带的：avatar 6 / team 5 / cert 4 / logo 7 —— 这些是图标、人物照与证书缩略图，另有来源。）
⇒ 「上线前必做」清单按 **34 张**列，而不是 18 张。详见 §9。

### 2.5 ⚠⚠ 本批最卡的一条：**每个剂型只有 1 张产品图，凑不出「3-4 张缩略图」**

全库枚举后确认：每个剂型**只有** `<slug>.webp` 一张（外加 150/300 两个同内容缩小版）。没有第二视角、没有包装图、没有细节图。

可用的"产品语义"图总共只有：

| 图 | 语义 | 适用范围 |
|---|---|---|
| `<slug>.webp` ×8 | 成品微距 | 各自那 1 页 |
| `blog-softchews.webp` | **包装**（空标签＝私标，很贴 OEM 主题） | **仅 soft-chews**（金色软咀嚼，其余 7 个剂型对不上） |
| `fac-packaging.webp` | 瓶装灌装线（空标签瓶） | 8 页通用，但语义是"产线"不是"产品" |

⇒ **你给的规格「主图 + 3-4 张缩略图」在本批无法用真实素材填满。** 这是需要你定的第一个阻塞项，三个方案见 §4.3。

---

## 3. 【点3】可复用 CSS/JS —— 有没有现成轮播组件？

### 3.1 结论：**没有轮播/幻灯片组件，但有一套现成的"照片栅格 + 渐进增强"语言必须照抄**

`assets/js/` 全量 14 个文件，逐个判定：

| 文件 | 是什么 | 可否复用 |
|---|---|---|
| `hero-slider.js` (1.1.1) | **首页** hero 全幅轮播（**仅 `is_front_page()` 入队**） | ✗ 与产品图集无关（全幅背景轮换，不是主图+缩略图） |
| `about.js` (1.3.0) | **`.sf-fac` 图集 → 灯箱**（`figure.wp-block-image img` 收集缩略图）+ 视频海报 + reveal | ⚠ 灯箱按你的拍板本批不接；**但它的"渐进增强"写法是本批的模板** |
| `quality.js` (1.1.0) | 证书缩略图 → 灯箱（**`.sf-lb` 第二份实现**）+ 证书条 | ✗ 同上 |
| `cert-modal.js` | 证书申请弹窗（`<dialog>`） | ✗ |
| `configurator.js` (2.3) | 配置器 | ✗（**但它定义了本批必须避让的类名空间**） |
| `formulas.js` (1.1.0) | K1 CTA 滚动 + K2 JSON 消费 | ✗（**实测它不碰任何 `img`/`figure`** → 零交互，见 §7） |
| `formula-filter.js` (1.0.0) | 档案页筛选 | ✗ |
| `toc-nav.js` (2.0.0) | 点轨 TOC | ⚠ **强相关**：它按 `h2` 建轨，新增 H2 会加一颗点（见 §7.4） |
| `ui-components.js` | cookie 横幅 + 联系浮层 + 回顶 | ✗ |
| `basket.js` / `quote-cta.js` / `mobile-nav.js` / `sticky-header.js` / `interactions.js` | 其它 | ✗（实测均不碰 `img`/`figure`） |

**全仓 `sf-gallery` / `sf-slide`（除首页）/ `swiper` / `carousel` / `slideshow` / `lightbox` 在模板层均 0 命中。**

### 3.2 必须照抄的现成语言：`.sf-fac`（About 页「Inside Our Factory」）

这是站内**唯一一处"照片栅格"**，而且做法完全正确，本批应当复刻而不是另创：

```html
<!-- templates/page-about.html:430 -->
<!-- wp:gallery {"className":"sf-fac","columns":3,"linkTo":"none","style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->
<figure class="wp-block-gallery has-nested-images columns-3 sf-fac">
<!-- wp:image {"sizeSlug":"large","linkDestination":"none","className":"sf-fac__item"} -->
<figure class="wp-block-image size-large sf-fac__item"><img src="…/fac-cleanroom.webp" alt="…" width="800" height="600" loading="lazy"/></figure>
<!-- /wp:image -->
… ×6
```

```css
/* style.css:4631–4696 */
.sf-fac { display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important; gap:10px !important; }
.sf-fac > .wp-block-image {
	width:100% !important; max-width:100% !important; margin:0 !important;  /* ← 必须 !important，见段内注释 */
	overflow:hidden; border-radius:8px; aspect-ratio:4/3;
	box-shadow:0 2px 12px rgba(0,0,0,.08); transition:box-shadow .25s ease; cursor:zoom-in;
}
.sf-fac > .wp-block-image img { width:100%; height:100%; object-fit:cover; object-position:center;
	transform:scale(1); transition:transform .25s ease; }
.sf-fac > .wp-block-image:hover img, … , .sf-fac > .wp-block-image.is-current img { transform:scale(1.05); }
@media (max-width:768px) { .sf-fac { grid-template-columns:repeat(3,minmax(0,1fr)) !important; gap:8px !important; } }
@media (prefers-reduced-motion:reduce) { .sf-fac > .wp-block-image, … { transition:none; } … { transform:none; } }
```

**段内注释记录的一条坑（直接适用于本批）**：
> core 的 gallery 样式表会把瓦片尺寸写成 `width: calc(33.33% - 16px)`（规则 `.wp-block-gallery.has-nested-images.columns-3 figure.wp-block-image:not(#individual-image)`），
> 瓦片会浮在永不填满的轨道里 ⇒ 我们的 `width/max-width/display/flex/margin` **必须带 `!important` 才能赢**。用 `wp:gallery` 就必须继承这条教训。

`.sf-eq`（`page-quality.html:97`）是同一模式的第二例。**信号：本主题用 `wp:gallery` + 自定类 + 少量 `!important` 是既定做法。**

### 3.3 灯箱现状（只盘不接，供后续独立批次估价）

| 项 | 实测 |
|---|---|
| CSS | `.sf-lb / __stage / __img / __bar / __btn(--prev/--next/--close) / __count / __request*` 定义在 **style.css:4701–7126**（≈ 425 行，**全局加载，剂型页本来就有**） |
| DOM | **全部由 JS 运行时 `createElement` 建**，模板层 0 静态引用 |
| 实现份数 | **2 份**：`about.js:107+`（82 行级）、`quality.js:66+` |
| 入队 | `about.js`→仅 `/about/`；`quality.js`→仅 `/quality/`；两者还各自绑定本页私有逻辑（reveal / 证书条 / 证书弹窗） |
| 结论 | **不能直接入队**，要做就得新增第三个入口或抽出共享文件 ⇒ 你选 C 是对的 |

`toc-nav.js:87` 有一条 `if (h.closest(".sf-lb, .sf-certmodal, dialog, template, [hidden], [aria-hidden='true']")) continue;` —— 灯箱内的标题不会进点轨。

---

## 4. 【点4】占位图插入方案

### 4.1 选型：**`fac-placeholder.webp`（1100×733，3:2，121 516 B）** —— 理由（基于我逐张目视，不是看文档）

| 判据 | fac-placeholder | equip-placeholder |
|---|---|---|
| 分辨率 | **1100×733**（≈ 0.81 MP） | 800×600（0.48 MP） |
| 容器适配 | 站内图集最大容器 ≈ 1200px 内容宽 − 左右 inset；1100 源 **不放大即可用** | 800 源在同等位置**会被放大 ~1.4×**，肉眼可辨软 |
| 构图完整性 | 3:2 宽幅，**左右两侧（输送台 / 灌装线）都在画内**，天花板与地坪都留有余量 | 4:3 裁切把**左侧输送台与右侧灌装线都切在框边**，像"裁歪了" |
| 水印观感 | **完整落在画面内**，落在浅色地坪上；虽可读，但是一个**完整的图形元素** | **被画框切掉一半**，只剩 "AI" + 半截残字 —— **读起来像渲染故障** |
| 对称性 | 一点透视、近左右对称，**缩略图裁成任意比例都不容易崩** | 同机位更紧，裁切余量更小 |

**唯一反向考虑，我如实说明**：完整水印比切边水印**更容易被认出"这是 AI 生成的"**。
但在你已拍板"本批接受水印、只验几何"的前提下，我反而认为完整水印**更安全** ——
它是**看得见、抹不掉**的提醒，不会在内部评审时被当成"这张是干净的"而溜到上线；切边的残字才最容易被误判成"已经没关系了"。

⇒ **选 `fac-placeholder.webp`。**

### 4.2 插入位置与底色

**位置：插在 Block 2（Hero）之后、Block 3（`#formulas`）之前**，成为新的第 2 个顶层 section。理由：

1. 产品页的常规信息序是 **hero → 产品图 → 规格/配方**；现在 hero 之后直接跳到"Standard Formulas"卡片墙，访客**从头到尾看不到这个剂型长什么样**（hero 无图，第一张图要滚到公式卡才出现）。
2. 不与任何既有锚点争位：`#formulas` / `#configurator` / `#actives` / `#inquiry-form` 都是显式 anchor，插入新 section 不改变它们。
3. 放在页面后半段（如 actives 之后）虽然零风险，但"产品图集"在 FAQ/Related 后面＝没有展示价值。

**底色：`backgroundColor: bg-light`（浅灰），不跟 hero 撞、也不与 `#formulas` 的白合并。**

- 现状底色节奏：hero**深绿** → formulas 白 → configurator 白 → spectable 白 → actives 白 → HowWeWork 浅灰 → FAQ 白 → Related 浅灰 → CTA 深绿
- 若图集用白：hero(深绿) → **图集(白)** → formulas(白) ⇒ 图集与 formulas **视觉连成一片**，没有分隔
- 用浅灰 ⇒ **深绿 | 浅灰 | 白** 三段分明；且 `.sf-fac` 的既有做法本身就是"瓦片浮在 `bg-light` 带上"
  （style.css:4627 原注释：「Tiles float on the section's bg-light band — the same token Core Values uses」）
  ⇒ **浅灰 + 带阴影的圆角瓦片是本主题已经确立的图集视觉语言。**

### 4.3 ⛔ 待你拍板：4 个槽位怎么填（因为真实素材只有 2 类）

规格是「主图 + 3-4 张缩略图」＝ 4 个槽位，但**每个剂型只有 1 张真图**。三个可选：

**方案 S1（推荐）— 主图＝本页剂型图，缩略图＝本页剂型图 + 3 张不同实景**
槽位：`<slug>.webp`(1:1) → `fac-placeholder`(3:2) → `fac-packaging`(4:3) → `<slug>.webp-300`(1:1)
- ✅ 4 张互不相同 → 几何验证**真实有效**（覆盖 1:1 / 4:3 / 3:2 三种比例，能暴露 letterbox 与裁切问题）
- ✅ 零新增资产；语义可解释（成品 → 车间 → 包装线 → 细节）
- ⚠ 8 页共用的只有中间 2 张，主图各页不同；**上线前替换清单多 3 个对象**

**方案 S2（最保守）— 只做 2 槽位：主图＝本页剂型图，缩略图＝fac-placeholder**
- ✅ 完全不违反"只用其中一张"；零重复；实现最简
- ❌ **不满足你要的 3-4 张**；缩略图条只有 2 个，横向布局（换行/滚动/居中）验证不足

**方案 S3 — 4 槽位全部用 fac-placeholder（含主图）**
- ✅ 最贴近"纯结构占位"的字面理解；替换时 4 处同一路径
- ❌ **4 张一模一样的缩略图**，看起来像坏了；且主图也不是产品

> 我推荐 **S1**：它是唯一能在本批**真正验证几何**（多比例）又不出现"重复图当错误"的方案。
> 若你更看重"少替换几个对象"，选 S2。**请指定其一，我按它出实施脚本。**

### 4.4 插入内容（占位符化，`__FORM__` 由脚本替换）

沿用块 3 的容器写法（`anchor` + `className` 换成新值），保持 8 页逐字同构：

```
<!-- B2D-S2: gallery -->
<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section id="gallery" class="wp-block-group sf-gallery has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:heading {"textAlign":"center"} -->
<h2 class="wp-block-heading has-text-align-center">__TITLE__</h2>
<!-- /wp:heading -->
<!-- wp:html -->
__GALLERY_MARKUP__
<!-- /wp:html -->
</section>
<!-- /wp:group -->
```

- 自闭合块一律 ` /-->`（紧贴斜杠，交付前 `grep -rn "/ -->"` 必须 0 命中）
- 注释只留短结构标注（`<!-- B2D-S2: gallery -->`）—— 同时给**限定证明**当 marker 用
- ⚠ `__GALLERY_MARKUP__` 若走 shortcode（`[sf_formula_gallery form="…"]`）则 8 页只有 `form` 不同，与 2D-S1 完全同构；
  若直接写死 HTML 则 8 页要各写一份（每页主图路径不同）。**建议走 shortcode**（与 `[sf_formula_actives]` 同源同法，
  直读 meta / 按 slug 解析图片，避免把 8 份路径硬编码进模板）。

---

## 5. 【点5】原生 JS 主图 + 缩略图切换方案（零依赖）

### 5.1 架构选择

**弃用 J1「4 个 figure 堆叠 + CSS 只显示 `.is-active`」**：无 JS 时会显示 4 张全叠或只剩 1 张不可切换，
且"哪张是主图"由 CSS 决定，键盘/无障碍语义含糊。

**采用 J2「stage + thumbs，单一数据源」**：

```
<section id="gallery" class="sf-gallery …">
  <h2>…</h2>
  <div class="sf-gal" data-sf-gal="soft-chews">          ← shortcode 产出，唯一根
    <div class="sf-gal__stage">                          ← 主图区
      <figure class="sf-gal__shot is-active">            ← 第 1 张默认激活
        <img src="…/soft-chews.webp" alt="…" width="720" height="720" loading="eager">
      </figure>
      <figure class="sf-gal__shot" hidden><img …></figure>   ← 其余 3 张服务端就渲染好
      …
    </div>
    <div class="sf-gal__thumbs" role="tablist" aria-label="…">
      <!-- JS 从这里按 stage 的 figure 生成 button；无 JS 时不显示 -->
    </div>
  </div>
</section>
```

**为什么缩略图由 JS 生成、而主图由服务端渲染**：
- **主图服务端渲染 ⇒ 首屏无 JS 也有图**（SEO / 降级 / 无 JS 访客都能看到产品），不会出现"图集空白"
- **缩略图条由 JS 从 `stage` 的 `figure` 派生 ⇒ 模板里图片数据只有一份**，未来实拍替换＝改 shortcode 里的一个数组，不需要在模板里同步两处
- 无 JS 时：`stage` 的 4 张 `figure` 通过 CSS 变成"两列小网格"（`[hidden]` 属性没有 JS 就没人设置，所以 4 张全显示）——**页面仍然是一组合法照片，不空白、不错位**

### 5.2 切换机制（不用任何库）

| 行为 | 实现 |
|---|---|
| 切到第 n 张 | `stage.children` 里给目标 `figure` 去 `hidden`、加 `is-active`；给旧图加 `hidden`、去 `is-active`（**只切属性与类，不移除、不重建 DOM**） |
| 对应缩略图高亮 | `thumbs` 里给目标 `button` 设 `aria-selected="true"`（其余 `false`），并加 `.is-current`（沿用 `.sf-fac` 既有命名） |
| 淡入淡出 | 仅 `@media (prefers-reduced-motion: no-preference)` 下给 `.sf-gal__shot` 一个 0.25s opacity 过渡；`reduce` 下直接切 |
| 键盘 | 缩略图是**真 `<button>`** ⇒ Enter/Space 天然可用；`←/→` 在 `thumbs` 上做**漫游焦点**（`role="tablist"` + `aria-selected`） |
| 焦点 | 切换**不移走焦点**（不 focus 主图），避免键盘用户被弹走 |
| 事件 | 全部用**事件委托绑在 `.sf-gal` 上**（一次 `addEventListener`），不逐张绑 —— 与主题既有写法一致，且未来增删槽位不用改 JS |
| 首屏 | `loading="eager"` 只给第 1 张，其余 `loading="lazy"` —— **避免 4 张一起抢带宽**（这是站内 `.sf-fac` 用 `loading="lazy"` 的同一考虑） |

**明确不做**（留给灯箱独立批次）：全屏查看、缩放、左右箭头浮层、计数、Esc、滚动锁、focus trap。

### 5.3 建议的 DOM/类名契约（避免撞名）

| 新名 | 用途 | 为什么不用既有名 |
|---|---|---|
| `.sf-gallery` | 新的顶层 section | 与 `.sf-fac`（about）/`.sf-eq`（quality）区分，将来三者可共享规则 |
| `.sf-gal` / `__stage` / `__shot` / `__thumbs` | 图集内部 | —— |
| `.is-current` | 当前缩略图 | **沿用** `.sf-fac > .wp-block-image.is-current` 的既有语义 |
| 版本 | 新增 `assets/js/gallery.js` (1.0.0)，**仅 8 剂型页入队**；`style.css` 2.10.45 → **2.10.46** | 主题惯例＝一功能一文件 + 页级入队 |

**必须避让的既有类名空间**（撞名会静默改样式）：`sf-fcard__*`、`sf-tile__*`、`sf-panel*`、`configurator__*`、`sf-actives__*`、`sf-spec-*`（**尤其 `sf-spec-term/value`＝K6 的喂数据口子，绝不能借用**）。

---

## 6. 【点6】移动端行为（滑动 or 点击）

**点击为主，滑动为辅，两者都不引库。**

| 视口 | 缩略图条 | 切图手势 |
|---|---|---|
| ≥ 1241px | 4 列网格，居中，`gap:10px`（照 `.sf-fac`） | 点击 |
| ≤ 1240px | 仍 4 列（`.sf-fac` 的先例：375px 也保持 3 列不拆） | 点击 |
| ≤ 768px | **横向单行滚动**：`overflow-x:auto; scroll-snap-type:x mandatory; -webkit-overflow-scrolling:touch`，每个缩略图 `scroll-snap-align:start`，宽 `calc((100% - 2*gap)/3)` ⇒ 露出一张半，暗示可滑 | 点击 **＋** stage 上左右滑 |

**滑动手势用 Pointer Events 实现（约 20 行，不用库）**：

- `pointerdown` 记 `x0/y0`；`pointermove` 累计 `dx/dy`
- **意图锁定**：只有当 `|dx| > 40px` **且** `|dx| > |dy| * 1.5` 时才认作"切图"，
  否则**完全放手**给页面纵向滚动（这是横向手势最常见的翻车点：劫持了纵向滚）
- 命中后 `dx < 0` → 下一张，`dx > 0` → 上一张；`pointerup` 复位
- **不做循环**（首尾到头就停），避免用户分不清"滑不动"和"坏了"

**其它移动端要点**：
- 本批新增 CSS **不使用任何 `:has()`** ⇒ 站内 `:has()` 计数（172 处）**保持不变**，不新增老 Android/WebView 风险
- 触屏无 hover ⇒ `.sf-fac` 的 `(hover:none) :active` 反馈写法应沿用（段内已有该先例）
- 375px 三个必查项：① stage 不产生横向溢出 ② 缩略图条可滑且滚不到非预期位置 ③ 主图切换后**页面纵向位置不跳**（`scroll` 锚定：切换只改 `hidden`，不改高度 ⇒ 天然不跳）

---

## 7. 【点7】与既有 K1 / K2 / 配置器 / JSON-LD / 回归门的交互影响

### 7.1 逐项实测结论

| 对象 | 实测 | 本批影响 |
|---|---|---|
| **K1** `.sf-formula__cta[data-formula]` + `formulas.js` | `grep -nE "querySelector(All)?\([^)]*(img\|figure\|picture)"` 在 `formulas.js` **0 命中** | **零交互**。图集不碰 `.sf-formula__cta`，CTA 的滚动与 `data-formula` 不变 |
| **K2** `.sf-formulas-data` JSON | 仅由 `[sf_formula_grid]` 产出 | **零交互**。图集不产出 K2、不消费 K2（避免把渲染推给客户端） |
| **配置器** `configurator.js` + `sessionStorage['sinofresh_config_<slug>']` | 无任何 `img`/`figure` 选择器 | **零交互**。唯一风险＝**类名撞车**（见 §5.3 避让清单） |
| **Product JSON-LD（K6）** | `image` 来自 `sinofresh_formula_card_image()`（按 slug glob）；`additionalProperty` 读**模板文件**里的 `<span class="sf-spec-term">` | **零交互**。⚠ 前提：新 CSS/HTML **不得**出现 `sf-spec-term` / `sf-spec-value`，否则会**意外喂到 K6**（2D-S1 已让 `sf-spec-term` 在页面上有了新出处，别再叠加） |
| **卡片图重复** | 本页剂型图已经在公式卡里出现 2–4 次 | 图集再用同一张 ⇒ **同页同图第二次出现**（不同尺寸/裁切）。这是既成事实（2D-S1 已接受），但要在报告里点名 |
| **`basket.js` / 其它** | 全量 grep：只有 `about.js`、`quality.js` 碰 `img`/`figure` | **零交互** |

### 7.2 入队与版本（会影响回归结论，需专门处理）

- `style.css` **2.10.45 → 2.10.46**（两处同步：`functions.php:26` + `style.css:5`）
- **新增 `assets/js/gallery.js` 1.0.0**，入队条件沿用剂型页白名单（`is_page($dosage_pages) || is_page_template(...)`）
- ⚠ **新增入队会让 8 个剂型页（+ zh 版）的"资源集合"发生变化** ⇒
  - **掩码回归会把它们判成 DIFF** —— 这是**预期**的，不是回归
  - 必须同时跑**资源清单报告**（`tools/b2c_s2_ver_inventory.py`）证明"只多了 gallery.js 一个、ver 只变了 style.css 一个"
  - **只掩码不报告 = 允许"顺手改错别的资源版本"溜过去**（第 1 批已验证过这条门规）

### 7.3 多语言（TranslatePress）

新图集的 `alt` / 标题 / `aria-label` 都是**新串**，TP **未收录** ⇒ `/zh/` 版本会显示英文原文。
2D-S1 的先例是"本批不补 TP 串，记为遗留"。**建议同办**：本批记为遗留，与实拍替换一起在 TP 重收录批次里处理。

### 7.4 点轨 TOC（唯一有真实副作用的项）

- `toc-nav.js` 只收 `h2`（`toc-nav.js:84`）；剂型页当前渲染 **7 个 H2** ⇒ 点轨 7 颗点
- 图集区若用 **`<h2>`** ⇒ 变 8 颗点，且其后所有 `id="sf-sec-N"` **序号整体 +1**
  - 这些 id 是**运行时注入、不落库、无外部深链**；显式 anchor（`#formulas`/`#configurator`/`#actives`/`#inquiry-form`）**不受影响**
  - 第 1 批已有先例（2D-S1 用 H2，点轨 6→7，浏览器核验通过）
- 若想**完全不加点**（点轨保持 7）：用 `<h3>` 或纯 `aria-label` + 视觉隐藏标题
  - ⚠ 但项目既有规则是"**新增区块标题一律 h3**"（K3 的推论），而 2D-S1 又用了 h2 —— **两种先例都在，需要你选**

**两个选项**：① 用 `<h2>`（与 2D-S1 一致，点轨 7→8，浏览器复核）② 用 `<h3>` 或 `aria-label`（点轨不动）。
我倾向 ①：图集是页面上半部的主要区块，进点轨对访客有价值，且已有先例与复核流程。

### 7.5 回归门（沿用第 1 批已固化的两把锁）

1. **限定证明（marker-driven）**：以 `<!-- B2D-S2: gallery -->` 为 marker，候选页删掉图集段后与基线**逐字节**比 → 期望 **47/47**
2. **掩码回归**：`tools/sf_masked_cmp.py <new> <live> --user`，**先跑 `--aa` 自检**（挑每个模板家族各一页）
3. **资源清单**：`tools/b2c_s2_ver_inventory.py` → 期望"仅 style.css ver 变化 + 新增 gallery.js"
4. JSON-LD 47 页 deep-equal（尤其 8 页 Product 的 `additionalProperty` 仍为空、`image` 未变）
5. K2 全等；K1 CTA 浏览器点击；配置器回填
6. 浏览器 30/30 ＋ 新增图集用例（4 页 × 切换/键盘/375px/zh）
7. 工作区↔云端 md5 全等

---

## 8. 实施计划（待确认后执行）

| 步 | 动作 | 产物 |
|---|---|---|
| 0 | 备份 10 个待改文件 → `_backup/b2d-step2-<ts>/` + MANIFEST | 回滚点 |
| 1 | `functions.php` 新增 `[sf_formula_gallery]`（直读 meta/按 slug 解析图，空则不输出） | 纯函数 + 短代码 |
| 2 | 8 模板插入图集块（锚点＝`Block 9: How We Work` 前的固定串，5 行） | 8 页同构 |
| 3 | `style.css` 追加图集段（照 `.sf-fac` 语言，零 `:has()`）；版本 → 2.10.46 | CSS |
| 4 | 新增 `assets/js/gallery.js` + `functions.php` 页级入队 | JS |
| 5 | `php -l` / 块配平 / `"/ -->"` 零残留 / 8 页签名一致 | 本地静态回归 |
| 6 | 预检装置（头门 + 独立主题目录 + `-u`）跑 A/B 两趟 | 预检证据 |
| 7 | 云端 12 项回归（§7.5） | 回归结论 |
| 8 | 删预检残留 + 复验基线 + 落档 + 汇报 | 收尾 |
| 9 | 独立 commit：实现 / 工具 / 文档 三条 | 可单独 revert |

**回滚顺序**（沿用铁律 7：中间态必须能停留）：
先 `git revert` 模板 commit（回落旧模板，页面仍可渲染）→ 再 revert `functions.php`（短代码多余但不被调用）→ 最后 CSS/JS。
**文件级兜底**：步 0 的 `_backup/b2d-step2-<ts>/`。

---

## 9. 【阻塞项4】「上线前必做」清单 —— 实拍图替换（**34 张，不是 18 张**）

见 §2.4 的更正。清单按"上线访客能看到"分层，**逐张替换后必须复核水印零残留**（`grep` 无 `AI生成` 无从验，需**目视**——水印是像素内容）。

### T1 必须换（产品页的核心素材，8 张）
| # | 文件 | 要求 |
|---|---|---|
| 1–8 | `<slug>.webp` ×8 | 720×720 或更大、1:1、**无任何叠加文字**；成品实拍或合规渲染；浅底、45°微距、与现有构图一致 |

### T2 图集新增位（按 §4.3 所选方案决定张数）
| # | 文件 | 要求 |
|---|---|---|
| 9 | `fac-placeholder.webp`（或实拍的 GMP 车间宽幅） | ≥1600×1067（3:2），无叠加文字 |
| 10–11 | 若选 S1：`fac-packaging` / 一张常压细节图 | 4:3，≥1600×1200，无叠加文字 |

### T3 站内其它页可见（26 张，可分批）
| 组 | 张数 | 文件 |
|---|---|---|
| 厂区 | 6 | fac-cleanroom / fac-lab / fac-line / fac-packaging / fac-retention / fac-warehouse |
| QC | 6 | qc-batching / qc-coa / qc-finished / qc-inprocess / qc-raw-material / qc-retention |
| 设备 | 3 | equip-aas / equip-gc / equip-hplc |
| 首页 hero | 4 | hero1-exterior / hero2-lab / hero3-line / hero4-warehouse |
| 其它 | 5 | blog-choose / blog-compliance / blog-softchews / coa-sample / video-cover |
| 备用 | 2 | equip-placeholder / （第二张 placeholder） |

**替换执行方式**（写好备查）：
- **同文件名覆盖上传** ⇒ 零模板改动、零版本号改动；
- 若新图尺寸/比例不同 ⇒ 必须同步改模板里的 `width/height` 与 `alt`（模板里现在写的是陈旧的 `width="800" height="600"`，而实际是 720×720 —— **不要拿它当尺寸真值**）；
- 替换后跑：限定证明（图集段字节会变，先删段比）＋掩码回归 ＋ 资源清单 ＋ 目视 8 页。

---

## 10. 待你确认（3 项）

| # | 问题 | 我的推荐 |
|---|---|---|
| **A** | §4.3 的槽位方案：**S1（1 主 + 3 缩略，4 张互不相同）** / S2（1 主 + 1 缩略，只 2 张） / S3（4 张全用同一占位） | **S1**（唯一能真验几何且不像坏图） |
| **B** | 图集标题：用 **`<h2>`（点轨 7→8）** 还是 `<h3>`/`aria-label`（点轨不动） | **`<h2>`**（与 2D-S1 一致，已有先例与复核流程） |
| **C** | 图集内容走 **shortcode**（`[sf_formula_gallery form="…"]`，8 页同构）还是模板里写死 HTML（8 份路径） | **shortcode**（与 `[sf_formula_actives]` 同源同法，替换实拍时只改一处） |

**你回 A/B/C 后我即开工**，按 §8 执行、按 §7.5 过回归、按 §8 留回滚点，完成后停下汇报。

---

## 附：复现命令

```bash
# 8 页图片/DOM 真值（带凭据，勿漏 -u）
python3 - <<'PY'
import re,base64,urllib.request
A=base64.b64encode(b'sfdev:VkEws18Kl5V1qp3TpZ6s').decode()
for s in ['soft-chews','tablets','powders','pastes','drops','liquids','fish-oil','dental-chews']:
    r=urllib.request.Request('https://dev.zxpet.com/products/%s/'%s,headers={'Authorization':'Basic '+A})
    h=urllib.request.urlopen(r,timeout=60).read().decode()
    print(s,len(h),len(re.findall(r'<img\b',h)),len(re.findall(r'sf-fcard__media',h)),len(re.findall(r'<h2\b',h)))
PY

# 图片全量尺寸（服务端，免下载）
ssh root@65.49.215.152 'php -r "\$d=\"/var/www/dev.zxpet.com/public/wp-content/uploads/2026/09/\";
foreach(glob(\$d.\"*.webp\") as \$f){\$b=basename(\$f);if(str_starts_with(\$b,\"._\"))continue;\$i=@getimagesize(\$f);
printf(\"%-34s %-11s %8d\n\",\$b,\$i?\$i[0].\"x\".\$i[1]:\"?\",filesize(\$f));}"'

# 水印取证图（第 0 批产出）
open docs/b2d-step0-shots/watermark-montage-18img.png
open docs/b2d-step0-shots/fac-placeholder-corner-zoom.png
open docs/b2d-step0-shots/equip-placeholder-corner-zoom.png
```
