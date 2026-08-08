# 2026-08-08 — Phase 20c: a node answers for its own step

Closes 20c. The half 20c left open was the page: it read neither
`site/data/suites.json` nor `results/<env>/latest.json`, so 180 collected tests
and a real cycle's verdicts were true and invisible. It reads both now, and the
three things the previous session found by WATCHING that cycle are fixed.

**ADR-0043.** Break tests in
`docs/sessions/2026-08-08-phase-20c-a-node-answers-for-its-own-step.log`.
Cost: nothing. No AWS call, no cycle, no credential.

## What the three findings turned out to be

They arrived as three rendering complaints and they are one structural mistake:
**liveness was attached to the box a node is drawn in, and a box is a layout
decision.**

```text
every node of a running phase said "running now"    -> a phase is not its nodes
a finished phase said "nothing recorded yet"        -> which is what NEVER RUN says
suite.db.stage lit during tests it takes no part in -> its step is in Provision
```

So a suite node now carries its own `live` binding, in the same shape a phase
already uses, and `scripts/generate-topology.py` checks it with the same code: a
workflow that does not exist, a job that does not exist, a step that has been
renamed, or a suite with no binding at all are four refusals at build time. A
node with no binding of its own still inherits its phase — and is MARKED as
having inherited it, so the page can say *its phase is running, and which node
is not published until the cycle ends* instead of picking one.

prod and stage stop disagreeing about `db` because neither is guessing: prod's
gate phase happened to bind its db step and stage's did not, which is why the
same suite behaved differently in the two environments and nothing looked wrong
in either.

## The gate, and why it is JavaScript

Every other fold on this map runs on the runner, in Python, because a join
written twice is one definition on two hosts. This one cannot follow: it reads
the Actions API live in the visitor's browser, and there is no run afterwards to
fold. Copying it into Python to test it would create exactly the defect the
other two exist to avoid.

`scripts/check-live-state.mjs` lifts the marked block **out of the built page**
and runs it verbatim against twelve recorded observations. `make
live-state-check`, in `ci.yml`, no AWS, no setup step.

Because it reads the BUILT page it also catches a template edited without
rebuilding. That was not designed; it is how the first run of the fixtures went
red, before this log was taken.

## Ten break tests, and what they say

Full output in the `.log` beside this file, green control either side, tree
clean at the end.

```text
1  a suite node with no live binding             REFUSED at build
2  a bound step renamed in the workflow          REFUSED, names the step
3  the gate's marker renamed in the page         REFUSED: "found 0 and 1"
4  the cases directory moved away                REFUSED: a gate with nothing
                                                 to check is not a green gate
5  the frozen phase snapshot moved away          REFUSED
6  finding one, put back                         6 cases red
7  the completed-run guard removed               1 case red - a finished run
                                                 covering the figures it published
8  finding three, put back                       3 cases red, and the sharpest
                                                 line in the log: suite.db.stage
                                                 "the machine reported nothing"
                                                 while its step was running
9  a skipped step treated as a finished one      1 case red
10 the phase clock restarted per step            6 cases red
```

Number 10 is a defect this session found while writing the gate rather than
while watching the cycle, and it is worth separating from the other three for
that reason: the phase clock took the START OF THE STEP RUNNING NOW, so a
four-minute apply read as ten seconds old every time Terraform moved from `plan`
to `apply`. It now runs from the first bound step that started. The old code's
own comment said it should — "a phase is busy from the moment its first step
began" — and the code under the comment did the other thing.

## What the page says now

Verified in a headless Chromium against a local copy of the site with a real
folded report in it, and again with each recorded observation dispatched into
the live listener. No page errors; the text below is quoted off the render.

```text
at rest, no run     "52 tests collected — not run yet"   COLLECTED, not files
a verdict           "passed | 0.6s | 52 passed"
not reported        "the last run here did not report this suite"  - ADR-0025
                    drawn: regression and the API contract cannot reach prod
in flight           "the PREVIOUS run here did not report this suite", because
                    the report carries the run that wrote it and the page can
                    tell those apart
its own step        "running now — its report arrives when the step ends"
                    (a suite's observer is its report, which does not exist yet)
inherited           "its phase is running — which node is not published until
                    the cycle ends"
finished mid-run    "finished in the run still going — figures publish when the
                    cycle ends"
```

The counts under the map already came from the generated file; the sentence over
it now names the run each environment's verdicts came from, with a link.

## Files

```text
assets/topology-groups.json          six suite nodes gain their own `live`
scripts/generate-topology.py         live_bindings() takes an owner; suite nodes
                                     are resolved and checked like phases
assets/index.template.html           the run-layer state machine, marked for
                                     extraction; the two new fetches; the node
                                     bodies for every state above
site/index.html                      rebuilt
site/data/topology.json              regenerated
scripts/check-live-state.mjs         NEW - the gate
tests/fixtures/live-state/           NEW - frozen phases.json, refresh.py, and
                                     twelve hand-written cases
Makefile                             live-state-check
.github/workflows/ci.yml             it runs in terraform-checks
README.md                            the gate list gains results-check and
                                     live-state-check
docs/decisions/0043-...              ADR
```

## Validation

```bash
make site-data-check      # clean, 116 resources across 8 levels
make site-page-check      # byte-identical to a fresh build
make live-state-check     # 12/12
make results-check        # 10/10
make docs-check           # 6 documents, 0 findings
```

Not run here, and not needed by anything in this session: `make test-unit`,
`make suite-inventory-check`. Both want the suites' own dependencies, and
nothing in this session touched a test or an inventory — the fixtures under
`tests/fixtures/live-state/` are read by the new gate alone.

## What is left

20c is closed. Next is **20d — cost, computed and reconciled**, which was blocked
on 20b and is not any more: the cycle 20c ran on 2026-08-08 is the first one it
can reconcile a bill against.

Two things this session deliberately did not do, so they are written down rather
than remembered:

```text
- the map still has no per-resource liveness, and cannot have one while the
  credential that could publish it is kept away from the bucket (ADR-0026).
  "its phase is running" is the honest ceiling, not a placeholder
- the new gate's phases.json is a FROZEN snapshot. When a binding changes on
  purpose, refresh it with tests/fixtures/live-state/refresh.py and read the
  diff; a case going red afterwards is the gate reporting the rename
```
