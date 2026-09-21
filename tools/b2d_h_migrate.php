<?php
/**
 * Batch H1 Step 3 — sf_formula meta migration (21 published records).
 *
 * Run on the dev server via `wp eval-file`:
 *
 *   wp eval-file tools/b2d_h_migrate.php dump
 *   wp eval-file tools/b2d_h_migrate.php dry-run
 *   wp eval-file tools/b2d_h_migrate.php apply /tmp/sf-h1-plan.json
 *   wp eval-file tools/b2d_h_migrate.php verify /tmp/sf-h1-plan.json
 *   wp eval-file tools/b2d_h_migrate.php rollback /tmp/sf-h1-prestate.json
 *
 * Output is one JSON document on stdout; human chatter goes to STDERR so the
 * stdout can be piped/sha-summed safely.
 *
 * What gets written (per record, 5 keys — everything else stays EMPTY, the
 * H1 plan forbids placeholder values):
 *
 *   sf_formula_intro      the EXACT string sinofresh_formula_intro() renders
 *                         today (meta override read back its own output, so
 *                         the 42 formula pages stay byte-identical);
 *   sf_formula_shelf_life shelf segment parsed out of sf_formula_specs with
 *                         the same key-regex the spec-cell parser uses
 *                         (/\d+\s*months?\s+shelf\s+life/ over ' · ' segments);
 *   sf_formula_lead_time  the dosage form's facts-mini Lead time value via
 *                         sinofresh_formula_spec_cell() — identical across all
 *                         eight forms ("Typically 7–15 working days…"), but
 *                         read per-form so a future form edit stays the source;
 *   sf_formula_faq_data   JSON [{q,a}] — the 9 preset questions; answers stay
 *                         blank EXCEPT the three dictated in batch C
 *                         (dogs-or-cats / storage / confidentiality), whose
 *                         text is lifted from sinofresh_formula_faq_data()
 *                         itself so there is no second copy to drift;
 *   sf_formula_source     existing note + a one-line migration annotation
 *                         (admin-only key, never rendered).
 *
 * apply() refuses to run unless the recomputed plan is byte-identical to the
 * plan file produced by dry-run — no silent drift between what was reviewed
 * and what is written. Before the first write it dumps the full pre-state
 * (old keys + which new keys already existed) to STDERR-saved JSON for
 * rollback; rollback restores values and deletes keys that did not exist.
 */

if (!defined('ABSPATH')) {
	fwrite(STDERR, "must run via wp eval-file\n");
	exit(1);
}

/* wp eval-file runs under whichever theme is active — the LIVE theme does not
 * carry inc/formula-admin.php. Everything this script calls (faq preset,
 * intro renderer, spec cells) must come from the gated candidate bytes, so
 * pull the preflight copy's inc files in explicitly when they are missing. */
if (!function_exists('sf_formula_faq_preset') || !function_exists('sinofresh_formula_intro')) {
	$pf = ABSPATH . 'wp-content/themes/sinofresh-theme-preflight/';
	if (!is_readable($pf . 'inc/formula-admin.php')) {
		fwrite(STDERR, "preflight theme copy not found — cannot guarantee gated code\n");
		exit(1);
	}
	require_once $pf . 'inc/formula-pools.php';
	require_once $pf . 'inc/formula-admin.php';
	fwrite(STDERR, "note: loaded inc files from the preflight theme copy\n");
}

const ANNOTATION = ' [H1 migration 2026-09-21: intro/shelf_life/lead_time/faq_data prefilled from existing rendered content; params/packaging/media keys intentionally left empty for the sales team to fill.]';

/** The three dictated answers, keyed by their preset question. */
function sf_h1_dictated_answers() {
	// Lifted from sinofresh_formula_faq_data() — the static pairs.
	return array(
		'Is this formula for dogs or for cats?'      => 'Our formulas can be customised for dogs, cats, or both. Tell us your target species when you enquire and we will adjust the formula, the dosage, and the label accordingly.',
		'How should the finished product be stored?' => 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the container tightly closed and use within the recommended period.',
		'Will you keep my formula and my brand confidential?' => 'Yes — every formula is produced exclusively under your own brand. We never sell your formula, your artwork, or your customer list to any third party, and we sign an NDA before sharing any custom formulation details.',
	);
}

/** All 21 published records, stable order. */
function sf_h1_ids() {
	$ids = get_posts(array(
		'post_type'      => 'sf_formula',
		'post_status'    => 'publish',
		'posts_per_page' => 30,
		'orderby'        => 'ID',
		'order'          => 'ASC',
		'fields'         => 'ids',
	));
	sort($ids, SORT_NUMERIC);
	return $ids;
}

/** Shelf segment of a specs line — the spec-cell parser's own regex. */
function sf_h1_shelf($specs) {
	$specs = trim((string) $specs);
	if ($specs === '') {
		return '';
	}
	foreach (explode('·', $specs) as $segment) {
		$segment = trim($segment);
		if ($segment !== '' && preg_match('/\d+\s*months?\s+shelf\s+life/i', $segment)) {
			// Normalise to the admin hint's shape, e.g. "24 months".
			if (preg_match('/(\d+\s*months?)\s+shelf\s+life/i', $segment, $m)) {
				return trim($m[1]);
			}
			return $segment;
		}
	}
	return '';
}

/** Compute the full plan. Deterministic: dry-run and apply must agree. */
function sf_h1_plan() {
	$dictated = sf_h1_dictated_answers();
	$preset   = sf_formula_faq_preset(); // 9 questions, blank answers
	$faq_init = array();
	foreach ($preset as $row) {
		$q = (string) $row['q'];
		$faq_init[] = array(
			'q' => $q,
			'a' => isset($dictated[$q]) ? $dictated[$q] : '',
		);
	}

	/* JSON_UNESCAPED_* keeps backslashes out of the JSON so update_post_meta's
	 * internal wp_unslash() cannot strip them (measured 2026-09-21: an em dash
	 * encoded as \u2014 came back from the DB as a literal "u2014"). The
	 * apply() loop additionally wp_slash()es every write, so even a literal
	 * backslash or quote survives the core API's magic-quotes behaviour. */
	$faq_json = wp_json_encode($faq_init, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

	$plan = array('records' => array()); // deliberately no timestamp: apply byte-compares against dry-run
	foreach (sf_h1_ids() as $id) {
		$terms = wp_get_post_terms($id, 'sf_formula_form', array('fields' => 'slugs'));
		$form  = (!is_wp_error($terms) && $terms) ? (string) $terms[0] : '';

		$src = (string) get_post_meta($id, 'sf_formula_source', true);
		$src = rtrim($src);
		if (strpos($src, '[H1 migration') === false) {
			$src = ($src === '' ? '' : $src . ' ') . ltrim(ANNOTATION);
		}

		$lead = $form !== '' ? trim((string) sinofresh_formula_spec_cell($form, 'Lead time')) : '';

		$plan['records'][] = array(
			'id'                    => (int) $id,
			'title'                 => get_the_title($id),
			'post_name'             => get_post_field('post_name', $id),
			'form'                  => $form,
			'writes'                => array(
				'sf_formula_intro'      => sinofresh_formula_intro($id),
				'sf_formula_shelf_life' => sf_h1_shelf(get_post_meta($id, 'sf_formula_specs', true)),
				'sf_formula_lead_time'  => $lead,
				'sf_formula_faq_data'   => $faq_json,
				'sf_formula_source'     => $src,
			),
			'old_state'             => array(
				'sf_formula_specs'       => (string) get_post_meta($id, 'sf_formula_specs', true),
				'sf_formula_source'      => (string) get_post_meta($id, 'sf_formula_source', true),
			),
			'new_keys_already_set'  => array_values(array_filter(array_map(function ($k) use ($id) {
				return get_post_meta($id, $k, true) !== '' ? $k : null;
			}, array('sf_formula_intro', 'sf_formula_shelf_life', 'sf_formula_lead_time', 'sf_formula_faq_data')))),
		);
	}
	return $plan;
}

/** Pre-state snapshot for rollback (old values + existence of the 5 keys). */
function sf_h1_prestate() {
	$keys = array('sf_formula_intro', 'sf_formula_shelf_life', 'sf_formula_lead_time',
		'sf_formula_faq_data', 'sf_formula_source');
	$out = array('keys' => $keys, 'records' => array());
	foreach (sf_h1_ids() as $id) {
		$r = array('id' => (int) $id);
		foreach ($keys as $k) {
			$v = get_post_meta($id, $k, true);
			$r[$k] = ($v === '') ? null : (string) $v; // null = did not exist
		}
		$out['records'][] = $r;
	}
	return $out;
}

function sf_h1_emit($data) {
	fwrite(STDOUT, wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT) . "\n");
}

$args   = isset($args) && is_array($args) ? $args : array();
$mode   = isset($args[0]) ? $args[0] : '';
$path   = isset($args[1]) ? $args[1] : '';

switch ($mode) {
	case 'dump':
		sf_h1_emit(sf_h1_prestate());
		break;

	case 'dry-run':
		sf_h1_emit(sf_h1_plan());
		fwrite(STDERR, "dry-run: no meta was written\n");
		break;

	case 'apply':
		if ($path === '' || !is_readable($path)) {
			fwrite(STDERR, "apply: plan file missing: {$path}\n");
			exit(1);
		}
		$plan = sf_h1_plan();
		$reviewed = (string) file_get_contents($path);
		if (rtrim(wp_json_encode($plan, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)) !== rtrim($reviewed)) {
			fwrite(STDERR, "apply: recomputed plan differs from the reviewed plan file — refusing\n");
			exit(2);
		}
		$pre = sf_h1_prestate();
		$pre_path = dirname($path) . '/sf-h1-prestate.json';
		file_put_contents($pre_path, wp_json_encode($pre, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT) . "\n");
		fwrite(STDERR, "pre-state saved: {$pre_path}\n");
		$n = 0;
		foreach ($plan['records'] as $rec) {
			foreach ($rec['writes'] as $key => $val) {
				update_post_meta($rec['id'], $key, wp_slash($val));
				$n++;
			}
		}
		fwrite(STDERR, "applied: {$n} key writes across " . count($plan['records']) . " records\n");
		break;

	case 'verify':
		if ($path === '' || !is_readable($path)) {
			fwrite(STDERR, "verify: plan file missing: {$path}\n");
			exit(1);
		}
		$plan = json_decode((string) file_get_contents($path), true);
		if (!is_array($plan)) {
			fwrite(STDERR, "verify: plan file is not valid JSON\n");
			exit(1);
		}
		$fails = array();
		$checked = 0;
		foreach ($plan['records'] as $rec) {
			$id = (int) $rec['id'];
			foreach ($rec['writes'] as $key => $val) {
				$checked++;
				$got = (string) get_post_meta($id, $key, true);
				if ($got !== (string) $val) {
					$fails[] = "post {$id} {$key}: value differs from plan";
				}
			}
			// JSON shape: 9 rows, questions in preset order.
			$rows = json_decode((string) get_post_meta($id, 'sf_formula_faq_data', true), true);
			if (!is_array($rows) || count($rows) !== 9) {
				$fails[] = "post {$id}: sf_formula_faq_data is not a 9-row JSON array";
			} else {
				$preset = sf_formula_faq_preset();
				foreach ($rows as $i => $row) {
					if ((string) $row['q'] !== (string) $preset[$i]['q']) {
						$fails[] = "post {$id}: faq row {$i} question out of order";
					}
				}
			}
			// Source must carry the annotation exactly once.
			if (substr_count((string) get_post_meta($id, 'sf_formula_source', true), '[H1 migration') !== 1) {
				$fails[] = "post {$id}: source annotation count != 1";
			}
			// The frontend invariant: the intro renderer must return its own stored text.
			if (sinofresh_formula_intro($id) !== (string) get_post_meta($id, 'sf_formula_intro', true)) {
				$fails[] = "post {$id}: renderer output != stored intro";
			}
		}
		// Key-count census: exactly 5 keys present on each of 21 records.
		$all = array('sf_formula_intro', 'sf_formula_shelf_life', 'sf_formula_lead_time',
			'sf_formula_faq_data', 'sf_formula_source', 'sf_formula_flavors', 'sf_formula_weight',
			'sf_formula_counts', 'sf_formula_shape', 'sf_formula_species', 'sf_formula_lifestage',
			'sf_formula_price_tiers', 'sf_formula_recommended_for', 'sf_formula_use_cases',
			'sf_formula_who_for', 'sf_formula_packaging_extra', 'sf_formula_colors',
			'sf_formula_cartons', 'sf_formula_container', 'sf_formula_gallery_ids',
			'sf_formula_video_url');
		$count = 0;
		foreach (sf_h1_ids() as $id) {
			foreach ($all as $k) {
				if (get_post_meta($id, $k, true) !== '') {
					$count++;
				}
			}
		}
		if ($count !== count(sf_h1_ids()) * 5) {
			$fails[] = "key census: {$count} non-empty new-key rows (want 21x5=105)";
		}
		sf_h1_emit(array(
			'checked_writes' => $checked,
			'key_census'     => $count,
			'fails'          => $fails,
			'pass'           => !$fails,
		));
		exit($fails ? 1 : 0);
		break;

	case 'rollback':
		if ($path === '' || !is_readable($path)) {
			fwrite(STDERR, "rollback: pre-state file missing: {$path}\n");
			exit(1);
		}
		$pre = json_decode((string) file_get_contents($path), true);
		if (!is_array($pre) || empty($pre['records'])) {
			fwrite(STDERR, "rollback: pre-state file is not valid JSON\n");
			exit(1);
		}
		$n = 0;
		foreach ($pre['records'] as $r) {
			$id = (int) $r['id'];
			foreach ($pre['keys'] as $k) {
				$old = isset($r[$k]) ? $r[$k] : null;
				if ($old === null) {
					delete_post_meta($id, $k);
				} else {
					update_post_meta($id, $k, $old);
				}
				$n++;
			}
		}
		fwrite(STDERR, "rolled back: {$n} key operations\n");
		break;

	default:
		fwrite(STDERR, "usage: wp eval-file tools/b2d_h_migrate.php <dump|dry-run|apply|verify|rollback> [plan-or-prestate.json]\n");
		exit(1);
}
