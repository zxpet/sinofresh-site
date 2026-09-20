# 认证口径 2.1 复核（2026-09-18 17:2x）
**方法**：不信任 `about-prelaunch-todo.md` §2.1 的行号，改为全量重扫活模板（排除 `_backup*/`、`docs/`、`tools/`），实体归一（`&middot;` / `&#183;` → `·`）后再匹配，并叠加前端渲染层复核（跟随 301）+ 数据库复核。
**脚本**：`sinofresh-theme/tools/_cert_scan.py`（文件层）· `curl -sL` 14 个 URL（渲染层）· `wp_options/wp_posts` 查询（DB 层）

---

## 一、doc §2.1 的 22 处逐项现状

| doc 项 | doc 位置 | 现状 | 结论 |
|---|---|---|---|
| A1–A8 | 8 剂型页徽章条 `:20` | 8 处全在。其中 `dental-chews / drops / fish-oil / liquids` 用 `&middot;` 实体写法，`soft-chews / tablets / powders / pastes` 用字面 `·` | **需改 8** |
| A9 | `page-quality.html:15` | 在 | **需改** |
| A10 | `page-services.html:15` | 该页 14:50 重构后 hero 已无徽章条；残留迁到 **168–169 行**「Compliance & Quality」清单（`FDA registration · cGMP` + `ISO 9001 · FSSC 22000` 两行） | **需改（新位置）** |
| A11 | `page-factory-tour.html:15` | 在，且同一行尾部挂着 `· 10,000-Class Cleanroom` | **需改** |
| B1–B8 | 8 剂型页规格行 `:66` | **全站已无「认证规格行」**：8 个剂型页现在每页只有 1 处认证文本（徽章条），规格面板不再列认证 | 已消失，无需改 |
| C20 | `page-quality.html:12` | 在（prose 句） | **需改** |
| C21 | `page-services.html:12` | 在（逗号列表形态） | **需改** |
| C22 | `page-soft-chews.html:546` | 在，现为 **532 行**（行号漂移），同 1 行同时喂 JSON-LD FAQ，渲染出 2 处 | **需改** |
| §2.2 | `factory-tour:15` 洁净车间 | 实际 **3 处**：`:12` prose、`:15` 徽章条、`:78` 清单条 | **需改 3** |

**遗漏 / 新残留（doc 未列）**

| # | 位置 | 当前文案 | 说明 |
|---|---|---|---|
| N1 | `functions.php:1171` | `8 dosage forms, flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000.` | /services/ 页的 meta description 与 JSON-LD `serviceType`，渲染层出现 2 次 |
| N2 | `page-services.html:168–169` | 见上 A10 | 页面重构后迁移的残留 |
| N3 | `functions.php:607` `sf_default_certifications()` | 默认仅 **4 项 active** + 4 空槽 | 全新安装/重置后顶栏徽章只出 4 认证 |
| N4 | DB `wp_options.sf_certifications` | 6 项 active，但第 5 项名为 **`BRCGS`**（全站口径是 `BRC`），顺序为 `… FSSC 22000 · BRCGS · HACCP`（与全站「… HACCP, BRC」不一致） | 顶栏徽章，每页可见 |

**已达标核对（§2.3 不动清单）**

- `parts/footer.html:9` ✅ 6 认证 · `page-about.html:181` ✅ 6 认证 · `page-faq.html:70` ✅ 6 认证
- `front-page.html` ✅ 6 认证在 **20 / 1248 / 1324 / 1490** 四处 + 证书卡 6 张（`:492–518`）。doc 写的 `1192 / 1268 / 1434` 三行已**不是认证文本**（分别是客户名 `Mark T.`、MAP 区块 `sf-map__region`、博客标题），行号失效
- `front-page.html:14` hero eyebrow `OEM / ODM · FDA registered · cGMP` → 按决定**不动**

**其他层复核**

- DB `wp_posts`：无正文残留。`wp_template` ID 91（front-page，publish，09-17 20:36）内容已是 6 认证，且被主题守卫中和；旧 revision 71–75 含 4 认证 + `10,000-class`，属历史快照，不参与渲染
- `inc/config-pdf.php:425 / 492`、`inc/cert-download.php` 均为 6 认证 ✅
- 洁净车间措辞：除 `page-factory-tour.html` 3 处外，全站（`front-page:54/1327`、`page-about:45/141`、`inc/config-pdf.php:432/519`、8 剂型页轮播 alt）**已是 `ISO 8 cleanroom(s)`** ✅

---

## 二、2.2 执行清单（17 处 / 12 文件）

### A 类 · 徽章条（11 处）
| # | 文件:行 | 旧 | 新 |
|---|---|---|---|
| 1–4 | `page-soft-chews/tablets/powders/pastes.html:20` | `FDA · cGMP · ISO 9001 · FSSC 22000` | `FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC` |
| 5–8 | `page-liquids/drops/fish-oil/dental-chews.html:20` | `FDA &middot; cGMP &middot; ISO 9001 &middot; FSSC 22000` | 追加 ` &middot; HACCP &middot; BRC`（**保留实体写法**） |
| 9 | `page-quality.html:15` | 同 #1–4 | 同新串 |
| 10 | `page-factory-tour.html:15` | `FDA · cGMP · ISO 9001 · FSSC 22000 · 10,000-Class Cleanroom` | `FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC · ISO 8 cleanroom` |
| 11 | `page-services.html:168–169` | `<li>FDA registration &#183; cGMP</li>` / `<li>ISO 9001 &#183; FSSC 22000</li>` | `<li>FDA registration &#183; cGMP &#183; ISO 9001</li>` / `<li>FSSC 22000 &#183; HACCP &#183; BRC</li>`（3+3 分配，保持实体写法） |

### B / C 类 · 正文（4 处）
| # | 文件:行 | 旧 | 新 |
|---|---|---|---|
| 12 | `page-quality.html:12` | `FDA registered, cGMP compliant, ISO 9001 and FSSC 22000 certified.` | `FDA registered, cGMP compliant, ISO 9001, FSSC 22000, HACCP and BRC certified.` |
| 13 | `page-services.html:12` | `… flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000.` | `… flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.` |
| 14 | `functions.php:1171` | 同 #13 字符串 | 同 #13 新串（meta description + JSON-LD） |
| 15 | `page-soft-chews.html:532` | `FDA registration, cGMP, ISO 9001, FSSC 22000.` | `FDA registration, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.` |

### D 类 · 洁净车间（3 处，其中 `:15` 与 #10 同一行）
| # | 文件:行 | 旧 | 新 |
|---|---|---|---|
| 16 | `page-factory-tour.html:12` | `… 10,000-class cleanroom, R&D center …` | `… ISO 8 cleanroom, R&D center …` |
| 17 | `page-factory-tour.html:78` | `10,000-class cleanroom` | `ISO 8 cleanroom` |

### 附 · 徽章数据源（2 处，随本轮一并收口）
| # | 位置 | 旧 | 新 |
|---|---|---|---|
| 18 | `functions.php:607 sf_default_certifications()` | 4 项 active（FDA/cGMP/ISO 9001/FSSC 22000）+ 4 空 | 6 项 active（FDA/cGMP/ISO 9001/FSSC 22000/HACCP/BRC）+ 2 空 |
| 19 | DB `wp_options.sf_certifications` | `… FSSC 22000 · BRCGS · HACCP` | `… FSSC 22000 · HACCP · BRC`（名称 `BRCGS`→`BRC`，顺序对齐全站） |

**已定默认假设（不留待确认）**
1. 洁净车间统一用**小写 `ISO 8 cleanroom`**（与 `front-page/about/config-pdf` 现有写法一致，也即指令里的字面串），徽章条内部大小写服从全站统一。
2. 徽章条 6 项顺序统一为 `FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC`（HACCP 在 BRC 前，与 footer/FAQ/About 一致）。
3. `page-quality.html` 证书行的 COA 按钮与灯箱小字不在本轮范围（阶段 1 已定稿）。

---

## 三、执行后校验口径
1. `grep -rn "FDA · cGMP · ISO 9001 · FSSC 22000"`（含实体等价形式）= 0
2. `grep -rn "10,000-Class\|10,000-class"` = 0
3. 8 剂型页徽章 + quality/services/factory-tour 徽章渲染层 = 6 认证
4. 渲染层复核 14 个 URL：无 4 认证串、无 `10,000-class`
5. 源码 = Local `cmp -s` 全等；`grep -rn "/ -->"` = 0
6. 截图：2 个剂型页 header + quality 徽章区 + factory-tour 徽章/清单
