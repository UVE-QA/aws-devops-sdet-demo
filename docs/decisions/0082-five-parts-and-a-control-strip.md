# ADR-0082: Five parts, and a row that carries the control

## Status
Accepted (Phase 39, 2026-09-10). Re-cuts **ADR-0079 D1**'s two parts into five;
its sorting question — *does a cycle change it* — still decides which side of the
live/static line a block is on, and only the live side is subdivided. Reverses
**ADR-0048 D1** and **ADR-0064** on where the Launch control lives. Moves the
identity bar out of the always-visible strip **ADR-0078 D3** put it in.

## Context

ADR-0079 sorted the page into what a cycle changes and what it does not, and its
own Consequences said the sort did not solve the scrolling it was reached
through: the live part was 2.7 screens at 2560 and 4.5 at 1440, against 2.6 for
the whole page before either. *"The sort is right about the data and the five
parts were right about the height, and the resolution is not in this decision."*

This is that resolution. The live half divides again — by the question a reader
is asking, which is a different axis from the one that separated it from the
static half, and both are properties of the content rather than a table of
contents.

## Decision

**D1. Five parts.**

    Now      the environments, the run in flight, what it cost
    Estate   the board — stage, prod, per service
    Cycle    the map of phases, and the state encoding
    Tests    what the repository asserts, and what the runs reported
    Details  everything a cycle does not change (ADR-0079)

**D2. The tab row carries the control.** Left: which part you are looking at.
Right: the one thing this page can be asked to do, and the number that says
whether it will be refused. Opposite ends of one line, because **they are the two
things true of the whole page rather than of any part of it** — and a button
reachable from one part in five is a button most visitors never see, which is the
cost ADR-0078 D3 named and left standing.

This reverses ADR-0048 D1, which put the control in the environments panel
because *"its refusals are statements about that state, so the refusal and the
thing it is about are in the same box"*. That reasoning was right about a page
that was one scroll. With parts, the box is one click away from four of five
views, and being *reachable* beat being *adjacent*.

**The three sentences that explain the button did not come with it.** Prose in a
control strip is prose nobody reads. They open `Now`, beside the environments the
button acts on and the run it starts, and `#launch-said` carries `hidden` with
`#launch` — a page that says what a button does while showing no button is worse
than one that says neither.

**D3. The identity bar is in `Details`.** It was above the parts by ADR-0078 D3,
on the grounds that the page's argument is not a part. Measured, that argument
cost 145px on **every** part, and the owner reads it fifty times a day.

**The cost was real and was paid back the same day (ADR-0084).** As first
written, the page no longer said what it was above the fold: a visitor arriving
from a CV link saw a tab row and a button. The name and one clause of the claim
now sit left of the parts, on the row that was already there, so the fix costs no
height. The paragraph, the links and the decision-record count stay here.

**D4. Every part shares its width with something.** `Now` is the shape ADR-0047
D1 measured, minus the request path that left for `Details`: environments in four
columns spanning both rows, the run in eight, the cost under the run. The run
panel alone had all twelve, and its content is a step name on the left with a
duration on the far right — at 1450px the eye crosses a metre of nothing to read
`7m 45s`.

## Consequences

Measured at rest, screens per part:

    2560x1440   now 1.0   estate 1.0   cycle 1.1   tests 1.0   detail 1.1
    1920x1080   now 1.0   estate 1.0   cycle 1.4   tests 1.1   detail 1.4
    1440x900    now 1.0   estate 1.1   cycle 1.7   tests 1.3   detail 1.8

Against ADR-0079's live part at 2.7 / 3.7 / 4.5. Four of five parts are exactly
one screen at 2560, and nothing anywhere exceeds 1.8.

**`Cycle` is the tallest and cannot be shortened from here.** The map is 1215px
of eight phases at any width; making it smaller is a change to the map, not to
the parts.

**The phone is untouched by all of this** and remains three to five screens per
part, because its problem was never the page's structure.

**`Details` still holds the request path.** It is static, so ADR-0079's sort puts
it there correctly — and `Cycle` is now a part about what a cycle does, which is
arguably where *where a request goes* belongs. Named, not moved: the sort's rule
is the one that has been holding up, and a single exception to it needs a better
reason than a hunch.
