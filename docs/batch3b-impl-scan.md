# 批 3b 补做 — 实施前扫描（只读）

> 扫描日期：2026-09-24　｜　范围：**只读**（读模板 / style.css / tools，curl 只 GET dev），**未改一行代码、未写一个字节、未碰 DB 与生产站**
> 触发：用户在「批 3b 补做 —— 5 项」中要求 **先扫描 → 报告 → 停下 → 等确认再实施**
> 结论一句话：**5 项的落点全部定位完毕，机制均有既有先例、无需新增 CSS/JS 库**；但有 **3 处与你给的指令不一致**（页脚会变 5 栏、区块级按钮的类与首页自身约定冲突、两带的底色交替需要动 1 个既有带）+ **7 条需你点头的细节**，见 §三 / §四。

---

## 〇 五项落点一览

| 项 | 文件 | 精确锚点 | 机制是否现成 |
|---|---|---|---|
| ② 页脚 Services 栏 | `parts/footer.html` | 在 **L29**（Products 栏 `<!-- /wp:column -->`）后插入 1 个新 `wp:column` | ✅ 复制现有栏结构，零 CSS |
| ③ 首页 4 框加链接 | `templates/front-page.html` | **L561 / L589 / L617 / L645** 四个 `h3` | ✅ `.sf-card__title-link::after{inset:0}` 已存在（style.css L365–370），零 CSS 零 JS |
| ③ 区块级按钮 | `templates/front-page.html` | **L670**（`<!-- /wp:columns -->`）之后、**L671**（`</section>`）之前 | ✅ 类已存在；⚠️ 类名与首页约定冲突（见 §三 D2） |
| ④ C1 定制能力 | `templates/page-services.html` | **L196**（What We Handle 的 `<!-- /wp:group -->`）之后 | ⚠️ 需定底色（见 §三 D3） |
| ④ C2 工厂能力 | `templates/page-services.html` | **L296**（How We Work 的 `<!-- /wp:group -->`）之后 | ⚠️ 同上 |
| ⑤ Cooperation Models | `parts/footer.html` | 同 ② 的新栏内 | ⚠️ 位置二义（见 §三 D6） |
| ⑥ 版本两处 | `style.css` L5 · `functions.php` L31 | 2.10.76 → **2.10.77** | ✅ 已确认只有这两处 |
| ⑥ 门断言 | `tools/b2d_h8c_live_check.py` L76 | `OVERVIEW_H2` 6 → 8 条 | ⚠️ 同 check 的**标签**也要改（见 §三 D9） |
| ⑥ E2E 版本 | `tools/b2d_h8c_live_accept.py` **L46** | `EXPECT_VER = "2.10.76"` → 2.10.77 | ❌ **你未列出，但必须改**（见 §三 D8） |

---

## 一 ② 页脚加 Services 栏

### 1.1 现有结构（`parts/footer.html`，共 94 行）

```
L1-2   <footer class="... sf-footer has-primary-background-color ...">      ← 深绿底
L3-4   <!-- wp:columns {"className":"sf-footer-grid"} -->
L5-15    column 1  Brand       {"width":"30%"}   logo + 简介 + 社媒
L16-29   column 2  Products    details.sf-footcol + summary + p.sf-footlinks（8 条）
L30-43   column 3  Company     （6 条）
L44-64   column 4  Contact Us  （邮箱 / WhatsApp / 地址 + Get a Quote 按钮）
L65-66 </div><!-- /wp:columns -->
L68-    sf-footer-legal（版权 + 法律链接）
```

每个导航栏的写法（以 Products 为准，可原样复制改文案与链接）：

```html
<!-- wp:column -->
<div class="wp-block-column">
	<!-- wp:details {"className":"sf-footcol","showContent":true} -->
	<details class="wp-block-details sf-footcol" open>
	<!-- wp:summary -->
	<summary>Products</summary>
	<!-- /wp:summary -->
	<!-- wp:paragraph {"className":"sf-footlinks","style":{"typography":{"fontSize":"14px"}}} -->
	<p class="sf-footlinks" style="font-size:14px"><a href="/soft-chews/">Soft Chews</a>…</p>
	<!-- /wp:paragraph -->
	</details>
	<!-- /wp:details -->
</div>
<!-- /wp:column -->
```

要点：`sf-footlinks` 是 **`flex-direction:column; gap:7px`**（style.css L947–951），所以**链接之间不加分隔符**，纯并列 `<a>`；`sf-footcol` 在桌面是常开标题、≤781 变可点折叠（`+` / `−`）。

### 1.2 ⚠️ 页脚会从 4 栏变 5 栏 —— 桌面列宽被压缩

- `.sf-footer-grid` **只有 `align-items: stretch`**（style.css L880–882），**没有固定列数**；列数由 WP 核心 flex 决定。
- WP 核心 `.wp-block-columns` 在 **≥782px 是 `flex-wrap: nowrap`** ⇒ 第 5 栏 **不会换行，只会被挤窄**。
- contentSize = **1200px**（theme.json L7），列间 gap = 2em(32px)，brand 栏 `flex-basis:30%`：

| 情形 | 导航列宽度（1440 视口，footer 占满 1200） |
|---|---|
| 现在 3 个导航列 | ≈ **248px** |
| 加栏后 4 个导航列 | ≈ **178px** |
| 1024 视口（内容区变窄） | ≈ **136px** |

- 最长新标签 `Contract Manufacturing`（22 字符 × ≈7px ≈ 154px）在 1440 装得下，**在 1024 会折成两行**。footer 链接折行不是故障，但会改变页脚高度节奏。
- ≤781px：栏堆叠成 5 个折叠项，`.sf-footer-grid{gap:0}`（style.css L2970，位于 `@media (max-width:768px)`）⇒ **手机无影响**。

**选项**：① 接受挤压，实施后按 1024 / 1280 / 1440 三档截图核验（**建议**）；② 把 brand 栏 `30%` 降到 ~24% 给导航列让位；③ 加一条 `.sf-footer-grid` 的 5 列显式规则（= 新增 CSS，与你「不加 CSS」的取向相悖，不推荐）。

### 1.3 目标路由实测

`/services/oem/` · `/services/odm/` · `/services/contract-manufacturing/` · `/services/private-label/` · `/cooperation/` —— **全 200** ✅

---

## 二 ③ 首页 4 框加链接 + 区块级按钮

### 2.1 4 张卡的精确位置与现状

`templates/front-page.html` **L544–672**，`<section class="wp-block-group sf-section sf-section--large sf-oem has-card-white-background-color has-background">`（**浅底** ✅）：

| 行 | 现状 h3 | 目标 href |
|---|---|---|
| L561 | `<h3 class="wp-block-heading">OEM &#8212; You Bring the Formula</h3>` | `/services/oem/` |
| L589 | `<h3 class="wp-block-heading">ODM &#8212; We Develop From Your Idea</h3>` | `/services/odm/` |
| L617 | `<h3 class="wp-block-heading">Contract Manufacturing</h3>` | `/services/contract-manufacturing/` |
| L645 | `<h3 class="wp-block-heading">Private Label</h3>` | `/services/private-label/` |

四张卡的容器是 `<div class="wp-block-group sf-card sf-card--roomy">`（L559 / L587 / L615 / L643）。

### 2.2 机制核验（确认「零 CSS、零 JS、视觉零变化」成立）

| 判据 | 实测 |
|---|---|
| `.sf-card { position: relative }` | ✅ style.css **L324–327**（`.sf-card, .sf-tile { position: relative }`） |
| `.sf-card__title-link::after { content:''; position:absolute; inset:0; z-index:1 }` | ✅ style.css **L365–370** |
| `:focus-visible` 描边（品牌绿） | ✅ style.css **L378–381** |
| hover 抬升是否会被新增链接「激活」 | ❌ 不会 —— `.sf-card:hover{transform:translateY(-2px)}`（L337–341）**与是否含链接无关**，今天已经生效 ⇒ 确实零变化 |
| 卡内 ✓ 要点会不会被覆盖层挡住 | 不会 —— 覆盖层 `z-index:1` 且要点本身不定位 ⇒ 行为与 `/services/` 4 卡完全一致（那 4 张已实测「整卡可点 + 单 tab 停点」） |

> ⚠️ 唯一需要**实施后实测**的点：`/services/` 的卡是 `backgroundColor:card-white` 的 group，而首页的卡是**同一元素既是 `.sf-card` 又是 `layout:constrained` group**（WP 核心会给它 `position:relative`）。两者最终都是「`::after` 落在 `.sf-card` 上」，预期一致，但我会在候选层用命中测试复核 4 卡正中心与四角。

### 2.3 区块级按钮 —— ⚠️ 你给的类与首页自身约定冲突

你给的写法：`<a href="/services/" class="sf-explore__btn">See all services →</a>`

实测：

| 事实 | 证据 |
|---|---|
| `sf-explore__btn` **已存在**，但只在**剂型页**用 | style.css **L8931**；`page-fish-oil.html` L50/L62、`page-drops/dental-chews/powders/pastes` 同 |
| `sf-explore__btn` 在 `front-page.html` 出现 **0 次** | 全文件 grep `sf-explore` = 0 |
| 首页**自己**的「See all X →」约定是 `sf-btn-outline` | `front-page.html` **L1318–1324**「View All Articles」、**L1373–1379**「View All FAQs →」 |
| 两者**视觉等同** | `.wp-block-button .sf-btn-outline`（L1365–1371）= 2px `primary`(#1B4D3E) 描边 / 圆角 6 / 透明底 / 600；`.sf-explore__btn`（L8931）= 2px `#1B4D3E` / 圆角 6 / 透明底 / 600 / 15px |
| 裸 `<a>` 不能直接躺在块模板里 | 需要 `wp:buttons`（flex，可给 gap 与居中）或 `wp:paragraph` 包一层 |
| 首页现有两个「See all」按钮都是**居中** | `"layout":{"type":"flex","justifyContent":"center"}` |
| 但 `sf-oem` 区块的 eyebrow/h2 是**左对齐** | L546–554 无 `textAlign` |

**选项**：(a) 按首页自身约定 → `wp:buttons`(center) + `sf-btn-outline`（**建议**，与同页两个「See all」完全同款）；(b) 按你的写法 → `sf-explore__btn`（视觉相同，但引入本页从未出现的类；且 ≤768 会变 `display:block;width:100%` 通栏）；(c) 不居中、左对齐贴齐 h2。
另外：箭头字符现有两处写法并存（`→` 字面量 与 `&rarr;`），需统一口径。

---

## 三 ④ `/services/` 补两带

### 3.1 现状与插入点

`templates/page-services.html` 368 行，渲染后 **7 个 section**，底色交替实测：

| # | 带 | 行 | 底色 |
|---|---|---|---|
| 1 | Hero | L3–15 | `sf-hero-inner`（深色首屏） |
| 2 | 模式对比（4 卡） | L17–110 | `bg-light` |
| 3 | Key Facts | L112–133 | `card-white` |
| 4 | What We Handle | L135–196 | `bg-light` ← **C1 插这之后** |
| 5 | How We Work | L198–296 | `card-white` ← **C2 插这之后** |
| 6 | FAQ | L298–329 | `bg-light` |
| 7 | Request a Sample | L331–366 | `primary`（深绿） |

### 3.2 ⚠️ 底色交替需要动 1 个既有带（两选一）

插入后的序列是：… `bg-light`(4) → **C1** → `card-white`(How We Work) → **C2** → `bg-light`(FAQ) → `primary`(7)

| | 方案 a（**建议**） | 方案 b |
|---|---|---|
| C1 | `card-white` | `card-white` |
| How We Work | **`card-white` → `bg-light`**（翻 1 处） | 保持 `card-white` |
| C2 | `card-white` | `bg-light` |
| FAQ | `bg-light`（不变） | 保持 `bg-light` |
| 结果 | **严格白/浅交替**，条纹节奏不断 | **2 处接缝**（连白 + 连浅） |
| 代价 | 改了 1 个既有带的底色（视觉与字节都变） | 既有 7 个带**零改动** |

### 3.3 要复制的既有写法（逐字对齐，别自创）

区块外壳（本页 7 处统一的写法；注意文件里 block 属性写 40px、inline style 写 32px，**是既有不一致**，新带建议照抄以保持一致外观）：

```html
<!-- wp:group {"tagName":"section","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}}}} -->
<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:32px;padding-bottom:32px">
```

标题 + 引导句：

```html
<!-- wp:heading {"textAlign":"center"} -->
<h2 class="has-text-align-center wp-block-heading">Custom Formulation Capability</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","textColor":"text-secondary"} -->
<p class="has-text-align-center has-text-secondary-color has-text-color">…摘要一句…</p>
<!-- /wp:paragraph -->
```

### 3.4 ⚠️ 列表类：`sf-checklist` 基础类**没有 CSS**

| 类 | 实测 |
|---|---|
| `.sf-checklist--panel` | ✅ style.css **L6290 / L6296 / L6301 / L6309** |
| `.sf-checklist`（基础） | ❌ **无任何独立规则**（L6283 的注释说明 2 列变体已随宽幅带删除） |

⇒ 本页现用法一律是 `class="sf-checklist sf-checklist--panel"`（L151 / L167 / L183）。C1/C2 的条目若想沿用这套勾号列表，**必须带 `--panel`**；否则用 `wp:list`（会带默认圆点，视觉与全站其它列表不同）。

### 3.5 ⚠️ 两带各两个"链接"怎么呈现

你写的是「内容：摘要 3-4 条」+ 另列「链接：A → /x/、B → /y/」。两种读法：
(a) 摘要列表 + **下方两个按钮**（建议，与 ③ 同一套按钮）；
(b) 把列表项本身做成链接。
选 (a) 的话，`/services/` 目前**没有「一个带里放两个 outline 按钮」的先例**；最近的先例是 `page-fish-oil.html` L50（单按钮，包 `wp:paragraph` 居中）与 L62（在 `.sf-explore` flex 容器内）。⇒ 建议 `wp:buttons`(flex, center) 放两个 `sf-btn-outline`，天然带 gap 与居中。

### 3.6 内容重叠提醒（你已指示只做摘要，这里把重叠点点名）

C2 的四条（GMP-certified facility / 8 dosage form production lines / In-house QC laboratory / Full traceability）与 **`/quality/` 已有 h2**（`In-House QC Laboratory`、`Full Traceability from Raw Material to Finished Product`）和 **`/factory-tour/` 的 `Built to Pharmaceutical Standards`** 语义重叠 ⇒ 摘要措辞要与那两页**不同字**，否则等于把两页的标题抄进来。我会按「能力主张（一句）+ 去处」写，不复制那两页的标题文本。

---

## 四 ⑥ 连带处理 — 你列的两条 + 我扫出的三条补充

| # | 项 | 实测 | 你要的动作 |
|---|---|---|---|
| 1 | toc-nav 圆点轨 | `toc-nav.js` L180–183：取 `main` 下**可见 h2**、**≥3 才出**；`SKIP` 只匹配首页文案 ⇒ `/services/` 现 **6 点**，加 2 带 → **8 点**。**无需改代码** ✅ | 你已确认，无需动作 |
| 2 | `OVERVIEW_H2` | `tools/b2d_h8c_live_check.py` **L76** 定义、**L347** 断言 `texts_of(svc,'h2') == OVERVIEW_H2` | 加 2 条 → 8 条（**顺序敏感**） |
| 3 | ⚠️ **同一 check 的标签** | L346 的标签是 `'...and the overview itself is otherwise untouched by the batch'` —— 加了带之后这句**变成假话** | **必须改写标签**，不能只加两条（判据标签也要诚实） |
| 4 | ⚠️ **你未列：E2E 硬编码版本** | `tools/b2d_h8c_live_accept.py` **L46** `EXPECT_VER = "2.10.76"`，L375–377 断言「首页服务的主题版本 == EXPECT_VER」 | **改为 2.10.77**，否则 E2E 第一条就红 |
| 5 | 版本两处 | `style.css` **L5** `Version: 2.10.76`；`functions.php` **L31** `wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.76')` ⇒ 全仓只有这两处 ✅ | 2.10.77（两处同步） |
| 6 | 抓页清单 | `tools/b2d_s3_paths.txt` **75 行**（`/` 在第 1 行、`/services/` 在第 8 行）；本批**不新增路由** ⇒ **清单不动** ✅ | 无需动作 |
| 7 | ⚠️ **DIFF 范围比你写的大** | 你写「首页 + /services/ + 页脚（全站）」。实际：`parts/footer.html` 是**全站 template part**，且 `style.css?ver=` 出现在**每一页** ⇒ **全站 79 页字节都会变**（76 页＋4 新路由）。§一 的 5 栏挤压因此要在**每页**页脚复核 | 知悉；比对时按全站 |
| 8 | E2E 卡片断言是否受影响 | `CARDS_JS`（accept L209）按 `.sf-card--roomy` 取 /services/ 的卡、要求 **每卡 1 个锚**；③ 的按钮在**卡外**、④ 若用 `wp:buttons` 也是独立元素 ⇒ **不受影响** ✅ | 无需动作 |

---

## 五 需你点头的 8 条（全部影响实现形态）

| # | 问题 | 我的建议 |
|---|---|---|
| D1 | 页脚 5 栏会挤压桌面列宽（1440 ≈178px / 1024 ≈136px，长标签会折行） | 先接受挤压，实施后按 1024/1280/1440 三档截图核验 |
| D2 | 区块级按钮用 `sf-explore__btn`（你给的）还是 `sf-btn-outline`（首页自身约定，视觉等同） | 用首页约定 `wp:buttons`(center) + `sf-btn-outline`；或按你的写法但知悉 ≤768 会通栏 |
| D3 | 两带底色：方案 a（严格交替，翻 1 个既有带）还是方案 b（零动既有带，2 处接缝） | 方案 a |
| D4 | 两带的"链接"：做成两个按钮，还是把列表项本身变链接 | 两个按钮（`wp:buttons` + `sf-btn-outline`） |
| D5 | C1/C2 的条目列表用 `sf-checklist sf-checklist--panel`（须带 `--panel` 才有样式）还是 `wp:list` | `sf-checklist sf-checklist--panel`（与本页现有 3 处一致） |
| D6 | ⑤ `Cooperation Models` 是**追加在新 Services 栏内**（该栏 5 条）还是**新增第 6 栏** | 追加在栏内 |
| D7 | 页脚 Services 栏内 4 条的排序：按你给的（… Private Label → Contract Manufacturing）还是跟 `/services/` 卡序（Contract → Private Label） | 按你给的 |
| D8 | 区块级按钮的居中 vs 左对齐（`sf-oem` 的 h2 是左对齐，首页其它「See all」都居中） | 居中（与同页两个「See all」一致） |

---

## 六 本报告明确**没有**做的事

- 未改任何模板 / `functions.php` / `style.css` / JS / tools
- 未写任何 DB 行、post meta、option；未碰 `wp_navigation`（导航由你自己改）
- 未 pull、未部署、未碰生产站（全程只对 dev 做带凭据的 GET）
- 未创建候选层、未跑门、未新增抓页清单条目
