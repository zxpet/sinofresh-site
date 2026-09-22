# Batch H7f — the inquiry basket leaves: icon, drawer, script, CSS, endpoint mode

**Status: ✅ complete.** `2.10.66 → 2.10.67`. Step 6 (`git pull` on the dev box)
**skipped**, as in every batch H7a..H7e: the batch is judged on a preflight copy
and the dev live site keeps serving the pre-H2b1 theme.

| commit | what |
|---|---|
| `0b015e1` | Batch H7f step 1: the inquiry basket leaves — icon, drawer, script, CSS, mode |
| (this document) | Batch H7f closure: the confinement proof, the browser pass and the frames |

Diff: **6 files, +41 / −1,161**, all theme-side.

| file | changed | size | change |
|---|---|---|---|
| `assets/js/basket.js` | +0 / −535 | 535 → 0 lines | **deleted** |
| `style.css` | +30 / −404 | 307,144 → 299,003 B | −8,141 B |
| `inc/config-pdf.php` | +7 / −195 | 543 → 355 lines | −8,088 B |
| `parts/footer.html` | +0 / −19 | 116 → 97 lines | the drawer + overlay |
| `functions.php` | +4 / −5 | 269,873 → 269,740 B | enqueue out, token up, docblock corrected |
| `parts/header.html` | +0 / −3 | 43 → 40 lines | the `wp:html` block holding the bag button |

The batch record, the tools and the frames are committed after the code, so the
gate and the confinement proof are run over **`84ffd39..0b015e1`**, which
contains theme code only. The confinement declaration names the later paths too,
so the same proof also passes over the closure range — but the numbers in §3 and
§4 are the code-only range's.

---

## 1. The carrier scan: an unsatisfiable affordance, not dead code

The brief was "delete the basket icon and its dead code". The scan's job was to
find out whether the icon was dead, because the two cases call for different
things: dead code is a deletion, and a control that no longer works is a **product
defect** that the deletion only hides.

Four findings, in the order they matter:

* **`SFBasket.add()` has zero callers outside `basket.js`.** Its only historical
  caller was `configurator.js`, which stopped adding several batches ago.
* **`sf:basket-change` has no listener outside the file that dispatches it** — the
  event the UI re-rendered from had nobody on the other end.
* **`config.js` does not post to `/config-pdf`.** It fills the form; `inquiry.js`
  posts to `/inquiry`. The endpoint's basket mode had no live caller at all.
* **`initUI()` returns early unless BOTH the header button and the footer drawer
  exist.** With the button gone the drawer could never open; with the drawer gone
  the button would open nothing. The drawer's own empty state said
  *"Configure a dosage form and click 'Add to Inquiry'"* — a control that does
  not exist anywhere on the site.

So the honest description is not "a dead icon was removed". It is: **the basket
was an affordance that could not be satisfied, and this batch removes the
affordance rather than the promise.** That distinction is why the header CTA
container and the four *shared* CSS rules were treated as load-bearing rather
than as part of the basket.

One thing deliberately kept: `.sf-toast`, which `formulas.js` and `toc-nav.js`
both use. It sat inside the basket's neighbourhood in the stylesheet and is not
the basket's.

---

## 2. The carve: `tools/b2d_h7f_carve.py` (new)

`style.css` could not be cut by section, because the basket did not own whole
sections. Four rule *headers* were shared with the certificate dialog and the
inquiry dialog — the backdrop, the open state, the hidden state and the scroll
lock — so the honest description of the edit is "delete these 15 ranges, keep
these selector lines", and 15 disjoint ranges is a different job from H6's
"delete these 48 blocks".

The tool asserts each range's two boundary lines before cutting, rewrites seven
prose passages that named the basket (including two z-index rationales), folds
the version token, and ends with a sweep asserting that no surviving line in the
file looks like a selector and says `basket`.

Two mistakes were made and fixed while writing it, both worth recording because
both were silent:

* **A replacement keyed to every line in its range printed the new section 45
  banner seven times.** The assembly loop applied the replacement text to each
  line of the range and never skipped the range's remaining lines. Fixed by
  keying the replacement to the range's first line only, marking the rest
  `skip`, and adding an assertion that *a replacement's text must land exactly
  once*. `style.css` was restored with `git checkout --` and its sha256
  re-verified before the tool was re-run.
* **The `basket` sweep caught six surviving prose lines** in the certificate and
  inquiry dialog sections — stale z-index rationales explaining that those rules
  cleared the basket drawer's `10001`. Four were rewritten (both dialog rules now
  say "the backdrop rules at section 45 hand out 10000… its own step above that
  stack"), and the rest fell inside cut ranges. A prose guard that merely
  demanded "no line contains basket" would have forced those comments to be
  deleted rather than corrected, which loses information for no gain.

---

## 3. The gate — `tools/b2d_h7_gate.py --batch h7f`

Declaration: `mode: 'insert'`, `applies: 225` (3 runs × 75 pages), 75 pages,
`nc13_mode: 'sighted'`, four sources (`hdr`, `ftr`, `php`, `pdf`) plus the CSS.

| pass | result |
|---|---|
| A/A (two captures of one install) | **75 / 0** |
| main proof `mask(transform(baseline)) == mask(candidate)` | **75 / 0**, applied 225 (declared 225), direction `insert` |
| coverage | **22 / 22** |
| invariants | **14 / 14** |
| masked-blob read-back | 23 page(s), **0 differ**; 46 masked currency values that are not text |
| source | **37 / 37** |
| sabotage matrix | **9 / 9 caught** |
| named negative controls | **17 / 17** |

### 3.1 Coverage, in the batch's own terms

```
sf-basket                          candidate count = 0    (want 0)
sinofresh-basket-js                candidate count = 0    (want 0)
assets/js/basket.js                candidate count = 0    (want 0)
?ver=2.10.66                       candidate count = 0    (want 0)
?ver=2.10.67                       candidate count = 75   (want 75)
the header bag button    base 75  -> candidate 0     (want 75 -> 0)
the drawer overlay       base 75  -> candidate 0     (want 75 -> 0)
the drawer               base 75  -> candidate 0     (want 75 -> 0)
the script tag           base 75  -> candidate 0     (want 75 -> 0)
every basket byte        base 1125 -> candidate 0    (want 1125 -> 0)
the header seam          base 0   -> candidate 75    (want 0 -> 75)
the footer seam          base 0   -> candidate 75    (want 0 -> 75)
the header CTA container base 75  -> candidate 75    (want 75 -> 75)
the cookie banner        base 75  -> candidate 75    (want 75 -> 75)
the float stack          base 75  -> candidate 75    (want 75 -> 75)
the Get a Quote button   base 208 -> candidate 208   (want 208 -> 208)
the certificate dialog   base 9   -> candidate 9     (want 9 -> 9)
the inquiry dialog       base 1350 -> candidate 1350 (want 1350 -> 1350)
the navigation           base 23061 -> candidate 23061 (want same)
one heading leaves per page, and it is the drawer's  base 1430 -> 1355
```

The seam rows are the ones that matter most: `\n\n\n` closing to `\n\n` where the
bag button was, and the footer's `</footer>` closing straight onto
`<div class="sf-cookie-banner"` — the drawer and the cookie banner shared one
`wp:html` block, so an over-reaching deletion would have taken the banner with it.

### 3.2 The sabotage matrix (9 mutants, all caught)

| mutant | differing pages | applied |
|---|---|---|
| the header button is never removed | 75 | 150 / 225 |
| the drawer is never removed | 75 | 150 / 225 |
| the script tag is never removed | 75 | 150 / 225 |
| the style token is not folded | 75 | 225 / 225 |
| the run count is declared one short | 0 | 225 / 224 |
| nothing is removed at all | 75 | 0 / 0 |
| one page keeps its drawer | 1 | 225 / 225 |
| the batch over-reaches and takes the cookie banner with the drawer | 1 | 225 / 225 |
| a stray character on one page | 1 | 225 / 225 |

The second-to-last is the one written for this batch: it is the exact failure the
shared `wp:html` block makes possible.

### 3.3 Negative controls (17)

`NC1`–`NC8` are the shared ones (mask set carries no catch-all; the catch-all
masks a same-offset edit but the real set sees it; a basket run put back fails
coverage; one page losing the token fails coverage; one injected `h2` fails the
invariants; A/A against another state fails; the blob read-back fails on a
doctored blob; the JSON-LD comparison fails on a renamed key).

`NC13`–`NC16` cover the proof's direction: with `insert`, the candidate is
compared whole, so a basket run put back is caught twice (`main_red=True
coverage_red=True`); strict A/A refuses another state's capture; A/A fails when
the two captures cover different pages; and the insert direction refuses an
unapplied candidate while accepting a real one.

`NC17`–`NC21` are this batch's, and all five of them are about the **source**
claims rather than the pages, because the endpoint is not on any captured page:
the source pass fails when the bag button comes back to the header (`NC17`), when
the endpoint reads a `basket` key again (`NC18`), when a basket selector comes
back to `style.css` (`NC19`), when a basket button appears in the wrong page
(`NC20`), and when one page loses its header CTA (`NC21`).

### 3.4 Source pass (37 assertions)

All 37 hold, including `the endpoint still registers its route`,
`no basket selector survives`, `the shared Dompdf wrapper survives`,
`the toast is untouched (formulas.js and toc-nav.js share it)`, and
`the certificate modal section is untouched`.

Two assertions had to be retargeted, and the reason is worth keeping: they were
written against `hdr_live`, the variant of the header with comment bodies
blanked. `<!-- wp:button -->` is a comment, so on `hdr_live` it is gone, and
*"which is now the buttons block's only child"* failed against a file that was
correct. Both now read the raw `hdr` blob. A comment-stripping view is the right
place to look for *code* and the wrong place to look for *block markup*.

---

## 4. Confinement — `tools/b2d_h7f_confine.py` (new, 38 checks + NC1–NC8)

The byte gate compares pages. Two kinds of file in this batch never appear in a
page's bytes, and one of them is the reason this proof exists:

* **`style.css` and `basket.js` reach a page as a URL.** A deletion — or, worse, a
  carve whose boundary reaches one line too far — leaves all 75 captured pages
  byte-identical and still changes what a reader sees.
* **`inc/config-pdf.php` registers a REST route no captured page calls.** The
  batch deletes two functions from it. A surviving caller would leave every byte
  on disk where it was and 500 at runtime only.

So the claim is about the **diff**, not the file:

* `style.css`'s **404 removed lines are exactly the 15 declared baseline
  intervals**, and each interval is pinned by its own first and last non-blank
  removed line. Naming the intervals is the point: "every removed line mentions
  basket" is a catch-all that a stray edit elsewhere in a 9,690-line stylesheet
  can satisfy, and an edit elsewhere is the failure this exists to catch.
* **and inside those intervals 45 `{` and 45 `}` leave together.** A carve that
  opened a block it did not close — or closed one it had half-taken — leaves the
  file *balanced* and wrong, and no page can see it. This is the check that would
  have caught the section-45 bug in §2 had it survived to the diff.
* what the batch did **not** mean to remove is named and counted: the header CTA
  alignment rule, the certificate and inquiry dialog families whose selector
  lists it shared, the rewritten section 45 banner, and `.sf-toast`.
* **the candidate stylesheet with its comments blanked out does not contain the
  word `basket` at all** (raw: 4 lines, stripped: 0). This is the honest form of
  "no basket selector survives" — the raw file does still say the word four
  times, as prose explaining why the neighbours survived, and those four are
  declared and counted so a fifth (the shape a real leftover rule takes) cannot
  hide among them.
* `functions.php` retires the old token through its one enqueue line, enqueues
  the new one, and **its brace structure does not move** (974−968 = +6 on both
  sides).
* `inc/config-pdf.php`'s function set is exactly the baseline's minus the two
  declared names, its route still registers, and **over the whole theme every
  `sinofresh_*` name that is still called is still defined** (111 declared, 76
  called, 0 dangling). That last clause is the only check in the batch that
  would see a dangling call on the endpoint path.
* `basket.js` is the only deleted file, and in the code the theme **loads** the
  string `basket.js` appears zero times; the one surviving mention is the
  docblock in `config-pdf.php` that records its removal.

### 4.1 Three controls that failed for the wrong reason, and the fix

Writing this proof produced three instructive failures. All three are the same
shape: **a control that fires is not a control that fires for its reason.**

1. **`NC6` fired on the wrong rule.** The mutant was supposed to remove a closing
   brace so that only the brace rule could see it. The first implementation
   shortened the interval to match, so the *interval* rule caught it instead, and
   the control proved nothing about the brace rule. Fixed by turning one removed
   `}` into a selector line: same interval, same total, same boundary text (the
   anchor check reads the base blob, not the mutated list) — only the brace
   composition moves. `fails()` now takes a `want` and *names* the rule it
   requires, which is the discipline that stops one defect talking through
   several mouths.
2. **`NC1` fired on the wrong rule, then was aimed properly.** "A wider range
   with foreign removals" first used "two commits back", and that range failed on
   the *anchor text* — because the H7e commit that bumped the token three lines
   above this batch's reach leaves `style.css`'s diff the *same 15 intervals*.
   The range is now picked by *measurement* (the most recent commit whose
   stylesheet diff removes meaningfully more than this batch's 404 lines), and
   every path that range touches is declared so the file-set rule cannot answer
   first. It now fails on the interval rule, as intended.
3. **Two survivor counts were written from assumption rather than measurement.**
   An assertion demanding four occurrences of `.sf-inquiry-modal` failed on a
   correct file: the string occurs 36 times, once per BEM child. A second,
   `.sf-certmodal,`, failed for the mirror reason — one *line*, two
   *occurrences*, because the same selector list appears again inside the
   reduced-motion block. Both now count occurrences measured off the candidate,
   and those measured values are what §4 declares.

---

## 5. The browser pass — `tools/b2d_h7f_e2e.py` (65 / 65)

**Site quiescent** before anything was trusted: `content_fingerprint()` (every
post's `id,modified`, paginated, ordered by id) taken at both ends of the pass —
`f6e7e15d1fd31573f93396c40209f994fb181630c419129d6be8c1d782b64d60`, 50 rows,
**identical**. Same digest as H7e's, which is the expected result: this batch
changes no content.

Five things the gate and the confinement proof cannot see, and what was measured:

* **The browser never asks for `basket.js`.** Read back off
  `performance.getEntriesByType('resource')` — **0** requests, and **0** elements
  carrying a basket class, and **0** `aria-label`s mentioning a basket, on both
  desktop and phone. This is the one claim about the enqueue that a page's bytes
  cannot make: a cached page, a plugin or an unrelated shortcode emitting the tag
  would show up here and nowhere else.
* **The header still works without its middle child.** `.sf-header__cta` is a
  flex box and it lost a child. Measured: the container is still laid out
  (children 1, box 134×48), the Get a Quote button is at 1186,55 with a real box
  and `visibility: visible`, `href="/contact/#quote"` unchanged, and the header
  is 81 px tall — not a collapsed strip. Logo and 16 nav links still there.
* **On a phone the header is unchanged too.** This one needed a correction. The
  first version asserted the CTA button is *visible* at 420 px; it is not, and
  never was — a pre-existing rule hides the CTA **button** at the phone
  breakpoint, and the comment above it used to say *"the inquiry basket icon
  inside the same container stays"*. The carve rewrote that comment, which is
  exactly why the correct claim is the narrower one: **the container is still in
  flow, the button is still hidden by the same rule, and the hamburger it now
  hugs is still there.** Asserting the pre-existing divider is the check that
  gives a future edit to that comment block something to trip over.
* **Both dialogs that shared the basket's four rules still open**, and are
  measured rather than assumed: `.is-open` set, `hidden` removed, panel 520×852
  (cert) and 560×805 (inquiry), the **element under the panel's centre point is
  the dialog itself** (the one place the whole layer stack has to own), computed
  `z-index` 10010 — its own step above the shared backdrop's 10000 and above the
  float stack's 9998 — and the scroll lock applied and released. Both were closed
  with the page's own close button, never Escape: two Escapes land the harness on
  `about:blank` and every assertion after that measures the wrong document.
* **The endpoint answers — and this is also how the pass proves which copy
  replied.** A basket payload returns **400** `{"message":"Unknown dosage form
  slug."}` as `application/json`. The dev box's live theme is several batches
  behind and its endpoint still had basket mode, which answered **200 with a
  PDF**; so a 400 with the single-configuration message is only producible by the
  candidate. A real configuration (`email: ""`, so nothing is sent) returns
  **200**, `application/pdf`, `%PDF-1.7`, 28,432 bytes. Both responses were
  written to files rather than captured on a pipe — reading PDF bytes through a
  text pipe dies inside the harness's own decoder, which reads like a failure of
  the thing under test.

No script errors on any page.

---

## 6. Frames — `docs/batchH7f-shots/` (6, checked by `tools/b2d_h7f_shots.py`)

| frame | viewport | what it is for |
|---|---|---|
| `h7f-01-header-desktop.png` | 1440×900 | the header with the CTA where the bag button sat, now holding only Get a Quote |
| `h7f-02-header-phone.png` | 420×900 | the same header at 420, where the CTA button is hidden by the phone rule |
| `h7f-03-footer-desktop.png` | 1440×900 | the footer: the cookie banner and the float stack that shared the drawer's block |
| `h7f-04-certmodal-open.png` | 1440×900 | `/quality/` with the certificate dialog open |
| `h7f-05-detail-bottom-closed.png` | 1440×900 | the detail page at the bottom of the scroll, nothing open |
| `h7f-06-detail-bottom-inquiry-open.png` | 1440×900 | the same offset with the inquiry dialog open |

The checker asserts each frame is a real PNG at the viewport it claims, that the
decompressed IDAT carries **more than 8 distinct byte values** (a
`screenshot <selector>` below the fold on this site returns a correctly sized
*blank* block — measured in H5, re-measured in H6 — which is why "the size is
right" is not evidence of anything), and that two pairs differ:

* `05` / `06` — **the pair carries the batch's claim**, and it is taken from the
  *fixed* float button on purpose. The other opener is in the flow, so clicking
  it scrolls the page and the two frames would differ by the scroll rather than
  by the dialog. The E2E asserts the offset is unchanged across the pair
  (`scrollY 5619 → 5619`), so the only difference in the two files is the dialog.
* `01` / `03` — two scroll positions on the same page at the same viewport, which
  must not be the same picture. This is the cheap check that the capture is not
  stuck on one frame for the whole pass.

**VERDICT: PASS — 6 frames, each a real render the size it claims** (min 91,154 B,
max 958,949 B), both pairs differ.

---

## 7. Preconditions and the state of the dev box

* **Site quiescent** — see §5. Digest identical at both ends, 50 rows.
* **WP core `7.1.2`**, verified on the box before the captures, unchanged from
  H7e. A core move mid-batch changes every page's core asset URLs and makes
  captures from before it incomparable (batch H7d lost a round to exactly that).
* Preflight copy: **`0b015e1`** (`2.10.67`), which is the candidate. **It stays
  installed as the next batch's starting point.** Verified byte-identical to the
  local tree:

  | file | sha256 |
  |---|---|
  | `functions.php` | `d8539adc7637f927470ed033fe384ab91759292f30860c817c3241da3e44a5f1` |
  | `style.css` | `93bd732f3c33ade870212dc851daffc6019fb88b971490feb945f7b87ce9287b` |
  | `inc/config-pdf.php` | `6f8a778149c36a670df3d471df0983518c53e2f4f67c34ca1bb5b58cce8c070a` |

  `assets/js/basket.js` is absent from the copy, as it should be.
* `mu-plugins/` holds its four files: `zz-sf-dev-lockdown.php`,
  `zz-sf-preflight.php`, `zz-sf-preflight.log`, `zz-sf-preflight.log.prev`.
* **Not live.** Step 6 skipped.

---

## 8. Evidence on disk

| what | where |
|---|---|
| baseline capture (75 pages, `2.10.66`) | `_backup/b2d-h7f-baselines-r2/` |
| candidate capture (75 pages, `2.10.67`) | `_backup/b2d-h7f-candidates/` |
| A/A capture (same install) | `_backup/b2d-h7f-candidates-aa/` |
| gate logs: main / source / matrix / negctl | `_backup/b2d-h7f-logs/` |
| confinement + its negative controls | `_backup/b2d-h7f-logs/confine*.txt` |
| browser pass (65 rows + both fingerprints) | `_backup/b2d-h7f-e2e.json` |
| the six frames | `docs/batchH7f-shots/` |

The baseline had to be re-fetched once: the first pass returned `000` for
`/zh/formulas/bladder-support-powder/`, and a baseline with one missing page is a
baseline that silently compares 74. `-r2` is 75/75 × 200.

Tools added: `b2d_h7f_carve.py`, `b2d_h7f_confine.py`, `b2d_h7f_e2e.py`,
`b2d_h7f_shots.py`. Tool changed: `b2d_h7_gate.py` — the `h7f` declaration, and
`nc13_label` so a batch can name what its direction control is testing.

---

## 9. Registered, not done

* **`sinofresh-theme/_backup/` ships to production — 348 tracked files.** The
  repository sweep in the confinement proof walked into it and found 17 archived
  `functions.php`-era files that still enqueue a `basket.js` from an older
  lineage. None of them is ever loaded, so this is not a dangling reference and
  not this batch's to fix — but it is three hundred and forty-eight stale PHP,
  CSS and HTML files going to production with the theme, including full copies of
  pages that no longer exist. Same class as the already-registered
  `sinofresh-theme/tools/` note. Worth one cleanup batch with the same five-layer
  zero-reference forensics used in the dead-asset batch.
* **`sinofresh-theme/tools/_cert_basket_regression.js` references the deleted
  basket UI.** It is a registered harness file that ships with the theme; running
  it would now fail. Carried forward from the H7f scan.
* **`functions.php`'s Organization schema hand-copies its address default** instead
  of reading `sf_site_settings_defaults()`. Carried forward from H7e.
* **`templates/page-about.html` and `templates/page-contact.html`** carry the
  origin string as body copy — content, not a renderer.
* **`docs/batch2d-stepH7c.md`'s "Place of Origin is a constant until H7e"**
  source assertion is false by design (H7e's note). Left as it was.

## 10. Next

**H7a's leftovers** — the missing `docs/batch2d-stepH7a.md`, and the Video-path
mu-plugin fixture (create, verify, remove; DB zero-trace). Then the five-batch
summary, and stop.

## 11. Still the user's to do before go-live

**Post 158** (`joint-support-soft-chews`) carries test placeholder data —
`Recommended For` → `testsadasdfasf`, `Use Cases` → `sdasdasdasad`, and
`sf_formula_price_tiers` → `[{"qty":"200","price":"2.5"}]`. Written by an
18:21:29 wp-admin edit, **not** introduced by any batch here. Left untouched
under the standing ruling, but it is on the front end now and would go live with
the site.
