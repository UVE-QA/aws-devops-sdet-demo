# ADR-0063: A gate over a moving subject needs a fixture that moves

## Status
Accepted (Phase 29, 2026-08-12). Implements the two Consequences **ADR-0062**
left open, and corrects **ADR-0051**'s qualifier and **ADR-0026**'s poll pacing
at the same point. Extends **ADR-0059 D5** — the instrument that had never
measured a page with figures on it — to an instrument that had never measured a
page while anything changed.

## Context

Phase 28 watched a live cycle through one tab and found two defects, both of
them visible only while something was running. `make page-inflight-check` was
green throughout. It holds one moment still and reads it, which is what every
page gate here does, and neither finding exists in a still moment.

Worse than blind: its third claim stated the false premise in its own comment —
*nothing publishes until a cycle ends, so every figure drawn during one belongs
to the cycle before it* — and therefore REQUIRED the disclaimer on figures the
run in flight had just written. Fixing the page would have reddened the gate. A
gate that asserts the defect is a stronger entry than one that merely misses it,
and it is the fourth time in this project that a sound instrument has been found
aimed at the wrong scope.

## Decision

### D1 — A fixture for a moving subject is a SEQUENCE, and the page is loaded once

`tests/fixtures/page-inflight/` grows two things that are never loaded as states:

```text
layer-published/   an OVERLAY on layer/, holding the one document deploy-stage
                   #64 writes from a step inside its own job. Applied while #64
                   is still in_progress.
new-run/           at-rest plus one queued run, twenty seconds later. It is what
                   the GitHub API STARTS ANSWERING while an at-rest page is
                   already open.
```

The gate loads the page once and changes a source underneath it — the bucket in
one pass, the API in the other. No reload, no navigation, no Refresh, and that
is asserted rather than assumed: a sentinel is left on `window` and required to
survive to the second reading. The clock is INSTALLED rather than fixed, because
a tick that has to happen in real time is a gate nobody will run.

Two guards make the pass a pass rather than a formality. The publish must have
MOVED something the page draws, or every sentence after it is a sentence about a
page that learned nothing — the mirror of a control that reproduces its defect,
and the risk peculiar to a sequence. And the document must be published by the
run actually in flight, checked against the history, not assumed from the
directory name.

### D2 — A figure is qualified by whose cycle it is (ADR-0062 D1, implemented)

Three changes, one predicate:

```text
readRunLayer()   attaches `published_by` to every node record. cycle.run.id has
                 been in the document since ADR-0039 and the fold threw it away,
                 which is why the question could not be asked.
underWayHere()   becomes flightHere() and answers with the RUN, not with a yes.
                 A boolean was exactly as much as the caller could then know.
nodeTense()      compares the two: `these figures are from the cycle under way`
                 when they match, at full colour, because a node this run has
                 already finished is done rather than stale.
```

`true` survives as flightHere()'s answer for a run in flight with no id —
honest, and unable to equal any `published_by`, so the disclaimer degrades to
the old behaviour instead of disappearing.

**The suite half already had the right predicate.** Phase 25 wrote
`String(env.run.id) !== String(obsRun.id)` for `result_previous`, two functions
below the node half that kept the boolean. One of the two mirrors was fixed a
phase earlier and nobody looked at the other.

### D3 — The idle poll is derived from the budget, and paid for by a read that could not change

`if (!live) return 300000` conditioned the interval on the news the page lacked.
The idle interval is now derived from the same rate budget as the live one,
floor 60 s and ceiling 300 s.

Nothing polls harder per hour. `readGitHub()` stops re-reading the STEPS OF A
FINISHED RUN, which cannot change, so an idle poll costs one request instead of
two — and 60 requests an hour is one a minute. The status at the time of the
read is stored beside the steps, so the read just after a run completes still
happens and only the ones after it are skipped. With eight requests left the
arithmetic returns to 300000 by itself.

This is the cost ADR-0062 D3's Consequences said was unpriced. It is priced, and
it is zero.

### D4 — A mock of a cross-origin response must model the headers the real one exposes

The first measurement said the first news arrives in `(105s, 120s]`, which is
neither the old constant nor the new floor — it is the fallback constant for
*the budget could not be read*. `api.github.com` is a different origin, the mock
never sent `access-control-expose-headers`, and `r.headers.get()` had therefore
returned null for both ratelimit headers since this gate was written. Every
reading it has ever taken was of the page's fallback branch.

It did not matter while the idle interval was a constant. It is the whole
subject now, so the gate REFUSES when the page could not read the budget.

Two independent things settle it, which is what the 2026-08-05 control failure
asks for: the page's own advertised cadence, read back off the DOM and equal to a
fallback constant, and Phase 28's live measurement of about 123 s — neither
fallback, and therefore evidence that the derived branch does run in production.

### D5 — A walk that stops at its ceiling reports a silence, not a measurement

The break test reverted D3 and the gate answered `the page still says nothing
about the run 150s after it started`. True, and empty: it does not say which
clock the page is on, which is the entire content of the finding. The walk now
runs to 330 s — past every interval the page can return — so a red variant names
the delay. It answers `(285s, 300s]` against Phase 28's live 293 s: the fixture
reproduces the finding to within one step.

The answer is a WINDOW and is printed as one. A poller cannot say more than *not
at T-step, and yes by T*, which is the discipline ADR-0062 D3 had to correct
`watch-convergence.sh` into.

### D6 — The narrative is identified by its phase, not by its date

Phase 28 closed without touching `docs/discussion-log.md` or
`docs/next-phases.md`, and `make session-close` printed
`narrative 2026-08-11, matching the newest session`. Phase 27 had closed the same
day, so the dates agreed while the block described the wrong phase. Nothing else
in the repository reads that file — `make docs-check` does not — and the next
session reads the top of it for context.

Several sessions a day is normal here, so a date is a weak identifier, and it is
weakest on exactly the days when the most is happening. The check now reads the
phase from the INDEX row's second column and from the block's own parenthesis,
and only the token after `(` — so a long title may wrap without the check going
quiet, which is how its predecessor failed in 2026-08-08.

### D7 — A committed break script derives its anchors, because it is for a later session

`scripts/break-narrative-phase.sh` named `28` and `2026-08-11` as literals and
scored 8 of 8 in the sandbox. It scored **2 of 8 on the devbox an hour later**,
for the one reason that could not appear before the closing patch: this phase's
own Current state block went on top, so every mutation landed in a block BELOW
the one the check reads, and six working refusals were scored as failures.

Phase 27's argument for committing a break script is that *the next change to
this schema owes the same proof*. A script that only runs in the session that
wrote it cannot supply it. So the anchors are read — the newest date and phase
from the last INDEX row, the phase below from the file's second `**As of` line —
and the script refuses when it cannot read them, or when the two newest blocks
name the same phase and a mutation would be judged on the wrong one.

**It is proved by running it in the future**, with a synthetic later phase
COMMITTED rather than merely written: `restore` is `git checkout`, so an
uncommitted plant is reverted by the first variant, which is how the first
attempt at that probe scored 5 of 8 and blamed the script rather than the probe.

## Consequences

- `page-inflight-check` now takes about three browser passes instead of two. It
  is still a checkout-plus-playwright gate and still not in the cheap list that
  a plain checkout can run.
- The page's idle GitHub cadence changes from one request every five minutes to
  one every minute for the same hourly spend. If the anonymous budget is ever
  shared with something else on the same IP, the derived arithmetic slows both
  intervals down together, as it already did for the live one.
- Two more instrument defects are on the record, both found by the break test
  rather than by review, and both the same shape as the phase's subject: an
  instrument that reads part of what it is looking at. That makes six in this
  project. The pattern is stable enough to plan for: when a gate is written for a
  moving subject, budget a break test that will find something in the harness.
- `flightHere()` renames a lifted function, so `check-page-tense.mjs`'s API list
  and one case file move with it. A future rename of anything in a PAGE TENSE
  block has the same three places.
- NOT closed by this phase: the dashboard bucket's declared-and-not-applied
  versioning, and Phase 26's broken-word rule. Neither is about a moving page.
