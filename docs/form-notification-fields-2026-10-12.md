# 表单通知「字段 ↔ 占位符 ↔ 渲染值」对照表

> 站点：生产 www.zxpet.com ｜ 生成日期：2026-10-12 ｜ 生成工具：`tools/h24b_audit_notifs.php` + `tools/h24b_build_field_map.py`
> 
> **数据来源**：直接读 `wp_fluentform_forms.form_fields` 与 `wp_fluentform_form_meta(meta_key=notifications)`，只读。
> **渲染值**用**构造样本**跑 FF 自己的 `ShortCodeParser`（邮件分支 `isHtml=true`），**不含任何真实客户数据**；
> 样本中 `«公司名»` 这类尖括号值 = 该字段的标签占位符，代表「这里会填访客输入的内容」。
> 
> ⚠️ 逐表单独立进程执行 —— FF 把字段定义缓存在静态属性里，同一进程连续渲染多个表单会串（见文末「踩坑」）。

---

## 0. 总览

| 表单 | form_id | 字段数 | 通知 feed | 自动回复状态 |
|---|---|---|---|---|
| Get a Quote | 8 | 8 | Admin Notification / Auto Reply to Customer | 已停用 |
| Request a Sample | 9 | 12 | Admin Notification / Auto Reply to Customer | 已停用 |
| Book a Factory Tour | 10 | 14 | Admin Notification / Auto Reply to Customer | 已停用 |
| Request COA | 11 | 10 | Admin Notification / Auto Reply to Customer | 已停用 |
| Feedback | 12 | 5 | Admin Notification | 无此 feed |

> 管理员通知一律发往 `sales@zxpet.com`；自动回复发往来访者填的邮箱。

---

## 1. form 8 — Get a Quote（报价询盘（网站主表单））

### 字段清单（`{inputs.<key>}` 可用）

| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |
|---|---|---|---|---|
| 1 | `company_name_1` | `input_text` | Company Name | 0 |
| 2 | `contact_person_2` | `input_text` | Contact Person | 0 |
| 3 | `email_3` | `input_email` | Email | 0 |
| 4 | `country_5` | `select` | Country | 8 |
| 5 | `interested_dosage_form_7` | `select` | Interested Dosage Form | 8 |
| 6 | `notes_10` | `textarea` | Notes | 0 |
| 7 | `privacy_consent_11` | `input_checkbox` | Privacy Consent | 1 |
| 8 | `configuration_summary_12` | `input_hidden` | （无标签） | 0 |

### Admin Notification — meta_id 39

- 收件人：`sales@zxpet.com`　·　状态：启用

**主题**

```text
New Inquiry: {inputs.interested_dosage_form_7} from {inputs.company_name_1} ({inputs.country_5})
-- 渲染后 --
New Inquiry: Soft Chews from «Company Name» (United States)
```

**正文模板**（原文；`<br />` 即换行）

```html
New inquiry received from the website:

Company: {inputs.company_name_1}
Contact: {inputs.contact_person_2}
Email: {inputs.email_3}
Country: {inputs.country_5}
Interested Dosage Form: {inputs.interested_dosage_form_7}
Notes: {inputs.notes_10}
Privacy Consent: {inputs.privacy_consent_11.value}

```

**正文渲染**（构造样本 → 邮件实际形态）

```text
New inquiry received from the website:

Company: «Company Name»
Contact: «Contact Person»
Email: «Email»
Country: United States
Interested Dosage Form: Soft Chews
Notes: «Notes»
Privacy Consent: I agree to the Privacy Policy

```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Company | `{inputs.company_name_1}` | Company Name | `input_text` | ✅ |
| Contact | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| Email | `{inputs.email_3}` | Email | `input_email` | ✅ |
| Country | `{inputs.country_5}` | Country | `select` | ✅ |
| Interested Dosage Form | `{inputs.interested_dosage_form_7}` | Interested Dosage Form | `select` | ✅ |
| Notes | `{inputs.notes_10}` | Notes | `textarea` | ✅ |
| Privacy Consent | `{inputs.privacy_consent_11.value}` | Privacy Consent | `input_checkbox` | ✅ |

✅ 未发现问题。

### Auto Reply to Customer — meta_id 40

- 收件人：`{inputs.email_3}`　·　状态：**已停用**

**主题**

```text
We've received your inquiry — SINO FRESH
-- 渲染后 --
We've received your inquiry — SINO FRESH
```

**正文模板**（原文；`<br />` 即换行）

```html
Dear {inputs.contact_person_2},

Thank you for your interest in SINO FRESH pet supplements.
We have received your inquiry regarding {inputs.interested_dosage_form_7} and our sales team will respond within 24 hours on business days.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**正文渲染**（构造样本 → 邮件实际形态）

```text
Dear «Contact Person»,

Thank you for your interest in SINO FRESH pet supplements.
We have received your inquiry regarding Soft Chews and our sales team will respond within 24 hours on business days.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Dear {inputs.contact_person_2}, | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| We have received your inquiry regardin | `{inputs.interested_dosage_form_7}` | Interested Dosage Form | `select` | ✅ |

✅ 未发现问题。

---

## 2. form 9 — Request a Sample（样品申请）

### 字段清单（`{inputs.<key>}` 可用）

| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |
|---|---|---|---|---|
| 1 | `company_name_1` | `input_text` | Company Name | 0 |
| 2 | `contact_person_2` | `input_text` | Contact Person | 0 |
| 3 | `email_3` | `input_email` | Email | 0 |
| 4 | `phone_whatsapp_4` | `input_text` | Phone / WhatsApp | 0 |
| 5 | `country_5` | `select` | Country | 8 |
| 6 | `target_market_10` | `select` | Target Market | 7 |
| 7 | `interested_dosage_form_7` | `select` | Interested Dosage Form | 8 |
| 8 | `sample_quantity_8` | `select` | Sample Quantity | 5 |
| 9 | `flavor_preference_9` | `input_text` | Flavor Preference | 0 |
| 10 | `shipping_address_6` | `textarea` | Shipping Address | 0 |
| 11 | `notes_11` | `textarea` | Notes | 0 |
| 12 | `privacy_consent_12` | `input_checkbox` | Privacy Consent | 1 |

### Admin Notification — meta_id 45

- 收件人：`sales@zxpet.com`　·　状态：启用

**主题**

```text
New Sample Request: {inputs.interested_dosage_form_7} from {inputs.company_name_1}
-- 渲染后 --
New Sample Request: Soft Chews from «Company Name»
```

**正文模板**（原文；`<br />` 即换行）

```html
New sample request received from the website:

Company: {inputs.company_name_1}
Contact: {inputs.contact_person_2}
Email: {inputs.email_3}
Phone / WhatsApp: {inputs.phone_whatsapp_4}
Country: {inputs.country_5}
Shipping Address: {inputs.shipping_address_6}
Interested Dosage Form: {inputs.interested_dosage_form_7}
Sample Quantity: {inputs.sample_quantity_8}
Flavor Preference: {inputs.flavor_preference_9}
Target Market: {inputs.target_market_10}
Notes: {inputs.notes_11}
Privacy Consent: {inputs.privacy_consent_12.value}

```

**正文渲染**（构造样本 → 邮件实际形态）

```text
New sample request received from the website:

Company: «Company Name»
Contact: «Contact Person»
Email: «Email»
Phone / WhatsApp: «Phone / WhatsApp»
Country: United States
Shipping Address: «Shipping Address»
Interested Dosage Form: Soft Chews
Sample Quantity: 1
Flavor Preference: «Flavor Preference»
Target Market: US
Notes: «Notes»
Privacy Consent: I agree to the Privacy Policy

```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Company | `{inputs.company_name_1}` | Company Name | `input_text` | ✅ |
| Contact | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| Email | `{inputs.email_3}` | Email | `input_email` | ✅ |
| Phone / WhatsApp | `{inputs.phone_whatsapp_4}` | Phone / WhatsApp | `input_text` | ✅ |
| Country | `{inputs.country_5}` | Country | `select` | ✅ |
| Shipping Address | `{inputs.shipping_address_6}` | Shipping Address | `textarea` | ✅ |
| Interested Dosage Form | `{inputs.interested_dosage_form_7}` | Interested Dosage Form | `select` | ✅ |
| Sample Quantity | `{inputs.sample_quantity_8}` | Sample Quantity | `select` | ✅ |
| Flavor Preference | `{inputs.flavor_preference_9}` | Flavor Preference | `input_text` | ✅ |
| Target Market | `{inputs.target_market_10}` | Target Market | `select` | ✅ |
| Notes | `{inputs.notes_11}` | Notes | `textarea` | ✅ |
| Privacy Consent | `{inputs.privacy_consent_12.value}` | Privacy Consent | `input_checkbox` | ✅ |

✅ 未发现问题。

### Auto Reply to Customer — meta_id 46

- 收件人：`{inputs.email_3}`　·　状态：**已停用**

**主题**

```text
Your sample request — SINO FRESH
-- 渲染后 --
Your sample request — SINO FRESH
```

**正文模板**（原文；`<br />` 即换行）

```html
Dear {inputs.contact_person_2},

Thank you for your sample request for {inputs.interested_dosage_form_7}.
A sampling fee of USD 200 applies, which is fully deductible from your first bulk order.
Your samples will be ready within 3-7 working days after we confirm the details.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**正文渲染**（构造样本 → 邮件实际形态）

```text
Dear «Contact Person»,

Thank you for your sample request for Soft Chews.
A sampling fee of USD 200 applies, which is fully deductible from your first bulk order.
Your samples will be ready within 3-7 working days after we confirm the details.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Dear {inputs.contact_person_2}, | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| Thank you for your sample request for  | `{inputs.interested_dosage_form_7}` | Interested Dosage Form | `select` | ✅ |

✅ 未发现问题。

---

## 3. form 10 — Book a Factory Tour（工厂参观预约）

### 字段清单（`{inputs.<key>}` 可用）

| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |
|---|---|---|---|---|
| 1 | `company_name_1` | `input_text` | Company Name | 0 |
| 2 | `contact_person_2` | `input_text` | Contact Person | 0 |
| 3 | `email_4` | `input_email` | Email | 0 |
| 4 | `phone_whatsapp_5` | `input_text` | Phone / WhatsApp | 0 |
| 5 | `country_6` | `select` | Country | 8 |
| 6 | `tour_type_8` | `select` | Tour Type | 2 |
| 7 | `preferred_date_9` | `input_date` | Preferred Date | 0 |
| 8 | `job_title_3` | `input_text` | Job Title | 0 |
| 9 | `preferred_time_10` | `input_text` | Preferred Time | 0 |
| 10 | `target_market_7` | `select` | Target Market | 7 |
| 11 | `interested_dosage_form_11` | `select` | Interested Dosage Form | 8 |
| 12 | `number_of_visitors_12` | `select` | Number of Visitors | 4 |
| 13 | `notes_13` | `textarea` | Notes | 0 |
| 14 | `privacy_consent_14` | `input_checkbox` | Privacy Consent | 1 |

### Admin Notification — meta_id 51

- 收件人：`sales@zxpet.com`　·　状态：启用

**主题**

```text
Factory Tour Request: {inputs.tour_type_8} - {inputs.company_name_1}
-- 渲染后 --
Factory Tour Request: On-Site - «Company Name»
```

**正文模板**（原文；`<br />` 即换行）

```html
New factory tour request received from the website:

Company: {inputs.company_name_1}
Contact: {inputs.contact_person_2}
Job Title: {inputs.job_title_3}
Email: {inputs.email_4}
Phone / WhatsApp: {inputs.phone_whatsapp_5}
Country: {inputs.country_6}
Target Market: {inputs.target_market_7}
Tour Type: {inputs.tour_type_8}
Preferred Date: {inputs.preferred_date_9}
Preferred Time: {inputs.preferred_time_10}
Interested Dosage Form: {inputs.interested_dosage_form_11}
Number of Visitors: {inputs.number_of_visitors_12}
Notes: {inputs.notes_13}
Privacy Consent: {inputs.privacy_consent_14.value}

```

**正文渲染**（构造样本 → 邮件实际形态）

```text
New factory tour request received from the website:

Company: «Company Name»
Contact: «Contact Person»
Job Title: «Job Title»
Email: «Email»
Phone / WhatsApp: «Phone / WhatsApp»
Country: United States
Target Market: US
Tour Type: On-Site
Preferred Date: «Preferred Date»
Preferred Time: «Preferred Time»
Interested Dosage Form: Soft Chews
Number of Visitors: 1
Notes: «Notes»
Privacy Consent: I agree to the Privacy Policy

```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Company | `{inputs.company_name_1}` | Company Name | `input_text` | ✅ |
| Contact | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| Job Title | `{inputs.job_title_3}` | Job Title | `input_text` | ✅ |
| Email | `{inputs.email_4}` | Email | `input_email` | ✅ |
| Phone / WhatsApp | `{inputs.phone_whatsapp_5}` | Phone / WhatsApp | `input_text` | ✅ |
| Country | `{inputs.country_6}` | Country | `select` | ✅ |
| Target Market | `{inputs.target_market_7}` | Target Market | `select` | ✅ |
| Tour Type | `{inputs.tour_type_8}` | Tour Type | `select` | ✅ |
| Preferred Date | `{inputs.preferred_date_9}` | Preferred Date | `input_date` | ✅ |
| Preferred Time | `{inputs.preferred_time_10}` | Preferred Time | `input_text` | ✅ |
| Interested Dosage Form | `{inputs.interested_dosage_form_11}` | Interested Dosage Form | `select` | ✅ |
| Number of Visitors | `{inputs.number_of_visitors_12}` | Number of Visitors | `select` | ✅ |
| Notes | `{inputs.notes_13}` | Notes | `textarea` | ✅ |
| Privacy Consent | `{inputs.privacy_consent_14.value}` | Privacy Consent | `input_checkbox` | ✅ |

✅ 未发现问题。

### Auto Reply to Customer — meta_id 52

- 收件人：`{inputs.email_4}`　·　状态：**已停用**

**主题**

```text
Factory tour request received — SINO FRESH
-- 渲染后 --
Factory tour request received — SINO FRESH
```

**正文模板**（原文；`<br />` 即换行）

```html
Dear {inputs.contact_person_2},

Thank you for your interest in visiting the SINO FRESH facility.
We will confirm your {inputs.tour_type_8} tour date and time within 24 hours on business days.
A factory audit preparation checklist will be attached with the confirmation.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**正文渲染**（构造样本 → 邮件实际形态）

```text
Dear «Contact Person»,

Thank you for your interest in visiting the SINO FRESH facility.
We will confirm your On-Site tour date and time within 24 hours on business days.
A factory audit preparation checklist will be attached with the confirmation.

If you have any additional requirements, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Dear {inputs.contact_person_2}, | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| We will confirm your {inputs.tour_type | `{inputs.tour_type_8}` | Tour Type | `select` | ✅ |

✅ 未发现问题。

---

## 4. form 11 — Request COA（合规文件（COA）索取）

### 字段清单（`{inputs.<key>}` 可用）

| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |
|---|---|---|---|---|
| 1 | `company_name_1` | `input_text` | Company Name | 0 |
| 2 | `contact_person_2` | `input_text` | Contact Person | 0 |
| 3 | `country_4` | `select` | Country | 8 |
| 4 | `target_market_5` | `select` | Target Market | 7 |
| 5 | `email_3` | `input_email` | Email | 0 |
| 6 | `interested_dosage_form_6` | `select` | Interested Dosage Form | 8 |
| 7 | `document_type_7` | `input_checkbox` | Document Type | 5 |
| 8 | `notes_8` | `textarea` | Notes | 0 |
| 9 | `privacy_consent_9` | `input_checkbox` | Privacy Consent | 1 |
| 10 | `certificate_10` | `input_hidden` | （无标签） | 0 |

### Admin Notification — meta_id 57

- 收件人：`sales@zxpet.com`　·　状态：启用

**主题**

```text
Document Request: {inputs.company_name_1} ({inputs.country_4})
-- 渲染后 --
Document Request: «Company Name» (United States)
```

**正文模板**（原文；`<br />` 即换行）

```html
New document request received from the website:

Company: {inputs.company_name_1}
Contact: {inputs.contact_person_2}
Email: {inputs.email_3}
Country: {inputs.country_4}
Target Market: {inputs.target_market_5}
Interested Dosage Form: {inputs.interested_dosage_form_6}
Document Type: {inputs.document_type_7.value}
Notes: {inputs.notes_8}
Privacy Consent: {inputs.privacy_consent_9.value}

```

**正文渲染**（构造样本 → 邮件实际形态）

```text
New document request received from the website:

Company: «Company Name»
Contact: «Contact Person»
Email: «Email»
Country: United States
Target Market: US
Interested Dosage Form: Soft Chews
Document Type: COA Sample
Notes: «Notes»
Privacy Consent: I agree to the Privacy Policy

```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Company | `{inputs.company_name_1}` | Company Name | `input_text` | ✅ |
| Contact | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| Email | `{inputs.email_3}` | Email | `input_email` | ✅ |
| Country | `{inputs.country_4}` | Country | `select` | ✅ |
| Target Market | `{inputs.target_market_5}` | Target Market | `select` | ✅ |
| Interested Dosage Form | `{inputs.interested_dosage_form_6}` | Interested Dosage Form | `select` | ✅ |
| Document Type | `{inputs.document_type_7.value}` | Document Type | `input_checkbox` | ✅ |
| Notes | `{inputs.notes_8}` | Notes | `textarea` | ✅ |
| Privacy Consent | `{inputs.privacy_consent_9.value}` | Privacy Consent | `input_checkbox` | ✅ |

✅ 未发现问题。

### Auto Reply to Customer — meta_id 58

- 收件人：`{inputs.email_3}`　·　状态：**已停用**

**主题**

```text
Your document request — SINO FRESH
-- 渲染后 --
Your document request — SINO FRESH
```

**正文模板**（原文；`<br />` 即换行）

```html
Dear {inputs.contact_person_2},

Thank you for your document request.
A sanitized COA sample is attached to this email for your reference.
The full compliance package for {inputs.interested_dosage_form_6} will be sent within 24 hours on business days.

If you need additional documents, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**正文渲染**（构造样本 → 邮件实际形态）

```text
Dear «Contact Person»,

Thank you for your document request.
A sanitized COA sample is attached to this email for your reference.
The full compliance package for Soft Chews will be sent within 24 hours on business days.

If you need additional documents, feel free to reply to this email.

Best regards,
SINO FRESH Pet Food Co., Ltd.
www.zxpet.com
```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Dear {inputs.contact_person_2}, | `{inputs.contact_person_2}` | Contact Person | `input_text` | ✅ |
| The full compliance package for {input | `{inputs.interested_dosage_form_6}` | Interested Dosage Form | `select` | ✅ |

✅ 未发现问题。

---

## 5. form 12 — Feedback（反馈）

### 字段清单（`{inputs.<key>}` 可用）

| # | 占位符 key | 元素类型 | 字段标签 | 选项数 |
|---|---|---|---|---|
| 1 | `feedback_type_1` | `select` | Feedback Type | 4 |
| 2 | `subject_2` | `input_text` | Subject | 0 |
| 3 | `description_3` | `textarea` | Description | 0 |
| 4 | `email_4` | `input_email` | Email | 0 |
| 5 | `privacy_consent_5` | `input_checkbox` | Privacy Consent | 1 |

### Admin Notification — meta_id 63

- 收件人：`sales@zxpet.com`　·　状态：启用

**主题**

```text
New Feedback: {inputs.feedback_type_1} — {inputs.subject_2}
-- 渲染后 --
New Feedback: General Feedback — «Subject»
```

**正文模板**（原文；`<br />` 即换行）

```html
New feedback received from the website:

Type: {inputs.feedback_type_1}
Subject: {inputs.subject_2}
Description: {inputs.description_3}
Email: {inputs.email_4} (may be blank = anonymous)
Privacy Consent: {inputs.privacy_consent_5.value}
Page: {embed_post.permalink}

```

**正文渲染**（构造样本 → 邮件实际形态）

```text
New feedback received from the website:

Type: General Feedback
Subject: «Subject»
Description: «Description»
Email: «Email» (may be blank = anonymous)
Privacy Consent: I agree to the Privacy Policy
Page:

```

**占位符映射**

| 行标签 | 占位符 | 对应字段 | 元素 | 判定 |
|---|---|---|---|---|
| Type | `{inputs.feedback_type_1}` | Feedback Type | `select` | ✅ |
| Subject | `{inputs.subject_2}` | Subject | `input_text` | ✅ |
| Description | `{inputs.description_3}` | Description | `textarea` | ✅ |
| Email | `{inputs.email_4}` | Email | `input_email` | ✅ |
| Privacy Consent | `{inputs.privacy_consent_5.value}` | Privacy Consent | `input_checkbox` | ✅ |

✅ 未发现问题。

---

## 5. 本次修复的 5 处「Privacy Consent」行（2026-10-12）

5 个表单的管理员通知里，这一行**全部是坏的**，三种坏法：

| 表单 | feed | 改前 | 改后 | 症状 |
|---|---|---|---|---|
| form 8 | meta_id 39 | `Privacy Consent: {inputs.company_name_1}` | `Privacy Consent: {inputs.privacy_consent_11.value}` | 显示成公司名（本批单独修） |
| form 9 | meta_id 45 | `Privacy Consent: {inputs.company_name_1}` | `Privacy Consent: {inputs.privacy_consent_12.value}` | 显示成公司名 |
| form 10 | meta_id 51 | `Privacy Consent: {inputs.company_name_1}` | `Privacy Consent: {inputs.privacy_consent_14.value}` | 显示成公司名 |
| form 11 | meta_id 57 | `Privacy Consent: {inputs.privacy_consent_9.i_agree_to_the_privacy_policy_9_1}` | `Privacy Consent: {inputs.privacy_consent_9.value}` | **完全空白**（孤儿 key） |
| form 12 | meta_id 63 | `Privacy Consent: {inputs.privacy_consent_5.i_agree_to_the_privacy_policy_5_1}` | `Privacy Consent: {inputs.privacy_consent_5.value}` | **完全空白**（孤儿 key） |

修复工具：`tools/h24b_fix_privacy_line.php`（自动发现隐私字段 / 逐表单备份 / 一条命令回滚）

## 6. 同批完成的另两项变更（2026-10-12）

### 6.1 自动回复（Auto Reply）全部停用

form 8 在 H24 防护上线时已停用，本批把 **form 9 / 10 / 11 一并停用**（form 12 本就没有此 feed）：

| 表单 | Auto Reply feed | 收件人 | 改前 | 改后 |
|---|---|---|---|---|
| form 8 | meta_id 40 | `{inputs.email_3}` | 已停用 | — |
| form 9 | meta_id 46 | `{inputs.email_3}` | 启用 | **已停用** |
| form 10 | meta_id 52 | `{inputs.email_4}` | 启用 | **已停用** |
| form 11 | meta_id 58 | `{inputs.email_3}` | 启用 | **已停用** |

判定依据（源码级）：`GlobalNotificationManager::getEnabledFeeds()` 里
`ArrayHelper::isTrue($feed, 'enabled')` 是**唯一**发送开关；写成 `false` 即停用。
用 FF 自己的这个函数实测：5 个管理员通知（39/45/51/57/63）仍然发送，4 个 Auto Reply（40/46/52/58）全部不再发送。

修复工具：`tools/h24b_autoreply_toggle.php`（status / disable / restore，逐 feed 备份整行原始值）。
**恢复时机**：等防护稳定 ≥1 周后 4 个一起恢复，恢复时统一加「仅非 spam 触发」守卫。

### 6.2 form 11「Document Type」占位符补 `.value`

| 表单 | feed | 改前 | 改后 | 症状 |
|---|---|---|---|---|
| form 11 | meta_id 57 | `Document Type: {inputs.document_type_7}` | `Document Type: {inputs.document_type_7.value}` | HTML 邮件里被包成 `<ul><li>` 多行列表 |

实测（同一份构造数据 × 两个渲染分支）：**裸用 + 数组 + `isHtml=true` → `<ul><li>`**；
`.value` 在**全部场景**（字符串 / 单元素数组 / 多元素数组 × 两个分支）都是**内联单行**，
多选时输出 `COA Sample, MSDS`（逗号连接，不会出现 `Array`）。

修复工具：`tools/h24b_fix_checkbox_value.php`（通用：自动发现所有 checkbox/radio 字段，批量规范化，逐 feed 备份）。

## 7. 以后改模板的注意事项

1. **复选框/单选框一定要加 `.value`**：`{inputs.privacy_consent_11}` 在邮件分支会被渲染成 `<ul><li>…</li></ul>`（多行列表），
   而 `{inputs.privacy_consent_11.value}` 直接输出**内联单行**文本（多选时逗号连接，如 `COA Sample, MSDS`）。
   其余字段（text/email/select/textarea）加不加都一样。
2. **只能用 `{inputs.<字段key>}`**：字段 key 形如 `company_name_1`（`{元素名}_{index}`）。
   不要用「选项级」key（例：`privacy_consent_9.i_agree_to_the_privacy_policy_9_1`）—— FF 解析不到，**渲染为空**。
3. **复制模板要整段检查**：本批 5 处坏法就是「复制 form 8 的通知、只改了字段却没改占位符」造成的。
4. **改完必须核对**：在 FF 表单编辑器里点「预览通知」，或跑 `tools/h24b_audit_notifs.php`（R1/R2/R3 三类校验会自动报）。
5. **索引不会重排**：删除中间字段后，已有字段的 `_index` 不变；但**新增**字段会用新索引，务必回模板核对。

### 踩坑：FF 的字段定义有静态缓存

`FormFieldsParser` 把字段定义缓存在静态属性里。同一个 PHP 进程里连续渲染多个表单时，
后一个表单会复用前一个的字段定义 —— 实测 form 9 只渲染出 form 8 也有的那几个字段，其余全空，
**看起来像模板坏了，其实是工具的问题**。所以普查脚本必须**逐表单独立进程**跑（`SF_H24B_FORM=<id>`），别在一个 `wp eval-file` 里循环所有表单。

---

*本文档由脚本生成，请勿手改 —— 要更新就跑 `tools/h24b_build_field_map.py`。*
