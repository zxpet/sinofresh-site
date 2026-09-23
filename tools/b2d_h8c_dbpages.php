<?php
/**
 * Batch H8c — the database half of the Services split.
 *
 * Four rows in wp_posts (post_type = page), all children of post 29
 * (slug `services`), so that the four cooperation-model cards on /services/
 * have somewhere to point:
 *
 *   /services/oem/                    slug oem                    page-oem.html
 *   /services/odm/                    slug odm                    page-odm.html
 *   /services/contract-manufacturing/ slug contract-manufacturing page-contract-manufacturing.html
 *   /services/private-label/          slug private-label          page-private-label.html
 *
 * Why this is needed at all: a block theme resolves page-{slug}.html only for a
 * page that exists. New template files alone leave /services/oem/ at the generic
 * page.html fallback, so the four detail pages are unreachable without the rows.
 *
 * post_content is deliberately empty. The theme template is the page — exactly
 * like the eight dosage pages (posts 20-27 all have empty post_content). Editing
 * a row here would not change a single served byte.
 *
 * Rollback. --dry-run writes the state of every slug it is about to touch to
 * _offroot/b2d-h8c-db-originals.json, and records nothing as created. --apply
 * refuses to run unless that snapshot exists and still describes the database
 * (parent id matches, every slug still absent), then writes the new post ids
 * back into the same file. --revert deletes exactly the ids recorded there and
 * verifies they are gone. The snapshot lives outside the docroot so it is not
 * web-reachable and survives a reboot; unlike /tmp it is a durable rollback.
 *
 * This is PHP and not .sql for the reason documented in b2d_h4e_dbpatch.php:
 * esc_sql() tokenises every % into a {sha256} placeholder that only the
 * wpdb->query filter removes, so a .sql file written from esc_sql() output bakes
 * the token in permanently.
 *
 * usage (mode comes from the environment — it survives the ssh hop and cannot
 * be mis-parsed by wp-cli's flag handling):
 *   SF_H8C_MODE=dry-run wp eval-file tools/b2d_h8c_dbpages.php
 *   SF_H8C_MODE=apply   wp eval-file tools/b2d_h8c_dbpages.php
 *   SF_H8C_MODE=verify  wp eval-file tools/b2d_h8c_dbpages.php
 *   SF_H8C_MODE=revert  wp eval-file tools/b2d_h8c_dbpages.php
 */
if (!defined('ABSPATH')) { fwrite(STDERR, "must run under wp eval-file\n"); exit(1); }

global $wpdb;

$PARENT_SLUG = 'services';
$PAGES = array(
	array('slug' => 'oem',                    'title' => 'OEM Manufacturing'),
	array('slug' => 'odm',                    'title' => 'ODM Development'),
	array('slug' => 'contract-manufacturing', 'title' => 'Contract Manufacturing'),
	array('slug' => 'private-label',          'title' => 'Private Label'),
);

$SNAP = '/var/www/dev.zxpet.com/_offroot/b2d-h8c-db-originals.json';
if (getenv('SF_H8C_SNAPSHOT')) { $SNAP = getenv('SF_H8C_SNAPSHOT'); }

$MODE = (string) getenv('SF_H8C_MODE');
$DRY    = ($MODE === 'dry-run');
$APPLY  = ($MODE === 'apply');
$REVERT = ($MODE === 'revert');
$VERIFY = ($MODE === 'verify');
if (!$DRY && !$APPLY && !$REVERT && !$VERIFY) {
	fwrite(STDERR, "SF_H8C_MODE must be one of: dry-run apply verify revert\n");
	exit(1);
}

/* ------------------------------------------------------------------ helpers */

/** Every page row whose post_name is one of the four slugs, any status, any parent. */
function sf_h8c_locator($slug) {
	global $wpdb;
	$rows = $wpdb->get_results($wpdb->prepare(
		"SELECT ID, post_name, post_title, post_status, post_parent FROM {$wpdb->posts}
		  WHERE post_type = 'page' AND post_name = %s ORDER BY ID", $slug), ARRAY_A);
	return $rows ? $rows : array();
}

/** The current, complete state of everything this batch is allowed to change. */
function sf_h8c_state($PARENT_SLUG, $PAGES) {
	global $wpdb;
	$parent = $wpdb->get_row($wpdb->prepare(
		"SELECT ID, post_name, post_title, post_status, post_parent FROM {$wpdb->posts}
		  WHERE post_type = 'page' AND post_name = %s AND post_status <> 'trash' ORDER BY ID", $PARENT_SLUG), ARRAY_A);

	$out = array(
		'parent' => $parent ? $parent : null,
		'pages'  => array(),
	);
	foreach ($PAGES as $p) {
		$rows = sf_h8c_locator($p['slug']);
		$norm = array();
		foreach ($rows as $r) {
			$norm[] = array(
				'id'          => (int) $r['ID'],
				'post_name'   => (string) $r['post_name'],
				'post_title'  => (string) $r['post_title'],
				'post_status' => (string) $r['post_status'],
				'post_parent' => (int) $r['post_parent'],
			);
		}
		$out['pages'][$p['slug']] = array(
			'slug'     => $p['slug'],
			'title'    => $p['title'],
			'existing' => $norm,
		);
	}
	return $out;
}

/** Anything already sitting on one of the four paths makes the batch unsafe. */
function sf_h8c_blockers($state) {
	$bad = array();
	if (!$state['parent'] || (int) $state['parent']['ID'] <= 0) {
		$bad[] = "the parent page (slug services) does not exist";
	}
	foreach ($state['pages'] as $slug => $p) {
		foreach ($p['existing'] as $r) {
			$bad[] = sprintf('slug %s is already taken by post %d (%s, parent %d)',
				$slug, $r['id'], $r['post_status'], $r['post_parent']);
		}
	}
	return $bad;
}

function sf_h8c_write_json($path, $data) {
	$dir = dirname($path);
	if (!is_dir($dir)) { mkdir($dir, 0755, true); }
	$json = wp_json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
	if ($json === false) { fwrite(STDERR, "json encode failed\n"); exit(1); }
	$tmp = $path . '.tmp';
	if (file_put_contents($tmp, $json . "\n") === false) { fwrite(STDERR, "cannot write $tmp\n"); exit(1); }
	rename($tmp, $path);
}

function sf_h8c_read_json($path) {
	if (!is_readable($path)) { return null; }
	$raw = file_get_contents($path);
	$d   = json_decode($raw, true);
	return is_array($d) ? $d : null;
}

function sf_h8c_line($s) { echo $s . "\n"; }

/* The identical() comparison is deliberately byte-exact on the fields that
   matter; an id that moved or a status that changed means the snapshot no
   longer describes this database and --apply must stop. */
function sf_h8c_same_pages($a, $b) {
	$k = function ($rows) {
		$out = array();
		foreach ($rows as $r) {
			$out[] = $r['id'] . ':' . $r['post_status'] . ':' . $r['post_parent'];
		}
		sort($out);
		return implode('|', $out);
	};
	return $k($a) === $k($b);
}

/* -------------------------------------------------------------------- start */

$state = sf_h8c_state($PARENT_SLUG, $PAGES);
$blockers = sf_h8c_blockers($state);

sf_h8c_line('== batch h8c / db pages ==');
sf_h8c_line('snapshot : ' . $SNAP);
sf_h8c_line('parent   : ' . ($state['parent'] ? sprintf('#%d %s (%s)', $state['parent']['ID'], $state['parent']['post_title'], $state['parent']['post_status']) : 'MISSING'));
foreach ($state['pages'] as $slug => $p) {
	sf_h8c_line(sprintf('  %-22s %s', $slug, $p['existing'] ? 'TAKEN by ' . json_encode($p['existing']) : 'absent'));
}
sf_h8c_line('mode     : ' . $MODE);

/* --------------------------------------------------------------- dry-run */
if ($DRY) {
	if ($blockers) {
		sf_h8c_line('REFUSING to snapshot: the crop is not clean —');
		foreach ($blockers as $b) { sf_h8c_line('  ! ' . $b); }
		exit(1);
	}
	$snap = array(
		'batch'      => 'h8c',
		'purpose'    => 'four /services/ child pages for the cooperation-model cards',
		'created_at' => gmdate('c'),
		'parent'     => array(
			'slug' => $PARENT_SLUG,
			'id'   => (int) $state['parent']['ID'],
			'path' => 'services',
		),
		'pages'      => array(),
		'applied_at' => null,
		'reverted_at'=> null,
	);
	foreach ($state['pages'] as $slug => $p) {
		$snap['pages'][] = array(
			'slug'          => $slug,
			'title'         => $p['title'],
			'url'           => '/services/' . $slug . '/',
			'existing_before' => $p['existing'],
			'created_id'    => null,
		);
	}
	sf_h8c_write_json($SNAP, $snap);
	sf_h8c_line('snapshot written — four absent slugs, nothing created yet');
	exit(0);
}

/* ----------------------------------------------------------------- apply */
if ($APPLY) {
	$snap = sf_h8c_read_json($SNAP);
	if (!$snap) { fwrite(STDERR, "REFUSING: $SNAP does not exist or is not JSON — run --dry-run first\n"); exit(1); }
	if ((int) $snap['parent']['id'] !== (int) $state['parent']['ID']) {
		fwrite(STDERR, sprintf("REFUSING: snapshot says parent is #%d, the database says #%d\n", $snap['parent']['id'], $state['parent']['ID']));
		exit(1);
	}
	foreach ($snap['pages'] as $sp) {
		$live = $state['pages'][$sp['slug']]['existing'];
		if (!sf_h8c_same_pages($sp['existing_before'], $live)) {
			fwrite(STDERR, sprintf("REFUSING: slug %s changed since the snapshot (%s -> %s)\n",
				$sp['slug'], json_encode($sp['existing_before']), json_encode($live)));
			exit(1);
		}
	}
	/* One further guard: --apply twice must not create a second set. */
	foreach ($snap['pages'] as $sp) {
		if (!empty($sp['created_id'])) {
			fwrite(STDERR, sprintf("REFUSING: slug %s is already recorded as created (#%d) — use --verify or --revert\n", $sp['slug'], $sp['created_id']));
			exit(1);
		}
	}
	if ($blockers) {
		fwrite(STDERR, "REFUSING: crop is not clean\n");
		foreach ($blockers as $b) { fwrite(STDERR, '  ! ' . $b . "\n"); }
		exit(1);
	}

	$parent_id = (int) $state['parent']['ID'];
	$made = array();
	foreach ($snap['pages'] as $i => $sp) {
		$id = wp_insert_post(array(
			'post_type'      => 'page',
			'post_status'    => 'publish',
			'post_title'     => $sp['title'],
			'post_name'      => $sp['slug'],
			'post_parent'    => $parent_id,
			'post_content'   => '',
			'comment_status' => 'closed',
			'ping_status'    => 'closed',
		), true);
		if (is_wp_error($id)) {
			fwrite(STDERR, sprintf("FAILED creating %s: %s\n", $sp['slug'], $id->get_error_message()));
			exit(1);
		}
		$id = (int) $id;
		$row = get_post($id);
		/* wp_insert_post quietly uniquifies a taken slug (oem -> oem-2). A
		   renamed row would 404 at the path the card points to, so this is a
		   hard stop, not a warning. */
		if (!$row || $row->post_name !== $sp['slug']) {
			fwrite(STDERR, sprintf("FAILED: wanted slug %s, WordPress stored %s (post #%d)\n",
				$sp['slug'], $row ? $row->post_name : 'NULL', $id));
			exit(1);
		}
		$snap['pages'][$i]['created_id'] = $id;
		$made[] = array('slug' => $sp['slug'], 'id' => $id, 'permalink' => get_permalink($id));
		sf_h8c_line(sprintf('created  #%-4d %-22s %s', $id, $sp['slug'], get_permalink($id)));
	}
	$snap['applied_at'] = gmdate('c');
	sf_h8c_write_json($SNAP, $snap);
	sf_h8c_line('applied — ' . count($made) . ' pages, ids written back into the snapshot');
	exit(0);
}

/* ---------------------------------------------------------------- verify */
if ($VERIFY) {
	$snap = sf_h8c_read_json($SNAP);
	$fail = 0;
	sf_h8c_line('-- verify --');
	foreach ($PAGES as $p) {
		$rows = sf_h8c_locator($p['slug']);
		$want = '/services/' . $p['slug'] . '/';
		if (count($rows) !== 1) {
			sf_h8c_line(sprintf('  FAIL %-22s expected exactly 1 page, found %d', $p['slug'], count($rows)));
			$fail++;
			continue;
		}
		$r    = $rows[0];
		$id   = (int) $r['ID'];
		$post = get_post($id);
		$path = (string) wp_parse_url(get_permalink($id), PHP_URL_PATH);
		$ok   = ((string) $r['post_status'] === 'publish')
		     && ((int) $r['post_parent'] === (int) $state['parent']['ID'])
		     && ($path === $want)
		     && ($post && trim((string) $post->post_content) === '');
		if (!$ok) { $fail++; }
		sf_h8c_line(sprintf('  %-4s %-22s #%-4d %-8s parent=%-3d path=%-32s title=%s',
			$ok ? 'ok' : 'FAIL', $p['slug'], $id, $r['post_status'], (int) $r['post_parent'], $path, $r['post_title']));
	}
	if ($snap) {
		sf_h8c_line('  snapshot applied_at = ' . ($snap['applied_at'] ? $snap['applied_at'] : 'NULL'));
	} else {
		sf_h8c_line('  WARN snapshot missing — cannot cross-check ids');
	}
	sf_h8c_line($fail ? "verify FAILED ($fail)" : 'verify PASSED (4/4)');
	exit($fail ? 1 : 0);
}

/* ---------------------------------------------------------------- revert */
if ($REVERT) {
	$snap = sf_h8c_read_json($SNAP);
	if (!$snap) { fwrite(STDERR, "REFUSING: $SNAP does not exist\n"); exit(1); }
	$fail = 0;
	foreach ($snap['pages'] as $i => $sp) {
		$id = (int) $sp['created_id'];
		if ($id <= 0) { sf_h8c_line(sprintf('  skip %-22s never created', $sp['slug'])); continue; }
		$post = get_post($id);
		if (!$post) { sf_h8c_line(sprintf('  skip %-22s #%d already gone', $sp['slug'], $id)); continue; }
		if ($post->post_name !== $sp['slug'] || (int) $post->post_parent !== (int) $snap['parent']['id']) {
			fwrite(STDERR, sprintf("REFUSING to delete #%d: it is not the row we created (%s / parent %d)\n",
				$id, $post->post_name, (int) $post->post_parent));
			exit(1);
		}
		$del = wp_delete_post($id, true);
		if (!$del) { fwrite(STDERR, sprintf("FAILED deleting #%d\n", $id)); $fail++; continue; }
		if (get_post($id)) { fwrite(STDERR, sprintf("FAILED: #%d still resolves after delete\n", $id)); $fail++; continue; }
		$snap['pages'][$i]['created_id'] = null;
		$snap['pages'][$i]['reverted_id'] = $id;
		sf_h8c_line(sprintf('  deleted #%-4d %s', $id, $sp['slug']));
	}
	$snap['reverted_at'] = gmdate('c');
	sf_h8c_write_json($SNAP, $snap);
	sf_h8c_line($fail ? "revert INCOMPLETE ($fail)" : 'revert done');
	exit($fail ? 1 : 0);
}
