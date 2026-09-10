# ADR-0083: A phase that runs as two jobs has one span

## Status
Accepted (Phase 39, 2026-09-10). Fixes what **ADR-0081**'s Consequences named and
declined to fix. Reuses **ADR-0062 D1**'s predicate for the third time.

## Context

ADR-0081 fixed the two teardown *nodes* and left the *phase's* figure alone,
with the reason written down:

    timeline/stage/nodes-destroy.json   destroy  468s  22:25:24 → 22:33:12
    timeline/prod/nodes-destroy.json    destroy  469s  19:45:14 → 19:53:03

`node-states.py` computes a phase span from **one job's** timeline,
`publish-status.sh` writes it per environment, and `readRunLayer()` folded both
into `RUNSTATE.phases` under the same id — last write wins.

So `last time 7m 49s` beside phase 8 was **one of its two teardowns, chosen by
the order of the `ENVS` array**, while the live clock beside it read eighteen
minutes because that one runs from the first bound step to now. The two numbers
had never measured the same thing, and nothing about the page said which job the
figure came from.

## Decision

**D1. Two spans under one key are merged when both documents name the same run.**
Not *is this the same phase* but *does this document belong to the same cycle* —
ADR-0062 D1's predicate, which has now fixed a node's figures, a node's binding
and a phase's span.

**D2. The merge is the union: earliest start to latest end.** For phase 8 in a
self-service cycle that is stage's teardown, the five-minute hold, and prod's —
and it **includes the hold**, deliberately. The live clock includes it, and a
span that excluded the wait would be a truer description of the work and a second
number that disagrees with the clock beside it, which is the defect being fixed.

The title says so: *measured on 2026-08-10, across 2 jobs of one cycle — first
start to last end, so a wait between them is inside it*. A merged figure that
looked like a single job's would be worse than the fold order it replaced.

**D3. From different runs, the one that finished LAST wins.** That is the owner's
path — each environment torn down by its own dispatch of `destroy.yml`, which are
not one cycle and must not be added together. It is what the page already showed,
except that it showed it by accident; now it is a rule.

**D4. A duration is recomputed only when both ends are readable**, otherwise the
existing one is kept. A merge that guessed would be exactly the plausible number
this page keeps refusing.

## Consequences

`scripts/read-phase-span.mjs` prints what the page draws beside a phase, and
`scripts/break-phase-span-merge.sh` runs four variants over it:

    [A] as committed - two dispatches, two runs      12m 5s   one teardown
    [B] both documents named one run                 32m 8s   the union
    [C] [B]'s fixture with the merge removed         12m 5s   one teardown
    [D] control, restored                            12m 5s

[C] is the one that matters: same fixture as [B], merge taken out, and the union
disappears. Without it [B] would prove only that the number changed.

**Not verified live.** The fixture's two documents name different runs — it
models the owner's path — so the merge branch is exercised by a patched copy and
not by a cycle. The next button cycle is the evidence, and the figure to watch is
phase 8's: it should read about twenty-five minutes, not eight.

**The runner still does not know a phase can be two jobs.** Both documents carry
`nodes: 1` and neither mentions the other; the union is arithmetic the page does
over what they publish. That is the right place for it — the page is the only
thing that sees both documents — but it means `node-states.py` cannot check the
claim, and neither can any gate that reads one document at a time.
