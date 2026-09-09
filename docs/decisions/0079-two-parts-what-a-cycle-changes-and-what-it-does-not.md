# ADR-0079: Two parts — what a cycle changes, and what it does not

## Status
Accepted (Phase 39, 2026-09-08). Replaces **ADR-0078 D1**'s five parts with two;
everything else in ADR-0078 stands unchanged — the hiding rule, the bar's
position, the map's `ResizeObserver`, the instrument's axis. Restores one of the
cuts ADR-0078 D4 removed.

## Context

ADR-0078 cut the page into five parts — Now, Estate, Cycle, Tests, Detail — and
the cut was made by *subject*: environments here, the board there, the map next.
That is how the page was already headed, so it looked like the obvious division,
and no reason for it was written down beyond "each is about one screen".

The owner sorted the same blocks by hand and used a different question. Not *what
is this about* but **does a cycle change it**:

    WHERE IT LIVES        static     the request path, generated from infra/
    PERMANENT             static     six levels no teardown touches
    OUTSIDE THE CYCLE     static     the devbox and GitHub
    EVERY RESOURCE NAMED  static     the whole of infra/, in words

    ENVIRONMENTS + Launch live       what AWS says now
    CURRENT CYCLE         live       the step in flight
    the estate board      live       what exists, per environment
    the map of phases     live       what a run reported
    assertions + runs     live       what the suites said

That is a better division than the one it replaces, and the reason it is better
is not taste. **The five subjects were a table of contents; live-versus-static is
a property of the data**, and this page's whole argument is about which of its
figures are observations and which are facts about the repository. A reader who
knows which part they are in knows whether what they are reading can change
while they watch.

## Decision

**D1. Two parts.** One holds everything a cycle changes; the other holds
everything that is true of the repository whatever runs.

**D2. The request path leaves the live grid.** `WHERE IT LIVES` was the middle
panel of `.top`, beside the environments and the run — and it is generated from
`infra/` and changes only when the infrastructure does. It moves to the static
part, which leaves `.top` as two panels. `.p-env` loses its `grid-row: span 2`
with it: that span existed to be as tall as the path and the run stacked, and
with the path gone it would hold a hole open.

**D3. One cut comes back.** `Every resource named` is four thousand pixels of
`infra/` written out, and ADR-0078 D4's rule — a cut inside a part is the same
hiding twice — is about a cut that hides *the point of the part*. This one is the
reference the dashboard deliberately is not, and flat it buries the three blocks
above it. Every other cut stays flat.

## Consequences

**The live part is nearly as long as the old page.** Measured, at rest:

    2560x1440   live 2.7 screens   static 1.0
    1920x1080   live 3.7           static 1.3
    1440x900    live 4.5           static 1.6
    390x844     live 11.0          static 3.8

Against ADR-0078's five, which were 1.0–1.5 screens each on a desktop, and
against 2.6 screens for the whole page before either. **So this division does not
solve the scrolling it was reached through** — it halves the page and no more.
That is not an argument against it: the sort is right about the data, and the
five parts were right about the height. Both can be true, and the resolution is
not in this decision.

What is bought is real and is not length: a reader on the live part is looking at
things that can change under them, and on the static part at things that cannot.
Nothing on the page said that before.

**`Cycle` is a poor name for a part that opens with the environments panel.** The
names are the owner's placeholders and were explicitly not discussed; they are
recorded here as provisional so the next session does not read them as decided.
