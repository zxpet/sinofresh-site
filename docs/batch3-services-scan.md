# 批 3 扫描报告 — 待办21「Services 4 详情页」

> 扫描日期：2026-09-23　｜　扫描范围：**只读**（curl / grep / DB SELECT），**未改一行代码、未写一个字节数据**
> 对应指令：批 3 ＝ 待办21。用户约束：**先扫描 → 报告 → 停下 → 等确认再实施**。
> 结论一句话：**`/services/` 目前是一张单页，4 张「合作模式」卡片存在但零链接，4 个候选子路由全部 404，数据库无任何子页。** 待办21 的原文不在仓库里 ⇒ **触发停机条件③（需要用户裁决）**，本报告停在此处。

---

## 〇 扫描结论摘要

| 项 | 实测结果 |
|---|---|
| `/services/` 是否单页 | ✅ 单页（`templates/page-services.html`，368 行） |
| 4 张合作模式卡片是否存在 | ✅ 存在（OEM / ODM / Contract Manufacturing / Private Label） |
| 4 张卡片是否有链接 | ❌ **0 个 `<a>`**（本地模板与 dev 线上字节**两边都数过**，都是 0） |
| 4 个子路由是否存在 | ❌ `/services/oem/`、`/services/odm/`、`/services/contract-manufacturing/`、`/services/private-label/` **全 404** |
| 数据库是否有子页 | ❌ `services` 只有 1 行（ID 29，`post_parent=0`），无子页 |
| 导航是否有下拉 | ❌ `OEM/ODM → /services/` 是**单条链接**，无 `navigation-submenu`（`Products` 才是下拉，9 个子项） |
| 是否有 DB 模板遮蔽 | ❌ 0 条生效（9 条 `wp_template` 全部 `status=trash`）⇒ 主题模板文件说了算 |
| 待办21 原文是否可查 | ❌ 仓库内**只有两处对它的引用**（`docs/batch2d-stepH8a.md` L4、`docs/batch2d-stepH8b.md` L354），**无原文**；历史会话检索亦未取回 |

---

## 一 现状实测（全部只读）

### 1.1 `/services/` 的带序与内容

按 `templates/page-services.html` 与 dev 线上字节（150,142 bytes）逐带核对：

| # | 带 | 内容 |
|---|---|---|
| 1 | hero | 面包屑 `sf-breadcrumb--d2`（Home / **OEM/ODM Services**）＋ `h1`＝`OEM/ODM Pet Supplement Manufacturing Services` ＋ 副标（8 剂型／MOQ／FDA·cGMP·ISO 9001·FSSC 22000·HACCP·BRC） |
| 2 | `sf-oem` | h2 `OEM or ODM — Choose Your Path` ＋ **4 张 `sf-card sf-card--roomy`** |
| 3 | Key Facts | `table.sf-keyfacts` 5 行：MOQ / Sampling / Lead Time / Payment / Trade Terms |
| 4 | What We Handle | `sf-panel--3` 三栏 × 5 条：R&D & Formulation / Compliance & Quality / Export Documentation |
| 5 | How We Work | 5 步（01 Inquiry → 05 Shipping & After-Sales） |
| 6 | FAQ | 3 条 `details.sf-faq__item` |
| 7 | Request a Sample | 左文右表：`gravityforms/form` **formId 3** |

**4 张卡片的实际标题与 2 条要点：**

| 卡片 | h3 | 要点 1 | 要点 2 |
|---|---|---|---|
| 1 | `OEM — You Bring the Formula` | Your formula, your specifications | We manufacture and deliver |
| 2 | `ODM — We Develop From Your Idea` | Concept to finished product | Formula development + palatability testing |
| 3 | `Contract Manufacturing — You Own the IP` | Your IP, protected by NDA | Scaled mass production |
| 4 | `Private Label — Pick From Our Proven Formulas` | Ready-to-market recipes | Low MOQ for new brands |

> 取证命令（两边都数）：
> - 本地模板：`page-services.html` 的 `sf-oem` 段落内 `<a>` 计数 = **0**
> - dev 线上：`curl -H 'X-SF-Preflight: 1'` 取 `/services/`，在 `sf-oem`…`Key Facts` 区间内 `<a>` 计数 = **0**
> ⇒ 不是「有链接被 CSS 藏了」，是**根本没有链接**。

### 1.2 路由状态码（dev，带 Basic Auth ＋ `X-SF-Preflight: 1`）

```
200  /services/
200  /cooperation/
404  /services/oem/
404  /services/odm/
404  /services/contract-manufacturing/
404  /services/private-label/
404  /services-oem/
404  /oem/
200  /zh/services/
```

`/zh/services/` 是 TranslatePress 孪生，渲染**同一英文 h1**。

### 1.3 导航与数据库

```
wp_navigation ID 16（Main Menu）:
  Products            ← wp:navigation-submenu（唯一的下拉，9 个子项）
  OEM/ODM  → /services/   ← 单条 wp:navigation-link，无子项
  Quality / About / Factory Tour / Blog / Contact

wp_posts（slug 命中）:
  29  services     page  publish  post_parent=0
  30  cooperation  page  publish  post_parent=0
  （services-oem / services-odm / contract-manufacturing / private-label / oem / odm 全部无记录）

生效的模板遮蔽：0 条
  （wp_template/wp_template_part 共 9 条，posts_status 全为 trash ⇒ 不生效）
```

### 1.4 与相邻页 `/cooperation/` 的关系（**重要，避免做重**）

`templates/page-cooperation.html`（269 行，`/cooperation/` 200）的内容是**另一个维度**：

- h1 `Cooperation Models` ＋ **Who We Work With**：6 类**买家**（Brand Owners / Cross-Border E-Commerce Sellers / Pet Store Chains & Distributors / Veterinary Clinics / Trading Companies / Domestic E-Commerce Sellers），每类带 MOQ·取样·交期·支持
- Compare Cooperation Models → FAQ（5 条）→ Contact Us CTA

⚠️ **两页的「4」不是同一组东西**：`/services/` 的 4 张是**合作模式**（OEM / ODM / Contract / Private Label，按「谁提供配方」分），`/cooperation/` 的 6 张是**买家类型**（按「你是谁」分）。维度不同、内容不重复，但导航标签都指向合作相关，**有信息架构上的混淆风险**，实施时需明确「4 详情页」挂在哪一张下面。

---

## 二 代码侧机制（决定实施形态）

### 2.1 关键约束：块主题模板不会自动造路由

块主题的模板层级是 `page-{slug}.html` → `page-{id}.html` → `page.html`。**它只在「存在对应 WP 页面」时命中。**
⇒ 光新建 `page-services-oem.html` 等 4 个文件，`/services/oem/` **仍然是 404**。必须有「路由 → 模板」的绑定，而绑定方式只有下面三条路。

### 2.2 三种落地形态（**待用户裁决**）

| | 方案 A：纯代码虚拟路由 | 方案 B：建 4 个 WP 子页 | 方案 C：不新增路由，就地扩写 |
|---|---|---|---|
| 做法 | `functions.php` 加 `add_rewrite_rule('^services/(oem\|odm\|contract-manufacturing\|private-label)/?$', …)` ＋ `template_include`／`get_block_template` 指向 `page-services-{x}.html` | 在 `/services/`（ID 29）下建 4 个 page（`post_parent=29`），模板 `page-services-oem.html` 等**自动命中** | 4 张卡改成锚点 `/services/#oem`…，在 services 页内追加 4 个详情区块 |
| 写 DB | **零** | **要写**（4 行 post ＋ 可能的 TP 翻译条目） | **零** |
| SEO | 4 个可独立收录的 URL，但需手写 canonical / `body_class` / 面包屑 | 4 个原生 URL，WP 自动给 canonical、`body_class`、`page-{id}` 支持 | 单页更长，只有 1 个可收录 URL |
| TP 多语言 | 要自己处理 `/zh/services/oem/` 前缀与语言切换 | TP 自动接管（新页会自动进翻译队列） | 无影响 |
| 风险 | 与 TP 路由过滤、`wp_rewrite` flush 时机耦合；需自证 `/zh/` 与尾斜杠一致 | 违反本指令「不碰数据」约束 ⇒ **需单独授权**；新建页默认 `publish` 会立刻公开 | 页面从 368 行涨到 ~800 行，首屏后内容很长（已有 On-this-page 圆点轨可用） |
| 与既有代码耦合 | 中（需改 `is_page()` 白名单读法） | 低（沿用现有 8 剂型页的成熟模式） | 最低（只改 1 个模板 ＋ 可能 1 段 CSS） |

> 参考既有同类先例：
> - 「卡片整体当链接」已有写法 —— `front-page.html` L1002：`<a class="sf-card sf-card--quote sf-story sf-story--link" href="/case-study-…/">`
> - 「子页 + 面包屑三层」已有写法 —— `page-soft-chews.html` 用 `sf-breadcrumb--d3`（Home / Products / Soft Chews）

### 2.3 若走 A 或 B，必须同步处理的 5 处既有机制

1. **`functions.php` L56 — toc-nav 白名单**
   ```php
   if (is_front_page() || is_page(array('quality','about','services','factory-tour','soft-chews',…)) || is_singular('post')) {
       wp_enqueue_script('sinofresh-toc-nav', … '/assets/js/toc-nav.js', array(), '2.0.0', true);
   }
   ```
   新子页**不加进这个数组**，「本页导航」圆点轨 JS 不加载（页面会静默少了那条轨）。

2. **`functions.php` L6732–6751 — Service schema 硬绑单页**
   ```php
   if (!is_page('services')) { return; }
   … 'name' => 'Pet Supplement OEM/ODM Manufacturing', 'areaServed' => ['US','EU','JP','KR','BR','MX'] …
   ```
   4 个子页**现在完全不会被覆盖**。三选一：① 复制成 4 条独立 Service；② 改成 `is_page(array('services','services-oem',…))` 共用一条；③ 不加（子页无结构化数据）。**这是 SEO 决策，需用户裁决。**

3. **面包屑**：子页应升为 `sf-breadcrumb--d3`（Home / OEM/ODM Services / <子页名>），参照 `page-soft-chews.html` 的 d3 三段式。

4. **`tools/b2d_s3_paths.txt`（**75 行**）＝ 门的页集基线**
   新增 4 条路由 ⇒ 页集 75 → 79。门的 A/A 与主证都按这份清单逐页比字节；**只加页面、不改清单**会让 A/A 变红而主证仍绿（静默缩到交集）。⇒ 必须扩清单，并把「新模板落库的提交」与「新基线提交」时序对齐。

5. **导航**：`wp_navigation`（ID 16）是**数据库内容**。要给 `OEM/ODM` 加下拉（4 子项）＝ 写 DB。若走方案 C 则不必动导航。

### 2.4 不变量（实施时不得破）

- `page-services.html` 现有 7 个带、`sf-keyfacts` 5 行、`sf-panel--3` 3 栏 × 5 条、How We Work 5 步、FAQ 3 条、GF **formId 3** —— 都是既有门/E2E 已在盯的字节。
- 站点**导航零当前态**是已知缺口（45 页全查无 `current-menu-item`）⇒ 新子页也不要指望导航自己高亮。
- 全站全屏层 ≥ 9998；新页面若要加任何覆盖层须先扫 z-index。
- 一个值可多载体 ⇒ 判据写**不变式**，不要按类名猜载体。

---

## 三 需要用户裁决的问题（4 条）

| # | 问题 | 为什么必须由用户定 |
|---|---|---|
| ① | **待办21 的原文**：这「4 个详情页」分别是什么？路径命名（`/services/oem/` 还是别的）？是否要进 `/services/` 的卡片链接、进导航下拉？ | 仓库里**没有原文**，只有两处引用。Agent 无法从代码或数据反推出用户当时的要求。 |
| ② | **落地形态选 A / B / C**（见 2.2） | B 需要写 DB，与「不碰数据」约束冲突 ⇒ 需授权；A 与 C 各有 SEO / 页长代价。 |
| ③ | **是否把 4 条新路由纳入 `tools/b2d_s3_paths.txt`**（75 → 79） | 这会改门的页集基线，属于「改判据」级别，需用户点头。 |
| ④ | **Service schema（2.3-2）与 toc-nav 白名单（2.3-1）如何处理** | 前者是 SEO 决策（1 条 vs 4 条 vs 不加），后者决定子页有没有圆点轨。 |

---

## 四 已排除的可能性（省掉重复排查）

- ❌ 「其实已有子路由，只是没链接」→ 6 个候选路径实测**全 404**
- ❌ 「4 张卡本来有链接、被 CSS 藏了」→ 本地模板与线上字节**两处 `<a>` 计数都是 0**
- ❌ 「英文页是 TP 没翻好」→ `/zh/services/` 200 且**渲染同一英文 h1**，是孪生不是缺失
- ❌ 「有 DB 模板遮蔽改了也没用」→ 生效遮蔽 **0 条**（9 条 `wp_template` 全在 trash）
- ❌ 「导航里有下拉只是没渲染」→ `wp_navigation` 内容里 `OEM/ODM` 是**单条 `navigation-link`**，`Products` 才是唯一的 `navigation-submenu`

---

## 五 本报告明确**没有**做的事（遵守指令约束）

- 未改任何模板 / `functions.php` / `style.css` / JS
- 未创建任何 WP 页面，未写任何 post meta / option
- 未 pull 到 dev，未碰生产站
- 未跑门（没有候选代码可比 ⇒ 跑门无意义）
- 未新增抓页清单条目（等裁决③）
