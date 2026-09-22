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

**④ 详细内容区（H3 已做 ⇒ ⚠️ 只落地 4 块，Shelf Life 不单列）**

> ⛔ **下面这段模块顺序是 H3 的原始计划，已被用户裁决部分作废**（详见 §第九部分【H3】"原文/裁决后"对照表
> 与 `docs/batch2d-stepH3.md` §1）。**实际落地**：Recommended For / Use Cases / Who It's For /
> Packaging & Specifications（Container Options / Additional Packaging / Color Options / Storage / Carton Dimensions）。
> **Ingredients / Guaranteed Analysis / Formula 不再渲染**（⑤ 两带已承担）；**Shelf Life 无独立行**。

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

**⑥ Sampling Process（H3 已做）**

> ✅ 文案与 4 步结构的**唯一真源**＝`sinofresh_sampling_steps()`（`functions.php`）。
> 它同时喂 ① 可见带 `[sf_formula_sampling]` ② HowTo JSON-LD ③ **H4 弹窗**（H4 必须复用，不得另写一份文案）。
> 改它 ⇒ 三处同步。下面这段结构描述保留作设计意图参考。

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

## 第六部分：工作铁律（11 条）

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
⛔ **并行 Edit 是静默丢改动，不是报错**（2026-09-22 实测）：同一条消息里对同一文件发两个 Edit，
两个回执都写「Successfully edited」，**后写的那次把先写的整个覆盖掉** —— 因为两次都基于同一份
快照、各自整文件落盘。丢的那一处**不报错、不留痕**，只能在事后 grep/read 时表现为「这次编辑
像是没生效」。判据：改完立刻用 `grep -c` 回读**每一处**断言（不为「有没有改」而读，是为
「几处改动都还在」而读）。多文件并行没问题，同一文件必须串行。

**【铁律10】先过门再上线**
线上从不服务未过门的字节。

**【铁律11】门的判据形状决定它的盲区**
2026-09-22 H5 实测，一次同族事故的第三次复现（H4e「掩码抹掉内容」→ H5-0「类没变≠视觉没变」→ H5「三个载体只改两个」）。
**一个门只能回答它那句话所问的问题**，而人读到的永远是「门全绿」。所以：
① **声明粒度必须与承载粒度一致**。同一串落在 `alt` / `data-label` / `aria-label` 三个属性上，
就必须声明**裸串**；声明成 `alt="串"` 形状，另外两个属性**天然在判据之外**。
② **白名单门必须带第三判据：覆盖断言**（批次跑完，声明的旧串出现次数 **= 0**）。
缺它则「没改 = 没变 = 与基线逐字节相同 = 相等 = 全绿」——
**反演式门对「漏改」结构性失明**，它只证「改了的都改对了」，不证「该改的都改了」。
③ 覆盖断言要用**负向前瞻**（`old(?!\s*—\s)`），因为**新串以旧串为前缀**，
朴素的 `old in text` 在正确候选上也不为 0，断言写不下去。
④ 同一事实还要**以不变式形式再声明一次**（本次：*同一页内，同一张图只有一个 alt*），
这样即使声明表本身过期，不变式仍然会响。
⑤ 判据修好后**必须用真实的坏样本验它响**（本次：先在**未修态**捕获页上跑，看它 FAIL；
再在补正态上跑，看它 PASS。两侧都要有）。

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

### 【前置改动：邮箱变更】—— ✅ 已执行（`24da600`，2026-09-22）

在 **H4 之前**自动执行：`info@zxpet.com` → `sales@zxpet.com`

**⚠️ 本节第 5 条（涉及改 DB 时停下汇报）已触发并已裁决。** 实测改动面：
主题侧 **9 处 / 5 文件**、DB 侧 **10 行 / 3 表**。四项裁决（用户 2026-09-22，全按推荐 A）：
① **全站统一** `sales@`（含联系页 mailto／PDF 页脚／证书邮件署名／法务页正文）
② `sf_contact_email` 连 **Organization schema** 一起改（单一真源）
③ TranslatePress 6 行**走 SQL 同步 `original` 列**（三行 `translated` 全空、status 0 ⇒ 无译文可破坏）
④ 三张法务页正文**一起改**
全档 ⇒ `docs/batch2d-stepH4e.md`｜扫描＋停机报告 ⇒ `docs/batch2d-stepH4-scan.md`

⛔ **本节第 3 条「CF email-protection 会自动跟随」是对的，但它带来一个门设计上的硬约束**：
CF 混淆**每次响应换密钥**，而既有掩码门 `sf_masked_cmp.py` 把 blob 直接抹成 `MASK`
⇒ **看不见"里面编的是哪个地址"**。本批因此改用**解码式归一化**，
并新增 **A/A 自检**（同一状态两次抓取，零误报）作为门可信度的前置条件。详见 **附录 A.9**。

原始范围（保留作意图参考）：

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
6. H4 新建的询盘表单收件人用新邮箱 —— ⛔ **改为直接读 `sf_contact_email`，不要再硬编码**
   （本次硬编码三处正是这个前置改动存在的原因；该重构不在本批范围，登记 H6）

**扫描口径补充（实测踩到）**：第一遍扫描的文件清单只到
`functions.php` / `style.css` / `assets/` / `inc/` / `templates/` / `parts/` / `patterns/`，
**漏了 `tools/`** ⇒ 差一处客户可见的 COA 生成器页脚。**扫"全站"必须显式包含 `tools/`**。
另：⛔ **header topbar／footer 联系行／悬浮邮件按钮在源码里搜不到 `info@`**
（它们走 `{{sf-email}}`，真源是 DB 选项）⇒ **只搜源码会把这三处判成"没问题"**。

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

### 【H3】内容区 + FAQ + Sampling —— ✅ 已执行（`4ca3aea`，2026-09-22）

> ⚠️ **本节原文的三处范围已被用户裁决改写**（见 `docs/batch2d-stepH3-scan.md`），落地以裁决为准：

| 原文 | 裁决后 | 理由 |
|---|---|---|
| 内容区 6 块，含 **Ingredients / Guaranteed Analysis / Formula** | **只做新增**：Recommended For / Use Cases / Who It's For / Packaging & Specifications（5 子块）。三块**不重渲染** | ⑤ `[sf_formula_detail_actives]` 两带已承担；`functions.php:1893-1900` 记载重复渲染是上一批专门删掉的 |
| **背景交替 white / bg-light**（逐块） | **内容区整段一色 `card-white`**；交替**只用在相邻带之间** | ④/⑤/⑥ 同色是一整片"this formula's data"面（`style.css:8103-8111`），逐块条纹会从中间切开它 |
| 6 子块含 Shelf Life 单列 | **Shelf Life 不单列**（H2a 参数表已展示） | 同一事实两个来源 ⇒ 必然漂；`sf_formula_shelf_life` 死键登记 H6 |
| （补充）Sampling 4 步 + HowTo | 做成**单一渲染函数** `sinofresh_sampling_steps()`，**H4 弹窗复用同一份** | 否则三条消费路径（带 / schema / 弹窗）会各自漂 |

**仍成立的部分：** 命名空间 `.sf-fdetail-content`；meta 空值整块不渲染；DIFF 集合 21＋21＝42 页；
JSON-LD FAQPage 不变 + HowTo 新增；详情页无点轨（实测铁律）。
Sampling 四步是否与 playbook 第十部分【⑥】的文案逐字一致，以 `sinofresh_sampling_steps()` 为唯一真源。
**Step 1–5 全过门 + E2E 全过 ⇒ 详见 `docs/batch2d-stepH3.md`。**

### 【H4】弹窗表单 + 悬浮按钮

> **✅ 已执行完毕（2026-09-22）：Step 1–5 全过门 + E2E 全过（31 ok / 0 FAIL，连续三遍绿）；
> Step 6 `git pull` 按规则跳过。全档 ⇒ `docs/batch2d-stepH4.md`；扫描＋四项裁决 ⇒ `docs/batch2d-stepH4-scan-body.md`。**

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
5. 4 步打样流程内嵌 —— ⛔ **必须复用 `sinofresh_sampling_steps()`（H3 已建立，见 `docs/batch2d-stepH3.md` §10）**，
   **不得另写一份文案**；改它 ⇒ 可见带 / HowTo JSON-LD / 弹窗**三处同步**
6. 弹窗移动端全屏抽屉

**⛔ 四项裁决（用户 2026-09-22 全按推荐 A 拍板，执行结果见 `docs/batch2d-stepH4.md` §9）：**

| # | 裁决 | 理由 |
|---|---|---|
| **D1** | **会话行取自当前配方元数据**（与参数带**同一份** meta，服务端按 post id **重算**，不信客户端） | 详情页今天**没有表单**（H2b2 已删配置器）⇒ 「自动带入」无来源；重算同时把客户端伪造挡在门外 |
| **D2** | **胶囊落悬浮栈内首位，胶囊形**（`width:auto`、`border-radius:26px`、52/44px 高） | 栈是贴底锚定，**首位＝最上**，挪不动既有三钮 |
| **D3** | **就是栈内那个胶囊**，不另设页内按钮 | 一个 CTA 两副面孔会漂 |
| **D4** | **纯邮件**：不抄送客户、不做自动回复 | 自动回复是独立决策，且「客户提交了」的即时反馈由弹窗成功态承担 |

**⛔ 本批新增的三条硬规则（详见 `docs/batch2d-stepH4.md` §2/§3/§6）：**

1. **标记必须打印在读它的脚本之前**：`wp_print_footer_scripts` 挂 `wp_footer` **优先级 20**，
   所以任何「由脚本读取的页脚标记」必须挂在**更早**的优先级（本批用 **5**）；同时脚本里**不要假设顺序**
   （`readyState === 'loading'` ⇒ 等 `DOMContentLoaded`）。**这条改动的效果在字节里完全看不见。**
2. ⛔ **不要往 shrink-to-fit 的 flex 列里加更宽的子女**：`.sf-float-stack` 靠 `right:24px` 定位、
   宽度由最宽子女决定，且**有显式宽度的子女在 `align-items:stretch` 下退化为 flex-start**
   ⇒ 150px 的胶囊会把三个 52px 圆钮挤左 **98px**。修法＝给栈 `align-items:flex-end`（同宽时是空操作）。
   **任何往悬浮栈里加东西的批次都要先量既有三钮的坐标。**
3. **改了 `style.css` 就要两处同步 bump**（`functions.php` 的 enqueue ＋ `style.css` 头部 `Version:`），
   本批 2.10.57 → 2.10.58 → 2.10.59。

**回归：**
- DIFF 集合：21 详情页 + 21 zh
- 表单提交实测（真发邮件到 sales@）—— **实测，共 5 封**
- 反垃圾验证 —— **实测：蜜罐最先被拒；1117ms/1628ms 提交被拒且断言时钟确实重打**

### 【H5】SEO/GEO 优化 —— ✅ 已执行（产品 `1eafe62` ＋ 修复 `2017dbe`，2026-09-22）

**范围（原计划 → 七条裁决后的实际）**

1. Product Schema 强化
   - additionalProperty：**剂型页 0/16 → 16/16**（复用 `sinofresh_formula_spec_cell()` 读 `sf-facts-mini` 四行；
     死锚点 `sf-spec-list` 与遗留表在剂型页命中 0）。`name` 用**可见标签**（`Packaging formats` 印作 `Packaging`）
   - offers：**渲染器优先，有数据才输出**。`sf_formula_price_tiers` 全空 ⇒ 今日 0/58 页输出，代码已就位。
     只认**整格纯小数**（`1.20` / `$1.20` / `USD 1.20` / `1.20 USD`）；**`1,200` 与区间跳过不解析**（否则发出去的价格差三个数量级）
   - isRelatedTo：58/58（读页面上**可见的** tile / card 链接，按序）；audience：**页头写明物种的才有**（`sf_formula_species` 全空 ⇒ 8 剂型里只有 4 个标题写了物种，其余 4 个**不给**）
   - material：**登记 H6**（本批不做）
2. Organization Schema 补 `knowsAbout`：**10 条**（8 个剂型标签 ＋ 2 条服务线），75/75
3. 图片 ALT 规范化：**只做规范化**——logo `alt="sinofresh"` → `"SINO FRESH logo"`（150＝75 页头＋75 页脚，
   真源是**媒体库 96 号附件**的 `_wp_attachment_image_alt`，不是模板）＋ 8 个剂型商品图各加视觉短语（314 处属性值 → 见下）
4. WebSite schema：**登记 H6**
5. 内容 80/20 审计：**只出报告**（`docs/batch2d-stepH5-audit-8020.md`），不改页面

**回归（H5 不能用字节门，见铁律11）**
- **JSON-LD 语义门**：每块 parse 后 deep-equal，允许**新增键**、禁改值/删键；且**新增键路径集合 = 声明的集合**
  （未声明的新增也 FAIL）
- **渲染 HTML 白名单字节门**：把 ld+json 挖掉、把声明的新串反演回旧串，然后要求逐字节相等
- **覆盖断言（第三判据，缺它则上述两门都能在漏改 126 处的构建上全绿）**：
  声明的**旧裸串**在候选上出现次数 **= 0**；负向前瞻 `old(?!\s*—\s)`，因为**新串以旧串为前缀**
- **不变式**：*同一页内，同一张图只有一个 alt*（同一张图有三个载体：模板缩略图 / 卡片 / 图集首帧+舞台）
- **两门必须同时成立**，另加 A/A 自检、破坏矩阵、具名负对照

⚠️ 本批**不改 CSS** ⇒ 版本令牌不动（**仍是 `2.10.60`**）⇒ 两态 provenance 只能**按内容**证
（基线 `alt="sinofresh"`×150 且 `knowsAbout`×0；候选 `alt="SINO FRESH logo"`×150 且 `knowsAbout` 满）

**结果（2026-09-22 完成，产品 `1eafe62` ＋ 修复 `2017dbe`；9 文件 +508/−77，零 CSS）：**
主门 **79 断言 / 0 FAIL**（`alt_totals` 398→398、旧串 **0**；logo 150→150、left 0；`isRelatedTo` 58、
`audience` 32＝12 formula_EN＋12 formula_ZH＋4 product_EN＋4 product_ZH、剂型页 `additionalProperty` 16/16、
`knowsAbout` 75/75、`offers` 0/58）／**A/A 3/0**／**破坏矩阵 17/17**／**具名负对照 7/7**／
**E2E 20 passed / 0 failed**（75 页、0 console error）／**截图 11/11**。
本批**唯一的 DB 写**＝媒体库 **96 号附件**的 `_wp_attachment_image_alt` → `SINO FRESH logo`（回滚＝改回 `sinofresh`）。
⛔ **产品图的同一个串有四个载体**，第四个（`button.sf-gallery__thumb`，**运行时由 `formula-gallery.js` 构建**）
**不在任何一份捕获 HTML 里，任何基于捕获的门永远看不见它** ⇒ 必须写成不变式「页内一图一 alt」＋
"缩略图保持装饰性"的**显式断言**。详见 `docs/batch2d-stepH5.md` §5。

### 【H6】数据迁移 + 清理 —— ✅ 已执行（产品 `9de31e5`，2026-09-22；**五批收尾批**）

**范围（原计划 → 六条裁决后的实际）**

1. 旧 CSS 清理 —— **48 条选择器**
   - `.sf-facts__*`（H1 遗留，14）／ `.sf-spectable__*`（批 E 遗留，23）／ `.sf-fdetail-media__*`（H2a 遗留，13）
   - 外加 `.configurator__summary-value`（H2b2 遗留，1）
   - **`style.css` 300,185 → 291,209 B（−8,976 ＝ −8.77 KB）**，9,540 → 9,272 行；
     工具实测 **48 条死选择器 / 36 个规则块**，另清 1 个 `@media` 空壳、保留 1 条部分规则
   - ⛔ 两种情形**不能整块删**：① 规则携带选择器列表且只有一半是死的
     （`.sf-facts__row, .sf-num {…}` ⇒ 只删选择器文本）② 死类名**只出现在注释里** ⇒ 先长度保持地剥注释再判定
2. 旧 PHP 函数清理 — **1 个孤儿渲染器**（`sf_formula_actives`，注册行 ＋ 函数体 ＋ 文档块，共 118 行）
   - ⛔ **不能连带删它的两个解析助手**：活着的 `sf_formula_detail_actives()` 用
     `sinofresh_formula_split_top_level()` / `analysis_pairs()` ＋ `.sf-actives__*` 三组样式 ⇒ **助手与样式全部保留**
3. 旧 JS 清理 — **孤儿脚本 0**（本项关闭）；实做的是 `formulas.js` 里的**一处死写 ＋ 一个死分支**
   （`sessionStorage.setItem('sinofresh_formula_'+slug)` 写侧无读者；`getElementById('configurator')` 的滚动分支）
4. MOQ 三处对账 —— **只出表，不改值**（用户裁决"保持现状"）⇒ 见下 §结果

**外加（同一事实的第四面）**：`sf_formula_grid` 输出的 **K2 死载荷**
`<script type="application/json" class="sf-formulas-data">` —— 唯一读者是已随 H2b2 删除的 `configurator.js:readFormula()`。

**回归**
- DIFF 集合：**两个 ver 令牌 ＋ 60 页的载荷元素**（本批动了 `style.css` ⇒ 两处同步 bump `2.10.60 → 2.10.61`，`formulas.js 1.1.0 → 1.2.0`）
- 全站功能回归：**四条判据**（字节证明／覆盖断言／不变式／**遮蔽读回**）＋ 几何两态 ＋ 浏览器 E2E

**⛔ H6 待办累计清单（15 项）—— 逐项裁决结果见下方 §结果**

| # | 待办 | 出处 |
|---|---|---|
| 1–4 | H6 原始 4 项：旧 CSS 三类残留 / 已删短码的 PHP 残留 / 无引用 JS / MOQ 三处对账 | 本节上方 |
| 5 | `sinofresh_formula_*` sessionStorage **写侧无读者** | `docs/batch2d-stepH2b2.md` §8 #4 |
| 6 | K2 `.sf-formulas-data` 失去唯一读者（60/75 页、72,720 B） | `docs/batch2d-stepH2b2.md` §8 #1 |
| 7 | `formulas.js:110` 的 `getElementById('configurator')` 死支（有 `if` 保护，不报错） | `docs/batch2d-stepH2b2.md` §8 #2 |
| 8 | `style.css:1220` 的 `.configurator__summary-value` 死选择器 | `docs/batch2d-stepH2b2.md` §8 #3 |
| 9 | ⛔ **`sf_formula_shelf_life` 无渲染器的死键**（`inc/formula-admin.php:42/106` 注册；H2a 行读的是 `sf_formula_specs`）—— 与 H2a 的 `Shelf life` 行是**一对**，必须同时裁决 | `docs/batch2d-stepH3.md` §8 #1 |
| 10 | ⛔ **`sales@zxpet.com` 在三处被硬编码**（`functions.php:4925` 收件人、`config-pdf.php` 两条 `Cc:`），而真源是 `sf_contact_email` 选项 —— 本批**没有**顺手重构（会让 diff 超出声明）。应收敛成读选项 | `docs/batch2d-stepH4e.md` §10.3；`docs/batch2d-stepH4-scan.md` §5 C2 |
| 11 | ⛔ **询盘弹窗提交成功后没有复位路径**：`form.hidden` / `success.hidden` 一旦翻转就不再复原 ⇒ 提交过的访客再点胶囊看到的是确认页而不是空表单。**不是 H4 引入的**（H4 没写复位），需决定：复原、还是把弹窗做成"一次性" | `docs/batch2d-stepH4.md` §11；附录 A.10 #14 |
| 12 | ⛔ **`sf-facts-mini` 的 4 行与 H3 内容区参数行有 3 项语义重叠**（Certifications / Lead time / Packaging 在两处都渲染）⇒ **双真源漂移风险**。H5 若以 `sf-facts-mini` 供剂型页 `additionalProperty`，会让"同一事实两个来源"从 2 处变 3 处。**与第 4 项「MOQ 三处对账」合并处理**（`functions.php:1994` 已有注释承认这个坑） | `docs/batch2d-stepH5-scan.md` §5 #3 |
| 13 | ⛔ **`theme.json` 的 `styles.elements.<tag>` 是"类未声明就掉"的隐式来源**：`styles.elements.h1.typography.fontWeight = 700` 只在元素名上，`.sf-formula-hero__title` 从未声明 `font-weight` ⇒ h1→div 时字重从 700 静默掉到 400（主门 0 FAIL）。**全站其它"由 h1 改来"或"将被改名"的元素需按三处枚举复查**（主题 CSS 元素选择器 / `theme.json` `styles.elements.<tag>` / 渲染页内联 global styles） | `docs/batch2d-stepH5-0.md` §2；附录 A.12 #1–#3 |
| 14 | ⛔ **Product 的 `material` 未声明**（H5 裁决 C：本批只做 `isRelatedTo` + `audience`）。源码 0 处；`sf_formula_*` 无材质字段 ⇒ 要么补一个真源（`sf-facts-mini` 的第 5 行？），要么明确不做并记档 | H5 裁决 C；`docs/batch2d-stepH5-scan.md` §3 |
| 15 | ⛔ **`WebSite` schema 全站缺**（H5 裁决 G：登记本批）。缺 `WebSite` + `SearchAction` ⇒ 站内搜索不被识别；需决定是否上线（影响 SERP 的 sitelinks searchbox） | H5 裁决 G |

**结果（2026-09-22 完成，`9de31e5`；主题树 **+93 / −505**，本批零新增 CSS、零新增 JS）：**

主门（`tools/b2d_h6_confine.py`）**四条判据全绿**：字节证明 **75/75**（折叠两次令牌、剥 60 页载荷 71,832 B、
掩 10 类噪声）／覆盖断言 **3 条旧裸串各 0 次**／不变式 **0 页计数变化**、logo alt 150/150／
**遮蔽读回 23 页 0 差异**、46 个被掩的 currency value **解不出 UTF-8**（证明它不是文本）。
**破坏矩阵 11/11（0 空转）**／**具名负对照 7/7**／**源码不变式 32 项**／**合成候选全绿**（门的可信度闭环）。
**浏览器 E2E 34 ok / 0 FAIL**；**几何两态 81 页面视图**（见下"方法①"）；**截图 14/14**
（首跑 2 帧被拒：一帧裁剪落在折叠线以下 ⇒ 空白 192 B、一处选择器凭记忆写错 ⇒ 脚本停机；两处均已修并留档，见"方法④"）。

六条裁决的落实：起订量**保持现状**（只出对账表）；`material`／`WebSite` **登记未来批**；
`sales@` 已完成（H4e）；弹窗**不复原**；`sf_formula_shelf_life` **保留**。
⛔ **唯一冲突**：soft-chews 的起订量在 `page-products.html` / `front-page.html` / `404.html` **三处独立字面量**
写的是 `from 500 units`，而真源（`sf-facts-mini`）与 42 个详情页 hero 是 `from 500–1,000 units`
——"+三处对账"这个提法**漏的恰好就是这三处**；其余 7 个剂型六处全部一致。按裁决**不改值**。
⛔ **实测残留（不在声明内 ⇒ 不动）**：`.sf-spectable` **根类** 30 处、`.sf-facts` **根类** 44 处仍是死的；
`data-form` / `{{FORM_SLUG}}` 因死写删除而实质归零，但属性仍在标记上 ⇒ 留给下一批标记整理。
⛔ 载荷体积**实测为 71,832 B**（扫描档曾记 72,720 B，差 888 B）⇒ 已在本档与提交信息中更正。
⛔ **另实测到一处内容脏数据（非本批引入、按裁决不动，但须上线前清理）**：post 158
（`joint-support-soft-chews`）在 **18:21:29** 被 wp-admin 编辑写入两段**测试占位文本**
（`Recommended For` → `testsadasdfasf`、`Use Cases` → `sdasdasdasad`，EN＋zh 两侧都渲染），
并留下 `sf_formula_price_tiers` 的测试值 `[{"qty":"200","price":"2.5"}]`。
dev 是**独立 WP**（独立 DB `sinofresh`、`blog_public=0`、全站 Basic Auth）⇒ **不是线上事故**，
但**会随内容一起上线** ⇒ 已在 `docs/batch2d-stepH6.md` §8/§9 登记为"上线前清理项"。

**⛔ 15 项待办逐项处置（收尾核对表）：**

| # | 处置 | 落点 |
|---|---|---|
| 1 | ✅ **已做** —— **48 条死选择器 / 36 个规则块**（＋1 空壳、保留 1 条部分规则），`style.css` **−8,976 B** | `9de31e5` |
| 2 | ✅ **已做** —— 删注册行＋函数体＋文档块 118 行；**助手与 `.sf-actives__*` 保留** | `functions.php` |
| 3 | ⊘ **关闭** —— 实测孤儿脚本 0；改为做 `formulas.js` 的死写＋死分支 | — |
| 4 | ✅ **已做（只出表）** —— 八剂型 × 六处对账，唯一冲突＝soft-chews 三处独立字面量；**按裁决不改值** | `_backup/b2d-h6-geom/moq-recon.json` |
| 5 | ✅ **已做** —— 删 `sessionStorage.setItem('sinofresh_formula_'+slug)` | `formulas.js` 1.2.0 |
| 6 | ✅ **已做** —— 删 60 页载荷元素（**实测 71,832 B**，非 72,720 B） | `functions.php` |
| 7 | ✅ **已做** —— 删 `getElementById('configurator')` 滚动分支 | `formulas.js` |
| 8 | ✅ **已做** —— 删 `.configurator__summary-value` | `style.css` |
| 9 | ✅ **裁决：保留**（后台对"保质期"的唯一记录，21/21 有值；删字段会让值变孤儿） | 无动作 |
| 10 | ✅ **已完成（H4e）** —— 用户裁决不需要额外动作 | — |
| 11 | ✅ **裁决：不复原**（H4 新建，用户裁定） | 无动作 |
| 12 | ✅ **已并入第 4 项** —— 对账表已覆盖 `sf-facts-mini` ↔ H3 参数行 ↔ 三处独立字面量 | 同上 |
| 13 | ⊘ **关闭** —— 全站只有一个实例，H5-0 已修；留登记：`.sf-slide__eyebrow` 若要显式化补 `font-size` | — |
| 14 | ⏳ **裁决：不做，登记未来批**（`material` 无真源，补它＝新增数据） | 未来批 |
| 15 | ⏳ **裁决：不做，登记未来批**（⛔ 前提不成立：**本站没有站内搜索**，`SearchAction` 会是虚假结构化数据） | 未来批 |

**本批新增的四条方法论（适用于后续任何批）：**

1. ⛔ **删除外部资源（CSS/JS）时，"字节门全绿"与"渲染没坏"是两件事。** 外链文件的内容**从不出现在任何捕获里**
   （页面只带 URL ＋ 令牌）⇒ 删 8.8 KB 对字节门完全不可见。必须**浏览器两态实测**，
   且比较器要先断言**两侧服务的不是同一份 sheet**（相同则 FAIL）—— 否则"两侧服务同一份 sheet"会打出完美一致却什么都没证明。
2. ⛔ **一个断言只要"总是成立"，它就没有证明任何东西。** 本批两次踩到：
   ① 破坏矩阵的靶串在页面上不存在 ⇒ 破坏是**空转**却显示"被捕获"（修法：builder 一律**返回改动量，为 0 判 INVALID**）
   ② 浏览器里剪贴板**读回恒为空**（`clipboard-write` 自动授予、`clipboard-read` 不授予，四条读回通道全被拒）
   ⇒ 断言退化为恒真。修法都是加**具名负对照**，要求"破坏必须改变被观察量"。
3. ⛔ **测噪声优先于测差异；"基线是谁"要用证据确认；两态渲染比较的前提是站点静止。**
   - **差异不能直接解释**：几何首跑 191 处差异，先做 **A/A（同一份安装扫两遍）** 分类，
     凡 A/A 就不同的即噪声（本批三类：动画相位 ⇒ 采样前冻结 transition/animation；
     Gravity Forms 的 uniqid id ⇒ 掩 id 内的 8+ 位十六进制连串；
     `.sf-slider-progress__bar` 由 JS 每帧写内联样式 ⇒ 只掩它的盒子与 `transform`，其余属性照比）。
     **处理完噪声的 A/A 必须归零，才去跑真两态。没有 A/A 的"0 差异"不可信，A/A 不通过的"有差异"也不可信。**
   - ⛔ **基线的提交身份必须用证据核实**：本批几何门一度装成 `084b246`（H5-0 修复），
     而字节门的基线是 H5 候选 `2017dbe` —— 两者之间夹着 H5 的产品提交，
     于是**几何比较把 H5 的改动（7 个 `SPAN.sf-fdetail2__chip` ＋ 价格阶梯表）算成了 H6 的差异**。
     "基线＝上一批预检副本"这条铁律在**两个门读取的基线不一致**时会静默失效
     ⇒ 每批的检查表要**显式写**"本批所有门的基线＝同一提交 X"，不能靠"我记得装的是基线"。
   - ⛔ **站点必须静止**：本批候选态扫描**进行中**（18:17–18:22），wp-admin 在 **18:21:29** 改了 post 158
     （`joint-support-soft-chews`）。症状极具误导性：**同一个提交**下 EN 1440 少 24 个元素、EN 390 多 24 个
     —— 看起来完全像"响应式被改坏了"，实际是**编辑器在打字**。
      ⇒ 新增 `content_fingerprint()`：扫描**前后各取一次**内容指纹（REST API 的 `id,modified`，分页取全），
      不同即 FAIL。⚠️ **它对 18:21:29 那次编辑的实测结论**：编辑同时写入了两段**测试占位文本**
      （`Recommended For`→`testsadasdfasf`、`Use Cases`→`sdasdasdasad`，EN＋zh 两侧），
      但**几何扫描（18:33/18:38）已在该编辑之后** ⇒ 两态都含它 ⇒ 0 差异成立；而**字节门捕获（约 17 时）早于它**，
      所以**截图帧上能看到这两段文本**。⇒ **读帧必须连同帧的时间戳一起读**，否则会把"内容变了"误读成"渲染变了"。
      ⛔ **守卫的"不可被静默关闭"要用对理由**：它走 `curl -u <dev Basic Auth>`，**它要凭据**（只是不读 DB）；
      真正拦住静默失效的是 `if rc != 0 or not out.startswith('['): raise SystemExit`
      —— **读不到就中止整轮**。理由写成"凭据无关"等于给门留了"401 就静默继续"的口子
      （本项目已踩过一次同型坑：不带凭据 ⇒ curl 拿到 401 页 ⇒ 两侧哈希同一个错误页 ⇒ 静默全绿）。

4. ⛔ **"证据存在"与"证据内容"是两条断言；选择器不能凭记忆写。**
   - 截图首跑有一帧**尺寸完全正确、内容全白**（192 B、209×38、4 个 distinct 字节值）——
     凡是只断言"文件在 ＋ 尺寸对"的门，这一帧会**全绿通过**。真正抓住它的是**"非平帧"断言**
     （解压 IDAT 后 distinct 字节 > 8）。**"尺寸对"永远不是"内容对"的证据。**
   - 一处选择器凭记忆写成 `.sf-actives`，**全站四份捕获（含基线）命中为 0**，真实容器是 `.sf-fdetail-actives`。
     修法不只是一改：选择器改对，并在脚本里写明"全站无 `.sf-actives`，别再写它"。
     **对照设计**：工具应当**拒绝拍摄不存在的元素**（`raise SystemExit`），
     而不是把 `null` 当 0 静默放过 —— 后者的产物是"看起来正常的空证据"。
   - 该帧被拒的另一半原因正是方法③的第一条：**折叠线以下的元素裁剪不可信**
     （`screenshot <selector>` 只在元素位于初始 `scrollY=0` 视口内时正确）⇒ 一律改用**视口帧 ＋ 说明滚动偏移**。

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

⛔ **门要按批次形状选，不能沿用上一批的**（铁律11）。判据清单至少三条，缺一条就是全绿假象：
① **位移/字节**（改了的都改对了）② **语义**（结构化数据 parse 后 deep-equal，允许新增键、禁改值/删键）
③ **覆盖**（该改的都改了：声明的旧串在候选上出现次数 **= 0**，裸串粒度 + 负向前瞻）
外加 ④ 把同一事实写成**不变式**再断言一次（本次 H5：*同一页内同一张图只有一个 alt*；H6：*遮蔽读回*）。
判据改完必须**两侧验响**：未修态要 FAIL、修好态要 PASS；再进矩阵与具名负对照。

⛔ **开工前先写一行"本批所有门的基线＝同一提交 `<SHA>`"**，并在每个门里**断言**它服务/比对的确实是该提交
（本批几何门曾装成 `084b246` 而字节门用 `2017dbe` ⇒ 把上一批的改动算成本批差异）。
⛔ **凡做"两态渲染比较"，扫描前后各取一次内容指纹**（REST `id,modified`），不同即 FAIL ——
dev 站不是独占的，并发编辑的症状与产品回归**无法区分**。

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

- 遵守工作铁律 11 条
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

## A.6 H2b2 执行期实测（2026-09-22，Step 1–5）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔ **`install` 的"先删后建"前提检查必须是 `if … exit`，不能是 `A && B`**。原写 `git cat-file -e <sha>^{commit} && echo present`，SHA 未 fetch ⇒ 检查失败但 **`set -e` 不拦 `&&` 列表左操作数**，脚本继续 `rm -rf $PRE; mkdir -p $PRE`、死在空 tar：**副本目录还在、里面是空的**。症状不是"install 失败"而是**该主题注册的 CPT 全部 301 回首页**（本次 44 页：`/formulas/` 归档 + 21 详情 ×2 语言）。已修为 `if ! <check>; then echo FATAL >&2; rm -f $MU.tmp; exit 4; fi` ＋ 解包后 `[ -f $PRE/functions.php ] \|\| exit 5` | 一切"先删后建"的脚手架脚本；RULES §Q.3 |
| 2 | ⛔ **换候选前必须 `git -C <server-repo> fetch --prune origin`**：`install` 只从**服务器上的 repo** 取对象，本地 push 到 GitHub ≠ 服务器有该对象。`git fetch` 只取对象、不动工作树（实测 HEAD 与 `git status` 均未变） | Step 4 前置 |
| 3 | ✅ **"删掉一个脚本"可以用注入证明是零行为变化**：`configurator.js` 是**裸 IIFE**（非 `DOMContentLoaded` 包裹，L12 `(function () {`），首句即 `.configurator` 不存在就 `return`。把基线自己那份字节 + 哨兵注进候选页 ⇒ `cfgRan=1`、`sessionStorage` 键不变、`<body>` 轮廓恒 455 节点、几何相同、configurator 请求 0→0 | 任何"惰性脚本"的删除批；⚠️ 若是 `DOMContentLoaded` 包裹则晚注入不执行，必须先确认入口形态 |
| 4 | ⛔ **测"点一下没反应"时不能点会跳转的锚点**：`a.sf-explore__btn` 的 `href="/formulas/"` ⇒ 页面导航、哨兵随旧文档消失、轮廓数"从 485 变 460"其实是在量另一个页面。改法＝**捕获阶段 `preventDefault`**（事件照常传播给元素自身处理器、只抑制跳转）＋ 断言"点击后仍在原路径" | E3；任何"点击后无变化"断言 |
| 5 | **几何对照必须用参考工具的**字段定义**，不能自己重新写一份**：首版 `rect()` 漏了 `bottom` ⇒ `gapWallEdgeToBand` 算成 `NaN`（JSON 序列化成 `null`）；`bandBtn` 漏了 `w`。补齐口径后 **210 项（35 字段 × 6 档）全部一致** | E5；跨批次几何对照 |
| 6 | **"上一批留下的唯一行为变化"要在这一批翻向验证**：删掉承载旧引擎复刻的整个文件后，正确断言是**旧引擎 stub 开/关两态必须相等**，而不是"旧引擎还是老值"。实测 480px `268/0`、1440px `100/0`，差值 **0** | E4；H2b1 附录 A.5 #7 的收口 |
| 7 | ⛔ **`git ls-tree --name-only` 给非 ASCII 路径加引号** ⇒ 与 `find` 的结果直接比会得到"同时新增和删除 12 个文件"的假结论。要用 `-z`（NUL 分隔）。另：工作树里的 `.DS_Store` / `__pycache__` 是未跟踪落地物，文件数断言必须排除 | S4 首轮 349 vs 154 假失败 |
| 8 | ⛔ **负对照要求"非零退出 **且** 有具名判据"**：`functions.php` 整个缺失时，首版是靠 `FileNotFoundError` 退出（rc=1）——数值上"抓到"了，却没有任何判据。静态门因此新增 **S0「必需输入存在」**，负对照台也改成必须带具名检查 | 所有负对照台 |
| 9 | **`class="configurator` 的"出现次数"与 `grep -c` 的"行数"不同**：live 剂型页实测 **210 次 / 132 行**。引用数字必须写明口径（RULES §Q.2） | 全站计数类断言 |

---

## A.7 H3 Step 0 扫描实测（2026-09-22，只读，停机）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔ **「这一批要新建的块」必须先问「这块的数据今天被谁渲染过」**：H3 的 12 个数据源里，`sf_formula_ingredients`/`sf_formula_analysis` 今天各被 ⑤ `[sf_formula_detail_actives]` 渲染 1 次，`sf_formula_specs` 被渲染 **4 次**（④ 卡片 ＋ H2a 三行解析）。照 playbook 字面新增 6 块 ⇒ `specs` 同一页出现 **5 次**，且前两块的「2 次」**正是上一批专门删掉的状态**（`functions.php:1893-1900` 有明确记载）。扫描必须逐块算**现有出现次数**，不能只看"键有没有值" | H3 裁决 1；任何"内容区/信息块"新增批的开场检查 |
| 2 | **「背景色交替」不是局部样式，是对相邻带的重新分节**：详情页 ④ Specification / ⑤ Formula & nutrition / ⑥ Ingredients & composition **同色 card-white**，`style.css:8103-8111` 注释写明 *"the three read as one 'this formula's data' surface"*。在两带之间插入逐块交替的 6 块，会把这片连续面从中间切开 | H3 裁决 2 |
| 3 | **同一个事实存两个来源时，新增块会静默造出重复**：`sf_formula_shelf_life`（21/21 `18 months`）从未被前台读过；H2a 的 `Shelf life` 行是**从 `sf_formula_specs` 解析**那一段得来的。H3 若按 playbook 读键，页面上同一事实出现两次而两处都会漂 | H3 裁决 3 |
| 4 | **「键已注册但 0/21 有值」不等于缺数据、更不等于要停机**：H3 的 12 源里 7 源为此态。`inc/formula-admin.php:26-115` 已注册全部键（含分组/类型/必填级/选项池），缺的只是运营录入。这与 H2a 已获批准的「先发渲染器、后填数据」（`functions.php:1975-1977`）**同一口径** ⇒ 该状态本身不停机，**重复才是停机理由** | 判断塞停的边界 |
| 5 | **只读探针要一次把"全库同前缀键清单"打出来**，不要只查预期的那几个键：`WHERE meta_key LIKE 'sf_formula%' GROUP BY meta_key` 一次就证明「21 条记录只有 8 个键 × 21 = 168 行」，比逐个 `get_post_meta` 更能排除"换了个拼写"的假阴性 | `tools/b2d_h3_dataprobe.php` |
| 6 | **Step 0 的探针必须是零写入**：只用 `get_posts` / `get_post_meta` / `get_option` / `wp_json_encode`，不碰 `update_*`、不建 option、不写 transient。停机报告的说服力来自「**未改任何字节**」这句可被验证的话 | §7 停机声明 |

## A.8 H3 执行期实测（2026-09-22，Step 1–5）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔ **JSON-LD 的序列化在语言管线上不稳定 ⇒ 任何"字面序列化匹配"的断言都对一半页面瞎**。TranslatePress 会把块**重新序列化**：EN 是紧凑 `"@type":"HowTo"` ＋ `https://schema.org`，zh 是 pretty-printed `"@type": "HowTo"` ＋ `https:\/\/schema.org`。实测 **21 紧凑 / 21 精美**，基线候选两侧一致。首版门的标记常量 `'"@type":"HowTo"'` 因此漏掉**全部 21 个 zh 页** | 一切跨语言的结构化数据断言；判据必须走**解析**（`json.loads` 取 `@type`） |
| 2 | ⛔ **"折叠令牌"的断言要写成"折叠后恰好剩 N 页有别"，而不是"折叠后等于 diff 条数"**：本批令牌在 **75 页全部移动**，但只有 **42 页**有实质差异。写成 `folded == len(diff)` 会得到 75 vs 42 的**无解断言** | 所有带 ver bump 的批次的 [1] 门 |
| 3 | ⛔ **掩码比较必须两侧对称干净**：一侧折叠了令牌、另一侧没有 ⇒ 会把令牌判成 75 页全差（假 FAIL） | §3.1 #3；RULES §B/§C 的具象案例 |
| 4 | ✅ **"渲染器先发、数据后填"的批，必须有离线单测兜底**：11/12 个数据源在 21 条记录上全空 ⇒ 实时抓取**永远只走空分支**，页面门在原理上分不出"渲染器работает"和"返回 `''`"。做法＝从 `functions.php` **按内容寻址的 START/END 标记逐字抽取函数体**（不是行号）再跑单测：**54 passed / 0 failed** | 任何"先发渲染器"的批次；与 H2a 的 `functions.php:1975-1977` 同一口径 |
| 5 | ⛔ **负对照要"具名"，`rc != 0` 不算**：`functions.php` 整个缺失时首版靠 `FileNotFoundError` 退出，数值上"抓到"了却没有任何判据。改为每条对照必须打出一行 `FAIL <label>` | 所有负对照台（H2b2 附录 A.6 #8 的延伸） |
| 6 | ⛔ **不可达的守卫是死断言，会一直"通过"**：`sinofresh_formula_content_block()` 里的空值守卫，四个调用方各自先测了自己的字段 ⇒ 任何变异都不可能让它失败。删掉死守卫、把责任落到真正会走到的函数，对照才开始失败 | 写"空值不渲染"类断言前先问"谁能让它失败" |
| 7 | ⛔ **不要拿函数自己的返回值当断言期望**：Storage 断言原写"页面等于 `sinofresh_formula_storage_line()` 的返回"，那函数返回什么都会通过。钉到**字面量**才有约束力 | 一切 `assert(page == f())` 形状的检查 |
| 8 | ⛔ **`set viewport '1440x1000'` 会被 `agent-browser 0.27.0` 静默忽略**：单参数字符串被接受、什么都不做，`innerWidth` 八档恒为 1280 ⇒ E5 "八档响应式"其实把**同一个布局量了八次**。正确写法是**两个参数** `set viewport <w> <h>`，并且必须加 `viewportW == 请求值` 的 **FATAL 断言** | 一切响应式/多视口测试；与 A.5 #1（init-script 只挂在启动命令上）同类：**文档与二进制不一致时以二进制为准** |
| 9 | ⛔ **数 `<details>` 时别忘了页脚手风琴，也别忘了"默认展开第一条"**：详情页共 **12 个** `<details>` ＝ 9 个 FAQ 答案 ＋ 3 个页脚手风琴，且 FAQ 块**默认展开第一条** ⇒ "点第一条"其实是把它**关上**。正确做法＝限定 `.sf-fdetail-faq`、要求 `faqItems==9 && faqOpen==1`、**点一条闭合的**、并断言页脚 3 个手风琴**未动** | E7；任何"点一下打开"的断言 |
| 10 | ⛔ **`<!-- wp:html -->` 分界不进产物，普通注释进**：模板里用它做插入锚点在源码上"看得见"，在抓取页面上**根本不存在**；而 `<!-- Batch C: the formula FAQ.` 这类普通注释**会到达输出**。三处 run 的锚点因此必须分成"源码锚"与"产物锚"两套 | 一切"在模板里插一段"的补丁器 |
| 11 | ✅ **同一 URL 的两种请求头＝live 与候选的复核锚点**：H3 收尾实测无头 `2.10.55`＋2 条 configurator＋210 次/132 行，带头 **`2.10.57`**＋0 资产＋`link` 指向 `-preflight/`＋详情页 HowTo=1。⚠️ 只断版本号不够 —— 必须同时断样式表**来自 `sinofresh-theme-preflight`**，否则顺序错了会静默比**旧字节**（A.5 #1 的同类教训） | 每批 Step 4/5 的候选确证；RULES §Q.4 |
| 12 | ✅ **主题树 695 vs 服务/提交 347 的疑团**：347 是**排除嵌套 `sinofresh-theme/_backup/`（348 个文件）**后的比对集；用 `git ls-tree -z` 数树同得 695。⚠️ `git ls-tree --name-only` 给非 ASCII 路径加引号 ⇒ 别拿它跟 `find` 直接比（A.6 #7） | 一切"文件数/文件集"断言 |
| 13 | **"先发渲染器"不是缺陷，但必须把裁决反写进 playbook 的范围段**：H3 原范围写的 6 块里 3 块与既有两带重复、背景交替与既有连续面色冲突 ⇒ 若只改代码不回写文档，下一批会照着**作废的范围**再犯一次 | 每次裁决后的文档回写（本批 §第九部分【H3】已加"原文/裁决后"对照表） |

## A.9 H4e 执行期实测（2026-09-22，邮箱变更批次）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔⛔ **既有掩码门对本批是瞎的**：`sf_masked_cmp.py` 的 `cf_email_link` / `cf_email_attr` 两条规则把 CF blob 直接换成字面 `MASK` —— 把 `info@` 换成 `sales@` 之后，**掩码后的两页完全相同**，门会打出**全绿**。这不是门坏了，是**掩码把要证的那件事一起抹掉了** | 一切改动落在"被掩码的内容"上的批次；判据必须从"打码"反转为"**解码**" |
| 2 | ⛔ **CF 混淆的密钥逐次随机**（不是固定的）：同一页连抓三次，`data-cfemail` 的 hex 与整页 sha256 **三者全不同**（首字节为密钥，其余异或）。⇒ blob 是逐次噪声**必须去掉**，而 blob 里的地址是信号**必须留下** —— 两个方向相反的要求，**只有解码能同时满足** | 一切涉及 CF 混淆站点的字节级回归；也解释了 H3 基线为何能 75/75 逐字节相同（那里的掩码吃掉了噪声） |
| 3 | ✅ **归一化写成 `norm(t) = clean(decode_emails(t))`，整批塌缩成一条**：`norm(候选) == norm(基线).replace('info@zxpet.com','sales@zxpet.com')`。⚠️ 绝不能用"原样比对"绕过 | 同类改动的最小判据形状 |
| 4 | ⛔ **噪声掩码必须"导入"而不是"重打一遍"**：`NOISE = [(p,r,n) for (p,r,n) in sf_masked_cmp.MASKS if n not in {'cf_email_link','cf_email_attr'}]`，并**断言恰好剔掉 2 条**。手抄一份会在两个工具间各自漂移，也没人拦得住"顺手把 CF 规则加回来" | 一切复用既有掩码集的工具 |
| 5 | ⛔⛔ **A/A 自检应升级为"门可信度的前置条件"**：同一状态的两份独立抓取跑门，**除故意设的 [1] 外任何一条不得触发**。本批首跑**确实报了一屏假 FAIL**（GF 的 `gform_currency` nonce ＋ `gform_phone_dropdown_<microtime-hash>` 逐次变化）—— A/A 是唯一能证明"噪声已清干净"的检查。⚠️ [1] 在 A/A 里**必然**失败（它断言"页面有差"），属设计内 | **所有批次的 Step 3 前置**，不止本批（H2b1/H2b2/H3 都是"直接跑门"，运气好才没踩到） |
| 6 | ⛔ **扫描口径要含 `tools/`**：第一遍文件清单只到 `functions.php`/`style.css`/`assets/`/`inc/`/`templates/`/`parts/`/`patterns/`，漏掉 `tools/make_coa_sample.php` ⇒ 实际 9 处而非 8 处 | 一切"全站找字符串"的扫描；清单要显式列目录而不是靠印象 |
| 7 | ⛔⛔ **改 DB 的批次没有"候选态"**：预检副本能隔离主题字节，**隔离不了 DB**。CF/主题两侧都改了而 DB 没改 ⇒ 门会把"DB 还没跟上"判成回归。⇒ 这类批次必须**先把 DB 改到位再抓候选**，并把"DB 状态"写进声明范围 | 一切触及 option/post/meta 的批次；声明范围要含"哪些行、哪些表、快照在哪" |
| 8 | ⛔ **wp-cli 会抢在脚本之前拒掉未声明的 `--flag`**（加 `--` 也不行）：`--dry-run` 直接报 unknown parameter。改用**环境变量** `SF_H4E_MODE=dry-run\|apply\|revert` | 所有 wp-cli 驱动的补丁器/探针 |
| 9 | ⛔ **回滚快照不能放 `/tmp`**：它可能是唯一的回滚路径，重启即失。放到 docroot **之外**（`_offroot/b2d-h4e-db-originals.json`），并同时留一份在本地 | 一切 DB 改动的回滚设计 |
| 10 | ⛔ **`--apply` 必须"快照存在 **且** 与当前 DB 相符"才允许写**：否则会在已漂移的库上覆盖出错误的回滚点。落盘前再断言 Snapshot **不含 `{sha256}` 令牌**（`esc_sql()` 的 `%` 令牌化，`_backup/*.sql` 同忌） | 所有 DB 补丁器；用户级记忆里那条"落盘 SQL 用裸 `mysqli_real_escape_string`" |
| 11 | ⛔ **E2E 的 JS 里不能写 Python 常量名**（`ReferenceError: OLD is not defined`）：改为 `__OLD__`/`__NEW__` 占位符，由 `measure_js()` 注入 | 一切"把断言值编进 JS 字符串"的 E2E |
| 12 | ⛔ **取正文要取 `.entry-content`，不是 `document.body`**：`body.innerText` 的第一个 `sales@` 是**页脚**，测出来的是全站件而不是文章。联系人页是模板、**没有** `.entry-content` ⇒ 换成 `.sf-contact-card` | E3 类"页面上读到什么"的断言 |
| 13 | ⛔ **子串匹配的"删掉"必须真删掉**：`band-removed` 变异第一版把标记改名成 `…contentX` —— **仍以子串形式包含标记**，判据以为还在场，只有 [2] 抓到。真正删除该子串后 [2]+[6] 同时开火 | 一切"标记在场/不在场"的断言 |
| 14 | ✅ **A.8 #1（JSON-LD 跨语言序列化不稳定）在本批第二次独立复现**：EN 紧凑、zh 精美，仍是 21/21。`schema-email-unchanged` 变异就是为这个坑准备的 —— 只改紧凑形态，若门还用字面匹配就会漏 | 已两次复现 ⇒ 可当定律用 |
| 15 | **"硬编码 vs 单一真源"的代价是可量化的**：`sales@` 在三处被硬编码（`functions.php:4925` 收件人、`config-pdf.php` 两条 `Cc:`），而真源是 `sf_contact_email` ⇒ **下次换邮箱又要改 DB＋三处硬编码**。本批**没有**顺手重构（会让 diff 超出声明范围），登记 H6 | 见 H6 第 10 项 |

## A.10 H4 执行期实测（2026-09-22，询盘弹窗批次）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔⛔ **页脚标记必须打印在读它的脚本之前 —— 而且这件事在字节里完全看不见**。`wp_print_footer_scripts` 挂 `wp_footer` **优先级 20**；弹窗挂在 **20** ⇒ 脚本先打印、解析期同步执行、`querySelector('.sf-inquiry-modal')` 为 null、首个守卫 `return` ⇒ **胶囊永不出现、弹窗永不打开，而控制台零错误、DOM 齐全**。实测字节偏移：脚本 116986 / 弹窗 122203。修法＝标记降到**优先级 5**；**并且**脚本侧不等顺序（`readyState === 'loading'` ⇒ `DOMContentLoaded` 再初始化） | 一切「PHP 打印标记 + 脚本读它」的组合；本条只能由**行为门**守住 |
| 2 | ⛔⛔ **不要往 shrink-to-fit 的 flex 列里加更宽的子女**。`.sf-float-stack` 是 `right:24px` 定位、宽度由**最宽子女**决定的列，且**有显式宽度的子女在 `align-items:stretch` 下退化为 flex-start** ⇒ 150px 胶囊把三个 52px 圆钮**挤左 98px**（1364 → 1266）。修法＝栈上 `align-items:flex-end`（三子女同宽时是空操作）。**同样在字节里看不见** | 一切固定/贴边容器；往悬浮栈加东西前**先量既有兄弟的坐标** |
| 3 | ⛔ **A/A 自检的两侧必须做同样的「摘除声明」**：A/A 的"基线"是**候选状态的第二次抓取**，它**同样带全部新增**；只摘一侧会把 42 个页面全部判成"超出声明的差异"（本批首跑 4 FAIL 全是这个）。主跑里基线没有新增 ⇒ 摘它等于空操作 ⇒ **两侧都摘**才是统一写法 | A/A 模式的一切判据；RULES §Q.5 的延伸 |
| 4 | ⛔ **A/A 的溯源目录也是预检副本**：`want_dir` 不能因为 `expect_change=False` 就退回 `sinofresh-theme/` —— 两个捕获**都**来自 `-preflight/` | 溯源门 |
| 5 | ⛔ **`elementFromPoint` 判等太严会误报"点空了"**：点胶囊命中的是它内部的 `span.sf-float-btn__label`。判据改为「点落在目标**子树内**」（`closest('.目标')`）：既容忍子元素，又仍能抓住坐标漂移 | 一切真实点击的命中校验 |
| 6 | ⛔ **断言不能要求四个按钮同宽**：胶囊本来是胶囊形。判据＝「三个圆 52/44 ＋ 四者**共享右边缘** ＋ 间距 12 ＋ 胶囊在最上」 | E2/E10 类几何断言 |
| 7 | ⛔ **弹窗打开时其背板铺满视口 ⇒ 被它盖住的元素物理上点不到**：点胶囊会命中背板。所以「点胶囊前先关掉已有弹窗」不是便利，否则把"点到背板"误读成"胶囊坏了" | 一切模态交互的复开流程 |
| 8 | ⛔⛔ **长会话会漂移到 `about:blank` / `chrome-error://chromewebdata/`，而漂移后的读数看起来完全像"元素从 DOM 里消失"**。本批因此产生过整整一屏假产品结论。修法：状态探针**先看 `location.href`**，发现漂移就**重启会话**（`close --all` → 凭据 → 打开 → **设头（自定义头＋Basic 一次给全）** → reload）并**走带溯源断言的路径**重开 | 一切长 E2E；与工作记忆里"eval 打到 about:blank"同源，本次给出**可自动恢复**的写法 |
| 9 | ⛔ **状态读取失败必须大声拒跑**，不能返回空对象让后续断言去"推断缺失"。本批假报告「an impossibly fast submission reached the success state」就是空对象被当成"没有成功态"读出来的 | 一切探针封装 |
| 10 | ✅ **探针要报"为什么"而不是布尔**：`form_ready()` 返回 `(bool, reason)`，把「没弹窗 / 没打开 / 表单不是可见块 / 时钟没打上」分清楚 —— 布尔让上面那个假报告多活了整整一轮 | 所有前置条件断言 |
| 11 | ⛔ **"3 秒下限"的断言必须同时断言时钟真的重打过**：`ts` 跨一次打开**必须变化**，否则测到的 delta 是相对上一次打开的，判据没有意义 | 任何时间窗反垃圾的实测 |
| 12 | ⛔ **蜜罐要证明"最先"被拒**：把同一份载荷配上**合法时钟**再带蜜罐 ⇒ 若仍被拒，拒绝只可能来自蜜罐（拒绝文案 `Submission rejected.` 与"太快"的 `Please take a moment…` 不同，可直接判别） | 多层反垃圾的逐层举证 |
| 13 | ✅ **真发邮件是唯一能证"线索可达"的检查**：本批 E2E 真发 **5 封**（标记 `H4 E2E`），收件人＝`sf_contact_email` ⇒ 同时验证了投递链路**与**"收件人读选项而非硬编码" | 表单类批次的 E2E |
| 14 | ⚠️ **成功之后没有复位路径**：`form.hidden`/`success.hidden` 一翻转就不再复原 ⇒ 提交过的访客再点胶囊看到的是确认页。**不是本批引入**（本批没写复位），登记 H6 第 11 项 | H6 |
| 15 | ✅ **本批最该记住的一句**：**两个产品缺陷（#1 顺序、#2 几何）在主门上都是 0 FAIL**。字节门能证"净效应就是这个声明"，**证不了交互**；凡改动触及**顺序或几何**，行为门不是补充而是**唯一**的判据 | 批次立项与门集合的取舍 |

## A.11 H5 Step 0 扫描期实测（2026-09-22，SEO/GEO 批次）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔⛔ **断面的「0 覆盖」必须先把断面的构成查一遍，再下结论**。75 页断面**不含博客单篇**（只有 `blog.html` 列表页）⇒ 直接读「`Article` 0/75」会得出"博客没有 Article schema"的**反向结论**；实际 `functions.php:5017-5100` 的 `is_singular('post')` 生成器**是活的**（`datePublished`/`dateModified`/`author`/`publisher` 齐全）。**本批首轮就差点把这个误报成缺口** | 一切基于固定页集断面的覆盖率统计；与 §Q.5「掩码门的盲区」同源：**工具没覆盖的地方，静默就是全绿／全缺** |
| 2 | ⛔ **注释会与实况脱节，而且脱节处正好是死代码**。剂型页 Product 生成器的注释宣称 `additionalProperty = the Specifications rows (sf-spec-list, with a fallback for the legacy key-facts table)`，实测该页 `sf-spec-list`、`sf-spec-term`、遗留 `flex-basis:35%` 表**命中全是 0** ⇒ 两条分支永不匹配、字段静默缺席 **16 页**（8 剂型 ×2 语言）。H2b1/F1 早已把该带换成 `sf-facts-mini` | **读注释判断"这个字段应该有"之前，先 grep 一遍锚点在渲染产物里是否真的存在** |
| 3 | ⛔ **同一个类名有 `dt`/`dd` 与 `span` 两种历史形态，grep 形态错会得出"两边都缺"的错结论**。配方详情页的真实标记是 `<dt class="sf-spec-term">`／`<dd class="sf-spec-value">`，而生成器的正则是 `<span …>`。详情页之所以有 `additionalProperty`，是因为它**走 post meta，压根不经过那条正则** ⇒ 修剂型页时**不能顺手把 `span` 改成 `dt`**（那条正则只服务剂型页，而剂型页早已不用 spec-list） | 任何"照着现有正则去修另一个页组"的动作 |
| 4 | ⛔ **手册写「自动生成」时，那描述的是期望，不是现状 —— 先量缺口，再决定动词**。手册 H5 第 3 项「图片 ALT 自动生成」，实测 **840 个 `<img>`、缺 alt = 0**，174 个空 alt **全部是刻意装饰件**（语言国旗 150 ＋ 博客头像 24）⇒ 没有"生成"的对象；真正该做的动词是**规范化**（logo `alt="sinofresh"` ×150 该写成 `SINO FRESH logo`）。若照字面做，只能加一层运行时字符串替换，与「模板即单一真源」的架构冲突 | **每次把手册条目翻译成动作前，先量它的前提** |
| 5 | ⛔ **粗算指标必须连口径一起报**。同一页正文词数：粗算（`<main>` 去标签后空白切分）**1,934**，严算（只数 `h/p/li/td/th/dt/dd` 标签内容）**777** —— **差 2.5 倍**，但排序一致。只报数字不报口径，等于给了一个可被任意解释的数 | 一切"内容量/密度"类审计 |
| 6 | ⛔⛔ **换批次类型时，先量「合法 DIFF 集」再决定门的形状**。H2b1–H4 的字节门在 H5 **不能沿用**：加 `knowsAbout` ＝ **75/75 页合法 DIFF**、剂型页加 `additionalProperty` ＝ **16 页合法 DIFF**、logo alt 规范化 ＝ **75 页合法 DIFF**。⇒ H5 的门必须＝**JSON-LD 语义门**（`json.loads` 后 deep-equal，**允许新增键、禁止改值/删键**）＋渲染 HTML 白名单字节门。**沿用字节门 ⇒ 第一批绿就是假绿；放宽成"能 parse 就过" ⇒ 删掉 `brand` 也能过，另一种假绿** | 每批立项的第一步：**这次改动会产生哪些合法差异？** |
| 7 | ⛔ **"数据一直在、只是没人读"是可复用的诊断句式**。手册 H5 要的「包装」数据早在 `sf-facts-mini` 第 4 行（`Packaging formats`，16/16 页齐备），而生成器读的是已消失的 `sf-spec-list`；且 `functions.php:646-690` 的 `sinofresh_formula_spec_cell()` **已有作用域正确的读取器**（限定在 `.sf-facts-mini` 块内）⇒ **零新代码即可修**。先找"现成的读法"再考虑新写 | 一切"字段缺失"类需求：先分清是**没数据**还是**没读对** |
| 8 | ⚠️ **`sf-facts-mini` 与 H3 内容区参数行有 3 项语义重叠**（Certifications / Lead time / Packaging 双处渲染）⇒ 双真源漂移风险。`functions.php:1994` 已有注释承认过这个坑（H3 原作者踩过一次）。H5 若用 `sf-facts-mini` 供 schema，会让"同一事实两个来源"从 2 处变 3 处 ⇒ **登记 H6 第 12 项，并入第 4 项「MOQ 三处对账」** | H6 |
| 9 | ✅ **无 SEO 插件是这条链路的隐性前提**。活跃插件仅 GF / TranslatePress×2 / consent-api / mail-logging / statistics ⇒ 主题 schema 具**唯一权威性**，不需要 FAQPage 那样的 "stand down if an SEO plugin is present" 守卫。**但换环境前这条会变**，guard 该留 | 一切手写 JSON-LD 的站点 |
| 10 | ✅ **`offers` 缺的不是代码而是决策**。数据源 `sf_formula_price_tiers` 存在（渲染器 `sinofresh_formula_tier_table()` 也在），但 21 个配方**全空**；而配方详情页源码已写死不报价的理由（`functions.php:4846-4849`：*"a standard formula is an OEM reference, not a priced SKU, and inventing a price would be worse than omitting the property"*）⇒ 手册要 `offers` ↔ 源码说 OEM 不报价，**两条互斥路线必须先裁决**，代码本身随时可写 | 批次立项时区分「缺实现」与「缺决策」 |

---

## A.12 H5-0 执行期实测（2026-09-22，H1 归位 ＋ 右栏语义）

| # | 结论 | 影响 |
|---|---|---|
| 1 | ⛔⛔ **改标签名＝改计算样式：「class 不变」推不出「视觉零变化」**。class 规则能压过元素规则，但**class 没声明的属性会留在元素规则上**。本批 Hero 的 `<h1 class="sf-formula-hero__title">` 改 `<div>`（class 逐字不变），当场掉了 **`font-weight`** —— 700 来自 `theme.json` 的 `styles.elements.h1.typography.fontWeight`，而 `.sf-formula-hero__title` **从未声明过字重** | 一切"换标签但保住 class"的改动 |
| 2 | ⛔⛔ **同一个坑在打印媒体里第二次出现，而且更隐蔽**：`@media print { h1, h2, h3, p, li, td, th { color:#000 !important } }` 是**唯一**把公式页标题在打印时压成黑的规则（该页 Hero **没有** `has-primary-background-color`，所以打印块的"强制白底"那一条也不管它）。改 `div` 后不再命中 ⇒ **打印时白底白字**。**字节门按构造比渲染文档，看不到与媒体相关的级联** | 一切触碰 Hero/标题的改动，**打印级联必须单独查** |
| 3 | ✅ **穷举元素规则要过三处，缺一处就会漏**：① 主题 CSS 里按元素名的选择器（`grep -E '^[^{]*\bh1\b[^{]*\{'`）② `theme.json` 的 `styles.elements.<tag>` ③ **渲染页内联的 global-styles**。本批三处合计只有 3 条命中，逐属性结论：size/line-height/letter-spacing/color **早被 class 覆盖（白拿）**；`font-family` **未被覆盖**，但 `theme.json` 里 **`heading` 与 `body` 是同一个 Inter 栈 ⇒ 天然无差**（**这条必须显式核验，不能假设**）；`font-weight` 与打印 `color` 是仅有的两处真泄漏 | 换标签前的固定动作清单 |
| 4 | ⛔ **「插入一行」在渲染产物里不是一行**。块分隔符被 `do_blocks()` 消费、换行留下 ⇒ 模板里插的注释，在页面里是 `\n\n` ＋ 注释 ＋ `\n\n`。撤销声明时若只摘注释、不连它后面那个换行一起摘，结果比基线**多一个换行** ⇒ **42 页全红，且看起来完全像产品缺陷** | 一切"插入注释/标记"的限定证明 |
| 5 | ⛔ **声明改动集要从提交推导，不要手抄**。两段注释五六行、带破折号，手抄一个字符错就表现为"42 页有差异"。做法：`git show <sha>:<file>` 取两端文本 ＋ 断言「旧的已不在候选、新的不在基线、新注释只在候选」，推导时就自证 | 一切 markdown/注释参与 diff 的批次 |
| 6 | ⛔ **"全站不得有 X"是危险断言**。站上本来就有 `<aside class="sf-basket-drawer" role="dialog">`（**75 页各一个**），"候选页不得再有 aside"因此**首跑 75 FAIL**。正确形态＝**"该元素恰好少一个、别处一个不动"**：逐页 `aside 计数 == 基线计数 − 是否带列` | 一切"删掉某个元素"的断言 |
| 7 | ⛔ **"盒子不许动"要分类：容器装了新东西就该长高**。"参数列 box 不变"因此 **48 FAIL**。正确形态＝**位置与宽度零变化 ＋ 高度增量必须等于新内容的盒高＋边距**（实测恰 34+16=50 / 67+16=83）—— "差不多一行"不通过 | 一切"给现有容器加内容"的几何断言 |
| 8 | ⛔ **两栏带的增高要按网格规则解释，而不是"没动就好"**。并排时带高＝更高者决定（桌面 758→758，图集列 662 更高）；堆叠时＝两者之和（手机 1202→1285＝列增量）。断言写成这条公式，才**同时**证明了"网格还是网格" | 多列布局的回归判据 |
| 9 | ⚠️ **取整要显式给容差并报出来**。探针把每个盒子取整，用三个取整值推算第四个会差 1px（本批 48 项里 2 项）。给 **1px 容差但把 off-by-one 打印成 note**，而不是咽掉 —— 容差是为了不误报，打印是为了不掩盖 | 一切基于 `getBoundingClientRect()` 的算术断言 |
| 10 | ✅ **行为门＝两态各扫一遍再逐页比，不是拿记忆里的数字比**：把预检副本**装回基线提交**扫一遍、**装候选**再扫一遍（本批 48 项：42 页桌面 ＋ 6 页手机抽样）。**抽样要明说它不完整**：被断言的性质是视口级事实，所以桌面那遍才是完整那遍 | 几何/计算样式类批次的固定形态 |
| 11 | ✅ **打印类断言可以不必真的切到打印媒体**：遍历 `document.styleSheets` 里 `conditionText` 含 `print` 的块，取**实际匹配该元素**的 `color` 声明（含 `!important` 标记）。两侧用同一算法 ⇒ 比较级联是有效比较 | 无需 CDP 的媒体查询核验 |
| 12 | ✅ **`display:block` 在 `h1` 与 `div` 上一致，`margin` 已被 class 声明** ⇒ 这两项不必额外补。**但要把"不必补"也量出来写进记录**，否则下一个人还得再查一遍 | 元素规则枚举的收尾 |

---

| 批次 | 状态 | commit | 说明 |
|---|---|---|---|
| H2b | **Step 0 完成 → 5 项不符已裁决（① 改 D / ②③④⑤ 同意）** | — | `docs/batch2d-stepH2b-scan.md` |
| **H2b1** | **Step 1–5 全过门 + E2E 全过 → 用户确认通过；`git pull` 跳过（playbook 明确不执行上线）** | 产品 `ebe8f50` + 证据 `69d4c21`/`d8ffd53`（均已 push） | `docs/batch2d-stepH2b1.md` |
| **H2b2** | **Step 1–5 全过门 + E2E 全过（2026-09-22）；Step 6 `git pull` 按规则跳过** | 产品 `3b9fc23`（已 push）；基线 `ebe8f50` | `docs/batch2d-stepH2b2.md` |
| **H3** | **Step 1–5 全过门 + E2E 全过（2026-09-22）；Step 6 `git pull` 按规则跳过** | 产品 `4ca3aea`（已 push）；基线 `109be91` | `docs/batch2d-stepH3.md`（内容区 + Sampling，三项裁决见扫描档） |
| **H4e**〔前置：邮箱变更〕 | **Step 1–5 全过门 + E2E 全过（2026-09-22）；Step 6 `git pull` 按规则跳过**。⚠️ **含 DB 改动，无"候选态"** | 主题 `24da600`（已 push）；DB 10 行（快照可回滚）；基线 `4ca3aea` | `docs/batch2d-stepH4e.md`（四项裁决见 `docs/batch2d-stepH4-scan.md`） |
| **H4** | **Step 1–5 全过门 + E2E 全过（31 ok / 0 FAIL，连续三遍绿）；Step 6 `git pull` 按规则跳过** | 产品 `92dee47`（含修复 `a75640a`，均已 push）；基线 `24da600` 的预检副本（`2.10.57`） | `docs/batch2d-stepH4.md`（四项裁决 D1–D4 见 `docs/batch2d-stepH4-scan-body.md`） |
| **H5-0**〔H1 扫描的两项裁决〕 | **Step 1–5 全过门 ＋ 行为门全过（2026-09-22）；`git pull` 按规则跳过**。**两处产品缺陷在字节门上都是 0 FAIL** | 产品 `c9884ed` ＋ 修复 `084b246`（均已 push）；基线 `92dee47` 的预检副本（`2.10.59`） | `docs/batch2d-stepH5-0.md`（方案 D ＋ `aside`→`div`；来源 `docs/scan-formula-detail-h1.md`） |
| **H5** | **Step 1–5 全过门 ＋ E2E 20/0 ＋ 截图 11/11；Step 6 `git pull` 按规则跳过**。⛔ **两个门在「漏改 126 处」的构建上都是 0 FAIL**（反演式门对「该改的没改」结构性失明） | 产品 `1eafe62` ＋ 修复 `2017dbe`（均已 push）；基线＝**H5-0 的预检副本**（`084b246` 树，`2.10.60`，仍在位未拆） | `docs/batch2d-stepH5.md`（七条裁决 A–G 落地 ＋ 四条判据的门 ＋ 四个新发现）／`docs/batch2d-stepH5-scan.md`（A–G 七条）／`docs/batch2d-stepH5-audit-8020.md`（裁决 E：80/20 已满足，余量 45 倍，不动） |
| H6 | 未开工 | — | 待办已增至 **15 项**（H5 新造 2 项＝Product `material` 未声明、`WebSite` schema 未声明；H5-0 新造 1 项＝`theme.json` `styles.elements.<tag>` 的隐式字重泄漏，见其 §2；H5 另新造 1 项＝`sf-facts-mini` 与 H3 参数行 3 项语义重叠，**并入第 4 项「MOQ 三处对账」**；H4 新造 1 项见其 §11；H4e 新造 1 项见其 §10.3；H3 新造 1 项见 `docs/batch2d-stepH3.md` §8；H2b2 新造 4 项见其 §8） |

**H2b1 门/E2E 摘要**：静态 S1–S8 全过；75 页基线 + 75 页候选；主门 **PASS 21 条 / 0 FAIL**
（58 页差 / 17 页同，逐字节重建）；破坏矩阵 **10/10**；三条负对照全 FAIL（as required）；
**可复现性 12/12 逐字节**；E2E **E1–E9 全过**。计划外行为变化（两个固定层落位 132/68 → 现代引擎收敛到
全站取值）已实测，**用户判定为收敛而非回归**。详见 `docs/batch2d-stepH2b1.md`。

**H2b2 门/E2E 摘要**：纯删除 **1,710 删 / 0 增**；静态 S1–S9 全过 + 负对照 6/6；基线重抓 **75/75 掩码 identical**；
服务器副本 = 本地树 **347/347 逐字节**；主门 **PASS 18 条 / 0 FAIL**（16 页恰少两行、59 页逐字节同、无 ver bump）；
破坏矩阵 **10/10**；负对照 **3/3**（均具名）；E2E **E1–E6 全过**、几何 **210 项逐值相同**。
唯一行为变化＝旧引擎差值归零（480px `268/0`、1440px `100/0`）。详见 `docs/batch2d-stepH2b2.md`。

**⛔ 立项规则变更（用户 2026-09-22 明确）**：① **playbook 不执行上线** ⇒ 各批**不开 Step 6 `git pull`**；
② **H2b2 起的基线＝上一批的预检副本，不是 live** ⇒ 预检副本成为"当前最新候选"的唯一载体，
**在下一批用完之前禁拆**（H2a 的"pull 完再拆"顺序作废）。因此 dev 站 live 主题会长期停在 pre-H2b1（`2.10.55`＋配置器），
那是预期状态，不是漏做 pull。
③ **新增停靠豁免**：扫描与预期**方向一致**、仅**派生数字/行号**有误 ⇒ 就地更正、**不停机汇报**，自动继续。

**H3 门/E2E 摘要**：纯新增 **554 增 / 2 删**，恰 3 文件（`functions.php` +354−1、`style.css` +184−1、模板 +16）；
基线重抓 **75/75 掩码 identical**（另加独立两轮交叉复现 **60/60 SAME**）；服务器副本 = 本地 `4ca3aea` 树 **347/347 逐字节**；
主门 **PASS 21 条 / 0 FAIL**（42 页逐字节重建 = 基线 ＋ 恰好三段 run、33 页仅令牌动、无第二处令牌移动）；
破坏矩阵 **15/15**（含两条新增的中文侧变异）；负对照 **3/3**（均具名）；
离线单测 **54 passed / 0 failed** ＋ 负对照 **6/6 具名**；E2E **E1–E7（31 ok / 0 FAIL）**、0 console error；
JSON-LD 由 0→**42 HowTo**，67 FAQPage **逐字节未动**；实拍 25 图 / 2.9 MB。
计划外行为变化：**无**。7 源 0/21 是"先发渲染器"预期态。详见 `docs/batch2d-stepH3.md`。

**H4 门/E2E 摘要**：主题 diff **5 文件**（`functions.php` +393、`assets/js/inquiry.js` 新 ~250 行、`style.css` +439、
`parts/footer.html` 1 行），ver **2.10.57 → 2.10.59**；**无 DB 改动**。新增三样（胶囊 / 弹窗 / `inquiry.js`）
都恰好落在 **42＝参数带页面**集合上，33 页零变更；`strip_declared(候选)` 归一化后 75/75 **逐字节＝基线**。
主门 **PASS 12 条 / 0 FAIL**；破坏矩阵 **17/17**；具名负对照 **5/5**；A/A 自检 **PASS（只余故意 [1]）**；
H3 单测复跑 **54/0 + 6/6**；E2E **31 ok / 0 FAIL**、0 console error、**连续三遍全绿**；实拍 **8 张**。
⚠️ **两个产品缺陷都是字节门看不见、由浏览器门抓到的**（脚本/标记顺序、更宽兄弟挤走既有兄弟），
⇒ 见 §2「缺陷一」「缺陷二」与附录 **A.10**。真发邮件 5 封（标记 `H4 E2E`，收件人＝`sf_contact_email`）。
**Step 6 上线跳过**；预检副本**不拆**（＝H5-0 的基线）。详见 `docs/batch2d-stepH4.md`。

**H5-0 门/行为门摘要**：主题 diff **3 文件 +55 / −14**（模板 +22−9、`style.css` +35−4、`functions.php` 12 行注释与 ver），
ver **2.10.59 → 2.10.60**；**无 DB、无脚本、无其他模板**。基线＝H4 预检副本，抓取前与 `_backup/b2d-h4-candidates/`
互证 **75/75 掩码 identical**。主门 **PASS 17 条 / 0 FAIL**（`undo_declared(候选)` 归一化后 **75/75 逐字节＝基线**、
`diff_pages = 0`；五处声明改动**各被精确撤销 42 次**）；A/A **PASS（只余故意 [1]）**；矩阵 **14/14**；具名负对照 **5/5**。
**行为门 48 项 0 FAIL**：Hero 标题 box ＋ 12 项计算样式、Hero 带 box、图集列 box **全部逐项相同**；
列的 `x/w/y` 零变化、高度增量**恰＝新标题盒高＋边距**；两栏带增高**恰等于网格规则算出的值**；
**打印媒体里实际作用到标题的颜色两侧都解析出 `rgb(0,0,0) !important`**。截图 **8 张**（min 45,858 B）。
⚠️⛔ **两处产品缺陷在字节门上都是 0 FAIL**：① 字重（`theme.json` 的 `elements.h1` 给 700，class 从未声明）
② **`@media print` 的 `h1,h2,h3,p,li,td,th{color:#000 !important}` —— 唯一让标题打印变黑的规则**，改后白底白字。
⇒ 「class 不变」**推不出**「视觉零变化」；换标签必须**逐属性枚举元素规则**（主题 CSS ＋ `theme.json` ＋ 渲染页内联
global-styles **三处**）且**打印级联单独查**。详见 §2「两个跟着元素名走的坑」与附录 **A.12**。
预检副本保持安装为 `084b246` / `2.10.60` ⇒ **这就是 H5 的基线，不拆**。

**H5 Step 0 摘要（2026-09-22，只读）**：**未改任何字节、未建新探针**（渲染产物＋源码两层即可判定）。
基线＝H4 预检副本（`92dee47` 树，`2.10.59`，仍在位）。四项范围实测 ⇒
① `Product.additionalProperty`：**配方详情页 42/42 已有**（读 post meta）／**剂型页 0/16 全缺** ——
生成器 `functions.php:4796-4806` 的两条分支（`sf-spec-list`、遗留 `flex-basis:35%` 表）在剂型页**命中均为 0**，
H2b1/F1 已把它换成 **`sf-facts-mini`**（4 行：MOQ / Lead time / Certifications / **Packaging**，16/16 页齐备）
⇒ **手册要的「包装」数据一直在，只是没人读**；且 `sinofresh_formula_spec_cell()`（`functions.php:646-690`）
**已有作用域正确的读取器**，零新代码可复用。② `Product.offers`：**0/58**，`sf_formula_price_tiers` **全空**
（`Quantity & Pricing` 0/42）⇒ ⛔ **需改数据，停机**。③ `material`/`audience`/`isRelatedTo`：源码 **0 处**
（后两个可零数据推导）。④ `Organization.knowsAbout`：源码 **0 处**（其余 10 字段已齐、75/75 页）⇒ 纯新增可做。
⑤ 图片 ALT：**840 个 `<img>`，缺 alt = 0**；174 个空 alt **全为装饰件**（语言国旗 150＋博客头像 24）
⇒ **手册「自动生成」的前提不成立，正确动词是「规范化」**。⑥ 内容 80/20：**已满足**
（词数中位 1,934/页、0 页 <300 词、CTA 密度 **3.6/千词＝0.36%**）。
另：**无 SEO 插件**（活跃仅 GF / TranslatePress×2 / consent-api / mail-logging / statistics）⇒ 主题 schema 具唯一权威性。

⚠️ **两条本批新增的通用教训**（详见附录 A.11）：
- ⛔ **断面「0 覆盖」先查断面构成**：75 页断面**不含博客单篇**（只有 `blog.html` 列表页）⇒ `Article` 0/75 是
  **采样假象**，`functions.php:5017-5100` 的 `is_singular('post')` 生成器**是活的**。把"没采到"读成"没有"会得出反向结论。
- ⛔ **H5 不能沿用字节门**：加 `knowsAbout`＝**75/75 页 DIFF**、剂型页加 `additionalProperty`＝**16 页 DIFF**、
  logo alt 规范化＝**75 页 DIFF**，**全部合法** ⇒ 门必须＝**JSON-LD 语义门**（`json.loads` 后 deep-equal，
  **允许新增键、禁止改值/删键**）＋渲染 HTML 的白名单字节门。**先量「合法 DIFF 集」再写门**：
  沿用字节门＝第一批绿就是假绿；放宽成"能 parse 就过"＝删掉 `brand` 也能过＝另一种假绿。

**⛔ 立项规则变更（用户 2026-09-22 明确）**：① **playbook 不执行上线** ⇒ 各批**不开 Step 6 `git pull`**；
② **H2b2 起的基线＝上一批的预检副本，不是 live** ⇒ 预检副本成为"当前最新候选"的唯一载体，
**在下一批用完之前禁拆**（H2a 的"pull 完再拆"顺序作废）。因此 dev 站 live 主题会长期停在 pre-H2b1（`2.10.55`＋配置器），
那是预期状态，不是漏做 pull。
③ **新增停靠豁免**：扫描与预期**方向一致**、仅**派生数字/行号**有误 ⇒ 就地更正、**不停机汇报**，自动继续。

**服务器状态**：未 pull；authority guard 未删；DB 未动。
**预检副本仍然挂着且必须保留**：`wp-content/themes/sinofresh-theme-preflight/`
（现＝**`92dee47`** 树，`2.10.59`；此前 H4e/H4 早期是 `24da600`/`ef4ee12`、H3 时期是 `4ca3aea`、
H2b2 时期是 `3b9fc23`、H2b1 时期是 `ebe8f50`）
＋ mu-plugin `zz-sf-preflight.php`。**H5 的基线就是它，拆掉等于自毁基线。**
复核锚点（2026-09-22 H4 收尾实测，同 URL 两种请求头）：
无头 → `2.10.55` ＋ 2 条 configurator 资产 ＋ `class="configurator` 210 次/132 行（＝H2a 状态，预期）；
带头 → **`2.10.59`** ＋ 0 条资产 ＋ `link` 指向 `themes/sinofresh-theme-preflight/` ＋ 详情页 **HowTo=1**
＋ 详情页出现胶囊/弹窗/`inquiry.js`（各 42 页）。
⚠️ 引用这两个计数时必须写明是**出现次数**还是 **`grep -c` 行数**（210 vs 132）。
⚠️ **H3 起，一个页面上的资源确证不能只看版本号**：必须同时断言样式表来自 `sinofresh-theme-preflight`，
否则顺序错了会静默比较**旧字节**、给出全绿假结论（H2b1 附录 A.5 #1 的同类教训）。

