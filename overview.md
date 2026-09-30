# H16b 修复执行 — `[SF_FACTS_MINI]` 裸文本（方案 B，已上线，3/3 验收通过）

> 2026-09-30 ｜ 详报：`docs/h16b-fix-execution-report-2026-09-30.md`（排查见 `docs/h16-facts-mini-marker-report-2026-09-30.md`）

## 一句话

`functions.php` 的 marker 过滤器从「只认 `core/html`」放宽为「**`core/html` + freeform**」（替换判据不变：`trim` 后整行精确等于 marker），**生产已上线**：Soft Chews 参数带恢复、8 个剂型页全绿、Site Editor 再保存也不复发；**4 份 DB 副本一律未删**。

## 改动与部署

- 唯一文件 `sinofresh-theme/functions.php`：md5 `d1be8b90…`（330929B）→ **`4adaf274…`（331822B）**，本地/dev/生产**三方一致**；git `578a24d` → **`983111b`**（已 push，dev 已 ff）。**未 bump 版本**（不改资产）。
- 生产显式部署：备份 `/root/h16-rollback-prod-functions.php` → `php -l` → 原子 `mv` → `chown apache:apache/644`；opcache 自动生效无需 reload。

## 验收（生产实测）

| # | 标准 | 结果 |
|---|---|---|
| ① | `/products/soft-chews/` 参数带正常、无裸文本 | ✅ 事实带 1 段/4 项，裸文本 0，其余 13 个区块全在；可见文本含 MOQ/Lead time/Certifications/Packaging |
| ② | 8 个剂型页全查 | ✅ 8/8 页 `code=200 leak=0 band=1 items=4`，配方网格/Explore/FF/FAQ 全在 |
| ③ | Site Editor 再保存一次不复发 | ✅ 真浏览器点保存（REST POST 200）后 `freeform-marker 1→1`（降级被固化＝会复发的机理仍在）但前台仍 `leak=0 band=1`；随后 396 按快照**逐字节还原**（md5 回 `33ba53cc…`）、探针修订删除、编辑锁清除、**4 份副本零残留** |

## dev 验证（生产前）

- **影响面**：整块内容恰为 marker 的集合**只有** `page-soft-chews` 副本 1 个（+3 条 revision）；「含 marker 但整行非 marker」的集合**为空** ⇒ 精确匹配零误伤。
- **测试 A**（生产真实受损字节）：修复后 `leak=0 band=1 items=4`；同字节跑修复前逻辑 `leak=1 band=0` ⇒ 差异只来自过滤器。
- **零漂移**：真回退文件后 8 个模板输出 **8/8 逐字节相同**（md5 列表见报告）。
- **误伤对照 10/10**、**dev 全页端到端**（用生产字节建临时副本，含判别性守卫串）修复前 `leak=1/band=0` → 修复后 `leak=0/band=1`；测试后 dev 回到基线（9 行/11 关系）。

## 保留与遗留

- 🔒 **4 份 DB 副本未删**（352 header / 353 front-page / 357 page-products / 396 page-soft-chews），其中 353 与 396 含用户今天的真实编辑（+618 字 / 剂型卡片文案重写）⇒ **另立批次反向同步进主题文件**。
- 遗留：方案 C（marker 真短码化，对块状态彻底免疫，需动 H10 字节基线）；块降级的**触发点**未完全钉死（编辑器内部校验/恢复环节，非序列化器）；`tools/p2_preverify.py` 仍过时；站点仍 `noindex`（P6 待开）。

---


> 2026-09-30 ｜ 详报：`docs/h16-sf-facts-mini-marker-report-2026-09-30.md`

## 结论（三层）

1. **前台也坏了，不只后台**：生产 Soft Chews 页参数带（MOQ/Lead time/Certifications/Packaging）整条缺失，原位置吐裸文本 `[SF_FACTS_MINI soft-chews]`；其余区块全在。其余 7 个剂型页全部健康，dev 8 页全健康。
2. **根因**：今天 13:38 在 Site Editor 保存 `page-soft-chews` 模板 → 产生 DB 副本（ID 396）→ 副本里该块的 `<!-- wp:html -->` 定界符被剥掉 → 块从 `core/html` 降级 freeform → H10 过滤器（只认 `core/html`）失配。同型损伤 2/2（header 09-28 也是）。已用 parse_blocks + do_blocks 实渲 + Gutenberg 序列化器源码 + 真实 JS parse→serialize 往返（不剥）四重定证。
3. **编辑器里看到裸文本＝设计如此**：HTML 块永远显示源码，`render_block` 是服务端 PHP 过滤器，编辑器不跑。页面编辑器（Pages→Soft Chews）实际是空的（post_content len=0）。

## ⚠️ 修法上的关键约束

生产现有 4 个模板 DB 副本，其中 **front-page（+618 字可见文本，`[sf_home_about]` 已被实际文案替代）和 page-soft-chews（相关剂型卡片文案已重写）含用户今天的真实编辑** —— 「删 DB 副本恢复文件权威」会丢工作，不可单用。

## 推荐修法（未执行）

**方案 B：过滤器加固（~3 行）** —— `functions.php:958` 从「只认 core/html」放宽为「core/html ＋ freeform」，前台立即恢复、零内容丢失、防复发。另立批次把两份编辑反向同步进主题文件（还「Site Editor 禁存模板」铁律的欠账）。

---

# H15 执行结果 — Shape/Container/FAQ 保存失效已修复上线

## 做了什么

| # | 内容 | 落点 |
|---|---|---|
| 1 | 3 处 **sanitize 幂等守卫**（`sf_shapes` / `sf_containers` / `sf_global_faq`） | `inc/formula-admin.php` 875 / 932 / 987 行 |
| 2 | **保存副作用盖章**治理：组内 23 个选项加 `pre_update_option_*` 守卫，未提交的字段一个字都不写 | 同文件 ~1136 行 |
| 3 | Factory Information 页 7 个信任框改为按**生效值**回填（`sf_formula_trust_value()`） | 同文件 ~1384 行 |
| 4 | 删除生产上被盖空的 **7 个 `sf_trust_*` 选项** → 回到出厂默认 | 生产 DB |

- 唯一改动文件：`sinofresh-theme/inc/formula-admin.php`
  `d5e6d407…` (72931 B) → `1a603e81…` (77585 B)，本地/dev/生产三方 md5 一致
- 生产是真实目录，已**显式原子部署**（`scp` → `php -l` → md5 → `mv` → `chown apache:apache`）；opcache `validate_timestamps=On`，无需 reload

## 验收结果

| # | 标准 | 结果 |
|---|---|---|
| 1 | Shape Library 选图→保存→刷新→图还在 | ✅ 生产真浏览器：`0 → 53`，保存 302，刷新仍 `53`，缩略图在，8 行未丢 |
| 2 | Container Library 同样 | ✅ 同上：`0 → 53`，刷新仍 `53`，7 行未丢 |
| 3 | 21 个配方页显示 Factory & Trust 版块 | ✅ 生产 **21/21**，每页 `band=1` `rows=4`，合计 84；内容 = 4 个出厂值 |
| 4 | 保存任一 Settings 页后 7 个选项没被盖空 | ✅ 生产 **7/7** 设置页逐一保存，7 项**始终「不存在」**（不是「值没变」） |

辅助门（生产实测全绿）：幂等对照门 3/3 + 2 项负对照；23 选项幂等普查「需要守卫：无」；盖章门 7 页 × 9 断言 = 63 项 0 FAIL，且门自身**零残留**。

## 关键点（值钱的）

- **盖章修复落在 `pre_update_option_*`**：该钩子在 `sanitize_option()` 之后、在「值未变则短路」之前 ⇒ 返回旧值即**完全不落库**；且未提交字段**从未被 sanitize** ⇒ 不需要逐字段幂等（修复 1 与修复 2 正交）。管理员主动清空某框（字段确在 `$_POST` 且为 `''`）仍照常生效 ⇒「主动关掉」与「被误盖」被彻底区分。
- **门自身缺陷已修（v3）**：③ 原把「拥有字段任何变化」判 FAIL，但 options.php 会把页面渲染值**回填**写库（`sf_certifications` 原本不存在 → 保存后被创建，内容与代码默认逐字段相同）⇒ 降级为 INFO；同时把还原范围扩到回填创建项，做到零残留。
  > 教训：断言「字段没变」必须先分清「**原本不存在**」与「**原本是空串**」—— 这正是本次 bug 病根的同类混淆。
- **生产净变化**：`21 → 14` 个 `sf_*` 选项，消失的**恰好**是那 7 个 `sf_trust_*`；其余 14 项逐字节相同，无新增。

## 回滚

`/root/h15-rollback-prod-formula-admin.php`（主题，md5 `d5e6d407…`）、`/root/h15-prod-trust-options-backup.json`、`/root/h15-prod-sf-options-backup.json`。
⚠️ 选项回滚**必须走裸 SQL**：`update_option('')` 会被「空则 delete」钩子实际执行成 `delete_option`。

## 遗留

- **P6（打开收录）未执行**，站点仍 `noindex`
- `tools/p2_preverify.py` 已过时（指向已删的 `:8080` 临时 vhost）
- 生产主题是真实目录 ⇒ 以后改动都要**显式部署**，不能只 `git pull`

## 痕迹

服务器与本地 `/tmp` 探针全部删除；两枚临时管理员会话已 `destroy()`；mu-plugins 无临时件（dev 3 个正式件 / 生产 1 个）。
