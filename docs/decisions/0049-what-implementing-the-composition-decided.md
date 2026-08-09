# ADR-0049: What implementing the composition decided

## Status
Accepted (Phase 20e.1, 2026-08-09, the composition on the real page). Implements
ADR-0047 D1-D6 and ADR-0048. Narrows nothing; records the decisions that only
appear once the composition is built rather than sketched.

## Context

ADR-0047 decided what the page is (blocks, not a strip) and ADR-0048 decided the
three things that blocked laying it out. Both were made against a sketch built
from real topology data and PLACEHOLDER run, environment and cost figures, with
no launch control on it and no live sources.

Building it on the real page settled six things the sketch could not, and each
is here because a future session will otherwise re-decide it from the same
starting position.

## Decision

### D1 — one width, and the reading measure moves to the prose

The page had two: a 60rem reading column for everything and 82rem for the map,
stated as a cap on `main`'s children. A panel that stops at 60rem beside one
that does not is not a composition, so the cap moves to the PROSE that needs a
measure — the claim in the identity bar, the map's sentence, the text under the
cuts — and `main` goes to 96rem, which is what the map's computed column count
needs at the legibility floor. No rule mentions `100vw`, for the reason the
previous one didn't: that is the viewport including the scrollbar.

### D2 — the map folds into whole rows, never into a stranded one

ADR-0047 D5 says the span total is computed, not that any number of columns may
be drawn. Fitting as many of the ten columns as the width allows gave NINE at
1920 and put phase 8 alone on a second row with a screen of air beside it —
which is the picture D5 was written after, reproduced by the code meant to end
it. So the total folds into the fewest whole rows whose column count fits: ten,
then five, then two, then one. The sketch's media-query breakpoints were doing
this by hand.

### D3 — the legibility floor is per NODE SHAPE, and the old number is still in use

`--node-min: 12rem` was measured, by looking, against a node carrying an icon, a
name, a duration BAR, a figures row and a monospace identifier. The composed
node carries a head, one meta line and one state line, and the bar and figures
row no longer exist (ADR-0048 D3). At 12rem the eight phases cannot share a row
at any width this page has.

The floor becomes 7rem for the map, and the old number is kept as `--card-min`
for the permanent and outside cards under the cuts, which still carry a level
path and a sentence. A floor is a property of what it holds; two shapes need two.

### D4 — a state's edge is a background COLOUR, never a gradient

The sketch drew the `working` edge as `repeating-linear-gradient`, to say
"dashed" in the same channel as the colour. `make contrast-check` reads
`background-color` off `::before`, and an element painted with a gradient
resolves that property to `transparent`: the state would be on the page and off
the instrument.

Exercised rather than reasoned about — the gradient version reads **1.00:1 in
both themes and the gate refuses**. `working` keeps a solid 4px edge and says
"dashed" with its 1px outline and its word instead.

The general rule, and the reason this is an ADR rather than a comment: a channel
that carries state has to be one the gate can READ. A second channel the
instrument cannot see is decoration.

### D5 — a shared ATTRIBUTE is said once, exactly like a shared state

ADR-0047 D3 says a state every node in a phase carries is said once in the phase
header. The environment tag is the same shape and was not covered: `Apply —
stage` printed STAGE seven times under a heading that says stage. It is now said
once, in the same place, by the same rule.

How, and this is the part worth keeping: the nodes are drawn, ASKED what word
they carry, and drawn again without it only when all of them agree. The branch
that decides a node's state stays the only one — a second copy of those branches
in the phase renderer would be one definition on two hosts, which is the shape
that handed the image scan `postgres:16`.

### D6 — the request path is generated from citations, not written

The `where it lives` panel is the one place on this page that would otherwise be
hand-written prose about architecture, which is exactly the 2026-08-08 finding.
The ORDER is editorial — nothing under `infra/` states where a request goes; a
listener rule and a security group imply a hop, they never assert it — and so
are the tool names, because nothing there says that docker builds the image or
that alembic migrates the database.

Everything else is derived: each hop CITES a node or a permanent card by id, the
label and the service come from what is cited, and the generator REFUSES when a
citation names something the map does not have. The panel cannot outlive the
infrastructure it draws. Both refusals were exercised.

## Consequences

```text
- The bar is gone, and so is the paragraph under the map explaining that its
  length was approximate and the seconds beside it exact. A node says
  `measured · 4m 12s` instead. Nothing else read #approx.
- A suite's `asserts` sentence is no longer on the node; it is under the
  `Every resource named` cut, where renderDetail already prints it. That is
  ADR-0047 D1's "extra detail below the first screen", applied to the one piece
  of node text that is a description rather than a state.
- --node-min now means "the composed node". A future change that puts a second
  figure row back on a node has to move it again, and D3 says why.
- The phone is unchanged and still deferred. The history table is 52px wider
  than a 390px viewport with the cuts open; it was 73px before this session, in
  the same table, and neither figure is a regression.
- The sketch is now behind the page in two ways - it has no launch control and
  its figures are placeholders - so it stops being the reference. The page is.
```
