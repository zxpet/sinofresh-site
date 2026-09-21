# Batch F1 — 极简核心事实行 + 详情页 hero meta 恢复

**状态：已上线并闭环（2026-09-21）**。提交链：`0c3243a`（源改动+门工具）→ `27b7aba`（门报告+负对照）→ `0480810`（渲染证明+闭环+日志审计）。最终 HEAD：本地=远端=云端=`0480810`。

## 一、这批做了什么

2D-E 删三段后，`sinofresh_formula_spec_cell()` 失去数据源（它从剂型页 spectable 读 MOQ/Lead time），21+21 详情页 hero meta 退化为纯剂型名。F1 一次补齐两侧：

1. **8 个剂型模板** L28（hero 与卡墙之间、2D-E 留下的 24px 间隙处）各插入一个 `wp:html` 块：`section.sf-facts-mini`，三项 **MOQ / Lead time / Certifications**，label（11px muted）+ value（ink），值元素带 `data-label`。**无 h2 ⇒ 点轨保持 6**。`b2d_f1_apply.py`（`--check`/`--apply` + 前置断言 + 读回自证）。
2. **`functions.php` `spec_cell()`**：从「全文找 `<td data-label>`」改为「先截 `.sf-facts-mini` 块、块内取 `data-label` 值」——作用域限定，第二个 data-label 永远遮蔽不了。选「改读新行」而非硬编码：单一事实源，页上改值详情页自动跟（同 FAQPage/Product schema 的规则）。
3. **`style.css`**：新增 `.sf-facts-mini` 命名空间（hairline 上下边线、桌面一行 flex 三项、`<768px` 纵向堆叠、无 `!important`）；旧 `.sf-facts__*`/`.sf-spectable__*` 未动（下批清理候选）。版本 **2.10.52 → 2.10.53**（`functions.php:26` + `style.css:5`）。

**值（八页）**：MOQ 三种——soft-chews `from 500–1,000 units`；tablets/fish-oil/dental-chews `from 1,000 units`；powders/pastes/drops/liquids `from 500 units`。Lead time 八页同文 **`Typically 7–15 working days after packaging is ready`**（用户拍板 C：与详情页参数表同口径，两处说同一件事措辞必须统一）。Certifications 八页同文 `FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC`。

## 二、门（`tools/b2d_f1_confine.py`，六门 + 负对照）

插入批 ⇒ 限定证明方向与 2D-E 相反：**在候选侧删块**，逐字节还原基线（函数名/注释写明方向）。

| 门 | 结果 |
|---|---|
| 0 候选身份 | 75/75 来自预检副本（副本哈希与本地提交逐位相同） |
| 1 资源清单 | 仅 style.css ver token 变化 ×75 |
| 2 掩码 DIFF 集合 | differ 58 / identical 17，与期望集合**精确命中**（8 剂型+8 zh+21 详情+21 zh） |
| 3 页级限定证明 | **58/58 逐字节还原**（删块 + meta 降级） |
| 4 源级重建 | 10 文件 undone==base（8 模板 + style.css + functions.php） |
| 5 JSON-LD | 75/75 deep-equal |
| 负对照（new=base） | **RC=1**，58 条该 DIFF 未 DIFF |

**门的 meta 期望值不是本地表**：MOQ/Lead time 从候选剂型页块内交叉读取（与 spec_cell 同一事实源），行/hero 漂移当场 FAIL。

### 冒烟方法（先合成候选再上真数据）

上线路由之前，先在基线渲染页上**人工施加本批变换**（插块/还原 meta/换版本 token）造出"合成候选"，把门在合成候选上跑 PASS、再拿基线当候选跑负对照 FAIL，然后才抓真候选。本轮冒烟逮到 3 个门 bug：

1. **剂型页键名漏 `.html` 后缀**（load 返回的键带扩展名，`'products__' + form` 匹配不到）；
2. **style.css 重建被拆成两次独立比较**（版本撤销、块撤销各比一次）——版本单独撤销永远回不到基线，两个比较各自的说法不成立 ⇒ 合并为一次整体重建；
3. **CSS 块撤销 TAIL 常量少末尾换行** + 一行 `say()` 缩进错位引用未定义变量。

### 渲染接缝：推演 ≠ 实测

模板行结构推演"块后 4 换行"，实测 **2 换行**（wp:html 闭合注释+空行+group 注释的渲染规则与预想不同）；块前 4 换行与推演一致。门因此设计成**宽容捕获换行串**（`\n+`）、**撤销还原成基线实测值**（4 换行）并在报告打印实际串——推演错误不会造成假 PASS/假 FAIL，撤销==基线的逐字节比较兜底。

## 三、上线闭环（pull 后）

| 步骤 | 结果 |
|---|---|
| pull | `b4ff86e → 27b7aba`，ff、工作树干净；上线前实测 live 仍 2.10.52 |
| 服务侧 | `style.css?ver=2.10.53`；剂型页 3 项 data-label 全在（值逐字正确）；详情页 meta 抽查恢复：`Powders · MOQ from 500 units · Lead time Typically 7–15 …`、`Soft Chews · MOQ from 500–1,000 units · …`；无凭据 401 |
| A/A | PASS（173579/173579 bytes） |
| 掩码闭环 | live 75 页抓取（无预检头）→ `sf_masked_cmp new live` **75/75 identical** |
| 身份链 | 拆预检前三方 691 文件 0 不一致；拆后两方 PASS |
| 浏览器 E2E | `tools/b2d_f1_evidence.py`：20 用例（10 页 × 1440/375）**0 失败**——新行三项值逐字正确、≥1024px 单行、无 h2、点轨仍 6 且自洽（dots==h2）、详情页 meta 恰三段（剂型 label · MOQ · Lead time，措辞与剂型页一致）、0 page error、无横向滚动 |
| 拆预检 | 主题目录/mu-plugin/日志移除（拆前日志 75 行已存档 `f1-preflight.log.txt`）；mu-plugins 只剩 lockdown；docroot 代码零残留；DB 指向 `sinofresh-theme`；拆除后线上复验 2.10.53/3 项/401 |
| 日志归因 | 显式窗口 04:12–05:00 UTC（我们自己的请求区间，475 条 sfdev 请求）：**窗口内 0 条**、40 条逐条归因清零、1 条显式例外（=2D-E 负对照故意写的 PHP fatal，跨批沿用 `--allow` 记录） |
| 仓库 md5 | **1294 文件 0 差异**（报告自身排除，`cmp` 可复跑） |

### E2E 工具踩坑（两处，均为选择器口径）

1. **点轨数被三倍**：`.sf-toc a, button, [class*="dot"], li` 每个点匹配 3 个节点 ⇒ 数出 18。正确选择器＝`.sf-toc__dot`（与 `b2d_e_evidence.py` 一致）。
2. **meta 开头不是 h1**：详情页 h1 是产品名（`Pure Fish Oil Blend`），meta 首段是**剂型 label**（`Fish Oil`）——断言"meta 以 h1 开头"从设计上就错。改为断言 meta 的真实结构：恰三个 `·` 分段、首段是剂型 label 形状、MOQ 在 Lead time 前、Lead time 措辞逐字一致。

### 日志归因的设计确认（非 bug）

`b2d_s5_logaudit.py` 对错误日志是**整文件逐条审计**，不是只审窗口内——「每一条都可归因」是永久不变量。因此 2D-E 负对照故意写的那条 PHP fatal（03:38:30）在日志轮转前**每个后续批次都要带同一条 `--allow` 理由**，这是记账不是屏蔽。

## 四、证据与产物

- 门：`docs/b2d-f1-gates.txt`（PASS）、`docs/b2d-f1-negctl.txt`（RC=1）
- 闭环：`docs/b2d-f1-shots/`——`closure.json`（75/75）、`e2e.txt`（20/20）、`logaudit.txt`（PASS）、`identity-pre.txt`（三方）、`identity-after-teardown.txt`（两方）、`cloud-md5.txt`（1294/0）、`teardown.txt`、`f1-preflight.log.txt`、11 张截图（8 剂型 1440 + soft-chews 375 + 2 详情页 1440）
- 基线：`_backup/b2d-f1-baselines/{base,new,live,src,src-templates}`

## 五、遗留

- 旧 `.sf-facts__*` / `.sf-spectable__*` CSS 成为死代码（约 80 行）——下批清理候选。
- MOQ 重复对账（原第 6 批）：spectable 已删，剩 **FAQ vs 详情页 meta** 两处；meta 现在自动跟随剂型页新行，对账范围进一步缩小。
