# Batch 2D Step 4b — 决定一（560px 卡改左对齐）：扫描、执行、撞到的分叉

> 状态：**未上线，等确认**。本地已提交并推送 `effa435`（版本 2.10.49），云端工作树仍是 `94d64fd` / **2.10.48**，
> 预检副本已拆净。**线上从未服务过 2.10.49 的字节。**（证据见 §5）

---

## 1. 我要做的事（用户批准项）

```
.sf-fdetail__grid--solo { 加 margin-inline: 0 }
版本 2.10.48 → 2.10.49（两处同步）
```

## 2. 改了什么

| 文件 | 改动 | diff |
|---|---|---|
| `sinofresh-theme/style.css` | `Version: 2.10.48` → `2.10.49`；`.sf-fdetail__grid--solo` 加 `margin-inline: 0;`；上方注释补写原因 | 2 hunk / +12 −3 |
| `sinofresh-theme/functions.php` | `wp_enqueue_style(... '2.10.48')` → `'2.10.49'` | 1 hunk / +1 −1 |

不变量：`:has(` 仍 **163**；新增行 `!important` 0、`url(` 0。
备份 `sinofresh-theme/_backup/b2d-step4b-20260921-070259/`（改前两文件 + `MD5.txt`），已断言与 `git show HEAD~1` 逐字节一致。

## 3. 四道门（`tools/b2d_s4b_confine.py`）——全 PASS

```
[1] 资源清单   style.css 2.10.48 -> 2.10.49 on 75 page(s)；其余资源 0 个变动；资产集合变化 0 页
[2] 掩码比对   ?ver= 折叠后 75/75 identical
[3] style.css  重建（撤销声明改动）= 改前逐字节  YES   c546caa331f54c78
[4] functions  重建（撤销声明改动）= 改前逐字节  YES  1a8a31342e81be88
```

**负对照**（`--new` 指向与 base 相同的字节）：FAIL，6 条问题，RC=1。
负对照顺带暴露了门自身的一处**真空 PASS**：声明文本缺失时"什么都没撤"，`undone == base` 却照打 YES——
已修（新增"每条声明都套用上了吗"这一维，未套用即判 NO 且不可比）。修后正跑仍 PASS、负对照仍 FAIL。

## 4. ⛔ 撞到的分叉：批准的声明在浏览器里是**空操作**

预检副本（`X-SF-Preflight: 1`，已断言拿到的是 `sinofresh-theme-preflight/style.css?ver=2.10.49`）实测：

```
gridLeft = 440   marginInlineStart = 402px   maxWidth = 560px   ← 仍然居中，纹丝不动
```

从 CSSOM 里把命中该元素的所有 margin 规则捞出来，找到真正的对手（WP core）：

```css
.is-layout-constrained > :where(:not(.alignleft):not(.alignright):not(.alignfull)) {
  max-width: var(--wp--style--global--content-size);
  margin-left: auto !important;      /* ← core 用了 !important */
  margin-right: auto !important;
}
```

`.sf-fdetail__grid--solo { margin-inline: 0 }` 的权重与它相同（0,1,0），但对方带 `!important`，**作者普通声明必败**。
所以批准的那行 CSS 在真实浏览器里**一个字都没生效**——这正是"验证 CSS 规则是不是空操作"那类坑。

**强制生效后落点又不对。** 注入 `margin-inline: 0 !important` 实测：

```
gridLeft = 38   width = 560   h2Left = 120
```

因为 `.sf-fdetail` 是 `has-background` 的 section，core 给它 38px 内边距
（`:where(.wp-block-group.has-background){ padding: 1.25em 2.375em }`），约束布局子元素是在这个**内容盒**里做 auto 居中的。
于是：

- **x = 38** = section 内容盒左缘
- **x = 120** = 1200px 度量左缘 ← 页面上 **每一个** h1/h2 都在这里

实测该详情页所有标题：`A Closer Look…@120 | Specification@120 | Formula & nutrition@120 | More Drops Formulas@120 | Ready to Launch…@120 | h1@120`。
直接照字面加 `!important`，560px 卡会落在 **x=38，比 Specification 标题外凸 82px**。

## 5. 两个候选（都已实测，等拍板）

| | 实现 | 实测落点 | 相对标题 | 代价 |
|---|---|---|---|---|
| **A｜字面执行** | `--solo { max-width:560px; margin-inline:0 !important }` | x=38 / w=560 | **外凸 82px** | 与页面所有标题不同一条左缘 |
| **B｜对齐页面左缘**（推荐） | 上限从 grid 移到内容：`--solo { grid-template-columns: minmax(0,560px) }`，`max-width` 不再写 | **x=120 / w=560** | **0px，与标题同一条线** | 动了第 4 批批准过的"上限写在 `--solo` 的 `max-width` 上"这条 |

补充两条实测约束，供选型时参考：

* B 若改用"给 `.sf-fdetail__card` 设 `max-width:560px`"，会得到 **610px** 而不是 560px——
  因为该卡片是 `box-sizing: content-box` + 左右各 24px 内边距 + 1px 边框（560+48+2=610）。要落在 560 得再补 `box-sizing: border-box`。
  所以 B 用 `grid-template-columns` 收轨道更干净：grid 保持 core 给的 1200 度量（x=120），单轨 560，卡片自然贴轨道左缘。
* A 无论如何都到不了 x=120：grid 的包含块是 section 的 38px 内边距盒，任何"自身上限 < 1200 + 关掉 auto 边距"都只能落到 38。

**版本/提交处置**（取决于选哪个）：
- 选 A：追加一个 commit 把 `margin-inline: 0` 改成 `margin-inline: 0 !important`；建议同时把版本推到 **2.10.50**（否则 2.10.49 会对应两份不同字节，违反"版本＝缓存唯一依据"）。
- 选 B：追加一个 commit 改 `--solo` 的写法，版本同样推到 2.10.50。
- 两种都**不要** amend + force-push：`effa435` 已推送，规则是"优先新提交"。

## 6. 现场状态（已收干净）

```
预检日志 83 行（curl 抓取 + 浏览器渲染都确实走了副本）
拆净后 mu-plugins/ 只剩 zz-sf-dev-lockdown.php；theme dir gone / mu-plugin gone / log gone
错误日志 /var/log/httpd/dev.zxpet.com-ssl-error.log  1494 B  mtime 2026-09-20 19:31:11  md5 3feaf736…  ← 零新增
云端 site-repo = 94d64fd，style.css = 2.10.48，git status 干净   ← 线上没有服务过 2.10.49
```

## 7. 顺带产出（可复用）

* `tools/b2d_s4b_confine.py`——**一行 CSS 改动**的门形态：资源清单（版本迁移记成一条 `旧->新`，不是"删除+新增"两条）+ 掩码比对 + **撤销声明改动的重建**（对新增/改字都适用）。含负对照自证。
* `tools/b2d_s4b_evidence.py`——渲染取证。**踩到的坑写进文件头注释了**：
  `agent-browser` 的 `set headers` 与 `set credentials` **互斥**（互相重建 context，后设的把先设的冲掉），
  且 `set headers` 按 origin 作用域，必须先落到目标站再设；`open` 会丢掉头，`reload` 才保留。
  唯一可用顺序：`close --all → set credentials → open → set headers{预检头+Basic 凭据} → reload → set viewport`。
  第一版就是顺序错了，拿**没用上的** 2.10.48 去"证明"改动生效——脚本里那句"断言拿到的是哪个主题目录"就是拦这个的。
* 新不变量（已可入 RULES）：**WP core 对 constrained 布局的直接子元素用 `margin-left/right: auto !important`**。
  凡靠 `max-width` + auto 边距定位的块，要改水平落点必须 `!important`；且落点是**容器内容盒左缘**，
  `has-background` 的 section 那圈 38px 内边距会把"左对齐"落到 38 而不是 1200 度量的 120。

---

### 需要你回的

1. 选 **A**（字面 x=38）还是 **B**（对齐页面左缘 x=120，推荐）？
2. `data-group="packaging"` 这类逐页差异，第 5 批要不要沿用（见 `docs/batch2d-step5-scan.md` §3 D3）？——这是第 5 批的事，可以和上面一起回。

---

## 附：`docs/b2d-step4b-shots/` 里两张图的身份

`01-live-solo-1440.png` / `01-live-solo-375.png` 是**取证脚本第一版（顺序错）跑出来的**，
所以它们拍的是**线上 2.10.48 的居中卡**，不是候选渲染 —— 文件名特意从 `01-solo-left-*` 改成 `01-live-solo-*`，
免得日后被当成"改后已左对齐"的证据。1440 那张正好是问题现场（卡在 x=440）。
`evidence.txt` / `evidence.json` 保留了那一次的全部断言输出，其中
`FAIL stylesheet really is the pre-flight copy` 就是拦下它的那条 —— **留着比删掉有用**。
