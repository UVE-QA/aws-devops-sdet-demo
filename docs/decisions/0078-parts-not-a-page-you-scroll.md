# ADR-0078: Parts, not a page you scroll

## Status
Accepted (Phase 39, 2026-09-08). Implements **ADR-0074** (*a dashboard is not a
log tail*), which had been Proposed since 2026-09-07 and whose shape was
undecided. Retires **ADR-0047 D2**'s below-the-fold cuts and the fold with them.
**ADR-0048 D2**'s legend stays and is opened.

## Context

The page was 3844px on a 1512px screen — 3.9 screens — and 8608px with every cut
open. Everything worked and nothing was hidden; reading it meant scrolling back
and forth between the thing you were looking at and the thing you were comparing
it against.

The owner asked for tabs, and then said exactly what kind:

> pseudo tabs (like filters) — just divide whole page into parts and show only
> what need at time. no diff links, no reloads

That rules out a router. Nothing here is a destination: there is no address to
share, no history entry, no fetch. It is a filter over a page that is entirely
loaded.

## Decision

**D1. Five parts, and one attribute decides which is showing.**

    Now      the environments, the request path, the step in flight, the cost
    Estate   the board — stage, prod, and the permanent levels
    Cycle    the map of phases, and the state encoding
    Tests    what the repository asserts, and the recent runs
    Detail   every resource named, outside the cycle, the counts

`<main data-showing="…">` and a `data-part` on each top-level block. The blocks
were **tagged, not re-nested**: wrapping them in containers would have changed
the layout on the way, and the point was to change what is shown, not how
anything is drawn.

**D2. The rule hides; it never shows.** Written the obvious way round — hide
everything, then `display: revert` the chosen part — it **flattened the cycle map
into a single column**, because `revert` rolls back to the *browser's* value and
discards `.cycle { display: grid }` along with the author rule it was meant to
restore. So the showing part is never given a `display` at all and keeps its own.
It also means a part carrying its own `hidden` — `#cost-box` does, meaning
*nothing to say yet* — stays hidden without a second rule about it.

**D3. What stays above the bar stays above it.** The identity, the claim, the
links, the red banner and the hold's clock. Those are the page's argument and its
alarms, and an alarm behind a filter is not an alarm.

The Launch control does **not** join them: ADR-0048 D1 put it in the environments
panel as that panel's footer and ADR-0064 raised it there, so it lives in `Now`.
`Now` is what a visitor gets, so the one action is on the first thing anybody
sees — but it is not reachable from the other four, and that is a real cost of
this decision rather than an oversight.

**D4. No cuts, because there is no fold.** ADR-0047 D2's rule was that a cut is
not hidden content: the header answers *is anything wrong* and the lines inside
answer *which*. The bar now answers a bigger version of the same question, and a
cut inside a part is the same hiding twice — two clicks from a fact. The four
page-level `<details>` open flat inside the parts that hold them, and the legend
with them: a key folded away on the one screen it explains is a key nobody reads.

`details.inline` survives and is a different animal — the per-resource lists
`renderDetail()` generates *inside* the reference text. Flattening those would not
remove a layer of hiding, it would print a hundred and sixteen lines nobody
asked for.

**D5. The choice is not remembered across a reload, and that is deliberate.** The
page re-reads its sources on a timer without reloading (ADR-0062 D2), so a tab
left open keeps its part for as long as it is open — which is the case that
matters, and the one a cycle is watched in. A visitor who comes back tomorrow
gets `Now`, which is what a visitor should get.

**D6. The map re-lays itself when its own box changes width.** `render()` folds
the phases by measuring `host.clientWidth`, and the parts made that measurement
**zero**: at load the page shows `Now`, so `#rows` is `display: none`, a hidden
element's `clientWidth` is 0, `fits` came out 1, and the whole map drew as a
single column. **Every gate was green over it** — not one of them looks at how
many columns the map has — and it was found by looking at the picture.

A `ResizeObserver` on `#rows`, replacing the window `resize` listener rather than
joining it: the width now changes for a reason the window knows nothing about,
and two paths re-laying the same map are two things to keep in step. Width only,
because `render()` sets `gridTemplateColumns`, which changes the map's height,
which fires the observer again.

**D7. The instrument's axis is the part, not the cut.** `measure-page` measured
`cuts closed` and `cuts open`; both are gone, and `open` would now be a state the
page cannot be in. It clicks through the five parts using the page's own switch —
a measurement taken by writing the attribute directly would be green over a
switch that no longer works — and refuses if the page ends up showing a different
part from the one it asked for.

## Consequences

**What a reader's screen now holds**, at rest, measured:

    2560x1440   now 1.0   estate 1.0   cycle 1.1   tests 1.0   detail 3.2
    1920x1080   now 1.1   estate 1.3   cycle 1.5   tests 1.2   detail 4.3
    1440x900    now 1.3   estate 1.6   cycle 1.9   tests 1.5   detail 5.2
    390x844     now 3.1   estate 4.6   cycle 4.5   tests 3.3   detail 9.2

Against 2.6 screens for the whole page closed and 6.1 open at 2560. Four of the
five parts are a screen or a screen and a half on any desktop; `Detail` is long
because it is a reference list and reading it *is* scrolling.

**The phone is not fixed by this.** Every part is still three to nine screens
there, because the phone's problem was never the page's structure — it is one
column of everything. The `tests` part carries a 105px horizontal overflow at
390px, which is the run-history table and predates this.

**A part is a place a gate can forget.** `measure-page` holds the list of five
by hand for the reason `assets/gates.json` holds `requires` by hand: a list read
out of the DOM cannot notice a part the page forgot to draw. Nothing yet checks
that every `data-part` value in the markup is one of the five.
