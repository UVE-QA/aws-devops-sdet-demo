# ADR-0087: The button says how long, before it is pressed

## Status
Accepted (Phase 40, 2026-09-12). Extends **ADR-0073**'s control strip and
**ADR-0082**'s row: the quota was the first thing put beside the button for this
reason, and this is the second.

## Context

The owner, looking at the launch control:

> и где-то в районе кнопки запуска нужно хорошо видимую плашку с эстимейтом
> полного цикла, чтоб запускающий понимал, на что он подписывается

A visitor can read every word on this page and not learn that the button starts
something that runs for the better part of an hour. The page says what the cycle
*does* — five phases, a five-minute hold, both environments destroyed — and
never what it *costs them in time*. Nobody watches fifty minutes of it; the
point is that they know that before they press, not after.

The same argument produced the quota badge in ADR-0073: *a visitor could not tell
a button that will work from one that will be refused until they pressed it*.
This is the other half of the same sentence.

## Decision

**D1. The row carries a measured duration, and only that.** `≈ 52 min`, beside
the button and the quota, quieter than the quota — the quota is a refusal the
button will make, this is a duration it will take, and the two must not read as a
pair of counters. No cost and no per-phase breakdown: the owner asked for time
alone, and the cost box already prices the last cycle three inches below.

**D2. It is measured, never written down.** The figure is the MEDIAN of the last
seven self-service runs that finished and succeeded, from the run history this
page already reads — no new request, no number in the markup. A figure typed into
the template would describe whatever the pipeline was on the day it was typed,
and this pipeline has grown from one environment to two inside a month
(ADR-0068).

Only finished, successful runs count: a cancelled one is shorter than the thing
it was going to do and a failed one stops wherever it broke, so neither answers
*how long will this take*. Owner dispatches count, because the workflow is the
same one and its shape is what is being measured.

The median rather than the mean: one run that waited twenty minutes for a runner
is a property of that morning, and a mean carries it into every reading
afterwards. The spread goes in the title — `the median of the last 7 that
finished (51–53 min)` — so it is available without a second number on the row.

**D3. Nothing to measure means nothing is shown.** The badge is hidden until a
cycle has finished, the same rule the cost box follows: a page that has never
seen a cycle finish has no business estimating one.

## Consequences

- The figure moves on its own as the pipeline changes, which is the point. It
  does NOT move when a cycle dies early — the 37-minute failure of 2026-09-08 is
  not in it — and that is why the filter is on `conclusion` and not only on
  `status`.
- It is a median of a sample of seven, so a cycle that grows by three minutes
  takes four cycles to show it. Acceptable: the alternative is a mean that reacts
  immediately and to the wrong things.
- One more thing the run history pays for, at no extra request: `state.runs` is
  already fetched for the panel, the history table and the quota approximation.
- The row is now button, duration, quota — three things at the right end of the
  tab row. A fourth would need a different shape, and the phone layout (deferred)
  will have to decide what it drops.
