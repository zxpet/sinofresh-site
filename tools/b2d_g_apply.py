#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch G — the four source edits, each self-proving.

  facts   eight dosage templates: a fourth .sf-facts-mini row,
          data-label="Packaging formats", value transcribed from the same
          template's own configurator option set (data-group="packaging"),
          minus the trailing "Custom", plus ", or custom formats" (decision
          III: the comma form reads as a list on all eight, and soft-chews'
          own "Box + Foil" would otherwise produce a third "+").
  media   single-sf_formula.html: the gallery section stops being a top-level
          band and becomes the left column of a two-column grid, with a new
          right column (intro / facts / CTA) beside it.
  php     functions.php: sinofresh_formula_specs_parts(), _intro(),
          [sf_formula_factsheet], the {{FORMULA_INTRO}} placeholder, and the
          version bump.
  css     style.css: the .sf-fdetail-media namespace, and the version bump.

Every part asserts its anchors before writing, then reads the file back and
undoes its own splice — a part that cannot reproduce its input byte-for-byte
is not a clean splice and the gate must not trust the same span.

No wp:group comments are self-closing here: they carry inner blocks, so the
theme's convention (and the engine's) is `-->`, not ` /-->`.

usage:
    python3 tools/b2d_g_apply.py --check
    python3 tools/b2d_g_apply.py --apply --backup-dir DIR [--part facts]
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, '..', 'sinofresh-theme')
TPL = os.path.join(THEME, 'templates')

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()

FROM_VER, TO_VER = '2.10.53', '2.10.54'

# --- part: facts ----------------------------------------------------------
# The facts band's own close, immediately followed by the card-wall group open:
# unique per template (the card wall is the only anchored "formulas" section).
FACTS_SEAM = ('</section>\n<!-- /wp:html -->\n\n'
              '<!-- wp:group {"tagName":"section","anchor":"formulas"')
ROW_FMT = ('<div class="sf-facts-mini__item">'
           '<span class="sf-facts-mini__label">Packaging</span> '
           '<span class="sf-facts-mini__value" data-label="Packaging formats">'
           '%s</span></div>\n')
PACK_SUFFIX = ', or custom formats'


def packaging_value(form):
    """The form's configurator packaging options, as the row's value.

    Read out of the template rather than restated: the row has to be the
    option set the configurator actually offers, or the page contradicts
    itself. The trailing "Custom" option is dropped (it is the configurator
    free-text escape hatch, not a format) and the list closes with the same
    ", or custom formats" the eight pages share.
    """
    html = open(os.path.join(TPL, 'page-%s.html' % form), encoding='utf-8').read()
    m = re.search(r'<div class="configurator__group" data-group="packaging"[^>]*>'
                  r'(.*?)\n    </div>', html, re.S)
    if not m:
        return None
    values = re.findall(r'data-value="([^"]+)"', m.group(1))
    if not values:
        return None
    if values[-1].strip().lower() != 'custom':
        # If the option set ever stops ending in Custom the transcription rule
        # below is no longer the whole story, and silently appending a suffix
        # would ship a value nobody chose. Refuse instead.
        raise SystemExit('%s: configurator packaging options do not end in '
                         '"Custom" (last=%r)' % (form, values[-1]))
    return ', '.join(values[:-1]) + PACK_SUFFIX


# --- part: media ----------------------------------------------------------
MEDIA_OLD = (
    '<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery",'
    '"backgroundColor":"bg-light","layout":{"type":"constrained"},'
    '"style":{"spacing":{"padding":{"top":"var:preset|spacing|80",'
    '"bottom":"var:preset|spacing|80"}}}} -->\n'
    '<section id="gallery" class="wp-block-group sf-gallery has-bg-light-background-color '
    'has-background" style="padding-top:var(--wp--preset--spacing--80);'
    'padding-bottom:var(--wp--preset--spacing--80)">\n'
    '<!-- wp:html -->\n[sf_formula_gallery]\n<!-- /wp:html -->\n'
    '</section>\n<!-- /wp:group -->')

PAD = ('"style":{"spacing":{"padding":{"top":"var:preset|spacing|80",'
       '"bottom":"var:preset|spacing|80"}}}')
PAD_ATTR = ('style="padding-top:var(--wp--preset--spacing--80);'
            'padding-bottom:var(--wp--preset--spacing--80)"')

# The background hangs on the new outer section only: on the left column it
# would paint a slab half the width of the band and read as two stacked
# pieces instead of one two-column band.
MEDIA_NEW = (
    '<!-- Batch G: media + facts, two columns. The background belongs to the\n'
    '     outer section only; the columns carry none, so the band reads as one\n'
    '     surface. #gallery, its h2 and all four slides are kept — only the\n'
    '     nesting changes. -->\n'
    '<!-- wp:group {"tagName":"section","className":"sf-fdetail-media",'
    '"backgroundColor":"bg-light","layout":{"type":"constrained"},' + PAD + '} -->\n'
    '<section class="wp-block-group sf-fdetail-media has-bg-light-background-color '
    'has-background" ' + PAD_ATTR + '>\n'
    '<!-- wp:group {"className":"sf-fdetail-media__inner","layout":{"type":"default"}} -->\n'
    '<div class="wp-block-group sf-fdetail-media__inner">\n'
    '<!-- wp:group {"tagName":"section","anchor":"gallery",'
    '"className":"sf-gallery sf-fdetail-media__left","layout":{"type":"default"}} -->\n'
    '<section id="gallery" class="wp-block-group sf-gallery sf-fdetail-media__left">\n'
    '<!-- wp:html -->\n[sf_formula_gallery]\n<!-- /wp:html -->\n'
    '</section>\n'
    '<!-- /wp:group -->\n'
    '<!-- wp:group {"tagName":"aside","className":"sf-fdetail-media__side",'
    '"layout":{"type":"default"}} -->\n'
    '<aside class="wp-block-group sf-fdetail-media__side">\n'
    '<!-- wp:html -->\n'
    '{{FORMULA_INTRO}}\n'
    '[sf_formula_factsheet]\n'
    '<a class="sf-fdetail-media__cta" href="/contact/">Request Sample</a>\n'
    '<!-- /wp:html -->\n'
    '</aside>\n'
    '<!-- /wp:group -->\n'
    '</div>\n'
    '<!-- /wp:group -->\n'
    '</section>\n'
    '<!-- /wp:group -->')


# --- part: php ------------------------------------------------------------
PHP_INIT_OLD = "\t$formula_use = '';\n\t$formula_meta = '';\n"
PHP_INIT_NEW = "\t$formula_use = '';\n\t$formula_meta = '';\n\t$formula_intro = '';\n"

PHP_FUNCS_OLD = """	return $cache[$key];
}

/**
 * wp_json_encode() for the body of an inline <script>."""

PHP_FUNCS_NEW = """	return $cache[$key];
}

/**
 * The three facts buried in a formula's one-line sf_formula_specs value.
 *
 * The meta is free text with " · " separators, and it is NOT uniform: ten
 * records carry three segments (unit / pack / shelf life), eleven carry two
 * (unit / combined pack-and-shelf-life), so a positional reader takes the
 * shelf life as the pack options on those eleven. Fields are therefore taken
 * by KEY REGEX, never by index:
 *
 *   shelf  the segment matching /\\d+ months? shelf life/
 *   pack   of what is left, the segment matching /\\sper\\s/
 *   unit   the first segment that is left
 *
 * The pack pattern needs the surrounding whitespace. A bare /per (bottle|...)/ 
 * also matches the "per bottle" inside "dropper bottle", measured on this data
 * as two false positives out of twelve hits; /\\sper\\s/ gives the true ten.
 *
 * Returns '' for anything it cannot find, so callers drop the row rather than
 * print an empty "Pack options". (Decision I: the eleven records without a
 * pack segment show four rows, the ten with one show five. Substituting the
 * packaging formats there would put container names under a quantity label.)
 */
function sinofresh_formula_specs_parts($specs) {
	$parts = array('unit' => '', 'pack' => '', 'shelf' => '');
	$specs = trim((string) $specs);
	if ($specs === '') {
		return $parts;
	}
	$segments = array();
	foreach (explode('·', $specs) as $segment) {
		$segment = trim($segment);
		if ($segment !== '') {
			$segments[] = $segment;
		}
	}
	$rest = array();
	foreach ($segments as $segment) {
		if ($parts['shelf'] === '' && preg_match('/\\d+\\s*months?\\s+shelf\\s+life/i', $segment)) {
			$parts['shelf'] = $segment;
			continue;
		}
		$rest[] = $segment;
	}
	$unit = array();
	foreach ($rest as $segment) {
		if ($parts['pack'] === '' && preg_match('/\\sper\\s/i', $segment)) {
			$parts['pack'] = $segment;
			continue;
		}
		$unit[] = $segment;
	}
	if ($unit) {
		$parts['unit'] = $unit[0];
	}
	return $parts;
}

/**
 * The intro paragraph of a formula's media column.
 *
 * Same wording root as the Product schema's description on this page
 * (wp_head, sf_formula Product): the first sentence is the same sentence, so
 * the visible copy and the structured data cannot drift apart. It is not the
 * same function on purpose — the schema generator's output is covered by the
 * JSON-LD gate, which must stay at zero change, and a shared function would
 * put this batch inside that path.
 *
 * sf_formula_intro (post meta) overrides the whole paragraph when set. That
 * is the slot the 21 real product blurbs go into later; until then every
 * record renders the template, which is why the template must read as a
 * finished sentence rather than a stub.
 *
 * {moq} and {lead_time} are the dosage page's own values (spec_cell is the
 * single source): a missing one drops its clause instead of printing an
 * empty label, the same rule {{FORMULA_META}} follows. Both values are
 * transcribed verbatim, so the sentence is built as "Label: value." rather
 * than "a minimum order of {moq}" — the values already read as clauses
 * ("from 500-1,000 units"), and glueing prepositions on would produce
 * "a minimum order of from 500-1,000 units".
 */
function sinofresh_formula_intro($post_id = 0) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		$post_id = (int) get_queried_object_id();
	}
	if ($post_id <= 0 || get_post_type($post_id) !== 'sf_formula') {
		return '';
	}
	$override = trim((string) get_post_meta($post_id, 'sf_formula_intro', true));
	if ($override !== '') {
		return $override;
	}
	$name = html_entity_decode((string) get_the_title($post_id), ENT_QUOTES, 'UTF-8');
	if ($name === '') {
		return '';
	}
	$form_slug  = '';
	$form_label = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug  = (string) $form_terms[0]->slug;
		$form_label = sinofresh_formula_label($form_terms[0]->slug, $form_terms[0]->name);
	}
	$text = $form_label !== ''
		? sprintf('%s is a standard %s formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name, $form_label)
		: sprintf('%s is a standard formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name);
	$text .= ' Produced in a GMP-certified facility in Linyi, China and shipped with full documentation, '
		. 'it is ready for your own brand.';
	if ($form_slug !== '') {
		$moq = sinofresh_formula_spec_cell($form_slug, 'MOQ');
		if ($moq !== '') {
			$text .= ' Minimum order quantity: ' . $moq . '.';
		}
		$lead = sinofresh_formula_spec_cell($form_slug, 'Lead time');
		if ($lead !== '') {
			$text .= ' Lead time: ' . $lead . '.';
		}
	}
	return $text;
}

/**
 * wp_json_encode() for the body of an inline <script>."""

PHP_SHORTCODE_ANCHOR = "add_shortcode('sf_formula_detail', 'sinofresh_formula_detail');\n"

PHP_SHORTCODE_NEW = PHP_SHORTCODE_ANCHOR + """
/**
 * [sf_formula_factsheet] - the media column's five-row specification list.
 *
 * <dt>/<dd>, not the .sf-spec-term / .sf-spec-value <span> pair: that pair
 * has two different readers in this theme (a visual one on <dt>/<dd>, and the
 * K6 parser looking for adjacent spans), and emitting the pair here would put
 * a second, richer source in front of the parser. A definition list is read
 * by neither.
 *
 * Order and sources are fixed by the brief: Unit size / Pack options / Shelf
 * life come out of the record's own sf_formula_specs, Certifications and
 * Packaging out of the dosage page's .sf-facts-mini row (the same single
 * source the hero meta reads). Rows with no value are omitted, so the eleven
 * records without a pack segment render four rows and the ten with one render
 * five; the band never prints a label with nothing after it.
 */
function sinofresh_formula_factsheet() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return '';
	}
	$form_slug = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug = (string) $form_terms[0]->slug;
	}
	$specs = trim((string) get_post_meta($post_id, 'sf_formula_specs', true));
	$parts = sinofresh_formula_specs_parts($specs);
	$certifications = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Certifications') : '';
	$packaging      = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Packaging formats') : '';
	$rows = array(
		'Unit size'      => $parts['unit'],
		'Pack options'   => $parts['pack'],
		'Shelf life'     => $parts['shelf'],
		'Certifications' => $certifications,
		'Packaging'      => $packaging,
	);
	$html = '';
	foreach ($rows as $label => $value) {
		$value = trim((string) $value);
		if ($value === '') {
			continue;
		}
		$html .= sprintf(
			'<dt class="sf-fdetail-media__term">%s</dt><dd class="sf-fdetail-media__value">%s</dd>',
			esc_html($label),
			esc_html($value)
		);
	}
	if ($html === '') {
		return '';
	}
	return '<dl class="sf-fdetail-media__facts">' . $html . '</dl>';
}
add_shortcode('sf_formula_factsheet', 'sinofresh_formula_factsheet');
"""

PHP_MAP_OLD = "\t\t$formula_meta = implode(' · ', $meta_bits);\n\t}\n\t$map = array(\n"
PHP_MAP_NEW = ("\t\t$formula_meta = implode(' · ', $meta_bits);\n"
               "\t\t/* Batch G: the media column's intro. Wrapped in its <p> here,\n"
               "\t\t   which is why the map entry below is escaped HTML and not\n"
               "\t\t   escaped text like {{FORMULA_META}}. Empty stays empty: no\n"
               "\t\t   empty <p> is written. */\n"
               "\t\t$intro = sinofresh_formula_intro($formula_id);\n"
               "\t\tif ($intro !== '') {\n"
               "\t\t\t$formula_intro = '<p class=\"sf-fdetail-media__intro\">' . esc_html($intro) . '</p>';\n"
               "\t\t}\n"
               "\t}\n"
               "\t$map = array(\n")

PHP_MAPROW_OLD = "\t\t'{{FORMULA_META}}'    => esc_html($formula_meta),\n"
PHP_MAPROW_NEW = PHP_MAPROW_OLD + "\t\t'{{FORMULA_INTRO}}'   => $formula_intro,\n"

PHP_DOC_OLD = """ *                        Falls back to the form label alone, or to ''.
"""
PHP_DOC_NEW = """ *                        Falls back to the form label alone, or to ''.
 *   {{FORMULA_INTRO}}    formula detail pages only - the media column's intro
 *                        paragraph, already wrapped in its own <p> (escaped
 *                        HTML, not escaped text), resolved by
 *                        sinofresh_formula_intro(); '' when it cannot be
 *                        composed, which writes nothing at all
"""

PHP_VER_OLD = "array(), '2.10.53');"
PHP_VER_NEW = "array(), '2.10.54');"


# --- part: css ------------------------------------------------------------
CSS_BANNER = '/* G \u2014 formula detail: media + facts, two columns'
CSS_BLOCK = """/* G \u2014 formula detail: media + facts, two columns.

   The gallery stops being a full-width band and becomes the left column of a
   3fr/2fr grid, with the intro, the five-row factsheet and the sample CTA in
   the right column. Layout only: the four slides, the #gallery anchor and
   its h2 are untouched, and the dot rail still counts the same five h2 (four
   dots) it counted before.

   minmax(0, ...) on both tracks is load-bearing, not tidiness: the packaging
   value is a 124-character list, and a bare 3fr track refuses to shrink below
   its content, so the two columns would push the page into horizontal scroll
   at every width where the value does not wrap on its own.

   Every rule stays inside the .sf-fdetail-media namespace. No !important
   anywhere except the one core override below, which needs it for the reason
   written there. ------------------------------------------------------------ */
.sf-fdetail-media__inner {
	display: grid;
	grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
	gap: 48px;
	align-items: start;
}
/* core gives every .is-layout-flow child after the first a 24px block-gap
   margin (":root :where(.is-layout-flow) > *"). In a grid row that lands on
   the aside and drops the right column 24px below the left one. The gap is
   the grid's job here, so the margins go. */
.sf-fdetail-media__inner > * {
	margin-block-start: 0;
}
/* .sf-gallery__stage was written for a full-width band: 680px wide and
   auto-centred. Inside the 3fr column that is a narrow box floating in the
   middle of its own column. Widened to the column and pinned left; its
   aspect-ratio (1/1) keeps the height arithmetic exactly as it was. */
.sf-fdetail-media__left .sf-gallery__stage {
	max-width: none;
	margin-inline: 0;
}
.sf-fdetail-media__side {
	min-width: 0;
}
.sf-fdetail-media__intro {
	margin: 0 0 24px;
	font-size: 15px;
	line-height: 1.6;
	color: var(--wp--preset--color--text-primary);
}
/* Two columns of a grid, not a table: the terms size to their own text so
   the five values start on one x, whatever the longest term is. Voice copied
   from .sf-facts-mini \u2014 11px letterspaced muted label, ink value. */
.sf-fdetail-media__facts {
	display: grid;
	grid-template-columns: auto minmax(0, 1fr);
	gap: 10px 16px;
	margin: 0 0 28px;
}
.sf-fdetail-media__term {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--wp--preset--color--text-secondary);
	white-space: nowrap;
}
.sf-fdetail-media__value {
	margin: 0;
	font-size: 14px;
	line-height: 1.5;
	color: var(--wp--preset--color--text-primary);
}
/* Same orange as the page's closing "Request a Quote": two call-to-action
   buttons on one page that looked different would read as two different
   kinds of action. */
.sf-fdetail-media__cta {
	display: inline-block;
	padding: 12px 24px;
	border-radius: 6px;
	background: var(--wp--preset--color--cta);
	color: var(--wp--preset--color--card-white);
	font-size: 15px;
	font-weight: 600;
	text-decoration: none;
	transition: background-color 0.2s ease;
}
.sf-fdetail-media__cta:hover,
.sf-fdetail-media__cta:focus-visible {
	background: var(--wp--preset--color--cta-hover);
	color: var(--wp--preset--color--card-white);
}
/* <=768px (the site's main breakpoint): one column, gallery first, facts
   under it. 32px because the desktop 48px is a column gap, not a section
   gap, and the band's own padding still supplies the outer rhythm. */
@media (max-width: 768px) {
	.sf-fdetail-media__inner {
		grid-template-columns: minmax(0, 1fr);
		gap: 32px;
	}
}
"""


def read(path):
    return open(path, encoding='utf-8').read()


def splice(raw, old, new, label, problems, count=1):
    """One literal replacement, asserted to be unambiguous."""
    n = raw.count(old)
    if n != count:
        problems.append('%s: anchor occurs %d time(s), expected %d' % (label, n, count))
        return None
    return raw.replace(old, new, count)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--apply', action='store_true')
    ap.add_argument('--backup-dir', default=None)
    ap.add_argument('--part', default='all',
                    choices=['all', 'facts', 'media', 'php', 'css'])
    args = ap.parse_args()

    todo = {'facts', 'media', 'php', 'css'} if args.part == 'all' else {args.part}
    problems = []
    plan = []          # (path, rebuilt, undo_check)

    def backup(path, raw):
        if args.backup_dir:
            os.makedirs(args.backup_dir, exist_ok=True)
            rel = os.path.relpath(path, os.path.join(HERE, '..')).replace('/', '__')
            with open(os.path.join(args.backup_dir, rel), 'w', encoding='utf-8') as fh:
                fh.write(raw)

    # ---- facts ----------------------------------------------------------
    if 'facts' in todo:
        for form in DOSAGES:
            path = os.path.join(TPL, 'page-%s.html' % form)
            raw = read(path)
            if 'data-label="Packaging formats"' in raw:
                problems.append('facts/%s: Packaging formats already present' % form)
                continue
            value = packaging_value(form)
            if value is None:
                problems.append('facts/%s: no data-group="packaging" group' % form)
                continue
            if FACTS_SEAM not in raw:
                problems.append('facts/%s: the facts seam is not where it was' % form)
                continue
            row = ROW_FMT % value
            if re.search(r'[<>&"]', value):
                problems.append('facts/%s: value carries markup-significant bytes: %r'
                                % (form, value))
                continue
            rebuilt = raw.replace(FACTS_SEAM, row + FACTS_SEAM, 1)
            if rebuilt.replace(row, '', 1) != raw:
                problems.append('facts/%s: not a clean splice' % form)
                continue
            plan.append((path, rebuilt, '%s (+%d B) value=%r'
                         % ('facts/page-%s.html' % form,
                            len(rebuilt.encode()) - len(raw.encode()), value)))

    # ---- media ----------------------------------------------------------
    if 'media' in todo:
        path = os.path.join(TPL, 'single-sf_formula.html')
        raw = read(path)
        if 'sf-fdetail-media' in raw:
            problems.append('media: sf-fdetail-media already present')
        else:
            rebuilt = splice(raw, MEDIA_OLD, MEDIA_NEW, 'media', problems)
            if rebuilt is not None:
                if rebuilt.replace(MEDIA_NEW, MEDIA_OLD, 1) != raw:
                    problems.append('media: not a clean splice')
                else:
                    # nothing the batch must keep may live only in the text it
                    # replaces: the anchor, the heading and the shortcode are
                    # all still in the rebuilt file, and the shortcode exactly
                    # once (a second copy would double the slides).
                    for needle in ('<section id="gallery"', 'sf-gallery sf-fdetail-media__left',
                                   '{{FORMULA_INTRO}}', '[sf_formula_factsheet]',
                                   'sf-fdetail-media__cta'):
                        if needle not in rebuilt:
                            problems.append('media: rebuilt file lacks %r' % needle)
                    if rebuilt.count('[sf_formula_gallery]') != 1:
                        problems.append('media: the gallery shortcode is not '
                                        'defined exactly once')
                    plan.append((path, rebuilt, 'media (+%d B)'
                                 % (len(rebuilt.encode()) - len(raw.encode()))))

    # ---- php ------------------------------------------------------------
    if 'php' in todo:
        path = os.path.join(THEME, 'functions.php')
        raw = read(path)
        cur = raw
        if "'2.10.54'" in cur:
            problems.append('php: version already bumped')
        for old, new, label in (
                (PHP_INIT_OLD, PHP_INIT_NEW, 'php/init'),
                (PHP_FUNCS_OLD, PHP_FUNCS_NEW, 'php/functions'),
                (PHP_SHORTCODE_ANCHOR, PHP_SHORTCODE_NEW, 'php/factsheet'),
                (PHP_MAP_OLD, PHP_MAP_NEW, 'php/map-compose'),
                (PHP_MAPROW_OLD, PHP_MAPROW_NEW, 'php/map-row'),
                (PHP_DOC_OLD, PHP_DOC_NEW, 'php/docblock'),
                (PHP_VER_OLD, PHP_VER_NEW, 'php/version')):
            cur = splice(cur, old, new, label, problems)
            if cur is None:
                break
        if cur is not None:
            undone = cur
            for old, new, _ in (
                    (PHP_VER_OLD, PHP_VER_NEW, ''),
                    (PHP_DOC_OLD, PHP_DOC_NEW, ''),
                    (PHP_MAPROW_OLD, PHP_MAPROW_NEW, ''),
                    (PHP_MAP_OLD, PHP_MAP_NEW, ''),
                    (PHP_SHORTCODE_ANCHOR, PHP_SHORTCODE_NEW, ''),
                    (PHP_FUNCS_OLD, PHP_FUNCS_NEW, ''),
                    (PHP_INIT_OLD, PHP_INIT_NEW, '')):
                if new in undone:
                    undone = undone.replace(new, old, 1)
            if undone != raw:
                # the multi-part undo above is order-sensitive; the gate does
                # this comparison properly, so only a whole-file equality is
                # claimed here.
                k = next((i for i in range(min(len(undone), len(raw)))
                          if undone[i] != raw[i]), min(len(undone), len(raw)))
                problems.append('php: the assembled file does not undo to the '
                                'source (first mismatch @%d)' % k)
            else:
                plan.append((path, cur, 'php (+%d B)'
                             % (len(cur.encode()) - len(raw.encode()))))

    # ---- css ------------------------------------------------------------
    if 'css' in todo:
        path = os.path.join(THEME, 'style.css')
        raw = read(path)
        if CSS_BANNER in raw:
            problems.append('css: the G banner is already present')
        else:
            entry = '\n' + CSS_BLOCK
            rebuilt = raw + entry
            rebuilt = rebuilt.replace('Version: 2.10.53', 'Version: 2.10.54', 1)
            if rebuilt.replace(entry, '', 1).replace('Version: 2.10.54',
                                                     'Version: 2.10.53', 1) != raw:
                problems.append('css: not a clean splice')
            else:
                plan.append((path, rebuilt, 'css (+%d B)'
                             % (len(rebuilt.encode()) - len(raw.encode()))))

    if problems:
        print('FAIL \u2014 %d problem(s):' % len(problems), file=sys.stderr)
        for p in problems:
            print('  * %s' % p, file=sys.stderr)
        return 1

    for path, rebuilt, note in plan:
        print('%-34s %s' % (note, 'WOULD WRITE' if args.check else 'writing'))
        if args.check:
            continue
        backup(path, read(path))
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(rebuilt)
        back = read(path)
        if back != rebuilt:
            print('  !! read-back differs', file=sys.stderr)
            return 1
    print('\n%d file(s) %s' % (len(plan), 'checked' if args.check else 'written'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
