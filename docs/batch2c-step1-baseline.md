# Batch 2C Step 1 — single-sf_formula.html 详情页 · 交付基线

日期：2026-09-20 ｜ 提交链：`4428085 → 04beba5 → 53898db → … → style 2.10.43`
部署：dev.zxpet.com（`git pull` fast-forward，主题为 site-repo 符号链接）

## 交付范围

| 项 | 内容 |
|---|---|
| 模板 | `templates/single-sf_formula.html`：hero（4 级面包屑 + 剂型标签 + H1 + 一行 meta + 双 CTA）→ Specification（3 字段卡）→ 长文案（空记录整段消失）→ 同剂型相关公式 → CTA band |
| 占位符 | 新增 `{{FORM_SLUG}}`(esc_attr)、`{{FORMULA_USE}}`(原文输出，禁 esc_html)、`{{FORMULA_META}}`（PHP 组装 `<form> · MOQ <row> · Lead time <row>`，缺行自动缩短） |
| 数据读取 | `sinofresh_formula_spec_cell()` 从 `page-<form>.html` 规格表按 `data-label` 取 MOQ/Lead time（单一真源，memoised） |
| 短代码 | `[sf_formula_detail]`（3 字段卡，空字段跳过，非 sf_formula 单页返回 ''）；`[sf_formula_body]`（post_content 为空则整段 band 不输出） |
| D2 | `sf_formula_grid` 新增 `exclude` 参数；当前公式在 PHP 内强制排除（block template 先 do_shortcode 后 do_blocks，模板传不进自己的 ID） |
| D4 | Product JSON-LD（priority 22）：name=标题、image=剂型图（`sinofresh_formula_card_image`，绝非"页面第一张 img"）、additionalProperty=三字段；**无 offers/price**（OEM 参考配方，非标价 SKU） |
| D1 + 缺口 | formulas.js **1.0.0 → 1.1.0**：slug 优先取 `data-form`；无 `#configurator` 时不滚动；enqueue 拆分——configurator 仍限剂型页，formulas.js 追加 `is_singular('sf_formula')` |
| D3 | `.sf-breadcrumb--d4`：手机端折叠 Home + Products（含分隔符），剂型 crumb 前加 `←`，视觉形态与 3 级折叠一致 |
| CSS | **style 2.10.43**（37b 段：`.sf-formula-hero*`、`.sf-fdetail*`、`.sf-fdetail-body*`、`.sf-breadcrumb--d4`、手机 20px 内边距） |

## 核验结果

| # | 项目 | 结果 |
|---|---|---|
| 1 | 21 条详情页 HTTP 200、无 PHP 报错、无占位符残留 | ✅（`tools/b2c_s1_verify.py`，**1150 断言 0 失败**） |
| 2 | `/zh/formulas/<slug>/` 21 页 200、hero 正常 | ✅ |
| 3 | 4 级面包屑：可见 DOM 与 BreadcrumbList JSON-LD 逐项一致（positions 1-4，末项无 item URL） | ✅ |
| 4 | 三字段卡与 post meta 逐字一致（21 页 × 3 字段） | ✅ |
| 5 | K1：`class="sf-formula__cta"` + `data-formula`（实体解码后为真实标题）+ `data-form`（剂型 slug） | ✅ |
| 6 | Product JSON-LD 与 DB 真值 deep-equal（name/description/image/additionalProperty），唯一 Product、无 offers、无 Article | ✅ |
| 7 | 缺字段降级（临时清空 sf_formula_analysis → 恢复）：卡片 3→2、additionalProperty 同步缩短、无空 `<p>`、恢复后逐字节一致 | ✅ `tools/b2c_s1_degrade.py` |
| 8 | 真实鼠标点击 K1：`writeText` 收到公式名、toast 出现、**scrollY 不变**（无 #configurator 不滚动） | ✅ `tools/b2c_s1_browser.py` |
| 9 | 几何：桌面 3 列同行（卡宽 387px）、手机 1 列、hero 色值 #2E6B54（25b 内页配方）、手机内边距 20px（27s） | ✅ |
| 10 | 手机面包屑折叠：Home/Products 及分隔符 display:none，剂型 crumb `::before` = `←` | ✅ |
| 11 | 全站回归 `tools/b2s0_regression.py`：22 页 200、无卡片泄漏、剂型页 K1 toast 链路不受影响 | ✅ |
| 12 | md5 工作区 ↔ 云端 4 文件一致；`grep "/ -->"` 零残留；云端 `www-error.log` 无新增 | ✅ |
| 13 | 截图：liquid-skin-coat 桌面 3 张 + 手机 4 张（`screenshots/batch2c-step1/`） | ✅ |

## 过程中抓到并修掉的 4 个坑（都已沉淀到项目记忆）

1. **block template 的 HTML 注释会原样输出到页面源码**——长篇实现注释（含 `{{FORMULA_USE}}` 字面量、"exclude={{...}}" 推导）泄漏进了 21 个公开页。模板注释只留短结构标注，推导放 functions.php。
2. **hero 误用 single.html 的 `backgroundColor:primary`**（#1B4D3E = 导航色）。内页 hero 的标准配方是 `.sf-hero-inner`（#2E6B54，25b/27s），与来源剂型页同色。
3. **受限布局只居中块级子元素**——hero 里 `inline-block` 的剂型标签流进全宽匿名块，渲染在 x=0；改 `display:block`（不能加 fit-content，auto 边距会把它居中）。
4. **CSS Grid auto-fit 的 computed track 列表含 0px 空轨道**——按字符串 split 数列数会得 4，须按非零轨道数或"卡片同行"判断。

另：改 CSS 后若版本号未 bump，Chromium 会按同 URL 命中缓存——本次即时复测就踩中，随即 2.10.42→2.10.43。

## 待决策 / 观察项

- **`sinofresh-theme/_backup/` 已进 Git**：`.gitignore` 的 `/_backup/` 是根目录锚定，匹配不到主题内路径，93 个批次备份（348 文件、22.86MB）已入库。已加 `**/_backup/` 止血（新备份不再入库）；历史清理需 `git rm -r --cached sinofresh-theme/_backup` + 一次 push，**会使云端工作区删除这批文件**（本地保留），是否执行待拍板。
- **1025–1199px 视口下所有内页 hero 文字贴边**：27s 的 20px 内边距只到 1024px，1240px 规则只覆盖 ≤1240 的非 hero 段。全站既有现象（非本批引入），一行修复是把 27s 侧边距断点放宽到 1199px，涉及全站，待拍板。
- Product JSON-LD 无 `offers`/`review`，Google 富结果不予展示（Search Console 可能有提示）——设计如此，非缺陷。
- 相关公式 band 在同类只有 1 条时会留 3 个空轨道（如 Liquids）；与剂型页网格行为一致，未做特殊处理。

## 下一步

- **Step 2**：`archive-sf_formula.html`（/formulas/ 档案页）
- **Step 3**：TranslatePress 重收录（option B：`original_strings_sync('zh_CN', $strings)`，预期 status=0 / translated 空，/zh/formulas/ 暂时英文可接受）
