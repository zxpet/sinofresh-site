#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step 1 — idempotent rewriter for the
"Active Ingredients & Guaranteed Analysis" band.

Writes, in this order:
  1. functions.php   — two pure parsers + the [sf_formula_actives] shortcode,
                       inserted right after add_shortcode('sf_formula_grid', …);
  2. templates/page-{slug}.html  x8 — the sf-actives group block, located by a
                       byte-identical anchor that must occur exactly once;
  3. style.css       — the band's CSS, appended at end of file;
  4. version bump    2.10.44 -> 2.10.45 in functions.php + style.css.

Every step asserts its own preconditions and re-reads what it wrote, so a
half-applied run is impossible: it either rewrites all ten files or it aborts
before touching any.

Usage:
    python3 tools/b2d_s1_apply.py --check     # dry run, prints the plan
    python3 tools/b2d_s1_apply.py --apply     # writes the files
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(HERE), "sinofresh-theme")

SLUGS = [
    "soft-chews", "tablets", "powders", "pastes",
    "drops", "liquids", "fish-oil", "dental-chews",
]

OLD_VER = "2.10.44"
NEW_VER = "2.10.45"

# The 4-line anchor the eight templates share. sha256[:16] = e2c5d61e6997f0d3
ANCHOR = "</table>\n<!-- /wp:html -->\n</section>\n<!-- /wp:group -->\n\n"
ANCHOR_SHA16 = "e2c5d61e6997f0d3"

# Anchor inside functions.php: the last line of [sf_formula_grid].
PHP_ANCHOR = "add_shortcode('sf_formula_grid', 'sinofresh_formula_grid');\n"

# --------------------------------------------------------------------------- #
# 1. functions.php additions
# --------------------------------------------------------------------------- #

PHP_ADDITION = r'''
/**
 * Split an "a, b, c" meta value on its top-level commas.
 *
 * The comma is the separator every sf_formula_ingredients value uses, and it
 * can also legitimately appear INSIDE a parenthesised share — "Tapioca (46%),
 * Peas (29%)" separates at depth 0 only. Today all 21 records split identically
 * either way (tools/b2d1_parser_dryrun.php §1), so this is defensive rather
 * than load-bearing: it costs a depth counter and removes a silent wrong split
 * if content ever writes "X (a, b), Y".
 *
 * Byte-wise on purpose: "(" ")" "," are ASCII and every UTF-8 continuation
 * byte is >= 0x80, so multi-byte terms pass through untouched.
 *
 * Returns a trimmed list with empty segments dropped; '' and whitespace give an
 * empty array, never one empty element.
 */
function sinofresh_formula_split_top_level($value) {
	$value = (string) $value;
	if (trim($value) === '') {
		return array();
	}
	$out   = array();
	$depth = 0;
	$cur   = '';
	$len   = strlen($value);
	for ($i = 0; $i < $len; $i++) {
		$ch = $value[$i];
		if ($ch === '(') {
			$depth++;
		} elseif ($ch === ')') {
			if ($depth > 0) {
				$depth--;
			}
		}
		if ($ch === ',' && $depth === 0) {
			$out[] = trim($cur);
			$cur   = '';
			continue;
		}
		$cur .= $ch;
	}
	$out[] = trim($cur);
	return array_values(array_filter($out, function ($s) { return $s !== ''; }));
}

/**
 * Turn "Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew" into term/value pairs
 * for the guaranteed-analysis table.
 *
 * Each segment splits at its FIRST U+2265 (≥), so the level half keeps any
 * further text verbatim ("Omega-3 ≥30%" → term "Omega-3", value "≥30%"). A
 * segment with no ≥ is kept as a term with an empty value — the caller decides
 * — while a value with no subject is dropped here, because that is not a row.
 */
function sinofresh_formula_analysis_pairs($value) {
	$pairs = array();
	foreach (sinofresh_formula_split_top_level($value) as $part) {
		$pos = strpos($part, "\xE2\x89\xA5"); // U+2265 GREATER-THAN OR EQUAL TO
		if ($pos === false) {
			$pairs[] = array('term' => $part, 'value' => '');
			continue;
		}
		$term  = rtrim(substr($part, 0, $pos));
		$level = ltrim(substr($part, $pos));
		if ($term === '' || $level === '') {
			continue;
		}
		$pairs[] = array('term' => $term, 'value' => $level);
	}
	return $pairs;
}

/**
 * [sf_formula_actives form="soft-chews"] — the "Active Ingredients &
 * Guaranteed Analysis" band on the eight dosage pages.
 *
 * Reads the same post meta [sf_formula_detail] reads (sf_formula_ingredients,
 * sf_formula_analysis), so the formula record stays the single source of truth
 * and stays editable in wp-admin: the eight block templates sit behind the
 * authority guard, post meta does not.
 *
 * Server-side by necessity. The K2 JSON mirror is a [sf_formula_grid]
 * by-product, so reading it would mean keeping the grid on the page, painting
 * nothing without JavaScript, and coupling this band to the grid. Querying the
 * records directly is crawlable, degrades to plain HTML, and cannot be broken
 * by editing the cards.
 *
 * Emits no JSON and no ItemList of its own: the page already carries the grid's
 * ItemList and the dosage Product schema, and a second copy would only
 * duplicate them. Returns '' when the dosage form has no published formula, so
 * the band collapses instead of leaving an empty padded section — the same
 * convention [sf_formula_body] follows.
 *
 * The query mirrors [sf_formula_grid]'s exactly (same post type, status,
 * orderby, tax_query) so a recipe holds the same position in the table as its
 * card holds in the grid above it.
 *
 * Labels are plain English literals, not gettext: that is how the eight
 * templates' own copy is written (and how [sf_formula_grid] writes "View
 * formula →"), so these strings land on the same TranslatePress path as the
 * rest of the page. No TP strings are registered in this batch.
 */
function sinofresh_formula_actives($atts = array()) {
	$atts = shortcode_atts(array('form' => ''), $atts, 'sf_formula_actives');
	$form = sinofresh_formula_current_form($atts['form']);

	$args = array(
		'post_type'           => 'sf_formula',
		'post_status'         => 'publish',
		'posts_per_page'      => -1,
		'orderby'             => array('menu_order' => 'ASC', 'title' => 'ASC'),
		'ignore_sticky_posts' => true,
		'no_found_rows'       => true,
	);
	if ($form !== '') {
		$args['tax_query'] = array(
			array('taxonomy' => 'sf_formula_form', 'field' => 'slug', 'terms' => $form),
		);
	}
	$formulas = get_posts($args);
	if (!$formulas) {
		return '';
	}

	$items = '';
	foreach ($formulas as $formula) {
		/* One authoritative name string, decoded once and re-escaped per
		   context — the rule [sf_formula_grid] follows ("Skin & Coat Soft
		   Chews" is stored entity-encoded). */
		$name = html_entity_decode(get_the_title($formula), ENT_QUOTES, 'UTF-8');
		if ($name === '') {
			continue;
		}
		$ingredients = trim((string) get_post_meta($formula->ID, 'sf_formula_ingredients', true));
		$analysis    = trim((string) get_post_meta($formula->ID, 'sf_formula_analysis', true));
		if ($ingredients === '' && $analysis === '') {
			continue;
		}

		$body = '<h3 class="sf-actives__name">' . esc_html($name) . '</h3>';

		$pills = '';
		foreach (sinofresh_formula_split_top_level($ingredients) as $term) {
			$pills .= '<li class="sf-actives__pill">' . esc_html($term) . '</li>';
		}
		if ($pills !== '') {
			$body .= '<p class="sf-actives__label">' . esc_html('Ingredients') . '</p>'
				. '<ul class="sf-actives__ing">' . $pills . '</ul>';
		}

		/* A segment with no level, or with no subject, is not a row: the dry
		   run (tools/b2d1_parser_dryrun.php §2/§3) finds zero such segments
		   in the 21 live records, and rendering one would emit an empty <dd>. */
		$rows = '';
		foreach (sinofresh_formula_analysis_pairs($analysis) as $pair) {
			if ($pair['term'] === '' || $pair['value'] === '') {
				continue;
			}
			$rows .= '<div class="sf-spec-row">'
				. '<dt class="sf-spec-term">' . esc_html($pair['term']) . '</dt>'
				. '<dd class="sf-spec-value">' . esc_html($pair['value']) . '</dd>'
				. '</div>';
		}
		if ($rows !== '') {
			$body .= '<p class="sf-actives__label">' . esc_html('Guaranteed Analysis') . '</p>'
				. '<dl class="sf-spec-list">' . $rows . '</dl>';
		}

		$items .= '<article class="sf-actives__item">' . $body . '</article>';
	}
	if ($items === '') {
		return '';
	}

	$label = sinofresh_formula_label($form);
	if ($label === '') {
		$label = 'dosage';
	}

	return '<div class="sf-actives__inner">'
		. '<h2 class="sf-actives__title">' . esc_html('Active Ingredients & Guaranteed Analysis') . '</h2>'
		. '<p class="sf-actives__intro">' . esc_html(sprintf(
			'Every formula in our standard %s range, with the ingredient list and the guaranteed analysis we hold to in production. Use one as a starting point, or ask us to adjust the actives and the levels for your own label.',
			$label
		)) . '</p>'
		. '<div class="sf-actives__list">' . $items . '</div>'
		. '</div>';
}
add_shortcode('sf_formula_actives', 'sinofresh_formula_actives');
'''

# --------------------------------------------------------------------------- #
# 2. template block
# --------------------------------------------------------------------------- #

# NOTE: no str.format() here on purpose — the wp:group attributes carry balanced
# braces that a format string would eat. __FORM__ is substituted verbatim.
TPL = """<!-- B2D-S1: actives -->
<!-- wp:group {"tagName":"section","anchor":"actives","className":"sf-actives","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section id="actives" class="wp-block-group sf-actives" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:html -->
[sf_formula_actives form="__FORM__"]
<!-- /wp:html -->
</section>
<!-- /wp:group -->

"""

# Byte-for-byte the same container markup block 2 (#formulas) uses on all eight
# pages, so this is the one container form the Site Editor has round-tripped.
TPL_REF = '<!-- wp:group {"tagName":"section","anchor":"formulas","className":"sf-formulas"'

# --------------------------------------------------------------------------- #
# 3. style.css addition
# --------------------------------------------------------------------------- #

CSS_ADDITION = """/* B2D Step1 — Active Ingredients & Guaranteed Analysis band on the eight
   dosage pages. One recipe per block, hairline-separated: the band sits on
   the white section, so card chrome would not read. The guaranteed-analysis
   table is the compact .sf-spec-list grid defined above (section "Compact
   8-row spec list"), reused here with <dt>/<dd> — the correct semantics for a
   term/value pair, and structurally out of reach of the dosage-page Product
   JSON-LD parser, which matches <span class="sf-spec-term">…</span>
   <span class="sf-spec-value">…</span> on the template file. ------------- */
.sf-actives__title { margin: 0; }
.sf-actives__intro {
\tmax-width: 720px;
\tmargin-top: 10px;
\tfont-size: 15px;
\tcolor: var(--wp--preset--color--text-secondary);
}
.sf-actives__list { margin-top: 30px; }
.sf-actives__item + .sf-actives__item {
\tmargin-top: 28px;
\tpadding-top: 28px;
\tborder-top: 1px solid var(--wp--preset--color--border-light);
}
.sf-actives__name { margin: 0; font-size: 17px; }
.sf-actives__label {
\tmargin: 16px 0 0;
\tfont-size: 11px;
\tfont-weight: 600;
\tletter-spacing: 0.08em;
\ttext-transform: uppercase;
\tcolor: var(--wp--preset--color--text-secondary);
}
/* Ingredient pills. Deliberately NOT .sf-fchip: that class carries
   cursor:pointer and a hover/.is-active state because it is a filter button —
   the wrong affordance on a static term. Outline pill mirrors the
   .sf-topbar-badges certificate pill, the site's existing pill vocabulary. */
.sf-actives__ing {
\tdisplay: flex;
\tflex-wrap: wrap;
\tgap: 8px;
\tmargin: 10px 0 0;
\tpadding: 0;
\tlist-style: none;
}
.sf-actives__pill {
\tpadding: 3px 10px;
\tborder: 1px solid var(--wp--preset--color--border-light);
\tborder-radius: 999px;
\tfont-size: 13px;
\tline-height: 1.5;
\tcolor: var(--wp--preset--color--text-primary);
}
/* <dl> ships margin-block 1em and <dd> margin-inline-start 40px — the reused
   .sf-spec-list grid needs both neutralised inside this band. */
.sf-actives .sf-spec-list { margin: 10px 0 0; }
.sf-actives .sf-spec-term,
.sf-actives .sf-spec-value { margin: 0; }
"""


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def plan():
    """Return the list of (label, path, new_bytes) and abort on any precondition."""
    assert sha16(ANCHOR) == ANCHOR_SHA16, "anchor constant drifted"

    out = []

    # ---- functions.php -----------------------------------------------------
    php_path = os.path.join(THEME, "functions.php")
    php = open(php_path, "r", encoding="utf-8", newline="").read()

    n_anchor = php.count(PHP_ANCHOR)
    assert n_anchor == 1, "functions.php anchor hit %d times (want 1)" % n_anchor
    assert "function sinofresh_formula_actives(" not in php, "shortcode already present"
    assert php.count(OLD_VER) == 1, "functions.php holds %d x %s (want 1)" % (
        php.count(OLD_VER), OLD_VER)

    php_new = php.replace(PHP_ANCHOR, PHP_ANCHOR + PHP_ADDITION, 1)
    php_new = php_new.replace("'" + OLD_VER + "'", "'" + NEW_VER + "'", 1)
    assert "function sinofresh_formula_actives(" in php_new
    assert php_new.count(NEW_VER) == 1 and php_new.count(OLD_VER) == 0
    out.append(("functions.php", php_path, php_new))

    # ---- the eight templates ----------------------------------------------
    for slug in SLUGS:
        tpl_path = os.path.join(THEME, "templates", "page-%s.html" % slug)
        tpl = open(tpl_path, "r", encoding="utf-8", newline="").read()
        assert tpl.count(ANCHOR) == 1, "%s: anchor hit %d times (want 1)" % (
            slug, tpl.count(ANCHOR))
        assert "B2D-S1" not in tpl, "%s: block already inserted" % slug
        block = TPL.replace("__FORM__", slug)
        tpl_new = tpl.replace(ANCHOR, ANCHOR + block, 1)
        assert tpl_new.count("B2D-S1: actives") == 1
        assert tpl_new.count('id="actives"') == 1
        out.append(("templates/page-%s.html" % slug, tpl_path, tpl_new))

    # ---- style.css ---------------------------------------------------------
    css_path = os.path.join(THEME, "style.css")
    css = open(css_path, "r", encoding="utf-8", newline="").read()
    assert ".sf-actives__pill" not in css, "style.css already holds the band"
    assert css.count("Version: " + OLD_VER) == 1, "style.css Version line not unique"
    assert css.endswith("\n"), "style.css does not end with a newline"

    css_new = css + CSS_ADDITION
    css_new = css_new.replace("Version: " + OLD_VER, "Version: " + NEW_VER, 1)
    assert css_new.count(NEW_VER) == 1 and OLD_VER not in css_new
    out.append(("style.css", css_path, css_new))

    return out


def self_check(items):
    """Re-parse what we are about to write, independently of plan()."""
    for label, _path, body in items:
        if label == "functions.php":
            assert body.count("function sinofresh_formula_split_top_level(") == 1
            assert body.count("function sinofresh_formula_analysis_pairs(") == 1
            assert body.count("function sinofresh_formula_actives(") == 1
            assert body.count("add_shortcode('sf_formula_actives'") == 1
            # the two helpers must stay byte-identical to the dry-run fixture
            fixture = open(os.path.join(HERE, "b2d1_parser_dryrun.php"),
                           "r", encoding="utf-8", newline="").read()

            def grab(text, name):
                m = re.search(r"function %s\(\$value\) \{.*?\n\}\n" % name, text, re.S)
                assert m, "cannot extract %s" % name
                return m.group(0)

            for fn in ("sinofresh_formula_split_top_level",
                       "sinofresh_formula_analysis_pairs"):
                assert grab(body, fn) == grab(fixture, fn), \
                    "%s drifted from the dry-run fixture" % fn
        elif label.startswith("templates/"):
            slug = re.search(r"page-(.+)\.html", label).group(1)
            # the pages already carry other `form="…"` shortcodes (block 2's
            # grid), so scope the assertion to the segment we inserted.
            seg_start = body.index("<!-- B2D-S1: actives -->")
            seg_end = body.index("<!-- Block 9: How We Work -->")
            seg = body[seg_start:seg_end]
            assert seg.count('form="%s"' % slug) == 1, label
            assert seg.count('<section id="actives"') == 1, label
            assert seg.count("<!-- /wp:group -->") == 1, label
            # the container must be block 2's own serialisation, with only
            # anchor + className swapped — that is the one form the Site
            # Editor round-trips, so nothing here is invented.
            ref_line = [l for l in body.split("\n") if '"anchor":"formulas"' in l]
            assert len(ref_line) == 1, "%s: block 2 comment not unique" % slug
            want = ref_line[0].replace("formulas", "actives")
            assert seg.count(want) == 1, "%s: group comment diverges from block 2" % slug
            ref_sec = [l for l in body.split("\n") if '<section id="formulas"' in l]
            assert len(ref_sec) == 1, "%s: block 2 section not unique" % slug
            assert seg.count(ref_sec[0].replace("formulas", "actives")) == 1, \
                "%s: section tag diverges from block 2" % slug
        elif label == "style.css":
            assert body.count(".sf-actives__pill {") == 1
            assert body.count("Version: " + NEW_VER) == 1


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--check", "--apply"):
        print("usage: b2d_s1_apply.py [--check|--apply]")
        return 2

    items = plan()
    self_check(items)

    print("%-28s %10s %10s %10s" % ("file", "bytes", "->", "delta"))
    for label, _path, body in items:
        old = len(open(_path, "rb").read())
        new = len(body.encode("utf-8"))
        print("%-28s %10d %10s %+10d" % (label, old, new, new - old))
    print("\n10 files staged, all preconditions asserted.")

    if mode == "--check":
        print("dry run — nothing written.")
        return 0

    for label, path, body in items:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        back = open(path, "r", encoding="utf-8", newline="").read()
        assert back == body, "read-back mismatch on %s" % label
    print("written and read back ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
