# 批次 1 / 步骤 2 —— Hero 极简（8 页剂型页）· 执行与核验报告

- **日期**：2026-09-20
- **范围**：8 个剂型页 `page-{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}.html` 的 Hero 区
- **备份**：`_backup/batch1-s2-hero-20260920-103207/`（11 文件 / 767,782 B，含 MANIFEST + 可执行回滚命令）
- **结论**：✅ 12 项核验全通过；**限定证明**证明 Hero 之外的字节差异 100% 归入 3 类已知例外，别无他项

---

## 一、改动清单

| # | 文件 | 改动 | 备份 md5 → 当前 md5 |
|---|---|---|---|
| 1 | 8 × `templates/page-*.html` | Hero 由「两栏（左文右轮播）」改为**单栏居中**；删轮播 DOM + 进度条 DOM；删描述段；删 Request a Quote；插入 `<h1>` 原文 + 新副标题 + 2 按钮；追加 `<!-- sf-schema-desc: … -->` 承载注释 | 逐页见下 |
| 2 | `style.css` | 删 `.sf-pslider`（96 行）/ `.sf-product-hero-image`（28 行）/ `.sf-hero-textlink`（13 行）；**保留** `.sf-slider-progress`；订正 1617 行注释 81px→61px；头部 `Version: 2.10.39` | `db80b653…` → `9f6f8058…`（241,468 → 237,655 B） |
| 3 | `functions.php` | 移除 `sinofresh-product-slider` enqueue；style 句柄版本 `2.10.38 → 2.10.39`；**Product JSON-LD 抽取重写**（见第四节） | `46382246…` → `2b251185…`（105,847 → 106,973 B） |
| 4 | `assets/js/product-slider.js` | **删除**（源码 + Local，三道闸协议） | `1a9368bc…` → 不存在 |

### 8 个模板体积

| page | 备份 B | 当前 B | ΔB |
|---|---:|---:|---:|
| soft-chews | 61,422 | 58,563 | −2,859 |
| tablets | 52,110 | 49,263 | −2,847 |
| powders | 51,362 | 48,515 | −2,847 |
| pastes | 48,544 | 45,701 | −2,843 |
| drops | 48,876 | 46,007 | −2,869 |
| liquids | 49,401 | 46,524 | −2,877 |
| fish-oil | 48,823 | 45,942 | −2,881 |
| dental-chews | 54,872 | 51,975 | −2,897 |
| **合计** | **415,410** | **392,490** | **−22,920** |

`style.css`：7,794 行 / 241,468 B → **7,644 行 / 237,655 B**（−150 行 / −3,813 B），大括号 1245/1245 平衡。

### 改后的 Hero 结构（以 liquids 为例）

```html
<section class="wp-block-group sf-hero-inner" style="padding-top:…--80);padding-bottom:…--80)">
<!-- sf-schema-desc: Custom liquid supplements for multivitamin, joint, immune, and skin & coat support. … -->
<!-- wp:html --> <nav class="sf-breadcrumb sf-breadcrumb--d3">…</nav> <!-- /wp:html -->
<!-- wp:heading {"level":1,"textAlign":"center","textColor":"card-white",…} -->
  <h1 class="has-text-align-center wp-block-heading has-card-white-color …">Private Label Liquid Pet Supplements</h1>
<!-- wp:paragraph {"align":"center","textColor":"card-white","style":{"typography":{"fontSize":"18px"}}} -->
  <p>8 dosage forms · FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC · Flexible MOQ · Export to 30+ countries</p>
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},…} -->
  <!-- wp:button {"backgroundColor":"cta","textColor":"card-white"} -->   → Browse Standard Formulas → #formulas（橙实心·主）
  <!-- wp:button {"textColor":"card-white","className":"is-style-outline"} --> → Build Custom Formula → #configurator（描边·次）
</section>
```

---

## 二、完整限定证明（核心证据）

**问题**：掩码 sha256 只能证明「变化集合 == 8 剂型页」，不能证明「每页的改动只在 Hero 内」。
**做法**：把基线掩码文本逐步归零，直到与当前逐字节相同。每一步都对应一个**可独立验证**的已知例外。

| 归零步骤 | 操作 | 8/8 通过 |
|---|---|---|
| 0 | 基线滞后订正 `after packaging ready` → `after packaging is ready` | ✅ |
| 1 | 替换 Hero 段（基线 `section.sf-hero-inner` → 当前） | ✅ |
| 2 | 删除 `<script id="sinofresh-product-slider-js" …></script>` | ✅ 各 1 个 |
| 3 | 中和 `<style id="core-block-supports-inline-css">` 内容 | ✅ |
| **结果** | **四步归零后 A ≡ B 逐字节相同** | **✅ 8/8** |

### 例外 ①：`<head>` 内 `wp-container-core-*` 布局规则集

WP 由区块标记重新计算，删了 columns/buttons 区块后规则集**合法**变化 —— 8 页**同构**：新增 1 条、删除 1 条。

| page | 基线规则数 | 当前规则数 | 新增 | 删除 | CSS 字节 |
|---|---:|---:|---:|---:|---|
| soft-chews / tablets / powders / pastes | 11 | 11 | 1 | 1 | 848 → 809 |
| drops / liquids / fish-oil / dental-chews | 14 | 14 | 1 | 1 | 1,171 → 1,132 |

规则级明细（8 页完全同构）：

```
＋ .wp-container-core-buttons-is-layout-b6c20db1   ← 新 Hero 按钮组（justifyContent:center）
      justify-content:center
－ .wp-container-core-group-is-layout-45ec56b7     ← 旧 Hero 两栏外层 group
      align-items:center
      flex-direction:column
      justify-content:center
```

> 即：**少了一个两栏布局容器、多了一个居中按钮组** —— 与「两栏轮播 → 单栏居中」的改动语义 1:1 吻合。

### 例外 ②：`<body>` 内 product-slider 脚本标签

8 页基线各 1 个（位于 `</head>` **之后**的 footer），当前各 0 个。这是决策 ⑥ 的必然产物，非意外改动。

### 例外 ③：`style.css?ver=` 版本号

2.10.38 → 2.10.39（决策 ⑧，已掩码，19 页各 1 处）。

### 例外 ④（非步骤 2 改动）：基线滞后

`Lead time` 措辞 `after packaging ready` → `after packaging is ready`。

- 依据 `tools/_b1r_step1_rollback.py:8` —— 该语法订正在**步骤 1 回滚时已被显式「保留（用户决策 ⑥）」**；
- 佐证 `_backup/batch1-s2-hero-20260920-103207/templates/*.html`（**步骤 2 之前的备份**）8 页均已是 `is ready`；
- 基线目录 `/tmp/b1/pages_s1` 爬取于 **09:17**，早于折叠/回滚周期（09:38–10:05）→ 抓到的是中间态。

> ★ **仪器教训**：限定证明在此充当了「**基线新鲜度探测器**」。若不归零该项，会误报成「Hero 之外还有第三类改动」。
> **铁律**：每完成一次**改状态**的动作，必须**重新抓取基线**，否则基线滞后会污染下一轮比对结论。

### 非剂型页零改动

11 个非剂型页（about / blog / contact / cooperation / factory-tour / faq / feedback / home / products / quality / services）掩码后 **sha256 逐字节全同**（如 `home` `e5e2d4a1e73cfb45` = `e5e2d4a1e73cfb45`）。

---

## 三、核验 12 项

| # | 判据 | 结果 | 证据 |
|---|---|---|---|
| 1 | 8 页 Hero ≤350px 一致 | ✅ | 桌面 1440：**8/8 = 328px**（pt/pb 48/48）。移动 375：460–499px（堆叠，无 350px 判据） |
| 2 | 无轮播 | ✅ | `.sf-pslider`/`.sf-product-hero-image`/`.sf-slider-progress` 节点 8 页均 **0**；Hero 内两栏 0 |
| 3 | 2 按钮且 href 正确 | ✅ | `Browse Standard Formulas → #formulas`（实心 `cta` 橙）/ `Build Custom Formula → #configurator`（outline）；`justify-content:center` |
| 4 | 副标题含 6 认证 + Flexible MOQ + 30+ countries | ✅ | 8 页逐字节同一句：`8 dosage forms · FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC · Flexible MOQ · Export to 30+ countries` |
| 5 | H1 逐页沿用原文 | ✅ | 8 页 h1 文本与备份逐字相同（见附录） |
| 6 | `product-slider.js` 已删、无 404 引用 | ✅ | 源码 + Local 两侧均不存在；`curl` → **404**；源码侧 `product-slider` 引用 **0** |
| 7 | `.sf-slider-progress` CSS 保留 | ✅ | `style.css` 3 处 + `templates/front-page.html` 1 处（首页 `hero-slider.js` 共用，**未动**） |
| 8 | 19 页均 200、无 PHP 报错 | ✅ | 19/19 → 200；`Fatal error/Parse error/Warning/Notice/Deprecated/Uncaught` **0 命中**；合计 2,845,486 B |
| 9 | 掩码 sha256 回归 | ✅ | 11 非剂型页 **SAME**；变化集合 == 恰好 8 剂型页；限定证明 8/8 通过 |
| 10 | 源码 = Local 一致 | ✅ | `diff -rq` → **Files differ = 0**（仅 `_backup/_backup_x/docs/screenshots/.DS_Store` 为源码侧不部署资产） |
| 11 | `grep -rn "/ -->"` 零残留 | ✅ | `*.html/*.php/*.css` 零命中（唯一命中在 `tools/_gf5_submit_test.php:211`，是**断言语句里的字面量**，已知假阳性） |
| 12 | 改后截图交付 | ✅ | `screenshots/batch1-step2-hero/`（liquids + soft-chews × 1440/375，共 10 图 + `measure.json`） |

---

## 四、⚠️ 附带发现并修复：Product JSON-LD 回归（步骤 2 的连带损伤）

这是本步**最关键**的发现 —— 一个**没有任何视觉表现**的数据层回归。

### 发现过程

限定证明第一次跑 **失败**：替换 Hero 段后页面仍不一致。深挖发现 body 差异来自**被删的脚本标签**（已归入例外 ②），但排除后**仍有差异** → 顺着查 `<script type="application/ld+json">`，发现 8 页 `description` 全变空、`image` 变成了**同类目下另一个产品的图**（7 页变成 `soft-chews.webp`，soft-chews 自己变成 `tablets.webp`）。

### 根因（hero 结构依赖）

`functions.php` 的 `wp_head` 钩子**从模板 HTML 正则抽取** Product JSON-LD：

| 字段 | 原抽取方式 | 删 Hero 后的后果 |
|---|---|---|
| `name` | Hero 的 `<h1>` | ✅ 未受影响（H1 保留） |
| `description` | Hero 里那个 `18px + card-white` 的 `<p>` | ❌ 该段被决策 ② 删除 → 抽到空串 |
| `image` | **「文件里第一个 `<img>`」** | ❌ 原本是轮播首图（本方剂型图），轮播删除后第一个 `<img>` 变成下方 **Related 区块里兄弟产品的缩略图** → 8 页里 7 页张冠李戴 |

### 修复方式

1. **description → 模板承载注释**（文案留在模板、不硬编码进 PHP）：
   在 Hero `<section>` 开标签后插入 `<!-- sf-schema-desc: {原文案} -->`，PHP 优先读它；找不到时降级回旧的 18px 段落正则。
2. **image → 按本方剂型名解析**，用 `wp_get_upload_dir()` + `glob('*/*/{slug}.webp')`；取不到就**丢弃该键**（宁缺勿错），再降级到「文件名含 slug 的 img」。
3. 组装改为**保序且跳过空键**，避免空串污染：
   ```php
   $schema = array('@context' => …, '@type' => 'Product', 'name' => $name);
   if ($description !== '') { $schema['description'] = $description; }
   if ($image !== '')       { $schema['image']       = $image; }
   $schema += array('brand' => …, 'manufacturer' => …, 'category' => 'Pet Supplements');
   ```

### 修复验证

- 8 页 `description` / `image` **与改动前逐字相同**；
- 整个 Product JSON-LD 对象与基线 **deep-equal 且键序一致**；
- `php -l functions.php` → `No syntax errors detected`；
- 19/19 页复抓 200、无 PHP 报错；重跑掩码回归与限定证明 **全通过**。

> ★ **升格为铁律**：**删 DOM 结构前，先扫描 `functions.php` 里是否依赖该结构做数据抽取。**
> 视觉回归 100% 通过 ≠ 无回归 —— 数据层（JSON-LD / SEO / structured data）必须**单独核验**。

---

## 五、决策 ⑦ 状态

| 项 | 状态 | 位置 |
|---|---|---|
| `style.css:1617` 注释「81px sticky bar」→ 61px | ✅ **已做** | `style.css:1617` → `land the form below the 61px sticky bar on desktop.` |
| 平板 900px sticky bar 119px vs 96px scroll-margin（仍遮 23px） | ⏳ **记入待办** | 见第七节 |

### ⚠️ 同时发现并修复一处版本号不一致

决策 ⑧ 的 bump 只落在 `functions.php` 的 enqueue，**`style.css` 头部 `Version:` 仍停留在 2.10.38**，与 enqueue 不一致（历史上二者一直同步：备份中均为 2.10.38）。

- 影响面：全仓无任何代码读取主题版本头（`wp_get_theme()->get('Version')` 等**零命中**），故为纯元数据不一致，不影响缓存破坏；
- 处置：`style.css:5` `Version: 2.10.38 → 2.10.39`，同步 Local，`cmp -s` 通过；
- 复验：重抓 19 页 **2,845,486 B 与此前完全一致** → 版本头**不进入渲染输出**，回归结论不受影响。

---

## 六、截图交付

目录 `sinofresh-theme/screenshots/batch1-step2-hero/`（另存 `/tmp/b1/step2/shots/`）

| 文件 | 说明 |
|---|---|
| `s2-liquids-1440-首屏.png` / `s2-soft-chews-1440-首屏.png` | 桌面 1440 干净首屏 |
| `s2-liquids-1440-首屏-标注.png` / `s2-soft-chews-1440-首屏-标注.png` | 桌面标注（Hero 虚线量高 + 右侧量高条 + 按钮编号 + 信息卡 + 「✓ 无轮播」徽标） |
| `s2-liquids-375-首屏.png` / `s2-soft-chews-375-首屏.png` | 移动 375 干净首屏 |
| `s2-liquids-375-首屏-标注.png` / `s2-soft-chews-375-首屏-标注.png` | 移动标注（标注文案视口感知：「移动端堆叠，无 350px 判据」） |
| `s2-liquids-1440-Hero特写.png` / `s2-soft-chews-1440-Hero特写.png` | Hero 元素级特写（无标注） |
| `measure.json` | 每页每档的测量原始数据 |

**实测读数**

| page | 视口 | Hero 高 | 轮播节点 | 按钮 | Hero 内两栏 | 轮播脚本 | 横向溢出 |
|---|---|---:|---:|---:|---:|---:|---:|
| liquids | 1440 | **328px** | 0 | 2 | 0 | 0 | 0 |
| soft-chews | 1440 | **328px** | 0 | 2 | 0 | 0 | 0 |
| liquids | 375 | 460px | 0 | 2 | 0 | 0 | 0 |
| soft-chews | 375 | 499px | 0 | 2 | 0 | 0 | 0 |

---

## 七、待办（未执行）

1. **平板 900px**：sticky bar 实测 119px，而 `scroll-margin-top` 为 96px → 锚点跳转后**仍被遮 23px**。（决策 ⑦ 记入）
2. `page-faq.html` / `page-services.html` 的 `after packaging ready` → `is ready`（**步骤 6**，剂型页本步已由步骤 1 保留的订正覆盖）。
3. `style.css:1913` 同一措辞的注释（**步骤 6**）。
4. 步骤 3：Key Facts 下移；步骤 4：Custom Formula 过渡区块（副标题接「描述段并入」的新句）；步骤 5：`#formulas` / `#configurator` 的 `scroll-margin-top: 96px`。

---

## 附录：8 页 H1 原文（逐字保留）

| slug | H1 |
|---|---|
| soft-chews | Private Label Soft Chews for Dogs & Cats |
| tablets | Private Label Pet Tablets for Dogs & Cats |
| powders | Private Label Pet Supplement Powders |
| pastes | Private Label Pet Supplement Pastes |
| drops | Private Label Pet Supplement Drops |
| liquids | Private Label Liquid Pet Supplements |
| fish-oil | Private Label Fish Oil for Dogs & Cats |
| dental-chews | Private Label Dental Chews & Sticks for … |

## 附录：工具与中间产物

| 工具 | 用途 |
|---|---|
| `tools/_b1r_step2_backup.py` | 步骤 1 备份（11 文件 + MANIFEST + 回滚命令） |
| `tools/_b1r_step2_hero.py` | 8 页 Hero 重写（双轨断言：内核级 + 页级 delta） |
| `tools/_b1r_step2_css.py` | CSS 清理（**内容锚点**定位，非行号；含大括号 tally 断言） |
| `tools/_b1r_step2_schema_carrier.py` | 插入 `sf-schema-desc` 承载注释 |
| `tools/_b1r_crawl.py` | **新增** 全站 19 页抓取（固化路径 + 301 跟随 + PHP 报错门禁） |
| `tools/_b1r_step2_render_cmp.py` | 掩码 sha256 回归（+`style_ver` 掩码） |
| `tools/_b1r_step2_confinement.py` | **新增** 四步归零限定证明 + inline-css 规则级盘点 |
| `tools/_b1r_step2_shots.js` | 交付截图（视口感知标注层） |

**关键 JSON**：`/tmp/b1/step2/{confinement_final.json, render_cmp_final.json, verify2.json, measure.json→shots/, pages_final/}`
