# 执行手册（agent-playbook）：H2b → H6

> **来源**：用户 2026-09-22 上传的 docx《任务：建立完整设计说明书与执行手册（详细版）》，逐字落盘。
> **性质**：用户授权 WorkBuddy 从 H2b 起到 H6 完成**自动执行**；用户只在「必须停」的 3 类情况被打扰。
> **配套**：`MEMORY.md`（摘要 + 指针）、`docs/RULES-sinofresh.md`（深度规则细则 A–P）。
> **进度区**在文末「附录 B」，每批收尾时更新。

```
用户授权：从 H2b 开始，一直到 H6 完成，WorkBuddy 按本手册自动执行。
用户只会在"必须停"的 3 类情况收到打扰。
```

---

## 第一部分：项目背景

### 【公司】

中鲜宠食（SINO FRESH），山东临沂，宠物营养补充剂 OEM/ODM 工厂。
服务欧美 B2B 品牌方，出口 30+ 国家。
认证：FDA / cGMP / ISO 9001 / FSSC 22000 / HACCP / BRC。

### 【网站】

- 域名：zxpet.com（生产）
- dev：dev.zxpet.com（开发）
- 技术：WordPress 块主题 sinofresh-theme
- 数据库：MariaDB
- 服务器：Apache 2.4.62 + PHP 8.3
- CDN：Cloudflare
- 多语言：TranslatePress（/zh/ 前缀）

### 【页面类型】

**一、剂型页（8个）**
- URL：`/products/{slug}/`
- slug：soft-chews / tablets / powders / pastes / drops / liquids / fish-oil / dental-chews
- 角色：列出该剂型下所有配方

**二、配方详情页（21个）**
- URL：`/formulas/{slug}/`
- 例：`/formulas/joint-support-soft-chews/`
- 角色：展示单条配方详情

### 【关键人物】

- 用户：老板，最终决策
- WorkBuddy：执行方
- Agent（Claude）：顾问，出指令

---

## 第二部分：核心设计原则

### 【原则1】客户第一眼判断"能不能做"

- 首屏必须有：产品名、MOQ、交期、价格区间
- 3-5 秒内让 B2B 买家判断是否继续

### 【原则2】关键决策信息前置

- MOQ / Lead time / Price tiers 放右栏
- 认证行放参数区底部
- 客户不用滚动就能提交询盘

### 【原则3】视觉克制专业

- 不用花哨动画
- 不用大色块
- B2B 导向，不是 B2C 电商

### 【原则4】SEO/GEO/AI 友好

- 所有内容服务端渲染（不用 JS 注入）
- 结构化数据完整
- 空值整块不渲染（不留空位）
- 图片 ALT 含关键词

### 【原则5】技术约束（硬）

- 不引入 ACF（用原生 meta box）
- 不引入 JS 库（用原生 JS）
- 不引入 CSS 框架（用原生 CSS）
- 不用 `:has()`（全站 170 处计数不增）
- 不用 `!important`（除非注释说明）
- 自闭合区块用 `/-->`（末尾无空格）

### 【原则6】单一事实源

- 认证：Site Settings 一处改全站生效
- 瓶型：Site Settings 一处改全站生效
- 全局 FAQ：Site Settings 一处改全站生效
- 详情页参数：只从 meta 读，不复制

---

## 第三部分：配方详情页完整设计规范

### 【页面模块顺序（从上到下）】

**① Header**（全站导航，不动）

**② Hero（绿色带 #2E6B54）**

结构：
- 面包屑：Home / Products / {剂型} / {配方名}
- H1：产品名（如 Joint Support Soft Chews）
- meta 行：{剂型} · MOQ from X units · Lead time
- 两个 CTA 按钮：
  - Reference this formula（配置器联动）
  - Build Custom Formula（H2b 后改向 `/contact/`）

样式：
- 高度桌面 328px / 移动 499px
- 面包屑字号 14px 白色
- H1 clamp(36px, 4vw, 52px) 白色
- meta 行 16px 白色
- CTA 按钮 48px 高

**③ 媒体 + 参数区（两栏，H2a 已做）**

桌面布局（≥1101px）：

```
┌──────────────────────┬─────────────────────┐
│                      │  H1（产品名）        │
│  ┌────┬──────────┐   │  （字号 28px 粗体）  │
│  │缩1 │          │   │                      │
│  │缩2 │  主图    │   │  简介（50-80词）     │
│  │缩3 │          │   │  （字号 16px 次色）  │
│  │缩4 │          │   │                      │
│  │缩5 │          │   │  ──────────────      │
│  │缩6 │          │   │                      │
│  └────┴──────────┘   │  Flavor              │
│                      │  （label 11px 大写）  │
│  [图片][视频]        │  ☐ Chicken ☐ Beef    │
│                      │  （chips 形态）       │
│                      │                      │
│                      │  Piece Weight        │
│                      │  ○ 1g ○ 2g ○ 3g      │
│                      │  （单选文本）         │
│                      │                      │
│                      │  Pack Size           │
│                      │  ☐ 60 ☐ 90 ☐ 120     │
│                      │                      │
│                      │  Suitable For        │
│                      │  ☐ Dogs ☐ Cats       │
│                      │                      │
│                      │  Life Stage          │
│                      │  ○ Puppy ○ Adult     │
│                      │  ○ Senior            │
│                      │                      │
│                      │  Quantity & Pricing  │
│                      │  ┌─────────┬──────┐  │
│                      │  │ 100     │ $X   │  │
│                      │  │ 500     │ $X   │  │
│                      │  │ 1,000   │ $X   │  │
│                      │  └─────────┴──────┘  │
│                      │  （qty 左对齐，      │
│                      │   price 右对齐）     │
│                      │                      │
│                      │  ──────────────      │
│                      │  ✅ FDA ✅ cGMP      │
│                      │  ✅ ISO 9001         │
│                      │  （pills 形态）       │
│                      │  ──────────────      │
│                      │                      │
│                      │  Lead time:          │
│                      │  Typically 7–15...   │
│                      │                      │
│                      │  [ Send Inquiry ]    │
│                      │  （橙色 #B54E0F）    │
└──────────────────────┴─────────────────────┘
```

媒体区细节：
- 竖缩略图轨道宽 72px
- 缩略图 6 张（或更少，有几张渲染几张）
- 主图与缩略图 gap 16px
- 缩略图比例 1:1，圆角 4px
- 选中缩略图：绿色边框 2px
- 主图比例 1:1（跟随产品图）
- 底部两个按钮：[图片][视频]
  - 按钮字号 14px
  - 选中态：绿色下划线
  - 未选：灰色文字

视频交互：
- 未播放时显示：YouTube 封面 + play 图标
- 点击 play：注入 iframe（youtube-nocookie）
- 已加载后：`data-loaded="true"` 防二次注入
- 无 JS 时：只显示封面，不跳 youtube.com

缩略图交互：
- 点击缩略图 → 切换主图（只切 class + hidden）
- 键盘：Tab 聚焦，←/→/↑/↓ 切换
- 鼠标悬停 → 仅 `@media (hover:hover)` 切换主图
- ARIA：role=tablist / role=tab / aria-selected

参数区交互：
- Flavor：多选 checkbox → chips
- Piece Weight：单选 radio → 文本
- Pack Size：多选 checkbox → 文本
- Suitable For：多选 checkbox → chips
- Life Stage：单选 radio → 文本
- Quantity & Pricing：单选 radio → 表格
- 空值规则：整行不渲染（不显示空 label）

断点：
- ≤480px：单栏
  - 缩略图横排 56px，可横向滚动
  - 参数区从上到下
  - Send Inquiry 按钮全宽
- 481-768px：单栏
  - 缩略图横排 84px
  - 其他同 ≤480
- 769-1024px：两栏
  - 媒体 50% / 参数 50%
  - gap 32px
- 1025-1100px：两栏
  - 媒体 55% / 参数 45%
  - gap 40px
- ≥1101px：两栏
  - 媒体 60% / 参数 40%
  - gap 48px

命名空间：`.sf-fdetail2`（H2a 已建立，H3/H4 继续用）

数据源（精确）：

| 字段 | meta key | 类型 | 空值行为 |
|---|---|---|---|
| Flavor | sf_formula_flavors | JSON array | 不渲染 |
| Piece Weight | 从 specs 解析 | string | 不渲染 |
| Pack Size | 从 specs 解析 | string | 不渲染 |
| Suitable For | sf_formula_species | JSON array | 不渲染 |
| Life Stage | sf_formula_lifestage | string | 不渲染 |
| Quantity & Pricing | sf_formula_price_tiers | JSON table | 不渲染 |
| Certifications | Site Settings | global | 不渲染 |
| Lead time | sf_formula_lead_time | string | 不渲染 |

**④ 详细内容区（H3 要做）**

模块顺序：

```
┌──────────────────────────────────────┐
│  Ingredients                          │
│  （H2 32px）                          │
│  [meta sf_formula_ingredients]        │
│  （正文 16px 行高 1.6）               │
│                                       │
│  Guaranteed Analysis                  │
│  [meta sf_formula_analysis]           │
│                                       │
│  Formula                              │
│  [meta sf_formula_specs 解析]         │
│                                       │
│  Recommended For                      │
│  [meta sf_formula_recommended_for]    │
│  （1-2 句话）                          │
│                                       │
│  Use Cases                            │
│  [meta sf_formula_use_cases]          │
│  （2-3 条列表）                        │
│                                       │
│  Who It's For                         │
│  [meta sf_formula_who_for]            │
│  （1-2 句话）                          │
│                                       │
│  Packaging & Specifications           │
│  （H3 20px）                          │
│  ├ Container Options                 │
│  │   （chips）                        │
│  ├ Additional Packaging              │
│  │   （chips）                        │
│  ├ Color Options                     │
│  │   （chips）                        │
│  ├ Shelf Life                        │
│  │   （文本）                         │
│  ├ Storage                           │
│  │   （文本）                         │
│  └ Carton Dimensions                 │
│      （表格：Pack Size / Qty / Size） │
└──────────────────────────────────────┘
```

样式：
- 每块间距 48px
- section padding 80px 上下
- 背景色交替：white / bg-light
- 表格：border-collapse，行间细线 1px

命名空间：`.sf-fdetail-content`
空值规则：整块不渲染（不显示空 H2）

数据源：

| 块 | meta key | 空值行为 |
|---|---|---|
| Ingredients | sf_formula_ingredients | 不渲染 |
| Guaranteed Analysis | sf_formula_analysis | 不渲染 |
| Formula | sf_formula_specs | 不渲染 |
| Recommended For | sf_formula_recommended_for | 不渲染 |
| Use Cases | sf_formula_use_cases | 不渲染 |
| Who It's For | sf_formula_who_for | 不渲染 |
| Container Options | Site Settings 瓶型 | 不渲染 |
| Additional Packaging | sf_formula_packaging_extra | 不渲染 |
| Color Options | sf_formula_colors | 不渲染 |
| Shelf Life | sf_formula_shelf_life | 不渲染 |
| Storage | 硬编码（所有产品同句） | — |
| Carton Dimensions | sf_formula_cartons | 不渲染 |

**⑤ FAQ**（批 C 已做，不动）

**⑥ Sampling Process（H3 要做）**

结构：

```
┌──────────────────────────────────────┐
│  How Sampling Works                   │
│                                       │
│  ①            ②            ③         │
│  Submit       Confirm      Sampling   │
│  Inquiry      Details      & QC       │
│  （描述）     （描述）     （描述）   │
│                                       │
│  ④ Ship & Evaluate                    │
│  （描述）                             │
│                                       │
│  Typically 3-7 working days           │
└──────────────────────────────────────┘
```

4 步文字：

1. **Submit Inquiry** — Tell us your target formula, flavor, and packaging ideas.
2. **Confirm Details** — We'll provide a sample spec sheet and a proforma invoice for the sample fee.
3. **Sampling & Quality Check** — Our lab produces your sample and runs a full quality check.
4. **Ship & Evaluate** — We ship the sample to you (typically 3-7 working days). You evaluate and provide feedback.

样式：
- 4 步横向排列（≥769px）
- 4 步纵向排列（≤768px）
- 每步：圆圈数字 + 标题 + 描述
- 圆圈：绿底白字，44px 直径

HowTo Schema：
- 服务端渲染 JSON-LD
- name: "How Sampling Works"
- step: 4 个 HowToStep
- totalTime: "P3D"（3-7 天）

命名空间：`.sf-sampling`

**⑦ More {剂型} Formulas**（不动）

**⑧ 悬浮询盘按钮（H4 要做）**

- 位置：右侧固定（right: 24px; bottom: 100px）
- 触发：滚动到参数区后出现
- 出现动画：从底部滑入 300ms
- 按钮：圆形或胶囊形，橙色 #B54E0F
- 文字：Send Inquiry 或图标+文字
- 点击：打开弹窗
- 移动端：改为底部固定栏（全宽）
- 命名空间：`.sf-floating-inquiry`

**⑨ 询盘弹窗（H4 要做）**

桌面版：

```
┌──────────────────────────────────────┐
│  Send Inquiry                  [×]  │
├──────────────────────────────────────┤
│                                       │
│  Your Selection:                      │
│  ┌─────────────────────────────────┐ │
│  │ Flavor:        Chicken          │ │
│  │ Piece Weight:  2g               │ │
│  │ Pack Size:     60/90/120        │ │
│  │ Suitable For:  Dogs             │ │
│  │ Life Stage:    Adult            │ │
│  │ Quantity:      500 units        │ │
│  │ Reference:     $X.XX / unit     │ │
│  └─────────────────────────────────┘ │
│  （自动带入客户勾选内容）              │
│                                       │
│  How Sampling Works:                  │
│  ① Submit → ② Confirm →              │
│  ③ Sampling → ④ Ship                 │
│  （4 步精简版）                       │
│                                       │
│  Name *      [                  ]    │
│  Email *     [                  ]    │
│  Company     [                  ]    │
│  Country     [                  ]    │
│  Message     [                  ]    │
│                                       │
│  [ Submit Inquiry ]                  │
└──────────────────────────────────────┘
```

移动版：全屏抽屉，从底部滑入

字段规则：
- Name：必填
- Email：必填，格式验证
- Company：选填
- Country：选填，下拉或文本
- Message：选填，textarea

反垃圾：
- honeypot 隐藏字段
- 简单时间验证（3 秒内提交拒绝）

提交后：
- AJAX 提交到 REST 端点
- 发送邮件到 sales@zxpet.com
- 弹窗显示"已收到，24 小时内回复"
- 3 秒后自动关闭

邮件内容：
- 主题：`[Inquiry] {产品名} — {Name}`
- 正文：勾选内容 + 客户信息 + 来源 URL

命名空间：`.sf-inquiry-modal`

**⑩ Footer**（全站页脚，不动）

---

## 第四部分：剂型页完整设计规范

### 【页面模块顺序】

**① Header**（全站导航）

**② 面包屑**：Home / Products / {剂型}

**③ Hero（绿色带）**
- H1：Private Label {剂型} for Dogs & Cats
- 标签行：{剂型} · 功效 · For Dogs & Cats
- 两个 CTA：Request Sample / Get Quote

**④ 极简核心事实行（F1 已做）**
- MOQ · Lead time · Certifications
- 一行三项，无 H2

**⑤ 标准配方图片卡片（配方卡墙 `#formulas`）**
- 4-12 张卡片
- 每卡：产品图 + 配方名 + 3 参数 + View formula →

**⑥ 配置器（H2b 删除）**
- 现位置：**卡墙 `#formulas` 之后**（实测 L56 起）〔2026-09-22 更正：原文"hero 之后、卡墙之前"系误记〕
- H2b 后消失

**⑦ `.sf-explore` 带 + `[sf_explore_chips]`（H2b 移位）**
- 现位置：配置器 `options` 列（65% 窄栏）内部
- H2b 移到：**卡墙之后、How We Work 之前**（＝配置器原槽位，**裁决 D**）
- 理由：chips 是"引导离开当前页"元素，应在客户看完当前剂型配方之后

**⑧ How We Work**（不动）

**⑨ FAQ**（不动）

**⑩ Related Dosage Forms**（不动）

**⑪ 询盘表单**（不动）

**⑫ Footer**

---

## 第五部分：设计系统（精确数值）

### 【颜色 token】

| 用途 | token | 值 |
|---|---|---|
| 主色 | primary | #1B4D3E |
| 品牌绿 | brand-green | #5AB735 |
| CTA 橙 | cta | #B54E0F |
| 浅底 | bg-light | #F3F6F4 |
| 细边 | border-light | #DCE2DF |
| 主文字 | text-primary | #1C2B24 |
| 次文字 | text-secondary | #5F6B65 |
| 白卡 | card-white | #FFFFFF |
| Hero 底 | hero-bg | #2E6B54 |

### 【字号】

| 元素 | 字号 | 字重 | 行高 |
|---|---|---|---|
| H1 | clamp(36px, 4vw, 52px) | 700 | 1.2 |
| H2 | 32px | 700 | 1.3 |
| H3 | 20px | 600 | 1.4 |
| 正文 | 16px | 400 | 1.6 |
| label | 11px | 700 | 1.4 |
| 次说明 | 14px | 400 | 1.5 |
| 按钮 | 15px | 600 | 1 |

### 【间距】

| 用途 | 值 |
|---|---|
| section padding | 80px 上下 |
| 组件间距 | 48px |
| 组内间距 | 24px |
| 参数行间距 | 32px |
| 移动端减半 | 40px / 24px / 12px / 16px |

### 【断点】

| 断点 | 用途 |
|---|---|
| 480px | 手机（H2a 新增） |
| 768px | 主断点（全站） |
| 1024px | 平板横 |
| 1100px | 点轨隐藏（全站） |
| 1101px | 桌面（H2a 新增） |

### 【圆角】

| 元素 | 半径 |
|---|---|
| 卡片 | 8px |
| 按钮 | 6px |
| 缩略图 | 4px |
| 圆圈数字 | 50% |

### 【阴影】

| 元素 | 阴影 |
|---|---|
| 卡片 | 0 1px 3px rgba(0,0,0,0.08) |
| 弹窗 | 0 10px 40px rgba(0,0,0,0.15) |

### 【按钮】

| 类型 | 背景 | 文字 | 边框 |
|---|---|---|---|
| 主按钮 | #B54E0F | #FFF | 无 |
| 次按钮 | 透明 | #1B4D3E | 2px solid #1B4D3E |
| 危险 | #D93025 | #FFF | 无 |

### 【chips（多选标签）】

- 背景：透明
- 边框：1px solid #DCE2DF
- 圆角：999px（胶囊）
- padding：6px 14px
- 字号：14px
- 选中态：背景 #5AB735，文字白色

### 【pills（认证徽章）】

- 背景：#F3F6F4
- 圆角：4px
- padding：4px 10px
- 字号：13px
- 图标：✅ 前缀

---

## 第六部分：工作铁律（10 条）

**【铁律1】报告与实际文件可能不一致**
编辑回执 ≠ 落盘成功。每次声明"已删除/已修改"，必须用 `grep -cE` 或 `cmp` 复核文件实际字节。

**【铁律2】WP 魔引号陷阱**
`update_post_meta` / `update_option` 内部会 `wp_unslash()`。写入含 `\u2014` 或 `\"` 的 JSON 前，必须 `wp_slash(wp_json_encode(..., JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES))` 包裹。

**【铁律3】functions.php 顶层插入防线**
任何向 `functions.php` 插入顶层代码，apply 后必跑：① `b2d_c_php_scope.php`（tokenizer 深度）② 门 4 顶层断言。

**【铁律4】grep 看清命中位置**
类名 token 可能在 PHP 字符串里拼出来。不能只看计数，要看上下文。

**【铁律5】设备模拟 ≠ 媒体环境**
`set device` 只改 UA，不改 hover/touch 媒体查询。hover 测试必须用 init-script 强制。

**【铁律6】截图假象 ≠ 布局错误**
cookie 横幅遮挡、元素截图裁切都会造成假象。必须用几何测量交叉验证。

**【铁律7】日志归因判据**
判据是"每一条都能归因"，不是"窗口内 0 条"。

**【铁律8】admin 资产 immutable 缓存**
admin JS/CSS 改动后，E2E 前必须 `agent-browser close --all` 清缓存。

**【铁律9】同文件禁并行 Edit**
串行编辑，一次一处。

**【铁律10】先过门再上线**
线上从不服务未过门的字节。

---

## 第七部分：停靠点规则

### 【必须停】（等用户确认才能继续）

1. **扫描发现与 playbook 预期不符** — 例：数据缺口、结构变化、新依赖
2. **门抓到产品 bug（不是测试 bug）** — 例：代码逻辑错误、渲染错误、数据损坏
3. **需要改数据（迁移、删除、批量写）** — 例：改 DB、删文件、批量操作

### 【不停】（自动执行）

- Step 推进
- 测试脚本 bug 修复
- 门工具自身 bug 修复
- CSS/JS 语法调整
- 版本号 bump
- 文档/记忆写入
- 预检 + 六门 + 负对照 + 矩阵
- 浏览器 E2E
- git commit + push（本地 + origin）
- 批次文档

### 【不执行】（等用户自己决定）

- `git pull` 到服务器（不上线）
- 删 authority guard
- 改数据库
- 清测试数据
- 拆预检副本
- 服务侧验证

---

## 第八部分：默认决策值

| 决策点 | 默认值 |
|---|---|
| 数据缺口 | 先建渲染，空库自动缺行 |
| 缩略图 | 有几张渲染几张 |
| 认证行 | Site Settings pills |
| 空值行为 | 整行/整块不渲染 |
| CSS 命名空间 | 新批次新 namespace |
| 版本号 | 每次 bump，两处同步 |
| 门方向 | 删除批＝基线删；插入批＝候选删；重组批＝逆操作还原 |
| 负对照 | 必须 FAIL |
| 破坏矩阵 | 全 FAIL |
| 测试零留痕 | 必须验证 |
| 日志归因 | 每条能归因 |
| 浏览器缓存 | E2E 前 `close --all` |
| 提交粒度 | 一批一 commit，可单独 revert |
| 图片 ALT | 产品名 + 剂型 + 卖点 + 视觉特征 |
| 提交 message | `"H2b: 配置器删除完成，门全绿"` |

---

## 第九部分：H2b-H6 五批详细范围

### 【前置改动：邮箱变更】

在 **H4 之前**自动执行：`info@zxpet.com` → `sales@zxpet.com`

1. 扫描全站 `info@zxpet.com` 位置
   - 模板（`parts/footer.html` 等）
   - PHP（`functions.php` / `inc/`）
   - JS
   - JSON-LD（Organization Schema email）
   - DB（Site Settings / 页面内容 / 菜单）
2. 全部改为 `sales@zxpet.com`
3. CF email-protection 会自动跟随
4. DIFF 集合：含邮箱的页面
5. **涉及改 DB 时停下汇报**
6. H4 新建的询盘表单收件人用新邮箱

### 【H2b】配置器删除

> **2026-09-22 裁决 + Step 0 实测更正**：块边界、chips 落点、enqueue 行号已按下表更新。
> 详案 `docs/batch2d-stepH2b1-plan.md`｜扫描 `docs/batch2d-stepH2b-scan.md`。
> **拆两批、各跑完整 Step0→6**：**H2b1**（结构/样式）→ **H2b2**（入队/资产）。
> 拆的理由：混做会让「16 页必差」被两种原因同时触发，失败无法归因。

**H2b1（纯删除 + 纯位移 + CTA 改向）**

1. **8 剂型页删配置器区块**（块边界按实测，块首＝`<!-- Block 4: Configurator -->`，块尾＝`<!-- /wp:group -->`）
   - soft-chews **56-271** ／ dental-chews 56-220 ／ tablets 56-207 ／ powders·fish-oil 56-203
   - pastes·liquids 56-190 ／ drops 56-189（8 页合计 **1,233 行 / 144.9 KB**）
2. **`.sf-explore` 带先移位、再随块删**
   - 现位置：配置器 `options` 列（65% 窄栏，`configurator.css:833-957` 按其调尺寸）内部
   - 移到：**卡墙 `#formulas` 之后、How We Work 之前**（＝配置器原槽位）＝**裁决 D**
   - 带内 `href="/products/"` 的 `Browse All Products →` 与卡墙 L50 `href="/formulas/"` 的 `Browse All Formulas →` 是**两个不同出口**，均保留
3. **CTA 改向**（原 `#configurator` 锚点随块消失）
   - 8 剂型页 hero `:22` `href="#configurator"` → `/contact/#quote`，**并加 `sf-quote-cta`**
   - 详情页 `:13` `{{FORM_HREF}}#configurator` → `/contact/#quote`，**并加 `sf-quote-cta`**
   - `sf-quote-cta` 由全局入队的 `quote-cta.js 1.0.0` 接管：**本页有 `#inquiry-form` 则本地平滑滚动，否则原生跳转**（`functions.php:39-40` 注释即此契约，与 header/footer 的 `Get a Quote` 完全同款）
   - 效果：剂型页 hero 保持"留在本页"的原始设计意图（落到本页 L590 `#inquiry-form`），无 JS/无表单时降级为 `/contact/#quote`
4. **`.sf-explore*` 迁移**：`configurator.css:833-957`（125 行）→ **`style.css` 末尾追加**，**原处同批删除**
   - 必须"迁入即删原地"：`style.css` 先加载、`configurator.css` 后加载（enqueue 顺序 31 vs 188），残留定义会**静默覆盖**迁入的规则
   - `:has(` 账：迁入 0 条（那 125 行内无 `:has(`）⇒ 删 `configurator.css` 后全站 **171 → 164**（不增）
   - `.sf-explore{margin-top}` 24px（桌面）/20px（移动）**归零**：带子成为独立 section 后不再需要与上一配置组拉开
5. **`style.css:5915-5921` 补偿归还**（整块 `@media(max-width:768px)` 删除）
   - `.sf-formulas{padding-bottom:0!important}` → 还原（模板 inline 的 48px 生效）
   - `#configurator{padding-top:32px!important}` → 死规则，删
6. **`.sf-explore` 通栏重定**（视觉验收项）：桌面由 65% 窄栏变通栏，chips 间距/尺寸可上浮一档（`gap` 6→8、`chip` padding `8px 12px`→`10px 16px`、字号 13→14px）；移动端 `flex-wrap:nowrap` 横滑行保留
7. **enqueue 本轮不动**：`configurator.css` 仍入队（内容已变 ⇒ **ver 2.9 → 2.10**）；`configurator.js` 2.3 不动
8. **ver bump**：`style.css` **2.10.55 → 2.10.56**（两处同步：`functions.php:31` ＋ `style.css:5`）

**H2b2（停入队 + 删资产）**

1. `functions.php` **停入队 `configurator.css`(188) / `configurator.js`(189)** ⛔ **`:186 $is_dosage_page` 必须留**（`:205` formulas.js、`:210` formula-filter.js 仍用）
2. 资产文件删除（先停入队并验证一轮，再 `git rm`）
3. **`inc/config-pdf.php` 保留**：被 `basket.js:391` 直连（`POST /wp-json/sinofresh/v1/config-pdf`）；只删 `configurator.js:699` 侧调用

**回归：**

- DIFF 集合：8 剂型页 + 8 zh = **16 页**（H2b1 起）；其余 59 页只许 ver 令牌移动
- 限定证明方向：**纯删除 + 纯位移**（基线删块、带子迁位 = 候选）
- **选择器唯一性**：迁入的 16 个 `.sf-explore*` 选择器全站只定义一次
- basket 功能回归；`config-pdf` 端点回归（H2b2）
- K1-K7 契约不变（`formulas.js` 不改；`sinofresh_formula_*` sessionStorage 写侧成为**无读者** ⇒ 记 H6 候选）
- **桌面点轨条目 6 → 5**，断言第 2 条为 How We Work
- 遗留引擎（`html.no-has`）：`.sf-float-stack` / `.trp-language-switcher` 底距回到 `style.css` 基线（H2b2 删 `configurator.css:700/705` 后）

### 【H3】内容区 + FAQ + Sampling

**范围：**

1. 详细内容区 6 块
   - Ingredients / Guaranteed Analysis / Formula / Recommended For / Use Cases / Who It's For
   - Packaging & Specifications（含 6 子块）
2. Sampling Process 4 步 + HowTo Schema
3. 模板插入
4. meta 空值整块不渲染

**样式：**
- 命名空间 `.sf-fdetail-content`
- 每块间距 48px
- 背景交替 white / bg-light
- 表格 border-collapse

**回归：**
- DIFF 集合：21 详情页 + 21 zh = 42 页
- JSON-LD：FAQPage 不变，HowTo 新增
- 点轨：详情页无点轨（实测铁律）

### 【H4】弹窗表单 + 悬浮按钮

**范围：**

1. AJAX 端点（PHP）
   - REST API 路由
   - 邮件到 sales@zxpet.com
   - honeypot 反垃圾
   - 简单时间验证（3 秒内拒绝）
2. 5 字段表单
   - Name（必填）/ Email（必填）/ Company / Country / Message
3. 悬浮按钮
   - 右侧固定 `right:24px bottom:100px`
   - 滚动到参数区后出现
   - 点击打开弹窗
4. 勾选内容自动带入
5. 4 步打样流程内嵌
6. 弹窗移动端全屏抽屉

**回归：**
- DIFF 集合：21 详情页 + 21 zh
- 表单提交实测（真发邮件到 sales@）
- 反垃圾验证

### 【H5】SEO/GEO 优化

**范围：**

1. Product Schema 强化
   - additionalProperty（口味/克重/包装等）
   - offers（阶梯价格）
   - material / audience / isRelatedTo
2. Organization Schema 补 knowsAbout
3. 图片 ALT 自动生成
   - 格式：产品名 + 剂型 + 卖点 + 视觉特征
   - 例：`Joint Support Soft Chews - Soft Chew - Chicken Flavor - 60 Count Bottle`
4. 内容 80/20 原则审计

**回归：**
- JSON-LD deep-equal（除新增字段）
- Rich Results Test 验证

### 【H6】数据迁移 + 清理

**范围：**

1. 旧 CSS 清理
   - `.sf-facts__*`（H1 遗留）
   - `.sf-spectable__*`（批 E 遗留）
   - `.sf-fdetail-media__*`（H2a 遗留）
   - 先确认无活引用再删
2. 旧 PHP 函数清理 — 已删短码的残留
3. 旧 JS 清理 — 无引用的脚本
4. MOQ 三处对账 — FAQ / 详情页 meta / 剂型页

**回归：**
- DIFF 集合：仅 ver 令牌
- 全站功能回归

---

## 第十部分：每批标准流程

**Step 0：扫描现状**
→ 检查是否与 playbook 预期相符
→ 相符：直接进 Step 1
→ 不符：停下报告

**Step 1-N：实施**
→ 自动推进
→ 遇到产品 bug：停下报告
→ 遇到需要改数据：停下报告

**Step N+1：预检 + 六门 + 负对照 + 矩阵**
→ 全绿：继续
→ 产品 bug：停下

**Step N+2：浏览器 E2E**
→ 全绿：继续
→ 产品 bug：停下

**Step N+3：收尾（不执行上线）**
→ `git commit`（message 格式见下）
→ `git push origin`
→ 批次文档 `docs/batch2d-step{X}.md`
→ 记忆 `MEMORY.md` 更新
→ 更新 playbook 进度
→ 自动进下一批

commit message 格式：
```
"H2b: 配置器删除完成，门全绿"
"H3: 内容区+Sampling 完成，门全绿"
"H4: 弹窗表单+悬浮按钮完成，门全绿"
"H5: SEO/GEO 优化完成，门全绿"
"H6: 数据清理完成，门全绿"
```

---

## 第十一部分：汇报格式

每批完成后汇报（简短）：

```
【状态】H2b 代码改完，门全绿
【数据】
- DIFF 集合：16 页精确命中
- 门：18/18 通过
- 负对照：FAIL as required
- 破坏矩阵：11/11 FAIL
【提交】commit xxx + push origin
【服务器】未 pull，守卫未删，DB 未动
【下一批】H3 开始
```

需要用户决策时汇报：

```
【需要决策】H3 扫描发现 X
【证据】
- ...
- ...
【建议】
- A：...
- B：...
- C：...
【等回复】
```

---

## 第十二部分：启动

收到本指令后：

1. 存手册到 `docs/agent-playbook.md`
2. 写进 `MEMORY.md`（摘要 + 指针）
3. 立即进 H2b Step 0 扫描
4. 如与预期相符，继续 Step 1
5. 全部按上述规则自动执行
6. 每批完成后自动进下一批

> 不需要问用户"是否开始"。不需要问用户"是否继续"。
> 只有 3 类必须停的情况才打扰用户。

---

## 第十三部分：H2b-H6 完成后收尾

全部完成后：

- 汇报总结（5 批状态 + commit 列表）
- 列出服务器状态（未 pull）
- 列出仍需用户处理的事项
- 停止

---

## 约束

- 遵守工作铁律 10 条
- 遵守默认决策值
- 遵守停靠点规则
- 不引入 ACF、不引入 JS 库、不引入 CSS 框架
- 不执行上线动作（`git pull`、拆预检）
- 不改数据库
- 不删 authority guard
- 3 类必须停的情况严格执行
- 每批一 commit，可单独 revert

---

# 附录 A：Step 0 实测核对表（H2b，2026-09-22）

> **性质**：补充证据，不修改正文。凡正文数值与实测不符者，**以实测为准**（正文行号系估算）。
> 完整扫描见 `docs/batch2d-stepH2b-scan.md`；工具 `tools/b2d_h2b_scan.py`、原始数据 `_backup/b2d-h2b-scan.json`。

## A.1 与新位置/新依赖有关的**实质不符**（触发「必须停」第 1 类）—— 已于 2026-09-22 全部裁决

| # | 正文说法 | 实测 | 影响 |
|---|---|---|---|
| 1 | §4⑥ 配置器「现位置：hero 之后、卡墙之前」 | 实际顺序：hero(L3-27) → **facts-mini**(L29-36) → **卡墙 `#formulas`**(L38-53) → **配置器**(L56-271) → How We Work | §4⑦ 与 §9【H2b】二 给的 chips 新位置「Hero 之后、卡墙之前」**不是配置器现在占的槽位**，chip 落点有二义 |
| 2 | §9【H2b】四「enqueue 清理 → 先注释后删文件」 | `.sf-explore__btn` 在**块外仍被引用**（8 页卡墙 L50 `Browse All Formulas →`）；`.sf-explore*` 规则（`configurator.css:833-957`，125 行）必须**外迁**（至少 `__btn`） | 直接删 `configurator.css` 会让卡墙按钮掉样式 |
| 3 | §9【H2b】未提 | `style.css:5919` `@media(max-width:768px){.sf-formulas{padding-bottom:0!important}}` 是**专为贴近配置器做的补偿**；配置器删除后须复原，否则移动端卡墙贴边 | 产品级视觉缺陷 |
| 4 | §9【H2b】回归只列「16 页 DIFF + basket + K1-K7」 | 剂型页 H2 由 **6 → 5**（含被删的 `Build Your … Formula`）⇒ 桌面点轨 `.sf-toc` 条目 6→5（`toc-nav.js` 从 H2 序列编号） | 需新增回归断言 |
| 5 | §5 断点/§9 未提 | `.sf-explore` 现状是**配置器 options 列内的 65% 宽窄栏**（CSS 注释：为在 1440px 一行放下 8 chip 而调）；移出后变通栏，尺寸/移动端节奏必须重定 | 需新增视觉验收 |

### A.1b 裁决结果（2026-09-22）

| 项 | 裁决 | 落地位置 |
|---|---|---|
| ① chips 落点 | **D**：卡墙之后、How We Work 之前（＝配置器原槽位）。理由：chips 是"引导离开当前页"元素，应在客户看完当前剂型配方之后。**§4⑥ 的「Hero 之后」系用户笔误，D 为更正** | §4⑦ ／ §9【H2b】2 ／ §9【H2b1】2 |
| ② `.sf-explore__btn` 外迁 | **同意**：125 行 `.sf-explore*` 从 `configurator.css` 迁到 `style.css` | §9【H2b1】4 |
| ③ `style.css:5919` 补偿归还 | **同意**：`.sf-formulas` `padding-bottom` 还原；`#configurator` 死规则删 | §9【H2b1】5 |
| ④ 点轨 6→5 | **同意记预期变化**，新增回归断言：第 2 条为 How We Work | §9【H2b】回归 |
| ⑤ `.sf-explore` 通栏重定尺寸 | **同意**，纳入 H2b1 视觉验收 | §9【H2b1】6 |
| 拆分 H2b1 ／ H2b2 | **确认分开过门** | §9【H2b】题头 |

> 数值漂移 **全部按实测执行**（已确认）：块边界 `56-271/220/207/203/203/190/190/189`、8 页合计 **1,233 行/144.9 KB**、`:has(` **171**（164+7）、`text-primary` **#1C2B24**、facts-mini **4 项**、enqueue 删 **188/189** 两行（**186 保留**）。正文 §4/§5/§9 已同步更正。

## A.2 数值漂移（**不阻塞**，按实测执行）

| 项 | 正文 | 实测 |
|---|---|---|
| 块起止行 | soft-chews 55-272 / tablets 55-207 / dental-chews 55-220 / 其余 55-189 左右 | **56**-271 / 56-207 / 56-220 / 56-203（powders, fish-oil）/ 56-190（pastes, liquids）/ 56-189（drops） |
| `functions.php` enqueue | 182-190 | 182-213 为整个 `wp_enqueue_scripts` 闭包；**删的是 188-189 两行**，`$is_dosage_page`(186) 必须留（205 行 `formulas.js` 仍用） |
| `:has()` 计数 | 170（163+7） | **171**（`style.css` **164** + `configurator.css` **7**，其中 2 处在注释里）。删 `configurator.css` 后 **164**，满足「不增」 |
| §4④ facts-mini | 一行三项 | 实际 **4 项**（MOQ / Lead time / Certifications / **Packaging**，Batch G 加的第 4 行） |
| §5 色表 `text-primary` | `#1A1A1A` | `theme.json` = **`#1C2B24`**；其余 token 全部一致；hero `#2E6B54` ✓（`style.css:1880 .sf-hero-inner`） |

## A.3 已核实**相符**的项

- 8 页 hero CTA 在第 **22** 行 `href="#configurator"`，文案 `Build Custom Formula` ✓
- 详情页 `single-sf_formula.html:13` `{{FORM_HREF}}#configurator` ✓（另一按钮 `Reference this formula →` 走 K1，不动）
- `inc/config-pdf.php` 被 `basket.js:391` 直接 `fetch('/wp-json/sinofresh/v1/config-pdf')` 调用，与 `configurator.js` 无耦合 ⇒ **端点必须保留** ✓
- 块内 **无** `application/ld+json` / `<script>` / `sf-schema-desc` ⇒ K6 剂型页 JSON-LD 不受影响 ✓
- 块内 SVG sprite（34 symbol）**无块外引用**（`<use href="#i-…">` 全部在块内）⇒ 可随块安全删除 ✓
- `[sf_explore_chips]` 短代码只产 `<nav class="sf-explore__chips">`；**band 外壳**（`.sf-explore` + `<h3 class="sf-explore__title">Explore more dosage forms</h3>`）硬编码在模板里，移位须一并搬 ✓
- `inc/formula-pools.php` 头部已声明「H2 删掉配置器后它是唯一副本」⇒ 卡墙参数池的单一事实源已就位 ✓

## A.4 写方案期追加实测（2026-09-22，第二轮只读核验）

| # | 结论 | 出处 |
|---|---|---|
| 1 | `.sf-float-stack` 是**全局元素**（`parts/footer.html:111`，基样式 `style.css:3913` + `body.has-cookie-banner` 3963 + 媒体查询 3997/4007/7810）。`configurator.css` 里 3 条：`:682`／`:690` 受 `body:has(.configurator__bar…)` 限定（配置器删除即死）；**`:705 html.no-has .sf-float-stack{bottom:132px}` 不受 `.configurator` 限定**，是给遗留引擎的补偿。`html.no-has` 探针另有 `style.css §30` 的独立消费者（`html.no-has section` 等 4 组）⇒ **探针必须保留**，随删的是那两条补偿 | 删 `configurator.css` 前必须确认这点，否则遗留引擎上页脚悬浮按钮被抬高 132px |
| 2 | **选择器唯一性陷阱**：`style.css`（enqueue `functions.php:31`）先加载、`configurator.css`（`:188`）后加载 ⇒ 同选择器以 `configurator.css` 胜。迁移必须**迁入即删原地**，否则旧值静默覆盖新值 | `.sf-explore*` 迁移 |
| 3 | `quote-cta.js 1.0.0` 已是**全站入队**的既有契约（`functions.php:39-40`）：`a.sf-quote-cta` + 目标 `#inquiry-form, #quote, #booking-form` → 页内有表单则平滑滚动，否则原生跳转。剂型页 `L590` 有 `#inquiry-form`；详情页**无**（`id` 只有 `gallery`）⇒ 详情页加 class 不改变行为，与 header/footer `Get a Quote` 同款 | CTA 改向零新增 JS |
| 4 | `.sf-explore__btn` 在 8 页共 **16 处**：块外 `L50`（`/formulas/`，**活**）＋ 块内（`/products/`，随带迁移）各 8 —— 两个不同出口，都保留 | §9【H2b1】2 |
| 5 | `configurator.css` 定义 **67** 个类；其中「块外或其它模板仍在用」的只有 **2 个**：`.sf-explore__btn`（迁）与 `.sf-float-stack`（`:has()` 限定，随删）。其余 **54 个**仅块内使用 ⇒ 可随文件删除 | H2b2 安全性 |
| 6 | `inc/config-pdf.php` 与 `inc/formula-pools.php` 里的 "configurator" **全是注释**（无代码耦合）⇒ 端点与选项池不受删文件影响 | §9【H2b2】3 |
| 7 | `--wp--preset--spacing--80` 实测 = **48px**（slug 名仍叫 80，legacy 映射）⇒ 相邻 section 实际间距 96px；新带子 section 取 `padding: 0 / 48px` 使带子读作卡墙的"尾巴" | §9【H2b1】2 |
| 8 | `style.css` 无任何 `.sf-explore*` **规则**（仅 5931/5977 两处注释引用其几何）⇒ 迁入无同名冲突；但为保住"后加载覆盖"语义，**追加到 `style.css` 末尾** | §9【H2b1】4 |

## A.5 H2b1 执行期实测（2026-09-22，Step 1–5）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔ **`AGENT_BROWSER_INIT_SCRIPTS` / `--init-script` 只在「启动浏览器的那条命令」上生效，而那是 `set credentials` 不是 `open`**。挂在 `open` 上＝注册太晚、脚本静默不跑（E8 首次就是这样假绿：`no-has` 永不出现，看起来像"stub 没生效"）。`agent-browser 0.27.0` **没有** `addinitscript` 子命令，尽管它自带的 `skills get core --full` 里写着有 ⇒ 文档与二进制不一致时以二进制为准。四条排序实测见 `docs/batchH2b1-gates/e8-init-script-probe.json` | 一切需要"页面加载前改环境"的测试（媒体查询/特性探测正负对照） |
| 2 | ⛔ **`agent-browser screenshot <selector> <path>` 写出空白图**（1440×259 的 section → 1.7 KB 纯白）。文件存在、看着像证据、其实什么都没有。可用做法＝滚到目标 + 视口整屏截图（`set viewport w band_h+240` → `scrollTo` → `screenshot <path>`），并加**字节下限**把空白变成 FAIL | E9；任何"截图交付" |
| 3 | ⛔ **取景要扣掉 sticky 头部，而它在 `scrollY=0` 时是 `static`**（滚动后才被 JS 立起来）⇒ 偏移必须**两段式测**：先粗滚让 sticky 生效，再量"顶部遮挡高度"并校正 | 移动端截图；`<header>` 有多个、`querySelector('header')` 拿到的不是 sticky 那个 |
| 4 | ⛔ **不要用固定 sleep 等平滑滚动**：约 1.2s 才落定，固定 1.2s 采样会抓到中途值（E4 误报 177px）。改法＝轮询 `scrollY` 至"连续两次相同"，并**断言落定在 `scroll-margin-top` 上**（实测 96 vs 96.0）而非一个拍出来的容差 | E4；任何锚点/滚动测试 |
| 5 | ⛔ **断言先在候选文本上跑、再落盘**：`apply_detail` 第一版先写后断言且期望值写错（`{{FORM_HREF}}` 2→1，不是 2→2），一次**正确**的编辑被报成失败、文件却已改写。改法＝pure 校验（写前后各一次）＋同进程回读 | 一切写文件的补丁器 |
| 6 | ✅ **可复现性可以做成一条门**：`tools/b2d_h2b1_repro.py` 用 `git archive <batch>~1` 搭沙盒、重跑补丁器、与提交比对 ⇒ H2b1 **12/12 逐字节相同**。这同时补上"首次运行时断言还不对"造成的证据洞（`_backup/b2d-h2b1-apply.json` 里的 `ok:false` 是假警报） | 「不是零差异批」的收尾 |
| 7 | **删掉 `body:has(.configurator__bar)` 之后，两个固定层落回 `style.css` 取值**：live（有条）恒为 float `132px` / lang `68px`；候选（无条）现代引擎 = 横幅在场 1440 `100px`、480 `268px`，无横幅 24/16px，lang `0px` —— 与**非剂型页**（`/about/`）完全一致 ⇒ 是向全站一致性收敛。旧引擎因 **`:700` / `:705`** 的无条件复刻仍是 132/68 | H2b2 直接把 `configurator.css` **整个文件**删掉（原先写的「`:667-707` 整段」行号不成立：`:667` 只是注释首行、`:707` 不是块边界；容器是 L642 的媒体查询、直开到 L831），删后旧引擎应与现代引擎差值归零 |
| 8 | `--wp--preset--spacing--80` 实测 **48px**；`.sf-explore` 是 `content-box` ⇒ 其边框盒 = `1200px 内容列 + 2×32px padding` = 1264px；面板**居中**（gutter 左右相等），且 1440 时其**内容列**正好压在卡墙内容列（x120）上 | 判断"通栏"要看 `section` 而不是面板 |

---

# 附录 B：进度区

| 批次 | 状态 | commit | 说明 |
|---|---|---|---|
| H2b | **Step 0 完成 → 5 项不符已裁决（① 改 D / ②③④⑤ 同意）** | — | `docs/batch2d-stepH2b-scan.md` |
| **H2b1** | **Step 1–5 全过门 + E2E 全过 → 用户确认通过；`git pull` 跳过（playbook 明确不执行上线）** | 产品 `ebe8f50` + 证据 `69d4c21`/`d8ffd53`（均已 push） | `docs/batch2d-stepH2b1.md` |
| H2b2 | **Step 0 扫描完成（2026-09-22）**，无裁决项 | — | 停入队 + 删资产；`configurator.css` / `configurator.js` **整文件删除**；⚠️ 删 `functions.php` **187–190 共 4 行**（185–186 必须保留，205 行仍在用）；基线＝H2b1 预检副本 |
| H3 | 未开工 | — | — |
| H4 | 未开工 | — | 前置：邮箱 `info@` → `sales@` |
| H5 | 未开工 | — | — |
| H6 | 未开工 | — | 候选 +1：`sinofresh_formula_*` sessionStorage 无读者 |

**H2b1 门/E2E 摘要**：静态 S1–S8 全过；75 页基线 + 75 页候选；主门 **PASS 21 条 / 0 FAIL**
（58 页差 / 17 页同，逐字节重建）；破坏矩阵 **10/10**；三条负对照全 FAIL（as required）；
**可复现性 12/12 逐字节**；E2E **E1–E9 全过**。计划外行为变化（两个固定层落位 132/68 → 现代引擎收敛到
全站取值）已实测，**用户判定为收敛而非回归**。详见 `docs/batch2d-stepH2b1.md`。

**⛔ 立项规则变更（用户 2026-09-22 明确）**：① **playbook 不执行上线** ⇒ 各批**不开 Step 6 `git pull`**；
② **H2b2 起的基线＝上一批的预检副本，不是 live** ⇒ 预检副本成为"当前最新候选"的唯一载体，
**在下一批用完之前禁拆**（H2a 的"pull 完再拆"顺序作废）。因此 dev 站 live 主题会长期停在 pre-H2b1（`2.10.55`＋配置器），
那是预期状态，不是漏做 pull。

**服务器状态**：未 pull；authority guard 未删；DB 未动。
**预检副本仍然挂着且必须保留**：`wp-content/themes/sinofresh-theme-preflight/`（＝`ebe8f50` 树，349/349 逐字节）
＋ mu-plugin `zz-sf-preflight.php`。H2b2 的基线就是它，**拆掉等于自毁基线**。
复核锚点（2026-09-22）：无头命中 `2.10.55` ＋ 132 处 `class="configurator`；带头命中 `2.10.56` ＋ 0 处。

