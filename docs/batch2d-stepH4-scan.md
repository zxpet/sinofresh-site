# 批次 H4 Step 0 —— 只读扫描 ＋ 【停机报告】

> **状态：只读扫描完成，未改任何字节（主题侧 0 字节、DB 0 行）。**
> **触发停机第 ③ 类「需改数据」** —— playbook §第九部分【前置改动：邮箱变更】第 5 条明写
> *「**涉及改 DB 时停下汇报**」*。扫描实测：**该前置改动确实必须改 DB（12 行 / 3 张表）** ⇒ 停机待裁决。
> 扫描方式：主题静态盘点 ＋ 75 页断面解码（`_backup/b2d-h3-candidates/`）＋ **两枚零写入探针**
> （`tools/b2d_h4_emailprobe.php`、`tools/b2d_h4_tpprobe.php`，均走 `wp eval-file`，只用 `get_option` /
> `get_posts` / `get_post_meta` / `$wpdb->get_results` 的 SELECT）。
> 关联：`docs/agent-playbook.md` §【前置改动：邮箱变更】／§【H4】。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 主题侧 `info@zxpet.com` | **8 处需改**（另 **5** 处已是 `sales@`，是注释与收件人，**不动**） |
| DB 侧 | ⛔ **11 行 / 3 表**（跳过 revision 后实改 **10 行**）：`wp_options` ×1、`wp_posts` ×4、TranslatePress ×6 |
| 渲染侧实测 | **75/75 页**都带这个地址：CF 混淆 **155 处**（全解码为 `info@`）＋ JSON-LD `email` **75 处** |
| DIFF 集合 | **75 / 75 页全变**（不是 42 页）—— 因为 header topbar ＋ footer ＋ 悬浮按钮 ＋ Organization schema 都是全站件 |
| 合规面 | 3 张法务页正文（Privacy ×2、Cookie ×1、Terms ×1）＋ 3 行 TP 原串 |
| 停不停 | ⛔ **停**（第 ③ 类：需改数据） |

---

## 1. 【前置】邮箱变更：主题侧（活代码，13 处）

| # | 文件:行 | 现值 | 类别 | 处置 |
|---|---|---|---|---|
| 1 | `functions.php:4040` | `'sf_contact_email' => 'info@zxpet.com'` | **站点设置默认值**（`sf_site_settings` 注册表） | 改 |
| 2 | `functions.php:4093` | `return ($v !== '') ? $v : 'info@zxpet.com';` | 净化器兜底 | 改 |
| 3 | `functions.php:4555` | Organization schema `'email' => get_option('sf_contact_email', 'info@zxpet.com')` | 结构化数据 | 改（默认值部分） |
| 4 | `functions.php:4962` | 证书出站邮件署名 `info@zxpet.com · +86 539 866 9539 · zxpet.com` | **发给客户** | 改 |
| 5 | `inc/config-pdf.php:440` | PDF 页脚 `Request samples<br>info@zxpet.com · …` | **发给客户（生成的 PDF）** | 改 |
| 6 | `inc/config-pdf.php:527` | PDF 页脚 `Request a sample<br>info@zxpet.com · …` | 同上 | 改 |
| 7 | `inc/cert-download.php:169` | 404 提示 `Please email info@zxpet.com.` | 面向访客文案 | 改 |
| 8 | `templates/page-contact.html:48` | `<a href="mailto:info@zxpet.com">info@zxpet.com</a>` | **联系页正文** | 改 |
| 9 | `functions.php:4925` | `$sales = 'sales@zxpet.com'` | 收件人 | **不动** |
| 10–11 | `inc/config-pdf.php:102` / `:195` | `array('Cc: sales@zxpet.com')` | 抄送 | **不动** |
| 12–13 | `inc/config-pdf.php:14` · `assets/js/basket.js:10` | 注释里的 `cc sales@zxpet.com` | 注释 | **不动** |

> ⚠️ **header / footer / 悬浮按钮里一个字母都不用改** —— 它们走 `{{sf-email}}` 占位
> （`parts/header.html:20` 顶栏、`parts/footer.html:52` 页脚联系行、`parts/footer.html:113` 悬浮邮件按钮），
> 由 `functions.php:4235` 从 **DB 选项** 替换而来。
> ⇒ **这三处在源码上"找不到 `info@`"不等于没问题：它们的真源在 DB。** 这正是本批必须停机的原因。

---

## 2. 【前置】邮箱变更：DB 侧（11 行 / 3 张表；跳过 revision 后实改 10 行）

只读探针输出（`tools/b2d_h4_emailprobe.php`）：

### 2.1 `wp_options` —— 1 行

| option_name | 现值 | 目标 | 驱动的界面 |
|---|---|---|---|
| `sf_contact_email` | `info@zxpet.com` | `sales@zxpet.com` | ① 顶栏邮箱 ② 页脚联系行 ③ **悬浮邮件按钮**（3 个悬浮按钮之一）④ Organization schema `email` |

### 2.2 `wp_posts` —— 4 行

| ID | 类型 | slug | `info@` 出现 | 处置 |
|---|---|---|---|---|
| 3 | `page` / publish | `privacy-policy` | **2** | 改 |
| 37 | `page` / publish | `cookie-policy` | **1** | 改 |
| 38 | `page` / publish | `terms` | **1** | 改 |
| 36 | `revision` / inherit | `3-revision-v1` | 2 | ⛔ **建议跳过**（revision 不对外渲染；动它只会污染修订史） |

### 2.3 TranslatePress —— 6 行（3 原串 × 2 表）

`wp_trp_original_strings`：

| id | `original` | 归属 |
|---|---|---|
| 53 | `info@zxpet.com` | 模板输出（顶栏/页脚） |
| 138 | `mailto:info@zxpet.com` | 联系页正文 |
| 1364 | `If you have questions about these Terms, please contact us at info@zxpet.com.` | **post 38 = Terms**（`wp_trp_original_meta` 实证 `post_parent_id = 38`） |

`wp_trp_dictionary_en_us_zh_cn`：同 id 的 3 行，`translated` **全为空串**、`status` **全为 0**
⇒ **这三串目前没有中文译文**，所以改 `original` 不会破坏任何已有译文配对；
但**必须跟着改**，否则 TP 会在下次渲染时把旧串当孤儿、新串当未登记。

`wp_postmeta` / `wp_terms`：**0 行**。

---

## 3. 【前置】邮箱变更：渲染侧实测（75 页断面解码）

CF 的 `email-protection` 是**异或混淆**（首字节为密钥）。对 75 页断面逐页解码后：

| 指标 | 实测 |
|---|---|
| 解码出的地址分布 | `{info@zxpet.com: 155}` —— **没有一个 sales@** |
| 每页 CF 邮箱数 | 71 页 ×2、3 页 ×3、1 页 ×4（合计 **155**） |
| JSON-LD `"email": "…"` | **75 / 75 页各 1 处**（44 页紧凑 ＋ 31 页精美 = 75，见下） |
| **会变的页数** | **75 / 75** |

> ⛔ **又一次踩中 H3 的那个坑（附录 A.8 #1）**：本扫描第一版用 `"email":"info@zxpet.com"`（紧凑字面）
> 去数，得到「**44 页有、31 页没有**」的假结论。真相是那 31 页（＝中文页）的 JSON-LD 由 TranslatePress
> **重新序列化成精美格式**（`"email": "info@zxpet.com"`，冒号后有空格）。
> 改用 `"email"\s*:\s*"…"` 后 **44 ＋ 31 = 75/75**。
> **教训升格**：凡"页面里有某字段"的计数，判据必须容忍序列化差异，或直接走解析。

**DIFF 集合推论**：因为顶栏／页脚／悬浮按钮／Organization schema 都是**全站件**，
这一前置改动**必然让 75 页全部变更**（不是 H3 那样的 42 页）。
⇒ 回归门不能用"H3 的 42 页清单"，必须重新走一遍 75 页限定证明。

> ⚠️ 断面里**没有** `/zh/privacy-policy/`、`/zh/terms/`、`/zh/cookie-policy/`
> （75 页清单里只有 EN 的三张法务页）。若要覆盖中文法务页，需**扩断面**，这是裁决项之一。

---

## 4. 停机判定

| 依据 | 内容 |
|---|---|
| playbook §第九部分【前置改动：邮箱变更】第 5 条 | *「**涉及改 DB 时停下汇报**」* |
| 停机分类 | **第 ③ 类「需改数据」** |
| 实测触发 | DB 侧 **11 行 / 3 表**（含 TP 自有的 6 行；跳过 revision 后实改 10 行）；且 **`sf_contact_email` 是真源**，不改它则顶栏/页脚/悬浮按钮 4 个界面全部滞留旧值 |
| 未改证据 | 主题 0 字节；DB 只读（`SHOW COLUMNS` / `SELECT` / `get_option` / `get_post_meta`） |

---

## 5. 待裁决 4 项

| # | 问题 | 推荐 | 理由 |
|---|---|---|---|
| **C1** | **改到什么范围**：只改"收件人/对外邮箱"，还是**全站连展示地址一起**换成 `sales@`？ | **A：全站统一 `sales@`**（含联系页 `mailto`、PDF 页脚、证书邮件署名、法务页正文） | playbook 第 2 条就是「**全部改为**」；留两套地址会让客户在两个入口看到不同邮箱，且 Organization schema 与页面不一致会被结构化数据校验标记 |
| **C2** | **`sf_contact_email` 的显示语义**：它同时喂 **Organization schema `email`**（公司级）与页脚/顶栏/悬浮按钮。改它＝让"公司联系邮箱"变成销售邮箱 | **A：一起改** | 单一真源；否则 schema 与页面又分叉。若将来要区分，应新增第二个选项，不该在本次拆 |
| **C3** | **TP 的 6 行怎么改**：走 TranslatePress 编辑器，还是直接 SQL 同步 `original`？ | **A：直接同步 `original`**（3 行 `original_strings` ＋ 3 行 `dictionary`），因为三行 `translated` **全空、status 0** ⇒ 无译文可破坏 | 走 TP 编辑器需要先改页面内容、再逐串重译，成本高且本批不产出中文新文案；三串都无译文，同步成本最低、风险最小 |
| **C4** | **法务页正文要不要改**：Privacy/Cookie/Terms 里写的是 `info@`。改了要动 3 张已发布页的正文 | **A：改**（与 C1 同口径） | 法务页写 `info@` 而站上其他地方是 `sales@` 会自相矛盾；且在合规审阅里"联系方式不一致"是要点 |

> **附带两条不改动项**（已判定，无需裁决）：
> ① `wp_posts` ID 36（revision）不动 —— 它不渲染。
> ② `functions.php:4925`、`config-pdf.php:102/195`、以及两处注释已是 `sales@`，不动。

---

## 6. H4 本体扫描（不受前置阻塞的部分）

### 6.1 端点范本：3 个现成 REST 路由

| 路由 | 文件 | 形态 |
|---|---|---|
| `/sinofresh/v1/article-feedback` | `functions.php:4693` | 最近的一个，无附件 |
| `/sinofresh/v1/config-pdf` | `inc/config-pdf.php:34` | 生成 PDF ＋ `wp_mail($email, …, array('Cc: sales@zxpet.com'), array($tmp))` |
| `/sinofresh/v1/cert-download` | `inc/cert-download.php:139` | 附件 ＋ 24h 单次令牌 |

⇒ H4 的询盘端点应**照 `article-feedback` 的轻量形态**（无附件、无 PDF），
但**发信口径照证书那条**：`gform_after_submission_5`（`functions.php:4919-4992`）的
「客户信 ＋ 必然一份给 sales」模式，即**地址不可用时把销售当唯一收件人**。

### 6.2 悬浮层现状

`parts/footer.html:112-114` 已有 **3 个悬浮按钮**：WhatsApp ／ 邮件（`mailto:{{sf-email}}`）／ 回到顶部。
H4 要加的第 4 个（询盘）必须与它们**同栈对齐**——
H2b1 附录 A.5 #7 已实测该栈的底距（现代引擎：有横幅 1440 `100px` / 480 `268px`，无横幅 24/16px；lang `0px`），
**新增按钮不能改这组既有几何**，只能插进栈内。

### 6.3 移动端抽屉范本：已有

`style.css` 第 45 节已有完整的 **slide-in drawer**：`.sf-basket-drawer` ＋ overlay ＋
`.is-open` ＋ `[hidden]` ＋ `__header` / `__close` / `__content` / `__actions`（6006-6260 行）。
⇒ H4 的「移动端全屏抽屉」应**复用这套交互语言**（同样的 `is-open` / `[hidden]` / overlay / esc 关闭），
而不是另造一套。

### 6.4 表单与锚点现状

- 锚点：`#inquiry-form` 存在于 `templates/front-page.html:1415` 与 8 个剂型页（如 `page-fish-oil.html:391`）；
  `/contact/#quote` 是全站 CTA 的落点（`sf-quote-cta` → `quote-cta.js 1.0.0` 智能滚动）。
- 邮件表单：现有 Gravity Forms（form 5 ＝ 证书索取，`gform_after_submission_5`）。
  **H4 的 5 字段询盘是"另建 REST 端点"还是"复用 GF 表单"，是 H4 Step 0 的第二个裁决点**
  （playbook 写的是 REST 路由 ＋ honeypot ＋ 3 秒时间验证，语气更接近自建）。

### 6.5 现有 enqueue（H4 要挂第 5 个脚本，需与它们同批）

`sinofresh-style 2.10.57`／`sticky-header 1.0.0`／`ui-components 1.0.0`／`mobile-nav 1.1.0`／
`basket 1.3.0`／`quote-cta 1.0.0`／`toc-nav 2.0.0`（条件）／`hero-slider 1.1.1`（首页）。
⛔ **H4 的弹窗脚本必须只挂在需要的页面**（详情页 ＋ 有 `#inquiry-form` 的页），
不要无脑全站入队 —— H2b2 刚因为"无脑入队"删掉过一个配置器。

---

## 7. 不受影响、可照做的部分

1. **H4 的 UI 骨架**（弹窗 DOM、悬浮按钮、移动端抽屉样式）与邮箱变更**无耦合**，可在裁决后一并做。
2. **Sampling 4 步内嵌**：`sinofresh_sampling_steps()` 已就位（H3），H4 直接复用。
3. **honeypot ＋ 3 秒时间验证**：纯新增，不受影响。
4. **回归门架构**：H3 的 `tools/b2d_h3_confine.py` 可直接改造成 H4 的版本
   （三段 run 换成"邮箱令牌 ＋ 新增块"两组，锚点机制不变）。

---

## 8. 证据索引

| 文件 | 内容 |
|---|---|
| `tools/b2d_h4_emailprobe.php` | DB 侧只读普查（options / posts / postmeta / TP / terms） |
| `tools/b2d_h4_tpprobe.php` | TranslatePress 三张表的逐行视窗 |
| `_backup/b2d-h3-candidates/` | 75 页断面（本次渲染侧解码的数据源） |
| 本档 §1–§3 | 主题 13 处 ＋ DB 12 行 ＋ 渲染 75 页的完整改动面 |
