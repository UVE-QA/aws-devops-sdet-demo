# ADR-0088: The public path runs the same suites, and gives the environment back

## Status
Accepted (Phase 40, 2026-09-12). Reverses the *smoke only* half of **ADR-0068**'s
unattended cycle. Does not touch its IAM shape, its quota, its lock or its TTL.
**ADR-0025**'s read-only/destructive split is unchanged and is what makes this
safe to do on stage and still refuse on prod.

## Context

`self-service.yml` ran one suite against stage: Playwright's `smoke`, four tests
with `db-assert`. The reason was written in the workflow and it was a good one:

> a public launch is a demonstration under a deadline, and the visitor gets a
> working environment rather than one a test suite has been writing to.

What that sentence did not price is what the promotion is conditioned on. The
`promote` job runs `if: needs.launch.result == 'success'`, and **success meant
those four tests**. The owner's own path through `deploy-stage.yml` puts sixty-six
behind the same word — the API contract suite, the destructive UI regression, and
the assertion that the browser's write reached RDS from inside the VPC.

So the public path promoted a digest to production on a weaker proof than the
manual one, and the page said nothing about it. Worse, it said something else:
the two suites that never ran were drawn as *not reported — the previous run
here did not report this suite*, which is the vocabulary of a LOST report used
for a deliberate omission (the defect **ADR-0071** named and did not reach).

The owner, asked why smoke only and what it buys:

> делай полный набор с пересидом

## Decision

**D1. The public cycle runs what the owner's cycle runs.** `API contract tests
against the ALB`, `Playwright smoke + regression against the ALB` and `Assert the
UI write reached RDS`, the same three steps with the same names as
`deploy-stage.yml` — so the map's bindings name one set of steps for two
workflows rather than describing two different gates.

Both Playwright projects are named explicitly, for the reason deploy-stage gives:
a bare `playwright test` adopts any future project, which is how prod nearly
inherited the destructive suite.

**D2. The environment is given back, and that is what pays for D1.** The suites
clean up after themselves except for the two probes `items.spec.ts` leaves on
purpose for the RDS assertion. A step after the assertion removes them through
the application's own API — the same door the browser used — re-runs `seed` and
re-runs `db-assert`. What a visitor opens is the seeded demo, which is the
property ADR-0068's sentence was protecting, bought for about a minute instead of
with sixty-two tests.

**Not `if: always()`.** A failed suite leaves its evidence standing; tidying up
after a failure is how a failure gets lost.

**D3. prod still runs the read-only pair, and this changes nothing there.** The
destructive suites are destructive by directory (ADR-0025), prod's gate names
`db` and `smoke`, and a public visitor writing test rows into the production
database through a promoted digest is not a trade anyone offered. The asymmetry
between the environments stays, and it is now the only asymmetry: stage is the
same on both paths.

## Consequences

- A cycle grows by roughly three minutes: ~52 becomes ~55. The estimate beside
  the button is a median of measured runs (ADR-0087), so it moves there on its
  own after four cycles and nobody has to remember to change a number.
- The promotion gate is now the same on both paths, which is the sentence the
  README has always made about this pipeline and did not have behind the public
  half of it.
- Two suite tiles stop reading *not reported* in every public cycle. The wording
  ADR-0071 objected to survives for the case it was actually about — a suite a
  cycle genuinely does not run — and prod is where that case lives.
- The probe removal talks to the app over HTTP from the runner, which is the
  first time this workflow does that for a reason other than testing. It is one
  page of items (100, the API's own ceiling) in an environment minutes old; if a
  row ever fell past it, the seed assertion still passes and a probe outlives the
  cycle by twenty minutes.
- `UI_PROBE_NAME` and `UI_EDIT_PROBE_NAME` are job-level here as they are in
  deploy-stage: three steps read them and a value repeated in three places can
  disagree with itself.
