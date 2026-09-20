# 批次 2C 第二步（`/formulas/` 档案页）回滚剧本

> 状态：**2026-09-20 用户指定写入项目记忆**。执行前提：改动都已在 Git 里（本地工作区 → `origin` → 云端 `site-repo`）。
> 云端真身：`/var/www/dev.zxpet.com/site-repo`（`wp-content/themes/sinofresh-theme` 是软链到 `site-repo/sinofresh-theme`）。

## 0. Commit 地图（执行回滚前先 `git log --oneline -6` 核对）

| 序 | 内容 | commit | 状态 |
|---|---|---|---|
| 1 | 新建 `templates/archive-sf_formula.html`（`archive.html` 一字未动） | `a518207` | 已 push |
| 2 | `functions.php` 八处改动（R1／R5／R6／noun／301／`[sf_formula_filters]`／sf-js／面包屑候选表）＋`tools/sf_masked_cmp.py` | `6767d1c` | 已 push |
| 3 | grid K1 补 `data-form` | 待提交 | — |
| 4 | `style.css` 37c＋36a＋版本 2.10.44 ＋ `assets/js/formula-filter.js` 1.0.0 | 待提交 | — |
| 5 | 8 个剂型页内部链接（单独 commit，可单独 revert） | 待提交 | — |

## 1. 顺序（**不可颠倒**）

```
① 先 revert 模板  a518207      ② 再 revert functions.php  6767d1c
```

为什么是这个顺序：

- **先退 functions.php 会留下更坏的中间态**：新模板仍在磁盘上，但 R1 短路与 noun 没了 → `/formulas/` 渲染出 0 张卡，计数还写「21 articles」（静默坏页）。
- **先退模板**则页面立刻回落到 `archive.html`：10 篇博客卡/页、`[sf_archive_count]` 输出「21 articles」。不理想，但**可用且无报错**——这是回滚过程中可以停留的一站。

## 2. 避免中间态的一条命令（推荐）

若不想经过任何一种中间态，把两步合成一次 revert（`git revert` 按参数顺序依次生效，等于「子项②的 commit 带上模板的 revert」）：

```bash
cd /Users/meng/WorkBuddy/sinofresh外贸网站建设
git revert --no-edit a518207 6767d1c      # 顺序即「先模板、后 functions.php」
git push origin HEAD
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/site-repo && git pull --ff-only'
```

## 3. 只回滚其中一步

```bash
# 只退模板（留着 functions.php 的档案页接线；R1 短路此时无害）
git revert --no-edit a518207

# 只退 functions.php（保留新模板；注意会退化成 0 卡 + "21 articles"，见 §1 反面）
git revert --no-edit 6767d1c
```

子项 ③／④／⑤ 各自单独 commit，回滚时**仍从后往前**逐个 revert；⑤（剂型页内部链接）单独成 commit 就是为了能只退它而不动档案页。

## 4. 文件级兜底（Git 之外的保险）

`sinofresh-theme/_backup/b2c-step2-20260920-182023/` 存有**改动前**的 `functions.php`（140546 B）、`style.css`（245144 B）与 `README.txt`（写明快照基准 `d9b80dd` 与覆盖范围）。

```bash
cd sinofresh-theme
cp _backup/b2c-step2-20260920-182023/functions.php functions.php
cp _backup/b2c-step2-20260920-182023/style.css     style.css
```

⚠️ **这个目录只在本地工作区存在**（`_backup/` 被 `.gitignore` 的 `**/_backup/` 忽略，云端没有）。所以云端要还原只能走 Git（§2／§3）；需要文件级还原时先在本地还原 → commit → push → 云端 pull。

适用场景：某次 revert 冲突解不开，或只想把单个文件按字节还原。`_backup/` 的历史清理**暂缓**，不执行 `git rm --cached`。

## 5. 回滚后必须验的（缺一不可）

```bash
# 5.1 云端回到基线：200 / 114403 B，且回到「博客配方」态
ssh root@65.49.215.152 'curl -s -o /tmp/rb.html -w "HTTP=%{http_code} bytes=%{size_download}\n" https://dev.zxpet.com/formulas/
  echo "blog-chips=$(grep -o sf-blog-chips /tmp/rb.html | wc -l)  fcard=$(grep -o "<article class=\"sf-fcard\"" /tmp/rb.html | wc -l)"
  rm -f /tmp/rb.html'
# 期望：HTTP=200 bytes=114403 / blog-chips=1 / fcard=0

# 5.2 云端工作区干净、HEAD 与 origin 一致
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/site-repo && git status --porcelain | wc -l && git log --oneline -1'

# 5.3 预检装置零残留（若曾用过 §6 的预检）
ssh root@65.49.215.152 'ls -A /var/www/dev.zxpet.com/public/wp-content/mu-plugins/ | wc -l; ls -d /var/www/dev.zxpet.com/preflight-themes 2>&1 | tail -1'
# 期望：0 / No such file or directory

# 5.4 本地工作区与云端 md5 一致
ssh root@65.49.215.152 'md5sum /var/www/dev.zxpet.com/site-repo/sinofresh-theme/functions.php'
md5 -q sinofresh-theme/functions.php
```

**权威基线数字**：`/formulas/` = **HTTP 200 / 114403 B**（改了 functions.php 但未上新模板时的基线是 114403；这也是「档案页回到改动前」的唯一硬指标）。

## 6. 与预检装置的关系

上线前的验证不走「先部署再验」，而是用**临时请求头门预检**（不改线上主题）：

1. `cp -a /var/www/dev.zxpet.com/site-repo/sinofresh-theme /var/www/dev.zxpet.com/preflight-themes/sinofresh-theme`，只替换待验文件；
2. 写 `wp-content/mu-plugins/zz-sf-preflight.php`：`theme_root` 过滤器，**仅当** `$_SERVER['HTTP_X_SF_PREFLIGHT'] === '1'` 时改指向副本；
3. 同一 URL 带／不带头两次 `curl` = A/B；配合 `python3 tools/sf_masked_cmp.py --fetch <dir> --header 'X-SF-Preflight: 1' <paths…>` 与 `--aa <url>` 自检；
4. **用完立刻**删 mu-plugin 与副本，并按 §5.1／5.3 复验。

回滚时若页面出现异常，先确认这两样东西不在（它们不属于 Git，容易漏删）。

---

## 附：第三步 TP 重收录的回滚（2026-09-20 执行，属本批回滚剧本）

本步**没有改主题任何文件**，只让 TranslatePress 在 `/zh/` 渲染时注册新串，因此回滚只涉及数据库。

### 备份位置

```
/root/tp-backup-20260920-115727.sql     425104 B
```

内容：10 张 `wp_trp_*` 表（`dictionary_en_us_zh_cn`、`original_strings`、`original_meta`、`gettext_en_us`、`gettext_original_strings`、`gettext_zh_cn`、`gettext_original_meta`、`machine_translation_locks`、`slug_originals`、`slug_translations`），
由 `mariadb-dump --single-transaction --add-drop-table` 生成，**带 `DROP TABLE IF EXISTS`，可整份导回**。
已实测：导入临时库 `sfs3_bak` 后表行数与现网基线一致（1290/1290/1178/623），确认可用。

### 完整回滚

```bash
export MYSQL_PWD="$(sed -n 's/^DBPASS=//p' /root/sinofresh-db-creds.txt)"
mariadb -u root sinofresh < /root/tp-backup-20260920-115727.sql
```

### 轻量回滚（推荐：本操作纯追加、id 单调，删除不影响既有行）

```sql
DELETE FROM wp_trp_dictionary_en_us_zh_cn WHERE id >= 1291;   -- 本轮新增 43 行
DELETE FROM wp_trp_original_strings        WHERE id >= 1291;
```

### 回滚后验收

- 表计数回到 **1290 / 1290**，gettext 侧 **1178 / 623（147×status0 + 476×status4）**
- `wp_trp_dictionary_en_us_zh_cn` 中 `Browse All Formulas →` 行数 = **0**
- 页面侧**不需要复验**：重收录已由掩码回归证明「19/19 SAME」，页面输出与串是否注册无关（译文为空 ⇒ 回落英文原文）
