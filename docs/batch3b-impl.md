# 批 3b 补做 — 实施记录

**状态**：主题改动完成，本地离线自检 **34/34**；已 commit + push。
**站点**：**未 pull**（按约束），dev 仍服务 `2.10.76` 的字节 ⇒ 站点级核验与 D1 的三档截图**待授权**。
**授权**：D1–D8 全部按建议；另两个连带坑（标签改写、`EXPECT_VER`）一并处理（2026-09-24）。

---

## 1. 五项交付（精确落点）

### ② 页脚加 Services 栏 — `parts/footer.html`

在 Products 栏的 `<!-- /wp:column -->`（原 L29）之后插入**一个** `wp:column`，
复刻既有列的结构（`wp:details` + `wp:footcol` + `wp:footlinks`）：

```html
<summary>Services</summary>
<p class="sf-footlinks" style="font-size:14px"><a href="/services/oem/">OEM Manufacturing</a><a href="/services/odm/">ODM Custom Formulation</a><a href="/services/private-label/">Private Label</a><a href="/services/contract-manufacturing/">Contract Manufacturing</a><a href="/cooperation/">Cooperation Models</a></p>
```

- **零 DB 改动**，纯模板文件 ✅
- **D7 按你给的原顺序**（…Private Label → Contract），`Cooperation Models` 按 **D6 追加在同一栏内**（不是第 6 栏）
- 页脚由 **4 栏变 5 栏**

### ③ 首页 4 框加链接 + 区块级按钮 — `templates/front-page.html`

4 个 `h3`（原 L561 / L589 / L617 / L645）各包一层，与 `/services/` 4 卡**同法**：

| 卡 | 链接 |
|---|---|
| OEM — You Bring the Formula | `/services/oem/` |
| ODM — We Develop From Your Idea | `/services/odm/` |
| Contract Manufacturing | `/services/contract-manufacturing/` |
| Private Label | `/services/private-label/` |

落点是 `<h3 class="wp-block-heading"><a class="sf-card__title-link" href="…">…</a></h3>`。
**视觉零变化、零 CSS、零 JS**：`.sf-card__title-link::after{inset:0}` 与 `:focus-visible` 描边都是**既有**规则。

区块末尾（`<!-- /wp:columns -->` 与 `</section>` 之间）加：

```html
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},…} -->
<div class="wp-block-buttons" …><div class="wp-block-button"><a class="wp-block-button__link wp-element-button sf-btn-outline has-border-color" href="/services/">See all services →</a></div></div>
```

**D2 用首页自己的约定**（`sf-btn-outline`，与 L1321 `View All Articles` / L1376 `View All FAQs` 同款），**D8 居中**。

### ④ 总览页补两带 — `templates/page-services.html`

**C1 `Custom Formulation Capability`**（What We Handle 之后）— `card-white`、`sf-checklist sf-checklist--panel` 4 条、两个按钮 → `/services/odm/`、`/quality/`
**C2 `Manufacturing Capability`**（How We Work 之后）— `card-white`、4 条、两个按钮 → `/factory-tour/`、`/quality/`

**只做摘要 + 去处，未搬 `/factory-tour/` 与 `/quality/` 的内容**；两带副标的措辞与那两页的既有 h2 不同字。

**D3 方案 a 落地**：`How We Work` 的带底色由 `card-white` 翻 `bg-light`，换得**严格白/浅交替**：

```
hero · light · white · light · white(C1) · light(How We Work) · white(C2) · light · primary
```

**D5** 用 `sf-checklist--panel`（基础类 `sf-checklist` 无 CSS，必须带 `--panel`）；**D4** 两个按钮。

### ⑤ `/cooperation/` 孤页

按 **D6** 追上在 Services 栏内：`Cooperation Models → /cooperation/`。该页已 200，此后**有常驻入口**。

---

## 2. 连带处理（⑥）

| 项 | 结果 |
|---|---|
| **toc-nav 圆点轨** | **零改动即 6 → 8 点** ✅（见下） |
| **`OVERVIEW_H2`** | 6 条 → **8 条**，顺序敏感：`…Custom Formulation Capability` 插在 What We Handle 之后、`Manufacturing Capability` 插在 How We Work 之后 |
| **同一断言的中文标签** | 由 `...and the overview itself is otherwise untouched by the batch` 改为 `...and the overview still carries its own breadcrumb level, terms table and full heading set` —— 加了带之后，原句"otherwise untouched"**变成假话** |
| **`EXPECT_VER`**（accept L46） | `2.10.76` → **`2.10.77`** |
| **`--expect-ver` 默认**（check L198） | `2.10.76` → **`2.10.77`**（你扫描时清单里没有的第三处版本硬编码） |
| **style.css 版本** | `Version: 2.10.76` → **`2.10.77`** |
| **functions.php enqueue** | `array(), '2.10.76'` → **`2.10.77`**（两处同步，主题树内已无 `2.10.76` 残留） |
| **DIFF 范围** | 比你写的更宽：`parts/footer.html` 是**全站 template part**，且 `style.css?ver=` 出现在**每一页** ⇒ **全站每一页的字节都会变**（不只是首页 + /services/ + 页脚） |

**toc-nav 为什么零改动**：`collectH2s` 取 `main` 下所有 `h2`，排除 lightbox/modal/`[hidden]` 与 4 个 `SKIP` 正则；那 4 个正则全是**首页专属**文案（Formulated Clean / From Inquiry to After-Sales / Trusted by 30+ / Ready to launch your product?）。两个新 h2 均不被排除 ⇒ 圆点轨自动 8 点。

---

## 3. 核验

**本地离线自检 `tools/b3b_local_check.py` — 34/34 PASS**（六组：页脚 / 首页 / 按钮 / 总览页 / 版本 / 块标记）

它读**工作区源文件**，不读站点——这是本批唯一可行的核验层，因为约束是「不 pull」，dev 仍在 `2.10.76`，渲染字节在这里根本读不到。断言覆盖：

- 四栏顺序、Services 栏 5 条链接与其顺序、旧三栏未被扰动
- 4 个字幕被包成链接、包住的**文本逐字未变**、4 条负对照（unlinked 原标签在首页**已消失**）
- 区块按钮作用于 `sf-oem` 带内（页级计数会把 FAQ 那个按钮一并捞进来，故限定作用域）
- 总览页 8 带顺序、白/浅交替序列、C1/C2 的条目与去处、`How We Work` 确已翻色
- 版本两处一致 + 主题树无 `2.10.76` 残留（负对照）
- 四个模板的块标记**开/自闭/闭合**配平 + **每个块注释的属性 JSON 可解析**（手写块唯一无法用肉眼发现的失败模式）

**PHP 语法检查**：本机无 `php` 可执行文件，跳过；本次对 `functions.php` 的改动仅为**一个字符串字面量**（版本号）。

**实测发现**：`tools/b2d_h7_gate.py --batch h8c`（对**冻存快照 + source JSON**跑）在批 3b 之后**仍然 PASS** —— 该门不读工作区源码，故本批的五个主题改动与两处版本令牌**不使其失效**。这一条是用实测纠正过的推断：最初据 `nc_source` 里硬编码的 `'Version: 2.10.76'` 判断它会红，实跑后否定。

**未做（需授权）**：

1. **站点级核验**（渲染字节）—— 需 `install` 到预检层或 `pull`，**两者都未获授权**。
2. **D1 的 1024 / 1280 / 1440 三档截图** —— 同上，需站点渲染。页脚 5 栏挤压的实测数据（1440 ≈ 178px / 1024 ≈ 136px、`Contract Manufacturing` 在 1024 折行）是**扫描时的几何推算**，尚未被截图证实。

---

## 4. 与扫描报告三处不一致的最终定论

| 扫描时的提醒 | 最终做法 |
|---|---|
| 页脚会由 4 栏变 5 栏、桌面列宽被挤 | 按 **D1** 接受；截图核验待授权 |
| 你给的 `sf-explore__btn` 是**剂型页**的类，首页 0 次使用 | 按 **D2** 改用首页约定 `sf-btn-outline`（视觉等同，2px 描边 / 6px 圆角 / 透明底 / 600 字重） |
| 两带底色交替必须动 1 个既有带 | 按 **D3 方案 a**：翻 `How We Work`，换严格交替 |

---

## 5. 待裁决（我没有替你决定）

1. **D1 截图核验的方式**：先 `install` 到预检层截图，还是等整体上线时一起看？
2. **C1 的 4 条与 `What We Handle` 的 `R&D & Formulation` 栏前 4 条同字**（这是你给的原文）。同页重复；若要差异化，改 C1 措辞即可，一处改动。
3. **C2 的 4 条与 `/quality/`、`/factory-tour/` 语义相邻**（措辞已刻意不同字，但读者可能仍觉重复）——是否进一步收紧？
4. **`/cooperation/` 之外**：导航仍无 4 子页入口（页脚现在有了）；导航改名由你自己做。
5. **手机固定层遮挡卡片下缘**（旧账，非本批引入）。
6. **生产上线**（`docs/dev-lockdown.md` 10 项）仍未授权。
