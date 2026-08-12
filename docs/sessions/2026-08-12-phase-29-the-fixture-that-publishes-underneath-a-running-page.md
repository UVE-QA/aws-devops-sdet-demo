# Phase 29 — The fixture that publishes underneath a running page

**2026-08-12. $0, nothing applied, no cycle, no AWS call.** Taken entirely in the
chat session's sandbox on chromium-1194, with the devbox re-running the gates at
close. **ADR-0063.**

`main` was green when this session started: `ci #31467525289` and
`publish-site #31467525301` on `cc2b304`, checked before anything was touched.

## What the cursor asked for, and what was found on the way to it

The next allowed step was the fixture. Loading state for it found two documents
that Phase 28 had left behind, and a gate that had let them.

### Two stale documents, and the check that was green over them

`docs/discussion-log.md`'s newest Current state block was Phase **27**'s. No
Phase 28 commit touched the file, and none touched `docs/next-phases.md` either
— whose "Still open" list still named all three items Phase 28 had closed.

`make session-close` printed `narrative 2026-08-11, matching the newest session`.
It compares the DATE. Phase 27 closed on 2026-08-11 and so did Phase 28, so the
check was green over a block describing the wrong phase. Nothing else in the
repository reads that file; the next session reads the top of it for context.

Fixed in the same commit as the documents, per the project's own rule about
fixing a shared invariant everywhere at once: the check now reads the phase from
the INDEX row's second column and from the block's own parenthesis (ADR-0063 D6).
Eight variants in `scripts/break-narrative-phase.sh`, committed rather than typed
into a session, because the subject is a convention spread across two documents
that nothing else compares — which is a schema.

**[B] is the defect itself, not a simulation:** it puts the repository back into
the state `main` was in on 2026-08-11.

**[E] failed on the first run and the gate was blameless.** The harness's own
filter matched the second line of the date refusal and not the first, which is
the line naming the two dates. An instrument that reads part of the right line —
the phase's subject, arriving in its first hour. In the log rather than quietly
widened.

## The fixture

`tests/fixtures/page-inflight/` gains two things that are never loaded as states:
`layer-published/`, an overlay holding the one document `deploy-stage #64` writes
from a step inside its own job, and `new-run/`, at-rest plus one queued run.

The gate loads the page ONCE and changes a source underneath it — the bucket in
one pass, the API in the other. A sentinel on `window` is required to survive to
the second reading, so a reload cannot be mistaken for a re-read. The clock is
installed rather than fixed.

**The entry was red on a page nobody had touched**, and the numbers are the
evidence: the same seven nodes, the same open tab, the figures changing
underneath a sentence that did not.

```text
stage.rds   measured · these figures are from the cycle before this one · 4m 47s
            measured · these figures are from the cycle before this one · 4m 11s
```

And after the fix, from the same instrument:

```text
stage.rds   measured · these figures are from the cycle before this one · 4m 47s
            measured · these figures are from the cycle under way · 4m 11s
```

**The gate did not merely miss ADR-0062 D1 — its third claim asserted it**, in a
comment stating the premise Phase 28 disproved. Fixing the page would have
reddened it.

## The two findings, implemented

**D1** is three changes and one predicate (ADR-0063 D2): `readRunLayer()` carries
`published_by`, `underWayHere()` becomes `flightHere()` and answers with the run
rather than with a yes, and `nodeTense()` compares the two. The suite half
already had the right predicate — Phase 25 wrote it two functions below and
nobody looked up.

**D2** is an interval derived from the budget instead of from what the page
already knows, floor 60 s, and it is paid for rather than borrowed: the steps of
a finished run cannot change, so an idle poll now costs one request instead of
two, and 60 an hour is one a minute. ADR-0062 said this cost was unpriced. It is
priced, and it is zero.

```text
sequence: first news in (45s, 60s], 2 GitHub requests spent getting it
```

## The instrument was wrong twice, and both are recorded

**The first reading of D2 was of the wrong branch.** It said `(105s, 120s]`,
which is neither the old constant nor the new floor — it is the fallback for *the
budget could not be read*. `api.github.com` is a different origin, the mock never
sent `access-control-expose-headers`, and `r.headers.get()` had returned null for
both ratelimit headers since this gate was written. Every reading it had ever
taken was of the page's fallback branch.

Two independent things settled it rather than one: the page's own advertised
cadence read back off the DOM, equal to a fallback constant; and Phase 28's live
measurement of about 123 s, which is neither fallback and is therefore evidence
that the derived branch runs in production. The gate refuses now (ADR-0063 D4).

**And the walk stopped at its ceiling**, so the red variant could only report
`still says nothing about the run 150s after it started` — true, and empty. It
runs to 330 s now and names the delay: `(285s, 300s]`, against Phase 28's live
293 s on `destroy prod #46`. The fixture reproduces the live finding to within
one step of the walk (ADR-0063 D5).

**Checked that the instrument was not setting the answer**, before believing any
of it: the walk was run at 120, 400 and 900 ms of settle per step and returned
the same window at all three.

## Break tests

Seven variants in `scripts/break-page-inflight-sequence.sh`, controls green
either side, tree committed before each. Two page defects for D1 — by DIFFERENT
mechanisms, the comparison disabled and the fold not carrying the id, the second
being the shape the real defect had — one for D2, and two instrument defects that
must REFUSE rather than answer: the mock not exposing the budget, and an overlay
that moves nothing.

Eight more in `scripts/break-narrative-phase.sh`. Fifteen in the session, and two
of them found something.

Not covered, deliberately: the reload sentinel. Breaking it means editing the
gate's own navigation, and a variant that rewrites the measurement to fail is not
evidence about the measurement.

## The devbox found a third one

`break-narrative-phase.sh` scored 8 of 8 in the sandbox and **2 of 8 on the
devbox**, an hour later, for the one reason that could not exist earlier: this
phase's own Current state block went on top of the file. The script named `28`
and `2026-08-11` as literals, so every mutation landed in a block BELOW the one
the check reads and six working refusals were scored as failures.

It failed loudly, which is the good outcome, and it is the wrong failure to
settle for. A break script is committed rather than typed so a LATER session can
re-run it; this one could not have been. The anchors are derived now, with two
refusals of their own, and the fix was proved by running it in the future — a
synthetic phase 30, COMMITTED, because `restore` is `git checkout` and an
uncommitted plant is reverted by the first variant. That mistake was made first
and scored 5 of 8 before the probe itself was fixed (ADR-0063 D7).

Third instrument defect in one phase, all three the same shape: the log filter
that read one line of two, the walk that stopped at its own ceiling, and a
mutation aimed at the wrong block. Not one of them was in the page.

## Validation

```text
make gates                    12/12 green
contrast-check                7 states, 3 ancestries, both themes
page-freshness-check          3 cases
page-tense-check              16 cases, 49 calls
page-inflight-check           every claim held, in both states, plus both sequences
break-narrative-phase.sh      8 of 8 (2 of 8 on the devbox first; see above)
break-page-inflight-sequence  7 of 7, on BOTH hosts, every number identical
                              including (45s, 60s] and [D]'s (285s, 300s]
```

## What this phase did not close

The dashboard bucket's declared-and-not-applied versioning, and Phase 26's
broken-word rule with its two desktop false positives. Neither is about a moving
page; both can be taken cold.
