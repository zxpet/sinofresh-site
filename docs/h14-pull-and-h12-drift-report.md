# H14 pull 落地报告 + h12 --live 7 红根因取证

日期：2026-09-28
范围：H14 修复 pull 到 dev、三道 live 门、两个顺带发现
结论一句话：**H14 修复本身完全成功（h14 --live 26/0、h13 --live 12/0）；h12 --live 的 7 条红与本次 pull 无关**，它照出的是三件事——① 三条 DB 模板覆盖悄悄遮蔽了文件模板 ② 首页因此丢了两个 BESTSELLER 标签 ③ 页面 14/15 有用户自己的编辑，基线陈旧。

---

## 一、pull 结果

| 项 | 值 |
|---|---|
| 本批本地提交 | `b385160`（.gitignore 补 `/_export/`）；H14 修复为 `f2a734c`，均已 push |
| dev 仓库 | `825f259` → **`b385160`**（24 files changed，fast-forward，无冲突） |
| 主题版本（经软链） | **2.10.88**（`readlink -f` 确认指向 `site-repo/sinofresh-theme`） |
| 前台 | 200，站点正常 |

修复落盘自证：JS 仅 94/125 两行使用选择器且都带 `[]`（裸形态只出现在注释里）；两个 sanitize 回调按平行数组读（875/915 两个 block）；enqueue `1.0.3`。

> 注：`grep -c` 的裸计数一度报警（`attachment_id]"` 命中 1 条、`$row['slug']` 命中 3 条），逐行核对后全部是**注释**或**getter**（`sf_shape_library()` 从行主序存储重建行数组，本就该读 `$row['slug']`）——再次印证「计数≠语义」。

## 二、三道 live 门

| 门 | 结果 | 说明 |
|---|---|---|
| `h14_gate.py --live` | **26 / 0 全绿** | 含浏览器实测：两个库各「选图后隐藏字段拿到非 0 值」；另有两条选择器语义断言（带 `[]` 匹配全部行输入、裸后缀匹配 0 个） |
| `h13_gate.py --live` | **12 / 0 全绿** | 版本行读到 2.10.88，证明版本常量同步到位（无假红） |
| `h12_gate.py --live` | **18 检查 / 7 红** | 5 条 zero-drift + 2 条 DB seed。**与本次 pull 无关**，见下 |

（h14 期望值我先前估 24，实际 26——负数对照期间新增了 2 条选择器语义断言，全部 PASS。）

## 三、h12 --live 7 红：不是 pull 造成的

**证明「与 pull 无关」的两条硬证据：**

1. 三条 DB 覆盖行的创建时间 = **2026-09-26 11:09–13:37 UTC**（北京 19:09–21:37），而本次 pull 发生在今天。`git pull` 只写 `site-repo` 里的文件，不可能创建 `wp_posts` 行。
2. 归档 `live-before-*.html` 钉的是 **2.10.87 字节 + footer 里的 `HACCP, BRC.` + 首页 `BESTSELLER`**。DB footer 覆盖在 09-26 21:25 就写入了 `BRCGS` ⇒ **pull 之前 live 就已经是 BRCGS**，归档就已经对不上 ⇒ 红是既有的。

### 3.1 五条 zero-drift 红 ← 三条 DB 模板覆盖在遮蔽文件

dev 库里存在**三条 publish 的模板覆盖**（旧的一批 260/272/273 早已删除归档，这是**新长出来的**）：

```
303  wp_template_part  publish  header      创建 2026-09-26 11:09:19 UTC
304  wp_template      publish  front-page  创建 2026-09-26 11:09:19 / 改 13:37:58
346  wp_template_part  publish  footer      创建 2026-09-26 13:25:21 / 改 13:26:05
```

WP 的模板解析里 **DB 覆盖优先于文件**，所以现在前台渲染的是这三条 DB 行，不是 git 里的文件。取证矩阵：

| | 缩进风格 | 结论 |
|---|---|---|
| 文件 `parts/header.html` | `\n\t<!-- wp:group -->\n\t<div` | 文件带缩进 |
| 归档 `live-before-about.html` | `\n\t\n\t<div class="…sf-topbar-left…"` | **归档 = 文件渲染** |
| DB 行 `dbtpl-260`（同型归档） | `<div …><!-- wp:group -->\n<div` | 重序列化形态 |
| 当前 live | `\n<div class="…sf-topbar-left…"` | **live = DB 覆盖渲染** |

**四条非首页页面的差异是什么性质**（逐项归一化后判定）：

| 差异 | 例子 | 性质 |
|---|---|---|
| 标签间缩进 | `>\n\t\n\t<` vs `>\n<` | 纯空白 |
| SVG 自闭合 | `<circle …/>` vs `<circle …></circle>` | 重序列化，DOM 等价 |
| HTML 实体解码 | `&middot;` vs `·` | 渲染等价 |
| `wp-container-core-*` 布局类名 hash | `group-is-layout-1be56b12` vs `…1036ba7b` | 属性顺序变化导致 hash 变化；**规则集合完全相同**（归一化后 16 vs 16、11 vs 11、9 vs 9、7 vs 7 全等） |

⇒ **四条页面视觉上无差别**（`text-equal` 首差仅为 `&middot;`/`·` 这类等价物）。

### 3.2 首页：DB 覆盖丢内容（真问题）

`templates/front-page.html` vs DB 行 304，归一化后实质差异两处：

1. **`BESTSELLER` 标签被丢掉** —— 文件里有 2 处，DB 行没有。live 实测：**首页 `BESTSELLER` 计数 0**（归档 2）。这是「有损重序列化」把产品卡上的 BESTSELLER 徽标吃掉了。
2. block comment 多出 `"theme":"sinofresh-theme"` —— 重序列化附加，无害。

### 3.3 两条 DB seed 红 ← 页面自己的编辑

| 页 | 到期时间 | 实质差异 | 性质 |
|---|---|---|---|
| 14 `/about/` | 改于 2026-09-26 09:40:48 UTC | `wp:image {"id":257…}` → `{"id":285…}`，工厂区 figcaption 也换了 | 用户的编辑器保存 |
| 15 `/quality/` | 改于 2026-09-27 07:54:55 UTC | block 属性顺序变化 + 文案变化（`HPLC … verifies active ingredient` → `… system for quantitative analysis`） | 用户的编辑器保存 |

页面 17/29/11 的 seed **通过**，说明改的是 14/15 两页，不是系统性事件。

### 3.4 三条覆盖行 vs 三个文件：完整实质差异清单

| 覆盖行 | 对应文件 | text 等价 | 实质差异 |
|---|---|---|---|
| 303 header | `parts/header.html` | ✔ 等价 | 只有 `<!-- wp:html -->` 包裹的 sentinel div 丢了块分隔注释（渲染等价，`.sf-header-sentinel` live 仍在） |
| 346 footer | `parts/footer.html` | ✘ | **`HACCP, BRC.` → `HACCP, BRCGS.`**（这正是 H13 列在「下次批次」的内容层改名；现已有人在 Site Editor 做了，但只落在 DB） |
| 304 front-page | `templates/front-page.html` | ✘ | **丢了 2 个 `BESTSELLER`**（损失）+ `"theme"` 属性（无害） |

## 四、两个顺带发现

### 4.1 `/_export/` 已进 .gitignore ✔

已在 `.gitignore` 的「大体积过程产物」块补 `/_export/`（含理由注释），提交 `b385160` 并 push。`git check-ignore -v _export/` → `.gitignore:12:/_export/` 命中。

### 4.2 「404 缩略图」真相：不是缩略图问题，是一整条僵尸媒体行 ⚠

用户以为是缩略图缺失，实际是 **attachment ID 42 的主文件都不存在**：

```
main: …/2026/09/微信图片_20260629142652_11_458-scaled.jpg   exists=N
medium 300x225 / large / thumbnail / medium_large / 1536 / 2048  exists=N   ← 全 6 个 size 全缺
```

- **无法重新生成**：`wp media regenerate 42 --only-missing` → `Warning: Can't find "微信图片_20260629142652_11_458" (ID 42). Error: No images regenerated (1 failed).`（元数据 6 size 前后不变，未被破坏）
- 全站 35 个附件里**只有这 1 个**主干文件缺失（`missing-main-file=1`）
- 该行：创建 2026-09-15 19:46:50、`parent=0`、非任何文章的特色图、全站 post_content/schema **零引用**、迁移包 `_export/uploads` 里也没有
- 影响面：**访客永远遇不到这个 404**（无人引用）；它只在**后台媒体弹窗**里显示成破图。h14 门把它归为 `(info) non-theme 4xx`，不影响任何断言

⇒ 只剩两条出路：**删掉这行僵尸记录**（推荐，零损失、可逆性来自它本身无价值），或你**重新上传**原图（需要源文件，磁盘与迁移包里都没有）。

## 五、建议动作（等拍板，未执行任何破坏性操作）

**建议 A（推荐）：恢复「文件权威」并保住那处有益的改动**

1. 把 footer 的 `BRC` → `BRCGS` 落到 `parts/footer.html`（代码层，进 git）；
2. 删掉 DB 行 303 / 304 / 346（先归档到 `docs/h14-archive/`，可逆）⇒ 首页 BESTSELLER 回来、header 的 `wp:html` 包裹回来、文件重新成为唯一权威；
3. 页面 14/15 的 seed 与 5 个 `live-before-*.html` 重立基线（= 你已批准的编辑）；
4. 复跑 h12 --live → 期望 18/0。

**建议 B：改由 Site Editor 主管模板**——那就把文件模板与库对齐并刷新基线；**代价**：以后 git 里改 `parts/header.html` / `parts/footer.html` / `templates/front-page.html` 都**不会**在前台生效，pull 管线对这三个模板失效。不建议。

**僵尸媒体行**：建议删除（等确认）。

## 六、遗留（与本批无关）

1. 模板/页脚/OEM-ODM 页正文 `BRC` 字样内容层统一（页脚已有 DB 覆盖版本；其余页正文仍 `BRC`）。
2. `docs/batch3b-live-accept-shots/` 两个 PNG 在工作区呈「已修改」（09-25 遗留二进制差异），未由本批产生，未触碰。
3. 工作区 `overview.md` 与 `tools/_h14_*.js|py|php` 仍是未跟踪文件（历史证据，是否入库待定）。
