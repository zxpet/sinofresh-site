# Batch G — 实施方案（详情页「主图 + 参数」两栏）

> 状态：**方案定稿 / 未动手**。等 §0.1 三处确认后开工。
> 范围：21 配方详情页 + 21 zh + 8 剂型页 + 8 zh = **58 页**
> 基线：服务器 `4504aa9`，线上版本 **2.10.53** → 目标 **2.10.54**
> 所有数字均为实测（2026-09-21，dev 站凭据访问 + MariaDB 直查），非推演。

---

## 0. 拍板已归档（7 项）

| # | 决策 | 定论 |
|---|---|---|
| 1 | Packaging | **A** — 8 剂型页 `.sf-facts-mini` 增第 4 行，`data-label="Packaging formats"`，值抄配置器 `data-group="packaging"` 选项集（去结尾 `Custom`，末尾加 `+ custom formats`） |
| 2 | 参数表与 `Specification` 重复 | 接受，两项都放 |
| 3 | 右栏 CTA | `Request Sample` → `/contact/`，单个按钮，主色实心 |
| 4 | 简介承载 | PHP 动态 + `sf_formula_intro` meta 覆写位 + 占位符 |
| 5 | 轮播 h2 | **保留**，点轨 4 点不变 |
| 6 | 命名 | **`.sf-fdetail-media`**（弃 `.sf-fdetail-hero`） |
| 7 | zh 简介 | 维持英文 |

---

## 0.1 ⚠️ 动手前需你确认的 3 处（新发现，各一句话即可）

### (I) ⛔ `Pack options` 的 11 条：用 `Packaging formats` 顶替会**语义错位**

你在 §三 写：「2 段式的 11 条：从剂型页 `.sf-facts-mini` 的 Packaging formats 读」。

实测这两项的**量纲不同**：

| 概念 | 实例值 | 含义 |
|---|---|---|
| `Pack options`（specs 段 2） | `60/90/120 per bottle` | **每件装多少**（数量） |
| `Packaging formats`（新第 4 行） | `Dropper Bottle, Glass Bottle, Plastic Bottle` | **用什么容器**（种类） |

后果：同一列在 21 条里会一半是数量、一半是容器种类；11 条会出现 `Pack options: Dropper Bottle, Glass Bottle, Plastic Bottle` 这种读不通的行。

三个选项：

- **(a) 缺就整行不渲染**（推荐）——11 条参数表显示 4 项，10 条显示 5 项。与主题既有约定一致（`{{FORMULA_META}}` 就是「缺一项则缩短，而不是打印空的 `MOQ`」）。
- **(b) 照你说的顶替**，但把该行标签改成中性的 **`Pack options / formats`**，一个标签吃两种量纲。
- **(c) 从 specs 段 1 拆容器词**（`30ml/50ml dropper bottle` → `30ml/50ml` + `Dropper Bottle`），得到语义接近的「装量 / 容器」，但**值不再是原文**，属于改写数据。

> 我推荐 (a)：语义诚实且实现最简。若你要「5 项永远齐」，选 (b)。

### (II) ⚠️ 第 4 行会让剂型页事实带**从 1 行变 2 行**

`.sf-facts-mini` 实测 CSS 是 `display:flex; flex-wrap:wrap; justify-content:space-between; gap:10px 40px`。

现有三项合计约 1030px（1200px 容器内单行成立）；新增 `Packaging formats` 后，最长一条（soft-chews）达 **124 字符**：

```
Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil + custom formats
```

合计约 **1900px** ⇒ 必然换行，第 4 项落到第二行靠左。剂型页 hero 下方的细线带从 1 行变 2 行。移动端（≤767px 已是 `flex-direction:column`）无影响。

处置选项：**(a) 接受换行**（推荐，实测后再定）／**(b) 值缩短**（如 `Pouch, Bottle, Jar, Blister (6 + custom)`）／**(c) 第 4 项独占整行**（`flex-basis:100%`，视觉更整齐）。

> ⚠️ 这条必须在**浏览器里实测**，不能按估算定稿（F1 血账：渲染接缝实测 ≠ 推演）。

### (III) ⚠️ 「末尾 `+ custom formats`」在 soft-chews 上会出现三重 `+`

该剂型第 6 项本身叫 **`Box + Foil`**，追加后成：

```
…, Blister Pack, Box + Foil + custom formats
```

读起来像 `Box` + `Foil + custom formats`。建议末尾改用 **`…, Blister Pack, Box + Foil, or custom formats`**（其余 7 个剂型无此冲突，逗号版也统一）。

> 你若坚持原写法，我照办；只是提醒这一处歧义。

---

## 一、结构改造

### 1.1 目标 DOM

```
section.sf-fdetail-media（新外层，bg-light，padding 80）
  div.sf-fdetail-media__inner                          ← CSS grid 3fr / 2fr
    section#gallery.sf-gallery.sf-fdetail-media__left  ← 原图库段提升为左栏
      h2.sf-gallery__title   "A Closer Look at {TITLE}" ← 保留
      [sf_formula_gallery]                              ← 4 帧 slide 全在
    aside.sf-fdetail-media__side                        ← 新右栏
      <p class="sf-fdetail-media__intro">  简介
      <dl class="sf-fdetail-media__facts"> 5 项参数表
      <a class="sf-fdetail-media__cta" href="/contact/">Request Sample</a>
```

**不删 DOM**：4 帧 slide、`id="gallery"`、h2 全部保留，只改层级与 class。

> 附实测：`#gallery` 锚点在**全仓无任何引用者**（JS 用 `data-gallery` 选择器，不是 `#gallery`）。仍保留，防未来断链。

### 1.2 块注释写法（`templates/single-sf_formula.html`）

替换现有第 18–25 行（原 `sf-gallery` group）：

```html
<!-- Batch G: media + facts, two columns -->
<!-- wp:group {"tagName":"section","className":"sf-fdetail-media","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section class="wp-block-group sf-fdetail-media has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:group {"className":"sf-fdetail-media__inner","layout":{"type":"default"}} -->
<div class="wp-block-group sf-fdetail-media__inner">
<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery sf-fdetail-media__left","layout":{"type":"default"}} -->
<section id="gallery" class="wp-block-group sf-gallery sf-fdetail-media__left">
<!-- wp:html -->
[sf_formula_gallery]
<!-- /wp:html -->
</section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"aside","className":"sf-fdetail-media__side","layout":{"type":"default"}} -->
<aside class="wp-block-group sf-fdetail-media__side">
<!-- wp:html -->
{{FORMULA_INTRO}}
[sf_formula_factsheet]
<a class="sf-fdetail-media__cta" href="/contact/">Request Sample</a>
<!-- /wp:html -->
</aside>
<!-- /wp:group -->
</div>
<!-- /wp:group -->
</section>
<!-- /wp:group -->
```

**layout 处置（关键）**：

- 外层 `constrained` — 与全站 section 一致，拿到居中 + 限宽 + padding。
- **内层 `__inner` 与左右两栏必须是 `default`**。core 的 constrained 规则会对 `.is-layout-constrained > *` 施加 `max-width: content-size; margin-inline:auto`；若 inner 保持 constrained，两栏会被各自限宽居中，**grid 布局会被打散**。
- 背景色只挂最外层。原 gallery group 的 `backgroundColor:"bg-light"` 一并去掉（否则左栏出现独立色块，两栏读成两个 slab）。
- ⚠️ 三处 layout / 背景 / className 的**实际渲染属性**（`is-layout-flow` / `wp-block-group-is-layout-flow` / class 顺序 / 换行）必须实测，不得推演。

### 1.3 轮播 h2 处理（决策 5）

保留。实测详情页 h2 = 5 个，`Ready to Launch Your Product?` 命中 `toc-nav.js` 的 SKIP 正则 ⇒ **实点 4 个**，本批不改动。

> 注：该 h2 由短代码 `sinofresh_formula_gallery()`（`functions.php:1287`）输出，不在模板里——本批既然保留，`functions.php` 这一处**零改动**。

---

## 二、Packaging 数据源（决策 1）

### 2.1 八剂型选项集（实测提取，全部以 `Custom` 结尾，8/8 齐整）

| 剂型 | 选项（已去 `Custom`） |
|---|---|
| soft-chews | Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil |
| tablets | Plastic Bottle, Jar, Blister Pack, Foil Pouch |
| powders | Jar, Foil Pouch, Stand-up Pouch |
| pastes | Plastic Tube, Metal Tube, Aluminum Tube |
| drops | Dropper Bottle, Glass Bottle, Plastic Bottle |
| liquids | Plastic Bottle, Glass Bottle, Bottle with Cup |
| fish-oil | Plastic Bottle, Glass Bottle, Pump Bottle |
| dental-chews | Foil Pouch, Stand-up Pouch, Box |

来源：各 `templates/page-{form}.html` 内 `<div class="configurator__group" data-group="packaging">` 的 `data-value` 序列。

### 2.2 插入位置与 markup

八个模板的 `.sf-facts-mini`（soft-chews 实测第 30–34 行）改为 4 行，新行插在 `Certifications` 行之后、`</section>` 之前：

```html
<div class="sf-facts-mini__item"><span class="sf-facts-mini__label">Packaging</span> <span class="sf-facts-mini__value" data-label="Packaging formats">Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil + custom formats</span></div>
```

- `data-label="Packaging formats"`（机器名，按你的指定）／可见 label 用 `Packaging`（简洁）。若要与机器名一致，可见 label 也可写 `Packaging formats` —— **一句话确认即可**。
- 值内仅含逗号、空格、字母、`+`，**无引号、无 `<`、无 `&`** ⇒ 放进属性 / 文本均安全（已逐剂型核对）。
- ⚠️ 第 4 行的换行 / 缩进会改变块内空白行数 ⇒ 渲染接缝必须实测（见 §0.1-II）。

### 2.3 `spec_cell` 复用

`sinofresh_formula_spec_cell($form, 'Packaging formats')` **直接可用**，零改动：它先把查找范围截在 `<section class="sf-facts-mini">…</section>` 内，再按 `data-label` 取值——新增行天然落在这个范围内。

> F1 已建立该行，hero meta 只读 `MOQ` / `Lead time` ⇒ 新增第 4 行 **不影响** hero meta。

---

## 三、5 项参数表数据源

### 3.1 逐项定案

| # | 项 | 数据源 | 覆盖 |
|---|---|---|---|
| 1 | Unit size | `sf_formula_specs` → 去掉 shelf life 段、去掉 `per` 段后**剩下的第 1 段** | 21/21 |
| 2 | Pack options | `sf_formula_specs` 中含 `[[:space:]]per[[:space:]]` 的段 | **10/21** ⛔ 见 §0.1-I |
| 3 | Shelf life | `sf_formula_specs` 正则 `(\d+)\s+months?\s+shelf\s+life` | 21/21 |
| 4 | Certifications | `spec_cell($form,'Certifications')` | 21/21（八页同文 `FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC`） |
| 5 | Packaging formats | `spec_cell($form,'Packaging formats')` | 21/21（本批新建） |

### 3.2 新函数 `sinofresh_formula_specs_parts($specs)`

按 **key 正则**取值，不按段位置（位置法会在 11 条上取到 shelf life）：

```
1. $parts = explode(' · ', $specs)
2. shelf = 第一个匹配 /(\d+)\s+months?\s+shelf\s+life/ 的段 → 移出
3. pack  = 剩余中匹配 /[[:space:]]per[[:space:]]/ 的段 → 移出（可为空）
4. unit  = 剩余的第一段
返回 ['unit' => …, 'pack' => …, 'shelf' => …]
```

自检：3 段式 10 条 → unit / pack / shelf 全非空；2 段式 11 条 → pack 为空、其余非空。

### 3.3 新短代码 `[sf_formula_factsheet]`

输出（顺序按你的指定）：

```html
<dl class="sf-fdetail-media__facts">
  <dt class="sf-fdetail-media__term">Unit size</dt><dd class="sf-fdetail-media__value">2g/piece</dd>
  <dt class="sf-fdetail-media__term">Pack options</dt><dd class="sf-fdetail-media__value">60/90/120 per bottle</dd>
  <dt class="sf-fdetail-media__term">Shelf life</dt><dd class="sf-fdetail-media__value">18 months shelf life</dd>
  <dt class="sf-fdetail-media__term">Certifications</dt><dd class="sf-fdetail-media__value">FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC</dd>
  <dt class="sf-fdetail-media__term">Packaging formats</dt><dd class="sf-fdetail-media__value">Aluminum Stand-up Pouch, …</dd>
</dl>
```

- 空值行按 §0.1-I 的定论处理（(a) 不渲染该行 / (b) 顶替 + 中性标签）。
- 用 `<dt>/<dd>`，**不用** `.sf-spec-term` / `.sf-spec-value` 的 `<span>` 对。
  > 依据：`.sf-spec-term` 有两个出处——视觉层 `<dt>/<dd>`（三处）／K6 解析器要找 `<span>` 紧邻（模板 0 处）。用 `<dt>/<dd>` 不会被解析器误抓。

---

## 四、解析陷阱（已实测，写进代码注释）

| 陷阱 | 实测 | 正确写法 |
|---|---|---|
| 裸 `per ` 假匹配 | `per (bottle\|bag\|jar\|tube)` 命中 **12** 条，其中 2 条是 **`dropper bottle`** 的子串 | `[[:space:]]per[[:space:]]` → 真值 **10** 条 |
| 按段位置取字段 | 3 段式 **10** 条 / 2 段式 **11** 条 | 按 key 正则取，与段数无关 |
| `shelf life` 位置 | 2 段式里是第 2 段、3 段式里是第 3 段 | 正则匹配，不按 index |

---

## 五、CSS

### 5.1 两栏

```css
.sf-fdetail-media__inner{
	display:grid;
	grid-template-columns:minmax(0,3fr) minmax(0,2fr);
	gap:48px;
	align-items:start;
}
```

- 移动堆叠：`@media (max-width:768px)` → `grid-template-columns:1fr; gap:32px`（768px 是全站主断点，实测 `style.css` 里出现 45 次）。
- `minmax(0,…)` 必须带：否则长值（124 字符的 Packaging formats）会把 grid 列撑破。

### 5.2 必须处置的既有规则

```css
.sf-fdetail-media__left .sf-gallery__stage{max-width:none;margin-top:0}
```
> 原规则 `.sf-gallery__stage{max-width:680px;margin:30px auto 0}` 是为全宽 section 设计的，进了 3fr 左栏会又窄又居中。

### 5.3 参数表（`<dl>`）

```css
.sf-fdetail-media__facts{display:grid;grid-template-columns:auto 1fr;gap:10px 16px;margin:0}
.sf-fdetail-media__term{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--wp--preset--color--text-secondary);white-space:nowrap}
.sf-fdetail-media__value{margin:0;font-size:14px;line-height:1.5;color:var(--wp--preset--color--text-primary)}
```
（视觉语言沿用 F1 的 `.sf-facts-mini`：11px letterspaced muted label + ink value。）

### 5.4 右栏 CTA

```css
.sf-fdetail-media__cta{
	display:inline-block;padding:12px 24px;border-radius:6px;
	background:var(--wp--preset--color--primary);color:var(--wp--preset--color--card-white);
	font-size:15px;font-weight:600;text-decoration:none;
}
.sf-fdetail-media__cta:hover{background:var(--wp--preset--color--brand-green);color:var(--wp--preset--color--text-primary)}
```

- 「主色」按 token 取 **`primary` = `#1B4D3E`**（深森林绿）+ 白字。
- 另两个候选：`brand-green` `#5AB735`（hero 的 `Reference this formula` 实心按钮用的）／`cta` `#B54E0F`（页尾 `Request a Quote` 用的橙）。若要「转化按钮」视觉统一，改 `cta`。**一句话确认即可。**
- 附实测：页尾已有两个转化按钮跳 `/contact/`（`Request a Quote`）与 `/contact/#quote`（`Get a Quote`）。新按钮文案 `Request Sample`、落点 `/contact/` ⇒ 同页会同时出现 `Request a Quote` 与 `Request Sample`，措辞不同、落点相同。语义可区分，视为可接受。

### 5.5 版本

**2.10.53 → 2.10.54**，两处同步：`functions.php:26`（enqueue）↔ `style.css:5`（`Version:`）。

---

## 六、简介模板（决策 4）

### 6.1 模板（56 词，4 变量）

```
{product} is a standard {form} formula from the SINO FRESH OEM/ODM range for private-label pet supplements. Produced in a GMP-certified facility in Linyi, China and shipped with full documentation, it is ready for your own brand. Minimum order quantity: {moq}. Lead time: {lead_time}.
```

实参渲染（soft-chews）：

> Joint Support Soft Chews is a standard Soft Chews formula from the SINO FRESH OEM/ODM range for private-label pet supplements. Produced in a GMP-certified facility in Linyi, China and shipped with full documentation, it is ready for your own brand. Minimum order quantity: from 500–1,000 units. Lead time: Typically 7–15 working days after packaging is ready.

### 6.2 实现

- 新函数 `sinofresh_formula_intro()`：
  1. 读 `sf_formula_intro` meta —— **有值直接返回**（覆写位）；
  2. 否则拼模板：`{product}` = `get_the_title()`，`{form}` = `sf_formula_form` 首 term 的 label，`{moq}` / `{lead_time}` = `spec_cell()`。
- **首句措辞复用 `functions.php:3422`** 那句（同一措辞来源，避免两处漂移）；但**不复用同一函数**——详情页 Product schema 的生成路径**保持零改动**，否则 JSON-LD 会变（§7 要求 0 变化）。
- `{moq}` 值**自带 `from`**（`from 500–1,000 units`）⇒ 模板用冒号槽位 `Minimum order quantity: {moq}.`，避免 `a minimum order of from …` 语法错。
- 缺失降级：`{moq}` 空 → 整句 `Minimum order quantity: …` 不输出；`{lead_time}` 同理（沿用 `{{FORMULA_META}}` 的「缺失则缩短」约定）。
- 占位符 `{{FORMULA_INTRO}}`：在 `sinofresh_template_placeholders()` 的 `$map` 里映射为 `<p class="sf-fdetail-media__intro">' . esc_html($intro) . '</p>`；`$intro` 为空时输出空串（不留空 `<p>`）。
  > 注意与 `{{FORMULA_META}}` 的差别——那个只替换纯文本，这个要带 `<p>` 外壳，所以是「已转义的 HTML」而非「已转义的文本」。

### 6.3 zh 侧

维持英文（决策 7）。实测依据：`/zh/formulas/{slug}/` 的 h1 / use / hero meta / schema-desc 与 en 侧**逐字相同**——PHP 拼装串不经 TranslatePress 翻译。简介走 PHP ⇒ zh 也是英文，**与现状一致**，非本批引入的退化。

---

## 七、回归门（`tools/b2d_g_confine.py`）

### 7.1 集合

**58 页** = 42 详情页（21 en + 21 zh）＋ 16 剂型页（8 en + 8 zh）。

21 条 slug：

```
bladder-support-powder     calcium-phosphorus-tablets  calming-soft-chews
digestive-soft-chews       ear-care-drops              hairball-remedy-paste
joint-support-soft-chews   joint-support-tablets       liquid-joint-support
liquid-skin-coat           multivitamin-tablets        natural-cleaning-dental-sticks
nutrition-paste            oral-care-dental-sticks     plaque-control-dental-chews
probiotic-powder           pumpkin-digestive-powder    pure-fish-oil-blend
skin-coat-soft-chews       urinary-care-drops          wild-alaskan-salmon-oil
```

8 剂型：`soft-chews tablets powders pastes drops liquids fish-oil dental-chews`

### 7.2 限定证明 —— **混合批次，两类页面两种方向**

⛔ F1 的血账：**方向写反不会被计数发现**。本批两类页面的方向**不同**，必须各自断言：

**A. 剂型页 16 页 = 插入批方向**（候选侧多一行）
> 逆操作：从候选页的 `.sf-facts-mini` 删掉 `data-label="Packaging formats"` 那一行 ⇒ 必须**逐字节等于基线**。

**B. 详情页 42 页 = 结构重组批方向**（层级变化，既非纯插入也非纯删除）
> 逆操作 3 步 ⇒ 必须**逐字节等于基线**：
> 1. 删掉 `aside.sf-fdetail-media__side`（右栏整块，含简介 / 参数表 / CTA）
> 2. 把 `section#gallery.sf-gallery.sf-fdetail-media__left` 从 grid 内**提升为顶层**
> 3. 恢复其 `className`（去 `sf-fdetail-media__left`）与背景（回 `has-bg-light-background-color has-background`），layout 还原为 `constrained`

**负对照**：`--new-*` 指向基线侧 ⇒ 三类断言必须全部 FAIL，RC=1。

### 7.3 六门

| 门 | 内容 | 预期 |
|---|---|---|
| 0 | 抓取确实来自预检目录（`sinofresh-theme-preflight`） | 必须断言，否则全绿无意义 |
| 1 | 资源清单：仅 `style.css` 版本变，75 页无资源增减（SET 变化 ≠ 版本变化） | PASS |
| 2 | 掩码比较，**DIFF 集合精确等于 58 页**（多一页少一页都 FAIL） | 58/58 |
| 3 | 页级限定证明（§7.2 两种方向 + 负对照） | A 16/16、B 42/42 还原 |
| 4 | 源码级重建：撤销声明编辑后等于批前源码（逆操作在此**重算**，不导入 apply 工具；两个实现必须一致） | PASS |
| 5 | JSON-LD deep-equal，75 页 | **0 变化**（本批不动 schema 生成路径） |

### 7.4 其余闭环

- `sf_masked_cmp.py` 先跑 **`--aa` 自检**（同 URL 抓两次必须 SAME）。
- **点轨数量：浏览器实测**（详情页预期 4、剂型页预期 6），不推演。
- **渲染接缝实测**：外层 / 内层 group 的 class 顺序、`is-layout-*`、换行数、`.sf-facts-mini` 加行后的空白行——全部先量后写。
- **先合成候选跑通门，再上真数据**（F1 用这招逮到 3 个门 bug）。
- 身份链（三方 + 两方，691 文件）+ 仓库 md5（`sf_repo_md5.py --exclude <报告>`，报告最后生成）。
- 日志审计（`b2d_s5_logaudit.py`，显式窗口 + `--allow`；**2D-E 负对照那条 fatal 仍要带同一条 `--allow`**）。
- 上线八步：`fetch` → `install <40 位 SHA>` → 带 `X-SF-Preflight: 1` 抓 58+17 页 → 全套门 → `pull --ff-only` → 上线后 `sf_masked_cmp <候选> <live>` 逐页 identical → 拆预检 →（日志 / 身份链 / md5）→ 文档。

---

## 八、工作约定（逐条落实）

| 约定 | 本批落实 |
|---|---|
| 先出方案，停下等确认 | ✅ 本文件；等 §0.1 三处确认 |
| 不删 DOM 内容 | ✅ 4 帧 slide / `id="gallery"` / h2 全保留；只改层级与 class |
| 自闭合区块用 ` /-->` | ✅ 模板里 `wp:template-part`、`wp:html` 等自闭合一律 ` /-->` |
| dev 访问带凭据 | ✅ 一切 curl / 浏览器 / 预检抓取带 `-u 'sfdev:…'` |
| 先过门再上线 | ✅ §7.4 八步；线上从不服务未过门的字节 |

---

## 九、实施步骤（确认后执行）

| Step | 内容 | 产出 |
|---|---|---|
| 0 | 建**合成候选**（假数据）→ 门 PASS + 负对照 FAIL | 逮门自己的 bug |
| 1 | 8 剂型模板增第 4 行 + 自证（行数、data-label、值与配置器一致） | `b2d_g_apply.py --part facts` |
| 2 | `single-sf_formula.html` 改写两栏结构 + 自证 | `b2d_g_apply.py --part media` |
| 3 | `functions.php`：`specs_parts()` / `intro()` / `factsheet` 短代码 / `{{FORMULA_INTRO}}` 映射 / 版本 | 同上 |
| 4 | `style.css`：`.sf-fdetail-media` 命名空间 + 版本 | 同上 |
| 5 | 真数据候选 → 六门 + 负对照 | `b2d_g_confine.py` |
| 6 | 浏览器取证（几何 + 点轨 + 截图，含 768px 堆叠与第 4 行换行实测） | `b2d_g_evidence.py` |
| 7 | 预检上线八步闭环 | 上线报告 |

---

## 附录：扫查留痕（可复跑）

```bash
# 配置器 packaging 选项集（8 剂型）
python3 -c "import re;h=open('templates/page-soft-chews.html').read();print(re.findall(r'data-value=\"([^\"]+)\"',re.search(r'data-group=\"packaging\".*?\n    </div>',h,re.S).group(0)))"

# 段数分布与 per 真值
SELECT ... REGEXP '[[:space:]]per[[:space:]]'   -- 10
SELECT ... REGEXP 'per (bottle|bag|jar|tube)'   -- 12（dropper bottle 污染 +2）

# 详情页 h2（点轨输入）
curl -sk -u 'sfdev:…' https://dev.zxpet.com/formulas/joint-support-soft-chews/ | grep -o '<h2[^>]*>[^<]*</h2>'
```

> ⛔ macOS 坑 REMINDER：本场再次踩到 `grep "a\|b"` 静默返回空 ⇒ **一律 `grep -E`**。
