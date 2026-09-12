# ADR-0093: The page reports the released line, and the work happens beside it

## Status
Accepted (Phase 40, 2026-09-12). A process decision with one line of code
behind it. Narrows nothing; adds a rule every later phase works under.

## Context

The dashboard is being handed to recruiters. Until today, development and the
exhibit were physically the same thing: a push to `main` republished the page
within a minute, and the public button dispatches `self-service.yml` from
`main`, so a half-finished workflow was on the public path the moment it was
committed. The owner:

> будет неудобно если они вдруг наткнутся на не работающее демо. надо как-то
> разнести разработку и текущее рабочее демо

Three things had to come apart, and they are different sizes.

**The code.** A branch. Trivial, and not sufficient on its own.

**The runs.** Every workflow here can be dispatched from any branch, and a cycle
dispatched from a working branch is a real run in the same account, against the
same `stage` and `prod`, holding the same `concurrency` group. The page reads the
forty most recent runs from the Actions API and used to show all of them: a
failed experiment from `next` would land at the top of the history as a red row,
turn the verdict badge red, and become *the step in flight* — on the page a
stranger was handed a link to.

**The environments.** `stage` and `prod` are one set. A cycle from `next` blocks
the button's cycle (the `self-service` concurrency group serialises them) and
could tear down what a visitor's cycle just built.

## Decision

**D1. `main` is the released line; the work happens on `next`.** `main` publishes
the page, the button dispatches from `main`, and `main` changes only by merging
`next` after a full cycle has gone green from it. The state handed out on
2026-09-12 is tagged `demo-2026-09-12`, so *exactly what they saw* is one
checkout away rather than an archaeology.

**D2. The page describes the released branch, and filters at the source.**
`state.runs` keeps only runs whose `head_branch` is `main`. One filter, one
place, so the history, the panel, the quota approximation, the busy state and
the duration estimate all answer about the same set of runs and cannot disagree
about which line they describe. Strict on the field: a run with no
`head_branch` is not something the Actions API returned, it is a fixture that
has not been told about this rule — so every fixture run now carries one, and
the in-flight fixture plants a newer, failed `next` run that the page must show
nowhere. `check-page-inflight.mjs` refuses to pass without that intruder, because
a claim about other branches over a fixture with none is vacuous.

**D3. Experiments on the shared environments do not run while the demo is out.**
This is the part no code enforces, and it is written here so that it is a rule
rather than a habit. Page work needs no AWS at all — the browser gates render
the page over fixtures. Pipeline and infrastructure work that needs a real
cycle uses an environment of its own (`lab`, its own state key, its own tags)
or waits. A `next` cycle on `stage` would still serialise safely behind a
visitor's — but the page would say *Launch a full cycle* while the environment
is busy, and that is the disagreement between halves this project keeps
refusing.

**D4. A second exhibit is deferred until the page changes shape.** For the
work that will change what the page IS — several services, a second runtime —
a lab site (its own bucket, its own distribution, `lab.` in front of the name,
published from `next`) is the right tool and `infra/public-site` is its
template. Not built now: D1–D3 cover everything before that work starts.

## Consequences

- The page loses nothing on the released line and stops reporting anything
  off it. A visitor who dispatches from a fork sees their run on GitHub and not
  here, which is the same rule stated from the other side.
- `demo-2026-09-12` is the first release tag this repository has. It marks a
  state, not a version; there is no changelog behind it and none is implied.
- The bucket versioning declared and never applied in Phase 28 is now the
  rollback mechanism for a bad publish, and stops being a curiosity. It is the
  first thing to close on `next`.
- Merging `next` is now a step with a precondition — a green cycle from that
  branch — and the precondition costs a cycle. That is the price of having a
  line that is never broken, and it is cheaper than a recruiter meeting a red
  banner.
