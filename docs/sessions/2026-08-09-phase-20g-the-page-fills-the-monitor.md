# 2026-08-09 — Phase 20g: the page fills the monitor it was written for

Evidence — `make measure-page`, before and after, in
`docs/sessions/2026-08-09-phase-20g-the-page-fills-the-monitor-measure.log`.
Cost: nothing. No cycle, no AWS call, nothing applied. `site/` changes, so the
next push republishes the static page.

The cursor's next allowed step was **the desktop, then a live cycle, in that
order and as two sessions**. It also said, in the same breath, that finding B is
not the list and the list has to be produced by looking. So this session
produced it, and then fixed the part of it that is a width rather than a packing.

## The list, produced by looking

Baseline first, on the committed instrument, in this sandbox: every figure
identical to the ones 20e recorded on the devbox — 1878px at 2560 in flight,
169.13px of history table past its parent at 390, `WWW` 31px in a 20px box. The
instrument replicated, so the numbers under it can be trusted.

Then screenshots at 2560, 1920 and 1440, and a probe that asked the page for the
things a screenshot shows but does not count.

```text
1  badges          text glyphs wider than their badge, EVERY viewport
                   WWW +11px, TEST +6px x7, YOU +2px, DEL          <- finding B
2  broken words    environme|nt at 2560, Secrets Mana|ger,
                   RDS PostgreSQ|L at 1440
3  the comb        2560: one row of 10 columns, tallest phase 513px,
                   air under the other seven summing to 1582px
                   1440: two rows, 960px
4  the ragged top  p-env 573px, p-arch 279px, p-run 235px at 2560
                   -> 294px and 338px of empty column beside the tallest
5  dangling sep    'docker ·' at a line end, 'terraform ·' / 'alembic'
6  the width       vw 2560, main 1536px. 1024px of margin on the stated
                   primary target - and main is ALSO 1536px at 1920
```

Items 1, 2, 5 and 6 are fixed here. Items 3 and 4 are a packing decision and
were deliberately left to their own session — decided in the chat, before the
work started, so that this session had a stated scope rather than a drifting one.

## What 6 turned out to be, and why 2 and 5 came with it

`main: 96rem` is ADR-0049 D1, and its reason is explicit: it is what the map's
computed column count needs at the legibility floor. Nothing else asked for a
number, so a FLOOR became the whole page's CEILING — and the page stops at
1536px whether the monitor is 1920 or 2560.

Ten columns inside 1536px are about 147px each. `overflow-wrap: break-word` only
fires when a word cannot fit at all, so `environme|nt` is not a typography
choice: it is the layout reporting that the column is narrower than the text
given to it. Same for the hop card that wrapped `docker · terraform` after its
separator. Widening the page fixed both without either being touched.

**ADR-0050 D1**: `main` goes to 120rem — 1920px. The page fills a 1920 screen
and keeps a margin on a 2560 one. Still no `100vw` anywhere, for ADR-0049 D1's
reason.

```text
in-flight, cuts closed      before    after
2560x1440                   1878px    1760px     1.3 -> 1.2 screens
1920x1080                   1878px    1790px     and now the full width
1440x900                    2190px    2190px     never was at the cap
```

## The badge grows rather than clips

`.icon` was a fixed 1.4rem box with `display: grid; place-items: center`, which
centres an oversized word and draws it straight through the border. `.icon.aws`
sets `overflow: hidden` and so never showed it; the text badge has no clip and
nothing in this repository could have seen it before the instrument existed.

Copying `overflow: hidden` across would have been the wrong repair — it hides a
WORD, and the word is the content. So `width: fit-content` with
`min-width: 1.4rem` keeps the square for a single glyph and lets `WWW` and
`TEST` size to themselves. The AWS mark keeps its exact square: it carries an
unmodified Architecture Icon, and a mark that changes size is a different mark
(**ADR-0050 D2**).

## A fix that was tried, measured and reverted

At 1440 the request path gets 5 of 12 columns — about 100px a hop — which is
where `RDS PostgreSQ|L` comes from. Moving the `.p-arch` breakpoint from 1100 to
1500 gives the path the whole row and fixes it.

It cost 290px of height: 2123 -> 2412 at rest, 2190 -> 2480 in flight. 2.4
screens becomes 2.7, on a page whose entire phase is "composed, not scrolled".
Reverted, and **the figure is written into the stylesheet beside the rule**, so
the next session does not spend the same twenty minutes discovering it
(**ADR-0050 D3**). 1440 keeps its word break, and it is on the open list.

## Validation

```bash
make measure-page
make site-page-check site-data-check docs-check
make contrast-check
```

All green. `site-data` was regenerated because the identity bar counts the
decision records from `topology.json` and ADR-0050 makes it 51 — the same trap
that produced commit `9c54577` a day earlier, caught this time before the gate
had to say so.

No break test: nothing here is a gate. The evidence is the before/after pair
from an instrument that was itself broken on purpose in 20e.

## What is left, and in what order

```text
- the comb, and the ragged top row. Items 3 and 4 above, both measured, both a
  packing decision. 1440's word break belongs to that session too - the row it
  lives in is the row being repacked.
- then a live cycle. BILLABLE, planned and confirmed before anything runs. The
  wired cost fold has never run live, so the teardown of either environment is
  the line to watch; and it is the first cycle since the composition landed, so
  the page will be seen doing its job for the first time.
- the phone stays deferred far, out of the near plan, per the scope answer given
  on 2026-08-09. It got 23px taller here (4818 -> 4841 in flight) because the
  badges grew, and it is 5.7 screens either way.
```
