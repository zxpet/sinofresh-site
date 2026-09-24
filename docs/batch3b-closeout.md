# Batch 3b close-out — deploy record

Commit `fcc7bdc`, installed to the preflight copy the same day. Live is still
`2.10.76` at `c5eb2ab`: the pull is held back until the tick confirms, so
nothing below was measured on the live theme.

Three items the batch-3b scan opened and the tick settled. All three land in
one changeset and ship as one pull.

## 1. What shipped

| # | Item | File | Change |
|---|---|---|---|
| 1 | C1 rewritten as the development path | `templates/page-services.html` | 4 `<li>` replaced; lead-in rewritten. Heading and both buttons stand |
| 2 | Quality band → three-up card grid | `style.css` (`.sf-qs`, ~L4963) | Pure CSS: the band becomes the grid, each step a flex `column-reverse`. Template untouched |
| 3 | One Custom chip per record group | `functions.php` | New `sf_formula_options_with_custom()`; all five record-driven groups route through it |

### 1a — C1

The four lines the batch-3b commit put in the band were byte-identical to What
We Handle's R&D & Formulation column one band above, so the band repeated the
page. They are now the four stages a custom recipe moves through:

- Brief & reference match
- Prototype & sample round
- Palatability & stability trials
- Scale-up & packaging validation

The framing is deliberately lab-side. The very next band is "How We Work — From
Inquiry to Delivery in 5 Steps" (the commercial path, numbered 01–05), so C1
names itself as stages *of formulation development* and stays an unnumbered
checklist: two step-lists in a row would read as one duplicated. No process
page exists to collide with — `how-we-work`, `process` and `our-process` are
all 404 — and none of the four phrases appears anywhere else in the repository
(the dosage-form pages' How We Work runs Inquiry → Requirement Confirmation →
Quotation & Sampling → Contract & Payment → Production & QC → Shipping &
Delivery → After-Sales & Reorder, a different list in a different voice).

The second button still reads "Palatability testing → /quality/". It is kept
on purpose: it names where the reader goes, not what the stage is called.

### 1b — Quality

Measured on the dev site before the change: 1800px, one step per row, photo
track 350px against a 620px copy track. After: **861px at 1440 and 1280**,
828px at 1024, 2344px at 375 — a 52% cut at desktop, exactly the number the
injected simulation predicted, now produced by the shipped stylesheet.

| viewport | before | after | per row | photo box | number |
|---|---|---|---|---|---|
| 1440 | 1800px | **861px** | 1 → 3 | 350×263 → 319×239 | 64px `#5AB735` |
| 1280 | 1800px | **861px** | 1 → 3 | 319×239 | 64px |
| 1024 | 1800px | **828px** | 1 → 3 | 297×223 | 64px |
| 375 | 2489px | **2344px** | 1 | 299×224 | 44px |

What was deliberately NOT done: no card frame. The photos already carry this
page's image language (8px radius, soft shadow — the same one `.sf-eq` uses),
so the six cards stand on the band's own background, and a white box with
padding would have cost ~80px of the 939px the change saves. The zigzag's
row hairlines and their 22px lead-in go with the layout: the 01–06 numbers
carry the sequence now.

The variant that puts the number ON the photo (705px) was measured and
dropped by the tick — readability of white-on-photo text is not controllable
enough to ship.

### 1c — the Custom chip

post 158's flavour meta carries "Custom" as its eighth entry, and the renderer
appended a second one on top: nine chips, two saying Custom, and the record's
own chip (unmarked) checked the radio and opened nothing. It also stole the
marked chip's tick, so the only answer it could send the sales desk was the
bare word "Custom" with no flavour in it.

The five record-driven groups (flavor, weight, pack, species, stage) now build
their lists through `sf_formula_options_with_custom()`, which marks the
record's own entry instead of appending — the rule
`sf_formula_library_options()` has always followed for the pool-driven shape
and container groups, and the one the H1 note spells out. A record that does
not spell Custom is untouched: the helper appends, exactly as before.

No record data was touched (the tick's constraint).

## 2. Verification

Four layers, each covering what the layer below cannot see.

| layer | tool | result |
|---|---|---|
| static, working tree | `tools/b3bc_local_check.py` | **54/54** |
| the shipped helper, run | `tools/b3bc_flavor_unit.php` | **9/9** |
| served bytes, preflight copy | `tools/b3bc_preflight_check.py` | **35/35** |
| rendered geometry | `tools/b3b_qs_measure.py --preflight` | table above |
| frames | `tools/b3bc_shots.py` | 10 frames, 0 flat |

The unit harness deserves a note: it lifts the two functions out of
`functions.php` and evals that slice, so what it runs is the shipped source
rather than a retyped copy — a retyped helper passes while the theme keeps the
bug. It runs post 158's real flavour array through it (eight options, exactly
one owner for the text box) plus the append path, the lowercase path, the
single-value path and the empty list.

The served-byte check is the one that closes the loop, because it compares the
candidate (2.10.77) against live (2.10.76) over the same host:

- post 158 draws **eight** chips, one Custom, one owner of the box, and the
  box is the one that says Custom. `weight` and `pack` on the same record each
  keep their one Custom.
- **the no-op control**: the `weight` group on three records and the `pack`
  group on two are byte-identical between live and the candidate. Those groups
  are driven by the same helper this batch rewrote, so a byte difference there
  would have been a regression; there is none.
- the sweep: all 21 formula pages, all **32 rendered record groups**, each
  draws exactly one Custom with the box on it.
- the overview serves the four stages and no longer the old four, still eight
  headings in order.

### What the served layer could not cover, stated rather than papered over

- The **flavour group renders on one page in the whole catalogue** (post 158).
  The other twenty records carry no `sf_formula_flavors` meta at all, so there
  is no second flavour group to compare against. The no-op control therefore
  runs on weight and pack, which do cover the catalogue.
- The **species and stage groups render on no page**: no record carries
  `sf_formula_species` or `sf_formula_lifestage`. Those two call sites cannot
  be exercised from the served layer at all. They are covered by the unit
  harness (which runs the helper they share) and by the static check that all
  five call sites route through it. If a record ever gains that meta, the
  sweep will pick the group up automatically.

## 3. Frames

`docs/batch3b-closeout-shots/`, all from the preflight copy, each asserting
which copy answered before it shot:

| frame | shows |
|---|---|
| `bc-quality-3up-{1440,1280,1024}` | the six steps in two rows of three |
| `bc-quality-1col-375` | the phone stack |
| `bc-services-c1-1440` | the four development stages and both buttons |
| `bc-footer-{1440,1280,1024}` | the five-column footer (batch 3b's D1 check) |
| `bc-158-flavor-1440` | eight chips, one Custom |
| `bc-158-flavor-custom-open-1440` | the Custom chip selected, box revealed |

The footer frames close batch 3b's D1 item, which until now was arithmetic:
at 1440 every label sits on one line; at 1024 "ODM Custom Formulation" and
"Contract Manufacturing" wrap to two lines and stay readable.

## 4. Observations, not defects

- The flavour group's frame is partly overlapped by the TranslatePress
  language switcher, a floating element of the same family as the known
  "phone fixed layers cover the card foot" issue. Not introduced here.
- The C1 checklist is left-aligned under a centred heading and lead-in. That
  is the form batch 3b shipped and the tick asked to keep; flagging it only
  because the band is now shorter and the imbalance is easier to see.
- `tools/b3b_local_check.py` (batch 3b's own checker) asserted the old four
  items and would have gone red on the new tree; it now asserts the stages,
  with a comment saying why a batch-3b checker asserts close-out copy.
  34/34 after the update.

## 5. State at the end of the batch

| layer | version | commit |
|---|---|---|
| working tree | 2.10.77 | `fcc7bdc` |
| preflight copy on dev | 2.10.77 | `fcc7bdc` |
| dev live | **2.10.76** | `c5eb2ab` |
| production | untouched | — |

`origin/main == fcc7bdc`, nothing unpushed, tree clean. The pull to dev live
is the one step left, and it waits for the tick.
