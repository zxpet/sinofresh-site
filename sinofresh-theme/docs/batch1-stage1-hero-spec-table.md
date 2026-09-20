# 批次 1 / 阶段 1 完工报告 —— Hero 三层按钮 + 参数速览表

日期：2026-09-20 09:1x–09:2x　范围：8 个剂型页模板 + `style.css`
备份根：`_backup/batch1-stage1-20260920-091451/`（含改动前全量文件 + 本阶段全部证据）
状态：**已完工并通过 13 项核验中的 11 项**（余 2 项属阶段 2/3）

---

## 1. 本轮交付的三件事

| # | 改动 | 落点 |
|---|---|---|
| ① | Hero 按钮改三层，移除死链 `Download Catalog` | 8 页 `templates/page-{slug}.html` |
| ② | `section.sf-formulas` 加固定锚点 `id="formulas"` | 同上（`wp:group` 注释同步加 `"anchor":"formulas"`） |
| ③ | Hero 之后新增「参数速览表」区块（5 字段） | 同上，新 `section.sf-spectable` |
| ④ | MOQ 措辞统一（附带上线：3 页补 `New brands can start with small trial orders.`） | liquids / fish-oil / dental-chews |
| ⑤ | 新样式段 `25c` / `25d`（Hero 文字链 + 速览表） | `style.css` |

改动脚本：`tools/_b1_stage1.py`（幂等，带断言；已在备份里留档）

---

## 2. Hero 三层按钮

| 层 | 文案 | 样式 | href | 实测盒模型（1440） |
|---|---|---|---|---|
| 主 | Build Custom Formula | 实色 Kiln `#B54E0F` | `#configurator` | 207×48 |
| 次 | Browse Standard Formulas | `is-style-outline` 白描边 2px | `#formulas` | 238×48 |
| 三 | Request a Quote | 纯文字链，白字 + 下划线 1px | `#inquiry-form` | 124×44 |
| — | ~~Download Catalog~~ | **已移除** | ~~`#`~~ | — |

**8 页按钮块签名完全一致**：`md5 = 19a7c818fd71`（8/8 同）。

### ⚠️ 需要你知道的一件事：桌面不是一行

`wp:block-gap` = 24px，Hero 左栏宽 **588px**（1200 内容宽 ÷ 2 − 32 沟），三个按钮合计需
**617px** → 差 29px，于是自然折成两行：

| 视口 | 结果 |
|---|---|
| 1440 | 2 行：`[Build Custom] [Browse Standard]` / `[Request a Quote]` |
| 1024 | 2 行（左栏更窄，480px） |
| 768 | **1 行**（此时列已堆叠，整行 728px 够用） |
| 375 | 3 行，逐个居中堆叠 |

你选项里写的「移动端不换行」在 375px 上物理上做不到（三按钮 569px > 可用 335px）。
桌面 2 行反而形成了「两个动作 + 一条备选路径」的层次，**我按自然结果保留**。
若要强制一行，唯一干净的路径是缩窄 `Browse Standard Formulas` 文案或压缩按钮内边距 —— 等你定。

---

## 3. 参数速览表

位置：Hero 之后、Standard Formulas 之前。**无 H2**（TOC 的 `sf-sec-N` 靠 H2 序号生成，
插入标题会让后续所有锚点漂移），可访问名由 `<caption>` 承担。

**一页一行**（本页剂型的规格）。§11 草案里那张 8 行对照表是数据采集表，不是页面成品 ——
若你要的是「8 行全剂型对照」，说一声我改，但那样每个剂型页会出现 8 页完全相同的大表。

### 8 页真实取值（全部来自各页自身 FAQ / Standard Specs，无新编造）

| 页 | Unit size | Pack options | Shelf life | MOQ |
|---|---|---|---|---|
| Soft Chews | 2 g/piece | 60/90/120 per bottle | 18 months | from 500–1,000 units |
| Tablets | 1 g/tablet | 60/120/180 per bottle | 24 months | from 1,000 units |
| Powders | 4/8/16 oz jar | — | **18–24 months** ← 你的裁定 | from 500 units |
| Pastes | 50/60/100/120 g tube | — | 24 months | from 500 units |
| Drops | 30/50 ml dropper bottle | — | 24 months | from 500 units |
| Liquids | 8/16/32 oz pump bottle | — | 24 months | from 500 units |
| Fish Oil | 8/16/32 oz pump bottle | — | 24 months | from 1,000 units |
| Dental Chews | 15–20 g/piece | 7/14/28 or 14/28/56 per bag | 18 months | from 1,000 units |

Lead time（全 8 页）：`7–15 working days after packaging ready`
> 已按你给的原话落字。英文更顺的是 `after packaging is ready`，要不要改由你定 —— 我没擅自动。

### 实测几何

| 项 | 桌面 1440 | 移动 375 |
|---|---|---|
| 区块高 | 149px（padding-top 40 + 表 109） | 290px |
| 表宽 | 1200px，居中于 x=120 | 100% |
| 列宽 | 229 / 229 / 165 / 229 / 347 | 纵向堆叠 |
| 表头 | `rgb(90,183,53)` 品牌绿底 + `rgb(28,43,36)` 墨绿字 | 表头行隐藏，字段名由 `data-label` 注入 |
| 单元格对齐 | 全部 `text-align: left` | 标签在上、值在下 |

**两处刻意的判断，请复核：**

1. **表头用墨绿字而不是白字**。白字压品牌绿对比度只有 **2.7:1**，13px 常规字重下不过 WCAG AA；
   墨绿字是 **5.8:1**，通过。站内其他地方（购物袋角标、抽屉发送键）确实用白字压品牌绿，
   但那些是 ≤14px 粗体或极小面积的装饰元素。
2. **`table-layout: fixed` + 定列宽**。用默认 auto 布局时 `7–15 working days after packaging ready`
   会独吞 434px，把 Shelf life 挤到 142px，读起来像乱格子；定列宽后五列成秩序网格。

---

## 4. MOQ 措辞统一（附带上线）

`liquids` / `fish-oil` / `dental-chews` 原来缺后半句，现已补齐。三页各命中 **2 处**：
可见 FAQ `<p>` 一次 + `FAQPage` LD+JSON 结构化数据一次（后者由 FAQ 内容自动派生，属正确传播）。

8 页现在措辞完全一致：模板各 1 处、渲染各 2 处。

---

## 5. 核验结果（对照你给的 13 项）

| # | 项 | 结果 |
|---|---|---|
| 1 | 8 页 Hero 3 个按钮，无死链 | ✅ 3 按钮 8/8；**页内容**死链 0；`href="#"` 模板残留 0 |
| 2 | 8 页速览表显示 5 字段 | ✅ 表头 5 列、`data-label` 5 个，8/8 |
| 3 | 桌面配置器默认收起（~140px） | ⏸ 属**阶段 2** |
| 4 | 移动端配置器保持现状（抽屉） | ✅ 未动：bar `flex`、drawer `hidden`、summary `display:none`、`mobilebar none` 全部照旧 |
| 5 | Build Custom → 展开 + 滚动不被遮 | ⏸ 展开属阶段 2；滚动属阶段 3（见 §7） |
| 6 | Browse Formulas → 滚动到 Formulas | ✅ 跳转本身通（`hash=#formulas`）；**落点被遮 82px** 见 §7 |
| 7 | TOC 正常，`sf-sec-N` 不变 | ✅ 8 页均为 `sf-sec-0…5`，与扫描基线逐项一致 |
| 8 | 8 页全 200，无 PHP 报错 | ✅ 19/19 页 = 200；特征串扫描 0 命中 |
| 9 | 源码 = Local（`cmp -s`） | ✅ 9 个变更文件逐个 `cmp -s` 一致；`diff -rq` 的 `Files differ = 0` |
| 10 | `grep -rn "/ -->"` 零残留 | ✅ 交付内容 = 0（仅 `tools/` 断言与 `docs/*.md` 命中，属豁免域） |
| 11 | 掩码 sha256 对比 | ✅ **11 个非剂型页逐字节全同**；8 个剂型页按设计变化（见 §6） |
| 12 | 桌面 1440 + 移动 375 截图交付 | ✅ 22 张（8 页桌面 Hero + 表 ×2，3 页移动 Hero + 表 ×2） |
| 13 | 5 条交互路径实测 | ⏸ 折叠/展开/深链属阶段 2；TOC 与配方跳转已验 |

**零回归的硬证据**：8 页 `.configurator` 高度与「改动前」扫描基线**逐页差 0**，
`.sf-formulas` 高度也**逐页差 0**。

---

## 6. 掩码回归：改动被严格关在 8 页里

掩码规则沿用 2.4.5 基线那套（GF 加密隐藏域 / 电话字段 id / `nonce=` / `config_nonce`），
并已处理 **WP nonce 的 12h tick**（2.4.5 基线在 07:56 = tick 41432，本次 09:2x = tick 41433，
边界恰为 UTC 00:00 = CST 08:00；加掩码后 11 个非剂型页逐字节全同，反证掩码集合完备）。

| 组 | 页数 | 结果 |
|---|---|---|
| 非剂型页（home/about/products/quality/faq/services/cooperation/contact/blog/factory-tour/feedback） | 11 | **逐字节全同** ✅ |
| 剂型页 | 8 | 变化，归一化后每页 **4–6 个变化块**，全部落在预期位置 |

逐块 diff 确认（以 liquids 为例，归一化 + 掩码后）：

| 块 | 内容 |
|---|---|
| 1 | `FAQPage` LD+JSON —— 只多了 ` New brands can start with small trial orders.` |
| 2 | 主按钮 `#inquiry-form` → `#configurator`、`Request a Quote` → `Build Custom Formula` |
| 3 | 删 `<!-- TODO: 指向 PDF Catalog… -->` |
| 4 | `Download Catalog`（`href="#"`）→ `Browse Standard Formulas`（`href="#formulas"`）+ 新增文字链 |
| 5 | 新增 `section.sf-spectable` + 整张表；`sf-formulas` 得到 `id="formulas"` |
| 6 | MOQ 段落补句 |

字节增量 +951 ~ +1,066 B/页，与上表逐项吻合。

---

## 7. 阶段 3 的 before 基线：锚点确实被遮

实测（桌面 1440，sticky header 81px，全页预滚动逼出懒加载后）：

| 目标 | 当前 `scroll-margin-top` | 落点视口 top | 判定 |
|---|---|---|---|
| `#formulas` | **0px** | **−1** | ⛔ 被 header 遮 **82px** |
| `#configurator` | **0px** | **−1** | ⛔ 被 header 遮 **82px** |
| `#inquiry-form` | 96px | 95 | ✅ 正确（原有规则） |

即：新增的两个锚点按钮目前点下去会**把目标标题顶到 header 底下**。阶段 3 按计划
桌面补 `96px`、移动端接入 `style.css:2865` 的归零规则即可闭合。

---

## 8. 两个如实报告、但不属本阶段范围的观察

1. **页脚 7 个社交图标仍是 `href="#"` 死链**（X / YouTube / WeChat / Instagram / TikTok /
   Facebook / LinkedIn，全部在 `footer p.sf-social`）。这是改动前就存在的全站问题。
   你核验项 1 说的「无死链」我按「页内容」口径达成为 0，页脚这 7 个没动 —— 要不要单独开一批。
2. **TranslatePress 浮动语言切换器**是 `position: fixed` 右下角，表格滚到底部时会在
   最后一列尾部压出约 10px 重叠（截图可见）。全站既有行为，与本批无关。

---

## 9. 文件清单

**改动**
```
sinofresh-theme/templates/page-{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}.html
sinofresh-theme/style.css                      # 新增 25c / 25d 两段
```

**新增工具**
```
tools/_b1_stage1.py            # 幂等改写脚本（含断言）
tools/_b1_stage1_verify.js     # 8 页 × 2 视口渲染核验
tools/_b1_stage1_probe.js      # 按钮换行 / 死链归属
tools/_b1_stage1_probe2.js     # 表格几何 + 锚点落点
tools/_b1_stage1_shots.js      # 截图交付
```

**未动**：`functions.php`（版本号留到阶段 3 一次性改，避免 style.css 被改两次却只升一格）、
`assets/css/configurator.css`、`assets/js/formulas.js`、`assets/js/toc-nav.js`

**证据包**：`_backup/batch1-stage1-20260920-091451/verify/`
（`stage1-geometry.json`、19 页 HTML、22 张截图、5 个脚本、`diff_rq.txt`）
