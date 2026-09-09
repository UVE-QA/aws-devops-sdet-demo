# ADR-0080: A called job is named twice, and the map was using the wrong name

## Status
Accepted (Phase 39, 2026-09-09). Finishes **ADR-0068**, which converted the
promotion and the prod teardown into calls and left both their bindings — and the
stage teardown — behind. Found by watching a live cycle end to end, not by any
gate.

## Context

Cycle #15 ran clean: six jobs green, prod served 200 through its hold, both
progress documents removed, nothing billable left. Two things in its logs were
not clean.

**The stage teardown never prices its cycle.**

    destroy       no cost to publish (looked at: '<none>')
    destroy-prod  cost: prod — COMPUTED ESTIMATE, 3 priced, 27 free

`destroy-prod` *calls* `destroy.yml`. `self-service.yml`'s own `destroy` job was
a hand-written copy of it — sixteen steps against nineteen — and the copy was
missing exactly one: **`Price the cycle from its two timelines`**. So every cycle
the button has ever run priced prod and never priced stage, and the stage figure
on the page came from whatever owner-run `destroy.yml` last touched it (2026-09-05
at the time of writing).

**And the prod half of the map has never pulsed on the public path.** The phase
bindings name a workflow and a job:

    approve, prod-apply, prod-gate   promote-prod.yml :: promote
    destroy                          destroy.yml      :: destroy

`bindingState()` refuses a binding whose workflow is not the running one
(`run.path !== b.path`), and a button cycle's run *is* `self-service.yml`. So
during every self-service cycle those four phases matched nothing and stayed at
`not reached yet` from start to finish. ADR-0068 made them calls and this is the
half it did not carry over.

## Decision

**D1. The stage teardown calls `destroy.yml`, like the prod one.** 176 lines of
copy removed. Adding the missing step to the copy would have fixed the symptom
and left two definitions of what a teardown is — which is what produced the
symptom.

**D2. A called job's runtime name is DERIVED, never written down.** In the file
the job is `destroy`; in the Actions API — which is what `bindingState()` matches
on — it is `destroy / destroy`: the caller's key, then the callee's.
`assets/topology-groups.json` keeps the **file's** name, because that is the one a
rename can be caught against, and `scripts/generate-topology.py` reads the `uses:`
line and emits the runtime name into `site/data/topology.json`.

Writing the runtime name by hand was tried first and the generator refused it —
correctly, because `self-service.yml` has no job called `promote / promote`. That
refusal is the check that has been catching renamed steps since ADR-0043, and it
would have gone on being right while the file grew a string it could not verify.

A called job's steps are the **callee's**, so they are checked there. Checking
them against the caller refuses every call, which is precisely what happened the
moment the stage teardown became one.

**D3. The generator refuses a called workflow with more than one job**, rather
than guessing which one names the runtime job. Every callable workflow here has
exactly one; the day one does not, the refusal says so and asks for the name
explicitly.

## Consequences

**Not verified live.** The bindings are checked against the workflow files and
every gate is green, and none of that watches a cycle: what `bindingState()`
matches is a string the Actions API returns, and this decision asserts what that
string will be from the shape of the YAML. The next button cycle is the evidence,
and the thing to watch is whether phases 5–8 pulse.

**The gate that caught this caught it by refusing, not by failing.**
`site-data-check` went red the moment the stage teardown became a call, because
the phase named steps the caller no longer had. It had nothing to say about the
prod bindings, which had been silently matching nothing for four days — those
were found by reading the binding table while fixing the refusal. **A binding that
matches no job is indistinguishable from a phase that has not started**, and
nothing checks that a binding ever matched anything. That is the next gate worth
having, and it is not in this decision.
