# Batch H7e — Place of Origin and OEM / ODM move from constants to Site Settings

**Status: ✅ complete.** `2.10.65 → 2.10.66`. Step 6 (`git pull` on the dev box)
**skipped**, as in every batch H7a..H7d: the batch is judged on a preflight copy
and the dev live site keeps serving the pre-H2b1 theme.

| commit | what |
|---|---|
| `0c8f90f` | Batch H7e step 1: the two factory facts get a settings page, and no page moves |

Diff: **4 files, +130 / −8**, all theme-side, all of it PHP plus one changed
line of `style.css`.

| file | change |
|---|---|
| `functions.php` | +39 / −8 — defaults gain the two keys, the renderer reads them, the version token moves in both places |
| `inc/formula-admin.php` | +69 / −0 — the subpage, its two `register_setting` entries, and one `$d` line |
| `inc/formula-pools.php` | +28 / −0 — one new function, the reader |
| `style.css` | +1 / −1 — the `Version:` header and nothing else |

The batch record and this document are committed separately, so the confinement
proof's range (`23357ad..0c8f90f`) contains code only.

---

## 1. What was scanned, and the decision that was made

The brief named two constants. The scanner's job was to find out how many
carriers each value actually has, because a value can be printed by more than
one thing and one of them can exist only at runtime.

`Linyi, Shandong, China` — **five carriers**, one in scope:

| # | carrier | in scope? |
|---|---|---|
| 1 | `functions.php` `$rows['Place of Origin']` in the spec-sheet renderer | ✅ **the batch target** |
| 2 | `functions.php` `sf_site_settings_defaults()['sf_contact_address']` — a substring of the street address | ❌ different meaning, registered |
| 3 | `functions.php` the Organization schema's `streetAddress` fallback, a hand-copied string | ❌ registered |
| 4 | `templates/page-about.html` body copy | ❌ registered |
| 5 | `templates/page-contact.html` address line | ❌ registered |

`Available` — **one carrier**, and it is the target.

JavaScript carriers: **none** for either value. Neither value is built at
runtime by any script. That matters because this project has already been bitten
once by a value whose fourth carrier was constructed by JS and appeared in no
capture at all (batch H5, the product-image `alt`); the scan is where that is
ruled out rather than assumed.

**Decision: no stop.** The two constants exist, each has exactly one carrier in
scope, and the instruction that defines the batch (Site Settings subpage, two
defaults, constants switch to the option) describes what the scan found. Carrier
#3 is a genuine finding — a default value copied by hand instead of read from
`sf_site_settings_defaults()`, exactly the drift this batch argues against — but
it is **another batch's business** and is registered rather than absorbed.

**Design choices, and why not the alternatives.**

* **A subpage, not a section on the parent page.** The brief says subpage; the
  project already has two (`Container Library`, `Global FAQ`), both built the
  same way, and a third one matches them. A new section on `Site Settings`
  would have meant editing the parent page's markup and its `$text_fields`
  loop — a wider diff on a file the byte gate reads, for no gain.
* **One option group.** The fields register into `sf_site_settings` and the page
  posts with `settings_fields('sf_site_settings')`, so a save on any of the four
  settings screens leaves the other screens' values alone (WordPress updates
  only the keys present in the request — verified live: the E2E asserts
  `option_page === 'sf_site_settings'`).
* **One reader, not `get_option()` twice.** `sf_formula_factory_value($key)`
  sits beside `sf_formula_certifications_value()` in `inc/formula-pools.php`,
  which is where the renderers' value readers already live. Both fall back to
  `sf_site_settings_defaults()` rather than repeating the string, so the field
  the admin sees and the value the page prints cannot disagree.
* **No asset on the new page.** It has no repeating row for `sf-mb-tables.js`
  to clone and no image for `wp.media` to pick, so its hook is deliberately
  absent from the list in `admin_enqueue_scripts()`. The E2E proves absence
  *and* proves the contrast (the Container Library does carry them).

---

## 2. The gate

Same tool, same mask set, a new **declaration** — `BATCHES['h7e']` in
`tools/b2d_h7_gate.py`. The comparison lives in one place and each batch
contributes the claims it makes; writing a sixth gate would have meant a sixth
copy of the mask set, and the mask set is the part that must not drift.

### 2.1 A new direction: the NULL EDIT

H7e is the first batch in this project whose **rendered output does not move at
all**, and that forced a decision about the direction.

* `insert` (H7a, H7b) needs the edited bytes to splice into the baseline.
* `delete` (H7c) needs the removed region's bytes to cut out of the candidate.
* `symmetric` (H7d) applies one pure function to both sides.

H7e has nothing to splice and nothing to cut: the two rows are still on the page,
still carrying the same text, and what changed is where the text comes from. So
the declaration is `mode: 'symmetric'` with an **identity transform** —
`applies: 0` on both sides — and the claim is the plainest one available:

> `mask(fold(baseline)) == mask(candidate)`, page by page, on all 75.

That is not a vacuous check, and the matrix proves it is not: three of the four
mutants move a page.

### 2.2 The one declared edit

The declaration is not empty: the **version token** travels `2.10.65 → 2.10.66`
in `style.css`, and the fold is what makes the two captures comparable. A
candidate that had forgotten to bump it fails the proof on all 75 pages — the
`tokens: []` mutant measures exactly that difference (75 differing pages).

`applies: 0` with a non-empty `tokens` is therefore the precise shape of this
batch: *the batch applies no edit to any page's markup, and exactly one edit to
the pages' version envelope.*

### 2.3 Results

| pass | result |
|---|---|
| A/A (candidate captured twice, same install) | **75 pages, 0 differing** |
| main proof — `symmetric`, identity, both sides | **75 pages, 0 differing**, applied 0/0 and 0/0 |
| coverage | **7/7** |
| invariants | **15/15** |
| masked-blob read-back | 23 pages, 0 differ; 46 non-text currency values |
| sabotage matrix | **4/4 caught**, none a no-op |
| named negative controls | **17/17** |
| source pass | **20/20** |

Coverage and the counts, verbatim:

```
?ver=2.10.65          candidate count = 0    (want 0)   ok
?ver=2.10.66          candidate count = 75   (want 75)  ok
the origin row still carries its default   base 42 -> candidate 42  ok
the OEM row still carries its default      base 42 -> candidate 42  ok
the origin row label is unmoved            base 42 -> candidate 42  ok
the OEM row label is unmoved               base 42 -> candidate 42  ok
every other origin mention is untouched    base 196 -> candidate 196  ok
```

The first two counts are the batch's central claim written as bytes: the
**value is locked to its cell** — `<dd class="sf-fdetail-specs__value">Linyi,
Shandong, China</dd>`, not merely "the string is somewhere on the page" — and it
is there 42 times before and 42 times after, once per detail page. The last one
is the precision claim: the other 154 occurrences of that string are untouched,
so the batch moved one row's source rather than replacing a global string.

The invariants add four `scoped` claims (one origin `<dd>` and one OEM `<dd>`
per detail page, and nowhere else), keep H7c's three `order` claims, and add one
that exists for this batch alone:

```
the factory settings slug stays in wp-admin   pages base=0 cand=0 (want 0)  ok
```

A settings page that leaked its own slug onto a product page would be invisible
to every other check in the gate.

### 2.4 The change the gate had to absorb

`negctl`'s **NC13** asserted one verdict in code: *the main proof is blind to the
payload, coverage is not*. That is true of `delete` — the region is carved out
before the comparison, so renaming a label inside it leaves the main proof green.
It is **false of a null edit**, where nothing is carved out and the main proof
compares the payload like everything else.

Run against the old literal, H7e would have reported a working gate as **FAIL**.

So the verdict now reads off the declaration (`nc13_mode`, default `'blind'`;
H7e sets `'sighted'`), and the control asserts the honest thing for the
direction:

```
NC13 the null edit SEES the payload, and coverage confirms it   ok
     page=formulas__joint-support-soft-chews.html  main_red=True  coverage_red=True
```

Hard-coding either verdict would have made the control assert the direction
rather than test it. It now has two shapes and both are exercised.

### 2.5 The sabotage matrix

```
the version token is not folded              caught   differing pages = 75, applied = 0/0
the null edit claims to have applied something  caught  differing pages = 0, applied = 0/1
the OEM row is renamed on one page           caught   differing pages = 1, applied = 0/0
a stray character on one page                caught   differing pages = 1, applied = 0/0
```

The second mutant is the interesting one on this direction: with the real count
at 0, a declaration that claims an edit is caught by the **count** rather than by
a page diff — which is the only way the number can do work when the true value
is zero.

The third is the one that answers "is this gate really looking at the payload?"
Rename one row label on one page and exactly one page differs.

### 2.6 Source pass (20/20)

Nothing on a rendered page can say **where** a value came from, so this is the
only pass that can tell the batch apart from doing nothing:

* the reader is defined, reads by key, falls back to `sf_site_settings_defaults()`
  and treats an empty value as the default;
* the defaults carry the two strings the constants held, character for character;
* the renderer reads through the reader, and **both constants are gone**
  (`esc_html('Linyi, Shandong, China')` → 0, `esc_html('Available')` → 0);
* the subpage is registered under `sf-site-settings`, its renderer exists, both
  fields register in the `sf_site_settings` group with the parent page's
  empty-falls-back sanitizer, and **no factory hook was added** to the admin
  asset list while the other two subpages' names are still exactly there;
* the version token is bumped in the enqueue and no `2.10.65` survives;
* `style.css` declares `2.10.66` and no `2.10.65` header survives.

### 2.7 Confinement — `tools/b2d_h7e_confine.py` (new, 14 checks + NC1–NC8)

The gate compares pages. A page is not a stylesheet, not a settings page, and
not a function body that never runs on a front-end request — so a file whose
bytes never reach a page needs its claim stated in its own terms.

**This is not `b2d_h7c_confine.py`, and the difference is not cosmetic.** That
proof is shaped like H7c: it asserts `style.css` gains *exactly one contiguous
block* and every selector inside it names the namespace. H7e adds **no CSS rule
at all** — its `style.css` diff is one header line — so H7c's assertion reads
`len(block_runs) == 1` on a run list of zero and reports FAIL. Correctly, for
H7c's claim; pointlessly for this one. H7c also asserts PHP's additions are
*contiguous*, and H7e's `functions.php` changes in four separate places.

What both need is the same underlying claim in the terms of the file: **nothing
changed that the declaration does not name.** Written out, over-specified:

```
the batch touches the four declared theme files and no others     ok
the two readings of the file set agree                            ok
style.css deletes the old version header and only it              ok  removed=['Version: 2.10.65']
...and adds back the new header and nothing else                  ok  runs=[['Version: 2.10.66']]
functions.php deletes exactly the seven declared lines            ok  removed=7 undeclared=none
...and adds back five runs of exactly the declared sizes          ok  [1, 3, 16, 8, 4]
...and neither declares nor loses a function                      ok  base=66 cand=66
formula-pools.php only gains — not a character is deleted         ok  removed=0
...in one run of the declared size                                ok  [28]
...and the set of functions it declares grows by the reader       ok  gained=['sf_formula_factory_value']
formula-admin.php only gains — not a character is deleted         ok  removed=0
...in four runs of the declared sizes                             ok  [5, 14, 4, 46]
...and the set of functions it declares grows by the page         ok  gained=['sf_render_factory_info_page']
```

The **function-set equality** is the one that matters most and the one a size
check cannot replace: H7e's product is two new functions, and a batch that also
slipped a third into `inc/formula-admin.php` at line counts that kept the run
sizes indistinguishable would pass every byte comparison in the gate. NC5
builds exactly that mutant.

**NC7 passed the first time this ran**, and the reason is worth keeping: the file
set was read twice — once from `git diff --name-only`, once from the `-U0` parse
— and the equality claim used only the first, so a fifth file present in the
parse alone was reported as fine. The repair was a **cross-check**, not a
relaxation; NC8 is the control that watches it fire.

```
NC1 a stray CSS rule is caught                             caught
NC2 a deleted existing CSS rule is caught                  caught
NC3 a sixth added run in functions.php is caught           caught
NC4 an undeclared deletion in functions.php is caught      caught
NC5 an undeclared function in formula-admin.php is caught   caught
NC6 a function lost from functions.php is caught           caught
NC7 a fifth theme file is caught                           caught
NC8 a file seen by one reading and not the other is caught caught
```

---

## 3. The routing probe — `tools/b2d_h7e_probe.py` (17/17)

**This is the batch's strongest product evidence, and it exists because the byte
gate cannot supply it.**

A green main proof says the 75 pages did not move. That is the whole point of
the batch — and it is *also* exactly what a batch that deleted the two rows
would have produced. Neither the gate nor the source pass answers the question a
person actually asks: *if operations edit that field tomorrow, does the page
change?*

`pre_option_<name>` short-circuits `get_option()` **before it reaches the
database**, so the option is made to answer differently in memory and the page
is asked. **No option row is created, none is read, and the mu-plugin is
deleted afterwards** — `test -e` confirms it, and the admin orchestrator
re-checks `mu-plugins/` from a separate process.

```
before   the candidate as it ships                      -> the default prints
during   pre_option returns FIXTURE-ORIGIN-H7E          -> the fixture prints
after    the mu-plugin is gone                          -> the default returns
```

| check | result |
|---|---|
| the product page is served, not a 401 | ok (`200`/`200`) |
| the spec sheet carries the origin default | ok (1 row) |
| with the fixture in place the origin row prints the FIXTURE value | ok (1) |
| ...and the OEM row prints the fixture value too | ok (1) |
| **...and the default has LEFT that row** | ok (`origin_row=0 oem_row=0`) |
| the spec sheet itself is still in place | ok (1) |
| **the other page is untouched by the fixture on the option path** | ok (3 → 3) |
| the fixture mu-plugin is gone before the state is re-measured | ok |
| no fixture string survives anywhere | ok |
| ...and the default is back in that row | ok (`1`/`1`) |
| the product page is back to the byte count it started at | ok (`140818` vs `140818`) |
| ...and so is the page that never had the row | ok (`124906` vs `124906`) |

Two of those are the reason the probe is worth its cost. *"The default has LEFT
that row"* is the other half of the routing claim: a renderer that printed the
fixture **and** the default would satisfy "the fixture is there" alone. And
*"the other page is untouched"* is the **precision** claim — `/about/` mentions
the same string for an entirely different reason, and a batch that had replaced a
global string instead of one row's source would pass the product-page check and
fail this one.

**A bug in the probe, found by running it, and how it failed.** The first run
reported every row green and then `remote command failed (2)`. Cleanup ran
`rm -f FILE && ls FILE` under `check=True`: `ls` exits 2 on a missing file —
the outcome being *sought* — so a successful cleanup raised `SystemExit`. Two
things made it worse than a noisy error: `SystemExit` is not an `Exception`, so
the `except Exception` around the cleanup did not catch it either, and the
mu-plugin **stayed on the dev box** while the whole visible symptom was those
two words under an otherwise green run.

Repaired in three places, all of them the same lesson: `remove()` asks
`test -e` instead of `ls`, the caller asserts the removal as a *row* rather than
letting it raise, and the guard catches `BaseException`. The leftover file was
removed by hand and `mu-plugins/` was verified back to its four files before the
probe was re-run.

---

## 4. The browser passes

### 4.1 Admin — `tools/b2d_h7e_admin_e2e.py` + `.js` (orchestrator 10/10, browser 26/26)

Throwaway admin (`sf-e2e`, random 24-character password), created for the run and
deleted after it, exactly as batch H2a built its admin pass. The user list and
`mu-plugins/` are read before and after and compared.

```
the user list is readable                                   ok  1 user(s)
no throwaway admin is left over from an earlier run         ok
the throwaway admin was created                             ok  id=1010
the admin E2E passes against the candidate                  ok  exit=0
the throwaway admin was deleted                             ok
the password file is gone from this machine                 ok
...and no copy was left on the dev box either               ok
the user list is exactly what it was (zero DB trace)        ok  before=1 after=1
mu-plugins/ holds exactly what it held                      ok  4 files
```

**The contrast is what makes the absence mean something.** The new page loads no
theme asset at all, so on that page there is no URL to read "which theme is
serving this" off. The Container Library does carry the shared assets, so the
run asserts their URL first and then asserts absence:

```
the contrast page is the Container Library                                    PASS
it carries the shared admin stylesheet      .../sinofresh-theme-preflight/assets/admin/sf-mb.css?ver=1.0.0
...served by the PREFLIGHT copy, which is what makes "which theme" a fact      PASS
and both shared scripts are on it too                                          PASS
no live-theme admin asset URL anywhere on either page                          PASS
the new page loads NO theme stylesheet (sf-mb.css absent)                      PASS
...and none of the row-table script                                            PASS
...and not the settings row helper either                                      PASS
...and wp.media is not enqueued for it                                         PASS
```

Without the first half, "the new page has no `sf-mb.css`" would be satisfied by
a site where the asset is broken everywhere.

The page itself:

```
the subpage resolves (a submenu this batch adds does not exist on the live copy)
its heading is Factory Information
Place of Origin defaults to the constant it replaced: "Linyi, Shandong, China"
OEM / ODM defaults to the constant it replaced: "Available"
both fields are text inputs
and they post under the option names the reader reads: sf_factory_origin / sf_factory_oem
the labels name the two spec-sheet rows: ["Place of Origin","OEM / ODM"]
each field explains which row it feeds (2 descriptions)
the form posts to the Site Settings option group: "sf_site_settings"
and carries a settings nonce
the submit button is present: "Save Changes"
Site Settings now offers three subpages: [...,"Container Library","Global FAQ","Factory Information"]
...and this one is the current menu item: "Factory Information"
zero page JS errors across every visited screen
```

Nothing is saved. The form is read and never submitted: a settings save is a DB
write and this batch does not make one. The sanitizer's empty-falls-back
behaviour is asserted in the source pass, against the same shape the parent page
uses.

**A login flake, stated rather than smoothed over.** On the second of four runs
the login timed out (`page.waitForURL: Timeout 30000ms exceeded`) — the same
script that had just succeeded, against a freshly created user. The run after it
succeeded first try. The single-shot login was replaced by three attempts that
print the landing URL, the page title and wp-login's own error box on each miss,
so the next occurrence is an answer instead of a timeout message. The check was
not weakened; it was made diagnosable.

### 4.2 Front end — `tools/b2d_h7e_front_shots.js` (10/10)

```
the page is the PREFLIGHT copy at 2.10.66   .../sinofresh-theme-preflight/style.css?ver=2.10.66
...and not the live theme
the specification sheet is on the page
it renders a full sheet: 10 rows (12 fields, minus the empty ones)
and the two rows this batch moved are the last two, in order: ["Place of Origin","OEM / ODM"]
Place of Origin reads "Linyi, Shandong, China"
OEM / ODM reads "Available"
the sheet sits below the sticky header inside the frame (top=71)
zero page JS errors
```

**Two expectations written wrong, caught by running them, and neither was a
product bug.**

* `twelve rows` was asserted and the page renders **ten**. The renderer offers
  twelve fields and drops every row with an empty value, so the count is a
  property of the *record*: this one has no `Applicable Pet` and no `Life Stage`
  meta, which is exactly what batch H7c said when it built the sheet. A hard
  `12` was a check on today's data wearing a check on the code's clothes. It is
  now structural and stronger — the two moved rows must be present **and be the
  last two, in order**.
* The first frame scrolled the sheet to the very top of the viewport, which put
  the first two rows **under the sticky header**. The frame was honest and the
  assertion `boxTop ≈ 0` was true; a reader would have had to take the missing
  rows on trust. The scroll offset now leaves the header's height (`top=71`) and
  the offset travels with the frame.

Both are the same class of mistake, and it is worth naming: an assertion that
encodes an expectation about today's render rather than a property of the batch.

---

## 5. Frames — `docs/batchH7e-shots/` (4 frames, checked by `tools/b2d_h7e_shots.py`)

```
h7e-01-factory-info.png                200259 B  2880x2160  256 values
h7e-02-factory-info-fields.png          61411 B  2564x634   256 values
h7e-03-container-library-contrast.png  275435 B  2880x2750  256 values
h7e-04-product-spec-sheet.png          245293 B  2880x1800  256 values

h7e-01 vs h7e-03   differ   two different admin pages
h7e-01 vs h7e-04   differ   an admin page against a product page
VERDICT: PASS — 4 frames, each a real render at the width it claims
```

Captures run at `deviceScaleFactor: 2`, so the width is checked exactly (2880 for
a 1440px viewport) and the height is **not**, for the three full-page frames: a
full-page height is the content's height and will move the day an admin notice
appears, and a check that broke on that would be a check on wp-admin's chrome.
The one viewport frame (`h7e-04`) is held to both. Every frame must decompress to
more than eight distinct byte values — `screenshot <selector>` on this site
returns a correctly sized **blank** block once the element is below the fold
(batch H5's measurement, re-measured in H6), so "the size is right" is accepted
as evidence of nothing.

The two pair comparisons are what a per-frame size check cannot do: a pass that
photographed the same screen four times would satisfy every other assertion here.

All four were also **looked at**: the admin page shows the heading, both fields
with their defaults, the descriptions, Save, and `Factory Information` bolded as
the current item under a Site Settings menu that now lists three subpages; the
product frame shows all ten rows with `Place of Origin` and `OEM / ODM` intact
and correct.

---

## 6. Preconditions and the state of the dev box

* **Site quiescent** before the captures were trusted: `content_fingerprint()`
  (every post's `id,modified`, paginated, ordered by id) taken twice, five
  seconds apart — `f6e7e15d1fd31573f93396c40209f994fb181630c419129d6be8c1d782b64d60`,
  50 rows, **identical**. The baseline, the candidate and the A/A capture were
  all taken inside this window.
* **WP core `7.1.2`**, verified on the box before the captures. A core move mid-
  batch changes every page's core asset URLs and makes captures from before it
  incomparable with captures after (batch H7d lost a round to exactly that), so
  all three captures here were taken in one session rather than reusing H7d's.
* Preflight copy: **`0c8f90f`** (`2.10.66`), which is the candidate. It stays
  installed as the next batch's starting point; the baseline copy (`1c68c61`,
  `2.10.65`) has served its purpose and can be dropped when the next batch
  installs its own.
* `sha256` of the copy as installed:
  `functions.php 126dbe184119a8b1cd4aa116672860a11dae1499593a3c3e1ab78806bc4815ae`,
  `style.css 47ea6c7f30dc7b3eb6d9d0665b6f52c1f94fd09724ee71199fe1dd45662f1452`.
* `mu-plugins/` holds its four files: `zz-sf-dev-lockdown.php`,
  `zz-sf-preflight.php`, `zz-sf-preflight.log`, `zz-sf-preflight.log.prev`. The
  H7e probe fixture is not among them.
* Not live. Step 6 skipped.

---

## 7. Evidence on disk

| what | where |
|---|---|
| baseline capture (75 pages, `2.10.65`) | `_backup/b2d-h7e-baselines/` |
| candidate capture (75 pages, `2.10.66`) | `_backup/b2d-h7e-candidates/` |
| A/A capture (same install) | `_backup/b2d-h7e-candidates-aa/` |
| confinement proof + NC1–NC8 | `_backup/b2d-h7e-confine.json` |
| routing probe, all three states | `_backup/b2d-h7e-probe.json` |
| admin E2E (orchestrator + browser) | `_backup/b2d-h7e-admin-e2e.json` |
| front-end frame assertions + scroll offset | `_backup/b2d-h7e-front-shots.json` |
| quiescence pair | `_backup/b2d-h7e-quiescence.json` |
| the four frames | `docs/batchH7e-shots/` |

Tools added: `b2d_h7e_confine.py`, `b2d_h7e_probe.py`, `b2d_h7e_admin_e2e.py`,
`b2d_h7e_admin_e2e.js`, `b2d_h7e_front_shots.js`, `b2d_h7e_shots.py`.
Tool changed: `b2d_h7_gate.py` — NC13 reads its verdict from `nc13_mode`.

---

## 8. Registered, not done

* **`functions.php`'s Organization schema hand-copies its address default**
  (`get_option('sf_contact_address', 'No. 22 Zhongshan Road B3, …')`) instead of
  reading `sf_site_settings_defaults()`. Found by the carrier scan; out of scope
  for H7e; the same drift this batch argues against, in the file this batch
  edited. Worth a one-line batch.
* **`templates/page-about.html` and `templates/page-contact.html`** carry the
  origin string as body copy. That is content, not a renderer, and it belongs to
  whoever owns the copy.
* **`docs/batch2d-stepH7c.md`'s "Place of Origin is a constant until H7e"**
  source assertion is now false by design. Re-running H7c's `--source` would
  report it FAIL; that is H7c's declaration describing H7c's source state, and it
  is left as it was.

## 9. Next

**H7f** — delete the nav basket icon, `basket.js`, and the basket entry in
`config-pdf.php` (the endpoint stays). `2.10.66 → 2.10.67`, 75 pages. Then
**H7a's leftovers** (`docs/batch2d-stepH7a.md` and the Video-path fixture), then
the five-batch summary.

## 10. Still the user's to do before go-live

**Post 158** (`joint-support-soft-chews`) carries test placeholder data —
`Recommended For` → `testsadasdfasf`, `Use Cases` → `sdasdasdasad`, and
`sf_formula_price_tiers` → `[{"qty":"200","price":"2.5"}]`. Written by an
18:21:29 wp-admin edit, **not** introduced by any batch here. Left untouched
under the standing ruling, but it is on the front end now and would go live with
the site.
