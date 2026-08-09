# 2026-08-09 — Phase 20j: the floor the map was folded at

Evidence — `make measure-page`, before and after, in
`docs/sessions/2026-08-09-phase-20j-packing-measure.log`.
Cost: nothing. No cycle, no AWS call, nothing applied. `site/` changes, so the
next push republishes the static page. **ADR-0052.**

The cursor's next allowed step was **20g's packing, then a live cycle**, and it
named what packing meant: the comb, the ragged top row, 1440's word break, and
the +67px the phone gained in 20i while the desktop gained nothing. All four are
here. None of them needed a cycle.

## The list was produced by looking, and then by asking

Screenshots at 2560, 1920 and 1440, both fixtures, and a throwaway probe that
asked the page for the things a screenshot shows and does not count. What came
back was the comb and the ragged row as expected — and a third thing, which is
what this session turned out to be about.

```text
the comb        map 495.03px in one row of ten, 1432.28px of air under seven
                phases at 1920; the shortest is 204.58px against a row of 495
the ragged row  465 / 228 / 235px: one panel decides the row's height, the
                other two end less than half way down it
a broken word   `environme|nt` on the phone, in the published page, since the
                composition landed. Nobody had reported it and no instrument
                here could: measure-page reports OVERFLOW, and a broken word
                is not overflow.
```

## A broken word is measurable

A `Range` over one word returns one client rect when the word sits on a line and
two when the line box split it. That is the whole mechanism, and it turns
`environme|nt` from something a person noticed into a number an instrument
reports. Fields that break long identifiers deliberately say so in CSS
(`overflow-wrap: anywhere`, which is inherited), so they are not asked.

Run against the page as it stood, with no hint about where to look, it reported
both of the breaks this project knows about: `RDS PostgreSQ|L` at 1440, which 20g
found by eye, and `environment` on the phone, which nobody had.

## The floor was a claim about the wrong thing

`--node-min` decides how many columns the map folds into (ADR-0039 D5). It has
been `12rem`, then `7rem` in 20e.1 — and both numbers were measured against what
a node CONTAINS. Neither was measured against what it has to DRAW, which is the
question the fold actually asks it.

With the same Range both answers are derivable, and both are printed now:

```text
every word whole      143.69px   the widest is "environment", 89.63px
every name unwrapped  295.58px
--node-min was            7rem = 112px
```

**18.5rem** — the second number, rounded up to the next half rem. A node draws
its name rather than enough of it to be guessed at. `143.69px` is not the floor
and is kept as the line beneath which no future number may go: below it the map
is drawing something a reader cannot read.

The map folds to five columns in two rows at 1920 and 2560, four in three rows
at 1440, and one column on a phone. What it costs, same fixtures either side,
cuts closed:

```text
at-rest        2560    1920    1440     390        in-flight   2560    1920
before         1734    1742    2123    4842        before      1760    1790
after          2039    2039    2346    5472        after       2051    2051
```

About 300px on the desktop — 1.2 screens becoming 1.4 on the stated primary
target — and 630px on the phone, which is the one viewport where this is not a
preference: two columns were breaking a word and one column is not.

One honesty note on the number itself. Measured on a page whose names are
wrapped, the sum of a name's line boxes reads 286.92–295.58px depending on where
the wrap falls; measured after the fold, with every name on one line, it is
295.58px exactly. The decision took the second reading, which is the only one
that is a width rather than an estimate of one.

## The top row was never three of anything

465 against 228 + 235 + a gap is 465 against 475, so the panels are two columns
now: the environments panel down the left over both rows, the path and the run
stacked to its right, `4 / 8 / 8` with `stretch`, source order untouched.

It also settled a fix 20g reverted. The five hops had 5/12 of the row — about
100px each at 1440, which is where `RDS PostgreSQL` broke — and 20g's breakpoint
at 1500 fixed that for 290px of height, so it was reverted with its figure. At
8/12 the hops have 184px at 1440, nothing breaks, and the row is 69px SHORTER
than the three-column one it replaces. The fix was always width. It came from
packing rather than from a breakpoint.

## The comb: two rows take a third of it, and the rest is structural

Nothing was packed by hand. At the new floor the map is two rows of five at 1920
and three rows of four at 1440, and the air under the phases falls on its own:

```text
1920, at-rest, cuts closed     air 1432.28px  ->  967.85px
1440                           air  909.65px  ->  694.72px
```

A wider column costs the tallest phase its wrapped header — the quality gate's
head goes 141.38px → 98.34px — and puts every phase in a row whose height comes
from a shorter neighbour. `align-items: stretch` then takes the teeth: every
phase ends where its row ends. It removes no air; it makes the row read as one
band instead of a comb.

The remaining 967.85px is structural, and the lever that would spend it was
measured rather than argued. The tallest phase is the quality gate, four suite
nodes stacked in one column, and making it wide (`WIDE_AT` 6 → 4) is the only
thing that shortens it. It loses at both floors this session considered:

```text
at 9rem      band 495 -> 365px, page 1737 -> 1607 at 1920 - and ELEVEN columns
             of 160.81px around a node needing 143.69px, with the instrument
             reporting `environment` broken at 1920 and NOT at 2560, which is
             the 5px main gains at its 120rem cap
at 18.5rem   three rows of four: 2039 -> 2205 at 1920 to save 2346 -> 2219 at
             1440 - a sixth of a screen spent at the primary target to buy a
             seventh back at a smaller one
```

The figures live beside the threshold in `scripts/generate-topology.py`.

## The instrument was aimed at its own new blind spot

Stretched boxes are all exactly as tall as their row, so `height` stops
answering "how much of this is used". An air measure written the obvious way
would have printed `0px` after the fix and read as a comb that was removed. Every
box is measured twice now — how tall it is, and where the last thing inside it
ends — which is what makes 1432.28 → 967.85px a reading rather than an
impression.

## 20i's +67px, settled exactly

20i measured +67/68px on the phone with every cut closed and +0 at 2560, 1920 and
1440, wrote a hypothesis, and marked it unverified. Measured per phase, at
`d96d9af~1` and at `d96d9af`:

```text
the phone, 390x844, at-rest, cuts closed
  Build            170.80 -> 204.58   +33.78   alone in its row      +33.78
  Approve          232.81 -> 266.59   +33.78   alone in its row      +33.78
  Provision        226.86 -> 260.64   +33.78   shares a row with the
                                               quality gate, 523.58       0
  everything else  unchanged
  the map          2033.52 -> 2101.08                              = +67.56
  the page         4774 -> 4842                                      +68
```

The mechanism is the hypothesis: three nodes gained a longer state line — the
three `observer` nodes that stopped saying `not run yet` — and each is alone in
its phase. Two of them are alone in their phone ROW as well, so each costs its
own 33.78px; the third shares a row with a phase three times its height and costs
nothing. On the desktop all three sat in the one row of ten, whose height came
from that same tall phase, so all three were absorbed and the delta was +0.

One detail of the hypothesis was wrong and is worth keeping: it named
`stage-apply`'s seven nodes as the row's height. The row's height came from the
quality gate — 495.03px against stage-apply's 350.34px — which is the same phase
D3 is about. The absorbing phase and the comb's tooth are one thing.

## Named rather than omitted

- **The comb is smaller and flattened, not removed.** 967.85px of air is inside
  the boxes at 1920, and D3 is where the price of removing the rest is written,
  at both floors.
- **The page is taller, and that is the decision rather than a side effect.**
  1.2 screens becoming 1.4 at 2560 was chosen against a variant that kept the
  height and kept a wrapped header on every narrow phase.
- **Six broken words remain, all on the phone, all outside the map**: three
  snapshot ids in the history table, two workflow filenames in a detail heading,
  and the repository URL in the footer. Each is a long identifier in a field that
  was never given `overflow-wrap: anywhere`. Left with the phone, deliberately.
- **The broken-word measure is not a gate.** It could be one — it reproduced a
  known defect and found an unknown one on its first run. Making it a gate needs
  its own break test and a decision about those six, and this session's scope was
  the packing.
- **Nothing here proves what a visitor sees.** Every figure is from the two frozen
  fixture sets in a headless chromium. The rendering half still has no gate, and
  the cost box is still unmeasured, because neither fixture set carries
  `cost/<env>/latest.json` (20i).
