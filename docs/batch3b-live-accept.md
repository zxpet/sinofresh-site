# Batch 3b — the live acceptance

The pull itself, and the three things it was asked for, measured on the bytes
dev serves with no request header. Run Thursday 24 September 2026.

## 1. The pull

| | |
|---|---|
| dev before | `c5eb2ab` (H8c 2/2), theme `2.10.76` |
| dev after | `95cac91` (batch 3b close-out 2/2), theme `2.10.77` |
| range | fast-forward, 4 commits, 46 files, +4712 −65 |
| working tree before | clean (`git status --short` empty) |
| working tree after | `## main...origin/main`, nothing behind |
| live theme | `/var/www/dev.zxpet.com/public/wp-content/themes/sinofresh-theme` is a symlink into `/var/www/dev.zxpet.com/site-repo/sinofresh-theme`, whose `style.css:5` reads `Version: 2.10.77` |

The production site was not touched, and the preflight copy was not re-installed:
its bytes already match what the pull put on live, which is what made the
pull-then-accept pair a comparison rather than a retype.

## 2. The three checks

### 2.1 The flavour group, EN and ZH

Post 158's page, `/formulas/joint-support-soft-chews/` (149,296 bytes) and its
Chinese path `/zh/formulas/joint-support-soft-chews/` (159,101 bytes). Both are
served from `sinofresh-theme` at `2.10.77`.

| | EN | ZH |
|---|---|---|
| chips | 8 | 8 |
| chips that say Custom | 1 | 1 |
| chips carrying `data-sf-config-custom="1"` | 1, and it is the Custom | 1, and it is the Custom |
| `data-sf-config-custom-input` on the group | 1 | 1 |
| order | Chicken, Beef, Lamb, Salmon, Peanut Butter, Cheese, Mint, Custom | same |
| group markup | 2,970 bytes | 2,970 bytes, **byte-identical to EN** |

Clicked with a real mouse at (1212, 450), both locales returned the same
reading: `checkedRadio: "Custom"`, the eighth chip carrying `is-on`,
`boxHidden: false`, `boxVisible: true`, `boxDisplay: "block"`, and the text
input holding focus. Nine chips with two of them called Custom is what the page
served before this batch; the dead chip that checked the radio and opened
nothing is gone with it.

### 2.2 `/quality/` at 1440

| | 1440 | 1024 |
|---|---|---|
| `.sf-qs` height | **861px** (was 1800px) | 865px |
| grid tracks | `319.328px 319.328px 319.344px` | three-up |
| rows, by the steps' own top edges | [3, 3] | [3, 3] |
| horizontal overflow | none (`scrollWidth` 1440) | none (`scrollWidth` 1024) |

Six `<article class="sf-qs__step">` on the page, the numbers read
`01 02 03 04 05 06`, six photos and six numbers, the photo is still 1.333
(4:3), and the number is still 64px in `rgb(90, 183, 53)`. The rows are grouped
by each step's rounded top edge (±4px) rather than by counting class names,
because "three to a row" is a geometry the stylesheet can fail in ways a class
list cannot describe — three tracks with the steps stacked inside one of them
would pass a count of class names.

### 2.3 The version

- The homepage, `/quality/` and both flavour pages link
  `themes/sinofresh-theme/style.css?ver=2.10.77`.
- All **75** pages of the catalogue serve, and every one of them links the
  theme at `2.10.77`; there is no 404 and no second token.
- Every `?ver=` value seen across the sweep, each one on all 75 pages:
  `7.1.2`, `2.10.77`, `3.3.6`, `efaa5193bbad9c60ffd1`, `1bf28ded04f9f188bdcb`,
  `1.0.0`, `1.1.0`, `14.16.14`. None of them matches this theme's own `2.10.x`
  namespace other than `2.10.77`, so no page cached a link to last week's CSS.
- The footer's own markup carries no asset token at all.

## 3. The gate, re-run on the pulled install

`tools/b2d_h8c_live_check.py --label live-after-b3b` reads the same install
without a header: **23/23 PASS**. That is the regression half of this report —
the H8a/H8b/H8c work that has only ever been served from the preflight layer is
now on live and still verified there: the sticky media rule and the element it
applies to, the phone fold rules plus the `config.js` enqueue, the thumbnail
strip as a scroll box, the Flavor group as one answer plus a box, the shelf-life
row printing the record's 24 months over a specs text that still says 18 six
times, the dosage-form pools, Container Type as a packaging format, the four
`/services/` subpages with their breadcrumbs and FAQ schema, the overview's four
linked cards, and the two batch-3b bands.

## 4. The frames

`docs/batch3b-live-accept-shots/`, six frames, none flat.

| frame | size |
|---|---|
| `la-quality-3up-1440.png` | 1440×897 |
| `la-quality-3up-1024.png` | 1024×865 |
| `la-flavor-en-1440.png` | 1440×143 |
| `la-flavor-en-custom-open-1440.png` | 1440×278 |
| `la-flavor-zh-1440.png` | 1440×143 |
| `la-flavor-zh-custom-open-1440.png` | 1440×278 |

## 5. Three things stated rather than papered over

1. **The frames are not evidence that EN and ZH agree.** The two locales'
   default-state captures differ in pixels, and chasing it down showed why: the
   differing region moves with the moment of capture (82×15px on one pair,
   690×143px on a deliberate re-shoot after `document.fonts.ready`), which is
   the signature of the chip thumbnails' lazy load, not of content. The
   open-state pair came back md5-identical (`39c126f0…`). The claim that the two
   locales render the same group rests on the served bytes — the two groups are
   byte-identical, 2,970 bytes each — and on the click readings matching field
   for field. The frames are for the eye.
2. **The flavour group renders on one page in the whole catalogue**, post 158,
   and its Chinese path is the same page. The species and stage groups render on
   none, because no record carries their meta; those two call sites are covered
   by `tools/b3bc_flavor_unit.php` and the static check that all five call
   sites route through the helper.
3. **The preflight copy is still on the box**, `themes/sinofresh-theme-preflight`,
   byte-identical to live now. Whether it is kept or deleted is a separate
   decision and nothing here depends on it.

## 6. Re-running

```
/Users/meng/.workbuddy/binaries/python/envs/default/bin/python \
    tools/b3bc_live_accept.py --json /tmp/b3bc-live-accept.json
/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
    tools/b2d_h8c_live_check.py --label live-after-b3b
```

`b3bc_live_accept.py` is the live twin of `b3bc_preflight_check.py`: same
selectors, same reading of the chip labels off the radio values, but with no
request header at all, plus the browser half (the 861px measurement, the
row grouping, and the real-mouse click) and the 75-page token sweep. It exits
non-zero on the first failed assertion, so a scheduled run is a usable gate.

**Result: 44 checks, 0 failed; 6 frames, 0 flat; gate 23/23.**
