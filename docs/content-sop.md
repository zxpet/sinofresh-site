# SINO FRESH 内容运营 SOP（博客文章）

> 配套文档：`docs/content-pre-publish-checklist.md`（发布前逐项勾选）
> 前置设施：后台 10 个文章 Pattern（分类 "SINO FRESH Article Templates"）

---

## 一、10 种文章类型适用场景 + Pattern ↔ 分类对应表

| Pattern | 适用场景 | 发布时选分类 |
|---------|---------|-------------|
| Case Study | 深度案例（800-1200字） | Case Studies |
| Client Story | 轻量好评（300-500字） | Case Studies |
| Educational Article | 认知科普（What is X?） | Manufacturing |
| Selection Guide | 选型（How to choose X?） | Manufacturing |
| Comparison Article | 对比（A vs B） | Manufacturing |
| Technical Deep Dive | 技术（工艺/检测/QC） | Manufacturing |
| Compliance Guide | 合规（各市场标签/法规） | Private Label |
| Buyer's Guide | 采购（供应商评估） | Manufacturing |
| Market Trends | 趋势（行业数据/分析） | Manufacturing |
| Thought Leadership | 观点（行业视角） | Manufacturing |

辅助标签（Tags）：Formulation / QC / Export，按文章主题选 1-2 个。

### Case Study vs Client Story 使用规则

- **Case Study（800-1200字）**：深度案例，每客户一篇精品，宁缺毋滥。数据点必须真实可公开。
- **Client Story（300-500字）**：轻量好评，可持续增加，作为内容供给的"日常补充"。
- **串联关系**：首页卡片 → Client Story → 底部 "Read the full case study →" 链接 → Case Study。
  一篇 Case Study 最多对应 1 篇 Client Story；写 Client Story 前确认对应 Case Study 已存在（或同步规划）。

---

## 二、GEO/SEO 优化规范

面向 Google + AI 搜索（GEO：Generative Engine Optimization）双优化。

- **答案前置**：每个 H2 下第一句给结论，解释放后面。AI 摘要只抓第一句。
- **Short Answer**：H1 后 40-80 字直答文章核心问题（Pattern 已内置锁定块）。
- **段落长度**：3-5 句一段，避免整屏大段落。
- **数据引用**：带具体数字、时间、场景（"MOQ 500 units"、"12 周首单"、"2026 年"），拒绝"很多""大量"等模糊词。
- **问题式 H2 标题**：优先用真实搜索问句（What is / How to / Why does），与 GSC 查询词对齐。
- **FAQ 用 `<details>` 标签**：Pattern 内置，可被 Google 抽取为富摘要；每题回答 40-60 字。
- **内链锚文本**：用关键词（如 "Learn about Soft Chews OEM"），禁用 "Click here" / "Learn more" / "Read more"。

---

## 三、Excerpt（摘要）规范

- 长度：**120-160 字（英文）**，列表页与 RSS 直接展示。
- 结构：第一句给结论，第二句补充价值点（数据/差异化）。
- **手动填写**，不用默认截取（默认截取会从 TL;DR 中间断开，观感差）。
- 位置：编辑器右侧栏 → Excerpt → Add an excerpt。

---

## 四、内链规范

- 每篇至少 **2 个内链**（Pattern 的 Products Involved + CTA 已含基础内链，正文再补 1-2 个）。
- 锚文本用关键词，格式建议 "[动词] + [产品/主题] + [限定词]"：
  - ✅ "Learn about Soft Chews OEM"
  - ✅ "our ISO 8 cleanroom quality process"
  - ❌ "Click here" / "Learn more"
- **内链回 Pillar Page**：每篇 Cluster 文章必须含 1 个指向对应 Pillar Page 的链接（见第八节架构）。
- 跨文章互链：Case Study ↔ Client Story 双向链接；同分类旧文可加"相关阅读"。

---

## 五、封面图规范

- 比例：**16:9**，尺寸 **1200×675 以上**。
- 格式：**WebP**（质量 80 左右，单张 <150KB）。
- OG 图（社交分享）依赖同一比例——不按 16:9 传图，分享卡片会被裁切。
- 命名：`blog-<主题>-<剂型>.webp`（小写、连字符），上传后设置 Featured Image。
- 内容优先级：实拍车间/生产线 > 产品图 > 设计图；禁止明显 AI 生成感图片。

---

## 六、元描述规范

- 长度：**150 字符以内**（英文），超长会被搜索结果截断。
- 必含核心关键词 + 1 个具体卖点（数据/认证/交期）。
- 与 Excerpt 可复用，但 Excerpt 上限 160 字、元描述上限 150 字，以短为准。
- 工具：Rank Math / Yoast 的Snippet 预览确认不截断。

---

## 七、FAQ 规范

- 数量：**3-5 题**，用 Pattern 内置的 `<details>` 块（勿改成普通段落）。
- 每题回答 **40-60 字**，首句直答，可带 1 个数据点。
- 问题来源：GSC 疑问词查询 / 销售邮件高频问题 / 竞品评论区。
- 问题式标题以 "？" 结尾；同一文章内 FAQ 不与 H2 正文重复作答。

---

## 八、内容规划方法

### 问题挖掘来源（季度执行）

1. **Google Search Console**：导出疑问式查询（what/how/why/can），按展示量排序。
2. **销售/客服邮件**：Sam 邮箱 + WhatsApp 高频问题，每月汇总一次。
3. **竞品评论区**：Amazon / Chewy 宠物保健品差评与提问（成分疑虑、适口性、包装）。
4. **AI 客服日志**：部署 MxChat 后，按月导出未命中知识库的问题（约等于内容缺口）。

### 五维度交叉法

> 物种 × 生命阶段 × 品种敏感度 × 健康问题 × 消费者约束

示例交叉："犬 × 幼犬 × 小型犬敏感肠胃 × 关节健康 × 美国品牌方预算" →
可产出 Educational（幼犬关节补充剂是什么）+ Selection Guide（如何选幼犬软咀嚼 OEM）+ Client Story 等一组选题。

### Pillar-Cluster 架构

- 每个核心主题建 **1 个 Pillar Page**（可先复用现有剂型页/Quality 页作为 Pillar）。
- 围绕该主题规划 **8-12 篇 Cluster Articles**（用对应 Pattern）。
- 每篇 Cluster 必须内链回 Pillar Page；Pillar Page 汇总链接所有 Cluster。
- 建议首批 Pillar：Soft Chews OEM / Private Label 全流程 / Pet Supplement Quality & QC。

### 季度更新流程

1. 从 GSC / 邮件 / 评论区 / AI 客服日志挖掘新问题
2. 评估搜索意图和竞争度（优先疑问式 + 低竞争）
3. 分配文章类型（对照第一节对应表）
4. 用对应 Pattern 写作（后台 → 新建文章 → 插入 Pattern）
5. 发布前对照检查清单（`docs/content-pre-publish-checklist.md`）
6. 内链回 Pillar Page，并在 Pillar Page 补反向链接

---

## 九、发布流程

```
草稿（选分类 → 插入 Pattern → 填占位符）
  → 对照发布前检查清单逐项勾选
  → 排版预览（桌面 + 移动端）
  → 发布
  → 回到 Pillar Page 补内链
  → （可选）若为 Client Story：更新首页对应卡片链接
```

首页 Client Stories 卡片与案例文章一一对应；发布新 Case Study / Client Story 后，通知更新 `templates/front-page.html` 的卡片链接（找技术侧处理）。
