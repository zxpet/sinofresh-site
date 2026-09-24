# 同意批 · 决定加版本与有效期 ＋ 接上 WP Consent API

> 日期 2026-09-24 · 落点 `sinofresh-theme/assets/js/ui-components.js` ＋ `functions.php`
> 候选 `46cabb7`（**已装预检副本，未 pull**）· dev live 仍 `aa9abc6` · 令牌仍 `2.10.79`（无 CSS 改动）
> 依据：`docs/security-supplement-2026-09-24.md` §3.2 的 Cookie 缺口 ②④⑤，用户裁决「技术修正可直接做」

## 1. 范围

| 裁决 | 本批 |
|---|---|
| 决定加 version / expires | ✅ 做了 |
| `wp-consent-api` 要么接上、要么停用 | ✅ 选**接上** |
| 政策页文案重写 | ⏸ 等用户拍板（用户列为「需要我拍板的三件」之一） |
| 去掉 `Manage Preferences` 按钮 | ⏸ 同上 |
| 加撤回入口 | ⏸ 同上 |

三件「待拍板」与已做的两件在同一条同意特性上，但分属不同文件（`parts/footer.html` / 内容页 vs
`ui-components.js`），因此**不必等**——本批自成一体，可单独上线；三件定下来是第二次小批。

## 2. 改了什么

### 2.1 一个校验器，三个消费者

改前：`decide()` 写 `{analytics, marketing, timestamp}`，读回时只判真假——

- **永不过期**：决定一次即永久，没有重新征询的路径；
- **无版本**：旧版横幅下的记录仍然回答新版横幅；
- **两个消费者各读各的**：GA4 桥独立 `JSON.parse` 同一个 blob，**任何**记录都会把 `analytics_storage`
  置为 granted。横幅与 GA4 之所以没有分歧，只是因为两者都不做校验。

改后：`readDecision()` 是唯一的判定口，横幅、GA4 桥、Consent API 都经它读：

```js
const VERSION = 2;
const DAYS = 182;
const readDecision = () => {           // 记录还成立才返回，否则 null
    rec = JSON.parse(localStorage.getItem(KEY) || "null")   // 解析失败 -> null
    if (!rec || typeof rec !== "object") return null;
    if (rec.version !== VERSION) return null;               // 旧形状不再回答新横幅
    if (typeof rec.expires !== "number" || rec.expires <= Date.now()) return null;  // 过期即重问
    return rec;
};
```

写回时带 `version: 2` 与 `expires: now + 182 天`。

### 2.2 Consent API 接上

`wp-consent-api` 2.1.0 装着、每页加载，而主题里 `wp_set_consent` **0 处调用**。现在决定写入时调用：

```js
const bridgeConsent = (on) => {
    if (typeof window.wp_set_consent !== "function") return;   // 插件不在也不炸
    const v = on ? "allow" : "deny";
    window.wp_set_consent("statistics", v);
    window.wp_set_consent("marketing", v);
};
```

它是该插件的公开入口（`assets/js/wp-consent-api.js`）：写入一个**带过期的** consent cookie（服务端可用
`wp_has_consent()` 读），并派发 `wp_listen_for_consent_change`。

**回访者加载时只在「插件的 cookie 与记录不一致」时才重写**（比对 `wp_has_consent()`），
避免每次页面浏览都重刷一枚 consent cookie。

### 2.3 脚本自身版本 `1.0.0` → `1.1.0`

`functions.php` 里 `wp_enqueue_script(... '1.0.0' ...)` 是该脚本**自己的**字面量，与主题令牌 `2.10.79` 无关。

⛔ **必须改**：静态资源现在是 `immutable, max-age=31536000`（本日 §6.2 之前是 1 月），
URL 不变则回访浏览器**一年**内不会取新文件 —— 那样本批只对首次访问者生效。

## 3. 证据

| 门 | 断言 | 结果 |
|---|---|---|
| `tools/b3g_consent_unit.js` | 在 stub DOM 里跑**真文件**，10 种情形 30 条 | **30/30** |
| 同上 · 负对照 | 内存里删掉两条守卫行，要求过期/旧版本两种情形**翻转** | **2/2**（证明断言确实在量那两条守卫） |
| `tools/b3g_consent_e2e.py` | 真浏览器、预检副本上 6 个状态流转 | **19/19** |
| 候选 vs live 字节对照 | 归一化目录名与 `?ver=` 后两页**完全一致** | **14/14** |
| `node --check` / `php -l` | 语法 | ok |

E2E 关键几条：首访横幅显示 → accept 写入 `version 2`、到期 ≈182 天、**Consent API cookie = `allow`** →
把记录改成已过期后重载**横幅重新出现** → 旧形状记录**同样重新出现** → reject 写 `deny` →
有效记录重载后仍关闭。另含一条回归：ZH 撤下规则仍 301 → `/about/`。

## 4. 两个后果（必须知道）

1. **所有已有记录的人会被再问一次。** 旧记录没有 `expires`，按新校验一律判为不成立。
   这是「给决定加上有效期」的必然代价 —— 记录从来没带过有效期，就没有「未过期的旧记录」可言。
2. **站点从此会设一枚 `wp_consent_statistics`（及 `wp_consent_marketing`）cookie。**
   之前实测「匿名访客一个 cookie 都不设」不再成立，这是接上 Consent API 的直接结果，
   也正是让服务端能读到同意的机制。⇒ **政策页文案重写时必须写上这两枚**（与待拍板的三件一并做）。

## 5. 回滚

`git revert 46cabb7` 即可（单文件 JS ＋ 一行 enqueue 版本）。预检副本另需重装到目标 SHA。

## 6. 下一步

1. 用户确认 → `git pull --ff-only` 到 `46cabb7` → 服务侧复验（`?ver=1.1.0`、E2E、无新增错误日志）；
2. 三件待拍板定下后做第二次小批（政策文案 / 去掉 Manage Preferences / 撤回入口）；
3. ⛔ **预检副本在 pull 前不要 remove**。
