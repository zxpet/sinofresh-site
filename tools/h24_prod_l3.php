<?php
/**
 * H24 — 生产/开发 决策层（L3）验收：直接驱动 mu-plugin 的纯评分函数
 *
 * 为什么需要这一层：
 *   写路径验收（HTTP 提交）会在库里留行、会发邮件，生产上不可随意做。
 *   本层**不碰网络、不写库、不发信**，只把构造样本喂给 sf_fg_score()，
 *   用来证明「真人样本低于阈值 / 机器人样本达到阈值 / S4 不计分」等判定规则。
 *
 * 用法
 *   SF_H24_SITE=prod|dev wp eval-file /root/h24-tools/h24_prod_l3.php --allow-root
 *
 * 退出码：0 全通过 / 4 有 FAIL
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

$FORM    = 8;
$THRESH  = SF_FG_SPAM_THRESHOLD;

$UA_MODERN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';
$UA_STALE  = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36';

/**
 * 造样本
 *
 * @param int|null $elapsed 距渲染经过的秒数；null = 不带计时字段
 */
function sf_h24_l3_case($company, $contact, $email, $country, $message, $elapsed, $ua, $ts, $want, $wantScore = null, $wantSignal = null)
{
    return array(
        'data' => array(
            'company_name_1'   => $company,
            'contact_person_2' => $contact,
            'email_3'          => $email,
            'country_5'        => $country,
            'notes_10'         => $message,
        ),
        'elapsed'    => $elapsed,
        'ua'         => $ua,
        'ts'         => $ts,
        'want'       => $want,        // 'pass' = 放行(score < 阈值) / 'block' = 拦截(score >= 阈值)
        'wantScore'  => $wantScore,   // 精确分值（null = 只判方向）
        'wantSignal' => $wantSignal,  // 必须出现的信号（null = 不查）
    );
}

$cases = array(
    'R1 真人-德国品牌私标询盘' => sf_h24_l3_case(
        'Zengarden Trading Oy', 'Mikko Virtanen', 'mikko.virtanen@zengarden-trading.de', 'Germany',
        'Hello, we are looking for a private label partner for soft chews. Could you share your MOQ and lead time for 5000 units?',
        12, $UA_MODERN, 'ok', 'pass', 0
    ),
    'R2 真人-美国经销商要规格书' => sf_h24_l3_case(
        'Brightpaw Distribution LLC', 'Sarah Whitfield', 'sarah@brightpawdist.com', 'United States',
        'We would like to discuss OEM production for dental chews. Please send your spec sheet and COA.',
        8, $UA_MODERN, 'ok', 'pass', 0
    ),
    'R3 真人-中国客户中文询盘' => sf_h24_l3_case(
        'Xiamen Petlink Import Co Ltd', 'Chen Wei', 'chenwei@petlink-import.cn', 'China',
        '您好，我们对贵司的软咀嚼片产品感兴趣，希望了解代工合作方式与最小起订量，请提供报价单与样品政策。',
        20, $UA_MODERN, 'disabled', 'pass'
    ),
    'B1 机器人-同后缀+模板短句' => sf_h24_l3_case(
        'RobertTon', 'Ton', 'robertton@gmail.com', 'United States',
        'Price?',
        null, $UA_STALE, 'disabled', 'block', 5, 'S1_shared_suffix'
    ),
    'B2 机器人-多弱信号叠加' => sf_h24_l3_case(
        'DavidBon', 'DavidBonDS', 'davidbon@mailinator.com', 'Germany',
        'Preis?',
        null, $UA_MODERN, 'disabled', 'block', 6
    ),
    'S4 陈旧UA单独出现（不应计分）' => sf_h24_l3_case(
        'Zengarden Trading Oy', 'Mikko Virtanen', 'mikko.virtanen@zengarden-trading.de', 'Germany',
        'Hello, we are looking for a private label partner for soft chews. Could you share your MOQ and lead time for 5000 units?',
        12, $UA_STALE, 'ok', 'pass', 0, 'S4_note_stale_ua'
    ),
    'T1 Turnstile 校验失败（单独成案）' => sf_h24_l3_case(
        'Zengarden Trading Oy', 'Mikko Virtanen', 'mikko.virtanen@zengarden-trading.de', 'Germany',
        'Hello, we are looking for a private label partner for soft chews. Could you share your MOQ and lead time for 5000 units?',
        12, $UA_MODERN, 'fail', 'block', 4, 'S7_turnstile_failed'
    ),
    'S6 提交过快（0 秒，仅 +2 不成案）' => sf_h24_l3_case(
        'Zengarden Trading Oy', 'Mikko Virtanen', 'mikko.virtanen@zengarden-trading.de', 'Germany',
        'Hello, we are looking for a private label partner for soft chews. Could you share your MOQ and lead time for 5000 units?',
        0, $UA_MODERN, 'ok', 'pass', 2, 'S6_too_fast'
    ),
);

$site = getenv('SF_H24_SITE');
if (!in_array($site, array('dev', 'prod'), true)) {
    $site = 'dev';
}

fwrite(STDOUT, "== H24 L3 决策层验收 [site={$site}] 阈值={$THRESH} ==\n");
fwrite(STDOUT, sprintf("   常量: MIN_FILL=%d STALE_MAJOR=%d MIN_FRAGMENT=%d\n",
    SF_FG_MIN_FILL_SECONDS, SF_FG_STALE_MAJOR, SF_FG_MIN_FRAGMENT));

$pass = 0;
$fail = 0;

foreach ($cases as $name => $c) {
    $data = $c['data'];
    if (null !== $c['elapsed']) {
        $data[sf_fg_time_field()] = sf_fg_time_token(time() - (int) $c['elapsed']);
    }

    $r     = sf_fg_score($FORM, $data, $c['ua'], $c['ts']);
    $score = (int) $r['score'];
    $sig   = implode(',', $r['signals']);

    $verdict = ($score >= $THRESH) ? 'block' : 'pass';

    $problems = array();
    if ($verdict !== $c['want']) {
        $problems[] = sprintf('方向=%s 期望=%s', $verdict, $c['want']);
    }
    if (null !== $c['wantScore'] && $score !== $c['wantScore']) {
        $problems[] = sprintf('分值=%d 期望=%d', $score, $c['wantScore']);
    }
    if (null !== $c['wantSignal'] && false === strpos($sig, $c['wantSignal'])) {
        $problems[] = sprintf('缺少信号 %s', $c['wantSignal']);
    }

    if ($problems) {
        $fail++;
        fwrite(STDOUT, sprintf("  [FAIL] %-34s score=%-2d signals=[%s]\n         └─ %s\n",
            $name, $score, $sig, implode('; ', $problems)));
    } else {
        $pass++;
        fwrite(STDOUT, sprintf("  [ OK ] %-34s score=%-2d verdict=%-5s signals=[%s]\n",
            $name, $score, $verdict, $sig));
    }
}

/* S4 不计分的强断言：把 S4 从信号里抹掉后分值必须不变 */
$c4  = $cases['S4 陈旧UA单独出现（不应计分）'];
$d4  = $c4['data'];
$d4[sf_fg_time_field()] = sf_fg_time_token(time() - 12);
$r4s = sf_fg_score($FORM, $d4, $UA_STALE, 'ok');
$r4m = sf_fg_score($FORM, $d4, $UA_MODERN, 'ok');
$inv = ((int) $r4s['score'] === (int) $r4m['score']);
if ($inv) {
    $pass++;
    fwrite(STDOUT, sprintf("  [ OK ] 不变量：陈旧UA vs 现代UA 分值相同 (%d == %d)\n",
        $r4s['score'], $r4m['score']));
} else {
    $fail++;
    fwrite(STDOUT, sprintf("  [FAIL] 不变量被破坏：陈旧UA=%d 现代UA=%d（S4 不应影响分值）\n",
        $r4s['score'], $r4m['score']));
}

fwrite(STDOUT, sprintf("== 结果：%d passed, %d failed ==\n", $pass, $fail));
exit($fail > 0 ? 4 : 0);
