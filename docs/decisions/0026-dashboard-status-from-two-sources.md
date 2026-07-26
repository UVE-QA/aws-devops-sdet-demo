# ADR-0026: Dashboard status comes from two sources, each authoritative only for what it observes

## Status
Accepted (Phase 11.1). Implements the open question left by `docs/next-phases.md`
Phase 11.1. Depends on ADR-0022 (the repository is public).

## Context

The dashboard has to answer two different questions that look like one:

```text
Where is the current cycle?     which stage of which run is planned, running, done
What exists in AWS right now?   is stage up, is prod up, or is everything destroyed
```

They feel adjacent and they have different sources of truth. GitHub Actions
knows everything about the first and **nothing** about the second: the most it
can say is that the last `destroy` run ended green, which is a statement about a
workflow, not about an account. An environment can be gone because a run
destroyed it, or because someone destroyed it by hand, or it can still be there
because the run went green and something was recreated afterwards. Conversely,
a file written by a workflow cannot report that a run is *in progress*, because
by the time anything is written the run has already got that far.

The project has been bitten twice by exactly this confusion — a claim standing in
for an observation. `promote-prod.yml` said "read-only smoke" and ran the whole
test directory (ADR-0025); a post-teardown check with an expired token printed
empty lists that were indistinguishable from a clean account. Both were sources
asserting something they were not in a position to know.

Because the repository is public (ADR-0022), the GitHub REST API can be read
anonymously from the browser: no token, no backend of our own, nothing to keep
in sync. That removes the reason the two options ever competed.

## Decision

**Both sources, split strictly by what each one observes.**

```text
GitHub Actions REST API, read anonymously from the browser
    run history, per-job and per-step status, durations, links to runs.
    Live by construction. No token, no server, nothing cached server-side.

status.json in the site bucket, written by the workflows
    the state of each environment in AWS, the digest of the image prod is
    running, and the URL of the published Playwright report.
```

The rule that settles every future addition:

> A source may only assert what it observes. Actions may not claim an
> environment is destroyed. `status.json` may not claim a run is in progress.

No credential ever reaches the browser, and no human writes either source by
hand.

## What keeps status.json honest

A file written at the end of a run goes stale the moment a run dies before
writing it, and a stale file that renders as fact is the failure mode this
project keeps rediscovering. Three properties, all required:

- it is written in a step that runs unconditionally at the end of
  `deploy-stage`, `promote-prod` and `destroy`, not only on success;
- it carries the id and the finish timestamp of the run that wrote it;
- **the page compares that run id against the newest run it just read from the
  GitHub API.** If the newest run is younger than the file, the environment
  panel renders "unknown", naming the run that has not reported. It does not
  render the last known value as though it were current.

That last property is what makes the two sources worth more together than
separately: each one is the other's staleness detector, and neither can go
quietly wrong on its own.

## Consequences

- The unauthenticated GitHub REST API is rate-limited to 60 requests per hour
  per IP. Accepted. The dashboard reads few endpoints, caches in the browser,
  and on a 403 renders "run history temporarily unavailable" — visibly, as a
  degraded state, never as an empty history. An empty result is not a clean
  result.
- Writing `status.json` costs a step in three workflows and requires one narrow
  publish role, scoped to the site bucket and the distribution and nothing else.
  It is written in Phase 11.1a and applied in 11.1b.
- Run history depends on the repository staying public. That is a real, visible
  coupling to ADR-0022 rather than a hidden one: making the repository private
  again breaks the history panel, and the panel says so rather than emptying.
- The dashboard displays two clocks — GitHub's and the bucket's. That is
  deliberate: a viewer can see not just the state but how recently each half was
  confirmed.
