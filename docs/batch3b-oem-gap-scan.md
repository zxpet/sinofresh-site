# 批 3b 扫描报告 — OEM/ODM 页改造缺口（只读）

> 扫描日期：2026-09-24　｜　范围：**只读**（curl / grep / 读模板与文档），**未改一行代码、未写一个字节数据、未碰 DB、未碰生产站**
> 触发：用户指出批 3（H8c）只做了「4 个子页 + 卡片可点」，另有**两项此前提出但未排进批 3 的要求**。
> 结论一句话：**两项都没做** —— 导航仍叫 `OEM/ODM`（`Services` / `合作模式` 这两个标签在站点上根本不存在）；**首页 4 个框 0 个链接**（模板与线上两边都数过）。总览页 `/services/` 的 7 个带里，**「定制能力」只有半带、「工厂能力」完全缺**。

---

## 〇 结论摘要

| # | 用户问的 | 实测答案 |
|---|---|---|
| 1 | 导航当前显示什么 | **`OEM/ODM` → `/services/`**（单条链接、无下拉）；**未改名**；中文站同一英文标签 |
| 2 | 首页 4 个框是否有链接 | ❌ **0 个**（4 张卡、4 个 `h3` 全是裸文本、`sf-card__title-link` 计数 0、区块内按钮 0） |
| 3 | 总览页 `/services/` 结构 | **7 带**：Hero / 模式对比(4 卡) / Key Facts / What We Handle / How We Work / FAQ / CTA —— 比「只有 4 卡 + Key Facts + What We Handle + How We Work」多 Hero/FAQ/CTA，比期望的 8 带少「定制能力(独立)」与「工厂能力」 |
| 4 | 哪些做了 / 没做 | 见 §四 |
| 5 | 建议补做方案 | 见 §五（分三组 A/B/C，均待裁决） |

---

## 一 导航当前显示什么

### 1.1 实测（dev，不带预检头，Basic Auth 后抓渲染后的 HTML）

`wp_navigation` 是**数据库内容**（`parts/header.html` L31 只有 `<!-- wp:navigation {"ref":16} -->`），
所以主题文件里查不到菜单文案 —— 必须读渲染结果。

```
dev.zxpet.com 顶部导航（16 项）：
  Products  → /products/        ← 唯一的下拉（9 子项：Tablets…Dental Chews + All Formulas）
  OEM/ODM   → /services/        ← ★ 单条 navigation-link，无子项
  Quality / About / Factory Tour / Blog / Contact
```

中文站 `dev.zxpet.com/zh/` 渲染的是**同一份英文标签**：

```
  OEM/ODM   → /zh/services/
```

⇒ **`Services` 与 `合作模式` 这两个标签在站点上都不存在。**

### 1.2 「改了吗？」——没有，且仓库里没有改名代码

| 取证 | 结果 |
|---|---|
| 线上渲染的导航项 11 | 文案 `OEM/ODM` |
| `functions.php` 中 `wp_nav_menu` / `wp_get_nav_menu` / `nav_menu_item` / `wp_navigation` 过滤钩子 | **0 命中** |
| `functions.php` 中 `'Services'` / `"Services"` / `合作模式` | **0 命中** |
| `parts/header.html`（40 行） | 无菜单项文案，只有 `ref:16` |
| 原始开发文档 `sinofresh-theme/docs/官网开发文档-全文.md` L466 | 写的也是 **「OEM/ODM Services」** |

⇒ 改名从未发生，且**需求原文不在仓库里**（与批 3 扫描的结论一致：待办类原话只在历史会话中，仓库内无原文）。

### 1.3 前置依赖（关于「中文＝合作模式」）

`/zh/` 的内容层**零翻译**，实测：

```
/zh/           <title> sinofresh              h1 = Your Private Label Pet Supplement Partner in China
/zh/services/  <title> OEM/ODM Services – …   h1 = OEM/ODM Pet Supplement Manufacturing Services
               ↑ 与英文站逐字相同
```

`/zh/` 页面上仅有的 14 个中文串，全部是 TranslatePress 自身的界面词与语言切换器：
`评论 / 打开菜单 / 关闭菜单 / 子菜单 / 网站语言选择器 / 简体中文 / 切换语言 / 可用语言`（另有一条是主题里的 `<!-- TODO -->` 注释被译）。

⇒ 中文站当前是**带语言切换器的英文镜像**。要让导航在 zh 显示 `合作模式`，**必须先在 TP 里有 `OEM/ODM → 合作模式` 这条翻译条目**；
只改数据库里的菜单 label 只会让两个语言都变（或都不变）——这是**前置依赖，不是同一步能做完的事**。

### 1.4 顺带发现：菜单与页脚都没有二级入口

| 检查 | 结果 |
|---|---|
| 页脚 4 栏（`parts/footer.html`）指向 `/services/` 的链接 | **0** |
| 页脚 4 栏指向 4 个子页的链接 | **0** |
| 导航里 4 个子页的入口 | **0**（OEM/ODM 是单链接，无下拉） |
| `/cooperation/`（Cooperation Models 页，200）在导航/页脚 | **0**（孤页） |

⇒ 全站指向 `/services/` 的入链**只有顶部导航那 1 条**；4 个新子页的入链**只有 `/services/` 页内那 4 条**。

---

## 二 首页 4 个框是否有链接

### 2.1 区块定位

`sinofresh-theme/templates/front-page.html` **L544–672**：

```
<section class="wp-block-group sf-section sf-section--large sf-oem has-card-white-background-color has-background">
  <p class="sf-eyebrow">Engagement types</p>
  <h2>OEM &amp; ODM Services</h2>
  <p>You bring the formula or the idea. We handle the rest.</p>
  <div class="wp-block-columns are-vertically-aligned-stretch">
    4 × <div class="wp-block-group sf-card sf-card--roomy">   ← OEM / ODM / Contract Manufacturing / Private Label
```

### 2.2 链接数 —— 两边都数过，都是 0

| 判据 | 模板源码 | dev 线上渲染 |
|---|---|---|
| 区块内 `<a>` 数量 | **0** | **0** |
| 4 个 `h3` 内含 `<a>` | 全部 `False` | 全部 `False` |
| `sf-card__title-link` 计数 | **0** | **0** |
| 区块内 `wp-block-button`（区块级 CTA） | 0 | **0** |
| 卡片要点条数 | 每卡 5 条 `✓` | 4 卡 × 5 条 |

线上实测输出：

```
sf-oem 区块 4852 bytes
区块内链接数: 0
卡片数(sf-card--roomy): 4
title-link 数: 0
h3 全文:  [OEM — You Bring the Formula] 含<a>: False
          [ODM — We Develop From Your Idea] 含<a>: False
          [Contract Manufacturing] 含<a>: False
          [Private Label] 含<a>: False
```

**结论：没做，且不是「被 CSS 藏了」—— 是没有链接。**
（首页全页只有 **1** 个 `/services/` 链接，来自**顶部导航**本身，正文 0 个。）

### 2.3 机制是现成的 —— 只是这 4 张没用

同页的博客卡（`front-page.html` L1244 / L1273 / L1302）写法是：

```html
<h3 class="wp-block-heading">
  <a href="/blog/" class="sf-card__title-link">How to Choose a Pet Supplement Manufacturer…</a>
</h3>
```

而 H8c 刚在 `/services/` 的 4 张卡上用的就是**同一个类**：

```html
<h3 class="wp-block-heading"><a class="sf-card__title-link" href="/services/oem/">OEM — You Bring the Formula</a></h3>
```

⇒ 首页这 4 张要变成「整块可点」，**只需把 h3 包一层 `<a>`**，零 CSS、零 JS（`::after{inset:0}` 版已存在）。

### 2.4 命名差异（改的时候注意）

| | 首页 4 卡 | `/services/` 4 卡 |
|---|---|---|
| 卡 3 | `Contract Manufacturing` | `Contract Manufacturing — You Own the IP` |
| 卡 4 | `Private Label` | `Private Label — Pick From Our Proven Formulas` |
| 卡 1/2 | 与 /services/ 相同（OEM/ODM 带长破折号副题） | 同 |

⇒ 首页是**短名**，`/services/` 是**长名**（同一模式在两页不同文案）。是否统一，是文案决策。

### 2.5 这批卡的来历（不是「从来没做过」）

`tools/oem_patch.py`（129 行）是**「2 张卡 → 4 张卡」**的补丁，同时改了 `front-page.html` 与 `page-services.html`，
文档注释写明「老卡补首页同款 ✓ 明细，四卡文案统一」。
⇒ **造卡做了，加链接没做** —— 这两件事在当时的补丁里是分开的。

---

## 三 总览页 `/services/` 当前模块结构

`templates/page-services.html` = **368 行**（与用户所述一致），渲染后 `<main>` 内 **6 个 h2**：

| # | 期望的带 | 现状 | 证据 |
|---|---|---|---|
| 1 | Hero | ✅ | `section.sf-hero-inner` + 面包屑 `sf-breadcrumb--d2`（Home / **OEM/ODM Services**）+ h1 `OEM/ODM Pet Supplement Manufacturing Services` + 副标（8 剂型／FDA·cGMP·ISO 9001·FSSC 22000·HACCP·BRC） |
| 2 | 模式对比 | ✅ | h2 `OEM or ODM — Choose Your Path` + 4 张 `sf-card sf-card--roomy`（H8c 已加整块可点 + `/services/{x}/`） |
| 3 | Key Facts | ✅ | h2 `Key Facts: MOQ, Lead Time, Payment & Trade Terms` + `table.sf-keyfacts` **5 行**（MOQ / Sampling / Lead Time / Payment / Trade Terms） |
| 4 | 通用流程 | ✅ | h2 `How We Work — From Inquiry to Delivery in 5 Steps` + 5 栏（01 Inquiry → 05 Shipping & After-Sales） |
| 5 | **定制能力** | ⚠️ **只有半带** | 仅作为「What We Handle」第 1 栏 `R&D & Formulation` 存在（5 条：Custom formula development / Custom active ingredient levels / Palatability testing / Stability testing / Packaging compatibility testing）。**无独立带、无图、无链去 `/quality/` 或 `/services/odm/`** |
| 6 | **工厂能力** | ❌ **完全缺** | `/services/` 上零内容。相关能力散在他页：`/factory-tour/`（Built to Pharmaceutical Standards / What You Can See During the Tour）、`/quality/`（In-House QC Laboratory / Quality Control at Every Step / Full Traceability）、`/about/`（Inside Our Factory） |
| 7 | FAQ | ✅ | h2 `Frequently Asked Questions` + **3** 条 `details.sf-faq__item` |
| 8 | CTA | ✅ | h2 `Request a Sample`：左文右表（`wp:gravityforms/form` **formId 3**） |

> **精确回答用户那句二选一**：既不是「只有 4 张卡 + Key Facts + What We Handle + How We Work」（还有 Hero / FAQ / CTA），
> 也不是完整的 8 带（缺独立「定制能力」与「工厂能力」）。

### 3.1 相邻页已有的结构（避免建议时做重）

| 页 | 现有 h2 |
|---|---|
| `/factory-tour/` | Built to Pharmaceutical Standards · Tour Options · What You Can See During the Tour · What to Prepare · Request a Factory Tour · FAQ |
| `/quality/` | Certifications & Registrations · In-House QC Laboratory · Quality Control at Every Step · Certificate of Analysis · Palatability Testing · Full Traceability … · FAQ · 两个 CTA |
| `/about/` | Who We Are · Our Journey · Our Core Values · Our Team · **Inside Our Factory** · Ready to Start? |
| `/cooperation/` | Who We Work With（**6 类买家**）· Compare Cooperation Models · FAQ(5) · Let's Discuss Your Project |

⚠️ `工厂能力` **已有归属页** ⇒ 建议 `/services/` 只做「摘要 + 去处」，**不要搬运内容**（会造成重复内容页）。

### 3.2 圆点轨（加带的连带影响）

`/services/` 载 `assets/js/toc-nav.js`（实测页面引用为真）。轨的生成规则（`toc-nav.js` L180–183）：

```js
var h2s = collectH2s(main, SKIP);   // main 下所有「可见、有文本」的 h2
if (h2s.length < 3) return;         // ≥3 才出轨
```

`/services/` 的 SKIP 列表只针对首页文案 ⇒ **现在 6 个点**；加 2 个带 ⇒ **8 个点**。

### 3.3 改动的影响半径（哪些门/E2E 会红）

| 若改动 | 会碰到 |
|---|---|
| `/services/` 的 h2 集合 | `tools/b2d_h8c_live_check.py` L76 `OVERVIEW_H2`（**6 条标题全文清单**，逐字相等）＋ 该页在主证/门的**逐页字节比对** |
| 首页区块字节 | 首页在 `tools/b2d_s3_paths.txt`（75 页基线）内 ⇒ 逐页字节比对；另有 `tools/b2d_s3_zh_paths.txt`（31 zh 页） |
| 导航 label（DB 写入） | 导航出现在**每一页** ⇒ 全站渲染字节都变。门的两侧（live vs 预检）同时面对同一 DB，**相对比对不受影响**；但任何**存下来的绝对基线/计数**需重取 |
| Service schema 名称 `Pet Supplement OEM/ODM Manufacturing` | `tools/b2d_h5_gate.py` / `b2d_h5_e2e.py` / `b2d_h5_unit.py`（各 1 处）＋ `functions.php` L6732–6751 硬绑 `is_page('services')` |
| 剂型页规格表行 `OEM / ODM` | `tools/b2d_h7_gate.py`（8 处，`('>OEM / ODM<', 42)`）—— 与本议题**无关**，别误伤 |

---

## 四 哪些做了 / 哪些没做

### 4.1 已做（批 3 ＝ H8c，已上线 dev `2.10.76`）

| 项 | 状态 | 取证 |
|---|---|---|
| 4 个合作模式子页 | ✅ | `/services/oem/`、`/services/odm/`、`/services/contract-manufacturing/`、`/services/private-label/` **全 200**（DB post 217–220，`post_parent=29`，content 空 ⇒ 模板渲染） |
| 子页面包屑升三层 | ✅ | `/services/oem/`：`Home` / `OEM/ODM Services` / `OEM Manufacturing`（d3） |
| `/services/` 4 张卡**整块可点** | ✅ | 4 × `sf-card__title-link`，7×5 网格逐点命中校验，真实鼠标点正中心四连跳 |
| 子页 ↔ 概览回链 | ✅ | `/services/oem/` 出链 `/services/` **2** 条（面包屑 + 正文） |

### 4.2 没做 —— 用户本次问的两项

| 项 | 状态 |
|---|---|
| ① 导航改名 `OEM/ODM → Services`（英）/ `合作模式`（中） | ❌ **完全没做**（线上仍是 `OEM/ODM`；主题里 0 行改名代码；zh 也显示英文） |
| ② 首页 OEM/ODM Service 区块 4 个框加链接 → `/services/oem/` 等 | ❌ **完全没做**（区块内 `<a>` = 0，`sf-card__title-link` = 0，连区块级按钮也没有） |

### 4.3 没做 —— 期望结构里的两带

| 项 | 状态 |
|---|---|
| 定制能力（独立带） | ⚠️ 半带（只剩 `R&D & Formulation` 一栏的 5 条） |
| 工厂能力（独立带） | ❌ 无 |

### 4.4 顺带发现的关联缺口（非用户所问，但影响 IA）

| 项 | 说明 |
|---|---|
| 页脚无 services 入口 | 4 栏 0 条，`/services/` 与 4 子页在页脚不可达 |
| 导航无下拉 | `OEM/ODM` 是单链接，4 个子页在导航不可达 |
| `/cooperation/` 是孤页 | 200 但导航/页脚均无入口（早前扫描已记为 IA 混淆风险） |
| zh 内容层零翻译 | `/zh/services/` 渲染同一英文 h1 ⇒ 改名到「合作模式」有前置依赖（见 §1.3） |

---

## 五 建议补做方案（待裁决，未实施）

### 组 1 — 导航

| | A1 只改 label | A2 label + 4 子项下拉 | A3 页脚加 Services 栏 |
|---|---|---|---|
| 做法 | 把菜单项 11 文案改成 `Services`；zh 侧另加 TP 条目 `合作模式` | 在 A1 基础上，仿 `Products` 加 4 条 `navigation-link` 子项 | 只改 `parts/footer.html`（**模板文件，零 DB**），加一栏 4 子页链接 |
| 写 DB | 1 行 label（+ TP 条目 1 条） | 5 条 | **零** |
| 收益 | 命名对齐，用户看得见 | 4 子页导航可达 | 补上页脚缺口；4 子页获得常驻入口 |
| 风险 | 低。但 zh 依赖 TP 条目存在（§1.3） | 中：改写 `wp_navigation` 结构；需处理 zh 的 TP 条目与 `current-menu-item`（站点导航**零当前态**是已知缺口） | 最低 |
| 备注 | 与 `/cooperation/`（Cooperation Models）命名更近 ⇒ 需一并定 IA | 建议 A1+A3 先做，A2 视 IA 决策 | 可与 A1 并行 |

### 组 2 — 首页 4 个框

| | B1 h3 包 `<a>`（**推荐**） | B2 整卡变 `<a>` | B3 追加区块级按钮 |
|---|---|---|---|
| 做法 | `<h3><a class="sf-card__title-link" href="/services/oem/">…</a></h3>` ×4 | 照 `front-page.html` L1002 case-study 写法把整块做成 `<a>` | 区块末加 `See all services →` → `/services/` |
| 与 H8c 一致性 | **与 `/services/` 4 张卡完全同法**（零 CSS、零 JS、focus 描边与整卡可点自动继承） | 不一致（两套写法） | 补充 |
| 视觉变化 | **零** | 有（hover/颜色会变） | 小 |
| 成本 | 4 处编辑 | 4 处重写 + 视觉回归 | 1 处 |

> 未定项：链到**子页**（`/services/oem/`）还是**概览锚点**（`/services/#oem`）。
> 建议子页（H8c 已建好 4 个实体页，且整块可点已在 `/services/` 验证过）。
> 另需定：首页卡是否统一成 `/services/` 的长名文案。

### 组 3 — 总览页补两带

| | C1 定制能力 | C2 工厂能力 |
|---|---|---|
| 建议 h2 | `Custom Formulation Capability` 类 | `Manufacturing Capability` 类 |
| 内容 | 3–4 条摘要（配方开发 / 活性物含量 / 适口性 / 稳定性）+ 链到 `/quality/`（Palatability Testing）与 `/services/odm/` | 摘要（GMP 车间 / 洁净等级 / 设备台数 / 产能 / 8 剂型线）+ 链到 `/factory-tour/` 与 `/quality/` |
| 插入位置 | 「What We Handle」之后 | 「How We Work」之后 |
| ⚠️ 约束 | **只做「摘要 + 去处」，不搬 `/factory-tour/`、`/quality/` 的内容**（避免重复内容页） | 同左 |
| ⚠️ 连带 | 圆点轨 6 → 8；`/services/` 字节变 ⇒ 必须同步更新 `b2d_h8c_live_check.py` 的 `OVERVIEW_H2` 六条全文清单与相关断言，并重跑门 | 同左 |

---

## 六 需要用户裁决（未做任何实施）

| # | 问题 | 为什么需要你定 |
|---|---|---|
| ① | 导航：改名为 `Services` 吗？中文一定要 `合作模式` 吗？（**zh 需要先有 TP 条目**，见 §1.3）加不加 4 子项下拉？ | 命名是品牌/IA 决策；且 zh 侧有前置依赖 |
| ② | 页脚要不要加一栏 Services（4 子页入口）？ | 补 IA 缺口，零 DB 风险，但改模板字节 |
| ③ | 首页 4 框：链到 4 个子页还是 `/services/` 锚点？卡名统一为长名吗？加不加区块级按钮？ | 文案与 IA 决策 |
| ④ | 总览页补「定制能力」「工厂能力」两带吗？按「摘要 + 去处」做可以吗？ | 会改 `/services/` 字节，连带门断言 |
| ⑤ | `/cooperation/` 孤页怎么处置（进导航 / 合并进 `/services/` / 保持孤页）？ | 与①的命名强耦合 |
| ⑥ | 这两项属于哪一批？（并进批 3b，还是排到生产上线之后） | 排序决策 |

---

## 七 本报告明确**没有**做的事

- 未改任何模板 / `functions.php` / `style.css` / JS
- 未写任何 DB 行、post meta、option；未改 `wp_navigation`
- 未 pull、未部署、未碰生产站（全程只对 dev 做 GET；Basic Auth 后只读）
- 未新增/修改任何门与 E2E 断言
