# ADR-0062: A qualifier outlives its premise, and the first news arrives on the slowest clock

## Status
Accepted (Phase 28, 2026-08-11). Extends **ADR-0051** (the sentence that
qualifies a figure while an environment is being touched) and **ADR-0059 D1**
(a figure names its cycle). Neither is reversed; both are applied to a case
their own reasoning did not cover.

## Context

Phase 28 ran a full cycle - stage up, promoted to prod through the approval
gate, both torn down - on a day different from the previous one, and watched it
through a single tab that was opened before the first dispatch and never
reloaded, navigated or Refreshed. Two of the three items the cursor carried are
answered elsewhere in this phase's record. This ADR is about the two things
nobody was looking for, both of which are visible only while something is
running, which is the only time anybody watches.

## Decision

### D1 — A figure is qualified by WHOSE cycle it is, not by whether a cycle is running

`nodeTense()`'s under-way branch attaches `these figures are from the cycle
before this one` to every record it draws while a run is touching that
environment. The comment above it states the premise out loud:

> NOTHING PUBLISHES UNTIL A CYCLE ENDS, so every figure drawn while one is
> running is the cycle before it

That is false, and the cycle printed the counter-example. `promote-prod`
publishes `timeline/prod/nodes-apply.json` from a step inside its own job, and
the job then goes on to run the prod quality gate and push the release tag. So
between the publish step and the job's completion the page holds figures written
by the run in flight and calls them the previous cycle's:

```text
06:11:43Z   publish writes nodes-apply.json     cycle.run.number = 12, date 2026-08-11
06:12:44Z   page    measured · these figures are from the cycle before this one · 23s
            page    promote-prod #12 · in progress · 16m 5s
06:17:29Z   page    measured · 23s                     the run completed; the sentence cleared
```

The eight figures drawn at 06:12:44 differ from the previous cycle's in all
eight positions - `23s · 8m 16s · 8m 15s · 3m 3s · 11s · 0s · 30s · 7s` against
`27s · 8m 18s · 8m 18s · 3m 7s · 12s · 1s · 31s · 8s` - and `prod.vpc` in the
published document reads `duration_s: 23.0`. They are this run's. The exposure
was about five minutes, bounded on one side by the publish step and on the other
by the job ending.

**This is the exact mirror of 20m's third finding.** There the disclaimer was
missing where it was needed; Phase 25 added it; here it is present where it is
wrong. One predicate was asked in both cases and it was the wrong one: *is a run
in flight about this environment?* The right one is *does this record belong to
the run in flight?*, and the record already answers it - `cycle.run.id` has been
in the document since ADR-0039. ADR-0059 D1 named the principle for cost; the
node captions did not get it.

### D2 — The poll interval must not be conditioned on knowing there is something to poll for

`scheduleRefresh()` reads:

```js
if (!live) return 300000;
```

and `live` is true only when the page ALREADY knows about an unfinished run. So
the page sits on a five-minute clock precisely while the news it lacks is that a
run has started, and speeds up to ~123 s only after it no longer needs to.

Measured, twice, in one cycle. `destroy prod #46` was created at 06:19:15Z; the
page's first word about it carried an elapsed of `4m 53s`, so it learned at
about 06:24:08Z - **293 s**, against a 300 s ceiling. Between two samples at
06:22:42Z (absent) and 06:25:16Z (present, `waiting`) this is pinned.

**It lands on the one node the map addresses to a person.** Phase 5 is
`Approve · a human, in the prod environment`. The human is needed at the start of
a run, and the start of a run is when this page is slowest to notice. The word
`waiting` exists and is correct when it appears; what is wrong is when.

Nothing here argues for polling harder. It argues that the interval is derived
from the wrong state: "I know of no live run" and "there is no live run" are
different, and the code treats the first as the second.

### D3 — An instrument's arithmetic hangs on the timestamp it needs, not on a neighbour

`scripts/watch-convergence.sh` computed `write->edge` only when `Age` was
present, because `Age` is how a cached response says when the edge fetched it.
CloudFront omits `Age` on a MISS - which is the response that FIRST carries a new
object, and therefore the one measurement the instrument exists to take. Three of
this cycle's five transitions printed `-` and had to be reconstructed by hand
from `head-object` afterwards. The condition now asks for `Last-Modified`; when
`Age` is absent the edge went to the origin during that request, so the fetch is
inside the request window, which is printed.

### D4 — A delay measured by a poller is reported with the poller in the sentence

Five transitions were measured:

```text
1.1s   1.6s   8.6s        the edge held nothing or an error - it fetched at once
57.6s  61.1s              the edge held a copy with a TTL still to run
```

The spread is not noise. A copy at the edge lives to the end of its current
sixty-second window, and where in that window a write lands is arbitrary - so the
delay is roughly uniform in `[0, 60]`, and five draws is five draws.

The two high ones are the instrument's own doing. Sampling every two seconds
keeps a fresh copy at the edge at all times with a full TTL ahead of it, so a
write can never find the edge empty. A visitor who does not poll frequently often
does, and gets the object immediately. **A log of these numbers without this
paragraph would say the opposite of what happened**, so the paragraph is in the
script, not only here.

One thing this settles rather than opens: the page prints `the figures up to a
minute behind the write` beside its own Refresh button. Measured, it is true.
20k caught that sentence being untrue once; this is the first time it has been
checked rather than believed.

## Consequences

- Two gates are owed, and neither can be written against the fixtures as they
  stand: `tests/fixtures/page-inflight/` holds the run layer FIXED while a run is
  in flight, and both D1 and D2 live in the layer or the clock CHANGING mid-run.
  A fixture that publishes underneath a running page is the new thing to build.
- D1's fix is a predicate, not a sentence: compare the record's `cycle.run.id`
  with the run in flight. The wording only becomes a question once the comparison
  exists.
- D2's fix has a cost this ADR does not price: a shorter interval while nothing
  is known to be running spends the anonymous GitHub budget the page already
  paces itself against. The budget was down to 23 of 60 during this cycle, partly
  from this session's own reads.
- The `not reached yet` arrangement (deleting a published record before a
  dispatch) is repeatable and cost-free, and it is how the mirror clause was
  finally seen. It is written up in `docs/phase-gates.md` under Phase 28 rather
  than turned into a script: it deletes from a live bucket and should be read
  before it is run.
