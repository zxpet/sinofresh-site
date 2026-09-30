# H16b 执行报告 — `[SF_FACTS_MINI]` 裸文本修复（方案 B）

- 日期：2026-09-30（北京时间 13:58–14:2x）
- 授权：用户选定**方案 B**（过滤器放宽为 `core/html + freeform`，`trim` 后整行精确等于 marker 才替换），并要求「先 dev 验证 → 显式部署到生产」，同时**保留 DB 副本里用户今天的真实编辑，不删副本**。
- 状态：**已上线生产，3 项验收全部通过，零残留。**

---

## 一、改动（唯一文件 `sinofresh-theme/functions.php`）

```php
add_filter('render_block', function ($block_content, $block) {
	$name = $block['blockName'] ?? null;
	if ($name !== 'core/html' && $name !== null && $name !== '') {
		return $block_content;
	}
	if (preg_match('/^\[SF_FACTS_MINI ([a-z0-9-]+)\]$/', trim((string) $block_content), $m)) {
		return sinofresh_form_facts_mini_html($m[1]);
	}
	return $block_content;
}, 10, 2);
```

- 原条件：`($block['blockName'] ?? '') !== 'core/html'` ⇒ 放行。
- 新条件：只放行「既不是 `core/html`、也不是 freeform（`blockName` 为 `null` 或 `''`）」的块。
- **替换判据未动**：仍是 `trim()` 后整行精确等于 marker。含 marker 但前后另有文字的块**不**被替换（见误伤对照）。
- 文件 md5：`d1be8b906ee96455ab45355ef15eefd2`（330929B）→ **`4adaf27497e04825b1257572e016631b`（331822B）**；本地/dev/生产**三方一致**。
- git：`578a24d` → **`983111b`**（已 push，dev `site-repo` 已 `--ff-only` 到 `983111b`）。
- **未 bump 主题版本**（沿用 H15 惯例：不改 CSS/JS 资产即不 bump，避免触发工具侧版本字面量同步）。

---

## 二、根因（H16 已定证，此处摘要）

Site Editor 保存模板 → 产生 DB 副本 → 副本里**根级** `core/html` 块的 `<!-- wp:html -->` 定界符被剥掉 → 块降级为 freeform（`blockName = NULL`）→ 原过滤器只认 `core/html` ⇒ 失配、原样输出裸文本 ⇒ 前台参数带整条缺失。

本次 dev 探针补上最后一环：**`render_block` 对 freeform 块确实会触发，`blockName` 为 `NULL`**（此前只是推断「失配」，现在确认「能看见但名不对」）：

| 输入形态 | `render_block` 触发 | `blockName` | 修复前替换 |
|---|---|---|---|
| 裸 marker（freeform） | 是 | `NULL` | 否 |
| marker 包在 `wp:html` 里 | 是 | `'core/html'` | 是 |
| freeform 含前后其它文本 | 是 | `NULL` | 否（整行非 marker） |

---

## 三、dev 验证（全部通过后才动生产）

### 1) 影响面定证（生产只读扫描）

`parse_blocks` 逐行普查「整块内容恰为 marker」的集合：

```
【A】整块内容恰为 marker（本次改动会替换的集合）
  wp_template  ID=396  page-soft-chews  block[3] name=NULL(freeform)
  （另有 3 条 revision 398/401/402 同型，不参与渲染）
【B】含 marker 但整块内容不等于 marker（不应被替换）    （无）
【C】模板层形态
  page-soft-chews  ID=396  core/html-marker=0  freeform-marker=1  (已降级 ⇒ 本次修复覆盖)
```

⇒ 改动半径**恰好 1 个已发布模板**，且【B】为空 ⇒ 精确匹配零误伤。

### 2) 测试 A — 用生产受损的真实字节（md5 `33ba53cce8346f9d3de78c608f6b169a`，27994B）渲染

```
【1】修复后（core/html + freeform）  leak=0  band=1  items=4
【2】对照（只认 core/html，同字节）  leak=1  band=0  items=0
=> ALL PASS（差异只来自过滤器本身）
```

### 3) 漂移证明 — 8 个模板文件逐字节比对（两进程，同序渲染）

把 dev 主题文件**真回退**到修复前（`git checkout --`，md5 `d1be8b90`）再渲染，与修复后对比：

```
page-soft-chews.html   md5 43670f07dfc2e2d6c23996227bb8b595   （前后相同）
page-tablets.html      md5 acb588b0e2a5b4f78c20b317171dac5a   （相同）
page-liquids.html      md5 6537fc52dc62bd0276489aba3e9a5dc8   （相同）
page-pastes.html       md5 e9e19c7a8ae881831713d5fa22dcda71   （相同）
page-powders.html      md5 7f6ad4d6b6e55245287b85d508e8a70a   （相同）
page-dental-chews.html md5 5c5a6ac31e815f591ab0f6d2304ce7f3   （相同）
page-drops.html        md5 ec9d393a5da7999015f3cbb1c55e770e   （相同）
page-fish-oil.html     md5 f80f19fcc2cd819b67c39f2ed1c837a1   （相同）
=> 零漂移 PASS（8/8 输出逐字节一致）
```

> 说明：第一次尝试的「同进程摘过滤器」对照**作废**——`remove_all_filters('render_block', 10)` 顺带摘掉了主题其它 `render_block` 过滤器，长度差来自它们，与本次改动无关；改为真回退文件后结论干净。

### 4) 误伤对照 10/10 PASS

```
整块=marker              → 替换=是 ✔      前有文字        → 替换=否 ✔
整块=marker 带空白        → 替换=是 ✔      后有文字        → 替换=否 ✔
core/html 路径            → 替换=是 ✔      大小写不符      → 替换=否 ✔
                                          slug 非法字符    → 替换=否 ✔
                                          core/html 内有其它文字 → 否 ✔
                                          paragraph 块     → 替换=否 ✔
```

### 5) dev 全页端到端（用生产字节建**临时**副本）

在 dev 建一份与生产**逐字节一致**的 `wp_template` 副本（`page-soft-chews`，md5 落库校验通过），再走真 HTTP：

```
修复前： 裸marker=1  事实带=0   （仍含用户编辑串）
修复后： 裸marker=0  事实带=1   可见文本含 MOQ / Lead time / Certifications / Packaging
```

判别性守卫：用只存在于**生产副本**、主题文件里没有的串 `Pet supplement tablets in round and heart shapes` 证明 dev 页**确实在渲染这个 DB 副本**（命中 1 次）。

测试后删除副本，dev 回到基线：模板行 `9 行`、`wp_theme` 关系 `11 条` **与测试前逐项一致**；该编辑串从 dev 页消失。

---

## 四、生产部署（显式）

```
部署前 : /var/www/zxpet-v2/.../themes/sinofresh-theme/functions.php  apache:apache 644  330929B
         md5 d1be8b906ee96455ab45355ef15eefd2
备份   : cp -p → /root/h16-rollback-prod-functions.php   （md5 已核 d1be8b90…）
opcache : enable=On, validate_timestamps=On, revalidate_freq=2  ⇒ 无需 reload php-fpm
上传   : install -o apache -g apache -m 644 …/functions.php.new
语法   : php -l → No syntax errors detected
原子替换: mv .new → functions.php
部署后 : apache:apache 644  331822B  md5 4adaf27497e04825b1257572e016631b ✔
```

---

## 五、生产验收

### ① `/products/soft-chews/` 参数带正常、无裸文本 — PASS

逐区块清点（`code=200`）：topbar/header、面包屑、Hero H1、Hero 按钮、**事实带（1 段 / 4 项）、裸文本 0**、Standard Formulas、配方网格、Explore more dosage forms、How We Work、FAQ（JSON-LD）、Related Dosage Forms、FluentForm、footer —— **全部在位**。

可见文本（hero → Standard Formulas 之间）：

> Build Custom Formula **MOQ from 500–1,000 units　Lead time Typically 7–15 working days after packaging is ready　Certifications FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRCGS　Packaging Aluminum Stand-up Pouch, …** Standard Formulas …

原裸文本 `[SF_FACTS_MINI soft-chews]` 已消失。

### ② 8 个剂型页全查 — PASS（8/8）

| 页面 | code | leak | band | items | 配方网格 | Explore | FF | FAQ |
|---|---|---|---|---|---|---|---|---|
| soft-chews | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| tablets | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| liquids | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| pastes | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| powders | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| dental-chews | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| drops | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |
| fish-oil | 200 | 0 | 1 | 4 | 2 | 2 | 25 | 1 |

其余页面健康度（`leak=0`，均 200）：`/`、`/products/`、`/formulas/`、`/about/`、`/quality/`、`/factory-tour/`、`/contact/`、`/privacy-policy/`、`/blog/`、`/faq/`。PHP 错误日志无本次相关条目。

### ③ 在 Site Editor 里再保存一次，确认不再复发 — PASS

用真浏览器（Playwright + 临时管理员会话）打开「外观 → 编辑器 → 模板 `page-soft-chews`」：

1. 载入后 `保存` 按钮 `aria-disabled="true"`（无改动，按钮禁用）。
2. 插入一个临时段落（`H16B-TEMP-SAVE-PROBE`）制造改动 ⇒ 按钮转为可用。
3. 点 `保存` ⇒ 真 REST 写入 **POST 200**，保存后按钮回到干净态。
4. **DB 侧**：ID 396 `27994 → 28068` 字节，md5 `33ba53cc… → 29573166…`，**`freeform-marker` 1 → 1**（降级形态被保存固化——这正是「会复发」的机理；修复点因此在渲染层，而非编辑层）。
5. **前台**：`code=200`，**裸 marker = 0，事实带 = 1 / 4 项**，插入的段落正常渲染。
6. 收尾：把 396 按快照**逐字节还原**（裸 SQL）⇒ `len=27994 md5=33ba53cce8346f9d3de78c608f6b169a`、`post_modified_gmt` 回 `05:55:16`；删除本次产生的修订（ID 403）；清除编辑锁；**4 份副本与快照逐字节一致（零残留 PASS）**。

**推论**：编辑器里仍会看到 marker 裸文本（HTML 块永远显示源码，`render_block` 是服务端 PHP 过滤器，编辑器不跑）——这是设计如此。而无论保存把块保持成 `core/html` 还是降级成 freeform，**渲染层两种形态都已覆盖**，所以「再保存即复发」的路径被切断。

---

## 六、DB 副本：按要求保留

生产现有 4 份已发布模板副本，**本次一律未删**，逐字节与保存前快照一致：

| ID | 名称 | 修改时间(gmt) | 备注 |
|---|---|---|---|
| 352 | header | 2026-09-28 09:01:43 | 根级 `core/html` 早在 09-28 被剥（sentinel，无可见影响） |
| 353 | front-page | 2026-09-30 03:31:03 | **含用户今天编辑**（较文件 +618 字，`[sf_home_about]` 已被实际文案替代） |
| 357 | page-products | 2026-09-28 09:10:34 | 可见文本与文件一致 |
| 396 | page-soft-chews | 2026-09-30 05:55:16 | **含用户今天编辑**（相关剂型卡片文案已重写）；marker 块已降级 |

⇒ 这批编辑**将来另立批次**反向同步进主题文件；在那之前副本继续提供权威内容，渲染已由本次修复保证正确。

---

## 七、回滚

| 用途 | 路径 |
|---|---|
| 主题文件回滚（修复前原件） | `/root/h16-rollback-prod-functions.php`（md5 `d1be8b906ee96455ab45355ef15eefd2`，330929B） |
| 4 份副本逐字节快照（含 base64 原文） | `/root/h16b-tpl-BEFORE.json`（＝ `/root/h16b-tpl-FINAL.json`，两者逐字节相同） |
| 本次保存后的中间态（诊断用，含探针段落） | `/root/h16b-tpl-AFTER.json` |

回滚命令（文件）：
```
install -o apache -g apache -m 644 /root/h16-rollback-prod-functions.php \
  /var/www/zxpet-v2/wp-content/themes/sinofresh-theme/functions.php
```
⚠️ 副本回滚必须走**裸 SQL**（`UPDATE wp_posts SET post_content=…`）：`wp_update_post()` 按 `$_POST` 语义 `unslash`、且「空数组即删除」等钩子会改字节。快照已按裸 SQL 可回灌的形态存档。

---

## 八、遗留与建议

1. **编辑反向同步（另立批次）**：把 `front-page`、`page-soft-chews` 两份副本里的真实编辑搬回主题文件，然后删副本、恢复「文件即权威」。搬完才有条件重新对齐「Site Editor 禁存模板」的铁律。
2. **结构性根治候选（方案 C）**：把 marker 变成**真短码**（`add_shortcode`）。块模板管线在 `do_blocks` **之前**先跑 `do_shortcode`（`wp-includes/block-template.php:259-262` 实读确认），真短码对块的 `core/html`/freeform 状态**完全免疫**；代价是动 H10 字节基线，需独立批次评估。
3. **块降级的触发点未完全钉死**：已钉死的是「DB 副本里是 freeform」「再保存会保持 freeform」「JS `parse→serialize` 纯往返不剥定界符」（H16 实测），因此降级发生在编辑器内部的某个校验/恢复环节，而非序列化器本身。渲染层现已在两种形态下都正确，故不影响可用性；若要追到底，需在编辑器内抓 block validation 日志。
4. `tools/p2_preverify.py` 仍过时（指向已删的 `:8080` 临时 vhost）——与本批无关，待清理。
5. 站点仍 `noindex`（P6 未执行），待用户核对 `sales@zxpet.com` 收件箱后开启。

---

## 九、痕迹清理

- 临时管理员会话：本次创建 3 枚，已全部 `destroy()`（会话数 10 → **7**，与操作前一致）。
- 服务器 `/tmp/h16b-*`、`/tmp/h16-*` 已清；本地 `/tmp/h16b-*`、`/tmp/h16-*` 已清。
- mu-plugins：dev 3 个正式件（lockdown / preflight×2 日志 / wps-consent-bridge），生产 1 个（wps-consent-bridge）——无临时件。
- 主题目录无 `.new` 残留。
- dev 测试副本已删，dev 模板行回到基线（9 行 / 11 关系）。

## 十、经验（已写入项目记忆）

- **`render_block` 会对 freeform 块触发**，`blockName` 为 `NULL`（不是不触发）——排查「过滤器失配」前先确认这条，否则会把「名不对」误判成「没跑到」。
- **WP 后台页面的 JS 侧计数不可靠**：`wp.blocks.parse()` 在不同后台页面的可用性不同（在 `/wp-admin/` 上直接返回空），且 JS `.length` 按 **UTF-16 码元**计数（同一内容 27966 vs 27994 字节）⇒ 一律以 PHP `parse_blocks` + 字节长度/md5 为准。
- **Gutenberg 的 `保存` 按钮状态看 `aria-disabled`**，不是 DOM `.disabled`（后者恒为 false）；无改动时保存禁用，要验证保存必须先制造一次改动。
- **`remove_all_filters('render_block', 10)` 会连带摘掉主题其它过滤器**，用它做「修复前对照」会引入无关差异——对照组应改为**真回退文件**。
