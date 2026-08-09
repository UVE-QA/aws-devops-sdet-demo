# 2026-08-09 — Phase 20h: the fold prices a real cycle, and the page dates it wrong

Evidence — the pricing step's own output, verbatim, in
`docs/sessions/2026-08-09-phase-20h-cost-fold-live.log`.
Cost: **$0.0178 .. $0.0235**, computed by the thing being tested. stage only;
prod was not deployed and was not touched.

The cursor's next allowed step was **a live cycle**, for two reasons it stated
itself: the wired cost fold had never run live, and the page had only ever been
seen on frozen fixtures. Both were exercised. The fold did its job. The page did
its job too, and in doing it revealed four things about WHICH CYCLE it is
describing — none of which a fixture could have said, because every one of them
lives in the gap between a run that is happening and a record that is published
at the end of it.

## The route, decided before anything was dispatched

Two facts settled the shape of the cycle, and both were read out of the
repository rather than assumed:

```text
1  the fold is wired into destroy.yml ALONE. self-service.yml has its own
   teardown job (its own `Terraform destroy`, its own publish) and no pricing
   step in it. The public launch button therefore cannot exercise the fold: it
   publishes an apply anchor and then tears the environment down without
   pricing it. So the cycle had to be deploy-stage.yml -> destroy.yml, dispatched
   by hand, not the button.

2  the anchor `timeline/<env>/apply.json` is written by scripts/publish-status.sh,
   and that clause landed in 222dd27 at 2026-08-09T00:28Z - AFTER the last
   stage teardown (2026-08-08T20:59Z). No anchor existed. A destroy run on its
   own would have printed `no apply anchor published ... nothing to price` and
   exited zero, under `continue-on-error`, GREEN. Indistinguishable from the
   fold failing.
```

The second is the reason the apply had to come from current `main` first. A
teardown alone would have produced a green run, no cost object, and no way to
tell refusal from absence — the empty result that looks clean, in its natural
habitat.

Noted while reading, not fixed here: `deploy-stage.yml` sets no
`TF_VAR_expires_at`, so a hand-dispatched stage carries no `ExpiresAt` tag and
the watchdog cannot collect it. The 90-minute TTL, the 3-a-day count and the
one-at-a-time lock are guarantees of the BUTTON's path. A manual cycle is owned
by the person who started it.

## What the fold did

`destroy stage #41`, step `Price the cycle from its two timelines`:

```text
cost: stage — COMPUTED ESTIMATE, not a bill
  rates captured 2026-08-08T23:13:42Z for us-west-2
  cycle CLOSED  2026-08-09T05:13:18Z -> 2026-08-09T05:43:24Z  (1806s)
  ESTIMATE  $0.0178 .. $0.0235

  resource                           low s  high s       low $     high $  state
  module.alb.aws_lb.this              1557    1766      0.0097     0.0110  closed
  module.rds.aws_db_instance.this      812    1339      0.0043     0.0071  closed
  module.ecs.aws_ecs_service.app      1100    1545      0.0038     0.0053  closed

  32 created: 3 priced, 25 free, 4 not metered, 0 UNPRICED
```

- **`0 UNPRICED`.** Every created resource landed in a class. The
  classification was written against fixtures and had never met a real apply's
  32 resources; nothing fell through.
- **ADR-0046's four pairing clauses all passed on a genuine pair** — same
  environment, apply `complete`, teardown starting after the apply finished, and
  a non-empty intersection. None of them had ever been asked about live data.
- The step's green check means nothing on its own: it is `continue-on-error`
  by design (a refusal must not redden a teardown and hold the launch lock),
  so it cannot fail. The evidence is the LOG LINE, and that is why the log is
  attached rather than the check being cited.
- Order of magnitude sits where `docs/cost-control.md` says it should: ~$0.02
  for a half-hour stage-only cycle against ~$0.09 measured for a full stage+prod
  cycle in Phase 16a.

## What the page said, and about which cycle

All four findings are one root: **every figure on the map comes from the
terraform timeline, and the timeline is published when the cycle ENDS.** So
during a run the map describes the previous cycle, and at rest it describes a
cycle rather than the present.

### 1. A finished phase prints the PREVIOUS cycle's duration, unlabelled

While the run was in flight, `Apply — stage` read `last time 8m 26s` beside a
live `3m 41s`. Both honest. The moment the phase finished — run still going —
it read `8m 26s` beside a green `done`, and the label was gone:

```js
const since = pst && pst.state === "running" ? pst.since : null;
...  ${since ? "last time " : ""}${secs(was.duration_s)}
```

The prefix is printed only while the phase is RUNNING. The comment two lines
above it says why that matters — *"The second is dated, because an unlabelled
duration is a claim about today"* — and the code then unlabels it in exactly the
state where the claim reads hardest as today's.

This run's apply took **8m 30s** (`05:13:18Z -> 05:21:50Z`, 510s). The page
showed **8m 26s** (506s). Four seconds apart: a defect that answers rather than
one that stops. The at-rest map now reads `8m 30s · measured`, which is the
same figure from the other side and closes the question.

The control that settled it was already on screen: `Provision — stage` finished
in the same run and printed `done` with **no number at all**, because it is an
ECS task with no terraform record and therefore no `was`. If the page could
print this run's duration, that phase would have had one.

Nothing asserts this. `last time` appears nowhere in the repository outside
`site/index.html` — not in `make live-state-check`, not in any fixture.

### 2. Two nodes read `not run yet` minutes after running

At rest, `Build -> ECR push` and `Provision -> migrate + seed` both read
`not run yet`. Both had just run: `Build, tag, and push image` 25s, `Run one-off
tasks (migrate, seed, db-assert)` 3m 16s, and the `seed assertion` node beside
the second reports `2 of 2`, which is impossible without the seed. Neither is a
terraform resource, so neither appears in the timeline, so `n.state` is absent.

During the run both said `finished in this run` — correct. At rest both say
something false. Opposite direction to finding 1, same cause.

### 3. A destroyed environment keeps its icons lit

```css
.node.absent            { opacity: 0.45; border-style: dashed; }
.node.absent .icon.aws  { filter: grayscale(1); }
```

`absent` means NO RECORD, not "not in AWS". stage was destroyed and verified
gone, and its ten nodes stayed at full colour because the apply record exists;
prod's identical nodes are grey because no record does. **Two environments in
the same state, drawn as opposites** — while the Environments panel a few
centimetres away reads `stage DESTROYED`, present tense, observed in AWS.

The `state encoding` legend explains the WORDS and says nothing about the
colour. The only statement of tense on the whole page is one line of grey prose
above the map.

### 4. The cost line was not found by the person looking for it

It renders. It sits under the map, above the below-the-fold divider, as an
unheaded grey paragraph in the prose flow. Every other number on the page lives
in a bordered box with a label. The person who dispatched the cycle, watching
for this specific line, read past it and reported it missing.

## Confirmations, all first-time-live

- 20c's two fixes, seen in a real run rather than a fixture: a phase whose steps
  are over no longer falls back to `nothing recorded yet`, and not every node of
  a running phase claims `running now`.
- ADR-0043's per-step binding: `seed assertion` and `API contract` went to
  `finished in this run` while `regression` and `smoke` were still running, in
  the same phase.
- The phase clock did not reset when terraform moved `plan` -> `apply` — the
  fix that was made "writing the gate, not watching the cycle".
- The tests panel carried real verdicts for the first time: 52 of 52, 12 of 12,
  2 of 2, 2 of 2. Before the run it read *"180 tests are collected from the
  suites themselves; no run has reported on them yet."*
- The history table, the one box that overflows its parent at 390px, is clean at
  desktop width with a self-service run absent from it.

## Teardown, verified from the devbox

Not from Terraform state, and not from the destroy job's own check. `sts` first,
every result assigned under `set -e` in a child shell, and — because no
non-empty reading was taken before the teardown — a control on a permanent
level that MUST answer:

```text
account : 993912191738
CONTROL ecr (must NOT be empty) : aws-devops-sdet-demo-app
alb :
rds :
ecs :
nat :
eks :
```

The control is what makes the five empty lines evidence rather than a
credential failure wearing the shape of success.

## Measured

```text
deploy-stage #30   16m 38s   (Terraform apply 8m 33s; apply timeline 8m 30s)
destroy stage #41   9m 39s   (Terraform destroy phase 8m 4s)
cycle lifetime     1806s = 30m 06s, apply start to destroy end
```

## Next

- **the page's tense**, chosen in the chat over the packing work: a figure is
  never printed without the cycle it belongs to; `not run yet` is not said about
  something that just ran; a destroyed environment does not read as a live one;
  and the cost line gets a place. All four are checkable on fixtures, so each
  can have the break test this project requires before a gate means anything.
- then the packing left by 20g — the comb and the ragged top row.
- the phone stays deferred far.
