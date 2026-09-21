#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch C — the two source edits, each self-proving.

  php   functions.php gains, in this order:
          sinofresh_formula_faq_data()   the nine pairs, the sf_formula_faq
                                         whole-set override, and the values
                                         read through sinofresh_formula_spec_cell
                                         (the same source {{FORMULA_META}} reads)
          sinofresh_formula_faq()        the <details> sequence, in the dosage
                                         pages' own markup vocabulary
          [sf_formula_faq]               the shortcode, no attributes
          FAQPage generator              an is_singular('sf_formula') branch that
                                         reads that same function instead of
                                         scanning the template file
  tpl   single-sf_formula.html: a core group + core heading + core/html block
        after "Ingredients & composition" and before the related-formulas grid.

There is NO css part and NO version bump: the accordion reuses style.css 13
(.sf-faq) and 31a (the 1200px measure), and the band reuses .sf-fdetail's
<=768px inset.  Batch C ships the same enqueued style.css bytes as batch G.

Every part asserts its anchors before writing, then reads the file back and
undoes its own splice — a part that cannot reproduce its input byte-for-byte
is not a clean splice and the gate must not trust the same span.

The PHP and the template never name a shortcode inside an HTML comment: a
block template runs do_shortcode() before do_blocks(), and do_shortcode() does
not know about HTML comments, so a bracket token in one would be expanded
inside the comment and ship the whole block twice.

usage:
    python3 tools/b2d_c_apply.py --check
    python3 tools/b2d_c_apply.py --apply --backup-dir DIR [--part php|tpl]
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, '..', 'sinofresh-theme')
TPL = os.path.join(THEME, 'templates')


# --- part: php ------------------------------------------------------------
# The anchor is the seam BETWEEN two top-level functions: intro()'s tail, then
# the docblock that opens the next one. The batch belongs BETWEEN the two
# halves. Splicing it in front of the whole anchor instead puts the block
# *inside* sinofresh_formula_intro() — the declarations then only execute when
# that function runs, and the second call in a request fatals with
# "Cannot redeclare sinofresh_formula_faq_data()". That is invisible to the
# splice's own undo proof (the splice is still clean) and to the synthesiser
# (which models bytes, not PHP scope); only a real render shows it, which is
# how it was caught. `return $text;` occurs exactly once in the file.
PHP_FUNCS_OPEN = """	return $text;
}

"""

PHP_FUNCS_CLOSE = """/**
 * wp_json_encode() for the body of an inline <script>."""

PHP_FUNCS_ANCHOR = PHP_FUNCS_OPEN + PHP_FUNCS_CLOSE

PHP_FAQ_BLOCK = '''/**
 * The nine question/answer pairs of a formula's FAQ band (batch C).
 *
 * The dosage pages answer "what about this dosage form"; this band answers
 * "what about THIS formula", so it is a different set of nine. Where the two
 * overlap they share the wording, not merely the meaning: the sampling fee and
 * turnaround, the certification list and the confidentiality promise are the
 * sentences /faq/ already publishes, so the site cannot end up contradicting
 * itself about its own commercial terms.
 *
 * Three answers carry a value, and each value is read from the single source
 * the rest of the page already reads:
 *
 *   Certifications      the dosage page's .sf-facts-mini row, through
 *                       sinofresh_formula_spec_cell() — the {{FORMULA_META}}
 *                       source, not a second copy
 *   Packaging formats   the same row (batch G's fourth item)
 *   the record's title  get_the_title()
 *
 * A value that cannot be resolved drops its clause instead of printing an
 * empty label, the rule {{FORMULA_META}} and sinofresh_formula_intro() follow.
 * That is why the packaging answer is written as an optional LEADING sentence:
 * it has to read as finished with and without the value.
 *
 * sf_formula_faq (post meta) overrides the whole set when it parses to two or
 * more usable pairs. The format is plain text because the slot is edited by
 * hand in wp-admin, one question line with its answer under it, repeated:
 *
 *   Q: question
 *   A: answer, continued on following lines until the next Q:
 *
 * A malformed override falls back to the generated set rather than shipping a
 * half-empty accordion, and says so in the PHP error log. Like
 * sf_formula_intro this key is deliberately left unregistered: the record type
 * supports custom-fields, which is the same editing route the intro uses.
 *
 * Returns RAW (decoded) text, never HTML. sinofresh_formula_faq() escapes it
 * for the page and the FAQPage generator takes it verbatim, which is what
 * keeps the structured data free of HTML entities — and both readers share
 * this one function, so the accordion and the schema cannot drift apart.
 */
function sinofresh_formula_faq_data($post_id = 0) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		$post_id = (int) get_queried_object_id();
	}
	if ($post_id <= 0 || get_post_type($post_id) !== 'sf_formula') {
		return array();
	}

	/* Whole-set override. Answers may run over several lines; a line that is
	   neither Q: nor A: continues the answer it is under, and a Q: with no
	   answer at all is dropped rather than shipped as an empty <details>. */
	$raw = (string) get_post_meta($post_id, 'sf_formula_faq', true);
	if (trim($raw) !== '') {
		$pairs    = array();
		$question = '';
		$answer   = array();
		foreach (preg_split('/\\R/u', $raw) as $line) {
			$line = trim((string) $line);
			if ($line === '') {
				continue;
			}
			if (preg_match('/^Q\\s*:\\s*(.+)$/iu', $line, $m)) {
				if ($question !== '' && $answer) {
					$pairs[] = array('q' => $question, 'a' => implode(' ', $answer));
				}
				$question = trim($m[1]);
				$answer   = array();
				continue;
			}
			if (preg_match('/^A\\s*:\\s*(.+)$/iu', $line, $m)) {
				$answer[] = trim($m[1]);
				continue;
			}
			if ($question !== '' && $answer) {
				$answer[] = $line;
			}
		}
		if ($question !== '' && $answer) {
			$pairs[] = array('q' => $question, 'a' => implode(' ', $answer));
		}
		if (count($pairs) >= 2) {
			return $pairs;
		}
		error_log(sprintf(
			'[sinofresh] sf_formula_faq: post %d override parsed to %d pair(s), '
			. 'below the two a FAQPage needs; using the generated set.',
			$post_id, count($pairs)
		));
	}

	$name = trim(wp_strip_all_tags((string) get_the_title($post_id)));
	$form_slug  = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug = (string) $form_terms[0]->slug;
	}
	$certs = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Certifications') : '';
	$pack  = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Packaging formats') : '';

	$pairs = array();

	$pairs[] = array(
		'q' => 'Can the active ingredients be changed?',
		'a' => 'Yes. This is a starting point rather than a fixed recipe: we can adjust the '
		     . 'levels, swap one active for another, or add new ones, and the specification '
		     . 'and the label are rewritten to match.',
	);

	$pairs[] = array(
		'q' => 'Can the flavour be changed?',
		'a' => 'Yes. The flavour profile is chosen with you for your target market, including '
		     . 'a profile you already sell.',
	);

	$pairs[] = array(
		'q' => 'Is a gluten-free or grain-free version available?',
		'a' => 'Yes. Wheat, gluten and grain carriers can be left out of the recipe, and the '
		     . 'change is recorded in the specification and in the Certificate of Analysis.',
	);

	$pairs[] = array(
		'q' => 'Is this formula for dogs or for cats?',
		'a' => 'Our formulas can be customised for dogs, cats, or both. Tell us your target '
		     . 'species when you enquire and we will adjust the formula, the dosage, and the '
		     . 'label accordingly.',
	);

	$pairs[] = array(
		'q' => 'Can I sample this formula before ordering?',
		'a' => 'Yes. The sample is made to the same specification as the bulk order: sampling '
		     . 'takes 3\u20137 working days for a standard formula, and the $200 sampling fee '
		     . 'is deducted from your bulk order.',
	);

	$answer = '';
	if ($certs !== '') {
		$answer .= 'Certifications: ' . $certs . '. ';
	}
	$answer .= 'Every batch is tested in our QC laboratory and ships with a Certificate of '
	         . 'Analysis, and we support FDA, EU and other target-market documentation.';
	$pairs[] = array(
		'q' => 'What certifications and documentation do you provide?',
		'a' => $answer,
	);

	$answer = '';
	if ($pack !== '') {
		$answer .= 'Standard formats for this dosage form: ' . $pack . '. ';
	}
	$answer .= 'The label, the carton and the barcode are all produced with your own brand '
	         . 'on them.';
	$pairs[] = array(
		'q' => 'Can the packaging and the label be customised?',
		'a' => $answer,
	);

	$pairs[] = array(
		'q' => 'How should the finished product be stored?',
		'a' => 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the '
		     . 'container tightly closed and use within the recommended period.',
	);

	$pairs[] = array(
		'q' => 'Will you keep my formula and my brand confidential?',
		'a' => 'Yes \u2014 every formula is produced exclusively under your own brand. We never '
		     . 'sell your formula, your artwork, or your customer list to any third party, '
		     . 'and we sign an NDA before sharing any custom formulation details.',
	);

	return $pairs;
}

/**
 * [sf_formula_faq] \u2014 the accordion itself, inside the template's core/html
 * block (batch C).
 *
 * The <details> sequence is built here rather than written as core/details
 * blocks in the template for the same reason every other dynamic band on this
 * page is: a block template runs do_shortcode() before do_blocks(), so a
 * {{placeholder}} in a block cannot be resolved, while a shortcode reads the
 * record at render time. It also means the nine answers exist once, in
 * sinofresh_formula_faq_data(), and both the page and the FAQPage schema read
 * that one copy instead of two implementations that can disagree.
 *
 * The markup is the dosage pages' own vocabulary \u2014 .sf-faq, .sf-faq__item,
 * .sf-faq__icon, wp-block-heading on the question, has-text-secondary-color on
 * the answer \u2014 so style.css needs no new rule and the two accordions cannot
 * look different. The first item ships open, as it does there, and the whole
 * sequence is one line: the band is a shortcode, so the renderer's newline
 * arithmetic has nothing to do here.
 *
 * Returns '' outside a formula, and '' if every pair is unusable, so nothing
 * empty is emitted. On a real record the generated set is never empty, so the
 * template's core heading always has an accordion under it.
 */
function sinofresh_formula_faq($post_id = 0) {
	$pairs = sinofresh_formula_faq_data($post_id);
	if (!$pairs) {
		return '';
	}
	$html  = '';
	$first = true;
	foreach ($pairs as $pair) {
		$question = trim((string) $pair['q']);
		$answer   = trim((string) $pair['a']);
		if ($question === '' || $answer === '') {
			continue;
		}
		$html .= sprintf(
			'<details class="wp-block-details sf-faq__item"%s>'
			. '<summary><h3 class="wp-block-heading">%s</h3>'
			. '<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
			. '<p class="has-text-secondary-color has-text-color">%s</p></details>',
			$first ? ' open' : '',
			esc_html($question),
			esc_html($answer)
		);
		$first = false;
	}
	if ($html === '') {
		return '';
	}
	return '<div class="sf-faq">' . $html . '</div>';
}
/* WP hands a shortcode callback its attribute array as the first argument, so
   the id is never read from it: the band only ever renders on the record being
   viewed. */
add_shortcode('sf_formula_faq', function() {
	return sinofresh_formula_faq();
});

'''

# The FAQPage generator: the branch goes in after the SEO-plugin stand-down and
# before the template-file resolution it replaces for this view.
PHP_FAQPAGE_ANCHOR = """	if (class_exists('RankMath') || defined('WPSEO_VERSION') || defined('RANK_MATH_VERSION')) {
		return;
	}

	// Resolve the template file for the current view (front page / page slug)."""

PHP_FAQPAGE_BLOCK = """	if (class_exists('RankMath') || defined('WPSEO_VERSION') || defined('RANK_MATH_VERSION')) {
		return;
	}

	/* Batch C: the formula detail page's accordion is generated by the
	   [sf_formula_faq] shortcode inside a core/html block, so the template
	   file holds no <details> pair to find \u2014 and its {{TITLE}} and
	   {{FORM_CRUMB}} tokens would be read as literal text. The pairs therefore
	   come from the same function the visible block renders from, which is the
	   only arrangement in which the page and the schema cannot disagree. */
	if (is_singular('sf_formula')) {
		$entities = array();
		foreach (sinofresh_formula_faq_data((int) get_queried_object_id()) as $pair) {
			$question = trim((string) $pair['q']);
			$answer   = trim((string) $pair['a']);
			if ($question === '' || $answer === '') {
				continue;
			}
			$entities[] = array(
				'@type'          => 'Question',
				'name'           => $question,
				'acceptedAnswer' => array(
					'@type' => 'Answer',
					'text'  => $answer,
				),
			);
		}
		if (count($entities) >= 2) {
			$schema = array(
				'@context'   => 'https://schema.org',
				'@type'      => 'FAQPage',
				'mainEntity' => $entities,
			);
			echo "\\n" . '<script type="application/ld+json">'
				. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
				. "</script>\\n";
		}
		return;
	}

	// Resolve the template file for the current view (front page / page slug)."""


# --- part: tpl ------------------------------------------------------------
# The seam is the closed composition block, the blank line, and the marker that
# opens the related-formulas grid. The insertion goes between the block's close
# and that blank line, so the base's five newlines stay five.
TPL_OLD = ('[sf_formula_detail_composition]\n<!-- /wp:html -->\n\n'
           '<!-- Block 4: related formulas -->')

TPL_COMMENT = """<!-- Batch C: the formula FAQ. The accordion is emitted by the FAQ shortcode
     in the core/html block below, so the nine answers can carry this record's
     own values and the FAQPage schema can read the same function instead of
     scanning this file for a details pair. sf-fdetail is on the section only
     for its <=768px inset; the .sf-faq class comes from the div the shortcode
     returns, which is what style.css 13 and 31a both key on. -->
"""

# what gets inserted; TPL_REGION is the exact span the gate has to be able to
# take back out (it ends on the group's own close, so the base's blank line
# before "Block 4" is preserved by the caller)
TPL_REGION = TPL_COMMENT + '''<!-- wp:group {"tagName":"section","className":"sf-fdetail sf-fdetail-faq","backgroundColor":"card-white","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section class="wp-block-group sf-fdetail sf-fdetail-faq has-card-white-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:heading -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:html -->
[sf_formula_faq]
<!-- /wp:html -->
</section>
<!-- /wp:group -->
'''

TPL_NEW = TPL_OLD.replace('<!-- /wp:html -->\n\n',
                          '<!-- /wp:html -->\n' + TPL_REGION + '\n', 1)
if TPL_NEW == TPL_OLD:
    raise SystemExit('tpl: the insertion point is not in the anchor')


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
    ap.add_argument('--part', default='all', choices=['all', 'php', 'tpl'])
    ap.add_argument('--theme-dir', default=None,
                    help='apply into a COPY of the theme (step 0 builds the '
                         'candidate sources the gate is exercised against '
                         'before the working tree is touched)')
    args = ap.parse_args()

    global THEME, TPL
    if args.theme_dir:
        THEME = os.path.abspath(args.theme_dir)
        TPL = os.path.join(THEME, 'templates')
        if not os.path.isdir(TPL):
            raise SystemExit('--theme-dir has no templates/ directory: %s' % THEME)

    todo = {'php', 'tpl'} if args.part == 'all' else {args.part}
    problems = []
    plan = []

    def backup(path, raw):
        if args.backup_dir:
            os.makedirs(args.backup_dir, exist_ok=True)
            rel = os.path.relpath(path, os.path.join(HERE, '..')).replace('/', '__')
            with open(os.path.join(args.backup_dir, rel), 'w', encoding='utf-8') as fh:
                fh.write(raw)

    # ---- php ------------------------------------------------------------
    if 'php' in todo:
        path = os.path.join(THEME, 'functions.php')
        raw = read(path)
        if 'sinofresh_formula_faq_data' in raw:
            problems.append('php: sinofresh_formula_faq_data already present')
        cur = raw
        for old, new, label in (
                (PHP_FUNCS_ANCHOR, PHP_FUNCS_OPEN + PHP_FAQ_BLOCK + PHP_FUNCS_CLOSE,
                 'php/faq-functions'),
                (PHP_FAQPAGE_ANCHOR, PHP_FAQPAGE_BLOCK, 'php/faqpage-branch')):
            cur = splice(cur, old, new, label, problems)
            if cur is None:
                break
        # Structural guard. The block has to be at include time, i.e. between
        # two top-level functions, not nested in one. Both halves of that are
        # checked here: what precedes the block is a column-0 closing brace,
        # and nothing inside the block is indented like a nested declaration.
        if cur is not None:
            i = cur.find(PHP_FAQ_BLOCK)
            if i < 0 or not cur[:i].endswith("\n}\n\n"):
                problems.append('php: the FAQ block does not start right after a '
                                'top-level closing brace — it would be declared '
                                'only when that function runs')
            for line in PHP_FAQ_BLOCK.split('\n'):
                if re.match(r'^[ \t]+function\b', line):
                    problems.append('php: the FAQ block declares a function at an '
                                    'indent level; it would not be declared at '
                                    'include time')
                    break
        if cur is not None:
            undone = cur
            for old, new, label in (
                    (PHP_FAQPAGE_ANCHOR, PHP_FAQPAGE_BLOCK, 'php/faqpage-branch'),
                    (PHP_FUNCS_ANCHOR,
                     PHP_FUNCS_OPEN + PHP_FAQ_BLOCK + PHP_FUNCS_CLOSE,
                     'php/faq-functions')):
                if new not in undone:
                    problems.append('php: the assembled file lacks the %s insert'
                                    % label)
                    break
                undone = undone.replace(new, old, 1)
            if undone != raw:
                k = next((q for q in range(min(len(undone), len(raw)))
                          if undone[q] != raw[q]), min(len(undone), len(raw)))
                problems.append('php: the assembled file does not undo to the '
                                'source (first mismatch @%d)' % k)
            else:
                plan.append((path, cur, 'php (+%d B)' % (len(cur.encode())
                                                         - len(raw.encode()))))

    # ---- tpl ------------------------------------------------------------
    if 'tpl' in todo:
        path = os.path.join(TPL, 'single-sf_formula.html')
        raw = read(path)
        if 'sf-fdetail-faq' in raw:
            problems.append('tpl: sf-fdetail-faq already present')
        elif '[sf_formula_faq]' in raw:
            problems.append('tpl: the FAQ shortcode already present')
        else:
            rebuilt = splice(raw, TPL_OLD, TPL_NEW, 'tpl', problems)
            if rebuilt is not None:
                if rebuilt.replace(TPL_REGION, '', 1) != raw:
                    problems.append('tpl: not a clean splice')
                else:
                    for needle in ('<!-- Batch C:', '<h2 class="wp-block-heading">'
                                   'Frequently Asked Questions</h2>',
                                   '[sf_formula_faq]',
                                   'sf-fdetail sf-fdetail-faq'):
                        if needle not in rebuilt:
                            problems.append('tpl: rebuilt file lacks %r' % needle)
                    if rebuilt.count('[sf_formula_faq]') != 1:
                        problems.append('tpl: the FAQ shortcode is not defined '
                                        'exactly once')
                    # a bracket token inside an HTML comment would be expanded
                    # by do_shortcode() inside the comment: refuse to ship that
                    for line in rebuilt.split('\n'):
                        if line.strip().startswith('<!--') and '[' in line:
                            problems.append('tpl: a comment line carries a '
                                            'bracket token: %r' % line)
                    plan.append((path, rebuilt, 'tpl (+%d B)'
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
