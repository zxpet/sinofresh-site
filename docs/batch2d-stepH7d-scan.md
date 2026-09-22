# 批次 H7d —— 右栏 7 个参数改交互控件（**进行中**：步 1 已提交并验证）

**状态**：**未完成**。`09cdf80` 已提交并推送（步 1：PHP 提供器 ＋ 交互带 ＋ 端到端校验 ＋ config.js ＋ CSS ＋ 两处令牌）。
**门未跑、E2E 未跑、批次档未写**。本档是**扫描 ＋ 决策 ＋ 已验证事实 ＋ 剩余清单**，供下一步继续。

**基线**：`e4c2dd9`（H7c 收尾，`2.10.64`）。
**令牌**：`2.10.64 → 2.10.65`（两处同步）＋ `inquiry.js 1.1.0 → 1.2.0` ＋ `config.js 1.0.0`（新）。
**预检副本现＝ `09cdf80`（`2.10.65`）**；`functions.php` sha256 `14bbc2cf…`、`style.css` sha256 `9191911d…`。

---

## 0. 扫描：手册说的 7 个控件，数据实际长什么样

这是本批最重要的一页。用户手册的 7 个控件按**实测数据**排开：

| 控件 | 类型 | **实际渲染页数** | 来源 |
|---|---|---|---|
| Flavor | ☐ 多 | **2**（1 条记录 × EN/ZH） | `sf_formula_flavors` |
| Piece Weight | ○ 单 | **42** | `specs` 的 unit 段 |
| Pack Size | ☐ 多 | **20**（10 条记录） | `specs` 的 `… per …` 段 |
| Suitable For | ☐ 多 | **0** | `sf_formula_species` —— **该 meta 键全站不存在** |
| Life Stage | ○ 单 | **0** | `sf_formula_lifestage` —— **该 meta 键全站不存在** |
| Container Type | ○ 单选图 | **2** | `sf_formula_container`（1 条）＋ 全局容器库 7 项 |
| Quantity & Pricing | ○ 单（显单价） | **2** | `sf_formula_price_tiers`（1 条） |

**结论**：42 个详情页里，**40 页只有 1–2 个控件**（Piece Weight，有时加 Pack Size）；7 个控件齐全的只有 **2 页**，
而那 2 页正是 post 158（`joint-support-soft-chews`）—— 已知带**测试占位内容**的记录。

⛔ **因此本批必须按「数据到了控件就出现」来验收**，不能按「7 个控件都活着」验收。这与 H7c 的立场一致
（销售填一个字段，那一行就出现，不需要部署）。

### 0.1 右栏今天的样子（42 页实测，H7c 候选态）

| 行数 | 页数 |
|---|---|
| 5 行 | 22 |
| 6 行 | 18 |
| 8 行 | 2（post 158 × EN/ZH） |

标签出现页数：Piece Weight／Shelf life／Packaging／Certifications／Lead time 各 **42**；Pack Size **20**；
Flavor／Quantity & Pricing 各 **2**；Suitable For／Life Stage／Container Type 各 **0**。

### 0.2 容器库：有图，但一页都还没有

`sf_container_library()`（`inc/formula-admin.php:531`）的每一项**本来就带 `attachment_id`**，
后台有 Site Settings → Container Library 子页，用 `wp.media` 选图。

**实测**：`sf_containers` 这个 option **在 dev 上不存在** → 走 `sf_default_containers()` 的 7 项，
而 7 项的 `attachment_id` **全是 0**。所以：

- 今天**没有任何容器图片**；
- 本批**不为此改数据**（改数据是停机条件）；
- 实现方式：有图用 `<img>`，无图退化为**虚线槽 ＋ 标签**。管理员上传图片的那天，选择器自己就有图了。

### 0.3 一个值有两个载体（本批登记，不修）

Container Type 控件读 `sf_formula_container`，而**同一事实**在内容区的
"Packaging & Specifications → Container Options" 里**已经有一个 chip**（`functions.php:2463`）。
本批**不动内容区**（手册没要求），因此该值在 post 158 的页面上会出现在两处。
登记为未来批候选：「容器事实的两个载体」——要么内容区那行去掉，要么控件改为从内容区那行读。

---

## 1. 步 1 已实现（`09cdf80`，5 文件 ＋860/−45）

### 1.1 一个提供器，三个读者

`sinofresh_formula_config_groups($post_id)` 返回 7 组的**唯一真源**：组键／标签／`meta`（记录自己的值）／
type（multi/single）／style（chips/image/tiers）／选项（value＋label＋image＋note）。三个读者：

1. **交互带渲染器** `[sf_formula_config]`；
2. **端点**用它判定「post 上来的值是不是这条记录真的提供的值」；
3. 两处**同一套标签** —— 这是它们不可能对「Chicken 叫什么」产生分歧的唯一安排。

### 1.2 右栏被劈成两半，劈线是读者能选／不能选

7 行**能选**的进了 `[sf_formula_config]`；**不能选**的 4 行（Shelf life／Packaging／Certifications／Lead time）
留在 `[sf_formula_params]`。所以本批**加了一个渲染器，同时让另一个渲染器少了 6 行** ——
不这么劈，这 6 个值会在同一页上出现两次。

`inquiry.js` 的悬浮胶囊**揭示锚点**随之改成 `.sf-fdetail-config, .sf-fdetail2__params`
（哪个先渲染就看哪个；两者都没有时走原有的「立即显示」分支）。

### 1.3 端点的老规则，换成能扛住「客户真的选了」的形式

老规则：「选择面板从 post id 重建，**绝不**来自请求体 —— 客户端的副本是渲染结果，而发帖客户端可以往里塞任何东西。」

本批保留这条规则**在它能成立的形式里**：**请求说「选了哪些」，服务器说「它们叫什么」**。
凡不在该记录选项值集合里的 post 值一律丢弃 ⇒ 手写请求最多只能在页面已提供的选项里挑，拿不到任何额外东西。

端点因此多一个 `config` 字段（JSON）；**空 = 什么都没勾** ⇒ 退回记录自己的值（＝本批之前的行为，换个路径到达）。
邮件里那一段的标题随之区分：`Selection (chosen by the customer):` 还是 `Specification:` ——
销售要能分清「客户提的要求」和「产品本来就这样」。

### 1.4 「记录自己的值」永远印在控件上方（`__meta`）

每组的 `__meta` 是无条件印出的**纯文本**。这一行做三件事：

1. **无 JS 的答案**（脚本没到，事实一个也不丢）；
2. **弹窗的回退**（什么都没勾时，弹窗显示的就是它）；
3. 让选项读起来像「在答案旁边的可选项」，而不是「一个不知道答案的表单」。

**没有任何预勾选**：没勾就没 post，邮件带的是记录自己的值。

### 1.5 Pack Size 真的需要切分

`"60/90/120 per bottle"` 是**一个**发布字符串描述**三个**规格。`sinofresh_formula_pack_parts()`
**在接线之前先对数据库里真实存在的形状做单元测试**（8/8）：

| 输入 | 选项 | 尾巴 |
|---|---|---|
| `60/90/120 per bottle` | 60 \| 90 \| 120 | per bottle |
| `60/120/180 per bottle` | 60 \| 120 \| 180 | per bottle |
| `14/28/56 per bag` | 14 \| 28 \| 56 | per bag |
| `7/14/28 per bag` | 7 \| 14 \| 28 | per bag |
| `1 kg bag` | `1 kg bag`（一个选项） | — |
| `2g/piece` | `2g/piece` | — |
| `4oz/8oz/16oz jar` | `4oz/8oz/16oz jar` | — |
| `""` | — | — |

尾巴**只印一次**（组上），不重复在每个选项里；并且**跟着选择进邮件**，否则销售收到「60, 90」没有单位。

### 1.6 服务端逻辑实测（临时 mu-plugin 探针，post 158，已删、DB 零留痕）

```
groups: flavor(7) weight(1) pack(3) container(7) pricing(1)
  container meta = "Round"                  ← 记录自己的 slug → 库标签
  pricing   meta = "200 — USD 2.5 / unit"   ← 单价随数量一起印

case full    {Flavor:"Chicken, Beef", Piece Weight:"2g/piece", Pack Size:"60, 90 per bottle"}
case single  {Quantity & Pricing:"200 (USD 2.5 / unit)"}
case foreign []                                   ← SALMON XL / 9999 / nope 全部被丢弃
case mixed   {Flavor:"Chicken", Container Type:"Pouch"}   ← 非法的丢、合法的留
case empty   []
fallback     {Flavor: 7 项, Piece Weight, Pack Size 原串, Quantity & Pricing:"200 — 2.5"}
```

`case mixed` 是**最关键的一条**：同一个字段里混进非法值时，丢弃是**按值**发生的，
而不是整组接受或整组拒绝。

### 1.7 渲染实测（dev 预检态，`2.10.65`）

| 页 | 组 | 选项数 | `sf-fdetail2__params` 行 |
|---|---|---|---|
| `joint-support-soft-chews`（post 158） | flavor, weight, pack, container, pricing = **5** | 19 | Shelf life／Packaging／Certifications／Lead time |
| `calming-soft-chews`（常规） | weight, pack = **2** | 4 | 同上 4 行 |

与第 0 节的预测**逐项吻合**（Suitable For / Life Stage 无数据所以不出现）。

### 1.8 前端三件事（`config.js`）

1. **实时摘要**：`[data-sf-config-summary]` 以 **空且 hidden** 发出 —— 无 JS 的页面不对「还没发生的选择」作任何声称；
2. **进弹窗的通道**：把选择写成 JSON 塞进隐藏 `config` 字段，并**同步改写弹窗里的面板**，
   让客户看到的就是销售收到的；没勾时**一个字都不动**，面板保持服务端渲染的产品规格；
3. **手机全屏抽屉**：7 组胶囊内联会把价格和 CTA 顶出前两屏，所以 ≤768 变成抽屉。
   **按钮由脚本创建** ⇒ 没有脚本的人永远看不到一个打不开的按钮；`:has()` 只用于**形状**（圆/方），
   不支持的浏览器退化成方框但仍然可勾。

---

## 2. 步 1 暴露的两个事实（登记）

1. **`sinofresh_formula_chip_list()` 成了孤儿**：它的两个调用点（Flavor／Suitable For 的 chip 行）
   都在本批进了控件带。**保留不删**并按本档登记 —— 删它属于「死代码清理」家族的活，本批手册没要求，
   而它对页面字节零影响（门看不见，所以更不该顺手改）。
2. **6 条记录的 Piece Weight 是「尺寸清单」而不是单个值**：`4oz/8oz/16oz jar`、`50g/60g/100g/120g tube`、
   `30ml/50ml dropper bottle` 这一形状的 `specs` **没有 ` per ` 段**，解析器于是把整串放进 `unit`，
   `pack` 为空 ⇒ 这些页**没有 Pack Size 控件**，而 Piece Weight 是「一个选项、值是一串清单」。
   这是**发布数据的形状**，不是渲染缺陷；要不要把这类清单拆成可选项，属于数据/口径裁决（登记）。
3. **post 158 的测试占位值现在多了一个出口**：`sf_formula_price_tiers = [{"qty":"200","price":"2.5"}]`
   是已知测试值，本批让它会出现在**控件、弹窗、以及发给 `sales@zxpet.com` 的询盘邮件**里。
   这是用户既有待办（「上线前须清一处内容」）的一个新增暴露面，**本批不改数据**，登记在此。

---

## 3. 剩余工作（H7d 尚未完成的部分）

1. **门**：H7d 的 `BATCHES['h7d']` 声明（`mode: delete` 或新方向）、基线／候选抓取、A/A、覆盖、不变式、
   `scoped`／`order`、破坏矩阵、具名负对照。**注意本批同时删行（6 行离开 params）与加块（config 带）**，
   所以主证方向需要重新想：`transform` 要同时处理「删掉新块」和「把删掉的 6 行放回基线」两件事。
2. **限定证明**：`b2d_h7c_confine.py` 已参数化，用
   `--ns .sf-fdetail-config` `--expect-php sinofresh_formula_config` `--tpl-line '[sf_formula_config]'`。
3. **浏览器 E2E**：勾选 → 摘要实时更新 → 打开弹窗面板同步 → 抽屉开合 → **不提交**（避免真发邮件到
   `sales@zxpet.com`）；提交路径的服务端逻辑已由第 1.6 节单测覆盖，端点鉴权／反垃圾由 H4 批已验证。
4. **截图 ＋ 非平帧断言**（桌面／手机／抽屉两态）。
5. **批次档 `docs/batch2d-stepH7d.md`**。

---

## 4. 与手册的差异（供裁决）

手册说「右栏 7 个参数变成交互控件」。实测下 3 个控件（Suitable For／Life Stage）**没有数据源**，
2 个（Flavor／Container Type／Pricing 中的 3 个）只有 1 条记录有数据，而那条记录带测试占位内容。
本批按「数据驱动、数据到了就出现」实现，**不改数据、不补数据**。
如果期望是「7 个控件都活着」，那需要先做一次**数据填充**（`sf_formula_species`、`sf_formula_lifestage`
两个键目前全站不存在），那是需要授权的数据变更。
