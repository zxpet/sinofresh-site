# Shape Library 图片存不上 — 只读诊断报告（2026-09-26）

> 一句话根因：**两个独立断点同时存在**——① JS 选图后写不进隐藏字段（选择器少两个方括号）；② PHP 保存时按错的数据结构读取（表单是「平行数组」，回调按「行数组」读）⇒ 每一行都被判空丢弃，再被 H13 的删 option 钩子抹成「未设置」。任一断点单独存在都足以让保存归零。

## 1. 点 Choose 后，隐藏字段有没有被写入？

**没有。** 浏览器实测（Playwright + 临时管理员 cookie，Shape Library 页 `/wp-admin/admin.php?page=sf-shapes`）：

```
wp.media loaded: true        media modal open: true
media items in library: 35   select button present: true
hidden inputs before pick: ["0","0","0","0","0","0","0","0"]
preview after pick:        ["<img src=\".../fda-registration-sinofresh-150x...\">", ...]
hidden inputs after pick:  ["0","0","0","0","0","0","0","0"]   ← 选了图，字段还是 0
```

预览图**更新了**（说明 `frame.on('select')` 回调确实执行了），但隐藏字段纹丝不动。

**原因＝选择器不匹配**（`assets/admin/sf-site-settings.js:117`）：

```js
var attInput = row.querySelector('input[name$="[attachment_id]"]');   // ← 匹配不到
```

渲染出来的输入框名字是 `sf_shapes[attachment_id][]`（`inc/formula-admin.php:1168`），**以 `[]` 结尾**；而 `$=` 比较的字符串是 `[attachment_id]`（没有尾部的 `[]`）⇒ 永远选不中，`attInput` 为 null，赋值语句整段跳过。预览分支用的是 `.sf-containers__preview` 类选择器，所以正常更新——**这正是这个 bug 看着像「选图成功了」的原因**。

浏览器内实测的选择器矩阵（同一行 DOM）：

| 选择器 | 结果 |
|---|---|
| `input[name$="[attachment_id]"]`（现役） | **false** ❌ |
| `input[name$="[attachment_id][]"]` | true ✅ |
| `input[name*="[attachment_id]"]` | true ✅ |

写入事件链：`click → wp.media 单图 frame → frame.on('select') → 写 attInput.value + 更新预览`。事件链本身没问题，断在最后这个选择器上。

## 2. 点保存后，PHP 收到什么？

后台表单 `POST options.php` → `register_setting('sf_site_settings', 'sf_shapes'|'sf_containers', …)` 的 `sanitize_callback`（`inc/formula-admin.php:877-892` 与 `899-914`）。

字段名**对得上**（同一批名字），断的不是名字而是**结构**：

| 侧 | 结构 |
|---|---|
| 表单标记（`inc/formula-admin.php:1125/1131/1132`、`1168/1174/1175`） | **平行数组**：`sf_shapes[attachment_id][]`、`sf_shapes[label][]`、`sf_shapes[slug][]` ⇒ `$_POST['sf_shapes'] = ['attachment_id'=>[…], 'label'=>[…], 'slug'=>[…]]` |
| sanitize 回调（`899-914`） | 按**行数组**读：`foreach ((array)$v as $row) { $row['slug'] }` |

于是遍历到的是三个「字段数组」而不是行：`$row = [573]` → `$row['slug']` 不存在 → 空 → `continue`。**每一行都被判空丢弃**。

## 3. H13 的 sanitize 是不是根因？

**结构读错是根因；H13 的改动是把症状从「存了空表」变成「什么都没存」，让它更难发现。**

- 判空条件 `if ($slug === '') continue;` 本身没错——错在它读的 `$slug` 永远为空（上一节）。
- H13 新增的写侧钩子（`inc/formula-admin.php:923-934`）：保存后若存活行数 = 0 就 `delete_option()`。所以一次「正常保存」的结局是 **选项被删掉**，页面上又变回 8 行默认形状（图片 ID 全是 0）——用户看到的就是「没存上」。
- 时间线：这个结构错配 **H7g 引入时就存在**（注释写着「rows with a slug survive」，但表单从来不会送出这个结构）；H13 只改了「空表怎么落库」，没碰读取结构。H13 诊断时看到的 DB `array(0)` 正是这个 bug 的历史产物。

**只读实测证据**（跑真实的注册闭包，然后 `apply_filters('sanitize_option_*')`，零写入）：

```
=== registrar inc/formula-admin.php:869
  sf_shapes      平行数组载荷（表单真实形态）  -> rows survived: 0    out: []
  sf_containers  平行数组载荷                  -> rows survived: 0    out: []
  sf_global_faq  平行 q/a 载荷                 -> rows survived: 1    out: [{"q":"Q?","a":"A!"}]
=== registrar functions.php:5891
  sf_certifications 行主序载荷                 -> rows survived: 1    out: [{"name":"FDA","url":"https://e.com","active":true}]
=== 反证：shapes 用行主序载荷                 -> rows survived: 1
```

（`active` 被转成了 `true`，证明回调确实执行，不是「过滤器没挂上」的假绿。）

## 4. Container Library 与 Certifications 对比

| 表 | 表单结构 | sanitize 读法 | JS 选择器 | 结论 |
|---|---|---|---|---|
| **Shape Library** | 平行数组 | 行数组 ❌ | `[name$="[attachment_id]"]` ❌ | **两层皆断** |
| **Container Library** | 平行数组 | 行数组 ❌ | 同一个 handler ❌ | **两层皆断（同病）** |
| Certifications | 行主序 `[0][name]` | 行主序 ✅ | 不涉及图片 | **无恙**（实测 1 行存活） |
| Global FAQ | 平行 q/a | 显式读 `$v['q']`/`$v['a']` ✅ | n/a | **无恙**（实测 1 行存活） |

补充发现（必须同批修）：**Add 行重置也用同一个坏选择器**（`sf-site-settings.js:90`），克隆新行时不会把 `attachment_id` 归零。今天所有 ID 都是 0 所以看不出来；**修好 picker 之后它会变成真 bug**——新行会继承上一行的图片 ID。

## 5. 修复方案（等确认再动）

**改动面：2 个文件、4 处，不动前台渲染与默认值。**

1. **JS（1 文件 2 处）** `assets/admin/sf-site-settings.js`
   - 第 90 行（Add 行重置）与第 117 行（picker 写入）：`input[name$="[attachment_id]"]` → `input[name$="[attachment_id][]"]`
   - enqueue 版本 `1.0.2 → 1.0.3`（改动 JS 必须 bump cache-buster）
2. **PHP（1 文件 2 处）** `inc/formula-admin.php` 的两个 sanitize 回调（sf_containers `877-892`、sf_shapes `899-914`）改为按平行数组读——照 Global FAQ 现成写法：
   ```php
   $ids    = isset($v['attachment_id']) && is_array($v['attachment_id']) ? $v['attachment_id'] : array();
   $labels = isset($v['label'])         && is_array($v['label'])         ? $v['label']         : array();
   $slugs  = isset($v['slug'])          && is_array($v['slug'])          ? $v['slug']          : array();
   for ($i = 0, $n = max(count($ids), count($labels), count($slugs)); $i < $n; $i++) {
       $slug = sanitize_title(isset($slugs[$i]) ? $slugs[$i] : '');
       if ($slug === '') { continue; }              // H13 契约不变：无 slug 的行丢弃
       $out[] = array(
           'slug'          => $slug,
           'label'         => sanitize_text_field(isset($labels[$i]) ? $labels[$i] : ''),
           'attachment_id' => absint(isset($ids[$i]) ? $ids[$i] : 0),
       );
   }
   ```
   （不建议反过来把标记改成行主序：那要给 shapes/containers 补一套行号重排 JS，改动面更大。）
3. **主题版本** `2.10.87 → 2.10.88`。

**门（补上让这个 bug 溜过去的盲区）**：h13 门只测了「空保存删 option」，而且是用 `update_option()` 直接写库——**绕过了表单与 sanitize**，所以结构错配永远测不出来。建议新增 h14 门三项：
- PHP：跑真实注册闭包 + 喂表单真实载荷（平行数组），断言「有 slug 的行存活」「attachment_id 被保留」；
- JS 源码断言：`sf-site-settings.js` 必须出现 `$="[attachment_id][]"`、不得出现 `$="[attachment_id]"`；
- `--live`（可选）：浏览器 pick 后隐藏字段 ≠ 0（本次两个脚本可直接改造复用）。

**验收方式**（实施后）：Shape 页给一行选图 → 保存 → 重载页面该行仍显示图片；`wp option get sf_shapes` 能取到该行；Container 页同验；Certifications/Global FAQ 回归（应零变化）。

## 附：本次诊断痕迹

- 只读，零写入；四个选项状态前后一致（`sf_shapes`/`sf_containers`/`sf_certifications` ABSENT、`sf_global_faq` `[]`），前台 200。
- 临时管理员会话已销毁；服务器无残留文件。
- 复用脚本：`tools/_h14_sanitize_probe5.php`（sanitize 矩阵）、`tools/_h14_picker_check.js`、`tools/_h14_selector_check.js`。
