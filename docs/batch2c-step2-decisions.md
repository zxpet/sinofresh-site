# 批次 2C 第二步：`/formulas/` 档案页 —— 决策与实测全档（2026-09-20）

> 本文件是 `MEMORY.md` 中该节的**全文版**（MEMORY.md 只留摘要＋指针，因为自动注入有体积上限）。
> 逐条命令见同目录 `batch2c-step2-rollback.md`；内部链接清单见 `batch2c-step2-internal-links.md`。

## 一、已拍板决策

- **单页 21 卡**（弃 core 分页；岔路1＝B）；**只按剂型筛选**（8 个；岔路2＝B）；**前端 JS 过滤**（方案甲）。
  方案甲含义：21 张卡默认全在 DOM 且全可见，过滤只加 `.is-sf-off` 隐藏。
  ⛔ 不能用 `hidden` 属性——`.sf-fcard` 是 `display:flex`，作者样式会盖掉 `hidden`。
- **无 JS 降级**：head 内 inline `sf-js` 标记（`<script>document.documentElement.classList.add('sf-js')</script>`，仅档案页输出）＋ CSS `html:not(.sf-js) .sf-fchips-wrap{display:none}` ⇒ 无 JS 访客看到的是干净的 21 卡列表，不是 9 个死按钮。
  已知外观代价：无 JS 时白色筛选带只剩自身 24px×2 内边距（不做 `:has()` 补偿，避免再引一个 `!important`）。
- **路线**：**新建** `templates/archive-sf_formula.html`，`templates/archive.html` 一字不动 ⇒ /blog/、/category/*、/tag/*、/date/*、/author/*、/search/ 的 DOM 完全不变（「不删 DOM」的最强保证）。WP 层级上 `archive-sf_formula.html` 优先于 `archive.html`。crumb 用 `--d2`（两级：Home / Formulas），**不是** d4（d4 = Home/Products/Form/Name）。
- hero 贴边（27s 段 1024→1239px）与 18px 基准差**均不在本批**，另开批次。
- `[sf_archive_count noun="formula"]`：/blog/ 的 `articles` 用默认值保住，逐字节不变。
- 分页：`page/2,3` → 301 回 `/formulas/`；`page/4` 维持 404；**不动 `pre_get_posts`**（改主查询会让 page/2 变 404 而不是 301，且会影响 TP／wp-statistics 对主查询的读取）。

## 二、⚠️ R1 根因（本项目最值得记的一次「静默坏页」）

- 档案页的 queried object 是 **`WP_Post_Type`**，不是 `WP_Post`。
- `sinofresh_formula_current_form()` 因此走 URL 回退 → 取末段 `formulas`（`/formulas/page/2/` 取 `2`）→ `tax_query` 拿一个不存在的 term → **grid 渲染 0 张卡**。
- 全程**不报错、不写日志**，和「还没有配方」长得一模一样 —— 这类 bug 只有实测渲染才能发现。
- 改法（`6767d1c`）：显式 form 短路之后、`WP_Post` 分支之前插 `if (is_post_type_archive('sf_formula')) return '';`。唯一调用点是 `[sf_formula_grid]`；8 剂型页走显式 `form="X"` 短路、详情页走 `WP_Post` 分支 ⇒ 均不受影响。
- **不用**「给 shortcode 加 `form="all"` 魔法值」：`sanitize_title()` 会把它当 term slug，与未来同名 term 冲突。

## 三、⚠️ 301 的语言前缀坑（预检实测抓出）

- 第一版用 `home_url($path)` 拼目标 ⇒ `/zh/formulas/page/2/` 重定向到 **`/zh/zh/formulas/`**。
  原因：**TranslatePress 过滤 `home_url()` 给它补语言前缀**，而 `$path` 里已经有 `/zh/` 了。
- `get_post_type_archive_link()` 同样不能用：它返回英文 `/formulas/`，会把访客踢出当前语言。
- 正解：**站点相对路径** —— `wp_safe_redirect($target . $query, 301)`，`$target` 由 `REQUEST_URI` 的 path 去掉尾部 `/page/N/` 得到。`wp_safe_redirect()` 接受相对路径（`wp_validate_redirect()` 对无 host 的路径放行）。
- 复测：`/formulas/page/2|3/` → `301 /formulas/`；`/zh/formulas/page/2/` → `301 /zh/formulas/`；`page/4` → `404`；`/zh/formulas/` → `200`。

## 四、数据源与顺序（实测）

- chips：**Products 子页**（`get_pages(['parent'=>19, sort_column'=>'menu_order'])`）定序 ⇒ soft-chews, tablets, powders, pastes, drops, liquids, fish-oil, dental-chews。
  ⚠️ 与 `get_terms('sf_formula_form')` 的顺序**不同**（drops/liquids/fish-oil 位置有别），所以不能拿 `get_terms` 直接输出。
  标签走 `sinofresh_formula_label($slug, $term->name)`；count=0 的 term 跳过（不渲染死链）。
- 21 条**全部**有 form term（无「未分类」桶）。
- 21 卡顺序（`menu_order ASC, title ASC`）**跨剂型混排**：mo=1→8 条／mo=2→8 条／mo=3→4 条／mo=4→1 条（Skin & Coat Soft Chews）。已接受；按剂型过滤后＝剂型页顺序（同一 orderby）。
- 计数文案：`[sf_archive_count]` 原为**匿名闭包零形参**，`noun=` 被 PHP 静默丢弃（零形参闭包可多收参数且不报错）⇒ 档案页一直写「21 articles」。现为闭集 switch；⚠️ `_n()` **只选串不填 `%d`**，必须外面套 `sprintf()`。
- 筛选状态行：`role="status"`，数字单独一个 `<span class="sf-fchips-count">` ⇒ JS 只改数字，句子保持一条可翻译串（TP 友好）。

## 五、预检实测结果（2026-09-20，预检主题 × 线上真实库）

| 项 | 结果 |
|---|---|
| `/formulas/` | 200 / 129959 B（未上 CSS/JS） |
| 卡片 | 21 × `<article class="sf-fcard">` |
| chips | 9（all + 8 剂型，序同上） |
| K1 | 21 × `.sf-formula__cta`，其中 21 个带 `data-formula`，`data-form` **0**（子项三待补） |
| 无 JS 标记 | `sf-js` × 1 |
| 入队 | `formulas.js` × 1、`formula-filter.js` × 1 |
| 模板残留 | `{{` 0、`[sf_` 0 |
| 文案 | 计数「21 formulas」；crumb 与 H1 =「Formulas」 |
| JSON-LD | 3 块：ItemList 21 条 position 1..21；BreadcrumbList 2 项＝可见面包屑；Organization |
| 301/404 | page/2、3 → `/formulas/`；`/zh/formulas/page/2/` → `/zh/formulas/`；page/4 → 404 |
| 零回归 | A/A 掩码自检 PASS；15 页（8 剂型页＋/blog/＋/category/manufacturing/＋/tag/formulation/＋/＋/contact/＋详情页）掩码后 **逐页 SAME** |
| 日志 | php-fpm 与 httpd 无新 Fatal |

## 六、复核结论（方法论）

- `.sf-archive-grid` 在 `style.css` **零规则**（只出现在 archive.html 与 2 个 `_backup` 副本）⇒ 新模板不带它即自然消失。
- **`wp eval` 不跑主查询** ⇒ `wp eval --url=…` 报 `is_post_type_archive=false`、`found_posts=0` 是**假阴性**，据此判断会得出完全相反的结论。用注入 `REQUEST_URI` 的 `tools/sf_web_ctx_probe.php`（每条路径 `new WP()`，否则 `is_paged` 粘滞）。
- 裸 md5 不能用来比对：CF 给每个 mailto 生成新 token（见 `MEMORY.md` 掩码规则）。
- 旧自检脚本 `sinofresh-theme/tools/_cpt2a_render_check.php:178` 断言 `current_form('') === 'soft-chews'`：它须在 Web 上下文跑；CLI 下 `is_post_type_archive()` 恒 false，R1 改动不会让它变红。

## 七、待做（本步剩余）

1. **grid K1 补 `data-form="<form_slug>"`**（现在只有 `data-formula`）：剂型页取值与 URL 回退相同＝零回归；详情页 related 修掉垃圾 sessionStorage 键 `sinofresh_formula_formulas`；档案页才真正可用。
2. **CSS 37c 新段 + 36a 选择器列表加 `.sf-fchips`**；`style.css` 版本 2.10.43 → **2.10.44**；新建 `assets/js/formula-filter.js` 1.0.0（仅档案页入队，无库无框架）。
3. **8 个剂型页内部链接**（文件改动，Edit Site 无效）—— 见 `batch2c-step2-internal-links.md` §B，单独 commit 便于单独 revert。
4. **首次云端 pull + md5 + 14 项验收 + 截图**（桌面／手机／过滤后）。

## 八、子项③④（grid 数据属性 + 前端筛选）验证全档 —— 2026-09-20

> 提交：③ `f6baf96`（grid K1 `data-form` + 卡片 `data-sf-form`）、④ `be08814`（`formula-filter.js` 1.0.0 + `style.css` 37c/36a + 2.10.44 + 截图 + 5 个预检工具）。
> 两者都已 push（`origin/main = be08814`）；**云端 HEAD 仍 `d9b80dd`、未 pull**，线上主题与 DB 一字未动。

### 8.1 预检装置（方法在本轮升级）

- **只验 PHP 渲染**：mu-plugin 过滤 `theme_root` → 指向 `cp -a` 副本。够用于模板/短代码/钩子核验。
- **要验 CSS/JS ⇒ 必须换成「装成另一个主题」**：副本放 `public/wp-content/themes/sinofresh-theme-preflight/`，mu-plugin 过滤 `stylesheet` + `template`。
  **根因**：入队的样式/脚本 URL 由 **stylesheet directory URI** 拼出（`get_stylesheet_uri()` / `get_template_directory_uri()`），换 `theme_root` 只改 PHP 找模板的路径，HTTP 交付的仍是线上那份 `style.css`，新 `formula-filter.js` 直接 404。
  **误判形态**：页面 HTML 看起来全对（21 卡、9 chip、双脚本都入队），但浏览器里 `computed display` 全是基础值、点击毫无反应 —— 极易归咎于 JS 写错。本轮就是这个现象。
- **浏览器带门**：`agent-browser open <url> --headers '{"X-SF-Preflight":"1"}'`（按 origin 生效，同源后续导航继续带）。
- 用完即删：mu-plugin、预检主题目录、`/tmp` 传输文件；复验 `mu-plugins` 空、`/formulas/` = 200 / 114403 B、云端 `git status` 干净、带 header 也回到旧页。

### 8.2 服务端断言 50/50

| 组 | 结论 |
|---|---|
| `/formulas/` | 200、21 卡、9 chip（All + soft-chews/tablets/powders/pastes/drops/liquids/fish-oil/dental-chews＝menu_order 序） |
| 数据属性 | 21 `data-formula`、21 `data-form`、21 `data-sf-form`；各剂型卡数 4/3/3/2/2/2/2/3 |
| 卡序 | 渲染顺序 **deep-equal** `SELECT post_title … ORDER BY menu_order ASC, post_title ASC` |
| 入队/标记 | `sf-js` ×1、`formulas.js` ×1、`formula-filter.js` ×1、`style.css?ver=2.10.44` |
| 残留 | `{{` = 0、`[sf_` = 0 |
| 文案 | 计数「21 formulas」；计数 span = 21；`sf-fchips-status` role=status ×1 |
| JSON-LD | ItemList 21 条 position 1..21；BreadcrumbList 2 项 = 可见面包屑（Home / Formulas）；Organization |
| 301/404 | `/formulas/page/2|3/` → 301 `/formulas/`；`/zh/formulas/page/2/` → 301 `/zh/formulas/`；`/formulas/page/4/` → 404；`/zh/formulas/` = 200 |
| 8 剂型页 | 每页 `data-form` 值集合 = {自身 slug}，与 URL 回退值相同 ⇒ 零行为变化 |
| 详情页 | `/formulas/ear-care-drops/` 的 related 按钮 `data-form="drops"`（不再是 formula slug） |
| 资源交付 | 预检主题的 `style.css` 与 `formula-filter.js` 均 200，且内容含 37c 规则 |

### 8.3 浏览器断言 34/34（agent-browser，预检主题）

- **桌面 1440**：筛选带 `display:flex` 渲染；9 chip 顺序正确；All 默认 `aria-pressed="true"` + `.is-active`；21 卡全可见、0 隐藏；状态「Showing 21 of 21 formulas」；网格 4 列；rail `flex-wrap: wrap`。
- **过滤（真实点击）**：Soft Chews → **4 可见 / 17 隐藏**、可见剂型集合 = {soft-chews}、`aria-pressed` 与 `.is-active` 都只有 soft-chews、状态「Showing 4 of 21 formulas」、文档高度下降（无幽灵行）；点 All → 21 复原。
- **无 JS**：服务端 `<html lang="en-US">` **不带** `sf-js`（由 head 内联脚本加）；抹掉该 class 后筛选带 `display:none`、21 卡仍 4 列全可见、无死按钮、网格不动（文档高度 −72px ＝ 白色筛选带自身内边距，即已记录的已知外观代价）。
- **移动 375**：rail `flex-wrap:nowrap` + `overflow-x:auto` 且 `scrollWidth > clientWidth`（真的可横滑，宽 299px）；网格 1 列；点 Tablets → 3 可见 / 18 隐藏。
- 控制台无 page error。

### 8.4 掩码回归（15 页）

- **A/A 掩码自检 PASS**（/blog/、/formulas/）。
- 原始比对：15/15 DIFF —— 首个差异**每页都是** `style.css?ver=2.10.44` vs `2.10.43`。
- **入队资源清单**（独立报告）：**仅** `style.css 2.10.43 → 2.10.44` 一个令牌移动（15 页），其余 33 个资源令牌全同，**资源集合每页相同**。⇒ 「只掩不报」的风险被排除。
- **归一化三类预期差异**后：**15/15 逐页 SAME**。三类 = ①`?ver=` 令牌 ②预检主题目录名（每个资源 URL + `wp-theme-<name>` body class）③本次故意新增的两个属性。
  ⇒ 结论：8 剂型页与 2 详情页的**唯一** DOM 变化就是那两个属性；/blog/、/category/、/tag/、/、/contact/ 五页除版本令牌外**逐字节不变**。

### 8.5 截图

`sinofresh-theme/screenshots/batch2c-step2-formulas/`（7 张，共 2.84 MB）：
`01-desktop-bar-viewport.png`、`02-desktop-filtered-soft-chews.png`、`03-mobile-chips-rail.png`、`04-mobile-filtered-dental-chews.png`、`05-desktop-1440-full.jpg`、`06-mobile-375-full.jpg`、`07-nojs-bar-hidden-full.jpg`（全页大图用 `sips` 转 jpg 72 压体积）。

## 九、子项⑤⑥（8 剂型页内链 + 首次 pull）验证全档 —— 2026-09-20

> 提交：⑤ `2f63c88`（8 个 `page-*.html` 各 +3 行）、`ab938c4`（三件套预检工具 + 截图）。
> 云端 `git pull` 首次执行：`d9b80dd → ab938c4`（fast-forward）。
> **线上 `/formulas/` = 200 / 131108 B**（pull 前 114403 B）、`/zh/formulas/` = 200 / 139432 B。

### 9.1 子项⑤ 静态检查

| 检查 | 结果 |
|---|---|
| `git diff --numstat` | 8 文件 **各 +3 / −0**，共 24 插入、0 删除 |
| 插入内容一致性 | 8 页**逐字节同一**三行（`uniq -c` 各为 8） |
| 块结构 lint | 8 文件 stack balanced、3 self-closing、无畸形斜杠/花括号 |
| `grep -rn "/ -->" templates/` | **0**（全主题仅 1 处，是旧测试脚本 `_gf5_submit_test.php` 里的断言字面量） |
| 插入点 | 公式短代码 `wp:html` 块与 `</section>` 之间（第 39/40 行之间），`.sf-explore__btn` 复用 `configurator.css:899`，**零新增 CSS** |

### 9.2 子项⑤ 预检（基线 `098afe8` × 候选 `2f63c88`，同一请求头门 + 独立主题目录）

- 快照 34 页（8 剂型页 + 21 详情页 + `/formulas/`、`/zh/formulas/`、`/blog/`、`/products/`、`/`）。
- **A/A 掩码自检** 3 页 PASS（`/formulas/`、`/products/soft-chews/`、`/formulas/ear-care-drops/`，两次抓取字节完全相同）。
- 原始比对：**8 DIFF / 26 SAME**，8 个 DIFF 全是剂型页，首个差异点**都在插入位置**，字节增量**每页一致 +181 B**。
- 归一化（删掉新段落连同其前导空行 → 恰好还原基线的空行）后：**34/34 SAME**，且归一化后的候选**字节数逐页等于基线**。
- 定向证据 106/106：每页恰好 2 个描边按钮（`/formulas/` + `/products/`）、文案与标记 8 页同一、位置在最后一张卡之后且仍在公式 section 内、卡片数/卡序（`data-sf-form` 与 K1 `data-formula` 双序列）逐字节不变、5 个 JSON-LD blob **逐字节相同**、新锚点不在任何 JSON-LD 内。
- 浏览器 113/113：8 页桌面均为 `inline-block` + `2px rgb(27,77,62)` 描边 + 18px/… 内边距 + `margin-top:32px`（`spacing|40`）+ 居中 + 段落是 `#formulas` 最后一子元素、其后兄弟是 `configurator`；375px 档 `display:block` 且按钮宽＝段落宽 299px、高 ≥44px；真实点击跳转 `/formulas/`；gated 目标页 9 chip / 21 卡 / 0 剂型按钮；控制台零错误。

### 9.3 方法级新发现（两条，均为预检装置纪律）

1. **浏览器缓存会串「变体」**：CF 给 HTML 盖 `cache-control: max-age=86400`，浏览器**按 URL** 缓存；请求头门只在 PHP 层生效，缓存层不知情 ⇒ 同一 URL 若**先被不带门访问过**，之后带门也会命中旧缓存（本轮表现为「点击后跳去的 `/formulas/` 是未改造的线上版」）。
   ⇒ **纪律：预检期间所有带门访问排在任何不带门访问之前；点击类测试放最后。** 已写入 `b2c_s2s5_browser_check.py` 的分节顺序与注释。
2. **DB 层改动主题预检带不到**：用户用 Edit Site 给 Products 下拉加了 `All Formulas`（`wp_navigation` post 16），发生在预检快照之后 ⇒ pull 后线上每页比预检基线多 **196 B**（全 34 页各一处，位于 header）。
   ⇒ 归一化工具 `b2c_s2s6_norm_nav.py` 精确删该 `<li>` 并**断言每页命中恰好 1 次**（命中 0 = FAIL，防止「悄悄丢导航」被当成 SAME）；`/zh/` 页面上 TP 把 href 改写成 `/zh/formulas/`，故路径按 `/(?:zh/)?formulas/` 匹配。

### 9.4 子项⑥ pull 后线上验收

| 组 | 结论 |
|---|---|
| 工作区 ↔ 云端 md5 | **146 个文件全等**（`sinofresh-theme/` 全树，排除 `_backup*`/`screenshots`/`.DS_Store`） |
| `/formulas/` | 200、21 卡、9 chip（序 = menu_order）、`{{`/`[sf_` 残留 0、计数「21 formulas」、`sf-js` ×1、`formulas.js` ×1、`formula-filter.js` ×1、`style.css?ver=2.10.44`、状态行 role=status |
| 卡序 | 渲染顺序 **deep-equal** DB（`menu_order ASC, post_title ASC`） |
| JSON-LD | 块类型集 {BreadcrumbList, ItemList, Organization}；ItemList 21 条 position 1..21；BreadcrumbList 2 项 = 可见面包屑 Home / Formulas |
| 301/404 | `/formulas/page/2|3/` → 301 `/formulas/`；`/formulas/page/4/` → 404；`/zh/formulas/page/2/` → 301 `/zh/formulas/`（**恰好一个 `/zh/` 前缀**）；`/zh/formulas/` 200 |
| 剂型页（线上） | 8 页各 2 个描边按钮（`/formulas/` + `/products/`）、链接标记精确 1 处；卡数 4/3/3/2/2/2/2/3；`data-form` 集合 = 自身 slug |
| 详情页 | related K1 只有 1 种 `data-form`（如 `drops`），非 formula slug |
| 资产 | 线上 `style.css?ver=2.10.44` 含 37c；`formula-filter.js?ver=1.0.0` 200 且内容为筛选脚本 |
| **合计** | **67/67 PASS**（`tools/b2c_s2s6_live_check.py`，跑在 dev box 上、**不带门**） |
| 回归 | 线上 vs pull 前基线：归一化两类预期差异（预检主题目录名、DB 导航项）后 **34/34 逐页 SAME**；8 剂型页定向证据 **106/106**（含卡片与 JSON-LD 逐字节不变） |
| 日志 | `error.log` pull 后（UTC 11:40+）**非 pool 行 0**；全日志 `PHP Fatal/Warning` 计数 **0** |
| 残留 | mu-plugins 空、无 `-preflight` 目录、`/tmp` 传输文件清；预检期线上始终 200 / 114403 B（带门同样） |

### 9.5 截图

- 预检：`docs/b2c-step2s5-shots/`（3 张：桌面剂型页新按钮、桌面档案页、375 剂型页）。
- 线上：`sinofresh-theme/screenshots/batch2c-step2-formulas-live/`（5 张：`01-live-desktop-formulas`、`02-live-desktop-filtered-soft-chews`、`03-live-mobile375-chips-rail`、`04-live-desktop-dosage-entry-link`、`05-live-nav-products-dropdown`）。

### 9.6 导航（§A，用户用 Edit Site 自行完成）

实测 Products 下拉 **9 项**，序为 8 个剂型 + **`All Formulas` 末位**，href = `/formulas/`（`/zh/` 页上 TP 自动改写为 `/zh/formulas/`，正确）；与剂型页末尾的 `Browse All Formulas →` 构成「列表读完 → 去总览」的同构收束。
