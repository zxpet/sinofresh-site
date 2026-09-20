# 全站代码冗余审计报告

**审计日期**：2026-09-20
**审计范围**：`sinofresh-theme`（块主题）+ `sinofresh.local` 站点数据库与媒体库
**审计性质**：**只读扫描**。未删除任何代码、未修改任何文件、未对数据库执行任何写操作（全部为 `SELECT`）。
**清洁室状态**：站点当前运行正常（审计期间 24 个 URL 全部 200、无 PHP 报错）。

---

## 0. 审计方法与取证口径（为什么这份清单可信）

每一条「冗余」判定都基于**三方交叉验证**，而不是单一来源的猜测：

| 证据源 | 具体做法 | 覆盖量 |
|---|---|---|
| **A. 运行时真实 DOM** | Playwright 加载 24 个 URL × 2 个视口（1440 / 375），抓取 `document.querySelectorAll('*')` 的全部 class；并额外做一轮交互（打开移动导航 / 询盘抽屉 / 折叠面板）捕获状态类 | 48 次页面加载 → **996 个运行时 class** |
| **B. 全量源码字面量** | 扫描 `templates/`、`parts/`、`inc/`、`functions.php`、`theme.json`、`assets/js/`、`assets/css/`、`style.css` 中的 `class="…"`、`className":"…"`、`classList.*(...)`、`querySelector('.x')` | 87 个业务文件 |
| **C. 数据库内容** | 只读 `SELECT`：`wp_posts.post_content`（全部状态）、`wp_options.option_value`、`wp_postmeta.meta_value`、`wp_media` 附件表 | 72 条内容 + 329 条 option + 124 条 meta |

**关键设计**：页面内容可能存放在数据库 `post_content`（而非模板文件）里，因此 C 源不可省略——本次正是靠 C 源发现了 `.sf-slot--photo` 存在于数据库模板记录中（详见 §6.1）。

覆盖的 24 个 URL：首页、19 个业务页（about / factory-tour / services / quality / contact / blog / products / faq / cooperation / feedback / 8 个剂型页）、单篇文章、单篇案例、分类归档、搜索结果页、404 页。

### 0.1 已排除的假阳性（重要：这些**不是**冗余，请勿删）

首轮自动扫描给出的原始数字比最终结论**大得多**。逐条人工复核后，以下都是误报，已从清单中剔除：

| 原始误报 | 数量 | 剔除依据 |
|---|---|---|
| `.no-has` | 1 类 / 8 条规则 | `functions.php:56` 的 `:has()` 能力探针会执行 `document.documentElement.className += " no-has"`，是**有意设计的旧浏览器降级** |
| `.admin-bar` | 2 条规则 | WordPress 对已登录用户自动加在 `<body>` 上，属核心类 |
| `.is-not-stacked-on-mobile` / `.always-shown` | 各 1 条 | WordPress 核心区块类（列布局 / 导航响应式容器），由编辑器输出 |
| `.sf-certmodal-lock` | 1 条 | `assets/js/cert-modal.js:39` 以 `const lockClass` 变量方式赋值后 `classList.add`，字面量扫描的盲区 |
| `.sf-spec-list` | 2 条规则 | `functions.php:1875/1912` 注释中明确点名该结构（虽在渲染输出中已无对应 markup，见 §3.4） |
| `IntersectionObserver` 出现在 `toc-nav.js` | 1 处 | 只出现在**注释**里，且注释内容是解释「为什么故意不用它」 |
| `interactions.js` 的 `frame()` 被判为死函数 | 1 个 | 它是 `requestAnimationFrame(function frame(now){…requestAnimationFrame(frame)})` 的**命名递归回调**，自动检测的误报 |
| 「同一选择器定义 176 次」 | 176 → **20** | 花括号深度计数后：156 次是媒体查询内的响应式重申（正常写法），另 2 组是 `@keyframes` 的 `from`/`to` 帧标记（解析噪声） |
| `-webkit-` 前缀 25 处「可清」 | 25 → **14** | 逐个核对现行浏览器支持：11 处仍必须保留 |
| 图片 `sino-fresh-logo-1.png` | 1 个 | 实际以 `-scaled.png` + srcset 形式在用，按「文件家族」判定后归于在用 |

> 审计纪律：**报「可删」之前先证伪自己**。上面每一项都经历了「为什么它看起来没用 → 去找它到底有没有被用 → 找到或找不到的证据」。

---

## 1. CSS 冗余（`style.css` 7,664 行 / 237 KB；`assets/css/configurator.css` 915 行）

解析出 **1,122 条规则**，选择器中出现的 class 共 **430 个**。

### 🔴 确定可删：孤儿 class 的样式（零引用，有明确依据）

**总量：9 个 class / 30 条规则 / 112 行 / 3.0 KB**（占 style.css 行数的 1.46%）

判定依据：这些 class 在证据源 A + B + C 中**全部零命中**（运行时 DOM 无、源码无、数据库内容无）。

| # | class | 位置（style.css 行） | 内容摘要 | 依据 | 体积 |
|---|---|---|---|---|---|
| 1 | `.wp-block-columns.sf-triple` | 1622, 1664, 1672 | `.wp-block-columns.sf-triple{display:grid !important;grid-…` | 全站零引用；旧版「三栏特性列表」组件已被卡片网格替代 | 约 60 行 |
| 2 | `.sf-triple > .wp-block-column` | 1628, 1633, 1667, 1675 | `…{margin:0;position:relative;min-width:0}` | 同上（含 3 处媒体查询内的重申） | 计入上项 |
| 3 | `.sf-triple__list` + `li` / `li + li` / `li::marker` | 1637, 1641, 1645, 1648 | `.sf-triple__list{padding-left:18px}…` | 同上 | 计入上项 |
| 4 | `.sf-spec-list` | 1681 | `.sf-spec-list{margin-top:14px;border-top…` | 零引用；且 `sf-spec-term` 解析分支已无输入（见 §3.4） | 1 条 |
| 5 | `.sf-spec-row` | 1685 | `.sf-spec-row{display:grid;grid-template-…` | 同上 | 1 条 |
| 6 | `.sf-params` | 534, 2820(媒体查询) | `.sf-params{margin-top:24px !important;…` | 零引用；旧版「统计面板下的商务条款行」 | 2 条 |
| 7 | `.sf-avatar` + `.sf-avatar p` | 507, 513 | `.sf-avatar{display:grid !important;…` | 零引用；人物头像占位组件未使用 | 2 条 |
| 8 | `.sf-footer-brand` | 713 | `.sf-footer-brand{letter-spacing:0.06em}` | 零引用 | 1 条 |
| 9 | `.sf-slot--photo` + `.sf-slot--document` | 491–504, 2374, 2599, 2618, 2621, 2629 | `.sf-slot--photo{background-color:card-white}` … | 零引用（该组件在用的变体只有 `--map` / `--video` / `--cover`） | 约 20 行 |

> ⚠️ **删除方式有讲究（这不是「整段删」）**：第 9 项与在用变体写在同一条规则里，例如 488 行是
> `.sf-slot--document, .sf-slot--map { … }` —— 必须**按选择器拆分删除**（只摘掉 `--document` / `--photo` 分支），整块删除会连带删掉在用样式。这是本次审计发现的**唯一一处需要拆分的删除**。

### 🟡 可能可删（需你确认）

| 项目 | 位置 | 判断 | 说明 |
|---|---|---|---|
| `.sf-slot--photo` / `--document` 变体 | 同上 | 是否作为「预留扩展位」有意保留？ | `.sf-slot` 是一个槽位系统，`--map`/`--video`/`--cover` 在用。删掉未用变体零风险，但若近期打算加「图片位/文档位」则建议留着 |
| 20 个「同选择器在非媒体上下文重复定义」 | 见下 | **不是误重复**，而是带注释的设计迭代 | 删/合并需人工判断，有视觉回归风险 |
| 14 处过时厂商前缀 | 见 §7 | 现代浏览器已忽略，删了更整洁 | 收益≈0，纯整洁 |
| 10 个单次使用的媒体查询断点 | 见下 | 均有明确组件用途，**不是废弃断点** | 不建议删；可考虑收敛 |

**关于「重复定义的选择器」（修正后的准确结论）**：

花括号深度计数（修正了首版解析器对嵌套 `@media` 归属不准的问题）后：

- 选择器中**有 176 个出现了 ≥2 次**；
- 其中**只有 20 个**存在「非媒体上下文里的重复定义」，剔除 `@keyframes` 的 `from`/`to` 后为 **18 个**；
- 这 18 个**全部**属于「分区块覆盖 / 设计迭代」，且多数在重复处上方就有解释性注释，**并非误重复**：

| 选择器 | 定义行（`grep -n` 实证） | 性质 |
|---|---|---|
| `.sf-certrow` | 2456 / 4761 / 6906 | 证书行组件的 v1 → v2 → v3 三代布局（4761 与 6906 上方都有长注释说明改了缩略图列宽与卡片化） |
| `.sf-certdetail` | 2453 / 6901 | 同上（`4fr/6fr` → `120px + 1fr` → 双列卡片） |
| `.sf-certrow__media a` / `__media img` / `--placeholder`(+`span`) / `__name` / `__issuer` / `__desc` / `__links` | 2469/4766、2472/4770、2482/4791、2492/4800、2497/4804、2502/4807、2508/4811、2514/4816 | 同属上述三代迭代 |
| `.sf-slot--cover`（+ `.wp-block-image` / `img`） | 766 / 4174 / 4228（+ 4181/4233、4186/4241） | 首页槽位样式在后续区块中被重新声明 |
| `.sf-header` | 1594 / 1848 / 1860 | 基础头 + 吸顶态 + 变体 |
| `.sf-slot--photo` / `--map` / `--video` | 628/633/636、636/2022、637/1682 | 槽位变体家族的分处声明 |
| `.sf-statbar__num` | 3950 / 3976 | 数字带在第二处被重新声明 |

> 结论：**style.css 没有发现「误重复」意义上的冗余**。真正可删的 CSS 只有上表 🔴 的 3.0 KB。三代样式并存带来的问题是**可读性**（维护时容易改错那一代），不是体积。

### 🟢 建议保留

| 项目 | 实测结果 | 依据 |
|---|---|---|
| **CSS 变量未使用** | **基本不存在**。`style.css` 规则体内只定义了 1 个局部变量 `--wp--style--global--content-size`，且已被 `var()` 引用 | 首版报告的「12 个变量未被引用」是把 `.sf-panel--3:` / `.sf-coa__btn--ghost:` 这类**类名里的 `--`** 误当成变量定义，已修正 |
| **theme.json 调色板** | 12 个 slug，**12/12 全部被引用**（跨 style.css + configurator.css + templates + functions.php 验证） | `brand-green` 仅 style.css 引用 1 处，但在用 |
| **theme.json 间距档** | 7 个 slug，**7/7 全部被引用**（20 被 13 个源、40 被 20 个源、80 被 23 个源引用…） | 首版「5 个未引用」是只查了 style.css 造成的假阳性 |
| **theme.json 字号档** | `eyebrow`/`small`/`body` 被 `has-*-font-size` 类使用；`h1`/`h2`/`h3` 在模板与渲染输出中零命中 | h1–h3 是编辑器排版刻度（`clamp()` 响应式值），建议保留 |
| **`.htaccess` / Apache 相关注释** | **0 处** | 不存在这个清理项（nginx 环境，主题里本来就没写 Apache 规则） |
| `.no-has` 降级（8 处规则 + PHP 探针） | 在用 | 有意的 `:has()` 兼容层 |

---

## 2. JS 冗余（`assets/js/` 14 个文件 / 3,362 行 / 152 KB）

### 2.1 enqueue 矩阵（实测自 `functions.php`，含触发条件）

| 句柄 | 版本 | 加载条件 | 触发页面数 |
|---|---|---|---|
| `sticky-header` | 1.0.0 | 全局 | 全部 |
| `ui-components` | 1.0.0 | 全局 | 全部 |
| `mobile-nav` | 1.1.0 | 全局 | 全部 |
| `basket` | 1.3.0 | 全局 | 全部 |
| `quote-cta` | 1.0.0 | 全局 | 全部 |
| `toc-nav` | 2.0.0 | `is_front_page()` 或 12 个指定页面 或 单篇文章 | 首页 + 12 页 + 文章 |
| `hero-slider` | 1.1.1 | `is_front_page()` | 1 |
| `interactions` | 1.2.0 | `is_front_page()` | 1 |
| `about` | 1.3.0 | `is_page('about')` 或 `page-about` 模板 | 1 |
| `quality` | 1.1.0 | `is_page('quality')` 或 `page-quality` 模板 | 1 |
| `cert-modal` | 1.2.0 | 同上 | 1 |
| `configurator` | 2.2 | `$is_dosage_page`（8 个剂型页） | 8 |
| `product-slider` | 1.0.1 | 同上 | 8 |
| `formulas` | 1.0.0 | 同上 | 8 |

### 🔴 孤儿文件：**0 个**

14 个 JS 文件全部有 enqueue 入口，无未加载的孤儿脚本。

### 🔴 死函数：**0 个**

逐文件解析函数定义并回查调用点（含跨文件调用、`add_event_listener` 式引用、PHP/模板内联调用）后，**无零调用函数**。首版把 `interactions.js` 的 `frame()` 误判为死函数，实为 rAF 命名递归回调。

### 🟡 重复逻辑（真重复，可抽取公共实现）

| # | 重复项 | 涉及文件 | 重复量 | 依据 |
|---|---|---|---|---|
| 1 | **toast 实现被写了 4 遍** | `basket.js:112 function toast(message)`、`configurator.js:506`（内联创建）、`formulas.js:21 function showToast(message)`、`toc-nav.js:145 function toast(msg)` | 约 30 行 | 4 处都创建/复用 `.sf-toast` 元素、都设 `role="status"`、都有定时移除逻辑；`style.css` 里对应 3 条 `.sf-toast` 规则（样式是共用的，DOM 创建逻辑却没有） |
| 2 | **平滑滚动落点修正函数 100% 重复** | `quote-cta.js` 与 `toc-nav.js` 的 `settleAndCorrect(el, tries)` | 约 19 行（536 字符完全相同 × 2 份，另含 5 行相同说明注释） | 字节级比对：相似度 **100%**。逻辑是「懒加载图片会在滚动途中撑高文档，导致原生平滑滚动落点偏短 → 等滚动停稳后重新测量再补一次」 |
| 3 | **IntersectionObserver one-shot 包装** | `interactions.js` 有通用 `once(nodes, options, hit)`；`about.js:29` 内联写了一个同语义的实现（`io.unobserve` + reveal + 2.5s 兜底） | 约 10 行 | 两者语义一致（进入视口一次 → 取消观察 → 加类）。**但注意**：`interactions.js` 只在首页入队，`about.js` 只在上线页，抽取共享实现需要新建一个跨页面加载的文件——这属于**结构改动**，有回归风险 |
| 4 | 简单平滑滚动调用 | `basket.js:509`、`configurator.js`、`formulas.js` | 各 1 行 | **不是冗余**：它们只是调用原生 `scrollIntoView({behavior:'smooth'})`，不含落点修正逻辑，无抽取价值 |

> 判断：第 1、2 项是**真重复但收益小**（合计约 50 行 / 未压缩约 1.5 KB）。考虑到它们分布在「全局脚本」与「页面级脚本」两类加载边界上，抽取公共文件会**增加一次网络请求**，净收益可能是负的。建议做法：**若清理，就把它们合并进已有的全局脚本 `ui-components.js`**（它已经全局加载，不产生新请求）；否则保持现状。

---

## 3. PHP 冗余（`functions.php` 2,513 行 + `inc/` 2 个文件）

### 🔴 未被调用的函数：**0 个**

自定义函数 **29 个**，逐个回查调用点（含 `add_action`/`add_filter` 的字符串回调形式）后，零调用函数为 **0**。

### 🔴 废弃钩子（回调缺失）：**0 个**

注册钩子 **36 个**，全部能对应到实际存在的回调函数定义。

### 🔴 注释掉的代码块（>5 行）：**0 处**

扫描结果：`>5` 行的注释块共 36 处，其中 **34 处是纯说明性文档注释**（解释「为什么这样写」，是主题的资产），另 2 处为 `/**` 开头的 docblock（`functions.php:2440-2448`、`inc/config-pdf.php:2-27`）。**没有发现整段被注释掉的代码**。

### 🔴 已废弃的 WP 函数调用：**0 处**

针对 `get_the_author_email`、`query_posts`、`get_currentuserinfo`、`create_function`、`ereg`、`get_usermeta`、`wp_get_single_post`、`screen_icon` 等 20 余个已废弃 API 的定向检索结果为空。

### 🟡 待确认项

| # | 位置 | 内容摘要 | 判断依据 | 体积 |
|---|---|---|---|---|
| 1 | `functions.php:1914` | `preg_match_all('/<span class="sf-spec-term">([^<]+)<\/span><span class="sf-spec-value">([^<]+)<\/span>/', $html, $rows)` —— Product Schema 的 `additionalProperty` 规格解析 | 该正则要求的 `sf-spec-term` / `sf-spec-value` span 在**全站渲染输出中 0 出现**（A/B/C 三源零命中），说明这个解析分支当前拿不到任何输入。同时 `functions.php:1875/1912` 的注释还在点名已无 markup 的 `sf-spec-list` | 约 6 行 |
| 2 | — | 是否存在**不同名但功能相同**的 helper | 未发现。主题的自定义数据都有单一入口（如 `sf_default_certifications()` 为认证数据的唯一来源）。已确认无重复 helper | 0 |

> 关于第 1 项：**不建议直接删**。它是「有 markup 就自动生成 Schema」的容错分支，留着不产生开销，删掉反而在将来补回规格表时丢失能力。正确动作是**修注释**（把已不存在的 `sf-spec-list` 说明改成实际在用的结构），属于文档问题而非冗余。

---

## 4. 模板冗余（`templates/` 26 个 + `parts/` 3 个）

### 🟡 未被任何页面引用的模板文件：**1 个**

| 位置 | 内容摘要 | 判断依据 | 体积 |
|---|---|---|---|
| `templates/home.html` | `<!-- wp:template-part {"slug":"header"…} /-->` + `<!-- wp:template-part {"slug":"blog-index"} /-->` + footer | **与 `templates/page-blog.html` 字节完全相同**（两者均 179 字节，md5 `0ced1734b6`）。`home.html` 是 WordPress 模板层级里的「文章索引」模板，但：① 首页由 `front-page.html` 服务；② 博客列表 `/blog/` 是一个**页面**，由 `page-blog.html` 服务。即 `home.html` **没有可达路由** | 179 B |

> 删除前置条件：确认后台「设置 → 阅读 → 主页显示」不会切换为「文章列表」。一旦切换，`home.html`（或缺失时的 `index.html`）才会被启用。

### 🟢 建议保留

| 文件 | 原因 |
|---|---|
| `templates/index.html`（1,248 B） | WordPress **必需**的兜底模板（主题标准要求），当前未被命中但删除会造成主题不合规 |
| `templates/page.html`（1,771 B） | **在用**：服务无专用模板的页面（隐私政策 / Cookie 政策 / 服务条款），内含 `{{TITLE}}` 面包屑与 `wp:post-content` |
| `parts/header.html`、`parts/footer.html` | 各被 **25 个模板** 通过 `"slug"` 引用 |
| `parts/blog-index.html` | 被 `home.html` 与 `page-blog.html` 引用（删除 `home.html` 后仍被 `page-blog.html` 使用） |

### 区块卫生：**全部干净**

| 检查项 | 结果 |
|---|---|
| `<!-- wp:html -->` 块 | 共 **100 个**，**空块 0 个** |
| 空 `<p></p>` 段落块 | **0 处** |
| 自闭合块误写 `/ -->`（正确写法 `/-->`） | **0 处** |
| 内容完全相同的模板组 | 仅 `home.html` == `page-blog.html`（即上表 🟡 项） |

---

## 5. 图片冗余

**两个位置**：媒体库 `uploads/`（104 文件 / 30 MB）与主题内置 `assets/images/`（13 文件 / 11.4 MB）。

### 🔴 uploads/ 中整族零引用的文件：**23 个 / 18.6 MB**

判定依据：按「文件家族」判定（去掉 `-WxH`、`-scaled` 后缀后同名视为一族，任一派生尺寸被引用即整族在用），全族在 A + B + C 三源零命中。

| 文件（族） | 文件数 | 体积 | 说明 |
|---|---|---|---|
| `微信图片_20260629142652_11_458.jpg`（含 -scaled / -2048x1535 / -1536x1152 / -1024x768 / -768x576 / -300x225 / -150x150） | 8 | **7.33 MB** | 最大单项。媒体库**有记录**（附件 ID 42）但无任何页面引用 |
| `hero-facility.png` | 1 | 2.24 MB | PNG 原图，站点用 `.webp` |
| `powders.png` | 1 | 1.69 MB | 同上 |
| `soft-chews.png` | 1 | 1.37 MB | 同上 |
| `dental-chews.png` | 1 | 1.20 MB | 同上 |
| `fish-oil.png` | 1 | 1.07 MB | 同上 |
| `pastes.png` | 1 | 1.04 MB | 同上 |
| `drops.png` | 1 | 0.97 MB | 同上 |
| `liquids.png` | 1 | 0.97 MB | 同上 |
| `tablets.png` | 1 | 0.96 MB | 同上 |
| `hero-line.webp` | 1 | 123 KB | 被 `hero3-line.webp` 取代 |
| `hero-facility.webp` | 1 | 119 KB | 被 `hero1-exterior.webp` 取代 |
| `hero-lab.webp` | 1 | 80 KB | 被 `hero2-lab.webp` 取代 |
| `world-map.webp` | 1 | 27 KB | 世界地图已改为内联 SVG |
| `burst/js/burst.min.js` | 1 | 13 KB | 已卸载插件的残留（见下） |

### 🔴 主题内置 `assets/images/` 中零引用的文件：**11 个 / 11.37 MB**

| 文件 | 体积 |
|---|---|
| `Macro_product_photography_of_f_…png` | 1.69 MB |
| `Wide_angle_interior_view_of_a__…png` | 2.24 MB |
| `Macro_product_photography_of_d_…png` | 1.37 MB |
| `Macro_product_photography_of_e_…png` | 1.20 MB |
| `Macro_product_photography_of_g_…png` | 1.07 MB |
| `Product_photography_of_a_matte_…png` | 1.04 MB |
| `Product_photography_of_a_small_…png` | 0.97 MB |
| `Product_photography_of_a_white_…png` | 0.97 MB |
| `Macro_product_photography_of_r_…png` | 0.96 MB |
| `configurator-preview.png` | 117 KB |
| `sinofresh-logo-nav.png` | 9.9 KB |

**额外发现——跨位置重复（同一文件存了两份）**：

经 md5 逐对比对，上述 9 个 `…photography…png` 与 `uploads/2026/09/` 下的剂型图**内容完全相同**（9 对一一对应）：

```
assets/images/Macro_product_photography_of_r_….png  ==  uploads/2026/09/tablets.png
assets/images/Wide_angle_interior_view_of_a__….png  ==  uploads/2026/09/hero-facility.png
assets/images/Macro_product_photography_of_e_….png  ==  uploads/2026/09/dental-chews.png
assets/images/Product_photography_of_a_white_….png  ==  uploads/2026/09/liquids.png
assets/images/Macro_product_photography_of_f_….png  ==  uploads/2026/09/powders.png
assets/images/Product_photography_of_a_small_….png  ==  uploads/2026/09/drops.png
assets/images/Macro_product_photography_of_g_….png  ==  uploads/2026/09/fish-oil.png
assets/images/Product_photography_of_a_matte_….png  ==  uploads/2026/09/pastes.png
assets/images/Macro_product_photography_of_d_….png  ==  uploads/2026/09/soft-chews.png
```

即：这批 AI 生成图**在两个位置各存了一份，且两份都没有被站点使用**。

### 🟡 家族在用、个别衍生尺寸无引用：**3 个 / 44 KB**

| 文件 | 体积 | 说明 |
|---|---|---|
| `sino-fresh-logo-1.png` | 37.7 KB | **建议保留**：这是 WordPress 的 `-scaled` 缩放**母版**，删除后后台「重新生成缩略图」将无源可用 |
| `sino-fresh-logo-1-150x150.png` | 1.9 KB | 可删（无 srcset 引用） |
| `blog-softchews-150x150.webp` | 4.8 KB | 可删（无 srcset 引用） |

### 🟡 已卸载插件的残留目录：**8.33 MB**

`active_plugins` 实测为：`gravityforms`、`translatepress-business`、`translatepress-multilingual`、`wp-consent-api`、`wp-mail-logging`、`wp-statistics` —— **不含 burst**，确认 Burst Statistics 已停用/卸载。

| 路径 | 体积 |
|---|---|
| `uploads/burst/maxmind/GeoLite2-Country.mmdb` | **8.31 MB** |
| `uploads/burst/maxmind/{index.php,.htaccess}` | 0 B |
| `uploads/burst/exports/{976b…,08b2…}/{index.php,.htaccess}` | 0 B |
| `uploads/burst/js/burst.min.js` | 12.7 KB |

> 🟢 `uploads/wp-statistics/.htaccess`（0 B）**保留**——WP Statistics 是**在用**插件，该文件是它的目录保护文件。

### 媒体库记录一致性：**健康**

| 检查项 | 结果 |
|---|---|
| 媒体库附件记录 | 9 条（ID 42 / 53 / 96 / 100 / 102 / 104 / 106 / 108 / 110） |
| **记录存在但磁盘无文件（孤儿记录）** | **0 条** ✅ |
| **文件存在但媒体库无记录（野文件）** | 95 个 / 29.1 MB（其中 `2026/09` 86 个：本主题所有图片均以「直接放置文件」方式引入，未注册进媒体库；`burst/*` 8 个；`wp-statistics/.htaccess` 1 个） |
| 整库内容哈希重复 | 3 组 → ① `fac-placeholder.webp` == `hero-facility.webp`（118.7 KB，删掉未引用的 `hero-facility.webp` 即解决）②③ 均为插件目录里的 `index.php`/`.htaccess` 保护文件（0 B，保留） |

---

## 6. 数据库冗余（全部只读 `SELECT`，未执行任何写操作）

### 6.1 🔴 最重要发现：一条 publish 状态的「僵尸模板」记录

| 字段 | 值 |
|---|---|
| ID / 类型 / 状态 | **91** / `wp_template` / **publish** |
| `post_name` | `front-page` |
| 体积 | **141,418 字符（约 141 KB）** |
| 创建时间 | 2026-09-17 20:36:10（从未修改过） |
| 主题归属 | `wp_theme` 分类法 → `sinofresh-theme` 术语（**确实挂在本主题上**） |

**它是否在生效？——实测结论：没有生效，但存在被激活的风险。**

三条独立证据：

1. **前台渲染比对**：前台首页 HTML 含 2026-09-19 之后才写入 `templates/front-page.html` 的标记（`sf-card__title-link` 3 处、`sf-card__more` 3 处、`200+` 1 处、`See Our Quality Control` 1 处），而这些在 ID 91 中计数**全为 0**（该记录早于这些改动）。
2. **反向证据**：ID 91 独有的 `sf-slot--photo`（6 处）在前台渲染输出中计数为 **0**。
3. **WordPress 自身 API**：CLI 调用 `get_block_template('sinofresh-theme//front-page')` 返回 `source=theme`、内容长度 **135,309**（= 文件模板长度），且返回内容**不含** `sf-slot--photo` — 即 WP 解析到的是文件模板。

**风险**：`get_block_templates(['slug__in'=>['front-page']])` 返回的该模板对象携带 `wp_id=91`。这意味着 WordPress 把它视为「与文件模板同 slug 的数据库记录」——一旦有人在**站点编辑器**里打开模板列表并保存/重置，这条 2026-09-17 的旧内容有可能被激活，把首页回退到旧版本。

**建议**：上线前处理（先转 `trash` 观察一个发布周期，确认首页无变化后再彻底删除）。**必须先做数据库备份。**

### 🟡 其他数据库冗余

| 项目 | 数量 | 体积/说明 |
|---|---|---|
| 已删除（trash）的 `wp_template` | 6 条 | `front-page`×5（52/66/67/68/69/70）+ `page-products`(77) + `index`(7)，合计约 1.0 MB |
| 上述模板的 `revision` | 6 条 | 约 0.6 MB（每条约 105 KB） |
| 回收站内容（`post_status='trash'`） | 23 条 | 含对应 `_edit_lock` 23 条、`_wp_trash_meta_*` 23×3 条 |
| 自动草稿（`auto-draft`） | 12 条 | 编辑器产生的空壳 |
| 文章修订版（`revision`） | 33 条 | — |
| **`burst_*` 残留 option** | **31 条 / 1,408 字节** | 已卸载插件 Burst Statistics 的配置残留（`burst_options_settings`、`burst_plugin_slug`、`burst_geo_ip_file` 等），其中 2 条 `autoload` 为 `on`/`auto` |
| **传统小工具 option** | **21 条 / 1,542 字节** | `widget_*` + `sidebars_widgets`。实测主题**未注册任何侧栏**（`functions.php`/`inc/` 中 `register_sidebar`、`widgets_init` 零命中），块主题不使用传统小工具 |
| 其他主题的 `theme_mods` | 2 条 | `theme_mods_twentytwentyfive`（340 B）、`theme_mods_twentytwentythree`（273 B）——均为未启用的自带主题 |
| `recently_activated` / `uninstall_plugins` | 2 条 | 6 B / 99 B 的历史痕迹 |

### 🟢 数据库健康项（**无问题**，无需清理）

| 检查项 | 结果 |
|---|---|
| 孤儿 `postmeta`（无对应文章） | **0 条** ✅ |
| 孤儿 `usermeta`（无对应用户） | **0 条** ✅ |
| 孤儿 `wp_term_relationships`（无对应对象） | **0 条** ✅ |
| **已过期未清理的 transient** | **0 条** ✅（31 条带 timeout 的 transient 全部未过期） |
| `autoload` 体积 | `off` 128 条 3.85 MB / `on` **111 条仅 44 KB** / `auto` 90 条 21 KB → 自动加载体积**健康**（44 KB 属优秀水平） |
| 单条最大 option | `_site_transient_wp_font_collection_url_…google-fonts-with-preview.json` **3.18 MB**，`autoload=off`（WP 核心的字体库预览缓存，会自行过期重建，**不建议手动删**） |

---

## 7. 兼容性代码

### 🟡 已不需要的 CSS 厂商前缀：**14 处**

现代浏览器（Chrome/Edge/Safari/Firefox 现版本）已普遍支持无前缀写法，以下属可清的死代码：

| 声明 | 处数 | 为什么可清 |
|---|---|---|
| `-webkit-overflow-scrolling: touch` | **11** | iOS 13 起系统已移除该属性的作用（滚动惯性成为默认行为），现行 Safari 忽略它 |
| `-webkit-radial-gradient(…)` | 2 | 无前缀 `radial-gradient()` 自 2013 年起全浏览器支持 |
| `-webkit-backface-visibility` | 1 | 无前缀 `backface-visibility` 早已全支持（同段若有 `-webkit-transform-style` 需一并核对） |

### 🟢 必须保留的 `-webkit-`（11 处，勿删）

| 声明 | 处数 | 保留原因 |
|---|---|---|
| `-webkit-scrollbar` / `::-webkit-scrollbar` | 5 | 自定义滚动条样式在 Chromium/Safari 中**仍然只能**用这个前缀选择器 |
| `-webkit-details-marker` | 3 | 隐藏 `<summary>` 默认三角标记，Safari 中仍需前缀（无前缀 `::marker` 尚未覆盖该场景） |
| `-webkit-mask-image` | 2 | Safari 的 `mask-image` 支持仍以 `-webkit-` 为主 |
| `-webkit-line-clamp` + `-webkit-box` / `-webkit-box-orient` | 3 | 多行截断的既有标准写法（`display:-webkit-box` 与 `-webkit-box-orient:vertical` 是 `line-clamp` 生效的前提） |
| `-webkit-tap-highlight-color` | 1 | iOS 专有属性，无替代品 |
| `-webkit-backface-visibility`（另一处） | — | 见上，需按用途逐个核对 |

> 合计：`style.css` + `configurator.css` 中共 25 处 `-webkit-`，**14 处可清、11 处保留**。`-moz-` / `-ms-` / `-o-` 前缀：**0 处**。

### 🟢 已废弃的 WP 函数 / 旧浏览器 polyfill：**均无**

| 检查项 | 结果 |
|---|---|
| 已废弃 WP 函数调用 | **0 处** |
| jQuery 依赖式实现 | **无**。仅 2 处使用 `window.jQuery` 且有 `if (window.jQuery)` 守卫（`cert-modal.js:311`、`basket.js:279`），用途是挂接 Gravity Forms 的 `gform_confirmation_loaded` 事件（GF 自带 jQuery），属正确用法的互操作，不是可清冗余 |
| IE 专属写法（`attachEvent` / `document.all` / `innerText`） | **0 处** |
| `XMLHttpRequest` 手写 AJAX | **0 处**（统一用 `fetch`） |
| 旧浏览器 polyfill | **无**。唯一的兼容层是 `:has()` 能力探针（`functions.php:53-56` 注入 `html.no-has`）+ `style.css` 中 8 处 `html.no-has` 规则 —— 这是**针对老 Android/iOS WebView 的有意降级**，应保留 |
| `prefers-reduced-motion` | 覆盖 10 个 JS 文件 + CSS 媒体查询 → 无障碍支持，保留 |

---

## 8. 额外发现：主题目录内的「非运行文件」（部署卫生）

这一类不在原任务清单里，但它对上线的影响**大于上述任何一项**——审计中发现主题目录里混入了大量开发期产物：

| 目录 | 文件数 | 体积 | 性质 |
|---|---|---|---|
| `screenshots/` | 104 | **34 MB** | 开发期验收截图 |
| `_backup/` | 345 | **24 MB** | 历次改动前的备份副本 |
| `tools/` | 103 | **15 MB** | 探针脚本与日志 |
| `docs/` | 3 | 40 KB | 文档（含本报告与实拍清单） |
| `_backup_x/` | 0 | 0 B | 空目录 |
| `.DS_Store` | 3 | — | macOS 元数据 |

| 对比项 | 体积 |
|---|---|
| 主题目录全部 | **86 MB** |
| 运行必需（`assets/` + `templates/` + `parts/` + `inc/` + `style.css` + `functions.php` + `theme.json`） | **13 MB** |
| **非运行部分占比** | **73 MB / 85%** |

> 若把整个主题目录打包上传，生产环境会多出 73 MB 无用文件（且 `_backup/` 里是**旧版本源码**，等于把历史代码一起公开）。这不需要删除本地文件，只需在部署时排除这几个目录。

---

## 9. 总结

### 9.1 冗余总量统计

| 类别 | 🔴 确定可删 | 🟡 可能可删 | 🟢 建议保留（有意/在用） |
|---|---|---|---|
| **1. CSS** | 9 个孤儿 class / 30 条规则 / **112 行 / 3.0 KB** | 18 个有意重复选择器（合并需人工判断）；14 处过时前缀；2 个槽位变体 | 12 个调色板 + 7 个间距档全部在用；`.no-has` 降级层；11 处必需 `-webkit-` |
| **2. JS** | 孤儿文件 **0**、死函数 **0** | 重复逻辑 3 组（toast×4、`settleAndCorrect`×2、IO 包装×2）≈ **50 行 / 未压缩 1.5 KB** | 14 个脚本全部在用；无 jQuery 依赖；无 polyfill |
| **3. PHP** | 死函数 **0**、坏钩子 **0**、注释掉的代码 **0**、废弃 API **0** | 1 处已无输入的 Schema 解析分支（6 行，建议改注释而非删） | 29 个函数 + 36 个钩子全部有效 |
| **4. 模板** | 空 `wp:html` **0**、空段落 **0**、`/ -->` 误写 **0** | `home.html`（**179 B**，与 `page-blog.html` 字节相同，无路由可达） | 25 个模板 + 3 个 part 在用；`index.html` 为 WP 必需兜底 |
| **5. 图片** | `uploads/` **23 个 / 18.6 MB**；主题 `assets/images/` **11 个 / 11.4 MB**；插件残留目录 **8.33 MB** | 2 个无引用的缩略图尺寸（**6.7 KB**）；1 个 `-scaled` 母版（保留） | 在用图 81 个；媒体库孤儿记录 **0** |
| **6. 数据库** | 僵尸模板 **1 条 / 141 KB**；trash 模板 **6 条 / 1.0 MB**；模板 revision **6 条 / 0.6 MB**；burst option **31 条**；传统 widget option **21 条** | 23 条回收站内容 + 12 条自动草稿 + 33 条 revision；2 个外来主题 `theme_mods` | 孤儿 meta **0**；过期 transient **0**；autoload 仅 44 KB |
| **7. 兼容性** | — | 过时 `-webkit-` 前缀 **14 处** | 必需前缀 11 处；`:has()` 降级层；`prefers-reduced-motion` |
| **（附）部署卫生** | 非运行目录 **73 MB**（`_backup` 24 + `screenshots` 34 + `tools` 15） | — | 运行必需 13 MB |

**合计可回收体积（不含需人工判断项）**：
- `uploads/` 未引用图片 + 插件残留：**27 MB**（30 MB → 约 3 MB 有效图）
- 主题 `assets/images/` 未引用：**11.4 MB**（11.4 MB → 0.03 MB）
- 主题非运行目录不上传：**73 MB**
- 数据库：**约 1.6 MB** 行数据 + 1 条高危僵尸模板
- 代码行数：CSS 112 行、JS 约 50 行、模板 179 B

### 9.2 清理后预估收益（**含一项与预期不符的诚实结论**）

| 维度 | 收益 |
|---|---|
| **体积** | 生产主题 **86 MB → 13 MB（−85%）**；`uploads/` **30 MB → 约 3 MB（−90%）**；数据库减少约 1.6 MB 行数据 |
| **加载提速** | ⚠️ **基本为 0，不要期待这一项**。上述待删文件**都不在请求链上**（实测 24 个 URL 的全部资源请求均返回 200，且从未请求过这些文件）；代码侧只减 112 行 CSS（3 KB / 占 1.3%）与约 50 行 JS（未压缩 1.5 KB），对 FCP/LCP 无可测量影响 |
| **真正的收益在哪** | ① 部署与备份时间（少传 73 MB）② 仓库/备份体积 ③ 媒体库与后台的干净度（找图不再被 15 个无用文件干扰）④ **消除 1 条可被激活的僵尸首页模板（风险归零）**⑤ 维护时不再踩到三代并存的证书样式 |
| **想要加载提速，需要的是另一条路线** | 图片格式与尺寸压缩、字体子集化、关键的 CSS 内联/拆分、第三方面板脚本（TranslatePress / WP Statistics / GF）的延迟加载 —— 这些**不属于本次冗余清理的范畴** |

### 9.3 建议清理顺序（按 ROI 排序）

| 顺序 | 动作 | ROI | 前置动作 | 风险 |
|---|---|---|---|---|
| **0** | 清掉 Local 部署副本里 15 个陈旧残留文件（主题根 13 + `parts/` 2，源码中本来就没有，见 §10） | ★★★★★ | 无需备份（源码是唯一真源，这些文件在源码中无对应物） | **无**（零引用、WP 从不加载） |
| **1** | 部署时排除 `_backup/` `_backup_x/` `screenshots/` `tools/` `docs/` `.DS_Store` | ★★★★★ | 无（不删本地文件） | **无** |
| **2** | 删除主题 `assets/images/` 中 11 个零引用文件（含 9 个与 uploads 重复的 AI 图） | ★★★★★ | 备份 + 记录清单 | **极低**（零引用，且有 uploads 副本兜底） |
| **3** | 清理 `uploads/` 未引用图片（23 个 / 18.6 MB）与 `burst/` 残留目录 | ★★★★☆ | **先全量备份 uploads**；确认无邮件签名/PDF 模板引用 | 低（注意保留 `sino-fresh-logo-1.png` 母版） |
| **4** | 处理 DB 僵尸模板 ID 91（先转 trash）+ 清理 trash 模板与 revision | ★★★★☆ | **数据库备份**（参照既有 `_db_backup/`） | 中（转 trash 后需观察首页是否变化） |
| **5** | 清理 `burst_*`（31 条）与传统 widget option（21 条） | ★★★☆☆ | 数据库备份 | 低（但需确认无插件读它们） |
| **6** | 删除 `templates/home.html` | ★★☆☆☆ | 确认「设置→阅读」不会切为文章列表 | 低 |
| **7** | 删除 CSS 孤儿样式（9 个 class / 112 行）**注意按选择器拆分** | ★★☆☆☆ | 备份 style.css | 低（务必不要整块删 488 行那条混合规则） |
| **8** | 删除 14 处过时 `-webkit-` 前缀 | ★☆☆☆☆ | — | 低（但需在 Safari + iOS 实机回归一次） |
| **9** | JS 重复逻辑抽并（toast / settleAndCorrect） | ★☆☆☆☆ | 建议合并进已全局加载的 `ui-components.js`，避免新增请求 | 中（跨页面加载边界改动，需全站回归） |
| **10** | 两代证书样式合并（`.sf-certrow` v1/v2/v3） | ★☆☆☆☆ | 需先确认是否还需要回退到旧版 | **高**（视觉回归） |

### 9.4 清理风险提示

**必须备份的目标**
- `uploads/` 全目录：有唯一副本的图（微信图片族）在媒体库里有记录，删除后记录会变成孤儿 → 先备份再删
- 数据库：僵尸模板 ID 91、trash 模板、option 清理**全部**需要先导出（`.sql`），并保留至少一个发布周期
- `style.css`：孤儿样式与证书样式的删除都涉及级联分支，需可回滚

**必须灰度/回归验证的目标**
- CSS 删除后：24 个 URL 的区块截图对照（尤其 `quality` 页的证书区、剂型页的配置器）
- JS 抽取后：toast（询盘篮 PDF 下载/复制邮箱/表单预填）、锚点平滑滚动（TOC 点击 / Quote CTA）、首页 reveal 与 count-up
- 僵尸模板转 trash 后：首页 HTML 指纹比对（应零差异）
- `-webkit-` 前缀删除后：Safari（macOS + iOS）实机各一次

**不要删的项（易误判）**
- `uploads/2026/09/sino-fresh-logo-1.png` —— WordPress `-scaled` 缩放母版
- `uploads/wp-statistics/.htaccess` —— 在用插件的目录保护文件
- `_site_transient_wp_font_collection_url_…`（3.18 MB）—— WP 核心缓存，会自动过期重建
- `.no-has` 相关规则、`.admin-bar`、`.is-not-stacked-on-mobile`、`.always-shown` —— 见 §0.1 假阳性清单

### 9.5 建议

审计结论是：**这份代码库本身相当干净**。代码层（CSS/JS/PHP/模板）几乎没有真正意义上的冗余——死函数 0、空块 0、废弃 API 0、孤儿脚本 0、媒体库孤儿记录 0、过期 transient 0；唯一确定的代码冗余只有 112 行 CSS 与约 50 行 JS。

**冗余的真正体量在「文件」，不在「代码」**：可回收的 111 MB 里有 110 MB 是图片与开发期产物。因此建议的优先级是「先清体积（第 1–3 步，零风险高收益），再清数据库（第 4–5 步，需备份），代码层留到最后且按需做（第 7–10 步收益极小）」。

按用户既定节奏（CWV 优化 + 删守卫 + 素材替换完成后再一次性清理）执行时，建议把本报告的第 4 步（僵尸模板）**提前单独处理**——它与其它任务无耦合，却是唯一带「可能回退首页」风险的项。

---

## 10. 补检：源码 ↔ Local 部署目录双向差异（初稿遗漏项，已补齐）

**为什么补这一节**：第 1–9 节都是「在源码里找冗余」，但从未把**源码目录**与**实际被 WordPress 加载的 Local 主题目录**做一次 `diff -rq`。补做后发现：两侧**双向不一致**，且两侧多余文件的性质完全不同。

| 方向 | 文件数 | 体积 | 性质 |
|---|---|---|---|
| **源码独有**（Local 没有） | 11 | **11.37 MB** | `assets/images/` 里 11 张 AI 占位图 —— 与 §5.2「主题零引用图片」**是同一批**（互为印证，非新增） |
| **Local 独有**（源码没有） | **15** | **≈ 603 KB** | 目录结构重组前留在旧位置的**陈旧副本** —— 本节新增发现 |

### 10.1 Local 独有的 15 个陈旧文件（🔴 确定可删）

成因：这些文件**曾经在主题根目录**，后来被移入 `assets/js/`、`assets/css/`、`parts/`、`templates/`；每次同步都是「增量 cp 单文件」，没有做过反向清理，于是旧副本一直留在 Local。

| Local 残留路径 | 体积 | mtime | 源码中的正确位置 | 正确文件体积 |
|---|---|---|---|---|
| `basket.js` | 2,417 B | 09-18 07:17 | `assets/js/basket.js` | 17,102 B |
| `configurator.css` | 18,517 B | 09-18 07:17 | `assets/css/configurator.css` | 23,045 B |
| `configurator.js` | 20,509 B | 09-18 07:17 | `assets/js/configurator.js` | 30,090 B |
| `formulas.js` | 3,157 B | 09-18 06:47 | `assets/js/formulas.js` | 3,157 B |
| `hero-slider.js` | 2,092 B | 09-15 21:24 | `assets/js/hero-slider.js` | 4,905 B |
| `header.html` | 8,197 B | 09-16 13:39 | `parts/header.html` | 4,074 B |
| `footer.html` | 7,647 B | 09-16 12:23 | `parts/footer.html` | 16,752 B |
| `front-page.html` | 146,814 B | 09-16 21:25 | `templates/front-page.html` | 135,309 B |
| `page-soft-chews.html` | 47,045 B | 09-16 13:40 | `templates/page-soft-chews.html` | 60,150 B |
| `page-dental-chews.html` | 58,111 B | 09-17 06:31 | `templates/page-dental-chews.html` | — |
| `page-drops.html` | 49,258 B | 09-17 06:31 | `templates/page-drops.html` | — |
| `page-fish-oil.html` | 49,048 B | 09-17 06:31 | `templates/page-fish-oil.html` | — |
| `page-liquids.html` | 49,542 B | 09-17 06:31 | `templates/page-liquids.html` | — |
| `parts/functions.php` | 33,748 B | 09-16 23:38 | `functions.php`（主题根） | 105,847 B |
| `parts/style.css` | 121,257 B | 09-16 23:38 | `style.css`（主题根） | 237,005 B |

> 注意第 14、15 项：`parts/functions.php`（33.7 KB）与 `parts/style.css`（121 KB）都是**旧版本**——真正的 `functions.php` 是 105.8 KB、`style.css` 是 237 KB。若误把 `parts/` 里这两个当成真源，会直接回到 9 月 16 日的代码状态。

### 10.2 判定依据（三条独立证据）

1. **引用计数 = 0**：精确 token 检索主题全部源码中指向根级路径的引用（`/basket.js`、`/configurator.css`、`/configurator.js`、`/formulas.js`、`/hero-slider.js`）→ **全部 0 命中**。
2. **正确位置上存在更完整的那一份**：Local 的 `assets/js/basket.js`（17,102 B）、`assets/js/hero-slider.js`（4,905 B）等全部存在且体积更大、mtime 更新 → 根级那份是旧副本。前台实测加载的也是 `assets/` 路径（`hero-slider.js?ver=1.1.1`）。
3. **WordPress 不会读它们**：块主题的模板发现只扫 `templates/` 与 `parts/`，**从不扫主题根目录的 `.html`**；`parts/*.php` 也不会被 WP 引入（WP 只从主题根加载 `functions.php`）。→ 这 15 个文件对运行完全惰性。

### 10.3 风险与处理时机

- **运行风险：无**。24 个 URL 全 200、资源请求全 200 已佐证；删掉后渲染不可能变化。
- **真正的风险是维护风险**：主题两份副本已不对称，将来若有人做反向同步（Local → 源码），会把 9 月 15–18 日的旧代码复活。这是 §9.4「不要删的项」最容易踩反的地方。
- **处理时机**：属部署/同步卫生，与 CWV 优化、删守卫、素材替换**均无耦合**，可与 §9.3 的第 1 步一起做（两步都不碰运行代码）。
- **只删 Local 侧的这 15 个文件，源码侧不需要任何改动**——源码本来就没有它们。

### 10.4 对前 9 节结论的影响

- §5.2 那 11 张「主题零引用图」不但是零引用，**在 Local 里根本不存在** → 删除风险再降一档（没有任何渲染路径依赖它们的物理存在）。
- §1–§7 其余结论**不变**：那些扫描的对象是源码，而源码是唯一真源；本次 `diff` 未发现「源码里有、Local 里内容不同」的运行时代码（`files differ` 行数为 **0**）。
- 本报告写在 `sinofresh-theme/docs/`，该目录在 Local 侧不存在，也**不应**同步过去——§8 已建议部署时不打包 `docs/`。

---

*审计执行方式：全部判定基于运行态实测（48 次页面加载）、全量源码正则扫描、源码↔Local 目录 diff 与数据库只读查询；未修改任何运行时代码、未写入数据库。*
