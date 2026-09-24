# 待办 31 — /quality/「Quality Control at Every Step」改 3 列卡片

**只读扫描报告** · 2026-09-24 · dev 站 `style.css?ver=2.10.76` · 工作区 `f83767f`
全程只读：只对 dev 做 GET + 在浏览器里读几何，未改一行代码、未写一个字节、未碰 DB 与生产站。

---

## 0. 一句话

**机制完全就绪、可以纯 CSS 完成（零模板、零 JS、零 DB），但有 3 处与你给的指令对不上**：① 区块是 **6 步**不是 3 步；② 6 步做 3 列必然 **2 行**，实测 **861px（省 52%）**，**600px 数学上做不到**；③ 图片不是「约 50%」而是固定 350px（占 34.5%）。图片比例 **4:3 与「大号绿色数字」现状已满足**，无需改动。

---

## 1. 现状

### 1.1 文件与锚点

| 项 | 位置 |
|---|---|
| 模板 | `sinofresh-theme/templates/page-quality.html` **L122–180**（`wp:group` `bg-light` 内含 `<!-- wp:html -->` 手写块） |
| 样式 · 桌面 | `sinofresh-theme/style.css` **L4963–5036**（注释段号 **31d**） |
| 样式 · 降级 | `style.css` **L5114–5141**（`@media (max-width:900px)` 内） |
| 渲染范围 | **仅 `/quality/` 一页**（抽查 `/`·`/about/`·`/services/`·`/factory-tour/`·`/products/`·`/contact/`·`/blog/` 全部 `sf-qs` = 0） |
| JS 依赖 | **无**（`assets/js/` 0 命中） |
| 中文站 | `/zh/quality/` 存在（200）但**不在** zh 31 页清单；共享同一模板，会跟着变 |

### 1.2 DOM 结构

```html
<div class="sf-qs">                                  <!-- 6 步，非 3 步 -->
  <article class="sf-qs__step">
    <div class="sf-qs__text">                        <!-- DOM 里文字在前 -->
      <div class="sf-qs__num">01</div>
      <h3 class="wp-block-heading">Raw Material Inspection</h3>
      <p>Every incoming ingredient is verified against its COA and specification.</p>
    </div>
    <figure class="sf-qs__media"><img …></figure>    <!-- 图片在后 -->
  </article>
  … 02 Batching &amp; Weighing ／ 03 In-Process QC ／
    04 Finished Product Testing ／ 05 COA Issuance ／ 06 Retention Sampling
</div>
```

**6 步标题全文**（你给的示例只到 03）：`Raw Material Inspection` · `Batching & Weighing` · `In-Process QC` · `Finished Product Testing` · `COA Issuance` · `Retention Sampling`

### 1.3 CSS 关键规则

```css
.sf-qs { max-width: 1014px; margin: 32px auto 0; }            /* 620 copy + 44 gap + 350 photo */
.sf-qs__step { display: grid;
               grid-template-columns: minmax(0,1fr) minmax(0,350px);
               column-gap: 44px; align-items: center; }
.sf-qs__step:nth-child(even) { grid-template-columns: minmax(0,350px) minmax(0,1fr); }
.sf-qs__step:nth-child(even) .sf-qs__text  { grid-column: 2; grid-row: 1; }   /* 翻转靠显式放置 */
.sf-qs__step:nth-child(even) .sf-qs__media { grid-column: 1; grid-row: 1; }
.sf-qs__step + .sf-qs__step { margin-top: 22px; padding-top: 22px;
                              border-top: 1px solid #e0e5dc; }   /* hairline 分隔 */
.sf-qs__num   { font-size: 64px; font-weight: 600; color: brand-green; }
.sf-qs__text h3 { font-size: 24px; color: accent; }
.sf-qs__text p  { font-size: 16px; color: #6b6b6b; }
.sf-qs__media img { aspect-ratio: 4/3; object-fit: cover;
                    border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
```

### 1.4 实测几何（before）

工具：**新建 `tools/b3b_qs_measure.py`**（只读；`close --all` → `set credentials` → `open` → 逐视口 `set viewport` → 读 `getBoundingClientRect()`）。

| 视口 | 区块高 | 每行步数 | grid 列 | 图片盒 | 数字 |
|---|---|---|---|---|---|
| **1440** | **1800 px** | 1 | `620px 350px` | 350×263 | 64px |
| **1280** | **1800 px** | 1 | `620px 350px` | 350×263 | 64px |
| **1024** | **1800 px** | 1 | `554px 350px` | 350×263 | 64px |
| **375** | 2489 px | 1 | `299px` | 299×224 | 44px |

- 每步行高 263（首行）/ 286 px；行间距 22px
- 图片比例实测 **1.333 = 4:3** ✅ 已满足
- 数字实测 `64px` / `rgb(90,183,53)` = **#5AB735** ✅ 已满足
- 整页 `body` 高 7122px（1440）

> 你给的「约 1800-2000px」**实测 1800px**，精确命中。

---

## 2. 三处与指令不一致

| # | 你的描述 | 实测 | 影响 |
|---|---|---|---|
| 1 | 「3 步各占一整行」 | **6 步**各占一整行（01–06） | 6 步做 3 列 ⇒ **必然 2 行**，不是 1 行 |
| 2 | 「高度约 600px（省 70%）」 | 3 列实测 **861px（省 52%）** | **600px 数学上做不到**（见 §4 的算式） |
| 3 | 「图片约 50% + 文字约 50%」 | 图固定 **350px** / 文字 620px ⇒ 图占 **34.5%** | 交替（zigzag）是真的，比例描述不对 |

**其余描述全部属实**：图左/图右交替 ✅、太占空间（1800px ≈ 2.6 屏）✅、数字大号绿色 ✅、图片 4:3 ✅、≤900px 已单列堆叠 ✅。

---

## 3. 可复用样式盘点（回答你的第 3 问）

**结论：没有可直接套用的「3 列卡片」类。** 逐项：

| 类 | 出处 | 形态 | 能否复用 |
|---|---|---|---|
| `sf-panel--3` | style.css L548 | 3 列 grid，**`gap:0` + hairline 边框** | ❌ 语义相反——源码注释写明「cells are separated by a hairline and nothing else, so the group reads as **one table rather than as N cards**」。**是在用的**（`page-oem`/`page-services`/`page-odm`/`page-contract-manufacturing`/`page-private-label` 的 Key Facts），但它是**表格式**、且挂在 `wp:columns` 上 |
| `sf-eq` | style.css L4899 | **同页** 3 列，图 4:3 + 圆角 8 + 阴影，文字在图下居中 | ⚠️ **视觉最接近你要的卡片形态**，但挂在 `wp:gallery` 上、类不能移用；只能当**视觉参照** |
| `sf-pal` | style.css L5045 | **同页** 4 列横排（Palatability） | ❌ 无图、4 列 |
| `sf-triple` | style.css L1919 | 3 列 grid gap 24 | ❌ **模板 0 使用**（死样式），且为「列表 3 栏」设计 |
| 同页 `Full Traceability` 卡片 | page-quality.html L258–341 | 4 列 `wp:columns` + `bg-light` + radius 8 + padding 30/25 | ⚠️ 真正的「卡片」先例，但 4 列、无图 |

> ⚠️ 本次扫描中第一次查 `sf-panel--3`/`sf-triple` 用了 BSD grep 的 `\|` 交替，**静默返回空**，一度得出「模板 0 使用」的错结论。改用 `grep -E` 后修正。凡本报告中的计数均为 `-E` 口径。

**⇒ 建议实现形态：纯 CSS 改 `.sf-qs`**（31d 段重写 + ≤900 降级段同步）。DOM 已经是 `.sf-qs > article > (text + media)`，用 `flex-direction:column-reverse` 即可把图提到文字上方——**模板一行不动、零 JS、读屏顺序不变**。

---

## 4. 3 列改造的实测模拟

方法：在真页里注入一段覆盖样式（`tools/b3b_qs_measure.py --simulate`），再读同一批节点 —— 所以下面是**实测**，不是算术推算。

| 方案 | 容器 | gap | 1440/1280 | 1024 | 375 |
|---|---|---|---|---|---|
| **A**（建议） | 1014px | 28px | **861px（−52%）** | **828px（−54%）** | 2380px（1 列，基本不变） |
| B | 1200px | 32px | 954px（−47%） | 828px（−54%） | 2400px |

方案 A 的细节（1440）：每行 3 步 × 2 行；单カード高 **417px**；列宽 **319px**；图 **319×239**（4:3 保持）；数字仍 **64px #5AB735**；整页 7122 → 6184px。
方案 B 列更宽（379px）但更高（954px）——**容器放宽反而变高**，因为列宽变大直接抬高 4:3 的图。

### 为什么到不了 600px（算式）

方案 A 单卡 417px 的构成：

```
图（319 宽 × 4:3）              239
数字：64px 字号 × line-height 1   64
数字上/下边距                    16 + 8
标题 24px × 1.25                 30
标题下边距                        8
描述 16px × 1.6（1–2 行）        26 ~ 51
────────────────────────────────────
合计                           391 ~ 416   ← 实测 417 ✅
```

6 步要让总高 = 600px，则单卡 ≤ (600 − 28) / 2 = **286px**。而 4:3 的图已经占 239px，**只剩 47px 装「64px 数字 + 标题 + 描述」——装不下**。

⇒ 要真到 600px，只能牺牲一条（都与你的约束冲突）：

| 手段 | 预计总高 | 冲突 |
|---|---|---|
| 数字叠加到图片上 | ≈ 686px | 与「数字保持大号绿色」冲突（照片上需改白字/加底色） |
| 图片改 16:9 | ≈ 742px | 与「图片比例 4:3」冲突 |
| 删掉 3 步（只留 3 步 1 行） | ≈ 417px | 与「标题 + 描述保留原文」冲突 |

---

## 5. 连带影响

| 项 | 结论 |
|---|---|
| **`/quality/` 在 `tools/b2d_s3_paths.txt` L5** | ✅ 在 75 页抓页基线内 ⇒ pull 后的全站逐字节比对会把这一页标为**预期差异** |
| **`b2d_h7_gate.py` 的 4 处 `/quality/`** | 均**不是**本区块断言：L3631（`H7J_MENU` 菜单表，判「无下拉子项」）、L4143（负对照把 mark 移到 `/quality/`）、L4476（H7k 批的历史 transform，读快照）、L4597（**注释**）。`sf-qs` 在该门 **0 命中** |
| **其他工具** | `b2d_h5_0_geom.py`／`b2d_h6_geom.py`／`b2d_h5_e2e.py`／`b2d_s3_fetch.py` 对 `quality`／`sf-qs` **各 0 命中**；`b2d_h8c_live_check/accept/e2e/shots` 也不抓 `/quality/` |
| **门是否需要更新断言** | **不需要**。没有任何活门对本区块做断言。（h7_gate 读**冻存快照**、不读工作区，批 3b 已实跑证明其在本类改动后仍 PASS。） |
| `_backup/b2d-h8c-baselines/quality.html` | 在（161444 B），h8c 门用它做快照比对 ⇒ 仍是快照 vs 快照，不受影响 |
| 历史工具 | `tools/q3_verify.js`／`q3b_diag.js`／`q4_shots.js`／`quality_scan.js`／`q2_patch_quality.py` 含 `sf-qs` 引用 —— 是当初做该页的**历史脚本**，不在活链 |
| **版本** | 工作区**已是 `2.10.77`**（批 3b bump、**尚未 pull**）⇒ 本项与批 3b 合并成**一次 pull** 的话，**共用 2.10.77 即可**，不必再 bump 到 2.10.78 |
| DIFF 范围 | **`/quality/` 一页**（+ `/zh/quality/` 同模板）＋ 每页 `style.css?ver=` ⇒ 与你写的「/quality/ 页」一致 |

---

## 6. 顺带核查：C1 与 `What We Handle` 同字重复（你要的执行顺序第 1 项）

实测两边文本**逐字相同**（4 条），同在 `/services/`，中间只隔一个带：

| 位置 | 内容 |
|---|---|
| `page-services.html` L150–177 · `What We Handle` → **`R&D & Formulation`** 栏 | `Custom formula development` / `Custom active ingredient levels` / `Palatability testing` / `Stability testing` / `Packaging compatibility testing` |
| 批 3b 新建的 **C1 `Custom Formulation Capability`** | `Custom formula development` / `Custom active ingredient levels` / `Palatability testing` / `Stability testing` ← **前 4 条逐字重复** |

**差异化建议（不改语义、不新增内容，三选一）**：

- **F1（最小改动）**：C1 换成「过程/结果」措辞 —— `Concept-to-formula development` / `Potency set to your label claim` / `Palatability & acceptance testing` / `Accelerated & real-time stability studies`
- **F2（换形态）**：C1 不列清单，改一段 prose + 两个按钮（与 `What We Handle` 的 checklist **形态**区分，视觉上不再像两个一样的表）
- **F3（换粒度）**：C1 用「数字」条目（如 `12–24 month shelf-life studies`），`What We Handle` 保持能力名

---

## 7. 需你裁决（4 项真分歧）

这 4 项不是 agent 能自取的——都涉及你对**内容取舍 / 视觉形态 / 文案风格**的判断，且与你的原始指令存在实测冲突：

| # | 问题 | 我的建议 |
|---|---|---|
| **Q1** | 内容实为 **6 步**（你以 3 步描述）⇒ 3 列必然 **2 行**。接受吗？还是你本来只想展示其中 3 步？ | 接受 3 列 × 2 行，6 步一条不删 |
| **Q2** | 高度 **861px（−52%）**。600px 做不到（§4 算式）。接受 861，还是牺牲一条规格换更矮（§4 表中三选一）？ | 接受 861（4:3 图与 64px 数字都不动） |
| **Q3** | 卡片外观：**E1 无框**（图 4:3 圆角 + 图下文字，照同页 `.sf-eq` 语言）／ **E2 白底卡片**（`card-white` + radius 8 + 轻阴影，照同页 Full Traceability） | **E2** —— 区块底色是 `bg-light`，白卡能立起来；无框会与同页 QC Lab 图库过于雷同 |
| **Q4** | C1 与 `What We Handle` 同字重复（§6），差异化用 **F1 换措辞**／F2 换形态／F3 换粒度？ | **F1**（改动最小、语义不失） |

## 7b. 已按默认拍板（4 项，如无异议即照此实施）

| 项 | 定为 | 依据 |
|---|---|---|
| 容器宽度 | 保持 **1014px** | 方案 A 实测 861px；放宽到 1200px 反而变高到 954px |
| 1024 视口 | **不加中间档**，维持 3 列 | 列宽 297px、图 297×223，可读；你只要求「桌面 3 列 + 移动 1 列」两档 |
| 移动端断点 | 保持 **900px** | 现状即 900；不改既有降级点 |
| 版本 | 与批 3b **共用 `2.10.77`** | 批 3b 尚未 pull ⇒ 两批字节合并成一次 pull，无需再 bump |

---

## 8. 若确认，建议的执行序列

1. `style.css` 31d 段重写（3 列 grid + `column-reverse` + 删 even 翻转与 hairline）+ ≤900 降级段同步
2. C1 差异化（F1）
3. `install <SHA>` 到**预检层**（不动 live）
4. 截图 1024 / 1280 / 1440（`b3b_qs_measure.py --simulate` 已能出数字，改后可用同一脚本复核）
5. 报告 → **停下等你确认 pull**

**已停下，等你指令。不继续实施，不碰生产站。**
