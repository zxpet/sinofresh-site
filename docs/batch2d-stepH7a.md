# Batch H7a — the media band gets the switch, and loses the heading

**Status: ✅ complete — code in `2.10.62`, and the record plus the Video-path
verification are the closure.** Step 6 (`git pull` on the dev box) **skipped**,
as in every batch H2b1..H6 and the rest of H7.

| commit | what |
|---|---|
| `ea17125` | Batch H7a: the media column gets the switch it was missing, and loses the heading that was only ever repeating the h1 |
| `d2b5bbd` | Batch H7a: archive the five gates that assert the heading this batch deleted |
| (this document) | Batch H7a closure: the Video path exercised for the first time, and the record |

Diff: **3 files, +280 / −118** for the product commit, plus **5 files, +67 / −0**
of archival comments.

| file | change |
|---|---|
| `assets/js/formula-gallery.js` | +147 / −64 — the switch, and the strip's video mode |
| `functions.php` | +49 / −25 — the switch is rendered in PHP, the heading is gone |
| `style.css` | +84 / −29 — a grid area for the switch, and four rules that died |

Two tokens moved, **both in both places**: `style.css` `2.10.61 → 2.10.62`
(the header and `functions.php`'s enqueue), and `formula-gallery.js`
`2.0.0 → 2.1.0` (its enqueue).

Baseline for the gate: **`dac9871`** (the H6 closure).

---

## 1. What the scan found, and why the heading was not "just redundant"

The brief said the heading was useless. The scan's job was to find out whether
that was true *by accident* or *by consequence*, because the two call for
different fixes.

* **The duplication is total and mechanical.** On 42/42 detail pages,
  `h2 == "A Closer Look at " + h1`, and not one page fails. It is the first of
  nine `h2`s, and the outline survives its removal.
* **It is the composite of two commits, not one decision.** `cb63af6`
  (2D-Step2) wrote `Inside Our {dosage} Production` on the eight dosage pages,
  where it does not repeat the `h1`. `cdcf4d3` (2D-Step3) moved it to the 21
  detail pages, and `9f4ee30` (2D-Step4) renamed it to `A Closer Look at
  {formula}`. Neither commit intended a duplicate; the duplicate is what the
  pair produced.
* **The reason it was written no longer exists on these pages.** One of the
  heading's stated justifications in `docs/batch2d-step2-plan.md` is that at 32
  characters it fits the dot-rail's label without an ellipsis. `toc-nav` is
  **enqueued zero times** on a detail page and `.sf-toc` appears **zero times**
  across all 75 pages. The heading was built for a rail that is not there.
* **Nothing reads it.** Zero JS references, zero ARIA references (the stage uses
  `aria-label`, not `aria-labelledby`), zero JSON-LD hits, and neither live gate
  (`b2d_h6_confine.py`, `sf_masked_cmp.py`) names it.
* **Five historical gates do name it** — `b2d_c_confine.py`,
  `b2d_g_confine.py`, `b2d_s4_confine.py`, `b2d_s4_evidence.py`,
  `b2d_s2_check.py`. Re-running any of them against the candidate would now
  FAIL, and the failure would be the batch's, not theirs. That is what `d2b5bbd`
  is: five comment-only edits marking those assertions archived, **zero logic
  changes**.
* The copy is generated in exactly one place, so **the deletion needs no DB
  edit**. (The TranslatePress dictionary already holds 21 `A Closer Look at …`
  rows, all untranslated; they become orphans and the next TP sync collects
  them. No action taken, by design.)

Four rulings were taken, and the batch is their sum: **Q1-a** build the
`[Photos][Video]` switch the band was missing, centred under the main photo with
a green underline on the selected label; **Q1-b** emit `[Video]` only when the
record has one, so no dead tab ships; **Q2** delete the heading and the two CSS
rules it owned; **Q4** carry all of it in one batch.

## 2. Three implementation constraints the scan produced

* **`.sf-js` could not be reused.** It is emitted only on the dosage *archive*
  page, so a detail page has no such hook. The band uses its own
  `.sf-gallery--js`, added by the script at init and treated as "paint nothing
  until it is there" by the stylesheet — which is the same no-flash,
  degrades-without-JS contract, reached a different way.
* **The two labels are rendered in PHP, not built by the script.** They are the
  only translatable strings in the band and the language layer only sees
  server-rendered text; a button created in JS is invisible to it.
* **Two `grid-template-areas` blocks had to move together** — the base
  single-column one and the ≥1101px one. Changing one and not the other leaves
  `grid-area: tabs` naming a region that does not exist, which is silent in the
  stylesheet and obvious only when the switch lands in the wrong place.

## 3. The gate — `tools/b2d_h7_gate.py --batch h7a`

| pass | result |
|---|---|
| A/A | **75 / 0** |
| main proof (direction `insert`) | **75 pages, 0 differing**, applied 42 (declared 42) |
| coverage | **8 / 8** |
| invariants | **7 / 7** |
| masked-blob read-back | 23 page(s), 0 differ |
| sabotage matrix | **7 / 7 caught** |
| named negative controls | **NC1–NC8, 8 / 8** |
| source | **16 / 16** |

The 42 declared edits are the 42 detail pages (21 formulas × EN/ZH), each losing
one heading and gaining one switch.

**The matrix**, because two of its seven are more than they look:

| mutant | verdict |
|---|---|
| switch not inserted | caught — 42 pages |
| switch inserted before the stage closes | caught — 42 pages |
| style token not folded | caught — 42 pages |
| JS token not folded | caught — 75 pages |
| one page left untransformed | caught — 1 page |
| a stray character on one page | caught — 1 page |
| one label flipped to Video | caught — 1 page |

The "JS token not folded" mutant fails on **75** pages while the style token
fails on 42, and that is the honest shape of this batch: the stylesheet is only
linked from the pages that have the band, while the script's version is in the
enqueue on every page that loads it.

## 4. The Video path — never exercised until now (39 / 39)

**This is the part that was missing, and it is the part that matters.** The
`[Video]` label is emitted only when the record carries a video, all 21 formulas
are without one, and so **the whole second half of the renderer had never run on
this site**. Every one of the 75 pages the gate captured takes the other branch.
A branch that has never executed is not a branch that works; it is a branch that
has not been wrong yet.

Three ways to reach it: write the meta (a row in the database, against the
batch's standing ruling), post the admin form (a request that could write), or
filter the read. The third was taken —
`tools/b2d_h7a_video_fixture.php` is a mu-plugin that supplies
`sf_formula_video_url` to **one** post out of the metadata layer, and
`tools/b2d_h7a_video_probe.py` installs it, verifies, removes it, and proves the
removal.

| | before | with the fixture |
|---|---|---|
| tabs | 1 — `[Photos]`, pressed, active | 2 — `[Photos]` pressed / `[Video]` released |
| frames on `/formulas/joint-support-tablets/` | 4 | 5, the new one `--video` with `data-video-id="SFH7AFIXTURE"` |
| visible frame | slot 1 | slot 1, and slot 2 once `[Video]` is clicked |
| iframes / YouTube requests | 0 / 0 | 0 / 0, before **and** after the click |

What holds, measured rather than inferred:

* the id travels through `sinofresh_formula_video_id()` intact;
* `[Video]` and `[Photos]` swap `aria-pressed` and `is-active` in both
  directions, and the stage's `aria-label` becomes the video's own alt
  (`Tablets product video`);
* the revealed frame has a real box (607×607) and its still **actually rendered**
  — asserted on `naturalWidth`, not on the attribute;
* it stays a **facade**: `Play video` is a `<button>`, no `<iframe>` is ever
  created, and not one request goes to `youtube.com` or `i.ytimg.com`. The probe
  never presses Play;
* and the switch takes the band back to where it started.

**The removal is the deliverable as much as the verification.** A fixture left
behind on a dev box becomes a difference nobody remembers making. So removal is
in a `finally`, and three checks follow it: `mu-plugins/` is back to exactly its
four standing files, the page has lost the `[Video]` tab, and — the one that
cannot be talked around — **the render is identical to the pre-fixture capture
under the same mask set**. `wp_postmeta` row count, `sf_formula_video_url` row
count and `MAX(meta_id)` read `359 / 0 / 566` before, during and after: the
fixture wrote nothing, so there is nothing to roll back and no auto-increment
left behind.

### 4.1 Two things the probe got wrong first

Both are the same shape as the mistakes the other H7 batches record: an
assertion that reads one thing and claims another.

* **"Visible" is two mechanisms on this band.** The server ships every frame after
  the first with `hidden`; at init the script takes `hidden` off the **photo**
  frames and controls them with `.sf-gallery__slide--off` instead, deliberately
  leaving the video frame on `hidden` until its tab is chosen. Reading only
  `hidden` reported **four frames visible when one was**, and would have
  "confirmed" a broken band. The predicate is now "neither `--off` nor
  `hidden`".
* **The still is fetched at page load, and always was.** The probe asserted the
  poster was *not* yet loaded, on the theory that a lazy image inside a hidden
  frame is not fetched. It is, and the renderer's own note says so — "a page load
  costs one image". The facade's promise is about YouTube's **player**, not its
  thumbnail, and the two assertions that matter are the ones that count iframes
  and third-party requests.

One thing the probe also had to learn: the frame count needle
`class="sf-gallery__slide"` does not match the video frame, whose class is the
photo class **plus** a modifier. It reported 4 frames where the browser reported
5 — a counting bug that would have read as a renderer bug.

## 5. Frames — `docs/batchH7a-shots/` (2, `tools/b2d_h7a_shots.py`)

| frame | what it is for |
|---|---|
| `h7a-01-gallery-photos.png` | the band as it ships: two tabs, `[Photos]` active, product photo showing |
| `h7a-02-gallery-video.png` | the same band after `[Video]`: the video frame revealed, photo frames off |

Both are 1440×900 viewport frames, checked for a real PNG at the size it claims
and for more than eight distinct byte values in the decompressed IDAT. They
**differ**, which is the claim: the click changed the render. The checker is
H7f's, reused through `verify()` rather than copied — two copies of a checker
drift until one of them stops checking.

The poster in `02` is a still the dev site already serves, supplied by the
fixture for one reason: `i.ytimg.com` is unreachable from the machine that
judges this, so the frame would otherwise photograph as a hole where a broken
image is — a fact about a third party's CDN, not about H7a.

## 6. Preconditions and the state of the dev box

* **Site quiescent.** The captures this batch was judged on were taken in one
  session; `content_fingerprint()` was used to establish that the site had not
  moved between them. Worth recording for the next batch: an A/A attempt that
  compared `b2d-h6-candidates` against `b2d-h7a-baselines` **crossed the
  18:21:29 post-158 edit** (two pages moved, +3,384 and +3,645 bytes) and is
  therefore not an A/A at all. A/A must be two captures of one state; the pair
  used was `b2d-h7a-cand2`.
* **A new per-request noise source appeared during this batch.** Gravity Forms'
  `gform_currency` changes value on every response, on 23 pages. It is already
  covered by the mask set the gate imports from H6 — which is why the gate
  imports it rather than carrying its own.
* The preflight copy was installed from `d2b5bbd` (`2.10.62`,
  `formula-gallery.js 2.1.0`) at the time; a snapshot was taken at
  `/root/preflight-snapshot-20260922-111020.tar.gz`. **It has since been
  superseded**: the copy now installed is `0b015e1` (`2.10.67`), put there by
  batch H7f. This record describes H7a's own state; the box has moved on.
* `mu-plugins/` holds its four standing files, and the Video fixture **is not
  among them** — verified again at the end of this closure.
* **Not live.** Step 6 skipped.

## 7. Evidence on disk

| what | where |
|---|---|
| baseline capture (`2.10.61`, 75 pages) | `_backup/b2d-h7a-baselines/` |
| candidate capture (75 pages) | `_backup/b2d-h7a-candidates/` |
| second capture of the same state (the real A/A) | `_backup/b2d-h7a-cand2/` |
| gate / matrix / source results | `_backup/b2d-h7a-{gate,matrix,source}.json` |
| Video-path pass (39 rows, both fixtures states) | `_backup/b2d-h7a-logs/video.txt` |
| the two frames | `docs/batchH7a-shots/` |
| preflight snapshot taken at the time | `/root/preflight-snapshot-20260922-111020.tar.gz` |

Tools added by this closure: `b2d_h7a_video_fixture.php` (the mu-plugin source),
`b2d_h7a_video_probe.py`, `b2d_h7a_shots.py`. Tool changed: `b2d_h7f_shots.py` —
its frame checker split into `verify()` so this batch reuses it.

## 8. Registered, not done

* **`role="tabpanel"` and the `tablist` are siblings, and the `tablist`'s
  `aria-label` is hard-coded.** The stage carries `role="tabpanel"` but the
  script-built `role="tab"` buttons point `aria-controls` at the individual
  `figure.sf-gallery__slide` elements, not at the panel; and the strip's
  `aria-label` reads `Product photos` — which, now that a video frame can be in
  the same group, tells a screen reader that the group of photos contains the
  video. Found during H7a's scan; out of scope for it and for this closure. It
  is an ARIA-modelling question, not a copy question.
* **The TranslatePress rows for the deleted heading** (`A Closer Look at …`,
  ids 1537–1557, all untranslated) are orphans by design. Left for TP's own
  sync.
* **The five archived gates** now describe a source state that no longer exists.
  Their assertions are marked archived rather than rewritten, which is the same
  treatment `docs/batch2d-stepH7c.md` gets for its "Place of Origin is a
  constant until H7e" assertion.
* **`sinofresh-theme/_backup/` (348 tracked files) and
  `sinofresh-theme/tools/`** ship to production. Registered under H7f; noted
  here because H7a's own `formula-gallery.js` and `style.css` are among the
  files those archives hold stale copies of.

## 9. Next

The five-batch summary, and stop. Nothing else in H7a, H7b, H7c, H7d, H7e or
H7f is outstanding: every batch is committed and pushed, and the only step not
taken in any of them is Step 6.

## 10. Still the user's to do before go-live

**Post 158** (`joint-support-soft-chews`) carries test placeholder data —
`Recommended For` → `testsadasdfasf`, `Use Cases` → `sdasdasdasad`, and
`sf_formula_price_tiers` → `[{"qty":"200","price":"2.5"}]`. Written by an
18:21:29 wp-admin edit, **not** introduced by any batch. Left untouched under the
standing ruling, but it is on the front end now and would go live with the site.
