# 扫描：配方图集「每帧可独立管理」（2026-09-30）

> 只读扫描，未改动任何文件。范围：`sinofresh-theme` 主题 + `tools/`。
> 前置：H17（帧①读特色图）已于今日上线，见 `docs/h17-fix-execution-report-2026-09-30.md`。

---

## 0. 先修正一个前提：Gallery images 已经是"每条配方独立"的字段

这一条改变了整个方案的形状，必须先说。

`sf_formula_gallery_ids`（后台 **Gallery images**）**本身就是 per-post 字段**，而且从批次 H2a 起**已经参与帧序**，排在帧① 之后、车间图之前：

```
帧①（特色图 > 剂型图） > 自有照片 > 视频 > 车间图      cap 6
```

**但它从未被用过**——dev 与生产各 21 条配方，该字段**全部为空**（本轮实测，见下表）。所以"帧2-4 改不了"的准确表述是：

- ❌ 不是「没有 per-record 字段」——有，只是没人填过；
- ✅ 而是「**没有"精确占位、不留车间图"的规则**」。

推演**已实测证实**（只读：`get_post_metadata` 过滤器喂假字段值 → 调**真实** `sinofresh_formula_gallery_slots()`，不写库；自证见下）：

| Gallery images | 视频 | 实际帧序（cap 6） | 问题 |
|---|---|---|---|
| 0 张 | 无 | 剂型图、fac-placeholder、fac-packaging、fac-line（**4 帧 = 现状**） | — |
| 0 张 | 有 | 剂型图、VIDEO、fac-placeholder、fac-packaging、fac-line（5 帧） | — |
| 1 张 | 无 | 剂型图、OWN1、fac-placeholder、fac-packaging、fac-line（5 帧） | 多出 3 张车间图 |
| 2 张 | 无 | 剂型图、OWN1、OWN2、fac-placeholder、fac-packaging、fac-line（**6 帧**） | **帧④⑤⑥ 全是车间图** |
| 3 张 | 无 | 剂型图、OWN1、OWN2、OWN3、fac-placeholder、fac-packaging（**6 帧**） | 帧②③④ 已达成，**但帧⑤⑥ 冒出 2 张车间图** |
| 4 张 | 无 | 剂型图、OWN×4、fac-placeholder（6 帧） | 仍残留 1 张 |
| 5 张 | 无 | 剂型图、OWN×5（6 帧） | 车间图全部挤掉 |

⇒ 放 3 张确实能让帧②③④ 变成自有图，**但要放到 5 张才能把车间图彻底挤掉**。真正要解决的是这条：现有字段只有"`追加 + 从头数到 6`"这一种手段，**没有"这三个槽用我的图、别的不出现"的精确表达**。

**实测自证**（证明过滤器确实在拦截，而非静默失效——第一轮就踩了这个坑）：
```
SELF-PROOF readback gal = [53,96,100]     ← 注入值被读到
SELF-PROOF readback vid = []              ← 注入空串被读到
own=0 video=N  frames=4  ::  soft-chews.webp | fac-placeholder.webp | fac-packaging.webp | fac-line.webp
own=3 video=N  frames=6  ::  soft-chews.webp | OWN#blog-softchews-1024x768.webp | OWN#sino-fresh-logo-1-1024x127.png | OWN#soft-chews.webp | fac-placeholder.webp | fac-packaging.webp
```
⚠️ 第一轮实测因 `wp eval` 的闭包里用 `global` 取不到外层变量（`wp eval` 代码不在全局作用域执行），过滤器静默返回 `null` ⇒ **所有组合输出完全相同**，看起来像"字段无效果"。必须用 `$GLOBALS['…']` 显式赋值，并加 readback 自证。此坑已记入项目 memory。

⚠️ 附带观察：自有照片取 `large` 尺寸，实际像素**由所选的图决定**——实测注入一个 logo 附件后出现 `1024×127` 的帧。尺寸不匹配不会破图（服务端声明的是真实像素），但极端宽高比会在缩略图条里露出差异。

### 字段现状实测（2026-09-30）

| 字段 | dev | 生产 |
|---|---|---|
| `sf_formula_gallery_ids` | 21/21 全空 | 21/21 全空 |
| `sf_formula_video_url` | 仅 158 有值 | 仅 158 有值 |
| `_thumbnail_id` | 21/21 全空 | 仅 158 = 404（H17 代设） |

⇒ 任何改造只要"新字段全空时行为不变"，就是**逐字节零漂移**，风险与 H17 同量级。

---

## 1. 帧2-4 现在在哪硬编码

**文件：`sinofresh-theme/functions.php`，函数 `sinofresh_formula_gallery_slots()`（1788-1949）**

| 帧 | 行号 | 文件 | 声明尺寸 | alt 来源 |
|---|---|---|---|---|
| 帧② | **1814-1820** | `fac-placeholder.webp` | 1100×733 | `sprintf('%s production line at the SINO FRESH GMP facility in Linyi, China', $label)` |
| 帧③ | **1821-1827** | `fac-packaging.webp` | 800×600 | `... packing line at ...` |
| 帧④ | **1828-1834** | `fac-line.webp` | 800×600 | `... moving along the tray line inside ...` |

配套链路：

- **URL 解析** `sinofresh_formula_gallery_file_url()`（**1720-1740**）：对 uploads 做 `glob('*/*/' . $filename)`，同名取最新月份目录。**文件名即唯一契约，全站共用同一批文件。**
- **帧①** `1799-1813`：`<剂型>.webp`，URL 走 `sinofresh_formula_card_image()`（**685-718**）；**已被 H17 覆盖**——特色图有值时接管（**1855-1889**）。
- **H2a 重排**（**1855-1937**）：`$head = array_slice($slots,0,1)`、`$facility = array_slice($slots,1)`，再 `merge(head, own, video, facility)` 切前 6。
- **出口过滤**（**1939-1948**）：URL 为空的槽被丢弃（不渲染破图）。

**逐条硬编码、无后台入口、8 剂型 21 配方共用同一组文件** —— 与你的描述一致。

---

## 2. Gallery images 字段现在的实现

| 层 | 位置 | 说明 |
|---|---|---|
| meta 注册 | `inc/formula-admin.php:28` | 描述写 "JSON array"，**实际存 CSV**（见下） |
| 字段规格 | `inc/formula-admin.php:94` | `type => 'gallery'`、`req => 1`（**警告级**，非必填）、`group => media` |
| hint 文案 | 同上 | `图集：可选。主图不用这里设——用编辑器右侧的特色图片面板。` |
| 后台渲染 | `inc/formula-admin.php:444-454` | `<input type="hidden" class="sf-mb__gallery-ids">` + `.sf-mb__gallery-preview`（缩略图）+ `Choose / update images` / `Remove all` |
| 保存 | `inc/formula-admin.php:579-582` | `absint` 逐项过滤 → `implode(',')` → `sf_mb_store()`；**空值即 `delete_post_meta`**（643-650） |
| 后台 JS | `assets/admin/sf-mb-tables.js:63-100` | `wp.media` 多选（`multiple: true`），取 `thumbnail` 尺寸做预览 |
| 前台读取 | `functions.php:1891-1913` | `explode(',')` → 逐 ID 取 **`large`** 尺寸 → 生成 slot（宽高取实际像素，alt 取附件 alt，空则回退模板句） |
| 样式 | `assets/admin/sf-mb.css:13-14` | 预览缩略图 + Remove all 红色 |

**存储格式实为逗号分隔 ID 串**（`implode(',', $ids)`），注册描述里的 "JSON array" 是**描述不准**，非 bug——但若新增字段沿用此模式，描述要写对。

---

## 3. 改成"每条配方独立"要动哪几处

取决于方案（见第 6 节）。**共用底座**（三个方案都要动）：

| # | 文件 | 位置 | 改动 |
|---|---|---|---|
| 1 | `functions.php` | `sinofresh_formula_gallery_slots()` 1855-1937 | 帧序规则：把槽②③④ 交给 per-post 数据，车间图降级为"回落" |
| 2 | `inc/formula-admin.php` | `sf_formula_mb_fields()` 94 行附近（`media` 组） | 新增/改写字段规格 + hint |
| 3 | `inc/formula-admin.php` | `init` 的 `$keys`（26-54） | 新增 meta key 的注册与描述 |
| 4 | `inc/formula-admin.php` | 渲染分支（388-476） | 若引入新字段类型需加 `case` |
| 5 | `inc/formula-admin.php` | 保存分支（548-620） | 同上 |
| 6 | `assets/admin/sf-mb-tables.js` | 63-100 | 若单图选择器，改 `multiple: false` + 单值回填 |
| 7 | `inc/formula-admin.php` | 765-766 | 改了后台资产则 bump 其版本号 |

**不需要动**：任何 `.html` 模板、`style.css`、前台 JS（`formula-gallery.js` 只按 DOM 顺序做缩略图条，与数据来源无关）。

---

## 4. 8 个剂型页会不会受影响

**不受影响**（三条独立证据）：

1. `[sf_formula_gallery]` 短码**只在 `templates/single-sf_formula.html:42` 出现一次**；8 个 `templates/page-<剂型>.html` **0 命中**。
2. 剂型页 hero 是**纯色带（无图）**；"Explore more" 瓦片图是模板里**写死的** `uploads/2026/09/<剂型>.webp` —— 走的是模板 HTML，**不经 gallery 函数**。
3. `sinofresh_formula_gallery_slots()` 全仓只有一个调用点 `sinofresh_formula_gallery()`（**1951-1965**），非单页时传 `post_id = 0`，直接跳过 per-post 分支。

⚠️ **唯一交集**：帧① 与剂型页瓦片用的是**同一张 `<剂型>.webp` 文件**。本批不碰剂型图 ⇒ 无影响。**但如果将来有人把剂型图挪走，两边会一起坏**——这是既有的耦合，不在本批范围。

---

## 5. 版本 bump 与门更新

### 版本

| 资产 | 现值 | 本批是否 bump |
|---|---|---|
| `style.css` 头部 / `functions.php:37` enqueue | `2.10.88` | **不 bump**——不改前台 CSS/JS 资产 |
| `assets/admin/sf-mb.css`（`formula-admin.php:765`） | `1.1.0` | **仅在改了此文件时** bump |
| `assets/admin/sf-mb-tables.js`（`formula-admin.php:766`） | `1.0.0` | **仅在改了此文件时** bump（纯后台，不影响前台字节） |

### 门

- **现有常跑门全部不涉及图集**：`h9/h10/h11/h12/h13/h14` 对 `gallery|sf-gallery|fac-` **0 命中**（已用 `grep -E` 复验——注意 macOS 的 `grep` 基本正则不支持 `\|`，会静默返回空）。
- **32 个 `b2d_*` 历史工具引用图集**（`b2d_s3_browser.py:56` 的 `SLOT_FILES` 写死 4 文件、`b2d_h7_gate.py:3106-3127` 写死整段 img markup、`b2d_s2_dimensions.py` 的尺寸表断言）——皆为**历史批次 source 门，非日常跑**。只要 21 条配方的新字段全空，它们的行为**逐字节不变**。
- **需新建本批门** `tools/h18_gate.py`（照 H17 的断言模式）：
  1. **零漂移**：21 条配方（+ 多语言页）gallery section md5 前后一致；
  2. **接管**：给某条配方设帧② → 该页帧② 变为自有图，其余页不动；
  3. **负控**：`_thumbnail_id`／新字段填不存在的附件 ID → 回落车间图，md5 回基线；
  4. **不新增红**：h10/h14 `--live` 与改前一致。

---

## 6. 方案

> 以下判断均基于第 0 节的**实测帧序**（非推演）。

### 待你拍板的两点（真正的产品决策，我无法代选）

**Q1｜字段形状**

| | B1：3 个独立槽位字段 | B2：1 个图集字段（复用 Gallery images） |
|---|---|---|
| 后台形态 | Media 组里 **Frame 2 / Frame 3 / Frame 4** 三个单图选择器 | 现有那一个多选图集 |
| 语义 | 每帧一个槽，**可精确指定**（想让帧③ 保持默认、帧④ 换自己的图 ⇒ 可以） | **按顺序填充**帧②起，不能跳号 |
| 与帧① 的关系 | 对称（槽① 走特色图面板，槽②③④ 走 Media 组） | 不对称 |
| 新代码 | 需新增 `image` 字段类型（渲染 + 保存 + JS 单图选择器，约 3 处） | **零新类型**（现有 `gallery` 类型已够） |
| 零漂移 | 3 字段全空 ⇒ 与原逻辑等价 | 需改补位规则，字段空时同样等价 |
| 编辑页入口数 | 4 个图片入口（特色图 + 3 槽 + 图集） | 2 个（特色图 + 图集） |

**Q2｜车间图的兜底边界**（决定"会不会残留"）

| | F1：有自己图就不补 | F2：始终补到 4 帧 | F3：每条配方开关 |
|---|---|---|---|
| 规则 | 该配方有任意自有图 ⇒ 车间图全部不出现 | 自有图不足 4 帧基准时，车间图按序补位 | 加一个勾选框，默认补位 |
| 结果 | 页面可能只有 2 帧（只放 1 张时） | 页面**恒 ≥4 帧** | 灵活但多一个字段 |
| 与你的原话 | 部分符合 | **"没设的回落默认图（保持现有页面不空）"逐字对应** | 超需求 |

### 我的推荐：**B1 + F2**

理由：

1. **B1 与你的原话逐字对应** —— "把帧2-4 从硬编码改造成每条配方自己的字段"，就是 3 个槽位；
2. **F2 与你的约束逐字对应** —— "没设的回落默认图（保持现有页面不空）"；
3. **帧数基数不变（4 帧）** ⇒ 375px 视口的缩略图条几何、`b2d_s3_browser.py` 的断言语义、`style.css` 里跟帧数相关的规则**全都不用动**；
4. **零迁移** —— 3 个新字段全空 = 现状，可做逐字节零漂移门；
5. 与 H17（帧① 走特色图）合起来，编辑页就是一句可讲清的话：
   > **帧① 用特色图片面板，帧②③④ 用 Media 组的三个槽，留空就显示工厂默认图。**

### 备选：B2 + F1（改动最小）

只改 `sinofresh_formula_gallery_slots()` 的补位规则（约 10 行）+ 改 hint 文案 + 后台预览加槽位标签。**不需要新字段类型**。代价：不能跳号指定，且会**改变现有字段语义**（own 从"追加"变"替代"）——虽然 21 条全空、无人受影响，但语义漂移会在半年后让人困惑。

### 实施步骤（确认后执行，约 8 步）

1. 本地改 `functions.php`（帧序规则，注释标 `Batch H18`）
2. 本地改 `inc/formula-admin.php`（字段规格 + meta 注册 + 渲染/保存分支）
3. 若需单图控件：改 `assets/admin/sf-mb-tables.js` + bump `1.0.0 → 1.1.0`
4. `php -l` 本地/dev 双侧
5. **dev 验证**：21 条零漂移 → 设帧②接管 → 负控回落 → 后台真会话端到端（含清空槽位）
6. 新建 `tools/h18_gate.py` 并跑（`--source` / `--live`）
7. 显式部署生产（备份 → `php -l` → md5 核对 → 原子 `mv` → `apache:apache 644`）
8. 生产验收 + 截图 + 报告

### 验收标准（三条）

1. 给某条配方设帧②③④ → 该页**只有这三个槽变**，其余配方页逐字节不变；
2. 3 个槽留空 → 该页与今日**逐字节一致**（含 158 的 5 帧）；
3. 8 个剂型页 + 首页 + 归档页 + 多语言页**零影响**。

---

## 7. 顺带发现（不在本批范围，供参考）

1. **`sf_formula_gallery_ids` 的注册描述写 "JSON array"，实际存 CSV** —— 描述不准，会误导后来的开发者。建议随手改对。
2. **帧①（特色图）与配方详情页 Product JSON-LD 的 `image` 不一致** —— JSON-LD 仍取剂型图（`functions.php:7013`）。H17 遗留项，建议与本批合并或紧接一批。
3. **帧② 的 `fac-placeholder.webp` 与 `hero-facility.webp` 内容相同**（`docs/redundancy-audit-2026-09-20.md` 已记），且 placeholder 是 1100×733 而另两张是 800×600 —— **帧② 与帧③④ 的纵横比不同**（1.50 vs 1.33）。如果本批要"每帧一张自己的图"，这个比例不一致会在同一页里露出来，建议一并决定是否统一。
