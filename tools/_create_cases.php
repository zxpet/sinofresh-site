<?php
/**
 * Create 6 case-study articles (one per homepage Client Stories persona).
 * Idempotent: re-running updates existing posts matched by post_name.
 */
define('WP_USE_THEMES', false);
require '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';
require ABSPATH . 'wp-admin/includes/image.php';

function sf_block($inner) {
	return $inner;
}

function h2($t) {
	return "<!-- wp:heading {\"level\":2} -->\n<h2 class=\"wp-block-heading\">$t</h2>\n<!-- /wp:heading -->\n";
}
function p($t) {
	return "<!-- wp:paragraph -->\n<p>$t</p>\n<!-- /wp:paragraph -->\n";
}
function ul($items) {
	$s = "<!-- wp:list -->\n<ul class=\"wp-block-list\">\n";
	foreach ($items as $it) { $s .= "<!-- wp:list-item -->\n<li>$it</li>\n<!-- /wp:list-item -->\n"; }
	return $s . "</ul>\n<!-- /wp:list -->\n";
}
function table($rows) {
	$s = "<!-- wp:table {\"hasFixedLayout\":true,\"className\":\"sf-cs-profile\"} -->\n<figure class=\"wp-block-table sf-cs-profile\"><table><tbody>\n";
	foreach ($rows as $k => $v) { $s .= "<tr><td>$k</td><td>$v</td></tr>\n"; }
	return $s . "</tbody></table></figure>\n<!-- /wp:table -->\n";
}
function quote($text, $cite) {
	return "<!-- wp:quote -->\n<blockquote class=\"wp-block-quote\"><!-- wp:paragraph -->\n<p>\xE2\x80\x9C{$text}\xE2\x80\x9D</p>\n<!-- /wp:paragraph --><cite>{$cite}</cite></blockquote>\n<!-- /wp:quote -->\n";
}

function article_content($profile, $challenge, $solution_p, $solution_items, $result_p, $result_items, $products_p, $quote_text, $quote_cite) {
	return h2('Client Profile')
		. table($profile)
		. h2('The Challenge') . p($challenge)
		. h2('Our Solution') . p($solution_p) . ul($solution_items)
		. h2('The Result') . p($result_p) . ul($result_items)
		. h2('Products Involved') . p($products_p)
		. h2('Client Feedback') . quote($quote_text, $quote_cite)
		. h2('Start Your Own Story')
		. p('Planning a similar launch? <a href="/contact/">Request a quote</a> and our team will reply within one business day.');
}

$cases = array(
	array(
		'slug' => 'case-study-us-brand-owner-soft-chews',
		'title' => 'Case Study: U.S. Brand Owner Launches a Soft Chews Line with SINO FRESH',
		'date' => '2026-09-10 09:00:00',
		'excerpt' => 'How a first-time U.S. brand owner moved from idea to a retail-ready soft chews line with formulation and regulatory support from day one.',
		'img' => 'soft-chews.webp',
		'quote_text' => 'They handled formulation and regulatory support from day one.',
		'quote_cite' => 'Mark T., Brand Owner · USA',
		'profile' => array(
			'Client type' => 'Brand owner (first-time founder)',
			'Country' => 'United States',
			'Dosage form' => 'Soft chews · 3 SKUs',
			'Cooperation model' => 'ODM (formula from our library, customized)',
			'Timeline' => 'Brief to first shipment in 12 weeks',
		),
		'challenge' => 'The client wanted to enter the fast-growing joint and calming chew category but had no in-house formulator and no experience with U.S. supplement labeling rules. They needed one partner who could take responsibility for the formula, the compliance paperwork and the production run — not just fill an order to spec.',
		'solution_p' => 'We started from our standard soft chews library and tailored three formulas to the client’s target claims and price point, then handled the documentation trail end to end.',
		'solution_items' => array(
			'Formula customization from our ODM library, including flavor trials',
			'cGMP production in our ISO 8 cleanroom with batch COAs',
			'Support for U.S. labeling review and claim wording',
			'Export documentation prepared for U.S. customs clearance',
		),
		'result_p' => 'The client launched all three SKUs with a retail-ready presentation, and the first reorder was placed shortly after the initial sell-through.',
		'result_items' => array(
			'3 SKUs launched in the first production run',
			'12 weeks from first brief to shipment',
			'Reorder placed within 60 days of launch',
		),
		'products_p' => 'This project used our <a href="/products/soft-chews/">soft chews</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
	array(
		'slug' => 'case-study-germany-ecommerce-powders',
		'title' => 'Case Study: German E-Commerce Seller Builds an Amazon-Ready Powder Range',
		'date' => '2026-08-30 09:00:00',
		'excerpt' => 'Fast sampling, clear communication and complete export documentation helped an Amazon seller launch powder supplements before the Q4 rush.',
		'img' => 'powders.webp',
		'quote_text' => 'Fast sampling and clear communication. Exactly what we needed for our Amazon launch.',
		'quote_cite' => 'Sophie L., E-Commerce Seller · Germany',
		'profile' => array(
			'Client type' => 'E-commerce seller (Amazon FBA)',
			'Country' => 'Germany',
			'Dosage form' => 'Powders · 2 SKUs',
			'Cooperation model' => 'OEM (client formulas, our production)',
			'Timeline' => 'First samples in 14 days; live before Q4',
		),
		'challenge' => 'The seller had a hard Q4 deadline and a category where review velocity decides success. Any delay in sampling or customs would push the launch past the selling season. They also needed packaging that survives FBA handling and documentation complete enough to clear EU import without friction.',
		'solution_p' => 'We compressed the sampling loop and kept one point of contact throughout, so every iteration had an answer within a business day.',
		'solution_items' => array(
			'First samples produced within 14 days of the brief',
			'Two flavor and solubility iteration rounds before final sign-off',
			'Export and import documentation prepared for EU customs',
			'FBA-ready packaging with barcodes applied at our facility',
		),
		'result_p' => 'Both SKUs went live before Q4 with zero customs delays, and the launch review ratings supported immediate paid-traffic scaling.',
		'result_items' => array(
			'2 SKUs live before the Q4 selling season',
			'0 customs holds thanks to complete documentation',
			'Listing reviews started within the first selling month',
		),
		'products_p' => 'This project used our <a href="/products/powders/">powders</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
	array(
		'slug' => 'case-study-uk-distributor-tablets',
		'title' => 'Case Study: UK Distributor Standardizes Tablet Supply with One Facility',
		'date' => '2026-08-22 09:00:00',
		'excerpt' => 'Consistent quality and reliable lead times turned a one-off tablet order into a standing supply arrangement for a UK distributor.',
		'img' => 'tablets.webp',
		'quote_text' => 'Consistent quality and reliable lead times.',
		'quote_cite' => 'James K., Distributor · UK',
		'profile' => array(
			'Client type' => 'Distributor (multi-brand portfolio)',
			'Country' => 'United Kingdom',
			'Dosage form' => 'Tablets · 5 SKUs',
			'Cooperation model' => 'OEM (produce to client specification)',
			'Timeline' => 'Standing orders since the first PO',
		),
		'challenge' => 'The distributor previously split tablet production across several suppliers. Batch-to-batch variation created customer complaints, and lead times slipped without warning, which made stock planning for retail accounts nearly impossible.',
		'solution_p' => 'We consolidated the range into a single production schedule with fixed capacity windows and full traceability on every batch.',
		'solution_items' => array(
			'5 tablet SKUs consolidated into one facility',
			'Fixed production windows agreed per order cycle',
			'Batch COA and retention samples with every shipment',
			'In-process QC checks shared transparently with the client',
		),
		'result_p' => 'Lead times settled into a predictable rhythm, quality complaints dropped to zero, and the distributor extended the range instead of switching suppliers.',
		'result_items' => array(
			'Lead-time variance reduced to within one week',
			'Batch COA delivered with 100% of shipments',
			'Range extended from 3 to 5 SKUs after the first two orders',
		),
		'products_p' => 'This project used our <a href="/products/tablets/">tablets</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
	array(
		'slug' => 'case-study-spain-veterinary-drops',
		'title' => 'Case Study: Spanish Veterinary Clinic Launches Its Own Drops Brand',
		'date' => '2026-08-15 09:00:00',
		'excerpt' => 'Precise dosing and professional documentation let a Spanish veterinary clinic extend its practice into a private-label drops line.',
		'img' => 'drops.webp',
		'quote_text' => 'Precise dosing and professional documentation.',
		'quote_cite' => 'Dr. Elena M., Veterinarian · Spain',
		'profile' => array(
			'Client type' => 'Veterinary clinic (private label)',
			'Country' => 'Spain',
			'Dosage form' => 'Drops · 2 SKUs',
			'Cooperation model' => 'Private label',
			'Timeline' => 'Brief to clinic launch in 10 weeks',
		),
		'challenge' => 'A veterinary clinic stakes its reputation on every product it recommends. The team needed small first batches, veterinary-grade dosing accuracy, and specification documents rigorous enough to answer any professional question from colleagues or regulators.',
		'solution_p' => 'We built the project around dosing precision and documentation depth, treating the clinic’s professional standards as the design brief.',
		'solution_items' => array(
			'Calibrated droppers verified as part of batch QC',
			'Low first-batch MOQ suited to a clinic-scale launch',
			'Full specification sheets and per-batch COAs',
			'Under-the-radar labeling compliant with EU expectations',
		),
		'result_p' => 'The clinic launched its own-brand drops in-house and through its online portal, with the documentation pack proving useful in professional conversations from day one.',
		'result_items' => array(
			'MOQ 500 units per SKU for the first batch',
			'2 formulas launched under the clinic’s own brand',
			'Dosing hardware verified batch by batch',
		),
		'products_p' => 'This project used our <a href="/products/drops/">drops</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
	array(
		'slug' => 'case-study-australia-fish-oil-trading',
		'title' => 'Case Study: Australian Trading Company Sources Fish Oil at Flexible MOQ',
		'date' => '2026-08-08 09:00:00',
		'excerpt' => 'Flexible MOQ and competitive pricing helped a trading company test two fish oil SKUs without over-committing capital.',
		'img' => 'fish-oil.webp',
		'quote_text' => 'Flexible MOQ and competitive pricing.',
		'quote_cite' => 'David R., Trading Company · Australia',
		'profile' => array(
			'Client type' => 'Trading company',
			'Country' => 'Australia',
			'Dosage form' => 'Fish oil · 2 SKUs',
			'Cooperation model' => 'OEM',
			'Timeline' => 'Pilot order shipped in 9 weeks',
		),
		'challenge' => 'The trading company wanted to test Australian demand for pet fish oil but was unwilling to lock capital into a large first order in a price-sensitive category where untested SKUs can sit in a warehouse for months.',
		'solution_p' => 'We structured a pilot order with a low MOQ per SKU and tiered pricing that rewarded the scale-up path, so the client could test the market with controlled risk.',
		'solution_items' => array(
			'Pilot MOQ of 500 units per SKU',
			'Tiered pricing tied to the second-order volume',
			'Export documentation prepared for Australian import',
			'Batch COAs supporting retail account onboarding',
		),
		'result_p' => 'The pilot sold through, and the client returned with a substantially larger second order at the tiered price point.',
		'result_items' => array(
			'Pilot: 2 SKUs × 500 units',
			'Second order at 3× pilot volume',
			'Landed cost within the client’s target band',
		),
		'products_p' => 'This project used our <a href="/products/fish-oil/">fish oil</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
	array(
		'slug' => 'case-study-japan-pastes-palatability',
		'title' => 'Case Study: Japanese Brand Owner Refines a Cat Paste with Palatability Testing',
		'date' => '2026-08-01 09:00:00',
		'excerpt' => 'Iterative palatability testing made the difference for a Japanese brand entering the demanding cat paste category.',
		'img' => 'pastes.webp',
		'quote_text' => 'The palatability testing made a real difference.',
		'quote_cite' => 'Yuki S., Brand Owner · Japan',
		'profile' => array(
			'Client type' => 'Brand owner',
			'Country' => 'Japan',
			'Dosage form' => 'Pastes · 1 SKU, 2 flavors',
			'Cooperation model' => 'ODM',
			'Timeline' => '14 weeks including 3 palatability rounds',
		),
		'challenge' => 'Japanese cat owners are among the most demanding buyers in the category: a paste that a cat refuses even once will not be reordered. The brand needed proof of palatability before committing to packaging and launch marketing, not after.',
		'solution_p' => 'We treated palatability as the core deliverable, running the formula through structured test rounds and adjusting flavor and texture between each round.',
		'solution_items' => array(
			'ODM formula development from our paste line',
			'Three structured palatability test rounds with flavor adjustment',
			'Premium tube packaging suited to the Japanese retail channel',
			'Export documentation and labeling support for Japan',
		),
		'result_p' => 'The final formula cleared the client’s acceptance threshold, launched successfully, and a second flavor is now in development on the same platform.',
		'result_items' => array(
			'3 palatability rounds completed before launch',
			'First-choice acceptance above the client’s target in panel tests',
			'Second flavor in development for the same SKU platform',
		),
		'products_p' => 'This project used our <a href="/products/pastes/">pastes</a> line. Explore the full range on the <a href="/products/">products overview</a>.',
	),
);

$cat = get_term_by('slug', 'case-studies', 'category');
if (!$cat) { fwrite(STDERR, "case-studies term missing\n"); exit(1); }

$report = array();
foreach ($cases as $c) {
	$existing = get_page_by_path($c['slug'], OBJECT, 'post');
	$content = article_content(
		$c['profile'], $c['challenge'], $c['solution_p'], $c['solution_items'],
		$c['result_p'], $c['result_items'], $c['products_p'], $c['quote_text'], $c['quote_cite']
	);
	if ($existing) {
		$pid = $existing->ID;
		wp_update_post(array(
			'ID' => $pid,
			'post_title' => $c['title'],
			'post_content' => $content,
			'post_excerpt' => $c['excerpt'],
			'post_date' => $c['date'],
			'post_status' => 'publish',
		));
		$action = 'updated';
	} else {
		$pid = wp_insert_post(array(
			'post_type' => 'post',
			'post_status' => 'publish',
			'post_name' => $c['slug'],
			'post_title' => $c['title'],
			'post_content' => $content,
			'post_excerpt' => $c['excerpt'],
			'post_date' => $c['date'],
		), true);
		if (is_wp_error($pid)) { fwrite(STDERR, 'ERROR ' . $c['slug'] . ': ' . $pid->get_error_message() . "\n"); continue; }
		$action = 'created';
	}
	wp_set_object_terms($pid, array((int) $cat->term_id), 'category', false);

	/* Featured image: reuse existing attachment or register one pointing at the file. */
	$file = '2026/09/' . $c['img'];
	$att = get_posts(array(
		'post_type' => 'attachment', 'numberposts' => 1, 'fields' => 'ids',
		'meta_query' => array(array('key' => '_wp_attached_file', 'value' => $file)),
	));
	if ($att) {
		$att_id = (int) $att[0];
	} else {
		$att_id = wp_insert_attachment(array(
			'post_mime_type' => 'image/webp',
			'post_title' => preg_replace('/\.[a-z]+$/', '', $c['img']),
			'post_status' => 'inherit',
		), $file);
		if (!is_wp_error($att_id)) {
			update_post_meta($att_id, '_wp_attached_file', $file);
			$meta = wp_generate_attachment_metadata($att_id, '/Users/meng/Local Sites/sinofresh/app/public/wp-content/uploads/' . $file);
			wp_update_attachment_metadata($att_id, $meta);
		}
	}
	if (!is_wp_error($att_id) && $att_id) set_post_thumbnail($pid, $att_id);

	$report[] = sprintf("%s\tID:%d\tthumb:%s\t%s", $action, $pid, $att_id ?: '-', get_permalink($pid));
}
echo implode("\n", $report) . "\n";
