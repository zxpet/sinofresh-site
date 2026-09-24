# Batch 3b-2 — deploy record

Theme commit `cfbdc2e`, installed to the preflight copy as
`sinofresh-theme-preflight`. Everything below was originally measured through
the preflight header, with live still on `2.10.77` at `4dc0906`.

**Post-pull addendum.** The tick approved the pull and dev took `fbec90b`
(`95cac91` → `fbec90b`), so live is now `2.10.78`. Both groups were re-measured
against live and reproduce field for field — `Manage 11/11` at all four widths
with the switcher intersection at 0, `term 宽=[120]` with one value x per
column, no overflow. The two theme directories are byte-identical:
`style.css` md5 `96c8ce70e65ed70730d09629258efad8` on the `cfbdc2e` blob, the
repo working tree, the preflight copy and live (a symlink) alike — the earlier
`dee6df66…` recorded here was a transcription error and matched no object in
the repository. The `2.10.77` bytes are `364ed825d4eccda4df8ede8f6c032f40`.
Re-measure with `--shots /tmp/...`: this harness's default frame directory
holds the committed before/after pair.

Two stylesheet defects, both fixed in `style.css` and nowhere else. One gate
assertion moves with them; nothing else does.

## 0. The instruction's three locations, against the source

Every location in the ticket was checked against the file before anything was
edited, and all three matched exactly.

| Claimed | Found | ✓ |
|---|---|---|
| `.sf-cookie-banner`, z-index 9999, fixed to the bottom | `style.css:3787-3796` — `position: fixed; left:0; right:0; bottom:0; z-index: 9999;` | ✓ |
| `.sf-fdetail-specs__row` is the cause, `style.css:7876` | line 7876 carried `grid-template-columns: minmax(150px, 40%) minmax(0, 1fr);` | ✓ |
| `b2d_h7_gate.py:749` hard-asserts that string | verbatim `r'\.sf-fdetail-specs__row \{[^}]*grid-template-columns: minmax\(150px, 40%\) minmax\(0, 1fr\)'`, and it read `ok x1` before the edit | ✓ |

One thing the ticket could not have known, found while checking: `b2d_h7_gate.py`
**already reads red**, before this batch, in both batches that were re-run. That
is by design and is documented in the gate itself (`tools/b2d_h7_gate.py:194-199`):
the `--source` mode is each batch's self-certification at the time it shipped,
and the version literals in it are "BASELINE-TIME claims … a later batch that
bumps style.css makes them read FAIL by design". So the criterion for this batch
is **no new red**, not all-green. §4 lays the two runs side by side.

## 1. What changed

| # | File | Change |
|---|---|---|
| A | `style.css` (+9) | `body.has-cookie-banner .trp-floating-switcher { bottom: 88px; }` after the stack's own desk rule, and the phone value `bottom: 280px` inside the existing `@media (max-width: 767px)` block, next to the stack's 268px |
| B | `style.css` (−1 +1) | `.sf-fdetail-specs__row`'s first track: `minmax(150px, 40%)` → `minmax(120px, max-content)`; the 20px gutter untouched |
| V | `style.css` + `functions.php` | `Version: 2.10.77` → `2.10.78`, both sites the theme keeps in step |
| G | `tools/b2d_h7_gate.py:749` | the assertion follows the rule it names: `minmax\(150px, 40%\)` → `minmax\(120px, max-content\)` |

Both A declarations are written on `bottom`, not through the plugin's
`--bottom` variable, and neither carries `!important`:
`body.has-cookie-banner .trp-floating-switcher` is specificity **0,2,1** against
the plugin's `.trp-floating-switcher` at **0,1,0**, so it wins on its own. The
numbers are the same family the theme already uses for its own float stack
(100 desk / 268 phone).

Not touched, as instructed: `b2d_h7_gate.py:747` (inner two tracks), `:756-762`
(the 1240/900/768 ordering chain), `b2d_h7c_e2e.py:156`. No template, no data,
no navigation, no JS.

## 2. Task A, measured

Fresh visitor each time (new browser context, so the banner is showing), one
session per cell, and every session asserts which theme it served before it
measures. `Manage × sw` is the intersection area of the Manage Preferences
button with the switcher, in px². `Manage n/11` samples the button along its own
width and counts the points that still belong to the button.

| Viewport | banner h | switcher `bottom` | live: Manage × sw | live: Manage | preflight: Manage × sw | preflight: Manage |
|---|---|---|---|---|---|---|
| 375×800 | 266px | 0px → **280px** | 3596 | **7/11** `######....#` | **0** | **11/11** `###########` |
| 768×900 | 140px | 0px → **88px** | 0 | 11/11 | **0** | **11/11** |
| 1024×900 | 97px | 0px → **88px** | 1122 | **7/11** `....#######` | **0** | **11/11** |
| 1440×900 | 76px | 0px → **88px** | 3255 | **2/11** `.........##` | **0** | **11/11** |

The switcher was not sacrificed to achieve this — it was clicked, with a real
pointer, in the preflight run at all four widths:

| Viewport | hit element | `aria-expanded` | dropdown `hidden` | links |
|---|---|---|---|---|
| 375 / 768 / 1024 / 1440 | `DIV.trp-language-switcher-inner` | `false` → **`true`** | `true` → **`false`** | `['https://dev.zxpet.com/zh/']` |

The hit element is the chip's own parent, not the chip: the chip is a static
child of `.trp-language-switcher-inner`, which is a positioned box and therefore
paints over it. That is how the plugin builds it, so the hit check asks that the
point belong to the switcher's nav at all — the first version of this check
demanded the chip itself and would have failed the switcher for being correct.

## 3. Task B, measured

`term w` is the computed width of the label track; `value x` lists the distinct
left edges of the value cells (two, because the sheet is two columns on a desk —
one per column, and the point is that each column has exactly **one**).

| Page | Width | live `term w` | preflight `term w` | live `value x` | preflight `value x` | overflow |
|---|---|---|---|---|---|---|
| `joint-support-tablets` | 1024 | 177px | **120px** | [235, 741] | [178, 684] | no |
| `joint-support-tablets` | 1280 | 227px | **120px** | [287, 919] | [180, 812] | no |
| `joint-support-tablets` | 1440 | 227px | **120px** | [367, 999] | [260, 892] | no |
| `probiotic-powder` | 1440 | 227px | **120px** | [367, 999] | [260, 892] | no |
| `joint-support-soft-chews` | 1440 | 227px | **120px** | [367, 999] | [260, 892] | no |

`template` reads back as `120px 428px` at 1280/1440 and `120px 302px` at 1024 —
a compact label track and the freed width handed to the value, which is the
whole point of the change.

The nine labels run 32–105px wide, all of them under the 120px floor, and the
floor is what makes the values line up: at 120px the widest label
(Main Ingredients, 105px) leaves a 15px dead zone, so the gap between the
longest label's last glyph and its value is 15 + 20 = **35px**, against
122 + 20 = **142px** before. A content-only track would have given every row a
different width (32…105) and staggered the values by up to 73px, which is why
the floor is there and not `max-content` alone.

Three pages, three dosage forms, same 120px — and no horizontal overflow at any
of the three widths.

## 4. Gates

`b2d_h7_gate.py --source`, before this batch and after it, same command:

| Batch | before | after | the assertion this batch moves |
|---|---|---|---|
| `h7c` | 5 FAIL | **5 FAIL** | `a row is a label/value grid` — `ok x1` before, **`ok x1` after** |
| `h8c` | 2 FAIL | **2 FAIL** | — |

The five h7c reds are `Shelf Life is the parsed shelf segment`, `Place of Origin
is a constant until H7e`, `OEM / ODM is a constant until H7e`, `the style token
is bumped in the enqueue`, `style.css declares 2.10.64`. The two h8c reds are
`style.css declares 2.10.76` and `functions.php enqueues 2.10.76 for style.css`.
Every one of them is a claim about a version or behaviours that a later batch
replaced — the gate's own comment says so — and every one of them was equally
red before this batch. **No new red.**

## 5. E2E

Three passes, all through the preflight header, and read with the same
before/after discipline the gate got — because two of the three are red, and
neither red belongs to this batch.

| Pass | Result | This batch? |
|---|---|---|
| `b2d_h7c_e2e.py --want-ver 2.10.78` | **PASS** — two tracks `568px 568px` at 1440 with the 64px gutter, one `380px` track at 420, both locales, 10 rows, labels identical EN/ZH, placement anchors in the declared order. Every step re-asserts it is still on `sinofresh-theme-preflight/style.css?ver=2.10.78` | **no red** |
| `b2d_h2b1_e2e.py` | **2 FAIL** — `E5 detail hero href = None`, `E5 the detail hero CTA did not land on /contact/ (/formulas/calming-soft-chews/)` | **no** — the same two, verbatim, on the pre-batch theme |
| `b2d_h2b2_e2e.py` | **1 FAIL** — `E5 geometry moved against the baseline: 480px wall {'x':0,'w':480,'h':2241} -> {…'h':2249}`, `wallContentBottom 3060 -> 3068` | **no** — the baseline is stale |

### Why the h2b1 reds are not this batch's

`E5` reads an *attribute*: it takes `a.sf-quote-cta` and looks at its `href`. A
stylesheet cannot reach an `href`. And the identical pair comes back when the
preflight copy is loaded with `4dc0906` — theme `2.10.77`, before a single byte
of this batch existed:

```
########## BEFORE (2.10.77) h2b1 ##########
   FAIL E5 detail hero href = None
   FAIL E5 the detail hero CTA did not land on /contact/ (/formulas/calming-soft-chews/)
E2E FAILURES: 2
```

### Why the h2b2 red is not this batch's

`E5` compares the candidate against `docs/batchH2b1-shots/geom-live-cand.json`,
a measurement taken **in the H2b1 batch**. As written it asserts that nothing has
moved geometry since H2b1 — which no later batch can satisfy. It also clicks
Accept first, and that removes `body.has-cookie-banner`, taking both of this
batch's rules out of the page before it measures anything.

So the real question is whether this batch moved the element. It did not.
Measured directly — both themes, both banner states, `section#formulas` on
`/products/soft-chews/` at 480px, four separate sessions:

| State | live (`2.10.77`) | preflight (`2.10.78`) |
|---|---|---|
| banner showing | `h = 2249` | `h = 2249` |
| after Accept | `h = 2249` | `h = 2249` |

Identical. The 2241 in the baseline is what H2b1 measured; the 8px since then
belongs to a batch that shipped between H2b1 and this one.

One caveat worth writing down rather than leaving in the harness: the same four
sessions also show `document.documentElement.scrollHeight` differing
(7,147 vs 7,919 after Accept). That number tracks lazy-loaded images, not
layout — it is the same instability this project already recorded for the chip
thumbnails — which is why the claim above is made on `section#formulas`' own
rect and repeated at four widths, not on the page height.

## 6. The pages this batch must not have touched

`tools/b3b2_noop_check.py`, four pages with neither the spec sheet nor the
configurator, live bytes against candidate bytes, **4/4 identical**:

| Page | live | candidate | masked equal |
|---|---|---|---|
| `/about/` | 124,341 B | 124,491 B | ✓ |
| `/quality/` | 162,197 B | 162,357 B | ✓ |
| `/contact/` | 138,644 B | 138,774 B | ✓ |
| `/zh/about/` | 130,765 B | 130,915 B | ✓ |

The raw counts differ by exactly 150 bytes on every page, which is the ten extra
characters of `-preflight` written fifteen times; three normalisations are
applied and each of them was *earned* by a failing run, not added up front:

1. the theme directory in an asset URL (by design — the candidate is served
   from its own directory),
2. the theme name in the body class (`wp-theme-sinofresh-theme` vs
   `…-preflight`; a distinct theme directory is what the preflight mechanism
   *is*),
3. Cloudflare's `email-protection` payload — the same address re-encoded under a
   fresh key on every response, so two fetches of one page differ in the
   ciphertext and nowhere else,
4. Gravity Forms' hidden-field token — a per-render nonce, present only on the
   two pages that carry a form, in the same place in both runs.

The check also asserts its own provenance on every row (`cand_is_preflight` and
`live_is_live`): with a silently-failed header both sides would be the live
theme, and "identical" would then be the most misleading pass available.

## 7. One thing the fix did not settle — needs a decision

Lifting the switcher past the banner moves it into the band the theme's own
float stack occupies, and that band is not the 44px column the ticket assumed.
At 375px the stack holds the WhatsApp button at **351px wide** (x 12–363,
y 474–522, z-index 9998), and the switcher lands on part of it:

| 375px | live | preflight |
|---|---|---|
| Manage Preferences | 7/11 | **11/11** ✓ |
| switcher opens | — | **yes** ✓ |
| WhatsApp button | 11/11 | **7/11** `######....#` |

So at 375px the WhatsApp button loses its right-hand third (the switcher is
z-index 99999 and stays on top), and keeps the left two thirds. Two things this
rules out, both of which the ticket proposed:

* `right: 80px` on the switcher would not help. The switcher would still sit at
  x 167–295, inside a button that spans 12–363; the overlap is in the vertical
  band, not the horizontal one.
* Raising the switcher is not free either: clearing the button upward needs
  roughly `bottom: 392px` at 375px, which puts the switcher near the middle of
  the viewport.

At 768 / 1024 / 1440 nothing regresses — the stack there is the 52px column the
ticket described, the two do not intersect (0 px²), and every visible button
reads the same before and after (`top` reads 0/11 on both sides at every width,
which is its own `opacity: 0; pointer-events: none` state until the page is
scrolled, not a regression).

Options, for the tick to pick:

* **A — accept.** Both controls remain usable; the cost is the right third of
  one button while the banner is unanswered, at phone width only.
* **B — lift the switcher clear of the stack** at ≤767px (`bottom: 392px`),
  trading a crowded mid-screen position for a fully clickable button.
* **C — make the stack yield instead**: at ≤767px with the banner up, lift the
  stack above the switcher rather than the switcher above the stack. One
  number moves, the WhatsApp button stays whole, and the switcher stays low.

## 8. Not in this batch

The sheet's nine labels are not in TranslatePress's string table, so the ZH page
still prints them in English. Deferred by instruction: this batch changes the
column width and nothing else.

## 9. How to reproduce

```
# §2 and §3 — geometry and hit-tests (needs the PIL interpreter)
python3 tools/b3b2_live_accept.py --json /tmp/b3b2-accept.json

# §6 — the pages this batch must not have touched
python3 tools/b3b2_noop_check.py

# §4 — no new red (see §0 for what "green" means in this gate)
python3 tools/b2d_h7_gate.py --batch h7c --source
python3 tools/b2d_h7_gate.py --batch h8c --source

# §5 — the browser pass. Pass --shots, or it writes into docs/batchH7c-shots/,
# which is the H7c record and not this batch's. Running it without --shots and
# then reverting those five frames is what happened here.
python3 tools/b2d_h7c_e2e.py --want-ver 2.10.78 --shots /tmp/h7c-e2e-shots
```

Frames: `docs/batch3b2-shots/` — 14 files, `a-cookie-<w>-<mode>.png` and
`b-specs-<page>-1440-<mode>.png`, none of them flat.
