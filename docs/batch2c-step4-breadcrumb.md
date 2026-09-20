# 批次 2C 第四步 · 面包屑前缀修复 —— 全档

> 状态：**已完成并上云**（commit `80d2696` 修复 / `ae4d2a1` 工具与截图）。
> 对象：`sinofresh-theme/functions.php` → `sinofresh_template_placeholders()` 的 `{{ARCHIVE_TITLE}}` 分支。
> 目标：`/zh/formulas/` 可见面包屑由 `归档： Formulas` 收敛为 `Formulas`，且英文站不回退、结构化数据同步收敛。

---

## 0. 一句话结论

本轮**最值得记录的不是修复本身，而是没有将错就错**：已批准的「一行正则」方案实测无效，
通过加诊断点打出真值 → 找到真根因（TranslatePress 标记包裹）→ 改为**源头抑制**，这条链路完整。
下文把「批准方案为什么失效」放在修法之前，因为**失效原因本身就是本轮最重要的产出**。

---

## 1. 批准方案：把正则末尾的 ASCII `:` 放宽为 `[:：]`

### 1.1 方案的依据

只读复看阶段（前一轮）测得：

- `/zh/formulas/` 可见面包屑 `归档： Formulas`（全角 `：`，U+FF1A），同页 H1 却是干净的 `Formulas`；
- 该串**不在 10 张 `wp_trp_*` 任何一张表**里，且字典/原串表 **id 1..1333 连续无断号**（⇒ 从未插入、也从未删过）；
- `functions.php` 的 `{{ARCHIVE_TITLE}}` 分支用一条 `^` 锚定正则事后剥离前缀，而该正则**末尾冒号是 ASCII `:`**。

据此推断：`[^:：]*` 不允许跨越全角冒号，加上末尾只认 ASCII `:` ⇒ 整条不匹配 ⇒ 前缀没剥掉。

### 1.2 批准方案本身

```diff
- ...\s*[^:：]*:\s*/iu
+ ...\s*[^:：]*[:：]\s*/iu
```

### 1.3 本地 PHP 验证：**全绿**（这就是坑所在）

用 Local 的 PHP 8.2 跑「输入 → 输出」表，7/7 PASS：

| 输入 | 修正后输出 | 期望 | 结果 |
|---|---|---|---|
| `归档： Formulas` | `Formulas` | `Formulas` | ✅ |
| `Archives: Formulas` | `Formulas` | `Formulas` | ✅ 不回退 |
| `Formulas` | `Formulas` | `Formulas` | ✅ 幂等 |
| `Category: News` | `News` | `News` | ✅ |
| `分类： 新闻` | `新闻` | `新闻` | ✅ |
| `归档： 2026 年 9 月` | `2026 年 9 月` | `2026 年 9 月` | ✅ |
| `Author: Sam` | `Sam` | `Sam` | ✅ |

**结论看起来完美。但把它装上预检装置后，`/zh/formulas/` 的面包屑毫无变化。**

### 1.4 为什么本地表验不出来

本地表喂的是**纯字符串**（`归档： Formulas`）。而真实渲染里，那个字符串**根本不是这个形状** —— 见 §2。
**正则逻辑正确，但它匹配的对象错了。** 只验正则、不验渲染，就必然漏掉这一层。

---

## 2. 真根因：TranslatePress 把 gettext 结果包进了自己的标记

### 2.1 诊断点打出的真值

在 `{{ARCHIVE_TITLE}}` 解析处加临时诊断点（mu-plugin，见 §6 的日志坑），打印
`get_the_archive_title()` 在 `/zh/` 上的**原始返回值**：

```
'#!trpst#trp-gettext data-trpgettextoriginal=0#!trpen#归档：#!trpst#/trp-gettext#!trpen# Formulas'
```

### 2.2 机制

- 前缀 `归档： ` 走的是 **gettext 路由**（`Archives: %s` 被 zh_CN 译成 `归档： %s`）；
- TranslatePress 在**非默认语言**下，会把 gettext 的结果**包进自己的标记对**：
  `#!trpst#trp-gettext … #!trpen#` … `#!trpst#/trp-gettext#!trpen#`；
- 于是 `归档： ` 位于**标记之后**，**不在偏移 0**。

### 2.3 为什么 `[:：]` 注定无效

`^` 锚定要求匹配从字符串开头开始，而开头是 `#!trpst#trp-gettext …`。
**无论把末尾冒号写成 ASCII、全角、还是同时接受两者，`^` 都不可能匹配到。**
全角 `：` 只是**叠加的第二个坑**，不是决定性原因 —— 这正是只读复看阶段判断偏差的地方。

### 2.4 旁证：H1 为什么一直是对的

H1 走 `wp:query-title` 块且 `showPrefix:false`。core 的实现是**用 filter 抑制前缀**，
拿到的就是**没有前缀**的标题 —— 全角/半角天然一致。
**同一个标题、同一个页面，一条路对一条路错：差异就在「事后剥离」vs「源头抑制」。**

---

## 3. 实际修法：源头抑制（`80d2696`，单文件 +13/−5）

```diff
 	} elseif (is_archive()) {
-		$archive_title = wp_strip_all_tags(get_the_archive_title());
-		/* … */
-		$archive_title = trim(preg_replace('/^(?:Category|Tag|Author|Year|Month|Day|Week|Post Format|Classification|Classification|Archives|分类|标签|作者|年|月|日|归档)\s*[^:：]*:\s*/iu', '', $archive_title));
+		add_filter('get_the_archive_title_prefix', '__return_empty_string', 1);
+		$archive_title = trim(wp_strip_all_tags(get_the_archive_title()));
+		remove_filter('get_the_archive_title_prefix', '__return_empty_string', 1);
 	}
```

- **整条 locale 正则删除**（连带清掉其中重复的 `Classification|Classification`）⇒ 不再有全角/半角、语言相关的脆弱逻辑；
- 用 `get_the_archive_title_prefix` filter **向 core 要「已经不带前缀」的标题** —— 即
  `wp:query-title` 块 `showPrefix:false` 用的**同一招**（这就是 H1 一直干净的原因）；
- `wp_strip_all_tags` 与 `'Archive'` 兜底保持不变；
- `add_filter` / `remove_filter` 成对紧贴，作用域只覆盖这一次调用。

---

## 4. 验证结果

### 4.1 预检（请求头门 `X-SF-Preflight: 1` + 独立主题目录 `sinofresh-theme-preflight`）

| 路径 | 可见面包屑 | BreadcrumbList `name[]` | 判定 |
|---|---|---|---|
| `/zh/formulas/` | `Formulas`（原 `归档： Formulas`） | `['Home','Formulas']` | ✅ 双项转正 |
| `/formulas/` | `Formulas` | `['Home','Formulas']` | ✅ 英文站不回退 |
| `/zh/blog/` | `Blog` | — | ✅ 不受影响 |
| 8 剂型页 + 21 详情页 | — | — | ✅ 掩码回归 **29/29 SAME** |

- 掩码回归中唯一命中的掩码是 **`sinofresh-theme-preflight` → `sinofresh-theme`**（预检副本的资源 URL 后缀），
  对线上基线零影响（新增掩码写明「live captures 永不命中」）。
- A/A 自检先于一切比对（§6 记录）。
- `php -l` 干净。

### 4.2 云端 `pull` 后线上终检（真实回源，`cf-cache-status: DYNAMIC`）

```
path                 st   cache       bytes  current crumb   h1         BreadcrumbList names
/zh/formulas/        200  DYNAMIC    139401  Formulas        Formulas   ['Home', 'Formulas']
/formulas/           200  DYNAMIC    131106  Formulas        Formulas   ['Home', 'Formulas']
```

- 线上 29 页回归 **29/29 PASS**（首轮报 1 页 FAIL，经查是**瞬时空响应**，重抓后 SAME）；
- `error.log` 无 PHP 错误；预检装置（主题副本 + mu-plugin + 日志）**已删净**，
  删净后**复读线上基线**证明未被改动；云端 `/tmp` 清净；工作区↔云端逐文件 md5 全等。

### 4.3 对照截图（`sinofresh-theme/screenshots/batch2c-step4-breadcrumb/`）

| 文件 | 内容 |
|---|---|
| `01-before-zh-desktop-formulas.png` / `02-after-…` | zh 桌面：`Home / 归档： Formulas` → `Home / Formulas` |
| `03-before-en-desktop-formulas.png` / `04-after-…` | en 桌面：不回退 |
| `05-before-zh-mobile375.png` / `06-after-…` | zh 375px：不回退 |

---

## 5. 回滚

| 项 | 值 |
|---|---|
| 修复 commit | **`80d2696`**（`sinofresh-theme/functions.php`，+13/−5，**单文件**） |
| 工具/截图 commit | `ae4d2a1`（校验脚本、截图、`sf_masked_cmp.py` 的 `--bust` 与预检掩码） |
| 前一状态 | `821973b`（第三步 TP 重收录） |

```bash
# 单独回滚修复（不动工具与截图）
git revert --no-edit 80d2696
git push origin main
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/site-repo && git pull --ff-only && chown -R apache:apache sinofresh-theme'
```

- 备份校验：`cmp -s` / md5（工作区 ↔ 云端全等）。
- **回滚后预期**：`/zh/formulas/` 面包屑与 BreadcrumbList 第 2 项**同时**退回 `归档： Formulas`
  （单一真源，两处一起动）；`/formulas/` 不受影响。
- 本步**不涉及数据库**：无表结构、无行写入，回滚只需 revert + pull。

---

## 6. 教训

1. **本地 PHP 的正则「输入→输出」表验不出标记包裹。**
   它只能证明**正则逻辑**对；一旦真实输入被框架改写（这里是 TP 的 `#!trpst#…#!trpen#` 标记），
   表的结论就与线上无关。**要验渲染，就必须验渲染。**
2. **「本地全绿 + 预检无变化」= 立刻加诊断点打真值，不要继续调正则。**
   本轮若顺着「冒号不对」的思路继续试，会反复空转；一个 `get_the_archive_title()` 的真值直接定案。
3. **同一数据的两条渲染路，一条对一条错 ⇒ 差异即诊断。**
   H1 干净、面包屑脏，说明问题不在「怎么翻译」，而在「怎么剥离」。**照抄对的那条路的机制**（源头抑制）。
4. **凡「先取本地化串、再事后正则剥离」的思路，在 TP 站上先怀疑标记包裹。**
5. **单一真源要双面验**：`{{ARCHIVE_TITLE}}` 同时喂可见面包屑与 BreadcrumbList JSON-LD，
   只验可见面的那次「绿」是假绿；两面都读，才算收敛。
6. **预检装置的两个操作细节**（本轮踩到）：
   - 临时诊断 mu-plugin 的日志**别写 `/tmp`** —— `open_basedir` 拦截、apache 写不进、**静默无日志**，白跑一轮；
     写到 `mu-plugins/` 自己旁边，用完连日志一起删。
   - 带门请求必须**排在任何不带门请求之前**（CDN 按 URL 缓存 HTML 达 86400s，门只在 PHP 层）；
     本轮所有抓取都带唯一 `?sfcap=` 强制回源。

---

## 附：相关文档

- 只读复看阶段的结论与纠偏：`.workbuddy/memory/2026-09-20.md`（含被本轮推翻的中间结论，按追加式保留）
- 深度规则：`.workbuddy/memory/RULES-sinofresh.md` §4（本步真根因）/ §5（invalid data 静默丢弃）/ §6（TP 表自然增长）
- 第三步全档：`docs/batch2c-step3-tp-preflight.md`
- 统一回滚剧本：`docs/batch2c-step2-rollback.md`
