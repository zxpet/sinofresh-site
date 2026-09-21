# Batch 2D-C — 配方详情页 FAQ（上线闭环档案）

**状态：已上线并闭环（2026-09-21 UTC）。**
源码提交 `89bdba8`（首版，带作用域 bug，已被下一提交修正）→
`b28d4cd`（作用域修正 + 双重防线）。线上 HEAD = `b28d4cd`。

## 一、本批做了什么

42 个配方详情页（21 en + 21 zh）在 "Formula & nutrition" 与相关产品网格之间
新增九问手风琴 FAQ 段（`section.sf-fdetail-faq` > `h2` > `div.sf-faq` > 9×
`<details class="sf-faq__item">`，首条 `open`），并在 head 内新增对应的
FAQPage JSON-LD（排在 BreadcrumbList 之前）。

- 数据源：`sinofresh_formula_faq_data()` 单一函数同时喂手风琴与
  FAQPage 生成器（页面与结构化数据不可能漂移）。
- 两条数据驱动答案：Certifications / Packaging formats 走
  `sinofresh_formula_spec_cell()`（与页面其余部分同一来源），值缺失时整句丢弃。
- `sf_formula_faq` meta 整段覆写位（Q:/A: 行格式，坏数据回退生成集 + error_log）。
- `[sf_formula_faq]` 短代码 + 模板 `wp:html` 块（占位符只在 core/html 生效）。
- style.css 零改动，版本保持 2.10.54（复用 `.sf-faq` 与 `.sf-fdetail` 手机内边距）。

## 二、Step 0 门的证据

- 工具：`tools/b2d_c_apply.py`（自撤销拼接）、`tools/b2d_c_synth.py`
  （从基线捕获独立造候选）、`tools/b2d_c_confine.py`（六门）。
- 合成候选六门 PASS（`_backup/b2d-c-baselines/gate-synth.txt`）：
  门 1 资产零变动；门 2 DIFF 恰 42（21 en + 21 zh）、33 页不变、A/A 0 差异；
  门 3 42/42 删块逐字节还原（首/尾换行 42/42 consumed 一致，SEAM_TALLY）；
  门 4 functions.php / 模板重建还原、style.css 同字节；
  门 5 42 页恰多一个 FAQPage、答案与页面逐字一致、33 页 deep-equal。
- 负对照 FAIL（91 条，`gate-negative-A0.txt`）；破坏矩阵 9/9 FAIL
  （`negative-matrix.txt`）。

## 三、事故与修复：FAQ 块嵌进了 intro()（已修正并加双防线）

第一刀把 `sinofresh_formula_faq_data()` / `sinofresh_formula_faq()` /
`add_shortcode()` 拼进了 `sinofresh_formula_intro()` **函数体内部**（锚点 =
「intro 尾 + 下一个 docblock」整段，插在其前）。本地全绿：`php -l` 干净、
拼接自撤销证明精确、合成器只建模字节不建模 PHP 作用域。**渲染才暴露**：
预检候选 42 × HTTP 500，恰好是调用 intro() 的 42 页（两次调用 →
`Cannot redeclare sinofresh_formula_faq_data()`），其余 33 页 200。

修复（`b28d4cd`）：块改落**两个顶层函数之间**。两道独立防线双向验证：

1. `tools/b2d_c_php_scope.php` — PHP tokenizer 走查全部声明的花括号深度，
   嵌套即 exit 1（修好版 5 个声明全 TOPLEVEL；坏版 line 847 depth 1）。
2. 门 4 新断言（字节级代理）：块必须紧跟列 0 的 `}` + 空行
   （修好版 gate_rc=0；坏版 gate_rc=1 + `!! the FAQ block is not at top level`）。

事故全记录见 `negative-matrix.txt` §C（坏提交字节留存
`_backup/b2d-c-baselines/php-nested/functions.php`）。

## 四、预检与真实数据门

- `b28d4cd` 装预检副本（sha256 与本地逐字节一致）→ `X-SF-Preflight: 1`
  抓 75 页，**75/75 HTTP 200**（首装 89bdba8 时同页 500）。
- 六门 PASS（`gate-preflight.txt`）：实测渲染与合成模型字节完全一致。
- 反向负对照 FAIL（`gate-negative-reversed.txt`）。
- 预检门日志取证：75 次请求全部被门拦截（`zz-sf-preflight.log` 90 行，
  拆除时已随之清除）。
- 真实渲染抽查：9 条 details、首条 open、`.sf-faq`、head 顺序
  FAQPage → BreadcrumbList。

## 五、Step 6 上线闭环（2026-09-21 11:35–11:50 UTC）

1. **pull**：`bb9cde3 → b28d4cd`（--ff-only，40 位 SHA 校验，theme 软链不变）。
2. **服务侧验证**：en/zh 详情页各 9 条 details、首条 open、h2 正确、
   FAQPage + BreadcrumbList 在 head、style.css `?ver=2.10.54`。
3. **live 75 页抓取**（`_backup/b2d-c-baselines/live/`，75×200）：
   - 预检候选 vs live：**75/75 identical**（A/A 自检 PASS 后比较，
     `sf_masked_cmp`）——线上服务的就是过门字节。
   - 批前基线 vs live：33 SAME / 42 DIFF，DIFF 集合**恰为 42 个配方页**
     （`cmp-base-live.json`）。
4. **浏览器 E2E**（`tools/b2d_c_evidence.py` live 模式，
   `_backup/b2d-c-baselines/e2e-live.json`）：**180 项 0 失败**——
   FAQ 段渲染、9 条 details 交互、FAQPage 在、页脚 details 不受影响
   （1440 open / 768+375 折叠＝线上既有行为，两侧一致）、0 JS 报错、
   全视口 stylesheet 2.10.54。截图 `docs/batchC-shots/`。
5. **拆预检零残留**：theme 目录 / mu-plugin / 日志全清，仅余常驻
   `zz-sf-dev-lockdown.php`。
6. **日志归因**（`logaudit-closure.txt`，窗口 06:40–11:50 UTC）：
   **AUDIT PASSED** —— 85 条靠 access log 归因清除，46 条立账（--allow，
   全部有据）：42 条 redeclare fatal ＝破坏候选 89bdba8 的负对照 500
   （本批自己修的文档化错误）；1 条 03:38 工作期 `/wp-settings.php`
   探测（sfdev+curl 实录）；3 条 11:41–11:45 第三方爬虫探测
   `/.htpasswd`（CF 边缘 IP，403 拒绝，非我方）。
7. **身份链**：691 tracked 文件本地↔HEAD↔服务器 **0 不一致**。
8. **仓库 md5**：**1344 文件 0 差异**（报告 `_backup/b2d-c-baselines/repo-md5.json`，
   `_backup` 未跟踪故无需 exclude）。

## 六、批 C 记录的教训

- ⛔ **锚点放错作用域，一切本地信号都绿**：`php -l`、自撤销证明、合成器
  都抓不到「块嵌进了函数体」。渲染（42×500）才暴露。永久防线 =
  `b2d_c_php_scope.php`（tokenizer 深度检查）+ 门 4 顶层断言。**任何
  向 functions.php 插入顶层代码的批次都必须跑这两道。**
- ⛔ zsh 不做 `$VAR` 词分割（`${(@f)$(...)}` / 数组传参），多值 CLI 参数
  必须用数组展开。
- 审计 1 秒偏差：error 行与 access 行时间戳差 1 秒时自动归因失配
  （.htpasswd 探测案），需人工核实后立账。
- 事故型负对照的价值：如果没有预检先炸 500，这个 bug 会直接上线
  （42 个详情页全站白屏级 fatal）。
