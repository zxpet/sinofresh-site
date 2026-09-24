# Batch H8c — 上线前剩余任务 · 批 3／3：四个合作模式各自成页，概览四张卡整块可点（2026-09-23）

> 代码提交 `b9930fd`（`Batch H8c (1/2)`）。本文是证据档（`(2/2)`）。
> 前两批：批 1 `d249fcf`／`c43708e`（H8a）＝ `2.10.74`；批 2 `a72bbcb`／`1234492`（H8b）＝ `2.10.75`。
> 本批版本 **`2.10.75 → 2.10.76`**。dev live 仍是 `2.10.73`（未 pull，等用户单独授权）。

---

## 〇、本批范围与三条裁决

### 0.1 范围

待办21「Services 4 详情页」。原话不在仓库里（`conversation_search` 未取回），
因此按停机条件③发问，用户给出三条裁决，**全选推荐项**：

| # | 问题 | 裁决 |
|---|---|---|
| 1 | 落地形态 | **B：建 4 个 WP 子页**（不是 4 个锚点段、不是 4 条独立顶级路由） |
| 2 | 改哪张卡 | **就是现有 4 张卡**（概览页那四张，不新做卡） |
| 3 | 点击范围 | **4 张卡整块可点**（不是只让标题文字可点） |

### 0.2 一条贯穿全批的原则

四个新页说的每一句话，都是站点**已经公开过的**事实：MOQ 500–1,000、取样 3–7 天 · $200 可抵、
量产 7–15 天、30% 定金 ＋ 70% 出货前、FOB/CIF/EXW/DDP、六项认证、8 个剂型、单据清单。
**没有发明任何新数字**，而且 Key Facts 表**逐字节重复概览页那一张**——
并且这一点是被门**断言**的（见 §3.4），不是"看着像"。

---

## 一、实现要点（为什么这么写）

### 1.1 整块可点：零 CSS、零 JS

主题**早就有**这套机制：`.sf-card__title-link` ＋ `::after{inset:0;z-index:1}` ＋
`:focus-visible::after{outline}`。所以改动只是把 h3 里的文字包一层 `<a>`：

```html
<h3 class="wp-block-heading"><a class="sf-card__title-link" href="/services/oem/">OEM &#8212; You Bring the Formula</a></h3>
```

收获三件事，且**一行 CSS、一行 JS 都没加**：

* 整卡可点（`::after` 铺满卡片）；
* 每卡**只有一个 tab 停点**（不是"标题里每个词一个链接"）；
* 键盘聚焦画出**围绕整张卡**的描边（帧 `after-card1-focus`，实测 5885 像素、颜色 `#5AB735`）。

### 1.2 路由机制：嵌套子页也命中按 slug 命名的模板

实测钉死（本批最重要的环境事实）：

```
page-{post_name}.html  →  page-{id}.html  →  page.html
```

* `/products/soft-chews/` 服务 `sf-breadcrumb--d3` ⇒ 命中 `page-soft-chews.html`；
* `/services/oem/`（同样是 `post_parent` 非零的子页）⇒ 命中 `page-oem.html`；
* **没有对应 WP page 时一律落 `page.html` 通用兜底**——这正是 §3.6 BEFORE 半边取证的东西。

### 1.3 四个模板只复用既有骨架

每页 202 行，带序固定：

```
hero(d3 面包屑＋h1＋18px 副标) → light(How <Mode> Works) → white(What You Provide / What We Handle)
→ light(Key Facts 表) → white(3 条 FAQ) → primary(CTA → /contact/) → footer
```

四页**除指名自己的那几处外逐字节同构**（h1／面包屑 current／band1 h2／band1 正文／三条 FAQ 问句）。

### 1.4 两处机制必须"认识"这四个新页

| 机制 | 改前 | 改后 |
|---|---|---|
| 点轨白名单 | 只有 `services` | `'services','oem','odm','contract-manufacturing','private-label'` |
| Service schema | 硬绑 `is_page('services')` | 按**当前页 slug** 查一张 5 项表（概览自己的那条**逐字节未变**） |

**FAQPage 与 BreadcrumbList 一行代码都不用改**：生成器扫模板里的
`<details><summary>` 对（≥2 才发）与 `.sf-breadcrumb`（≥2 crumb 才发）——
**按图案写对模板就自动有 schema**。这一点被 E2E 在真实 DOM 里验过（§4.1）。

---

## 二、改动清单（提交 `b9930fd`）

| 文件 | 改动 |
|---|---|
| `templates/page-oem.html` 等 4 个 | 新建，各 202 行／11.0–11.2 KB |
| `templates/page-services.html` | 4 行：四张卡的 h3 各包一层锚 |
| `functions.php` | 3 处：点轨白名单 ＋ enqueue 版本 `2.10.75→2.10.76` ＋ Service schema 改查表 |
| `style.css` | **1 行**：`Version: 2.10.76`（本批 CSS 侧唯一改动） |
| `tools/b2d_h8c_dbpages.php` | 新建：建 4 个 page，dry-run/snapshot/apply/verify/revert 五模式 |
| `tools/b2d_s3_h8c_paths.txt` | 新建：4 条新路由（**75 行清单不动**，改它会破坏 H8a/H8b 基线与 A/A） |
| `tools/b2d_h7_gate.py` | 新增 `BATCHES['h8c']` ＋ `new_pages` 取证段 ＋ 八个 helper |
| `docs/batch3-services-scan.md` | 批 3 扫描报告（实施前） |

**数据侧**（用 `b2d_h8c_dbpages.php`）：创建 #217 oem／#218 odm／#219 contract-manufacturing／
#220 private-label，全部 `post_parent=29`（/services/）、`publish`、`post_content` 空
（与 8 个剂型页一致的形态）。`verify` **4/4 PASSED**。
守卫：四个 slug 任一被占用即拒；`wp_insert_post` 静默改 slug 即**硬停** exit 1；
revert 只删自己快照里记的 `created_id` 并校验 slug/parent 未变。

**未引入**：ACF／任何 JS 库／任何 CSS 框架。

---

## 三、门（`tools/b2d_h7_gate.py --batch h8c`）

### 3.1 全绿表

| 段 | 结果 |
|---|---|
| A/A（同状态两份抓取） | 75 页 **0 差异** |
| main proof（`insert`） | 75 页 **0 差异**，`applies` **4/4** |
| coverage | **16/16** |
| invariants | **21/21** |
| 掩码 blob 回读 | 23 页 **0 不符** |
| 破坏矩阵 | **6/6** |
| 负对照 | **26/26** |
| `new_pages`（本批新增段） | **47/47** |
| `--source`（**独立跑一次**） | **29/29** |
| **合计** | **两个 JSON 全绿** |

命令（每批两个 JSON，`--source` 必须独立跑）：

```
--batch h8c --base _backup/b2d-h8c-baselines --cand _backup/b2d-h8c-candidates \
  --aa _backup/b2d-h8c-candidates-aa \
  --base-new _backup/b2d-h8c-baselines-new --cand-new _backup/b2d-h8c-candidates-new \
  --matrix --negctl --json _backup/b2d-h8c-gate.json
--batch h8c --source --json _backup/b2d-h8c-gate-source.json
```

### 3.2 `new_pages`：新增路由为什么不能走主证

主证要求「把 baseline 变换成 candidate」。而这四条路由在 baseline 侧渲染的是**通用兜底页**——
让 transform 去"造一整页"等于把渲染器教给门，而**会渲染的门就能同意一个坏渲染器**。
所以新路由另开一段，只在两份抓取与已服务字节上作证：

* **BEFORE**：四条路由是**同一张通用页**，只被标题改过名；且四条 payload 计数全 0。
* **AFTER**：各带自己的 h1／三级面包屑／三条 FAQ；该一致的地方逐字节一致，
  该不同的地方两两不同；Service／BreadcrumbList／FAQPage 各一条。

`new_pages` 的判据里有两处**必须自证**而不是靠 `find()` 返回 -1 静默通过：

* shell 段计数 `unmatched`：锚点缺失即 FAIL（否则比较两个空串恒真）。
* 身份计数改成**点名承载元素**（见 §3.5）。

### 3.3 四处"判据自己写错"（都是本批自查发现并重构，未放宽）

| # | 症状 | 病根 | 修法 |
|---|---|---|---|
| 1 | `before` 四条路由 distinct=**4** | 归一化漏了 `page-id-NNN`、`"source_id":N`、`"signature":"…"` | 补齐三类正则 ＋ 复用站点掩码 `mask()` |
| 2 | 同上，改完仍 distinct=**2**（三 + 一） | ⛔ `t.replace(crumb,…)` **太粗**：private-label 的名字是 Organization 节点里**四页都一样的常量** `"Private Label Pet Supplements"` 的子串 ⇒ 归一化**制造**出一处差异 | 改成**按承载元素点名**（`<title>`／`<h1>`／`aria-current` span／`ListItem` name），且只在该元素内确认命中 crumb 才抹 |
| 3 | 身份计数 `crumb x5/x6/x7` | 用裸子串计数，而 crumb 同时住在 title／`<h1>`／Service name／band1 h2 里 | 改成三个**只命中一个元素**的 needle：`<title>…</title>`、`>…</h1>`、`aria-current="page">…</span>` |
| 4 | `commercial-terms region could not be read` | ⛔ 锚点写成 `<!-- wp:heading`，而**已服务的页面里区块注释为 0** | 锚在渲染后的 `<h2` → `</table>` |

### 3.4 最关键的几条断言

* **四页重复的那张表**：`_h8c_keyfacts_region()` 从概览页与四个详情页各切出
  「h2 开标签 → `</table>`」的**内容区**，要求**逐字节相同**。
  切的是内容而不是包装层——**背景色两边故意不同**（概览的带序与详情页不同），
  写在包装层上会为一件设计上的差异判红。
* **`sf-card__title-link` 不能只用它自己计数**：这个类**改动前就有载体**
  （首页与 `/zh/` 各 3 张文章卡）⇒ 逐页计数在那些页会是 3、概览页是 4。
  本批特有的claim 是**「这个类 ＋ 四条新路由之一」这个组合**，它在别处没有任何载体。
* `corroborated` 的期望值：概览页读 **baseline 的 `sf-card--roomy` 卡盒数**；
  其他页读**该页 baseline 自己的类计数**（即"本批没动它"这个更弱但成立的说法）。

### 3.5 负对照 26/26——并且**点名**了它该打断哪条断言

本批给 `nc_source` 加了**第 5 个元素**：这条突变**应该**打断哪条 source 断言的 label。
理由是本项目已经写进纪律的那条：

> 「负对照『响了』≠『因它的理由响』」。

所以 `nc_source` 现在先取失败集合，再要求 owner 在集合里，否则报
`wanted '<label>' among [...]`。兼容性已实测：H8b 的 **12 条四元组**照常全部响
（用 `git archive a72bbcb sinofresh-theme` 建副本跑 `--source --theme` 验证，`PASS`）。

**顺手修掉 5 条"不可能响"的负对照**（3 条靶子根本不存在 + 2 条靶子打不动断言）：

| 负对照 | 原症状 | 修法 |
|---|---|---|
| overview 失去 terms 表 | 靶在 `tpl_svc`，没有任何断言读它 | 补断言「概览自己仍发布那张表」 |
| 详情页掉成二级面包屑 | 靶在 `tpl_oem` 的 `--d3`，没有断言读它 | 补 4 条 `--d3` 导航断言 |
| 详情页不再点名父页 | 靶在 `tpl_odm`，断言只在 `tpl_oem`/`tpl_con` | 补 `tpl_odm`／`tpl_pri` 两条 |
| 详情页丢商业条款 | 改的是 `<table>` 的类名，而断言读的是 Trade Terms **行** | 靶改成那一行 |
| 详情页藏起第二条 FAQ | ⛔ 三条里**有一条写作 `sf-faq__item" open>`**（多一个 `open` 属性）⇒ 要求 `"` 后紧跟 `>` 的 needle 只命中 2/3，改完还剩 1 条 ⇒ 断言仍真、负对照报 "sabotage survived" | 靶改成 **class token**，三处一起抹 |

### 3.6 旧批回归

`_h8c_norm_baseline`／`new_pages` 都是 h8c 专属；被改动的公共路径只有
`nc_source` 的循环（见 §3.5）与 `invariants` 的**闭包**。回归方式：
用 `git archive a72bbcb` 出 **H8b 主题副本**跑 `--batch h8b --source --theme <副本>` ⇒ `PASS`，
再用同一副本跑 `--negctl` ⇒ 12 条 NC-src 全响。

---

## 四、E2E（`tools/b2d_h8c_e2e.py`）

### 4.1 预检 **91/91 PASS**（2.10.76）

只做**字节层看不到**的两件事：

* **整卡是不是链接**：7×5 网格（四角内缩 6%，避开圆角）逐点 `elementFromPoint` 分类，
  再用 `mouse move/down/up` 在**卡片正中心**真实点击（不是 `click <选择器>`——
  那会点在链接文字自己的中心，overlay 完全缺失也照样通过）。
  桌面 1440：**四个卡各 35/35 点全中链接**，四次点击分别落到
  `/services/oem/`、`/odm/`、`/contract-manufacturing/`、`/private-label/`。
* **点轨是每页现建的**：`nav.sf-toc li` 与 `.sf-toc-target` 各 **5**，
  且 `railItems == 该页 h2 文本`（标签就是页面自己的标题）；滚动后
  `sf-toc--hidden` 自动摘掉。

四页各自：h1 唯一且是自己的、面包屑 3 级且 current 是自己、5 个 h2、
3 条 FAQ（**恰第一条 open**）、Terms 表 5 行与概览同序、
Service/BreadcrumbList(3 级)/FAQPage 各一、无横向溢出。

### 4.2 live 24/24（2.10.73）——按"该红的地方红"设计

四条路由在**共享 DB** 里，所以 live 上**路由能解析**（200），但由 live 主题的
**通用兜底页**作答：`crumbLevels=2`、`d3=False`、`keyfacts=False`、`service=None`、`rail=0`；
四张卡 `linksInCard=0`。这轮就是"这个脚本能红"的证据。

### 4.3 ⛔ 本批踩到的两个工具坑（写进判据注释）

1. **`mouse move` 必须用整数坐标**。实测：传 `"499.6"` 时指针**没动**，
   随后的 `down/up` 落在 **(0,0)**——页面 HEADER——并且**工具不报错**，
   `<a>` 收不到 click，症状是"命中校验说在链接上、真点击却不跳转"。
   整数 `261 500` ＋ `mouse down left` ⇒ 立刻跳到 `/services/oem/`。
   判据现在**取整**并显式给按钮名。
2. **手机断点上卡片会被站点自己的固定层盖住**（不是本批的问题，也不是链接没铺满）。
   网格分类于是有**三类**：`link` / 站点自有固定层（悬浮按钮、cookie 横幅）/ `other:`。
   实测 375 宽、卡片居中时：**21/35 点是链接，其余 14 点是悬浮按钮**
   （其中一张卡另有 7 点被 cookie 横幅盖住），**`other` 恒为空**。
   判据的两半写死为：卡片**正中心**必须是链接 ＋ **每个非链接点都必须可归因**——
   把遮挡笼统算成"不是链接"会让本批替别人背锅；只看中心又会把真实遮挡藏在绿线后面。

---

## 五、帧（`docs/batchH8c-shots/`，15 张，**0 平帧**）

| 组 | 帧 |
|---|---|
| live 2.10.73 | `before-card1`、`before-oem-top`、`before-odm-top` |
| preflight 2.10.76 | `after-card1`、**`after-card1-focus`**、`after-overview-terms`、`after-oem-top`、`after-oem-terms`、`after-oem-faq`、`after-odm-top`、`after-contract-top`、`after-private-top`、`after-oem-top-375`、`after-private-terms-375`、`after-private-faq-375` |

### 5.1 `after-card1-focus` 是唯一诚实画得出"整卡是链接"的帧

静息态前后**看起来一模一样**（锚继承卡片颜色），所以拿静息态做 before/after 是**没有差别**的。
真正能拍下来的是**键盘聚焦时的描边**：连按 **19 次 Tab** 落到卡片链接，
`:focus-visible` 生效，主题画出的描边**圈住整张卡**（实测 5885 像素、
主色 `(90,183,53)`＝`#5AB735`）。这同时就是"每卡一个 tab 停点"的画面。

### 5.2 一条比断言更硬的静息态事实

`before-card1` 与 `after-card1` 逐像素比对：

* **暗像素包围盒完全相同**：`(34,38,259,275)`，暗像素数都是 **4179** ⇒ **零布局位移**；
* 卡盒尺寸 298×341 两侧相同；
* 差异 3425 像素、全部落在标题文字块内，最大通道差 228 —— 这是
  文本被内联 `<a>` 包住后**重新光栅化**（子像素提示不同），
  **两张图肉眼无法区分**。

⇒ 本批在静息态**没有加任何可见像素**：变的只有命中区域和焦点态。

### 5.3 一个拍帧机制坑（已修）

像素带裁切必须**夹到图像高度**：live 那半边的通用兜底页**比对照的详情页短**，
不夹就会把页面之外补成黑边，一帧"黑底"看起来像渲染故障。

---

## 六、待办 & 约束遵守情况

### 交给用户的

1. **`/services/` 概览自身**：本批只动了四张卡的 h3（包锚）。**没有**改它的文案、带序、Key Facts 表。
2. **手机断点上的固定层遮挡**（§4.3 第 2 条）：卡片居中时下缘约 40% 落在悬浮按钮／cookie 横幅之下。
   这是站点既有的固定层行为（live 上同样存在），本批不改；若希望卡片下缘也可点，
   需要另一批单独裁决（改悬浮层位置或给卡片让位）。
3. 四个新页的**销售内容**（价格、交期、认证口径）目前全部引用站点既有公开事实；
   若要按模型分别给不同承诺，属内容变更，等销售确认。
4. 长期待办不变：post 158 三处演示值／`sf_formula_container="Round"`／
   `sf_formula_shelf_life` 与 specs 矛盾；Shape(8)/Container(7) 图库待传图；
   预检副本 `79ec18e1…`／`1234492…` 的删/留；`docs/dev-lockdown.md` 10 项生产上线清单。

### 本批的约束遵守

| 约束 | 状态 |
|---|---|
| 不引入 ACF／JS 库／CSS 框架 | ✅ 零新增依赖；style.css 只改版本号一行 |
| 不碰 post meta | ✅ 只建 4 个 page（空 `post_content`）；数据问题只报告 |
| 先扫描、报告后停、等确认再实施 | ✅ 批 3 扫描报告 ＋ 三条裁决后才动手 |
| 每批完成 commit ＋ push | ✅ 代码段 `b9930fd` 已 push；证据段见本档 |
| **不 pull（等单独授权）** | ✅ dev live 仍 `2.10.73`；候选只装进 **preflight 层** `b9930fd` |

### 停机条件检查

| 条件 | 本批 |
|---|---|
| ① 扫描与预期方向不符 | 未触发（扫描结论与四条裁决一致） |
| ② 门抓到产品 bug | **未触发**——门自身四处判据写错并已重构（§3.3），产品侧零缺陷 |
| ③ 需要用户裁决 | 触发一次（待办21 落地形态），已按 §0.1 三条裁决执行 |
