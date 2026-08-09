# ADR-0052: The floor is what a node has to draw

## Status
Accepted (Phase 20j, 2026-08-09, the packing). Supersedes **ADR-0049 D3**'s
number and the reasoning that produced it; **ADR-0039 D5** — the map folds rather
than shrink past its floor — is unchanged, and this is the first session that
measured what the floor is. Closes the two items **ADR-0050** named and left: the
comb and the ragged top row.

## Context

Three numbers have been the map's legibility floor, and the first two were
measured against the same wrong thing.

`12rem` was measured by looking at a node that carried an icon, a name, a
duration bar, a figures row and a monospace identifier. `7rem` replaced it in
20e.1 because the composed node carries a head, one meta line and one state
line: the bar and the figures row were gone, so the floor came down. Both are
statements about what a node CONTAINS. Neither is a statement about what it has
to DRAW, and the fold consults it as if it were the second.

The difference is visible on the page. At `7rem` the fold is allowed a 162.7px
column, and on a phone it takes two of them — inside which the word
`environment` does not fit, and `overflow-wrap: break-word` splits it across two
lines. That break has been in the published page since the composition landed.
Nobody reported it, and the instrument could not: `make measure-page` reports
overflow, and a broken word is not overflow. It is the layout obeying an
instruction that was wrong, exactly as ADR-0050 said of the breaks it found by
eye.

So this session gave the instrument the question. A `Range` over a single word
returns one client rect when the word sits on one line and two when the line box
split it, which makes `environme|nt` a measurement rather than something a
person happened to notice. Run against the page as it stood, it reported both
known breaks without being told where to look — `RDS PostgreSQ|L` at 1440, which
20g found by eye, and `environment` on the phone, which nobody had.

With the same Range the floor itself is derivable. For every node the map draws:
the widest single word in its name, and the whole name on one line, each plus
everything between the name's box and the node's own — the icon, the gaps, the
padding.

```text
every word whole      143.69px   the widest is "environment", 89.63px
every name unwrapped  295.58px
--node-min                7rem = 112px
```

The two other items in front of this session were the ones ADR-0050 measured and
left. Measured again here, on the page as it stood, at 1920, cuts closed:

```text
the comb          map 495.03px in one row of ten columns, 1432.28px of air
                  under seven phases; the shortest is 204.58px
the ragged row    465 / 228 / 235px - one panel decides the row's height and
                  the other two end less than half way down it
```

## Decision

### D1 — `--node-min` is 18.5rem: a node draws its name, not enough of it to guess

295.58px is where no node name wraps, and 18.5rem is that number rounded up to
the next half rem. The map folds to five columns in two rows at 1920 and 2560,
four in three rows at 1440, and one column on a phone.

The other measured number, `143.69px` — where the widest word merely stops
BREAKING — is not the floor. It is the line beneath which the map draws
something a reader cannot read, and no future number may go under it. Both are
printed by `make measure-page` so that the next person moving this can see which
one they are moving toward.

What it costs, measured either side with the same fixtures, cuts closed:

```text
at-rest        2560    1920    1440     390        in-flight   2560    1920
before         1734    1742    2123    4842        before      1760    1790
after          2039    2039    2346    5472        after       2051    2051
```

About 300px on the desktop — 1.2 screens becoming 1.4 on the stated primary
target — and 630px on the phone, which is the one viewport where the change is
not a preference: at two columns it was breaking a word, and at one column it is
not.

The one-line figure is honest only where nothing wraps. Measured on a page whose
names are wrapped, the sum of a name's line boxes reads 286.92–295.58px
depending on where the wrap falls; measured after the fold, with every name on
one line, it is 295.58px exactly. The number in this decision is the second
reading.

### D2 — The first screen is two columns, and the request path gets the width

The environments panel down the left over both rows; the request path and the
run in flight stacked to its right. `4 / 8 / 8` of the same twelve-column grid,
with `align-items: stretch`, and the source order unchanged so a reader still
meets the environments, then the path, then the run.

The shape comes from the content rather than from taste: 465 against 228 + 235 +
a gap is 465 against 475. Three panels in a row were never three of anything.

It also settles a fix 20g reverted. Five hops had 5/12 of the row — about 100px
each at 1440, where `RDS PostgreSQL` broke. Giving the path the whole row below
1500 fixed it and cost 290px, so it was reverted with its figure. At 8/12 the
same hops have 184px at 1440, nothing breaks, and the row is 69px SHORTER than
the three-column one. The fix was always width; it came from packing rather than
from a breakpoint.

### D3 — The comb: two rows take a third of it, `stretch` takes the teeth, and the rest is structural

At the floor in D1 the map is two rows of five at 1920, and the air under the
phases falls from 1432.28px to 967.85px there — 909.65 → 694.72px at 1440 —
without anything being packed by hand:
a wider column costs the tallest phase its wrapped header (141.38px → 98.34px)
and gives every phase a row whose height comes from a shorter neighbour.

`align-items: stretch` takes the teeth: every phase ends where its row ends. It
removes NO air — the same emptiness is inside the boxes — and the honest reason
to prefer it is that a box which ends where its neighbours end reads as a column
of the same thing, which is what a phase is.

The remaining 967.85px is structural, and the lever that would spend it was
measured rather than argued. The tallest phase is the quality gate, whose four
suite nodes stack in one column; making it wide (`WIDE_AT` 6 → 4 in the
generator) is the only thing that shortens it, and it loses at both floors this
session considered — at 9rem it produces an eleventh column of 160.81px and
breaks `environment` at 1920; at 18.5rem it folds into three rows of four and
costs 2039 → 2205 at 1920 to save 2346 → 2219 at 1440. The figures are written
beside the threshold, in `scripts/generate-topology.py`.

### D4 — The instrument answers for the packing, and for its own scope

`make measure-page` now reports every phase against the height of the row it
shares, every panel above the map against the same question, the words a line
box split, and both floors above. Still not a gate: no verdict, nothing in
`ci.yml` depends on it.

One property of D3 forced a second measurement. Stretched boxes are all exactly
as tall as their row, so `height` stops answering "how much of this is used" —
an instrument that reported the air as zero after D3 would be hiding the comb
rather than measuring it. Every box is therefore measured twice: how tall it is,
and where the last thing inside it ends. The air is the difference, which is how
the 1432.28 → 967.85px above is a reading rather than an impression.

## Consequences

- `--node-min` is 18.5rem and carries the measurement that produced it. A node
  whose name gains a longer word moves this number; the instrument says by how
  much, and 143.69px is the line it may not go under.
- The map is two rows of five at 1920 and 2560, and THREE of four at 1440.
  `layout.columns` is unchanged and still computed — the fold, not the total, is
  what moved.
- The page is about 300px taller on the desktop and 630px on the phone. Anything
  later that argues from "composed, not scrolled" is arguing against this
  decision and should say so.
- The first screen is two columns above 1100px. Below it the previous rule stands
  unchanged: the path takes the whole row, and the environments panel gives up
  its second row with it.
- 20g's reverted 1500 breakpoint stays reverted and its figure stays in the
  stylesheet, now as the first half of a decision rather than as an open item.
- The comb is smaller and flattened, not removed. D3 is where the price of
  removing the rest is written, at both floors.
- `make measure-page` gained three measurements and no verdict. The broken-word
  measure is the one that could become a gate; it is not one today, because a
  gate here needs its own break test and a decision about the six breaks it finds
  on the phone — all outside the map, all long identifiers in fields that were
  never given `overflow-wrap: anywhere`.
