# 批次 2C 第二步 · 内部链接入口清单（/formulas/ 孤岛页破局）

> 状态：**✅ 已执行**（2026-09-20）。§A 由用户在 Site Editor 完成，§B 由代码完成并上云。
> 排期：必须**排在第三步 TranslatePress 重收录之前**——新增的英文串要靠那一步收集（已就绪）。
> 验证全档：`docs/batch2c-step2-decisions.md` §九。
> 背景：`/formulas/` 是 21 条公式记录的总入口，但导航与 footer 都没有入口，详情页面包屑也不经过它 →
> 目前是**孤岛页**（实测详情页全页 `href="/formulas/"` 计数 0）。补入口是本批最大的 SEO 价值点。

---

## A. 导航 Products 下拉（DB 改动，Site Editor 可改）

**改动位置**：`wp_navigation` 文章 ID **16**（由 `parts/header.html:31` 以 `{"ref":16}` 引用）。
结构 = `wp:navigation-submenu{label:"Products"}` 包着 8 个 `wp:navigation-link`。

**要加的一项**

| 项 | 值 |
|---|---|
| 文案 | `All Formulas` |
| 链接 | `/formulas/` |
| 位置 | **Dental Chews 之后、`/wp:navigation-submenu` 闭合之前**（末位） |

放末位的理由：不打断「8 个剂型＝剂型页 menu_order 顺序」这条既有序列；且与剂型页公式区**末尾**的
"Browse All Formulas →" 形成同构（列表读完 → 去总览）。

**序列化形态**（若走代码/DB 直接改，用这一行；注意自闭合 ` /-->`）：

```
<!-- wp:navigation-link {"label":"All Formulas","url":"/formulas/","kind":"custom"} /-->
```

**Site Editor 走法**：外观 → 编辑器 → 导航 → 展开 `Products` → 添加链接 →
链接地址填 `/formulas/`、文字填 `All Formulas`；拖到列表最后一位 → 保存。

---

## B. 8 个剂型页入口（**必须改文件，Edit Site 无效**）

**为什么不能交 Edit Site**（两条独立原因，任一成立即失败）：

1. **模板归属守卫**：`functions.php:65`（`pre_get_block_template`）与 `:102`（`get_block_templates`）
   两个过滤器规定——只要 `templates/<slug>.html` 存在，**磁盘文件永远胜出，DB 副本被丢弃**。
   在 Site Editor 里保存 `page-soft-chews` 只会写一条 DB `wp_template`，前台仍读文件。
2. **页面内容根本不渲染**：`page-*.html` 里**没有 `wp:post-content`** → 在页面编辑器里改内容也不会出现。

实测证据：DB `wp_template` / `wp_template_part` 文章数均 = **0**；`resolve_block_template('page-soft-chews')`
→ `source=theme`、`has_theme_file=true`；两个 guard 钩子均已注册。
**症状**：保存成功、页面毫无变化、没有任何报错（静默无效）。

### 逐页清单（8 个文件完全同构）

| 文件 | 公式短代码所在行 | 插入位置 |
|---|---|---|
| `sinofresh-theme/templates/page-soft-chews.html` | 38 | 第 39 行 `<!-- /wp:html -->` 与第 40 行 `</section>` 之间 |
| `page-tablets.html` | 38 | 同上 |
| `page-powders.html` | 38 | 同上 |
| `page-pastes.html` | 38 | 同上 |
| `page-drops.html` | 38 | 同上 |
| `page-liquids.html` | 38 | 同上 |
| `page-fish-oil.html` | 38 | 同上 |
| `page-dental-chews.html` | 38 | 同上 |

**插入内容**（三行，词句 8 页完全相同）：

```html
<!-- wp:paragraph {"align":"center","style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->
<p class="has-text-align-center" style="margin-top:var(--wp--preset--spacing--40)"><a class="sf-explore__btn" href="/formulas/">Browse All Formulas →</a></p>
<!-- /wp:paragraph -->
```

**为什么复用 `.sf-explore__btn` 而不新建类**：该样式已存在（`assets/css/configurator.css:899`），
剂型页本来就会入队 configurator.css；形态是 2px 描边按钮，**同一页的配置器里已有一个同款
"Browse All Products →"**，两者并列读作同一族。⇒ 本批**零新增 CSS**。
（`.sf-explore__btn` 仅在剂型页可用，故档案页不吃它，档案页用自己 CTA band 的样式。）

---

## C. 交给 TranslatePress 的新串（第三步收集）

当前 `/zh/` 站几乎零翻译（`/zh/products/soft-chews/` 全页中文片段只有 1 个：语言切换器的"简体中文"），
所以新增英文串不增加本批工作量，只需**保证它们存在于第三步收集之前**：

| 串 | 出处 |
|---|---|
| `All Formulas` | 导航 post 16 |
| `Browse All Formulas →` | 8 个剂型页 × 1 |
| `Formulas` | 新档案页 H1（`wp:query-title`）与面包屑 |
| `1 formula` / `21 formulas` | `[sf_archive_count noun="formula"]` 的两个 msgid |
| `All` + 8 个剂型标签 | `[sf_formula_filters]` 的 9 个按钮（标签走 `sinofresh_formula_label()`，与导航同名） |
| `Showing N of 21 formulas` | 筛选状态播报（`role="status"`） |

---

## D. 应用后的核验清单（2026-09-20 实测结果）

1. 导航：每个页面（含 `/zh/`）下拉里出现 `All Formulas` → 点击落到 `/formulas/`，状态 200
   → ✅ 实测 9 项、末位、`/formulas/`；**`/zh/` 页上 href 被 TP 自动改写为 `/zh/formulas/`**（正确）
2. 8 个剂型页：公式区末尾出现描边按钮，链接 `/formulas/`；按钮在 375px 档 `display:block;width:100%`
   → ✅ 8/8；桌面 106/106 断言、浏览器 113/113（375px 实测宽 = 段落宽 299px、高 ≥44px）
3. 剂型页的**卡片数与顺序逐字节不变**（本批只加一个段落，不应触碰 grid 输出）
   → ✅ 删除新段落后归一化，候选**逐字节等于基线**（34/34 SAME）
4. 8 个剂型页 + 21 个详情页的 JSON-LD 与改动前一致（新增段落不进 JSON-LD）
   → ✅ 每页 5 个 blob **逐字节相同**；新锚点不在任何 blob 内
5. `grep -rn "/ -->" sinofresh-theme/templates/` 零残留
   → ✅ 0（全主题唯一 1 处是旧测试脚本里的断言字面量）
6. 工作区 ↔ 云端 md5 一致；`/zh/formulas/` 仍 200
   → ✅ 146 文件 md5 全等；`/zh/formulas/` = 200 / 139432 B

## E. 回滚

8 个文件的改动 = 各删 3 行；导航 = 在 Site Editor 里删掉那一项（或把 post 16 的 `post_content` 还原）。
建议与档案页模板同批但**单独一个 commit**，以便单独 revert。
