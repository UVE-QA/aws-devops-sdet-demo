# ADR-0081: The run says which teardown it is, on the path where it does

## Status
Accepted (Phase 39, 2026-09-09). Narrows a premise written into
`runLayerStates()` in Phase 20c. Uses the per-node binding **ADR-0043 D1** built
for suites, unchanged. Follows **ADR-0080**, which is what made the map's
teardown pulse visible on the public path for the first time — and therefore
what made this visible.

## Context

The first button cycle whose prod phases pulsed showed phase 8 like this:

    8  Destroy   terraform   last time 7m 49s   18m 9s
       its phase is running
       DEL  stage — everything above   which node is unknown
       DEL  prod — everything above    which node is unknown

Both teardown nodes lit, for eighteen minutes, while stage had been gone for
fifteen of them and a five-minute hold sat in the middle.

The page's own comment predicted it and gave the reason:

> A live PHASE does not mean this node is doing anything. Destroy holds one node
> per environment and destroy.yml tears down one per run, so lighting the phase
> lit both … When the run does not say which environment it is about, both are
> lit: that is the honest rendering of "it could be either".

**The premise is false on the self-service path.** There the two teardowns are two
jobs with different names — `destroy / destroy` and `destroy-prod / destroy` — so
the run says exactly which. Same shape as ADR-0062's *nothing publishes until a
cycle ends*, which was true of the workflow it was written for and false of the
one that came later.

## Decision

**D1. Each teardown node binds its own job, and only where the run says which.**
`destroy.stage` → `self-service.yml :: destroy`, `destroy.prod` →
`self-service.yml :: destroy-prod`. No page change: `runLayerStates()` has
preferred a node's own binding over its phase's since ADR-0043 D1, marking it
`via: "own"`.

Only the self-service bindings are given. An owner-run `destroy.yml` takes the
environment as an **input**, so its job is called `destroy` whichever environment
it is tearing down and nothing in the run says which. That case still falls
through to the phase and still reads `which node is unknown` — which remains the
honest answer to *it could be either*.

**D2. A whole-level node may carry a binding, and it is optional.** The generator
resolved `live` for suite nodes only. A phase without a binding is refused,
because a phase that cannot pulse leaves a hole in a running map; a node without
one simply inherits its phase, which is a real and correct answer.

## Consequences

**The phase's own clock is still odd, and this does not fix it.** `18m 9s` runs
from the earliest bound step that started — stage's teardown — through the hold to
prod's. That is arguably what the *phase* is, and it is not what the figure beside
it measures.

`last time 7m 49s` comes from the published phase span, and this cycle published
**two of them under one key**:

    timeline/stage/nodes-destroy.json   destroy  468s  22:25:24 → 22:33:12
    timeline/prod/nodes-destroy.json    destroy  469s  19:45:14 → 19:53:03

`node-states.py` computes a phase span from one job's timeline, `publish-status.sh`
writes it per environment, and `readRunLayer()` folds both into `RUNSTATE.phases`
by the same id — last write wins, which is prod's, by the order `ENVS` happens to
be in. So the at-rest figure for phase 8 has always been **one of its two jobs,
chosen by fold order**, and the live clock is both plus a hold. The two numbers
have never measured the same thing.

Named, not fixed. The fix is in the fold rather than the page — a phase that runs
as two jobs needs a span that is their union, and `nodes: 1` in both documents
says neither knows about the other. That is its own decision.

**A binding that matches nothing is still indistinguishable from a phase that has
not started.** ADR-0080 said this and it is still true: nothing checks that a
binding ever matched a real job, and both of the last two findings were reached by
reading a live page rather than by any gate going red.
