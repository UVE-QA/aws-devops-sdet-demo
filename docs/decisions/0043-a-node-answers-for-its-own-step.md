# ADR-0043: A node answers for its own step, and the page says what it does not know

## Status
Accepted (Phase 20c, 2026-08-08). Completes ADR-0042, which collected the
suites and folded their reports onto the map's nodes and stopped there — the
page read neither. Narrows ADR-0039 D4, which made liveness a property of a
PHASE.

## Context
After ADR-0042 the repository knew, and the page did not. 180 tests collected
from the suites themselves sat in `site/data/suites.json`; a real cycle's
verdicts sat in `results/stage/latest.json`, published by the run that produced
them; and `site/index.html` fetched neither. Everything that phase established
was true and invisible.

Watching that cycle also produced three observations about the map that no gate
could have found, because all three are about a page rendering an observation
nobody had recorded:

```text
1  every node of a running phase said "running now" while Terraform was
   creating exactly one of them
2  a phase that had FINISHED fell back to "nothing recorded yet" - the sentence
   a phase that has never run shows - because the figures publish at the END of
   the cycle
3  suite.db.stage is drawn in the quality gate and its step runs in Provision,
   so it lit during tests it takes no part in. prod does not have this problem:
   its gate phase binds the db step, so the same suite behaved differently in
   the two environments
```

The three look like rendering bugs. They are one structural mistake: **liveness
was attached to the box a node is drawn in, and a box is a layout decision.**

## Decision

### D1 — a suite node carries its own `live` binding, checked like a phase's
`assets/topology-groups.json` gains a `live` block per suite node, in exactly the
shape a phase already uses, and `scripts/generate-topology.py` resolves and
verifies it with the same code: the workflow must exist, the job must exist, and
every step named must exist in that job. A suite node with no binding is a
refusal, for the reason a phase with none already is — something that can never
pulse is a hole in the picture, and a hole is invisible.

Where a node is DRAWN stays a layout question. What it is doing is answered by
the step that produces its report:

```text
suite.db.stage          Run one-off tasks (migrate, seed, db-assert)   [Provision]
suite.api.stage         API contract tests against the ALB             [gate]
suite.regression.stage  Playwright smoke + regression, and the UI-write assertion
suite.smoke.stage       Playwright smoke + regression / Playwright smoke (self-service)
suite.db.prod           Provision the prod database (migrate, seed, db-assert)
suite.smoke.prod        Read-only smoke against prod
```

stage and prod stop disagreeing because neither is guessing any more.

### D2 — a node without a step of its own inherits, and SAYS it inherited
ADR-0039 D4's limit stands: per-resource liveness would need the timeline
published during the apply, by the step holding the deploy role, and ADR-0026
keeps that credential away from the bucket that reports on it. So a node with no
binding takes its phase's state — and is marked `via: "phase"`, which the page
renders as *its phase is running, and which node is not published until the cycle
ends*. The pulse is reserved for a node that owns a running step.

Three states, not two. `running`, `failed` and `finished` — where finished means
*in the run that is still going*, whose figures publish at the end. Without the
third, a phase that finished thirty seconds ago is drawn exactly like one that
has never run, which is what observation 2 was.

A COMPLETED run reports none of them. Its publish step has already written the
figures and the reports, so those are the better answer, and "finished in this
run" would otherwise sit over the top of real measurements until somebody
started another cycle — which on a demo torn down between cycles is most days.

### D3 — the one fold that cannot move to Python is gated where it lives
`node-states.py` and `fold-results.py` run on the runner because a join written
twice is one definition on two hosts, and this project has paid for that once
already. This logic cannot follow them: it reads the Actions API live, in the
visitor's browser, and there is no run afterwards to fold.

So instead of a second copy, `scripts/check-live-state.mjs` lifts the marked
block **out of the built page** and runs it, verbatim, against recorded
observations:

```text
site/index.html    ==== RUN-LAYER STATE MACHINE - begin ====
                     bindingState(observation, bindings)
                     runLayerStates(observation, phases)
                   ==== RUN-LAYER STATE MACHINE - end ====
```

The markers are load-bearing and the gate refuses if either has gone missing —
a gate that quietly found nothing to check is the empty result that reads as
clean. The phases it folds against are a FROZEN snapshot, for the reason
`check-results.py` freezes its inventory: this gate is about the state machine,
and one that read the live map would redden when a node was added and teach the
person who added it that the fixture is stale.

Because it reads the BUILT page it also fails on a template edited without
rebuilding — `site-page-check`'s property, arriving here for free, and the way
the first run of these fixtures went red.

### D4 — what the page does not know, it names
The suite half of the map is read from two files and nothing is joined on the
page: `fold-results.py` already did the join, onto ids it looked up in the same
topology the page draws.

```text
a verdict        passed / failed / incomplete, with per-status counts and the
                 suite's own duration
not reported     the run did not report this suite. ADR-0025 drawn: regression
                 and the API contract cannot reach prod, and a self-service
                 launch runs smoke alone
not run yet      no run has reported at all - with the COLLECTED test count,
                 never a file count
from the previous run
                 a verdict published by an earlier run while another is in
                 flight. The report carries the run that wrote it, so this is
                 checkable rather than assumed
```

## Consequences
- A step rename now breaks the build twice as loudly: phases and suite nodes are
  both checked against the workflow, and both refuse.
- The map has a third source. `timeline/` says what Terraform did, `results/`
  says what the suites said, and the Actions API says what is happening now.
  They are published on different rules and are never merged into one date.
- `make live-state-check` needs Node. It is preinstalled on the runner image and
  the block is plain ES2015, so there is no setup step and no version to pin —
  but a machine without Node cannot run this gate.
- The phase clock changed while this was being written: it used to restart every
  time the apply moved from one bound step to the next, so a four-minute phase
  read as ten seconds old. It now runs from the first bound step that started.
  Found writing the gate, not watching the cycle.
- Nothing here costs anything. No AWS call, no cycle, and the whole session was
  checked offline against fixtures and a headless render.
