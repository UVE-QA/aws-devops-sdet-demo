# 2026-08-09 — Phase 20l: the page re-reads its figures, and the gate found a second defect

The cursor's next allowed step, written by 20k: **the page re-reads its
figures.** $0, no cycle — and it stayed $0. Nothing was applied, nothing was
launched, no AWS API was called for anything but reading this document's own
claims.

Decisions in **ADR-0053**. Break-test output, all eight readings with the built
page's hash beside each one, in
`docs/sessions/2026-08-09-phase-20l-freshness-break-test.log`.

## What was wrong, and why it was four defects rather than one

20k found `readRunLayer()` called once, in the bootstrap chain, while `tick()`
re-read `status/*.json` and the Actions API every 30 seconds. Reading the code to
fix it turned one root into four, and **each one alone would have been invisible
on the page** — a fix that addressed any three of them would have looked exactly
like no fix at all:

```text
1  the run layer was never re-read              the finding as 20k wrote it
2  readRunLayer() ACCUMULATED - four pushes     a second call duplicates the
   and a merge                                  cycle list and the ledger
3  the re-render signature had no figures in    a price arriving changes no
   it: states only                              state, so nothing redraws
4  the sentence under the map and the cut       fresh numbers under a stale
   below it were written in the bootstrap       date, which is the same defect
   chain                                        one level up
```

(2) is the one that makes this a decision rather than a patch: calling the
existing function on a timer would have doubled the `unknown` ledger every 30
seconds. (3) is the one that would have been quietest — the fetch in the network
tab, the numbers in memory, and the same page on the screen.

Beside them, 20k's mirror clause: a node has no record until its cycle ENDS, so
during a run every phase ahead of the front said `not run yet` — what a phase
that never ran says. It now says `not reached yet` when a cycle is under way and
is about that environment. `underWayHere()` decides that from the run's own
environment list, handed over rather than re-derived.

And one thing the page cannot fix, now stated on it: these objects are published
`max-age=60` with no invalidation, deliberately, so a figure arrives up to a
minute after it is written whatever this timer does. The line beside Refresh says
so. Leaving it unsaid was how 20k's reader came to trust "bucket every 30 s" for
figures it did not cover.

## The gate

`make page-freshness-check`. Freshness is not a property of a liftable block —
`check-page-tense.mjs` and `check-live-state.mjs` can say what the page ANSWERS,
neither can say when it asks — so this one drives the built page in chromium on
measure-page.mjs's harness, and unlike measure-page it has a verdict.

Its property is the reload that fixed all four of 20k's symptoms:

```text
A TAB LEFT OPEN CONVERGES ON WHAT A FRESH LOAD OF THE SAME SOURCES SHOWS.
```

Three cases — one bucket tick on a pushed clock, the Refresh button, three ticks
in a row — each opening on one run-layer set, swapping the bucket underneath the
tab, and comparing against a cold load of the second set.

**Counting requests was rejected on purpose.** A page can re-fetch and decline to
draw; that is defect (3) above, and a request count would have called it green.

## The break test, and the one that failed to break

Eight readings, each with the built page's own hash, because a variant has to be
MEASURED rather than assumed different — 20j spent a session on four break tests
that were byte-identical to each other.

```text
B0  nothing broken                                        exit 0   f42d1d59
B1  readRunLayer() off the tick - 20k's defect            exit 1   3d79d561
B2  the figures half of the signature deleted             exit 1   c775e01d
B3  the layer appends instead of being rebuilt            exit 1   420470ea
B4  renderMapSub() not called by the re-read              exit 2   8648e471
B5  the first observation dropped again                   exit 1   235d789c
R1  the two fixture sets stop differing                   exit 2   f42d1d59
R2  a request nobody declared                             exit 2   11aba83a
```

Before any of that, the gate had already gone red on the REAL defect: written
against the unfixed page it failed all three cases, and the failures named `map`
as still showing what was published before the cycle. A gate whose first reading
is on a genuine defect rather than a planted one is the strongest form of this
that this project has managed.

**B4 was green on the first attempt, and the gate was wrong, not the break.**
With the map's sentence unhooked from the re-read, that region holds the same
static markup in both sessions — it converges trivially, and its silence reads as
agreement. The control asked whether the two sets rendered differently ANYWHERE.
It now names four regions and refuses if any of them cannot move (ADR-0053 D8),
and B4 refuses. A region that cannot move cannot testify: the same shape as 20a's
`scrollWidth` on the document, which was green about a box that never reached it.

**One measurement error of my own, caught by re-reading the numbers rather than
the code.** The first full sweep had B2, B3, B5 and R2 all reporting exit 2, which
read like four breaks landing on the control. They were not: the restore step in
the throwaway harness reverted the FIXTURE along with the page, so every case
after the first ran against fixtures whose ledger no longer moved, and the
control refused for that reason alone. The readings were indistinguishable from
real ones. What settled it was that B0 had passed with the same fixture the
others refused on.

## Found by the gate, not by anyone watching

Its first green attempt was not green: the open tab and the fresh load disagreed
about the map, and neither was stale — the open tab said `destroyed`, the fresh
load said `measured`, and the FRESH LOAD was the wrong one.

The dashboard announces its first observation from `load()`, which fires before
`topology.json` and the run layer come back. The map's listener starts with
`if (!DATA) return`, so that first observation was dropped, and the next one is a
bucket tick away. **For 30 seconds after a cold load, every node of a destroyed
environment was drawn as though it still stood** — the exact claim ADR-0051's
destroy rule exists to prevent. Held and replayed now.

Nobody was looking for this, and 20k could not have seen it: there the reload was
the FIX, so nobody asked what the reload itself showed. Comparing an open tab
against a fresh load asks that question by construction.

## Files

```text
assets/index.template.html                     the page; site/index.html rebuilt
scripts/check-page-freshness.mjs               new gate
scripts/check-page-tense.mjs                   underWayHere() in its API list
Makefile                                       page-freshness-check
.github/workflows/ci.yml                       in local-ci, beside contrast-check
tests/fixtures/page-freshness/                 sources/, before/, after/
tests/fixtures/page-tense/cases/               two new cases, 33 calls in all
docs/decisions/0053-the-page-re-reads-what-it-draws.md
README.md                                      the two page gates the list omitted
```

## Validation

```bash
make site-page-check site-data-check docs-check
make page-tense-check
make live-state-check
make page-freshness-check
```

All green. `page-freshness-check` needs chromium: on a machine whose build is not
the pinned one, `CHROMIUM_PATH=` as for `measure-page` and `contrast-check`.

## Cost

**$0.** No environment was created, no workflow was dispatched, no cycle was
ordered. The next cycle will exercise this against real records for free.

## Next

The cursor's next allowed step is **a live cycle with the tab left open** — the
first one that can confirm any of this outside a fixture, and the first that will
see `not reached yet` on a phase a run has not reached. It is BILLABLE and is
planned and confirmed before anything runs. Everything above is gated on
fixtures; what no gate here can see is the ceiling in D9 — whether a minute of
CloudFront TTL reads as "converging" or as "broken" to somebody watching.
