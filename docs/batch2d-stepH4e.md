# 批次 H4e 全档 —— 邮箱变更（H4 的【前置改动】）

> **状态：Step 1–5 全过门 + E2E 全过；Step 6（`git pull`）按用户 2026-09-22 规则整条跳过。**
> 主题提交 **`24da600edecfb666445d01e9b96b0675b7e1d893`**；基线 **`4ca3aea`（＝H3 预检副本断面）**。
> 声明范围：**主题侧 9 处**（5 文件）＋ **DB 侧 10 行**（3 表）＝ 全部 `info@zxpet.com` → `sales@zxpet.com`。
> **无 ver bump**（`style.css` 未动、无资产变更）⇒ 判据是「**每一页上唯一的差别就是这个地址**」。
> Step 0 扫描档：`docs/batch2d-stepH4-scan.md`（含四项裁决）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 主题 diff | **9 增 / 9 删**，恰 5 文件（`functions.php` ×4、`config-pdf.php` ×2、`cert-download.php` ×1、`page-contact.html` ×1、`make_coa_sample.php` ×1） |
| DB diff | **10 行 / 3 表**：`wp_options` ×1、`wp_posts` ×3、TP `original_strings` ×3、TP `dictionary` ×3（**revision 36 按声明跳过**） |
| 主门（解码式限定证明） | **PASS — 八条门全过**：75/75 页**逐字节**有差，且**解码后**＝基线做**一次全局替换** |
| 破坏矩阵 | **14/14** 全 CAUGHT |
| 具名负对照 | **5/5** 全部按名失败 |
| **A/A 自检** | **PASS** —— 同一状态的两次独立抓取，**零误报**（这条是本批门可信度的核心） |
| H3 单测复跑 | **54 passed / 0 failed**（邮箱改动未破坏 H3 断言）＋ 负对照 **6/6** |
| 浏览器 E2E | **PASS — 17 ok / 0 FAIL**（E1–E5），0 console error |
| 实拍 | 6 张，全部 > 8000 B 下限（54 KB – 189 KB） |
| 页数 | **75/75 全部变更**（不是 H3 的 42——顶栏/页脚/悬浮按钮/schema 都是全站件） |
| 计划外 | **无** |

---

## 1. ⛔ 本批最重要的发现：既有掩码门对这次改动**是瞎的**

`tools/sf_masked_cmp.py` 的 Step 0 掩码集里有两条：

```python
(re.compile(r'email-protection#[0-9a-f]+'), 'email-protection#MASK', 'cf_email_link'),
(re.compile(r'data-cfemail="[0-9a-f]+"'),    'data-cfemail="MASK"',    'cf_email_attr'),
```

它们**把 Cloudflare 混淆的 blob 直接替换成字面 `MASK`** —— 对 H2b1/H2b2/H3 都是完全正确的
（那些批里这些 blob 只是运行噪声），但对本批**恰好抹掉了要证的那件事**：
把 `info@` 换成 `sales@` 之后，**掩码后的两页完全相同**，门会打出全绿。

**⇒ 本批不能使用标准掩码门。** 判据必须反过来 —— **把 blob 解码成明文地址**，而不是把它打码。

### 1.1 而且必须解码，不能用「原样比对」

实测（同一页连抓三次，`data-cfemail` 的 hex 全不同，整页 sha256 也全不同）：

```
about        run1: ['3b52555d547b41434b5e4f15585456', '2940474f46695351594c5d074a4644']
             run2: ['d7beb9b1b897adafa7b2a3f9b4b8ba', '50393e363f102a282035247e333f3d']
             run3: ['f891969e97b88280889d8cd69b9795', '2e474048416e54565e4b5a004d4143']
```

**Cloudflare 每次响应换一个密钥**（首字节为密钥，其余做异或）。
⇒ blob 本身是**逐次噪声必须去掉**，而 blob 里的**地址是必须留下的信号**。
两个方向相反的要求同时成立，只有「解码」能同时满足。

这也解释了 H3 的基线为什么能 75/75 逐字节相同：**那里的掩码把噪声吃掉了**。

---

## 2. 门的形状

归一化：`norm(t) = clean(decode_emails(t))`

- `decode_emails()`：`data-cfemail="H"` 与 `email-protection#H` 都解回明文地址
- `clean()`：**从 `sf_masked_cmp.py` 直接导入 `MASKS`，按名字剔掉两条 CF 规则**
  （`cf_email_link` / `cf_email_attr`），并断言「**恰好剔掉 2 条**」——
  这样两个工具不会各自漂移，也不会有人"顺手"把 CF 规则加回来
  保留的噪声掩码：preflight 目录后缀 / cache buster / GF 的 microtime 伪 id /
  GF 12h nonce / inline nonce / url nonce / 两条 base64 兜底

于是整个批次塌缩成一条陈述：

```
norm(candidate) == norm(baseline).replace('info@zxpet.com', 'sales@zxpet.com')
```

这就是主门的 [2]。八条门分别是：

| # | 断言 | 实测 |
|---|---|---|
| [0] | 两侧各 75 页、全 200、MANIFEST 均在 | ok |
| [1] | **75/75 页逐字节有差**（每一页都带这个地址） | ok |
| [2] | 解码后 = 基线做**恰好一次全局替换** | ok（逐页） |
| [3] | 候选页上**每一个**解出的地址都是 `sales@`，且明文里**没有** `info@` | ok |
| [4] | 混淆锚点**数量**不得漂移（`data-cfemail` 与 `email-protection#` 各算） | ok |
| [5] | JSON-LD 块数不变、`email` 字段恰好 1 个且为 `sales@` | ok |
| [6] | 既有不变量：h1 = 1、H3 内容带／Sampling 带／FAQ 带／Related 网格**不得出现或消失** | ok |
| [7] | **没有任何资产版本令牌移动**（本批不 bump） | ok |
| [8] | 全站混淆地址总数基线 155 ＝ 候选 155，且解码后**只有** `sales@` | ok |

**⚠️ [6] 的一个易漏点**：`band-removed` 变异第一版是把 `sf-fdetail-content` 改名成
`sf-fdetail-contentX` —— 而 `X` 版本**仍然以子串形式包含着标记**，[6] 因此判"在场"、
只有 [2] 抓到。改成**真正删掉**该子串后，[2] 与 [6] 同时开火。断言用子串匹配时必须想到这一点。

---

## 3. 破坏矩阵 14/14

```
  address-not-changed                              CAUGHT   [1] [2] [3] [5]
  half-the-pages-changed                           CAUGHT   [1] [2] [3] [5]
  address-reverted                                 CAUGHT   [2] [3] [5]
  extra-surface-added                              CAUGHT   [2]
  surface-removed                                  CAUGHT   [2] [4] [8]
  schema-email-unchanged                           CAUGHT   [2] [3] [5]
  ver-token-moved                                  CAUGHT   [2] [7]
  unrelated-word-changed                           CAUGHT   [2]
  one-page-left-behind                             CAUGHT   [1] [2] [3] [5]
  zh-pretty-schema-unchanged                       CAUGHT   [2] [3] [5]
  h1-duplicated                                    CAUGHT   [2] [6]
  band-removed                                     CAUGHT   [2] [6]
  obfuscated-blob-swapped-to-another-address       CAUGHT   [2] [3]
  mailto-kept-but-text-changed                     CAUGHT   [2] [3] [4]
  14/14 variants caught
```

`zh-pretty-schema-unchanged` 是**专门为 H3 附录 A.8 #1 那个坑**准备的：只改紧凑形态的
schema 不改精美形态 —— 如果门还用字面匹配，这条会漏。
`mailto-kept-but-text-changed` 是"半完成的编辑"的镜像形态：href 还指着旧地址而文本已改。

---

## 4. A/A 自检 —— 本批门可信度的核心

用**同一状态**的两份独立抓取（`b2d-h4e-candidates` vs `b2d-h4e-candidates-aa`，相隔数分钟）跑门：

```
  [1] pages that differ from themselves: 75 (expected 75 — the gate asserts a change happened)
  ok  [2]-[7] no page trips on noise: the decoded comparison is stable across two independent captures
A/A VERDICT: PASS — only the deliberate [1] failures, none spurious
```

**为什么必须有这条**：本批的首次运行**确实报了一屏假 FAIL** ——
Gravity Forms 的 `gform_currency` nonce 与 `gform_phone_dropdown_<microtime-hash>` 逐次变化。
那不是回归，是噪声。A/A 是唯一能证明"噪声已清干净、门不会再冤枉一个没改动的批次"的检查。
（[1] 在 A/A 里**故意**失败：它断言"页面有差"，两份相同状态当然没差。）

---

## 5. 具名负对照 5/5

```
  served-manifest-missing          FAIL (as required)  baseline MANIFEST.tsv is missing
  baseline-empty                   FAIL (as required)  baseline directory is empty
  candidate-equals-baseline        FAIL (as required)  candidate is a copy of the baseline
  page-missing-from-candidate      FAIL (as required)  one candidate page is absent
  addresses-never-moved            FAIL (as required)  candidate still carries the old address throughout
  5/5 controls failed as required
```

每一条都打印**具名的判据行**（`[0] baseline MANIFEST.tsv is missing` 等），
不是裸的非零退出 —— `FileNotFoundError` 也非零，但它什么都没说（A.6 #8 的延续）。

---

## 6. 改动面

### 6.1 主题侧（9 处 / 5 文件）

| 文件 | 处 | 驱动力 |
|---|---|---|
| `functions.php` | 4 | `sf_contact_email` 默认值、其净化器兜底、Organization schema 兜底、**证书出站邮件署名** |
| `inc/config-pdf.php` | 2 | 配置器 PDF 页脚（samples / single sample 两条） |
| `inc/cert-download.php` | 1 | 证书链接过期时的 404 文案 |
| `templates/page-contact.html` | 1 | 联系页可见地址与其 mailto |
| `tools/make_coa_sample.php` | 1 | COA 生成器页脚（客户可见） |

**不变的 5 处**（已声明）：`functions.php:4925` 的收件人、`config-pdf.php` 的两条 `Cc:`、
以及解释它们的两条注释 —— 全都是 `sales@`。
`sinofresh-theme/docs/官网开发文档-全文.md:662` 保留旧表述：那是**上传 docx 的逐字落盘**，
是历史记录，不是活代码。

**⚠️ 第一遍扫描漏了 `tools/`**（文件清单只到 `functions.php/style.css/assets/inc/templates/parts/patterns`），
第二遍才补上 `make_coa_sample.php` ⇒ 扫描档的 8 处已就地更正为 **9 处**。

### 6.2 DB 侧（10 行 / 3 表）

| 表 | 行 | 说明 |
|---|---|---|
| `wp_options` | `sf_contact_email` | **真源** —— 顶栏、页脚联系行、**悬浮邮件按钮**、Organization schema 四处都读它 |
| `wp_posts` | 3 / 37 / 38 | Privacy Policy(2)、Cookie Policy(1)、Terms(1) |
| `wp_trp_original_strings` | 53 / 138 / 1364 | TranslatePress 提取的原串 |
| `wp_trp_dictionary_en_us_zh_cn` | 53 / 138 / 1364 | 同三行的字典行（`translated` 全空、`status` 0 ⇒ 无译文可破坏） |
| `wp_posts` 36 | — | **revision，按声明跳过**（不对外渲染；动它只污染修订史） |

### 6.3 ⛔ 这次改动**不能只在预检副本里发生**

`sf_contact_email` 是**全站共享的 DB 选项**，dev 站 live 与预检副本共用同一个库
⇒ 改 DB 的瞬间，**live dev 站也换成 `sales@` 了**（实测：无头请求 `CF 解码 = sales@`、
`JSON-LD email = sales@`）。这是本批的性质，不是事故；但它意味着
**这个改动没有"候选态"**，只有"改了"。回滚靠快照（§7），不靠 git。

---

## 7. 回滚

| 资产 | 位置 |
|---|---|
| 原始值快照（含三页完整 `post_content`） | 服务器 `/var/www/dev.zxpet.com/_offroot/b2d-h4e-db-originals.json`（18,832 B，docroot **之外**）＋ 本地 `_backup/b2d-h4e-db-originals.json` |
| 回滚命令 | `SF_H4E_MODE=revert wp eval-file .../b2d_h4e_dbpatch.php` |
| 主题回滚 | `git revert 24da600` |

⛔ **为什么快照必须是完整原文而不是一段 SQL**：回滚若靠"再替换回去"，
那就不是回滚 —— 三个法务页里 `info@` 只是页面文字的一小部分，
"把 `sales@` 换回 `info@`"会连带改掉任何本来就有 `sales@` 的地方。
`--apply` **拒绝在没有快照、或快照与当前库不一致时运行**，
所以磁盘上那份快照永远描述着"正在被改的那个状态"。

⛔ 用 PHP 而不是 `.sql`：`esc_sql()` 会把每个 `%` 令牌化成 `{sha256}`，
只有走 `$wpdb->query()` 的 SQL 才由 `remove_placeholder_escape()` 过滤器还原
⇒ **写进 .sql 文件的令牌会永久固化**，交给裸 mysqli 也永远不会还原。
快照落盘前已断言产物里**不含** `{64位hex}` 令牌。

---

## 8. 浏览器 E2E（`tools/b2d_h4e_e2e.py`）

```
E1  四处全站件 ＋ 联系页模板                    7 页 × 3–4 条 mailto，全 sales@
E2  联系页可见文本与 mailto                     topbar / footer / 悬浮按钮 三处
E3  三张法务页正文（DB 侧唯一可见处）            正文 1894–4166 字符，旧值消失、新值在场
E4  悬浮栈未受扰动                             3 按钮、同一列 left=1364、tops=[720,784,848]
E5  console errors                            none
------------------------------------------------------------
VERDICT: PASS — 17 ok, 0 FAIL
```

**为什么字节门之外还需要这条**：字节门比较的是**源站发出的字节**，
而"读者最终拿到一个能点的 mailto"这一步发生在**浏览器里**（CF 的 email-decode 脚本改写 href）。
E2E 先**等解码完成**（轮询到页面上一个 `a[href*="email-protection"]` 都不剩），
再从真实 DOM 读地址 —— 否则读到的是混淆串，等于在比另一个东西。

E3 的取样点也修过一次：第一版取 `document.body.innerText` 的**首个** `sales@`，
取到的是**页脚**（页脚也带这个地址），也就是说它证明的不是"法务页正文改了"。
改成读 `.entry-content`（法务页的正文容器，实测 1894–4166 字符）后才有说服力。

---

## 9. 证据索引

| 文件 | 内容 |
|---|---|
| `docs/batch2d-stepH4-scan.md` | Step 0 扫描 ＋ 停机报告（四项裁决的前提） |
| `docs/batchH4e-gates/main-gate.txt` / `.json` | 主门（解码式限定证明） |
| `docs/batchH4e-gates/matrix.txt` | 破坏矩阵 14/14 |
| `docs/batchH4e-gates/negctl.txt` | 具名负对照 5/5 |
| `docs/batchH4e-gates/aa-selftest.txt` | A/A 自检（零误报） |
| `docs/batchH4e-gates/unit-h3-recheck.txt` / `unit-h3-negctl-recheck.txt` | H3 单测复跑 54/0 ＋ 6/6 |
| `docs/batchH4e-gates/measurements.json` | E2E 逐页原始读数 |
| `docs/batchH4e-shots/` | 6 张实拍（顶栏 / 页脚＋悬浮栈 ×2 / 联系页 / Terms / ZH 页脚） |
| `_backup/b2d-h4e-db-originals.json` | DB 回滚快照 |
| `_backup/b2d-h4e-candidates/` · `-aa/` | 候选断面 ＋ A/A 第二份 |
| `tools/b2d_h4e_patch.py` · `_dbpatch.php` · `_confine.py` · `_e2e.py` · `_shots.py` | 本批工具链 |

⚠️ **`_backup/` 与 `.workbuddy/` 都在 `.gitignore` 里**（前几批同例）⇒ 上表里
`_backup/b2d-h4e-db-originals.json` 与两份候选断面**不进版本库**。
DB 回滚能力因此依赖**两个磁盘位置**：服务器 `_offroot/` ＋ 本地 `_backup/`；
两者其一丢失，DB 回滚就只能靠 `--apply` 时的"快照必须与当前库相符"这条断言来发现。
**H4 开工前先确认本地那份快照仍在**（`ls -l _backup/b2d-h4e-db-originals.json`，期望 18,832 B）。

---

## 10. 交 H4 的不变量

1. **上线不存在**：`git pull` 整体跳过；live 长期停 `2.10.55` ＋ 配置器是预期状态。
2. **本批的候选断面 `_backup/b2d-h4e-candidates/` 就是 H4 的基线**；
   预检副本（现＝`24da600` 树）**在 H4 用完之前禁拆**。
3. ⛔ **`sf_contact_email` 已是 `sales@`，且它是全站真源**：H4 的询盘收件人**直接用它**，
   不要再硬编码 `sales@zxpet.com`（这次硬编码三处正是这个前置改动存在的原因）。
   —— 该重构**不在本批范围**（会让 diff 超出声明），登记 H6。
4. ⛔ **回归门不能再无脑用 `sf_masked_cmp.py`**：凡改动涉及**被 CF 混淆的内容**，
   必须用解码式归一化（`tools/b2d_h4e_confine.py` 的 `norm()`），并跑 A/A 自检。
5. H6 待办由 **9 项增至 10 项**（见 §6.1 与 §10.3）。
