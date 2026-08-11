# ADR-0059: A figure belongs to a cycle, and a cycle belongs to an environment

## Status
Accepted (Phase 25, 2026-08-11). Implemented in the same session: the fixture,
the gate, the three clauses it reddened, and the break tests.

Closes the two findings **Phase 20m** left open and the one Phase 22 fixed
without ever being able to demonstrate. Extends **ADR-0053 D6**'s mirror clause
— `not reached yet` for a phase a running cycle has not got to — to the node
that HAS a record. Uses **ADR-0051 D2**'s rule about where an observation may
come from, from the other side: there the run layer was not allowed to speak for
an estate node, here it is not allowed to speak for it silently. Leaves
**ADR-0043 D2**'s per-step binding and **ADR-0042 D5**'s publishing rule
untouched; both are what make the fix expressible.

## Context

Phase 20m watched a full cycle from one tab and found the page's account of it
wrong three ways, every one of them invisible at rest. Phase 22 fixed the first.
The other two sat in the cursor for three phases, not because they were hard but
because nothing could see them: the FUNCTIONS were correct and were not called.

That is the shape worth stating, because it is the third time this repository has
met it. `nodeTense()` decides what a node says when no run is speaking for it,
and `check-page-tense.mjs` lifts it out of the built page and interrogates it —
fourteen cases, forty-two calls, all green while the page was wrong. During a run
the renderer consulted the run layer first and never reached the function. A gate
aimed at a correct function cannot see the branch that skips it, exactly as a
document-level overflow measurement could not see a box that overflows its
parent (20a) and a fingerprint comparison could not see two pages agreeing on the
same wrong caption (20m).

So the subject had to be the rendered page, in flight. The fixture that needs is
what 20m said this repository does not have, and building it produced a finding
of its own — see D5.

## Decision

### D1 — A figure drawn while a cycle is running names the cycle before it

Nothing publishes until a cycle ends. Every figure on the page during a run is
therefore the previous cycle's, and the page says so:

```text
measured · 4m 47s · these figures are from the cycle before this one
```

`nodeTense()` gains one branch, after the `destroyed` one and before the plain
`measured`. The predicate is `underWay` — already computed, already handed in,
true only when a run is in flight AND it is about this environment.

The sentence is deliberately the sibling of the two that already exist: `these
figures are from the cycle that ended` for a destroyed environment, and `a cycle
is under way and has not got here` for a phase the run has not reached. Three
statements of one idea, in the three states it takes.

### D2 — And the second half of that predicate is load-bearing

`underWayHere()` asks two questions, and the page had been getting the answer
right on one half of itself and wrong on the other:

```text
the node half     asked neither. Every node with a record printed its figure
                  unqualified, whether or not a run was touching it
the suite half    asked only the first. `result_previous` compared the report's
                  run id against the run in flight and marked EVERY verdict
                  `from the previous run` - including prod's, during a stage
                  deploy that never goes near prod
```

A label that appears on everything during any run says nothing about anything.
Both halves now use the same predicate, which is the point: this was one missing
question, not two bugs.

### D3 — A node nothing can ever measure never promises figures, in any branch

Three nodes carry `observer: "actions"` — the image push, the migrate/seed task,
the human approval. Terraform reports resources; none of the three is one, so no
timeline will ever carry them. At rest they said so. The moment the run layer had
something to say about their step they lost the sentence, and one branch replaced
it with `figures publish when the cycle ends` — a promise the same cycle refutes.

The run layer's word about the STEP is kept, because it is true and useful: the
step started, or finished, or failed. What travels with it is the clause about
what could ever measure the node. One expression, used in all three run-layer
branches, so a fourth branch cannot forget it as quietly as these did.

### D4 — The gate renders the page, and the fixture is the deliverable

`make page-inflight-check` is the first gate here whose subject is the WHOLE
rendered page in a state that is not rest. Three claims, both states, and the
fixture — `tests/fixtures/page-inflight/` — carries two things no existing set
does:

```text
an otherwise-green history  the one in-flight fixture that existed carries two
                            failures, so the badge has a bad verdict for a
                            reason unrelated to the run in flight and the
                            green-while-unknown shape never appears
the RUN LAYER               the ten documents readRunLayer() fetches per page
```

Two states over one layer: `in-flight`, and `at-rest` thirteen minutes later.
The second is the control and is required to DIFFER — named rather than hashed
(the verdict, and at least one node's state line), because on 2026-08-05 this
project built a control that reproduced the defect it was controlling for.

Five refusals, all exercised: an unmocked request, an origin 404, a
source-failure banner, a fixture whose history is not otherwise-green, and a
fixture whose declared cycle disagrees with its own history.

### D5 — THE INSTRUMENT HAD NEVER MEASURED A PAGE WITH FIGURES ON IT

Found while building D4's fixture, and it is about `measure-page.mjs` rather
than about the page.

That script mocks the three sources the sandbox cannot reach and guards itself by
recording every request that LEAVES the origin. The run layer does not leave the
origin: it is ten relative paths under the page's own host, published into the
bucket beside it by `publish-status.sh`, and absent from `site/` in the
repository. They 404 against the static server, `readJSON` folds a 404 into
`null`, and the page renders happily — no banner, every node reading `not run
yet`, not one figure printed anywhere.

Measured, not inferred: ten 404s per fixture, on both sets, with `unmocked`
empty. Its own docstring says the thing it does not do — "measured with them
unreachable the page renders its banners and its 'no observation' panels, and is
SHORTER than the page a visitor gets". It fixed that for the remote three and
left it in place for these ten.

So every layout figure this project has argued from since 20e — including
ADR-0058 D6's 2039 → 3116px and 1.9 → 2.9 screens, and 20j's 18.5rem node floor —
is a measurement of the short bodies. **How much shorter is NOT MEASURED**, and
guessing it here would be the same species of error. It is a phase of its own in
`docs/next-phases.md`, and it is not this one: the cursor named the gate, and a
session that starts remeasuring the layout here is how Phase 20 happened.

`check-page-inflight.mjs` refuses on an origin 404 for exactly this reason.

## Consequences

- The map dims and qualifies every node of an environment a run is touching, for
  the length of that run. That is a visible change to the busiest state of the
  page, and it is the state a visitor is most likely to be looking at.
- `data-id` is on every node. The page can be asked about a node by name, which
  is what made a gate over the rendered map possible at all; the label could
  never do it, because stage and prod draw the same labels.
- A third browser gate joins `local-ci` in `ci.yml`. The job now installs nothing
  new — playwright and chromium are still side effects of the smoke step.
- The break-test log records that it was taken in a chat session's sandbox on
  chromium-1194, not on the devbox. The devbox re-ran the gate green and one
  refusal red; the four defect breaks were not re-run there.
- D5 puts a number in doubt that four ADRs quote. Nothing is retracted here —
  the figures were honestly measured with an instrument whose limit nobody knew.
  What follows is a remeasurement, and the comparison is what makes it worth
  doing.
