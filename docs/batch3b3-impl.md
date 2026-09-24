# Batch 3b-3 — the language switcher's lift above the phone bottom bar

Theme commit `841c1eb` (2.10.79), tooling `274dc36`. Installed to the preflight
copy as `sinofresh-theme-preflight` (style.css md5
`cf3590a41c14b12c2f3e96339c440bfe`). **Live is still 2.10.78 at `fbec90b`** —
the pull is held back until the tick confirms, so everything below was measured
through the preflight header, never on the live theme.

---

## 0. What was decided, and what the decision rested on

The tick's first ruling was to hide `.sf-float-stack` at 375. The read-only scan
before it found that the "float stack" at that width is not a marketing widget
but the H7h bottom bar — the delivered full-width inquiry + WhatsApp bar with
its own E2E assertions — so hiding it would have been a retirement dressed as a
CSS tweak, with `body { padding-bottom: 78px }` left orphaned. That ruling was
withdrawn.

The second ruling was to lift the switcher instead, and to put the lift in the
`767` block. Measuring the counterfactual moved the placement: **one `bottom`
value cannot serve the two layouts that block spans.**

| The stack at | what it is | height | the lift that clears it |
|---|---|---|---|
| ≤ 480 | the full-width bar, `left:0; right:0` | 69px | 345px is the 8px floor |
| 481–767 | still the circle column, `right:16px` | 156px (3×44 + 2×12) | 432px, i.e. the whole column |

At 481 the switcher rides at `--right:10vw` and laps the column's left edge by
12px, so a 350 lift puts its band (y 495–550 at 900 tall) across the WhatsApp
button's own centre line (y 498) — 3 of that button's 11 sample points. The
scan measured 8/11 there against 11/11 today. **481–500 is clean now and should
not pay for a 375 problem**, so the value went into the `480` block, beside the
268 the bar itself carries, and the `767` block kept its 280.

The tick accepted that: "断点应与它补偿的布局同域；481–500 本就干净，不该为 375
付代价。我上一轮『只改 767 块』的约束前提（375 命中 767 块）被你推翻，约束作废。"

## 1. The change

One declaration, plus the version bump three files needed.

| # | file | where | change |
|---|---|---|---|
| A | `sinofresh-theme/style.css` | L9854, inside `@media (max-width: 480px)` (block opens L9628), directly after `body.has-cookie-banner .sf-float-stack { bottom: 268px }` | `body.has-cookie-banner .trp-floating-switcher { bottom: 350px }` |
| — | `sinofresh-theme/style.css` | L5 | `Version: 2.10.79` |
| — | `sinofresh-theme/functions.php` | L31 | enqueue `2.10.79` |

**Untouched, deliberately:** the `767` block's `bottom: 280px` (L3998), the
global `bottom: 88px` (L3948), every `sf-float-stack` rule, the bar, the H7h
block's `padding-bottom`, and the plugin's own `--bottom` variable. The
declaration wins on specificity — `body.has-cookie-banner .trp-floating-switcher`
is 0,2,1 against the plugin's 0,1,0 — so no `!important` and no fighting over
the plugin's inline variable. `350px` occurs exactly twice in the file: once in
prose at L5860, once in this rule.

Static checks: braces 1558/1558 balanced (the pre-rule count was 1557); the new
rule's enclosing block resolves to the one opening at L9628 and nothing else;
`php -l` clean; no `2.10.78` left anywhere except the two lines that must name
it (see §8).

## 2. 375 — the target

Every session asserts which theme it served and which viewport it got before it
measures. Live row = 2.10.78, candidate row = 2.10.79, same page, banner up,
fresh visitor each.

| | live 2.10.78 | candidate 2.10.79 |
|---|---|---|
| switcher computed `bottom` | 280px | **350px** |
| switcher rect | y 565–620 | y 495–550 |
| bar (the stack) rect | y 563–632, h 69 | y 563–632, h 69 |
| horizontal overlap | 128px | 128px |
| **clear air: bar top − switcher bottom** | **−57px** | **+13px** |
| Manage Preferences, 11 points along its width | 11/11 | 11/11 |
| **WhatsApp button (351px wide), 11 points** | **7/11** `######....#` | **11/11** `###########` |
| switcher clickable | — | `ok=true`, `aria-expanded=true`, list shown, `links=['/zh/']` |
| switcher bottom edge to the banner's top (y 634) | 14px | 84px |

The asked-for floor was ≥ 8px and the delivered air is 13px. The −57 is the
defect this batch exists for, and it is the same one batch 3b-2 flagged in §7 of
its record and left for a ruling: **the switcher was sitting on the bar's own
WhatsApp button**, which held 7 of its 11 points. That is now 11/11. Manage
Preferences, which 3b-2 already raised to 11/11, is unaffected.

Neither control is sacrificed: the switcher still opens and still lists `/zh/`
from the phone width.

## 3. 481–600 — the band above the breakpoint, held as a negative control

This is the part of the ruling that has to be *proved* rather than asserted,
because the value that would have broken it is the one that was rejected.

| width | band | stack height | live `swBottom` | candidate `swBottom` | live vs candidate | WhatsApp |
|---|---|---|---|---|---|---|
| 481 | column | 156px | 280px | 280px | **identical** | 11/11 both |
| 500 | column | 156px | 280px | 280px | **identical** | 11/11 both |
| 600 | column | 156px | 280px | 280px | **identical** | 11/11 both |

Identical on every judged field, not just the version: computed bottom, both
rects, horizontal overlap, vertical gap, and the Manage hit count. Horizontal
overlap is 12px at 481 and 10px at 500, falling to 0 at 600 as predicted — the
column and the switcher do share the band, which is exactly why the lift had to
not be sent there.

## 4. 768 / 1024 / 1440 — desktop and tablet regression

| width | live `swBottom` | candidate `swBottom` | live vs candidate | WhatsApp / email |
|---|---|---|---|---|
| 768 | 88px | 88px | **identical** | 11/11 both |
| 1024 | 88px | 88px | **identical** | 11/11 both |
| 1440 | 88px | 88px | **identical** | 11/11 both |

`.sf-float-btn--top` reads 0/11 at every width in both themes: the back-to-top
button is not painted until the page has been scrolled, and neither pass scrolled
it. Pre-existing, unchanged, and not a finding about this batch.

Frames: `docs/batch3b3-shots/` — 14 files, `b3b3-<width>-<mode>.png`, all
non-flat (23,497–60,300 distinct colours).

## 5. Gates — no new red

`b2d_h7_gate.py --batch <b> --source`, the same command as the 3b-2 record:

| batch | before | after | assertion this batch could have moved |
|---|---|---|---|
| `h7c` | 5 FAIL | **5 FAIL** | `a row is a label/value grid` — `ok x1` before, `ok x1` after |
| `h8c` | 2 FAIL | **2 FAIL** | — |

The five h7c reds are `Shelf Life is the parsed shelf segment`, `Place of Origin
is a constant until H7e`, `OEM / ODM is a constant until H7e`, `the style token
is bumped in the enqueue`, `style.css declares 2.10.64`; the two h8c reds are
`style.css declares 2.10.76` and `functions.php enqueues 2.10.76 for style.css`.
Every one is a claim about a version or a behaviour a later batch replaced, every
one was equally red before this batch, and the gate's own comment at
`b2d_h7_gate.py:194-199` says `--source` is each batch's self-portrait and these
version claims go red by design as soon as a later batch bumps. So the judgement
is **not "all green" but "no new red"**, and the historical assertions were left
alone rather than "fixed".

Structurally this batch could not have tripped the gate: `trp-|switcher` has
**0** matches in the gate, `268|280px|78px` has **0**, and the h7h assertion that
binds source (`:3044`, "the bottom bar rule is in the phone block", requiring
`left: 0;` to stay the first declaration) anchors `sf-float-stack`, which this
batch does not touch.

## 6. E2E

| tool | command | result |
|---|---|---|
| `b2d_h7c_e2e.py` | `--want-ver 2.10.79 --shots /tmp/b3b3-h7c-shots` | **PASS**. Two 568px tracks with the 64px gutter at 1440, one 380px at 420, both locales, 10 rows, labels identical EN/ZH, placement anchors in order. Every step re-asserts `sinofresh-theme-preflight/style.css?ver=2.10.79` |
| `b2d_h2b1_e2e.py` | `--out /tmp/b3b3-h2b1.json` | **2 FAIL** — `E5 detail hero href = None`, `E5 the detail hero CTA did not land on /contact/`. **The same two as the recorded baseline** |
| `b2d_h2b2_e2e.py` | `--out /tmp/b3b3-h2b2.json` | **1 FAIL** — `E5 geometry moved against the baseline: 480px wall 2241 -> 2249`. **The same one as the recorded baseline** |

`--shots` was passed explicitly: this harness's default output directory is
`docs/batchH7c-shots/`, the H7c record, and running it without the flag rewrites
five historical frames. It was passed, and `git status docs/batchH7c-shots/` is
empty afterwards.

**Two things worth recording rather than smoothing over.**

*The first h2b2 run died mid-E4* with `FATAL open: ✗ Operation timed out`, after
E1, E2, E3 and one line of E4 — and wrote no JSON. An absent output is not a
pass; it was re-run, and the re-run completed. (Its first line is worth having
anyway: at 480px the computed bottoms are `float=268px lang=350px`, i.e. the new
rule is in effect and the bar's own 268 is untouched.)

*The E5 red was proved out, not argued away.* E5 compares 34 fields at six widths
against `docs/batchH2b1-shots/geom-live-cand.json`, an archive the **H2b1** batch
wrote; 2241 was the value then. E5 also clicks the banner's Accept button first,
which removes `body.has-cookie-banner` — the exact class this batch's rule is
scoped to. Rather than rest on that reasoning, the state was measured directly at
480px on `section#formulas`, the object E5 compares:

| 480px, `/products/soft-chews/` | live 2.10.78 | candidate 2.10.79 |
|---|---|---|
| banner **up**: switcher `bottom` | 280px | **350px** ← the rule is live here |
| banner **accepted** (= E5's state): switcher `bottom` | 0px | 0px |
| banner **accepted**: `section#formulas` height | **2249** | **2249** |
| banner **accepted**: `wallContentBottom` | 3116 | 3116 |

So in E5's own state the two themes are identical, the rule is provably inert
(the switcher falls back to the plugin's own 0px on both sides), and live itself
reports 2249 — the archive's 2241 is stale. **Not this batch.** This also
confirms the placement a second way: with the banner up the new value takes
effect at 480.

## 7. No side effects

`b3b2_noop_check.py --label "batch 3b-3"`, live vs candidate, four pages that
render neither the spec sheet nor the switcher-over-banner pair:

| page | live bytes | cand bytes | masked equal | provenance |
|---|---|---|---|---|
| `/about/` | 124,341 | 124,491 | yes | candidate is preflight, live is live |
| `/quality/` | 162,197 | 162,357 | yes | candidate is preflight, live is live |
| `/contact/` | 138,644 | 138,774 | yes | candidate is preflight, live is live |
| `/zh/about/` | 130,765 | 130,915 | yes | candidate is preflight, live is live |

**4/4.** After masking, each pair is byte-identical, so the raw delta is entirely
the ten characters of `-preflight` written once per theme-directory occurrence
(13–16 per page, hence 130–160 bytes). The provenance columns are asserted on
both sides: if the header had silently failed, both sides would be the live
theme and "identical" would be the most misleading possible pass.

Four normalisations are folded, all of them earned by a failing run rather than
added up front: the theme directory name in asset URLs, the
`wp-theme-…-preflight` body class, Cloudflare's per-response
`email-protection` key, and Gravity Forms' per-render `gform_hidden` nonce.
`?ver=` is folded too.

## 8. The version literals — synced here, hoisted out of here

The bump to 2.10.79 reached **nine lines in six harnesses**, because several of
them pin the version they expect as a literal instead of taking it as an
argument:

`b2d_h8c_live_accept.py:46`, `b3bc_live_accept.py:47` (+ doc `:15`),
`b3bc_shots.py:264/276`, `b3bc_local_check.py:258–265` (whose `:262–263` reach
back and assert the literals carried by `b2d_h8c_live_check.py` and
`b2d_h8c_live_accept.py` — the three move together or the checker reports a green
tree against a dead harness), `b2d_h8c_live_check.py:201`, and
`b3bc_preflight_check.py:182` (+ doc `:11`) which the ticket's list had missed.

Two things this record adds to that list:

- `b3bc_preflight_check.py:183–184` needed **2.10.78**, not 2.10.79. Its claim is
  not "the candidate is X" but "live is the OLD one and the pull is still held
  back" — and after this batch's pull, 2.10.78 is what "held back" means.
- `b3bc_shots.py`'s docstring and `b3b2_live_accept.py`'s both named the version
  they would photograph if the preflight header quietly failed. The version added
  nothing to the warning and guaranteed the prose would go stale, so it is gone.

`b3bc_local_check.py:176/177` still says 2.10.77 and **should**: it is the batch
3b snapshot, not a live harness.

⚠️ **This is the same disease the h7h E2E died of.** `b2d_h7h_e2e.py:75` pins
`ver=2.10.69`, which is why it can no longer run — and therefore why nothing in
the current live routine gate guards the 375 bottom bar at all. Both are the same
root cause: a version pinned as a tool-side literal. **Standing recommendation,
not implemented here:** make `--expect-ver` required, or read the version from
`functions.php`, and bring h7h back into the routine. Raised as its own project;
a layout batch is the wrong place to re-architect the harnesses.

## 9. How to reproduce

```
# §2–§4 — geometry, hit-tests and the band above the breakpoint
# (needs the PIL interpreter; --shots defaults to the batch evidence dir)
python3 tools/b3b3_live_accept.py --json /tmp/b3b3-accept.json

# §7 — the pages this batch must not have touched
python3 tools/b3b2_noop_check.py --label "batch 3b-3"

# §5 — no new red (see §0 of the 3b-2 record, and §5 here, for what "green" means)
python3 tools/b2d_h7_gate.py --batch h7c --source
python3 tools/b2d_h7_gate.py --batch h8c --source

# §6 — the browser passes. --shots is NOT optional on the h7c one: its default
# directory is docs/batchH7c-shots/, the H7c record, and omitting the flag
# rewrites five historical frames.
python3 tools/b2d_h7c_e2e.py --want-ver 2.10.79 --shots /tmp/b3b3-h7c-shots
python3 tools/b2d_h2b1_e2e.py --out /tmp/b3b3-h2b1.json
python3 tools/b2d_h2b2_e2e.py --out /tmp/b3b3-h2b2.json
```

The preflight copy must be installed at `841c1eb` first
(`python3 tools/b2d_s1_preflight.py install 841c1eb0672a232f905ccd4ea3bdcf315ed8bb4f`),
and both `b3b3_live_accept.py` and `b2d_h2b2_e2e.py` go fatal if the theme or the
viewport the session asked for is not the one it got — a run that cannot prove
which bytes it measured produces no result rather than a plausible one.
