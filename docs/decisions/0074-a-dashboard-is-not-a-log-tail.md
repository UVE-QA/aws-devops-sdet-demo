# ADR-0074: A dashboard is not a log tail

## Status
Proposed (Phase 38, 2026-09-07). Supersedes the single-layout assumption in
**ADR-0047 D1** and absorbs **ADR-0071** D1 and D3, which are symptoms of it.
Nothing implemented; the design is settled and the work is not started.

## Context

Watched by its owner through three live cycles, the page failed at the only job a
dashboard has: **saying what is happening.**

```text
the estate         twelve cards, one state for the whole cycle. No more
                   informative than the two UP / DESTROYED badges above them,
                   and between the reader and the live front - so following a
                   cycle meant scrolling up and down through a dead field.
"the step in flight"  opened with a job that had finished half an hour earlier,
                   because ADR-0068 turned three jobs into six and the live one
                   is last.
after the countdown   the tile removes itself exactly when the teardown it
                   announced begins, and nothing replaces it.
the explanation    is prose. Good prose, and nobody reads it: what the system
                   does and how it is built are carried by paragraphs on a page
                   whose reader has ninety seconds.
```

The owner's summary is the finding: *это дашборд, а не прогонка логов* — this is a
dashboard, not a log tail. And the Current cycle panel **is** a log tail: job
names and step lists, in API order.

Two rules came out of that, and everything below follows from them:

> In a cycle, the visible part of the layout must be live. Everything static
> belongs out of view unless it complements what is happening.

> Before the cycle, there must be an explanation of what happens here and how it
> is built — **not as text**, nobody will read it. Visual, and expandable.

## Decision

### D1 — tabs, not one page and not a layout that reflows

Three, across the top:

```text
Now            environments, the live front, the elapsed counter, the countdown
How it works   the phase map and the request path - the visual explanation
What's there   the estate, the permanent levels, the suite inventory, the cost
```

**Tabs rather than collapsing sections.** The first design here was a mode that
folded static sections away when a cycle started. That moves content under a
reader's cursor at the exact moment they are trying to follow something, and it
means a page arrived at during a cycle is a different page from the one at rest —
which matters, because this page is also a portfolio piece and must look finished
in both states. Tabs move nobody and hide nothing; the reader navigates.

### D2 — the default follows the cycle, and the reader is never moved

The tab a visitor lands on depends on whether a cycle is running: `Now` if one
is, `How it works` if not. **A reader already on a tab stays there.** A cycle
starting while somebody is reading the map must not throw them somewhere else —
that is the reflow this ADR exists to avoid, with the loss of their place added.

`Now` carries an activity marker in its own tab heading instead, so a reader on
another tab can see that something started and decide for themselves.

### D3 — the live tab fits one screen

No scrolling to follow a cycle. This is a measurable claim, not an intention, and
`make measure-page` is the instrument that already exists for it: the target is
one screen at 1440, cuts closed.

### D4 — the explanation is visual by default and prose on demand

The visual explanation already exists and is below the fold: the phase map,
generated from `infra/` and `tests/`, drawn in the order a cycle runs. What is
needed is not a new diagram but an inversion — the map first, the paragraphs
behind a cut.

This is also the strongest argument for the swap. The map is not decorative: a
gate refuses when a resource block belongs to no group, so the picture cannot
drift from the infrastructure it describes. Promoting it promotes that property.

### D5 — the counter counts up, and the estimate is an observation

The page never subtracts and never predicts.

```text
elapsed     counts up from the phase's start. What is happening, now.
estimate    "~10min", stated flat, from what previous cycles measured.
```

**Not "5 minutes left".** Every figure on this page is an observation, and a
remaining time is an inference — the one thing this project has never published.
The two numbers sit beside each other and the reader does the comparison. When a
phase overruns, the page has promised nothing and retracts nothing.

**Phases carry the number; nodes carry the highlight.** A phase estimate is
stable enough to decide on — `apply` measured 489s — while a per-node figure is
not: RDS took 455s last cycle and may take 700 this one, and a reader watching
`11 minutes, of about 7` learns only that the page is unreliable. Nodes light up
to show where the front is; they do not each carry a promise.

## Consequences

- **Three gates read the rendered DOM and all three are affected.**
  `measure-page` (11 DOM reads) would measure only the visible tab — which is the
  right answer to "how many screens is this page", and a change in what the
  recorded figures mean. `page-inflight-check` (8) and `page-freshness-check` (7)
  look for elements that may sit in a hidden tab and must be taught to open it.
  None of this is new machinery: they already open the map's cuts.
- **`page-freshness-check`'s claim needs narrowing.** *A tab left open shows what
  a reload would show* becomes ambiguous the moment a selected tab exists: a
  reader on `How it works` when a cycle starts sees something a reload would not.
  The rule becomes per-tab, and that narrowing is part of this work rather than a
  surprise during it.
- **The estate is not enlivened here.** Per-resource live state is a separate
  phase and belongs after this one: making twelve cards informative and then
  putting them behind a tab is the wrong order. The states it would need already
  exist — `live`, `working`, `done`, `failed-now`, `gone`, `absent` — and the
  terraform stream already emits `apply_start`, `apply_complete`, `apply_errored`.
  What is missing is publishing them during the apply, which is ADR-0043 D2's
  recorded limit and, on inspection, stated too strongly: it says per-resource
  state needs the timeline published *by the step holding the deploy role*, and
  it does not. The job already holds the publish role at the end; publishing
  earlier needs interleaving, not a wider deploy credential. That correction
  belongs to whichever phase takes it.
- **The estimate data is already published and already on the page**, as static
  per-node durations. Nothing new is measured or stored; what changes is that a
  figure sitting there as trivia becomes the thing a reader decides on.
- ADR-0071 D1 and D3 are absorbed rather than fixed separately. Leading with the
  live job and replacing the countdown when it ends are both what `Now` is for,
  and fixing them inside today's layout would be work thrown away.
