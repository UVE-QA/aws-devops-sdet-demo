# Phase 25 — A figure names its cycle, and the instrument had never seen one

**2026-08-11. $0 — no AWS call, no cycle, nothing applied.**
**ADR-0059.** Break-test output in
`docs/sessions/2026-08-11-phase-25-inflight-break-test.log`.

**Main was green when this session started** — `ci #198` and `publish-site #35`
on `e7f00e1`, checked before anything was touched. Phase 22 is why that is the
first line of every summary now.

## What this session established

The page tells the truth while a cycle is running, and a gate holds it there.
`make page-inflight-check` renders the whole built page over a fixture holding a
cycle mid-flight and reads the sentences a visitor reads — the first gate here
whose subject is the page in a state that is not rest.

Four findings closed, one of them new. And one found on the way that is about the
instrument rather than the page, and is larger than any of them.

## The gate was red before anything was fixed

Entry `[0]` in the break-test log is `make page-inflight-check` against the page
as it stood: two claims down, three findings named, `exit=1`.

That is a stronger entry than any of the nine breaks that follow it. A
reintroduced defect proves a gate reacts to an edit. A defect that was already
there — and that 20m had watched a live cycle print for twelve measured minutes —
proves it reacts to the thing.

## Why nothing had seen these

The functions were correct. `nodeTense()` has fourteen cases and forty-two calls
in `check-page-tense.mjs`, all green, for three phases, while the page was wrong
— because during a run the renderer consults the run layer first and never
reaches the function.

A gate aimed at a correct function cannot see the branch that skips it. Third
time in this repository: a document-level overflow measurement could not see a
box that overflows its parent (20a), and a fingerprint comparison could not see
two pages agreeing on the same wrong caption (20m).

## The four findings

```text
1  the run-history badge counted unfinished runs as successes
   Fixed in Phase 22. Never demonstrated on a page until now, because no
   fixture had a history that was green APART FROM the run in flight.

2  a node nothing can ever measure promised figures
   `build.ecr` read `finished in this run · figures publish when the cycle
   ends`. Terraform reports resources; the image push is not one. The run
   layer's word about the step is kept; the clause about what can measure the
   node now travels with it, in all three run-layer branches.

3  a figure drawn during a run was printed unqualified
   Seven stage nodes and `destroy.stage`, each with the previous cycle's
   figures and nothing saying so. `nodeTense()` gains the under-way branch:
   `measured · 4m 47s · these figures are from the cycle before this one`.

4  NEW, and found by the fixture: every prod verdict read `from the previous
   run` during a stage deploy that never touches prod
   `result_previous` asked whether a run was in flight and not whether it was
   about this environment. The exact mirror of 3 — the node half asked neither
   question, the suite half asked only the first — and one predicate,
   `underWayHere()`, fixes both. One missing question, not two bugs.
```

## The prediction was wrong, and in a useful direction

The cursor said, twice, to expect the GATE to be the hard part. The gate took an
afternoon. The FIXTURE found three things, because building it meant asking what
the page actually reads rather than what it appears to read.

## The instrument had never measured a page with figures on it

`measure-page.mjs` mocks the three sources the sandbox cannot reach and guards
itself by recording every request that LEAVES the origin. The run layer does not
leave the origin: ten relative paths under the page's own host, published into
the bucket by `publish-status.sh`, absent from `site/` in the repository.

Measured rather than reasoned about: **ten 404s per fixture, on BOTH sets, with
`unmocked` empty and no banner drawn.** `readJSON` folds a 404 into `null` and
the page renders quietly — every node reading `not run yet`, not one figure
printed anywhere.

Its own docstring names the thing it does not do: *"measured with them
unreachable the page renders its banners and its 'no observation' panels, and is
SHORTER than the page a visitor gets"*. It fixed that for the remote three and
left it in place for these ten.

So every layout figure this project has argued from since 20e — ADR-0058 D6's
2039 → 3116px and 1.9 → 2.9 screens, 20j's 18.5rem floor — measured the short
bodies. **How much shorter is not measured**, and guessing it here would be the
same species of error the finding is about. Phase 26.

`check-page-inflight.mjs` refuses on an origin 404 for exactly this reason.

## The break tests

Nine, plus a control either side, with the tree committed before each one and
verified clean after it. Each break was checked to have actually changed the
BUILT page before its reading was believed — a break measured through an
unchanged artifact measures the artifact (2026-08-08).

```text
[0]      the gate on the unfixed page                      exit 1
[1]-[4]  each finding reintroduced alone, after the fix    exit 1 each
[5]-[9]  the five refusals                                 exit 2 each
```

`[5]` is the one worth reading: with the run layer taken away the page renders
quietly, prints no figure and draws no banner — the state both `page-measure`
sets are permanently in.

`[7]` is recorded as it happened rather than as it was meant. The break written
to exercise `controlDiffers()` never reached it: the fixture audit objected
first, on the disagreement between the meta and the history. `[9]` is the one
that reaches it. Same family as the 2026-07-28 break test that failed to break —
there a green reading hid a rule that did not match; here a red reading credited
one check with another's refusal, exactly as in Phase 24.

## Where the break tests were taken

Not the usual place. The chat session ran them in its own sandbox, against its
own clone, on chromium-1194 rather than the build Playwright 1.62 pins. The
devbox re-ran the gate green and refusal `[5]` red, identically; the four defect
breaks were not re-run there. The log says so in its own header, because `one
definition, two hosts` has cost this project a scan of `postgres:16` already.

## Files

```text
tests/fixtures/page-inflight/         the fixture: one run layer, two states
scripts/check-page-inflight.mjs       the gate
Makefile, assets/gates.json, ci.yml   one row, one target, one step
assets/index.template.html            three clauses and data-id; site/index.html rebuilt
tests/fixtures/page-tense/cases/...   one case for the new branch, with the
                                      mirror clause beside it as a control
docs/decisions/0059-...md             the ADR
```

## Cost

Nothing. No AWS call, no cycle, nothing applied. The published page changes, so
the next push to `main` republishes it.

## Next

**Phase 26 — the instrument measures a page that has figures on it.** Serve the
run layer to `measure-page.mjs`, refuse on an origin 404 there too, and remeasure
ADR-0050, ADR-0052 and ADR-0058 D6 against the same instrument on the same
commits. $0.

Phase 27 — the contrast contract's second ancestry — is still carried, and is
the smaller of the two.
