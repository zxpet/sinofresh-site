# 批 H1 实施方案 —— 配方详情页后台发布模板（含认证配置补三处）

> 状态：**待确认，未动手**。工作树停在 `b28d4cd`（批 C 修正版）。
> 决策依据：H1 扫描报告 + 用户三项拍板（必填清单 18+7、认证复用 Site Settings、配置器删除拆 H2）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 〇、总原则与批次拆分

- **H1a（后台 + 数据）**：meta box ×6、admin 资产、服务器验证、迁移脚本、三个全局配置的后台部分。**前端 75 页字节零变化**。
- **H1b（认证四触点）**：Site Settings 增删行、剂型页 hero 副标题改读 option、详情页认证行改读 option、Organization Schema 补 `hasCredential`。**前端字节变化 = 仅 schema 一处对象**（默认值与现硬编码逐字相等 ⇒ hero/factsheet 渲染逐字节不变）。
- H1a、H1b 各自过门；H1b 在 H1a 之后（同一批交付，两个门）。
- 配置器（8 剂型页区块 + configurator.css/js + enqueue）**本批不碰**（H2 处理，CTA 改指 /contact/）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 一、Meta box 设计（6 组）

全部走原生 `add_meta_box`（context=normal），仅在 `post.php`/`post-new.php` 的 `sf_formula` 屏注册与入队。古腾堡编辑器保留（标题/特色图/分类法仍用编辑器面板），`post_content` 区不使用（21 条全空，前台 `[sf_formula_body]` 空带契约不变）。

### 组 1 基础（sf-mb-basics）
| 字段 | key | 控件 | 级别 |
|---|---|---|---|
| 标题 | `post_title` | 编辑器原生 | **阻断** |
| 简介 | `sf_formula_intro` | textarea 4 行 | **阻断** |

注：`sf_formula_intro` 此前**故意未注册**（走自定义字段面板）。本批正式 `register_post_meta`（string/single/show_in_rest + auth_callback），面板路由继续可用，meta box 成为主编辑口。

### 组 2 媒体（sf-mb-media）
| 字段 | key | 控件 | 级别 |
|---|---|---|---|
| 主图 | `_thumbnail_id` | **编辑器原生特色图面板**（已支持，验证层检查） | **阻断** |
| 图库 | `sf_formula_gallery_ids` | 媒体库多选（wp.media，WP 自带） | 警告 |
| YouTube | `sf_formula_video_url` | url 输入（`esc_url_raw`） | 警告 |

### 组 3 右栏参数（sf-mb-params）
| 字段 | key | 控件 | 选项池 | 级别 |
|---|---|---|---|---|
| 口味 | `sf_formula_flavors` | checkbox 多选 | **按剂型**（配置器 flavor 组） | **阻断** |
| 单粒克重 | `sf_formula_weight` | radio | **按剂型**（weight/weight_per_piece/serving_size 组） | **阻断** |
| 装量 | `sf_formula_counts` | checkbox 多选 | **按剂型**（count/net_weight/tube_weight 组） | **阻断** |
| 形状 | `sf_formula_shape` | radio | **按剂型**（shape/texture/appearance/form 组），标签随剂型变 | **阻断** |
| 适用宠物 | `sf_formula_species` | checkbox 多选 | Dog / Cat（固定池） | **阻断** |
| 适用阶段 | `sf_formula_lifestage` | radio | Puppy / Kitten / Adult / Senior / All Life Stages | **阻断** |
| 阶梯价格 | `sf_formula_price_tiers` | 可重复表格 | — | **阻断**（≥1 行且两列非空） |

**剂型→配置器组映射表**（选项值逐字取自扫描记录，PHP 函数 `sf_formula_field_pool($form, $dim)` 单一来源）：

| 剂型 | 形状组 | 克重组 | 装量组 | 口味组 |
|---|---|---|---|---|
| soft-chews | shape(8) | weight(9) | count(9) | flavor(13) |
| tablets | shape(5) | weight(6) | count(5) | flavor(6) |
| dental-chews | shape(6) | weight_per_piece(6) | count(5) | flavor(7) |
| pastes | texture(4) | tube_weight(6) | tube_weight(6) | flavor(6) |
| powders | appearance(4) | serving_size(5) | net_weight(5) | flavor(6) |
| drops | appearance(4) | bottle_size(5) | bottle_size(5) | flavor(6) |
| liquids | appearance(4) | bottle_size(6) | bottle_size(6) | flavor(6) |
| fish-oil | form(4) | omega3 规格（functions 组 200–1000mg 段） | count(5) | —（source 组代口味位，标注“来源”） |

（pastes/drops/liquids/fish-oil 四组“形状/克重/装量”是**同组复用**，标签注明剂型词，如 pastes 显示 Texture。此映射是方案内拍板点，确认后冻结。）

### 组 4 详细内容（sf-mb-detail）
| 字段 | key | 控件 | 级别 |
|---|---|---|---|
| 成分 | `sf_formula_ingredients` | textarea（已有值预填） | **阻断** |
| 保证值 | `sf_formula_analysis` | textarea（已有值预填） | **阻断** |
| 配方说明 | `sf_formula_specs` | textarea（已有值预填） | **阻断** |
| Recommended For | `sf_formula_recommended_for` | textarea | **阻断** |
| Use Cases | `sf_formula_use_cases` | textarea | **阻断** |
| Who It's For | `sf_formula_who_for` | textarea | **阻断** |

### 组 5 包装（sf-mb-packaging）
| 字段 | key | 控件 | 级别 |
|---|---|---|---|
| 附加包装 | `sf_formula_packaging_extra` | checkbox 多选（剂型 packaging 组） | 警告 |
| 颜色 | `sf_formula_colors` | checkbox 多选（剂型 color 组） | 警告 |
| 保质期 | `sf_formula_shelf_life` | text | **阻断** |
| 纸箱尺寸 | `sf_formula_cartons` | 可重复表格（装量/装箱数/尺寸 cm 三列） | 警告 |

### 组 6 FAQ 与交付（sf-mb-faq）
| 字段 | key | 控件 | 级别 |
|---|---|---|---|
| Lead time | `sf_formula_lead_time` | text（迁移值预填） | 警告 |
| Container Type | `sf_formula_container` | radio（选项读 `sf_containers` 全局库） | **阻断** |
| 产品 FAQ | `sf_formula_faq_data` | 可重复表格（Q/A 两列），新建预填 9 条 | 警告 |

**存储格式**：标量＝单值 string；多选＝JSON 字符串数组；两张表＝JSON 对象数组，各占一个 key（`wp_json_encode` 落库，读出 `json_decode`）。全部 `register_post_meta`（type=string, single, show_in_rest, auth_callback=edit_posts）——不注册进 REST 结构化字段，仅元数据路由。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 二、三个全局配置

### 配置1 认证（复用 Site Settings，不新建菜单）
现况：`sf_certifications`（name/url/active ×固定 8 槽）已在 Site Settings；`{{sf-certifications}}` token 只在 header 顶部栏消费。四项补齐：
1. **增删行**：sanitize 从固定 8 槽改循环处理（shape 不变，向后兼容），「Add row」按钮 + 删行（原生 JS，admin 侧）；
2. **剂型页 hero 副标题**：新增 token `{{sf-certifications-line}}`（active 项逗号连接），8 个 `page-*.html` 副标题中的认证段替换为该 token。默认值与现硬编码逐字相等 ⇒ 渲染字节不变；
3. **详情页认证行**：`sf_formula_factsheet()` 与批 C FAQ 生成器的 Certifications 值改为「先读 option（join），option 为空回退 `spec_cell()`」——值相等 ⇒ 字节不变；
4. **Organization Schema**：`hasCredential` = active 认证名数组（`wp_json_encode`，所有页面 head 唯一新增字段）。

### 配置2 瓶型（Site Settings 子页，新建）
- `add_submenu_page('sf-site-settings', 'Container Library', …)`，option `sf_containers`：`[{slug,label,attachment_id}]`，预置 7 项 Round/Square/Oval/Jar/Pouch/Tube/Custom；
- 图片走**媒体库**（wp.media 选择器，上传后自动有 attachment 记录与 `_wp_attachment_image_alt` 落点）；400×400 1:1 用固定尺寸约束 + CSS `object-fit:cover` 裁切，方案 A（图下文字标签）；
- 前台消费（详情页 Container Type radio 池 + H2 后的展示区）本批只出数据，不改展示。

### 配置3 全局 FAQ（Site Settings 子页，新建）
- 子页 `sf-global-faq`，option `sf_global_faq`：`[{q,a}]` JSON；
- 编辑界面与产品 FAQ 表格同一套可重复行 JS；
- 前台渲染顺序＝产品 FAQ → 全局 FAQ（本批只存数据；消费端在 H1b 的 FAQ 生成器加一段全局追加——**注意**：这会让 42 个详情页新增 FAQ 条目 ⇒ 属前端字节变化，归入 H1b 门内，DIFF 集合相应扩大为 42 页 +FAQPage/手风琴）。
  ——若想把 H1b 前端影响压到最小，全局 FAQ 的前台追加可推迟到 H2，本批只建菜单与数据。**方案取后者（默认只建后台），待确认。**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 三、服务器端强制验证

```
REQUIRED_SPEC（18）: title / intro / thumbnail / flavors / weight / counts /
  shape / species / lifestage / price_tiers / ingredients / analysis /
  specs / recommended_for / use_cases / who_for / shelf_life / container
WARNING_SPEC（7）: gallery / video_url / packaging_extra / colors /
  cartons / lead_time / faq_data
```

- `sf_formula_missing_required($post)`：单一规格表驱动，返回缺失中文名数组。
- **经典路径硬拦**：`save_post_sf_formula` —— 仅当「新状态或旧状态 = publish」时校验；缺失即 `wp_die('<ul>缺失清单</ul>', …, ['back_link'=>true])`。草稿/待审不拦。
- **REST 路径硬拦**：`rest_pre_insert_sf_formula` 返回 `WP_Error`（拦 API/应用密码对已发布文的改动；meta box 数据不走此路，双保险而已）。
- **后台 JS 预检（不阻断，只提示）**：`assets/admin/sf-mb-precheck.js`（原生 JS ~100 行）——发布按钮点击时读取 meta box 表单 DOM，缺失时用 `wp.data` notices（WP 自带 store，不算引库）弹警告清单；无 `wp.data` 时退化为 meta box 顶部横幅。真正的拦截始终在服务端。
- **分期上线（拍板点）**：迁移后 21 条已发布文的 species/lifestage/price/container 等无历史数据 ⇒ 若立即硬拦，运营第一次编辑旧文就会被卡。建议：**第一期只挂警告清单（编辑页顶部横幅 + 补录进度）；运营补录完成后第二期切硬拦**。若你要一步到位硬拦，迁移时需给 21 条预填占位值（物种=Both、阶段=All Life Stages、价格表=1 行占位）——不推荐，占位假数据会直接上前台。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 四、三个可重复表格（原生 meta box）

- 共用 `assets/admin/sf-mb-tables.js`（原生 JS ~160 行）：行模板 `<template>` 克隆、增/删/上移/下移、`name="sf_price[0][qty]"` 数组式提交、删除前确认；
- 共用 `assets/admin/sf-mb.css`（~120 行，admin 专用，与前台 style.css 完全隔离，**不 bump 前台版本号**）；
- 存储：`sf_formula_price_tiers` / `sf_formula_cartons` / `sf_formula_faq_data` 各一份 JSON；
- sanitize：逐行 `sanitize_text_field`，数值列 `is_numeric` 校验，FAQ 答案允许 `<a href>`（`wp_kses` 白名单），存前 `wp_json_encode`、读后逐字段转义；
- nonce：每表一个 `sf_mb_<key>_nonce`。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 五、FAQ 预设

- 新建 `sf_formula` 且 `sf_formula_faq_data` 不存在时（`wp_insert_post` 首次 + `save_post` 判空），注入批 C 的 9 条标准问题；
- 答案预填策略（拍板点）：**默认 A 全部留空**（运营填）；可选项＝把批 C 7 条固定文案预填、仅留 Certifications/Packaging 两条空。默认取「全空」，避免旧文案固化后无人复核；
- 全局 FAQ（option）与产品 FAQ（meta）**分开存储、分开编辑**，前台顺序产品在前；
- 数量不限：表格可加任意行；答案支持 `<a>` 链接（wp_kses 白名单），其余纯文本。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 六、数据迁移（21 条）

工具：`tools/b2d_h_migrate.php`（`wp eval-file` 执行）+ `tools/b2d_h_migrate.py`（本地编排：备份 → dry-run → apply → 核验）。

1. **备份**：`mysqldump sinofresh wp_postmeta wp_posts --where` 导出 sf_formula 相关行至 `_backup/b2d-h-migrate/`（含行数校验）；
2. **dry-run**：打印 21 × 新 key 的拟写入值表，人工过目；
3. **写入**（来源→去向）：
   - `sf_formula_specs`（已有）→ 拆出 unit/shelf（现有 key 正则解析器复刻）→ `sf_formula_shelf_life`；
   - 8 份剂型 facts-mini 的 **Lead time**（全同）/ **MOQ**（剂型级）→ 每条配方的 `sf_formula_lead_time`（MOQ 不单设字段，暂留剂型页；H2 再定）；
   - 批 C 9 条 Q（+3 条定稿 A 原文）→ `sf_formula_faq_data` 初值；
   - 现渲染 intro 段落（从 75 页捕获抽 21 条）→ `sf_formula_intro`（补足阻断项，避免旧文一编辑就缺简介）；
   - ingredients/analysis/specs 原值不动，仅被表单读取；
   - species/lifestage/price/container/图库等**留空**（无历史数据，不做假值）；
   - 每条 `sf_formula_source` 追加迁移批注（沿用既有惯例）；
4. **核验**：apply 后 SQL 断言（key 计数、JSON 可解码、值抽检逐字），输出核验报告；
5. 前台不读任何新 key ⇒ 迁移前后 75 页捕获必须逐字节相同（这就是 H1a 的主门）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 七、Step 0–6 执行计划

| Step | 内容 | 关键判据 |
|---|---|---|
| **0a** | H1a 门先行：`tools/b2d_h_confine.py` —— 合成候选=「仅 DB 迁移 + 后台代码」，75 页捕获**逐字节 identical**；门含：掩码 75/75 identical、functions.php/新 admin 资产 cut-rebuild 还原、迁移 SQL 断言集 | 正向 PASS；**负对照**：把门指向 H1b 捕获（schema 变了）必须 FAIL；破坏矩阵（stray-byte / 少一个 meta 断言 / JSON 坏值）全 FAIL |
| **0b** | H1b 合成候选：从基线捕获独立第二实现造「hero 换 token / factsheet 换源 / 75 页 Organization +hasCredential」的合成字节，跑 H1b 门 | DIFF 集 = 恰 75 页且每页恰一个 JSON-LD 对象变化（Organization gains hasCredential，其余 deep-equal）、hero/factsheet 字节不变；负对照（改认证名 / 删对象 / 多对象变化）必须 FAIL |
| **1** | 写源码：functions.php（register_post_meta 扩展、6 个 add_meta_box、pool 函数、验证双钩子、schema hasCredential、token `{{sf-certifications-line}}`）、8 剂型模板副标题行、admin 资产 3 新文件（css/tables.js/precheck.js）、Site Settings 增删行 + 两个子页 | `php -l` 过；**`b2d_c_php_scope.php` 全 TOPLEVEL**（批 C 教训，块必须落两个顶层函数之间）；style.css 逐字节不动、前台 enqueue 版本号全不动 |
| **2** | 本地核验：diff 人工复核、锚点自撤销证明（沿用 apply 工具模式）、新资产 hash 对照 | 三方 cmp（work-base / src-new / 工作树） |
| **3** | 迁移：备份 → dry-run（贴拟写入表给你看）→ **停一次等确认** → apply → SQL 核验 | 备份行数一致；核验报告 0 缺口 |
| **4** | 预检：fetch → install 40 位 SHA → `X-SF-Preflight: 1` 抓 75 页 → 跑 0a/0b 两道门 + 负对照 | 六门全 PASS、负对照全 FAIL |
| **5** | E2E（浏览器，带凭据）：管理端——缺必项发布被拦（wp_die 清单截图）、补齐后发布成功、FAQ 预填 9 条、三表增删行、Site Settings 认证加行、瓶型选图、全局 FAQ 子页；前端——75 页掩码逐字节一致、预检与 live 一致；0 JS 报错；截图入 docs/batchH1-shots/ | E2E 全绿 + 前端 75/75 identical |
| **6** | 上线八步闭环（等你确认后）：pull --ff-only → 服务侧验证 → live 掩码 75/75 → live E2E → 拆预检零残留 → 日志归因（含 2D-E fatal `--allow`）→ 身份链 + 仓库 md5 → 文档与记忆同步 | 全部既有闭环判据 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 需要你确认的 4 个拍板点

1. **剂型→配置器组映射表**（第一节）：pastes 的 Texture 当形状、powders 的 net_weight 当装量、fish-oil 无口味（用 source 组标注“来源”）——按表冻结？
2. **验证分期**：第一期只警告、补录完再切硬拦（我的建议）；还是一步硬拦 + 占位假值？
3. **FAQ 预填**：9 条只给问题、答案全空（默认）；还是 7 条固定文案预填答案？
4. **全局 FAQ 前台追加**：H1b 只建后台菜单与数据（我的建议，前端门最小）；前台追加放 H2？
