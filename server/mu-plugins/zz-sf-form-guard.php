<?php
/**
 * Plugin Name: SINO FRESH - Form Guard
 * Description: 表单机器人询盘治理（批次 H24，方案 B）：① 按真实 IP 收紧提交限流；② 五路弱信号评分制内容判定（模式化，不硬编码机器人特征）；③ 判为垃圾的提交**落库标 spam**、**不触发任何邮件**（管理员通知与自动回复都不发）、写入独立审计日志表；④ 后台「表单防护」人工复核页（查看 / 标为正常 / 一键加黑名单）；⑤ 当日垃圾超阈值发一封告警（每天最多一封）。Turnstile 走 Fluent Forms 原生字段，服务端提供健康探测与**降级开关**：挑战服务不可用时自动跳过校验，靠蜜罐 + 计时 + 评分兜底，绝不让真客户填不了表。DEV 与生产共用同一文件。
 * Version:     1.0.0
 * Author:      SINO FRESH
 *
 * WHY THIS EXISTS (2026-10-12, batch H24)
 * ---------------------------------------
 * 「Get a Quote」表单（form 8）自 10-10 起被同一台机器人以**慢速滴灌**方式刷入 210 条垃圾
 * （212 条中 210 条），且因该表单配了「自动回复客户」，每条垃圾都会向被滥用的第三方邮箱
 * 发出一封本域名的信 —— 3 天 412 封，收件人含 dshs.wa.gov / dss.virginia.gov /
 * lincolnps.org 等真实机构域名。这是本批实际损失最大的一项：持续消耗发信域名信誉
 * （SPF 正常，DMARC 仍为 p=none）。
 *
 * 只读扫描（docs/scan-form-spam-2026-10-12.md）确认：三层应用防护全部未启用；根因不是
 * 「没有反垃圾功能」，而是 Fluent Forms 拿不到访客真实 IP —— 它的 resolveIp() 不信任任何
 * 代理（config/trustedproxy.php 在本插件里不存在），存的永远是 CF 边缘地址；于是内置限流
 * 按「边缘节点」计数，对慢速滴灌结构上无效（实测任意 IP 任意 30 秒窗口内最大提交数 = 1，
 * 阈值是 5）。真实 IP 由 zz-sf-aa-real-ip.php 统一修复（本文件 B2 有硬前置守卫）。
 *
 * WHY THE SCORE, NOT A BLACKLIST OF STRINGS
 * -----------------------------------------
 * 运营要求「不写死 RobertTon」——今天的特征明天就变，硬编码只会变成一份会过期的名单。
 * 因此判定由五路**弱信号**构成，每路都是模式（结构 / 语言 / 映射 / 版本阈值），单一信号
 * 永远不足以判 spam（最高 2 分 < 阈值 4），必须叠加：
 *
 *   S1  公司名**后缀**与联系人共享片段（≥3，非通用词）              +3
 *       共享片段不在公司名尾部（家族企业常见）时降为                 +1
 *   S2  短句价格追问模板（多语种价格词 + 无任何具体采购特征）         +1
 *   S2b 极短、无数字、无采购特征的留言（语言无关的补位信号）          +1
 *   S3  申报国家与邮箱域/TLD 不一致（保守映射，未知国别不判）        +1
 *   S4  被恶意软件套壳 / 版本滞后的 UA —— **只记录，不计分**          +0
 *   S5  一次性 / 临时邮箱域                                        +1
 *   S6  提交过快（服务端签名的计时字段，< 3 秒）                     +2
 *   S7  Turnstile token 校验不通过（只算「带了 token 但无效」；未带一律 0）  +4
 *
 * 阈值 4 ⇒ 本批形态沿 S1(3)+S2 / S1(3)+S2b / S1(3)+S3 / S1(3)+S2+S3 等多条路径
 * 都能命中；真客户即使偶然命中 S2（一句 "what is your price"）也只有 1 分，
 * 而 S4 永不参与成案。明确**不做**的规则见 docs/h24-form-antispam-plan-2026-10-12.md §四：
 * 邮箱域名黑名单（t-online.de / web.de / libero.it / alice.it 都是真实德意客户的主流邮箱）、
 * 「非英语即拒收」、UA 陈旧即拒收。
 *
 * WHY THE SPAM LANDS IN THE DB BUT NO MAIL GOES OUT
 * ------------------------------------------------
 * 被拦提交仍然入 `fluentform_submissions`（status = 'spam'）——留证、可统计、可复核；
 * 但**根本不会进入 Fluent Forms 的处理流程**（`wp_ajax_nopriv_fluentform_submit` 上以更高
 * 优先级接管，输出成功响应后即结束请求），因此管理员通知与自动回复**一封都不会发**。
 * 对机器人返回「成功」而不是错误，是刻意的：让它以为提交有效，不调整策略，也不暴露防护细节。
 *
 * ROLLBACK
 * --------
 * 删除本文件（或改名 .off）即停用全部逻辑；Fluent Forms 侧的蜜罐与「拒绝空提交」两项是
 * 后台配置，回滚方法见 docs/h24-*-report-*.md。审计日志表 wp_sf_form_spam_log 可保留，
 * 它不在任何数据流上。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* -------------------------------------------------------------------------
 * §0  配置（常量可被 wp-config.php 覆盖，也可用同名的过滤器在运行时调整）
 * ---------------------------------------------------------------------- */

/** 判定为垃圾所需的最低分。单一信号最高 2 分 ⇒ 结构上不可能单信号成案。 */
if ( ! defined( 'SF_FG_SPAM_THRESHOLD' ) ) {
	define( 'SF_FG_SPAM_THRESHOLD', 4 );
}

/** B2：同一真实 IP 在窗口期内允许的提交次数与窗口长度（秒）。 */
if ( ! defined( 'SF_FG_MAX_SUBMISSIONS' ) ) {
	define( 'SF_FG_MAX_SUBMISSIONS', 3 );
}
if ( ! defined( 'SF_FG_MIN_INTERVAL' ) ) {
	define( 'SF_FG_MIN_INTERVAL', 3600 );
}

/** S1：公司名与联系人共享片段的最小长度。 */
if ( ! defined( 'SF_FG_MIN_FRAGMENT' ) ) {
	define( 'SF_FG_MIN_FRAGMENT', 3 );
}

/** S4：低于此主版本的 Chrome/Edge 且声明 Windows 10 才计入。
 *  取 140：2026-10 的正常版本已远高于此（本批机器人用的是 129/130/131），
 *  而留出的余量保证「稍旧的办公电脑」不会被单独成案（单信号最高 2 分 < 阈值 4）。 */
if ( ! defined( 'SF_FG_STALE_MAJOR' ) ) {
	define( 'SF_FG_STALE_MAJOR', 140 );
}

/** S6：表单渲染到提交的最短合理间隔（秒）。 */
if ( ! defined( 'SF_FG_MIN_FILL_SECONDS' ) ) {
	define( 'SF_FG_MIN_FILL_SECONDS', 3 );
}

/** ⑤：当日垃圾数达到该值发一封告警（每天最多一封）。 */
if ( ! defined( 'SF_FG_ALERT_THRESHOLD' ) ) {
	define( 'SF_FG_ALERT_THRESHOLD', 50 );
}

/** 存储位置。 */
if ( ! defined( 'SF_FG_LOG_TABLE' ) ) {
	define( 'SF_FG_LOG_TABLE', 'sf_form_spam_log' );
}
if ( ! defined( 'SF_FG_DB_VERSION' ) ) {
	define( 'SF_FG_DB_VERSION', '1.0.0' );
}
if ( ! defined( 'SF_FG_ALERT_OPT' ) ) {
	define( 'SF_FG_ALERT_OPT', 'sf_fg_alert_state' );
}
if ( ! defined( 'SF_FG_BLOCKLIST_OPT' ) ) {
	define( 'SF_FG_BLOCKLIST_OPT', 'sf_fg_blocklist' );
}
if ( ! defined( 'SF_FG_HEALTH_OPT' ) ) {
	define( 'SF_FG_HEALTH_OPT', 'sf_fg_turnstile_health' );
}
if ( ! defined( 'SF_FG_ENABLED_OPT' ) ) {
	define( 'SF_FG_ENABLED_OPT', 'sf_fg_enabled' );
}

/**
 * 总开关。紧急时可 `wp option update sf_fg_enabled 0` 立刻停用全部判定
 * （日志、告警、复核页仍可用，便于事后复盘）。
 *
 * @return bool
 */
function sf_fg_enabled() {
	return (bool) apply_filters( 'sf_fg_enabled', '0' !== (string) get_option( SF_FG_ENABLED_OPT, '1' ) );
}

/**
 * 受保护的表单 id 列表。默认「全部表单」——本批只有 form 8 被打，但其余表单
 * 用的是同一套 Fluent Forms 提交端点，没有理由只护一张。
 *
 * @param int[] $ids
 * @return int[]
 */
function sf_fg_guarded_forms( $ids = null ) {
	if ( null === $ids ) {
		$ids = array(); // 空 = 全部
	}

	return array_map( 'intval', (array) apply_filters( 'sf_fg_guarded_forms', $ids ) );
}

/**
 * 该表单是否受保护。
 *
 * @param int $form_id 表单 id。
 * @return bool
 */
function sf_fg_is_guarded( $form_id ) {
	$list = sf_fg_guarded_forms();
	if ( ! $list ) {
		return $form_id > 0;
	}

	return in_array( (int) $form_id, $list, true );
}

/* -------------------------------------------------------------------------
 * §1  B2 真实 IP 上的限流收紧
 *
 * 顺序硬约束：B2 必须在 B1（zz-sf-aa-real-ip.php）之后。若真实 IP 层没生效，
 * 计数键就是 CF 边缘地址 —— 两个走同一节点的真客户会被一起计数，收紧阈值会
 * 先挡住真客户。因此这里不是"相信部署顺序"，而是**运行时检查**：只要直连方
 * 仍是 CF 边缘地址，就退回插件默认值，绝不收紧。
 * ---------------------------------------------------------------------- */

/**
 * 真实 IP 层是否已生效（可安全地按 IP 计数）。
 *
 * @return bool
 */
function sf_fg_real_ip_ready() {
	if ( ! function_exists( 'sf_real_ip_is_cloudflare' ) ) {
		return false; // 真实 IP 层缺失。
	}
	if ( ! isset( $_SERVER['REMOTE_ADDR'] ) ) {
		return true; // CLI 环境，无直连方。
	}
	$remote = trim( (string) $_SERVER['REMOTE_ADDR'] );
	if ( '' === $remote ) {
		return true;
	}

	// 直连方仍是 CF 边缘 ⇒ 归一没做成 ⇒ 不能按 IP 计数。
	return ! sf_real_ip_is_cloudflare( $remote );
}

/**
 * @param int $max     插件默认值。
 * @param int $form_id 表单 id。
 * @return int
 */
function sf_fg_filter_max_submissions( $max, $form_id = 0 ) {
	if ( ! sf_fg_enabled() || ! sf_fg_real_ip_ready() ) {
		return $max;
	}

	return (int) apply_filters( 'sf_fg_max_submissions', SF_FG_MAX_SUBMISSIONS, $form_id );
}
add_filter( 'fluentform/max_submission_count', 'sf_fg_filter_max_submissions', 10, 2 );

/**
 * @param int $interval 插件默认窗口（秒）。
 * @param int $form_id  表单 id。
 * @return int
 */
function sf_fg_filter_min_interval( $interval, $form_id = 0 ) {
	if ( ! sf_fg_enabled() || ! sf_fg_real_ip_ready() ) {
		return $interval;
	}

	return (int) apply_filters( 'sf_fg_min_submission_interval', SF_FG_MIN_INTERVAL, $form_id );
}
add_filter( 'fluentform/min_submission_interval', 'sf_fg_filter_min_interval', 10, 2 );

/* -------------------------------------------------------------------------
 * §2  字段解析 —— 按 element 类型与 label 语义定位，不写死字段名
 * ---------------------------------------------------------------------- */

/**
 * 读取表单的字段定义。
 *
 * Fluent Forms 把字段存在 `{prefix}fluentform_forms.form_fields` 的
 * `{"fields":{"1":{...}}}` 结构里（不在 form_meta）。直接查列，避免依赖插件内部 API。
 *
 * @param int $form_id 表单 id。
 * @return array<string,array> 以 index 为键的字段定义。
 */
function sf_fg_form_fields( $form_id ) {
	global $wpdb;

	$table = $wpdb->prefix . 'fluentform_forms';
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 只读单列，表名来自 $wpdb->prefix。
	$raw = $wpdb->get_var( $wpdb->prepare( "SELECT form_fields FROM {$table} WHERE id = %d", (int) $form_id ) );
	if ( is_string( $raw ) ) {
		$raw = json_decode( $raw, true );
	}
	if ( ! is_array( $raw ) ) {
		return array();
	}

	$fields = ( isset( $raw['fields'] ) && is_array( $raw['fields'] ) ) ? $raw['fields'] : $raw;

	return apply_filters( 'sf_fg_form_fields', $fields, $form_id );
}

/**
 * 把「语义角色」映射到该表单的字段 name。
 *
 * 角色 → 判定依据（全部是类型或 label 语义，与具体机器人的字符串无关）：
 *   email   ← element = input_email
 *   message ← element = textarea
 *   country ← element ∈ {select, country, input_country} 且 label 含 countr/国家
 *   company ← element = input_text 且 label 含 compan/organi/business/firm
 *   contact ← element = input_text 且 label 含 contact/person/name/nom/nombre
 *
 * 匹配不到的角色留空字符串，对应信号自然不参与评分。
 *
 * @param int $form_id 表单 id。
 * @return array{company:string,contact:string,email:string,country:string,message:string}
 */
function sf_fg_field_map( $form_id ) {
	$map = array(
		'company' => '',
		'contact' => '',
		'email'   => '',
		'country' => '',
		'message' => '',
	);

	foreach ( sf_fg_form_fields( $form_id ) as $field ) {
		if ( ! is_array( $field ) ) {
			continue;
		}
		$element = isset( $field['element'] ) ? (string) $field['element'] : '';
		$attrs   = ( isset( $field['attributes'] ) && is_array( $field['attributes'] ) ) ? $field['attributes'] : array();
		$name    = isset( $attrs['name'] ) ? (string) $attrs['name'] : '';
		$label   = '';
		if ( isset( $field['settings']['label'] ) ) {
			$label = (string) $field['settings']['label'];
		}
		if ( '' === $name ) {
			continue;
		}

		if ( '' === $map['email'] && 'input_email' === $element ) {
			$map['email'] = $name;
			continue;
		}
		if ( '' === $map['message'] && 'textarea' === $element ) {
			$map['message'] = $name;
			continue;
		}
		if ( '' === $map['country']
			&& in_array( $element, array( 'select', 'country', 'input_country' ), true )
			&& preg_match( '/countr|国家|pa[ií]s|land|paese/i', $label )
		) {
			$map['country'] = $name;
			continue;
		}
		if ( 'input_text' === $element ) {
			if ( '' === $map['company'] && preg_match( '/compan|organi|business|firm|entreprise|empresa/i', $label ) ) {
				$map['company'] = $name;
				continue;
			}
			if ( '' === $map['contact'] && preg_match( '/contact|person|name|nom|nombre/i', $label ) ) {
				$map['contact'] = $name;
				continue;
			}
		}
	}

	return apply_filters( 'sf_fg_field_map', $map, $form_id );
}

/* -------------------------------------------------------------------------
 * §3  五路弱信号 —— 每一个都是纯函数，便于门做表驱动断言
 * ---------------------------------------------------------------------- */

/**
 * 归一化：小写、折平空白、去掉首尾标点。
 *
 * @param mixed $value 原值。
 * @return string
 */
function sf_fg_norm( $value ) {
	if ( is_array( $value ) ) {
		$value = implode( ' ', array_filter( array_map( 'strval', $value ) ) );
	}
	$value = is_string( $value ) ? $value : '';
	$value = strtolower( trim( $value ) );
	$value = preg_replace( '/\s+/u', ' ', $value );

	return is_string( $value ) ? trim( $value, " \t\n\r\0\x0B.,;:!?-\"'()[]{}" ) : '';
}

/**
 * 最长公共**连续字母**子串长度（只比较字母，避免数字/符号造成的巧合）。
 *
 * @param string $a 已归一化的字符串。
 * @param string $b 已归一化的字符串。
 * @return string 最长公共子串原文。
 */
function sf_fg_longest_common_alpha( $a, $b ) {
	$best = '';
	$len_a = strlen( $a );
	$len_b = strlen( $b );
	if ( 0 === $len_a || 0 === $len_b ) {
		return '';
	}

	$prev = array_fill( 0, $len_b + 1, 0 );
	for ( $i = 1; $i <= $len_a; $i++ ) {
		$curr = array_fill( 0, $len_b + 1, 0 );
		for ( $j = 1; $j <= $len_b; $j++ ) {
			if ( $a[ $i - 1 ] === $b[ $j - 1 ] && ctype_alpha( $a[ $i - 1 ] ) ) {
				$curr[ $j ] = $prev[ $j - 1 ] + 1;
				if ( $curr[ $j ] > strlen( $best ) ) {
					$best = substr( $a, $i - $curr[ $j ], $curr[ $j ] );
				}
			}
		}
		$prev = $curr;
	}

	return $best;
}

/**
 * 行业通用词 —— 这些片段出现在公司名里是正常的，不能算"共享片段"。
 *
 * 注意：这是**业务词汇表**，不是机器人特征名单。它也用于压制
 * "ABC Pet" / "John Pet" 这类巧合。
 *
 * @return string[]
 */
function sf_fg_generic_words() {
	return apply_filters(
		'sf_fg_generic_words',
		array(
			'inc', 'ltd', 'llc', 'corp', 'co', 'company', 'group', 'holding', 'holdings',
			'gmbh', 'srl', 'spa', 'bv', 'nv', 'sa', 'sas', 'sarl', 'ab', 'as', 'oy', 'ag',
			'pte', 'plc', 'limited', 'international', 'global', 'trading', 'trade',
			'import', 'export', 'industries', 'industry', 'enterprise', 'enterprises',
			'tech', 'technology', 'technologies', 'solutions', 'solution', 'services',
			'service', 'supply', 'supplies', 'supplier', 'distribution', 'distributor',
			'products', 'product', 'brands', 'brand', 'store', 'shop', 'market', 'markets',
			'pet', 'pets', 'animal', 'animals', 'food', 'foods', 'feed', 'nutrition',
			'health', 'healthcare', 'care', 'pharma', 'pharmaceutical', 'biotech', 'life',
			'science', 'sciences', 'laboratory', 'laboratories', 'labs', 'lab',
		)
	);
}

/**
 * S1 —— 公司名与**联系人共享公司名的后缀片段**（+3；片段不在公司名尾部则降为 +1）。
 *
 * 本批形态：公司名 RobertTon / 联系人 ElijahTonGM ⇒ 公司名以 "Ton" 结尾，且该
 * 片段出现在联系人里。这是「同一台机器在两个字段上用了同一个词根」的表现。
 *
 * 为什么分两档：真人企业也会用姓氏命名公司（"Nordic Pet AB" / "Anna Nordic"），
 * 但那种情况下共享片段出现在公司名的**开头**而不是尾部。只有「公司名以该片段
 * 结尾」才升为 3 分，其余降为弱信号 1 分 —— 这样家族企业不会被单独成案。
 *
 * @param string $company 公司名。
 * @param string $contact 联系人。
 * @return int 0（不命中）/ 1（弱）/ 3（强）
 */
function sf_fg_signal_shared_fragment( $company, $contact ) {
	$company = sf_fg_norm( $company );
	$contact = sf_fg_norm( $contact );
	if ( strlen( $company ) < SF_FG_MIN_FRAGMENT || strlen( $contact ) < SF_FG_MIN_FRAGMENT ) {
		return 0;
	}

	$fragment = sf_fg_longest_common_alpha( $company, $contact );
	if ( strlen( $fragment ) < SF_FG_MIN_FRAGMENT ) {
		return 0;
	}

	// 命中的片段含行业通用词 ⇒ 视为巧合（"Nordic Pet" / "Anna Pet"）。
	foreach ( sf_fg_generic_words() as $word ) {
		if ( '' !== $word && false !== strpos( $fragment, $word ) ) {
			return 0;
		}
	}

	// 公司名以该片段结尾 ⇒ 强信号。
	return ( substr( $company, -strlen( $fragment ) ) === $fragment ) ? 3 : 1;
}

/**
 * 「价格」语义词（多语种）。
 *
 * 这是**语言词典**，不是机器人特征名单 —— 每个词都是该语言里「价格 / 报价」的
 * 常用说法，单独出现毫无意义（真客户也会问价），只有与「无任何具体采购特征」
 * 组合时才构成 S2。词表按语言整理，覆盖本批观察到语种所用的词形，也覆盖我们
 * 目标市场的语言。
 *
 * @return array{latin:string[],other:string[]}
 */
function sf_fg_price_words() {
	return apply_filters(
		'sf_fg_price_words',
		array(
			// 拉丁字母语言 —— 用词边界匹配，避免 "prettiest" 命中 "pret"。
			'latin' => array(
				// 英德荷
				'price', 'prices', 'pricing', 'price list', 'pricelist', 'quotation', 'quote',
				'preis', 'preise', 'preisliste', 'prijs', 'prijslijst',
				// 罗曼语族
				'prix', 'precio', 'precios', 'prezzo', 'prezzi', 'preco', 'preço', 'precos',
				'preços', 'prezo', 'pret', 'preturi', 'preț', 'prezioa', 'çmimi',
				// 北欧 / 日耳曼小语种
				'pris', 'prislista', 'hinta', 'hinnasto', 'verð', 'verdt', 'präis', 'priis',
				// 斯拉夫 / 中欧
				'cena', 'ceny', 'cenik', 'cennik', 'cijena', 'цена', 'цены', 'ціна', 'цен',
				'прайс', 'стоимость', 'стоимость', 'ára', 'ár', 'árlista',
				// 其他
				'praghas', 'intengo', 'hind', 'harga', 'gia', 'giá', 'timi', 'τιμή', 'arvo',
				'cost', 'pretium',
			),
			// 非拉丁文字 —— 直接包含匹配。
			'other' => array(
				'цена', 'цената', 'цену', 'ціна', 'стоимость', 'прайс',
				'価格', '値段', '見積', '报价', '報價', '价格', '價格',
				'가격', '견적', 'ราคา', 'ລາຄາ',
				'قیمت', 'قيمة', 'السعر', 'מחיר', 'τιμή',
				'ფასი', 'মূল্য', 'দাম', 'daim',
			),
		)
	);
}

/**
 * 真客户会提到、机器人模板不会提到的**具体采购特征词**。
 *
 * 任一命中 ⇒ 立刻放弃 S2。这是「宁可漏放不可误杀」的具体落实：
 * 只要留言里出现任何具体信息，就当成真人对待。
 *
 * @return string[]
 */
function sf_fg_specificity_words() {
	return apply_filters(
		'sf_fg_specificity_words',
		array(
			'moq', 'minimum order', 'sample', 'sampling', 'kg', 'kilogram', 'gram', 'mg',
			'ton', 'tonne', 'lb', 'container', 'carton', 'pallet', 'pack', 'package',
			'packaging', 'bottle', 'jar', 'pouch', 'sachet', 'blister', 'tube',
			'tablet', 'chew', 'powder', 'liquid', 'drop', 'paste', 'capsule', 'gummy',
			'oem', 'odm', 'private label', 'white label', 'contract manufactur',
			'specification', 'spec sheet', 'coa', 'msds', 'iso', 'gmp', 'haccp',
			'certificate', 'certification', 'formula', 'ingredient', 'flavor', 'flavour',
			'quantity', 'qty', 'unit', 'units', 'batch', 'lead time', 'delivery',
			'shipment', 'shipping', 'port', 'fob', 'cif', 'exw', 'invoice', 'payment term',
			'factory', 'production line', 'capacity', 'we are', 'we would like', 'we need',
			'we want', 'we plan', 'looking for', 'interested in', 'please send', 'send me',
			'attached', 'our company', 'our brand', 'our product', 'our market',
		)
	);
}

/**
 * S2 —— 短句价格追问模板（+1）。
 *
 * 判据（三者同时成立）：
 *   ① 长度 ≤ 120 字符（模板句都很短）
 *   ② 含「价格」语义的多语种词
 *   ③ 不含任何具体采购特征词
 *
 * 单独命中只有 1 分，无法成案；与 S1/S3 组合时才产生意义。
 *
 * @param string $message 留言原文。
 * @return bool
 */
function sf_fg_signal_template_message( $message ) {
	$text = sf_fg_norm( $message );
	if ( '' === $text ) {
		return false;
	}
	if ( function_exists( 'mb_strlen' ) ? mb_strlen( $text ) > 120 : strlen( $text ) > 240 ) {
		return false;
	}

	foreach ( sf_fg_specificity_words() as $word ) {
		if ( '' !== $word && false !== strpos( $text, $word ) ) {
			return false;
		}
	}

	$words = sf_fg_price_words();
	foreach ( $words['latin'] as $word ) {
		if ( preg_match( '/\b' . preg_quote( $word, '/' ) . '\b/u', $text ) ) {
			return true;
		}
	}
	foreach ( $words['other'] as $word ) {
		if ( '' !== $word && false !== strpos( $text, $word ) ) {
			return true;
		}
	}

	return false;
}

/**
 * S2b —— 极短、无数字、无采购特征的留言（+1，语言无关）。
 *
 * 为什么要它：价格词表再全也穷举不了所有语种（本批出现 30+ 种机翻语言）。
 * 换一个不依赖语言的角度 —— **真客户几乎总会在留言里给一个具体信息**
 * （数量、规格、型号、剂型、合作方式），至少会给个数字；而群发模板是一句
 * 空泛的问候 + 一个诉求，短且干净。
 *
 * 单独命中只有 1 分，无法成案；它存在的意义是与 S1 / S3 / S4 叠加。
 *
 * @param string $message 留言原文。
 * @return bool
 */
function sf_fg_signal_short_message( $message ) {
	$text = sf_fg_norm( $message );
	if ( '' === $text ) {
		return false;
	}
	$length = function_exists( 'mb_strlen' ) ? mb_strlen( $text ) : strlen( $text );
	if ( $length > 60 ) {
		return false;
	}
	if ( preg_match( '/\d/u', $text ) ) {
		return false; // 有数字 ⇒ 很可能在讲数量/规格 ⇒ 放行。
	}
	foreach ( sf_fg_specificity_words() as $word ) {
		if ( '' !== $word && false !== strpos( $text, $word ) ) {
			return false;
		}
	}

	return true;
}

/**
 * 国家名 → ISO-3166 alpha-2（业务相关国别的保守子集）。
 *
 * 只覆盖我们实际做生意的地区；不在表内的国家**返回空串 ⇒ S3 不参与评分**，
 * 这是刻意的保守：宁可漏判，不要因为不认识一个国家名而把真客户算成垃圾。
 *
 * @return array<string,string>
 */
function sf_fg_country_codes() {
	return apply_filters(
		'sf_fg_country_codes',
		array(
			'germany' => 'DE', 'deutschland' => 'DE', 'italy' => 'IT', 'italia' => 'IT',
			'spain' => 'ES', 'espana' => 'ES', 'españa' => 'ES', 'france' => 'FR',
			'netherlands' => 'NL', 'belgium' => 'BE', 'austria' => 'AT', 'switzerland' => 'CH',
			'poland' => 'PL', 'portugal' => 'PT', 'sweden' => 'SE', 'norway' => 'NO',
			'denmark' => 'DK', 'finland' => 'FI', 'ireland' => 'IE', 'greece' => 'GR',
			'czech republic' => 'CZ', 'czechia' => 'CZ', 'hungary' => 'HU', 'romania' => 'RO',
			'bulgaria' => 'BG', 'croatia' => 'HR', 'slovakia' => 'SK', 'slovenia' => 'SI',
			'lithuania' => 'LT', 'latvia' => 'LV', 'estonia' => 'EE', 'ukraine' => 'UA',
			'russia' => 'RU', 'turkey' => 'TR', 'united kingdom' => 'GB', 'uk' => 'GB',
			'england' => 'GB', 'scotland' => 'GB', 'ireland' => 'IE',
			'united states' => 'US', 'usa' => 'US', 'canada' => 'CA', 'mexico' => 'MX',
			'brazil' => 'BR', 'argentina' => 'AR', 'chile' => 'CL', 'colombia' => 'CO',
			'peru' => 'PE', 'australia' => 'AU', 'new zealand' => 'NZ', 'japan' => 'JP',
			'south korea' => 'KR', 'korea' => 'KR', 'china' => 'CN', 'india' => 'IN',
			'indonesia' => 'ID', 'malaysia' => 'MY', 'singapore' => 'SG', 'thailand' => 'TH',
			'vietnam' => 'VN', 'philippines' => 'PH', 'south africa' => 'ZA',
			'united arab emirates' => 'AE', 'uae' => 'AE', 'saudi arabia' => 'SA',
			'israel' => 'IL', 'egypt' => 'EG', 'morocco' => 'MA', 'pakistan' => 'PK',
			'bangladesh' => 'BD', 'sri lanka' => 'LK', 'nigeria' => 'NG', 'kenya' => 'KE',
		)
	);
}

/**
 * 通用 / 超国家顶级域 —— 不携带国别信息，遇到就放弃 S3。
 *
 * @return string[]
 */
function sf_fg_generic_tlds() {
	return apply_filters(
		'sf_fg_generic_tlds',
		array(
			'com', 'net', 'org', 'info', 'biz', 'name', 'pro', 'mobi', 'email', 'mail',
			'io', 'co', 'ai', 'app', 'dev', 'cloud', 'site', 'online', 'shop', 'store',
			'tech', 'xyz', 'top', 'club', 'space', 'website', 'digital', 'agency',
			'group', 'world', 'zone', 'live', 'life', 'team', 'works', 'solutions',
			'eu', 'asia', 'int', 'edu', 'gov', 'mil', 'aero', 'coop', 'museum',
		)
	);
}

/**
 * 取邮箱域名（小写）。非法输入返回空串。
 *
 * @param string $email 邮箱。
 * @return string
 */
function sf_fg_email_domain( $email ) {
	$email = is_string( $email ) ? trim( $email ) : '';
	if ( '' === $email || false === strpos( $email, '@' ) ) {
		return '';
	}
	$domain = strtolower( substr( strrchr( $email, '@' ), 1 ) );
	$domain = trim( $domain, " \t\n\r\0\x0B." );

	return ( '' !== $domain && false !== strpos( $domain, '.' ) ) ? $domain : '';
}

/**
 * S3 —— 申报国家与邮箱域/TLD 不一致（+1）。
 *
 * 只在两边都能确定国别、且**确定冲突**时才计分：
 *   Germany + @x.de    ⇒ 一致，不判
 *   Germany + @gmail.com ⇒ 通用域，不判
 *   Germany + @x.it    ⇒ 冲突，+1
 *   Germany + @dshs.wa.gov ⇒ gov（US 州政府域）与 DE 冲突，+1
 *
 * @param string $country 申报国家名。
 * @param string $email   邮箱。
 * @return bool
 */
function sf_fg_signal_country_mismatch( $country, $email ) {
	$codes = sf_fg_country_codes();
	$key   = sf_fg_norm( $country );
	if ( '' === $key || ! isset( $codes[ $key ] ) ) {
		return false;
	}
	$declared = $codes[ $key ];

	$domain = sf_fg_email_domain( $email );
	if ( '' === $domain ) {
		return false;
	}
	$parts = explode( '.', $domain );
	$tld   = (string) end( $parts );
	if ( '' === $tld ) {
		return false;
	}

	if ( in_array( $tld, sf_fg_generic_tlds(), true ) ) {
		// gov / edu / mil 带国别含义：.gov 视为 US 政府域。
		if ( 'gov' === $tld || 'mil' === $tld ) {
			return 'US' !== $declared;
		}
		return false;
	}

	if ( 2 === strlen( $tld ) ) {
		return strtoupper( $tld ) !== $declared;
	}

	return false;
}

/**
 * S4 —— User-Agent 被恶意软件套壳、或版本严重滞后（+1）。
 *
 * 两类形态都只作弱信号：老旧的办公电脑可能真的停在很久以前的版本，
 * 单凭 UA 判垃圾会误伤真实设备。
 *
 * @param string $ua User-Agent。
 * @return bool
 */
function sf_fg_signal_stale_ua( $ua ) {
	$ua = is_string( $ua ) ? $ua : '';
	if ( '' === $ua ) {
		return false;
	}

	// 被恶意软件复制的真实用户 UA 常带这些安全软件后缀。
	if ( preg_match( '/\b(avast|avg|ccleaner|comodo|bitdefender|kaspersky)\//i', $ua ) ) {
		return true;
	}

	// 主版本严重滞后 + 声明 Windows 10。
	if ( preg_match( '#(?:chrome|edg|edgA|crios)/(\d+)#i', $ua, $m ) ) {
		if ( (int) $m[1] > 0 && (int) $m[1] < SF_FG_STALE_MAJOR && false !== stripos( $ua, 'windows nt 10.0' ) ) {
			return true;
		}
	}

	return false;
}

/**
 * 一次性 / 临时邮箱域（通用清单，非本批专属）。
 *
 * @return string[]
 */
function sf_fg_disposable_domains() {
	return apply_filters(
		'sf_fg_disposable_domains',
		array(
			'mailinator.com', 'guerrillamail.com', 'guerrillamail.net', 'sharklasers.com',
			'10minutemail.com', '10minutemail.net', 'temp-mail.org', 'tempmail.com',
			'tempmail.net', 'tempr.email', 'yopmail.com', 'yopmail.fr', 'trashmail.com',
			'trashmail.net', 'dispostable.com', 'maildrop.cc', 'getnada.com',
			'throwawaymail.com', 'fakeinbox.com', 'mailnesia.com', 'mintemail.com',
			'spam4.me', 'mytrashmail.com', 'mailcatch.com', 'discard.email',
			'emailondeck.com', 'moakt.com', 'tempmailo.com', '1secmail.com',
			'1secmail.net', '1secmail.org', 'mailtemp.info', 'email-temp.com',
			'linshiyouxiang.net', 'mailbox52.ga', 'byom.de', 'gmail.com.de',
		)
	);
}

/**
 * S5 —— 一次性邮箱域（+1）。
 *
 * @param string $email 邮箱。
 * @return bool
 */
function sf_fg_signal_disposable_email( $email ) {
	$domain = sf_fg_email_domain( $email );

	return ( '' !== $domain && in_array( $domain, sf_fg_disposable_domains(), true ) );
}

/**
 * 计时字段名（服务端渲染、HMAC 签名）。
 *
 * @return string
 */
function sf_fg_time_field() {
	return (string) apply_filters( 'sf_fg_time_field', 'sf_fg_t' );
}

/**
 * 生成签名后的计时值：`<秒级时间戳>.<hmac>`。
 *
 * HTML 可能被边缘/页面缓存，值可能陈旧 —— 陈旧只会让时间差更大（更容易通过），
 * 不会误伤，这是刻意的取舍。
 *
 * @param int|null $timestamp 指定时间戳，默认当前。
 * @return string
 */
function sf_fg_time_token( $timestamp = null ) {
	$ts = null === $timestamp ? time() : (int) $timestamp;

	return $ts . '.' . hash_hmac( 'sha256', (string) $ts, wp_salt( 'nonce' ) );
}

/**
 * 校验计时值，返回「填写耗时（秒）」；无法信任时返回 null。
 *
 * @param string $token 计时值。
 * @return int|null
 */
function sf_fg_time_elapsed( $token ) {
	$token = is_string( $token ) ? trim( $token ) : '';
	if ( '' === $token || false === strpos( $token, '.' ) ) {
		return null;
	}
	list( $ts, $sig ) = explode( '.', $token, 2 );
	if ( ! ctype_digit( $ts ) || '' === $sig ) {
		return null;
	}
	$expect = hash_hmac( 'sha256', $ts, wp_salt( 'nonce' ) );
	if ( ! hash_equals( $expect, $sig ) ) {
		return null; // 签名不对 ⇒ 伪造或被缓存改写 ⇒ 不参与判定。
	}
	$elapsed = time() - (int) $ts;

	return $elapsed >= 0 ? $elapsed : null;
}

/**
 * S6 —— 提交过快（+2）。
 *
 * 只在计时字段**存在且签名有效**时才计分：字段缺失（无 JS、被缓存剥离）一律
 * 不加分，避免把正常客户算成垃圾。
 *
 * @param string $token 计时值。
 * @return bool
 */
function sf_fg_signal_too_fast( $token ) {
	$elapsed = sf_fg_time_elapsed( $token );
	if ( null === $elapsed ) {
		return false;
	}

	return $elapsed < SF_FG_MIN_FILL_SECONDS;
}

/**
 * S7 —— Turnstile 状态对应的分值（纯函数，便于门做表驱动断言）。
 *
 *   带了 token 但校验不通过（fail）  +4  足以单独成案
 *   其余（absent / ok / degraded / disabled）  0
 *
 * 「未带 token」一律 0 分：访客侧脚本没加载出来（真实降级场景）与机器人不跑 JS
 * 在服务端无法区分，而前者绝不能连累真客户。降级时由 S1/S2/S3/S4/S5/S6 兜底。
 *
 * @param string $state 状态。
 * @return int
 */
function sf_fg_signal_turnstile( $state ) {
	return ( 'fail' === $state ) ? 4 : 0;
}

/**
 * 综合评分。
 *
 * @param int    $form_id 表单 id。
 * @param array  $data    已解析的提交字段。
 * @param string $ua      User-Agent。
 * @return array{score:int,signals:string[],values:array<string,string>,map:array<string,string>}
 */
function sf_fg_score( $form_id, $data, $ua = '', $ts_state = 'disabled' ) {
	$map   = sf_fg_field_map( $form_id );
	$value = function ( $role ) use ( $map, $data ) {
		$name = isset( $map[ $role ] ) ? $map[ $role ] : '';
		if ( '' === $name || ! isset( $data[ $name ] ) ) {
			return '';
		}
		$raw = $data[ $name ];

		return is_array( $raw ) ? implode( ' ', array_map( 'strval', $raw ) ) : (string) $raw;
	};

	$company = $value( 'company' );
	$contact = $value( 'contact' );
	$email   = $value( 'email' );
	$country = $value( 'country' );
	$message = $value( 'message' );
	$token   = isset( $data[ sf_fg_time_field() ] ) ? (string) $data[ sf_fg_time_field() ] : '';

	$score   = 0;
	$signals = array();

	$s1 = sf_fg_signal_shared_fragment( $company, $contact );
	if ( $s1 > 0 ) {
		$score += $s1;
		$signals[] = ( 3 === $s1 ) ? 'S1_shared_suffix' : 'S1_shared_fragment';
	}
	if ( sf_fg_signal_template_message( $message ) ) {
		$score += 1;
		$signals[] = 'S2_template_message';
	}
	if ( sf_fg_signal_short_message( $message ) ) {
		$score += 1;
		$signals[] = 'S2b_short_message';
	}
	if ( sf_fg_signal_country_mismatch( $country, $email ) ) {
		$score += 1;
		$signals[] = 'S3_country_mismatch';
	}
	// S4 只记录、不计分：方案 §四 明确「UA 陈旧即拒收」会误伤老旧设备与企业代理，
	// 本信号仅供人工复核时参考，永不单独或参与成案。
	if ( sf_fg_signal_stale_ua( $ua ) ) {
		$signals[] = 'S4_note_stale_ua';
	}
	if ( sf_fg_signal_disposable_email( $email ) ) {
		$score += 1;
		$signals[] = 'S5_disposable_email';
	}
	if ( sf_fg_signal_too_fast( $token ) ) {
		$score += 2;
		$signals[] = 'S6_too_fast';
	}
	$ts_points = sf_fg_signal_turnstile( $ts_state );
	if ( $ts_points > 0 ) {
		$score += $ts_points;
		$signals[] = 'S7_turnstile_failed';
	}

	return array(
		'score'   => $score,
		'signals' => $signals,
		'values'  => array(
			'company' => $company,
			'contact' => $contact,
			'email'   => $email,
			'country' => $country,
			'message' => $message,
		),
		'map'     => $map,
	);
}

/* -------------------------------------------------------------------------
 * §4  黑名单（IP / 邮箱域 / 内容签名）
 * ---------------------------------------------------------------------- */

/**
 * 全部黑名单条目。
 *
 * @return array<int,array{type:string,value:string,added:string,note:string}>
 */
function sf_fg_blocklist() {
	$list = get_option( SF_FG_BLOCKLIST_OPT, array() );
	if ( ! is_array( $list ) ) {
		return array();
	}

	return array_values( array_filter( $list, 'is_array' ) );
}

/**
 * 是否命中黑名单，返回命中项的 type（'' = 未命中）。
 *
 * @param string $ip        访客真实 IP。
 * @param string $domain    邮箱域。
 * @param string $signature 内容签名。
 * @return string
 */
function sf_fg_blocklist_hit( $ip, $domain, $signature ) {
	foreach ( sf_fg_blocklist() as $entry ) {
		$type  = isset( $entry['type'] ) ? (string) $entry['type'] : '';
		$value = isset( $entry['value'] ) ? (string) $entry['value'] : '';
		if ( '' === $value ) {
			continue;
		}
		if ( 'ip' === $type && '' !== $ip && $ip === $value ) {
			return 'ip';
		}
		if ( 'domain' === $type && '' !== $domain && $domain === $value ) {
			return 'domain';
		}
		if ( 'signature' === $type && '' !== $signature && $signature === $value ) {
			return 'signature';
		}
	}

	return '';
}

/**
 * 加入黑名单（幂等）。
 *
 * @param string $type  ip|domain|signature
 * @param string $value 值。
 * @param string $note  备注。
 * @return bool
 */
function sf_fg_blocklist_add( $type, $value, $note = '' ) {
	$type  = (string) $type;
	$value = trim( (string) $value );
	if ( ! in_array( $type, array( 'ip', 'domain', 'signature' ), true ) || '' === $value ) {
		return false;
	}

	$list = sf_fg_blocklist();
	foreach ( $list as $entry ) {
		if ( isset( $entry['type'], $entry['value'] ) && $entry['type'] === $type && $entry['value'] === $value ) {
			return true; // 已存在。
		}
	}

	$list[] = array(
		'type'  => $type,
		'value' => $value,
		'added' => current_time( 'mysql' ),
		'note'  => (string) $note,
	);

	return (bool) update_option( SF_FG_BLOCKLIST_OPT, $list, false );
}

/**
 * 移除黑名单条目。
 *
 * @param int $index 序号。
 * @return bool
 */
function sf_fg_blocklist_remove( $index ) {
	$list = sf_fg_blocklist();
	$index = (int) $index;
	if ( ! isset( $list[ $index ] ) ) {
		return false;
	}
	unset( $list[ $index ] );

	return (bool) update_option( SF_FG_BLOCKLIST_OPT, array_values( $list ), false );
}

/* -------------------------------------------------------------------------
 * §5  审计日志表
 * ---------------------------------------------------------------------- */

/**
 * 建表（幂等，dbDelta）+ 版本标记。
 *
 * @return void
 */
function sf_fg_maybe_install() {
	if ( get_option( 'sf_fg_db_version' ) === SF_FG_DB_VERSION ) {
		return;
	}

	global $wpdb;
	require_once ABSPATH . 'wp-admin/includes/upgrade.php';

	$table   = $wpdb->prefix . SF_FG_LOG_TABLE;
	$collate = $wpdb->get_charset_collate();

	$sql = "CREATE TABLE {$table} (
		id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
		form_id int(10) unsigned NOT NULL DEFAULT 0,
		submission_id bigint(20) unsigned NOT NULL DEFAULT 0,
		created_at datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
		ip varchar(45) NOT NULL DEFAULT '',
		edge_ip varchar(45) NOT NULL DEFAULT '',
		ua varchar(191) NOT NULL DEFAULT '',
		country varchar(16) NOT NULL DEFAULT '',
		email_domain varchar(120) NOT NULL DEFAULT '',
		score smallint(5) NOT NULL DEFAULT 0,
		signals varchar(191) NOT NULL DEFAULT '',
		signature char(64) NOT NULL DEFAULT '',
		source varchar(32) NOT NULL DEFAULT '',
		released tinyint(1) NOT NULL DEFAULT 0,
		released_at datetime NULL DEFAULT NULL,
		PRIMARY KEY  (id),
		KEY form_id (form_id),
		KEY created_at (created_at),
		KEY ip (ip),
		KEY signature (signature)
	) {$collate};";

	dbDelta( $sql );

	update_option( 'sf_fg_db_version', SF_FG_DB_VERSION, false );
}
add_action( 'admin_init', 'sf_fg_maybe_install' );

/**
 * 内容签名 —— 用于把同一台机器人的不同马甲聚成一簇（分析演化用）。
 *
 * @param array $values score() 返回的 values。
 * @return string
 */
function sf_fg_signature( $values ) {
	$parts = array(
		sf_fg_norm( isset( $values['company'] ) ? $values['company'] : '' ),
		sf_fg_norm( isset( $values['contact'] ) ? $values['contact'] : '' ),
		sf_fg_norm( isset( $values['message'] ) ? $values['message'] : '' ),
	);

	return hash( 'sha256', implode( '|', $parts ) );
}

/**
 * 写入一条审计记录。
 *
 * @param array $row 字段。
 * @return int 日志行 id。
 */
function sf_fg_log_row( $row ) {
	sf_fg_maybe_install(); // 惰性建表：前台首次触发时也能落盘。

	global $wpdb;
	$table = $wpdb->prefix . SF_FG_LOG_TABLE;

	$data = array(
		'form_id'       => (int) ( isset( $row['form_id'] ) ? $row['form_id'] : 0 ),
		'submission_id' => (int) ( isset( $row['submission_id'] ) ? $row['submission_id'] : 0 ),
		'created_at'    => current_time( 'mysql' ),
		'ip'            => substr( (string) ( isset( $row['ip'] ) ? $row['ip'] : '' ), 0, 45 ),
		'edge_ip'       => substr( (string) ( isset( $row['edge_ip'] ) ? $row['edge_ip'] : '' ), 0, 45 ),
		'ua'            => substr( (string) ( isset( $row['ua'] ) ? $row['ua'] : '' ), 0, 191 ),
		'country'       => substr( (string) ( isset( $row['country'] ) ? $row['country'] : '' ), 0, 16 ),
		'email_domain'  => substr( (string) ( isset( $row['email_domain'] ) ? $row['email_domain'] : '' ), 0, 120 ),
		'score'         => (int) ( isset( $row['score'] ) ? $row['score'] : 0 ),
		'signals'       => substr( (string) ( isset( $row['signals'] ) ? $row['signals'] : '' ), 0, 191 ),
		'signature'     => substr( (string) ( isset( $row['signature'] ) ? $row['signature'] : '' ), 0, 64 ),
		'source'        => substr( (string) ( isset( $row['source'] ) ? $row['source'] : '' ), 0, 32 ),
	);

	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表，无核心 API 可用。
	$wpdb->insert( $table, $data );

	return (int) $wpdb->insert_id;
}

/* -------------------------------------------------------------------------
 * §6  告警（当日垃圾数达阈值 ⇒ 每天最多一封）
 * ---------------------------------------------------------------------- */

/**
 * 当天已拦截计数自增，必要时发一封告警。
 *
 * @return void
 */
function sf_fg_alert_tick() {
	$today = wp_date( 'Y-m-d' );
	$state = get_option( SF_FG_ALERT_OPT, array() );
	if ( ! is_array( $state ) || ! isset( $state['date'] ) || $state['date'] !== $today ) {
		$state = array(
			'date'  => $today,
			'count' => 0,
			'sent'  => false,
		);
	}

	$state['count'] = (int) ( isset( $state['count'] ) ? $state['count'] : 0 ) + 1;

	$threshold = (int) apply_filters( 'sf_fg_alert_threshold', SF_FG_ALERT_THRESHOLD );
	$should_send = ( $state['count'] >= $threshold && empty( $state['sent'] ) );

	if ( $should_send ) {
		$state['sent'] = true; // 先标记后发送，避免并发下重复发信。
	}
	update_option( SF_FG_ALERT_OPT, $state, false );

	if ( $should_send ) {
		sf_fg_send_alert( $state['count'] );
	}
}

/**
 * 发送告警邮件。
 *
 * @param int $count 当日累计。
 * @return bool
 */
function sf_fg_send_alert( $count ) {
	$recipients = apply_filters( 'sf_fg_alert_recipients', array( 'sales@zxpet.com' ) );
	$recipients = array_values( array_filter( array_map( 'sanitize_email', (array) $recipients ) ) );
	if ( ! $recipients ) {
		return false;
	}

	$host    = wp_parse_url( home_url(), PHP_URL_HOST );
	$subject = sprintf( '[%s] 表单垃圾告警：当日已拦截 %d 条', $host, (int) $count );

	$lines = array(
		sprintf( '站点：%s', home_url( '/' ) ),
		sprintf( '日期：%s', wp_date( 'Y-m-d' ) ),
		sprintf( '当日已拦截：%d 条（阈值 %d）', (int) $count, (int) apply_filters( 'sf_fg_alert_threshold', SF_FG_ALERT_THRESHOLD ) ),
		'',
		'本邮件每天最多一封。明细见后台「表单防护」页：',
		admin_url( 'admin.php?page=sf-form-guard' ),
	);

	return (bool) wp_mail( $recipients, $subject, implode( "\n", $lines ) );
}

/* -------------------------------------------------------------------------
 * §7  拦截器 —— 在 Fluent Forms 的处理流程之前接管
 *
 * 真实入口是 wp_ajax(_nopriv)_fluentform_submit（FormHandler::onSubmit 已被插件
 * 注释掉，见 app/Hooks/Ajax.php:22）。我们以更早的优先级挂同一 action：
 *   · 判定为垃圾 ⇒ 落库（status=spam）+ 写审计表 + 计数告警 + 输出「成功」并结束请求
 *     ⇒ Fluent Forms 的通知与自动回复**一封都发不出去**。
 *   · 判定为正常 ⇒ 直接返回，交回 Fluent Forms 原流程（蜜罐、限流、Turnstile 都在那）。
 * ---------------------------------------------------------------------- */

/**
 * 读取并解析提交数据（与 Fluent Forms 同一口径：data 是 urlencoded 字符串）。
 *
 * @return array|null
 */
function sf_fg_read_submission() {
	if ( ! isset( $_REQUEST['form_id'], $_REQUEST['data'] ) ) {
		return null;
	}
	$form_id = (int) $_REQUEST['form_id'];
	if ( $form_id <= 0 ) {
		return null;
	}
	$raw = (string) wp_unslash( $_REQUEST['data'] ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- 交给 parse_str，值与 Fluent Forms 保持一致。
	$data = array();
	parse_str( $raw, $data );
	if ( ! is_array( $data ) || ! $data ) {
		return null;
	}

	return array( $form_id, $data );
}

/**
 * 主拦截。
 *
 * @return void
 */
function sf_fg_intercept() {
	if ( ! sf_fg_enabled() ) {
		return;
	}

	$parsed = sf_fg_read_submission();
	if ( null === $parsed ) {
		return;
	}
	list( $form_id, $data ) = $parsed;

	if ( ! sf_fg_is_guarded( $form_id ) ) {
		return;
	}

	$ip       = function_exists( 'sf_real_ip_client_ip' ) ? sf_real_ip_client_ip() : '0.0.0.0';
	$edge     = isset( $_SERVER['SF_ORIGINAL_REMOTE_ADDR'] ) ? (string) $_SERVER['SF_ORIGINAL_REMOTE_ADDR'] : '';
	$ua       = isset( $_SERVER['HTTP_USER_AGENT'] ) ? (string) $_SERVER['HTTP_USER_AGENT'] : '';
	$ts_state = sf_fg_ts_state( $data, $ip );
	$score    = sf_fg_score( $form_id, $data, $ua, $ts_state );

	$email_domain = sf_fg_email_domain( sf_fg_value( $data, $score['map'], 'email' ) );
	$signature    = sf_fg_signature( $score['values'] );
	$hit          = sf_fg_blocklist_hit( $ip, $email_domain, $signature );

	$threshold = (int) apply_filters( 'sf_fg_spam_threshold', SF_FG_SPAM_THRESHOLD );
	if ( '' === $hit && $score['score'] < $threshold ) {
		return; // 正常 —— 交回 Fluent Forms。
	}

	$source  = '' !== $hit ? 'blocklist:' . $hit : 'score';
	$signals = $score['signals'];
	if ( '' !== $hit ) {
		$signals[] = 'BLOCKLIST_' . strtoupper( $hit );
	}

	$submission_id = sf_fg_store_spam( $form_id, $data, $score, $ip, $edge );

	sf_fg_log_row(
		array(
			'form_id'       => $form_id,
			'submission_id' => $submission_id,
			'ip'            => $ip,
			'edge_ip'       => $edge,
			'ua'            => $ua,
			'country'       => sf_fg_value( $data, $score['map'], 'country' ),
			'email_domain'  => $email_domain,
			'score'         => $score['score'],
			'signals'       => implode( ',', $signals ),
			'signature'     => $signature,
			'source'        => $source,
		)
	);

	sf_fg_alert_tick();

	/**
	 * 已接管一次提交（落库 + 审计 + 告警，未进入 Fluent Forms 流程）。
	 *
	 * @param int   $form_id       表单 id。
	 * @param array $score         评分结果。
	 * @param int   $submission_id 落库的记录 id。
	 * @param string $source       score|blocklist:*
	 */
	do_action( 'sf_fg_spam_captured', $form_id, $score, $submission_id, $source );

	// 静默「成功」：机器人以为提交有效，不调整策略，也不会知道被拦。
	wp_send_json_success(
		array(
			'insert_id' => $submission_id,
			'result'    => array(
				'message' => sf_fg_success_message( $form_id ),
				'action'  => 'hide_form',
			),
		)
	);
}
add_action( 'wp_ajax_nopriv_fluentform_submit', 'sf_fg_intercept', 5 );
add_action( 'wp_ajax_fluentform_submit', 'sf_fg_intercept', 5 );

/**
 * 从提交数据按角色取值。
 *
 * @param array  $data 提交数据。
 * @param array  $map  角色 → 字段名。
 * @param string $role 角色。
 * @return string
 */
function sf_fg_value( $data, $map, $role ) {
	$name = isset( $map[ $role ] ) ? $map[ $role ] : '';
	if ( '' === $name || ! isset( $data[ $name ] ) ) {
		return '';
	}
	$raw = $data[ $name ];

	return is_array( $raw ) ? implode( ' ', array_map( 'strval', $raw ) ) : (string) $raw;
}

/**
 * 把被拦的提交写入 fluentform_submissions（status = 'spam'）。
 *
 * 这是刻意保留的：记录在案才能复核、统计、追查机器人演化；但因为它同时被
 * 记入审计表且**从未进入插件流程**，所以不会被发信，也不会污染收件箱。
 *
 * @param int    $form_id 表单 id。
 * @param array  $data    提交数据。
 * @param array  $score   评分结果。
 * @param string $ip      真实 IP。
 * @param string $edge    边缘 IP。
 * @return int 记录的 id（失败为 0）。
 */
function sf_fg_store_spam( $form_id, $data, $score, $ip, $edge ) {
	global $wpdb;

	$table = $wpdb->prefix . 'fluentform_submissions';
	$now   = current_time( 'mysql' );

	// serial_number 与插件同算法：同表单内自增。
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 与插件写入同一张表，保持列一致性。
	$prev_serial = $wpdb->get_var( $wpdb->prepare( "SELECT serial_number FROM {$table} WHERE form_id = %d ORDER BY id DESC LIMIT 1", $form_id ) );
	$serial      = $prev_serial ? ( (int) $prev_serial + 1 ) : 1;

	$browser = sf_fg_detect_browser( isset( $_SERVER['HTTP_USER_AGENT'] ) ? (string) $_SERVER['HTTP_USER_AGENT'] : '' );

	$row = array(
		'form_id'       => (int) $form_id,
		'serial_number' => $serial,
		'response'      => wp_json_encode( $data, JSON_UNESCAPED_UNICODE ),
		'source_url'    => site_url( isset( $data['_wp_http_referer'] ) ? (string) $data['_wp_http_referer'] : '' ),
		'user_id'       => get_current_user_id(),
		'status'        => 'spam',
		'browser'       => $browser['browser'],
		'device'        => $browser['device'],
		'ip'            => $ip,
		'city'          => null,
		'country'       => null,
		'created_at'    => $now,
		'updated_at'    => $now,
	);

	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 与插件同一张表。
	$ok = $wpdb->insert( $table, $row );

	return $ok ? (int) $wpdb->insert_id : 0;
}

/**
 * 极简浏览器/平台识别（与插件 Browser 类的常见取值保持一致，只用于后台展示）。
 *
 * @param string $ua User-Agent。
 * @return array{browser:string,device:string}
 */
function sf_fg_detect_browser( $ua ) {
	$browser = 'Unknown';
	$device  = 'Unknown';

	if ( preg_match( '#(Edg|Edge|OPR|Opera|Chrome|CriOS|Firefox|FxiOS|Safari)#i', $ua, $m ) ) {
		$map     = array(
			'edg'     => 'Edge',
			'edge'    => 'Edge',
			'opr'     => 'Opera',
			'opera'   => 'Opera',
			'chrome'  => 'Chrome',
			'crios'   => 'Chrome',
			'firefox' => 'Firefox',
			'fxios'   => 'Firefox',
			'safari'  => 'Safari',
		);
		$key     = strtolower( $m[1] );
		$browser = isset( $map[ $key ] ) ? $map[ $key ] : 'Unknown';
	}

	if ( false !== stripos( $ua, 'windows' ) ) {
		$device = 'Windows';
	} elseif ( false !== stripos( $ua, 'android' ) ) {
		$device = 'Android';
	} elseif ( preg_match( '/iphone|ipad|ipod/i', $ua ) ) {
		$device = 'iOS';
	} elseif ( false !== stripos( $ua, 'macintosh' ) || false !== stripos( $ua, 'mac os' ) ) {
		$device = 'macOS';
	} elseif ( false !== stripos( $ua, 'linux' ) ) {
		$device = 'Linux';
	}

	return array(
		'browser' => $browser,
		'device'  => $device,
	);
}

/**
 * 给被拦提交返回的成功文案 —— 尽量沿用表单自己的确认文案。
 *
 * @param int $form_id 表单 id。
 * @return string
 */
function sf_fg_success_message( $form_id ) {
	$raw = get_option( 'sf_fg_success_message' );
	if ( is_string( $raw ) && '' !== $raw ) {
		return $raw;
	}

	/**
	 * 返回给被拦提交的成功文案（与 Fluent Forms 的默认文案一致）。
	 *
	 * mu-plugin 加载早于插件的 textdomain，所以这里不用 __()，
	 * 文案固定为英文，需要时用本过滤器覆盖。
	 *
	 * @param string $message 默认文案。
	 * @param int    $form_id 表单 id。
	 */
	return (string) apply_filters( 'sf_fg_success_message', 'The form has been successfully submitted.', $form_id );
}

/* -------------------------------------------------------------------------
 * §8  计时字段注入（与 Turnstile 共用一段内联脚本）
 * ---------------------------------------------------------------------- */

/**
 * 是否需要注入前端脚本（页面里有 Fluent Forms 表单时才注入）。
 *
 * @return bool
 */
function sf_fg_should_inject() {
	if ( ! sf_fg_enabled() ) {
		return false;
	}
	// 后台与 REST 不注入。
	if ( is_admin() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
		return false;
	}

	return true;
}

/**
 * 输出内联脚本：给页面上每个 Fluent Forms 表单注入计时字段。
 *
 * 计时字段的值由服务端签名（wp_salt('nonce')），前端改不了；缺字段一律不扣分，
 * 所以即使 JS 被禁用或被缓存剥离，真客户也不受影响。
 *
 * @return void
 */
function sf_fg_print_footer_script() {
	if ( ! sf_fg_should_inject() ) {
		return;
	}

	$field      = sf_fg_time_field();
	$token      = sf_fg_time_token();
	$ts_sitekey = sf_fg_ts_enabled() ? sf_fg_ts_sitekey() : '';
	?>
	<script id="sf-form-guard">
	(function () {
		var FIELD = <?php echo wp_json_encode( $field ); ?>;
		var TOKEN = <?php echo wp_json_encode( $token ); ?>;
		var TS_KEY = <?php echo wp_json_encode( $ts_sitekey ); ?>;
		function forms() {
			return document.querySelectorAll('form.frm-fluent-form');
		}
		function injectTiming() {
			var list = forms();
			for (var i = 0; i < list.length; i++) {
				if (list[i].querySelector('input[name="' + FIELD + '"]')) { continue; }
				var input = document.createElement('input');
				input.type = 'hidden';
				input.name = FIELD;
				input.value = TOKEN;
				list[i].appendChild(input);
			}
		}
		/* Turnstile 是加强层，不是门槛：脚本加载失败 / 超时 ⇒ 不插 widget，
		   表单照常可提交。服务端对应地把「未带 token」只算 1 分弱信号。 */
		function injectTurnstile() {
			if (!TS_KEY) { return; }
			var list = forms();
			if (!list.length) { return; }
			var mounted = false;
			function mount() {
				if (mounted || !window.turnstile) { return; }
				mounted = true;
				for (var i = 0; i < list.length; i++) {
					var box = document.createElement('div');
					box.className = 'cf-turnstile';
					list[i].appendChild(box);
					try { window.turnstile.render(box, { sitekey: TS_KEY }); } catch (e) {}
				}
			}
			var script = document.createElement('script');
			script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
			script.async = true;
			script.defer = true;
			script.onload = mount;
			script.onerror = function () { /* 降级：什么都不做。 */ };
			document.head.appendChild(script);
			window.setTimeout(mount, 6000);
		}
		function boot() {
			injectTiming();
			injectTurnstile();
		}
		if (document.readyState === 'loading') {
			document.addEventListener('DOMContentLoaded', boot);
		} else {
			boot();
		}
	})();
	</script>
	<?php
}
add_action( 'wp_footer', 'sf_fg_print_footer_script', 99 );

/* -------------------------------------------------------------------------
 * §9  Turnstile：自管校验 + 健康探测 + 降级兜底
 *
 * 为什么不用 Fluent Forms 自带的 Turnstile 字段：
 *   插件链路是「校验失败 ⇒ throw 422 ⇒ 提交被拒」。CF 侧抖动、访客所在网络
 *   取不到 challenges.cloudflare.com，都会让**真客户填不了表** —— 这正是运营
 *   明确要求避免的情形。那个链路里没有「降级为放行」的位置。
 *
 * 本文件的做法：Turnstile 由我们自己接。
 *   · 前端：注入 api.js 与 widget（显式 render），token 落在表单内被序列化提交；
 *     脚本加载失败 / 超时 ⇒ 不插 widget，表单照常可提交。
 *   · 服务端：在拦截器里校验 token，结果只作为**一路评分信号**（S7），永不硬拒：
 *       token 有效               ⇒ 不加分
 *       token 无效 / 校验不通过   ⇒ +4（足以单独成案）
 *       未带 token（含降级场景）  ⇒ +1（弱信号；真客户即使因此 +1 也到不了阈值 4）
 *       校验请求本身失败（服务不可达）⇒ 不加分（降级：退回蜜罐 + 计时 + 评分）
 *   净效果：最坏情况退化成「不加分」，真客户永远能提交；而伪造/缺失 token 的
 *   脚本化提交拿不到分差优势。
 *
 * 密钥沿用 Fluent Forms 的存放位置（_fluentform_turnstile_details 的 siteKey /
 * secretKey），这样运营在插件后台填一次即可，不必改文件。
 *
 * 附带保留 fluentform/disable_captcha：若将来运营改用插件原生字段，
 * 该过滤器保证「挑战服务不健康时整体跳过校验」，行为与本文件的兜底一致。
 * ---------------------------------------------------------------------- */

/**
 * Turnstile 密钥（Fluent Forms 标准存放位置）。
 *
 * @return array{siteKey?:string,secretKey?:string}
 */
function sf_fg_turnstile_keys() {
	$opt = get_option( '_fluentform_turnstile_details' );
	if ( ! is_array( $opt ) ) {
		return array();
	}
	if ( empty( $opt['siteKey'] ) || empty( $opt['secretKey'] ) ) {
		return array();
	}

	return $opt;
}

/**
 * Turnstile 服务是否健康（探测结果 15 分钟内有效）。
 *
 * 未探测过时**默认健康** —— 避免因为没跑过探测就把校验关掉。
 *
 * @return bool
 */
function sf_fg_turnstile_healthy() {
	$state = get_option( SF_FG_HEALTH_OPT, array() );
	if ( ! is_array( $state ) || ! isset( $state['ok'], $state['ts'] ) ) {
		return true;
	}
	if ( ( time() - (int) $state['ts'] ) > 900 ) {
		return true; // 结果过期，按健康处理，等下一次探测。
	}

	return (bool) $state['ok'];
}

/**
 * 探测 Turnstile 脚本可达性并记录结果。
 *
 * 由 wp-cron 每 15 分钟触发一次；失败连续 3 次才标记为不健康（抗抖动）。
 *
 * @return void
 */
function sf_fg_turnstile_probe() {
	if ( ! sf_fg_turnstile_keys() ) {
		return;
	}

	$url      = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
	$response = wp_remote_head(
		$url,
		array(
			'timeout'     => 5,
			'redirection' => 2,
			'user-agent'  => 'SINO-FRESH-Healthcheck/1.0; ' . home_url( '/' ),
		)
	);

	$ok     = ( ! is_wp_error( $response ) && 200 === (int) wp_remote_retrieve_response_code( $response ) );
	$state  = get_option( SF_FG_HEALTH_OPT, array() );
	$state  = is_array( $state ) ? $state : array();
	$strikes = $ok ? 0 : (int) ( isset( $state['strikes'] ) ? $state['strikes'] : 0 ) + 1;

	update_option(
		SF_FG_HEALTH_OPT,
		array(
			'ok'      => $ok ? true : ( $strikes < 3 ), // 连续 3 次失败才认定不健康。
			'strikes' => $strikes,
			'ts'      => time(),
		),
		false
	);
}
add_action( 'sf_fg_turnstile_probe_event', 'sf_fg_turnstile_probe' );

/**
 * 注册健康探测计划（15 分钟一次）。
 *
 * @return void
 */
function sf_fg_turnstile_schedule() {
	if ( ! sf_fg_turnstile_keys() ) {
		return;
	}
	if ( ! wp_next_scheduled( 'sf_fg_turnstile_probe_event' ) ) {
		wp_schedule_event( time() + 60, 'sf_fg_quarter_hour', 'sf_fg_turnstile_probe_event' );
	}
}
add_action( 'init', 'sf_fg_turnstile_schedule' );

/**
 * 自定义 15 分钟调度间隔。
 *
 * @param array $schedules 现有计划。
 * @return array
 */
function sf_fg_cron_schedules( $schedules ) {
	if ( ! isset( $schedules['sf_fg_quarter_hour'] ) ) {
		$schedules['sf_fg_quarter_hour'] = array(
			'interval' => 900,
			'display'  => 'Every 15 minutes (SINO FRESH form guard)',
		);
	}

	return $schedules;
}
add_filter( 'cron_schedules', 'sf_fg_cron_schedules' );

/**
 * Turnstile 是否启用（有密钥 + 服务健康 + 总开关打开）。
 *
 * @return bool
 */
function sf_fg_ts_enabled() {
	if ( ! sf_fg_enabled() ) {
		return false;
	}
	if ( ! sf_fg_turnstile_keys() ) {
		return false;
	}

	return (bool) apply_filters( 'sf_fg_turnstile_enabled', sf_fg_turnstile_healthy() );
}

/**
 * Turnstile siteKey（前端渲染用）。
 *
 * @return string
 */
function sf_fg_ts_sitekey() {
	$keys = sf_fg_turnstile_keys();

	return isset( $keys['siteKey'] ) ? (string) $keys['siteKey'] : '';
}

/**
 * 校验 Turnstile token（服务端 siteverify）。
 *
 * 三态返回：
 *   true  —— 校验通过
 *   false —— 校验明确不通过（token 无效 / 过期 / 复用）
 *   null  —— 无法判定（服务不可达、非 200）⇒ 调用方按「降级」处理，不加分
 *
 * @param string $token 前端 token。
 * @param string $ip    访客 IP。
 * @return bool|null
 */
function sf_fg_ts_verify( $token, $ip = '' ) {
	$keys = sf_fg_turnstile_keys();
	if ( empty( $keys['secretKey'] ) ) {
		return null;
	}
	$token = is_string( $token ) ? trim( $token ) : '';
	if ( '' === $token ) {
		return false;
	}

	$body = array(
		'secret'   => (string) $keys['secretKey'],
		'response' => $token,
	);
	if ( '' !== $ip && '0.0.0.0' !== $ip ) {
		$body['remoteip'] = $ip;
	}

	$response = wp_remote_post(
		'https://challenges.cloudflare.com/turnstile/v0/siteverify',
		array(
			'timeout' => 5,
			'body'    => $body,
		)
	);

	if ( is_wp_error( $response ) ) {
		return null; // 服务不可达 ⇒ 降级。
	}
	if ( 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
		return null; // 非 200 多为 CF 侧问题 ⇒ 降级。
	}

	$json = json_decode( (string) wp_remote_retrieve_body( $response ), true );
	if ( ! is_array( $json ) || ! array_key_exists( 'success', $json ) ) {
		return null;
	}

	return (bool) $json['success'];
}

/**
 * 把一次提交的 Turnstile 情况归成一个状态（供纯函数信号消费）。
 *
 * @param array  $data 提交数据。
 * @param string $ip   访客 IP。
 * @return string disabled|absent|ok|fail|degraded
 */
function sf_fg_ts_state( $data, $ip = '' ) {
	if ( ! sf_fg_ts_enabled() ) {
		return 'disabled';
	}

	$token = isset( $data['cf-turnstile-response'] ) ? (string) $data['cf-turnstile-response'] : '';
	if ( '' === trim( $token ) ) {
		return 'absent'; // 含「访客侧脚本没加载出来」的降级场景。
	}

	$result = sf_fg_ts_verify( $token, $ip );
	if ( null === $result ) {
		return 'degraded';
	}

	return $result ? 'ok' : 'fail';
}

/**
 * 若运营改用 Fluent Forms 原生 Turnstile 字段，这条保证挑战服务不健康时整体跳过校验。
 *
 * @param bool   $disable 插件当前判断。
 * @param mixed  $form    表单对象。
 * @param string $type    验证码类型。
 * @return bool
 */
function sf_fg_disable_captcha( $disable, $form = null, $type = '' ) {
	if ( 'turnstile' !== $type ) {
		return $disable;
	}
	if ( ! sf_fg_enabled() || ! sf_fg_turnstile_keys() ) {
		return $disable;
	}
	if ( sf_fg_turnstile_healthy() ) {
		return $disable;
	}

	return true; // 降级：不阻塞真客户。
}
add_filter( 'fluentform/disable_captcha', 'sf_fg_disable_captcha', 10, 3 );

/* -------------------------------------------------------------------------
 * §10  后台「表单防护」复核页
 * ---------------------------------------------------------------------- */

/**
 * 注册菜单。
 *
 * @return void
 */
function sf_fg_admin_menu() {
	add_menu_page(
		'表单防护',
		'表单防护',
		'manage_options',
		'sf-form-guard',
		'sf_fg_render_admin_page',
		'dashicons-shield-alt',
		58
	);
}
add_action( 'admin_menu', 'sf_fg_admin_menu' );

/**
 * 处理复核动作（标为正常 / 加黑名单 / 移除黑名单）。
 *
 * @return void
 */
function sf_fg_handle_admin_action() {
	if ( ! isset( $_POST['sf_fg_action'] ) ) {
		return;
	}
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	if ( ! isset( $_POST['sf_fg_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['sf_fg_nonce'] ) ), 'sf_fg_admin' ) ) {
		return;
	}

	$action = sanitize_text_field( wp_unslash( $_POST['sf_fg_action'] ) );
	$notice = '';

	if ( 'release' === $action ) {
		$log_id = isset( $_POST['log_id'] ) ? (int) $_POST['log_id'] : 0;
		$notice = sf_fg_release_row( $log_id ) ? 'released' : 'failed';
	} elseif ( 'blocklist_add' === $action ) {
		$type  = isset( $_POST['bl_type'] ) ? sanitize_text_field( wp_unslash( $_POST['bl_type'] ) ) : '';
		$value = isset( $_POST['bl_value'] ) ? sanitize_text_field( wp_unslash( $_POST['bl_value'] ) ) : '';
		$ok    = sf_fg_blocklist_add( $type, $value, 'manual' );
		$notice = $ok ? 'blocked' : 'failed';
	} elseif ( 'blocklist_remove' === $action ) {
		$index = isset( $_POST['bl_index'] ) ? (int) $_POST['bl_index'] : -1;
		$ok    = sf_fg_blocklist_remove( $index );
		$notice = $ok ? 'unblocked' : 'failed';
	}

	if ( '' !== $notice ) {
		$url = add_query_arg(
			array(
				'page'    => 'sf-form-guard',
				'sf_fg_n' => $notice,
			),
			admin_url( 'admin.php' )
		);
		wp_safe_redirect( $url );
		exit;
	}
}
add_action( 'admin_init', 'sf_fg_handle_admin_action' );

/**
 * 把一条被拦提交改回正常（保留记录，仅在日志里标记已放行）。
 *
 * @param int $log_id 日志行 id。
 * @return bool
 */
function sf_fg_release_row( $log_id ) {
	global $wpdb;
	$log_id = (int) $log_id;
	if ( $log_id <= 0 ) {
		return false;
	}

	$log_table = $wpdb->prefix . SF_FG_LOG_TABLE;
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表。
	$row = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$log_table} WHERE id = %d", $log_id ), ARRAY_A );
	if ( ! $row ) {
		return false;
	}

	if ( (int) $row['submission_id'] > 0 ) {
		$sub_table = $wpdb->prefix . 'fluentform_submissions';
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 与插件同一张表。
		$wpdb->update(
			$sub_table,
			array(
				'status'     => 'unread',
				'updated_at' => current_time( 'mysql' ),
			),
			array( 'id' => (int) $row['submission_id'] )
		);
	}

	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表。
	return (bool) $wpdb->update(
		$log_table,
		array(
			'released'    => 1,
			'released_at' => current_time( 'mysql' ),
		),
		array( 'id' => $log_id )
	);
}

/**
 * 渲染复核页。
 *
 * @return void
 */
function sf_fg_render_admin_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}

	global $wpdb;
	$log_table = $wpdb->prefix . SF_FG_LOG_TABLE;

	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表。
	$total = (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$log_table}" );
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表。
	$today = (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$log_table} WHERE created_at >= %s", wp_date( 'Y-m-d' ) . ' 00:00:00' ) );
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- 自建审计表。
	$rows  = $wpdb->get_results( "SELECT * FROM {$log_table} ORDER BY id DESC LIMIT 100", ARRAY_A );
	$alert = get_option( SF_FG_ALERT_OPT, array() );
	$block = sf_fg_blocklist();
	$notice = isset( $_GET['sf_fg_n'] ) ? sanitize_text_field( wp_unslash( $_GET['sf_fg_n'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- 仅用于展示提示。
	?>
	<div class="wrap">
		<h1>表单防护</h1>
		<?php if ( '' !== $notice ) : ?>
			<div class="notice notice-success is-dismissible"><p>操作已提交：<?php echo esc_html( $notice ); ?></p></div>
		<?php endif; ?>

		<p>
			<strong>今日拦截：</strong><?php echo esc_html( (string) $today ); ?> 条　|　
			<strong>累计拦截：</strong><?php echo esc_html( (string) $total ); ?> 条　|　
			<strong>今日告警：</strong><?php echo ( is_array( $alert ) && ! empty( $alert['sent'] ) ) ? '已发送' : '未触发'; ?>　|　
			<strong>总开关：</strong><?php echo sf_fg_enabled() ? '启用' : '停用'; ?>
		</p>
		<p class="description">
			被拦提交以 <code>status = spam</code> 存于 Fluent Forms 条目列表（同样受筛选器管辖），
			并且<strong>不会触发任何邮件</strong>。此处「标为正常」只把记录改回 <code>unread</code>。
		</p>

		<h2>拦截记录（最近 100 条）</h2>
		<table class="widefat striped">
			<thead>
				<tr>
					<th>时间</th><th>表单</th><th>真实 IP</th><th>边缘 IP</th><th>国别</th>
					<th>邮箱域</th><th>评分</th><th>命中</th><th>来源</th><th>状态</th><th>操作</th>
				</tr>
			</thead>
			<tbody>
			<?php if ( ! $rows ) : ?>
				<tr><td colspan="11">还没有拦截记录。</td></tr>
			<?php else : ?>
				<?php foreach ( $rows as $row ) : ?>
					<tr>
						<td><?php echo esc_html( (string) $row['created_at'] ); ?></td>
						<td>#<?php echo esc_html( (string) $row['form_id'] ); ?></td>
						<td><code><?php echo esc_html( (string) $row['ip'] ); ?></code></td>
						<td><code><?php echo esc_html( (string) $row['edge_ip'] ); ?></code></td>
						<td><?php echo esc_html( (string) $row['country'] ); ?></td>
						<td><?php echo esc_html( (string) $row['email_domain'] ); ?></td>
						<td><?php echo esc_html( (string) $row['score'] ); ?></td>
						<td><small><?php echo esc_html( (string) $row['signals'] ); ?></small></td>
						<td><small><?php echo esc_html( (string) $row['source'] ); ?></small></td>
						<td><?php echo ( (int) $row['released'] === 1 ) ? '已放行' : '拦截中'; ?></td>
						<td>
							<?php if ( (int) $row['released'] !== 1 ) : ?>
								<form method="post" style="display:inline">
									<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
									<input type="hidden" name="sf_fg_action" value="release">
									<input type="hidden" name="log_id" value="<?php echo esc_attr( (string) $row['id'] ); ?>">
									<button class="button button-small">标为正常</button>
								</form>
							<?php endif; ?>
							<form method="post" style="display:inline">
								<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
								<input type="hidden" name="sf_fg_action" value="blocklist_add">
								<input type="hidden" name="bl_type" value="ip">
								<input type="hidden" name="bl_value" value="<?php echo esc_attr( (string) $row['ip'] ); ?>">
								<button class="button button-small">封该 IP</button>
							</form>
							<form method="post" style="display:inline">
								<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
								<input type="hidden" name="sf_fg_action" value="blocklist_add">
								<input type="hidden" name="bl_type" value="signature">
								<input type="hidden" name="bl_value" value="<?php echo esc_attr( (string) $row['signature'] ); ?>">
								<button class="button button-small">封该内容</button>
							</form>
							<?php if ( '' !== (string) $row['email_domain'] ) : ?>
								<form method="post" style="display:inline">
									<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
									<input type="hidden" name="sf_fg_action" value="blocklist_add">
									<input type="hidden" name="bl_type" value="domain">
									<input type="hidden" name="bl_value" value="<?php echo esc_attr( (string) $row['email_domain'] ); ?>">
									<button class="button button-small">封该邮箱域</button>
								</form>
							<?php endif; ?>
						</td>
					</tr>
				<?php endforeach; ?>
			<?php endif; ?>
			</tbody>
		</table>

		<h2>黑名单（<?php echo esc_html( (string) count( $block ) ); ?> 项）</h2>
		<table class="widefat striped">
			<thead><tr><th>类型</th><th>值</th><th>加入时间</th><th>备注</th><th>操作</th></tr></thead>
			<tbody>
			<?php if ( ! $block ) : ?>
				<tr><td colspan="5">黑名单为空。</td></tr>
			<?php else : ?>
				<?php foreach ( $block as $i => $entry ) : ?>
					<tr>
						<td><?php echo esc_html( (string) $entry['type'] ); ?></td>
						<td><code><?php echo esc_html( (string) $entry['value'] ); ?></code></td>
						<td><?php echo esc_html( (string) ( isset( $entry['added'] ) ? $entry['added'] : '' ) ); ?></td>
						<td><?php echo esc_html( (string) ( isset( $entry['note'] ) ? $entry['note'] : '' ) ); ?></td>
						<td>
							<form method="post">
								<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
								<input type="hidden" name="sf_fg_action" value="blocklist_remove">
								<input type="hidden" name="bl_index" value="<?php echo esc_attr( (string) $i ); ?>">
								<button class="button button-small">移除</button>
							</form>
						</td>
					</tr>
				<?php endforeach; ?>
			<?php endif; ?>
			</tbody>
		</table>

		<h2>手动加入黑名单</h2>
		<form method="post">
			<?php wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' ); ?>
			<input type="hidden" name="sf_fg_action" value="blocklist_add">
			<select name="bl_type">
				<option value="ip">IP</option>
				<option value="domain">邮箱域</option>
				<option value="signature">内容签名</option>
			</select>
			<input type="text" name="bl_value" class="regular-text" placeholder="例如 203.0.113.7 或 example.com">
			<button class="button">加入黑名单</button>
		</form>
	</div>
	<?php
}
