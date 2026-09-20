# 批次 2D 第 4 批 — 配方详情页两处调整

**产品 commit `9f4ee30`（已上线）** ← 基线 `9132f83`；`style.css` `2.10.47 → 2.10.48`（两处同步）。
影响面 **42 页**（en 21 + zh 21 配方详情页）；其余 **33 页逐字节未动**（16 剂型 + 17 其它）。
扫描方案 `docs/batch2d-step4-scan.md`｜门报告 `docs/b2d-step4-gates.txt`｜取证 `docs/b2d-step4-shots/`。

---

## 1. 改了什么

### A. `[sf_formula_detail]` 只渲染 STANDARD SPECS

`sinofresh_formula_detail()`（`functions.php:1401`）的 `$fields` 从 3 项减为 1 项：

```php
$fields = array(
    array('label' => 'Standard Specs',      'key' => 'sf_formula_specs'),
);
```

删掉的 **Ingredients** / **Guaranteed Analysis** 两张卡，其数据在同一页的 **⑤ `Formula & nutrition`** 段
（2D-S3 加入）里已按同一份 meta 渲染过一次 —— 也就是说**这两张卡与 ⑤ 段是同一份数据的两次渲染**，
删的只是重复的那一份。

**三个 meta 一个都没删**；Product JSON-LD 的 `additionalProperty` 由 meta 直接构造（不读渲染 HTML）
⇒ 机器可读的那份一字未减。

**单卡宽度**：循环与 grid 结构保持多卡形态，只增加一个计数；恰好一张卡时给 grid 加修饰类：

```php
$grid_class = 'sf-fdetail__grid' . ($count === 1 ? ' sf-fdetail__grid--solo' : '');
return '<div class="' . $grid_class . '">' . $cards . '</div>';
```

CSS 只针对修饰类下宽度上限（`style.css` 37b-iii 段内，紧跟 `.sf-fdetail__grid` 之后）：

```css
.sf-fdetail__grid--solo { max-width: 560px; }
```

> 之所以不直接改 `.sf-fdetail__grid`：将来 grid 恢复多卡时，`auto-fit minmax(280px,1fr)` 的行为不受影响。

### B. 图集 h2 改文案：`Inside Our {剂型} Production` → `A Closer Look at {配方名}`

`sinofresh_formula_gallery()`（`functions.php:1265`，全库唯一一处）：

```php
$title = is_singular('sf_formula') ? trim((string) get_the_title()) : '';
if ($title === '') {
    $title = $label;   // 剂型兜底，h2 永不消失
}
... sprintf('A Closer Look at %s', $title)
```

- `get_the_title()` 与 hero `h1` 的 `{{TITLE}}`（`sinofresh_template_placeholders()` `functions.php:2721`）
  **同源**，两者不可能各说各话；`esc_html()` 也对齐（`&` 一律出 `&#038;`）。
- shortcode 保持通用：非单个 `sf_formula` 语境或标题为空 ⇒ 退回剂型 label。
- **旧文案确实指错了名词**：实测旧 h2 是 `Inside Our Drops Production`，而该页 h1 是 `Ear Care Drops`
  —— `Drops` 是剂型（taxonomy slug 的 `ucwords` 人化），不是配方名。本批把它改对了。

## 2. 六个门 / 核验（全 PASS）

| 门 | 仪器 | 结果 |
|---|---|---|
| [1] ver inventory | `b2d_s4_confine.py` | `style.css 2.10.47→2.10.48` 75 页；**ADDED / REMOVED 皆空**（`formula-gallery.js` 前后都在同样 42 页）；无其它令牌变动 |
| [2] 限定证明（**改为重建式**） | 同上 | 42 页：band 区（`<!-- B2D-S3: gallery -->` → `<!-- Block 4: related formulas -->`）**等于基线区套用两处声明改动后的字节**；前后区段逐字节相同；33 页 identical |
| [3] 脚本标签 | 同上 | `formula-gallery.js` 仍在**恰好 42** 详情页 |
| [4] 跨版本数据（**改造**） | 同上 | **42/42**：新页 ⑤ 段的药丸/行 == **旧基线页面自己的两张卡的值**；且 Product JSON-LD 仍带这三项 |
| 身份链 | `b2d_s3_identity.py --sha256` | 工作区 ↔ 实服务主题 ↔ 预检副本，**691 文件全 0 不一致** |
| 快验 | `b2d_s3_quickcheck.py` | **12/12**（缩略图 / 375px / 键盘） |
| 渲染取证 | `b2d_s4_evidence.py` | **20/20**；`--solo` 实测 **560px**（1440）、335px（375，容器宽）、375 无横向溢出 |
| 仓库级 md5 | 见 §5 | 工作区 ↔ 云端 1196 跟踪文件逐字节一致 |

**门 2 为什么改成"重建"**：本批是**改 + 删**，不是纯新增，所以不再能像第 3 批那样把新增单元与旧单元并列记账。
现在的做法是把基线区**重建**成"基线区 + 两处声明改动"的期望字节，再要求它与新页逐字节相等：

- 改动 1：h2 文本。**期望值从基线页自己的 h1 推出**（`A Closer Look at ` + h1 内文），
  所以门不是"接受新页打印了什么"，而是"推出新页必须打印什么" —— 顺带证明 h2 与 h1 同源。
  基线 h2 里那个 label 也被断言过：必须等于该 band 自己 `data-gallery` 的剂型 slug 人化结果。
- 改动 2：grid 只剩一张卡 + 加 `--solo`。**替换文本由基线卡片的原始字节拼出**，
  所以"留下的那张卡"是基线的字节，而非新页的字节。

**门 4 为什么这样是"非循环"的**：拿**旧基线页面**的两张卡去比**新页面的 ⑤ 段**。
若反过来（新页卡 vs 新页段）两边同源、证明不了任何事；现在是跨版本，等于说
"数据没变，只是第二份渲染没了"。

**负对照**：`--new` 指向 base 自己 ⇒ **42 条失败、33 页 identical、exit 1**
（失败点全落在 `+367…+374`，即 h2 起始处），门可被证伪、且不会误报非目标页。

## 3. 上线方式（一项比第 3 批更强的做法）

第 4 批把**候选先跑门、再上线**：`git fetch` 只取对象不动工作树（线上仍服务 2.10.47），
`git archive <sha>` 建预检副本，候选页**经 `X-SF-Preflight: 1` 抓取** ⇒ 门通过后
才 `git pull --ff-only`。所以**线上从头到尾没有服务过未经门的字节**。

- 抓取自证：候选 75/75 = 200，`themes/sinofresh-theme-preflight/style.css?ver=2.10.48`，
  同期 live 仍是 `themes/sinofresh-theme/style.css?ver=2.10.47`。
- 上线后复核：`sf_masked_cmp.py new live` ⇒ **75/75 identical**
  ⇒ 门认证的就是随后上线的那份字节（`--aa` 自检先跑，无头 / 带头各一次，均 PASS）。
- A/A 自检：`--aa /about/` 与 `--aa <详情页> --header 'X-SF-Preflight: 1'` 都 PASS
  （掩码集仍是 `sf_masked_cmp.py` 那一套，含 `sinofresh-theme-preflight → sinofresh-theme`）。

## 4. 拆除预检（成对取证）

- **拆前**：不带头 → `sinofresh-theme/style.css?ver=2.10.48`；带头 → **`-preflight/`**（开关确实在生效）；
  带头渲染的标记里已能看到两处改动（`A Closer Look at Ear Care Drops` + `--solo`）。
- **拆后**：`no preflight theme / mu-plugin / log`（`mu-plugins/` 只剩常驻 `zz-sf-dev-lockdown.php`）；
  **带头发回到实服务主题**；匿名 **401** / 凭据 **200**；详情页 `sf-fdetail__card` **1** 张；
  剂型页 `sf-gallery` **0**。
- 预检日志存档 `docs/b2d-step4-shots/preflight.log.txt`（80 行，与拆除时的线上行数一致）。
- ✅ **PHP 错误日志零新增**：`/var/log/httpd/dev.zxpet.com-ssl-error.log`
  **1494 B / mtime `2026-09-20 19:31:11`**，与本批基线逐字节一致（覆盖 fetch→装副本→抓候选→六门→pull→E2E→拆除全程）。

## 5. 同步与校验

- 产品 commit `9f4ee30`（`functions.php` + `style.css`，2 文件 +48/−14）→ push → 云端 `pull --ff-only`
  → **三方同 SHA**；`site-repo` 仍 `root:root`，主题 691 文件重新 `apache:apache`
  （本批 pull **触及主题文件**，所以 chown 是必需的，与第 3 批不同）。
- 云端落盘复验：`style.css` `Version: 2.10.48`、`functions.php` `'2.10.48'`；`git status` 干净。
- **仓库级 md5**：工作区 ↔ 云端逐文件比对，见 §7；排序只在本地做，中文名逐条证明参与比对。

## 6. 无回归的证据（不变量）

- PHP 语法：`php -l functions.php` → `No syntax errors detected`。
- CSS：`:has(` **163**（style.css）+ **7**（configurator.css）= **170 不变**；本次新增规则里
  `!important` **0**、`url(` **0**。
- 未动：8 个 `templates/page-*.html`、入队逻辑、`formula-gallery.js`、任何 meta、⑤⑥⑦⑧ 段。

## 7. 待确认 / 遗留

- `b2d_s4_evidence.py` 里 375px 段**先重新加载再设视口**，并在同一次 eval 里断言 `readyState` + `clientWidth`
  —— 沿用第 3 批的教训（沿用上一段页面状态会读到空 DOM，报出与 CSS 无关的"无溢出"）。
- 本批顺手修的两处工具问题（都不是产品问题）：`b2d_s3_fetch.py` 增加 `--header`（并把它记进 `MANIFEST.tsv`
  —— 一份"预检"抓取若其实是 live 抓取，过同一套门却什么也证明不了）；`b2d_s3_quickcheck.py` 增加 `--out`
  （首次运行把两张截图写进了**第 3 批**的证据目录并覆盖了已入库的 `05-quickcheck-thumb2-1440.png`，
  已 `git checkout --` 还原，截图现落在 `docs/b2d-step4-shots/`）。
- 观察项（非本批范围）：`/products/soft-chews/` 的探测在拆除脚本里出现过一次空输出，
  已即时复验（200 / 177547 B / `sf-gallery` 0）并写入 `teardown.txt`；
  一次空白不能区分"带已删"与"页面为空"，所以没有当成结论。
- 仍未做：详情页 ③ 详细介绍 `post_content` 仍是 0 字节（结构已搭好、恒不输出）；
  ≤1239px 内页 hero 贴边；实拍图 34 张。
