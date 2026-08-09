# 2026-08-09 — Phase 20m: the cycle watched through one tab — and what the map says while it is running

The step the cursor had named since 20l: a live cycle with the tab left open.
Ordered as a full cycle — stage up, promoted to prod through the approval gate,
both environments torn down, both priced — and watched from a single Safari tab
that was opened BEFORE the cycle was dispatched and never reloaded, navigated or
closed until it ended.

Evidence, with timings and the code paths behind each finding, in
`docs/sessions/2026-08-09-phase-20m-cycle-evidence.log`.

Everything 20l fixed holds against real records. What this cycle found is that
the page's account of a cycle IN FLIGHT is wrong in three separate ways, none of
which any existing gate can see, and all three of which are visible only while
something is running — which is the only time anybody watches.

## The findings

### 1. An in-progress run is counted as a success

`Recent lifecycle runs` takes its verdict from a numerator of COMPLETED runs and
a denominator of ALL of them, so a run in flight is asserted to have succeeded
before it finishes. Read five times, on four runs; the proof is the pair either
side of a completion:

```text
15:11   all 7 succeeded   while deploy-stage #32 in progress
15:14   all 7 succeeded   #32 completed successfully — THE BADGE DID NOT MOVE
```

It does not lag; it pre-assumes. Had #32 failed, the badge would have flipped to
`1 of 7 failed` — which carries the same defect, claiming six successes of which
one is unknown. The clearest single frame is at 16:01, where the badge reads
`all 10 succeeded`, its own right-hand half reads `last: destroy stage #45 · in
progress`, and the table row below reads `in progress`. One sentence
contradicting itself twice.

This is the shape the page elsewhere is careful about. Two screens up, the same
page says `This job has not started, so it reports no steps yet. That is an
absence, not a failed read.` The badge answers the same question the opposite
way.

### 2. The run layer overrides the one caption that is permanent

The node renderer consults the run layer FIRST and falls through to `nodeTense`
only if the run layer says nothing. So for the three nodes no timeline can ever
carry — `ECR push`, `migrate + seed`, `a human, in the prod environment` —
`nodeTense`'s permanent `not measured here · its step is in Actions, not in a
timeline` is replaced, for as long as their phase runs, by a temporary one. One
node, four states, one tab:

```text
15:00  not measured here · its step is in Actions, not in a timeline
15:07  its phase is running · which node is unknown
15:11  finished in this run · figures publish when the cycle ends
15:14  not measured here · its step is in Actions, not in a timeline
```

The middle two are false, and the third is a PROMISE the same cycle refuted
eleven minutes later.

**The caption serves two opposite futures.** At 15:31 all eight terraform nodes
of `Apply — prod` carried `figures publish when the cycle ends` too, and for
them it was true — their figures arrived at 15:38. Nothing distinguishes the
node whose figures are coming from the node whose figures do not exist.

**`which node is unknown` is false on arithmetic as well.** Phase 5 `Approve`
contains ONE node. Phase 8 `Destroy` contains two, and the page had already
drawn the other one as `measured · 7m 33s` — it had resolved the node and said
otherwise in the same box. The string dates from 20c, when a running phase
genuinely could not be resolved (Terraform creating one of eight); the
per-environment binding added later resolves it, and the caption never caught
up.

### 3. The `destroyed` disclaimer does not cover `unknown`

`nodeTense` attaches `these figures are from the cycle that ended` to
`envs === "destroyed"` and nothing else. There is no `unknown` branch — and
`unknown` is the state an environment is in whenever a run is touching it, which
is exactly when ADR-0051's rule is needed.

Predicted from the code before it could be seen, then witnessed on both
environments, in both halves of the cycle:

```text
15:44 – 15:56   prod  UNKNOWN     phase 6 `measured`, eight nodes at full
                                  colour with figures, no qualification —
                                  while prod was being deleted
15:56           prod  DESTROYED   phase 6 `destroyed`, all dimmed,
                                  "these figures are from the cycle that ended"
16:00 – …       stage UNKNOWN     phase 2 `measured`, same shape, same silence
```

Twelve minutes for prod, with the environment panel three screens above saying
`Last reported values, shown for reference only` about exactly the data the map
was presenting as current — and, inside the map itself, phase 7's suites saying
`from the previous run` at the same instant.

## Why no gate could see any of this

- `page-tense-check` lifts `nodeTense` as a PURE BLOCK and hands it data. There
  is a case named `a-node-no-timeline-can-carry-never-says-not-run-yet.json`,
  and it passes. The function is correct. The defect is that while a phase runs,
  nothing calls it. The instrument is aimed at the right function and the wrong
  scope.
- `page-freshness-check` requires an open tab to converge on what a fresh load
  shows. Both render the same wrong caption, so they converge — a gate about
  WHEN the page asks cannot see that the answer is wrong in both.
- `site-page-check` and `site-data-check` never ask the history badge anything.
  A fixture with an in-progress run exists
  (`tests/fixtures/page-measure/in-flight/runs.json`), but it also contains
  failures, so the badge takes the other branch there and the
  green-while-unknown shape never appears.

The common property: **every existing page gate examines the page at rest, or
examines a piece of it in isolation.** The three findings live in the transition
— the states a node passes through while a cycle runs — and no fixture in this
repository holds a cycle in mid-flight with an otherwise-green history.

## What held, live, against real records

- **The re-read (ADR-0053).** The front moved 2 → 3 → 4 and the figures arrived
  on a tab nobody touched. And the thing 20k explicitly could NOT do: prod's
  price, computed by the teardown at 15:56, reached the cost box at 16:01 on the
  same open tab — `prod $0.0182 .. $0.0237`.
- **Per-step binding (ADR-0043)**, twice: `seed assertion` running while `smoke`
  beside it had not started, and `API contract` reading `passed` (this run) next
  to `52 of 52 · 14s · from the previous run` (the last published report).
- **Per-environment binding in a shared phase.** During `destroy prod` only the
  prod node of phase 8 was lit; during `destroy stage` the roles swapped exactly.
- **Tense clears both ways** — with no run in flight, `from the previous run`
  disappeared from the suites.
- **prod runs the bytes stage tested**: stage by tag, prod by
  `@sha256:b080e23c…`.
- **19f's teardown order earned itself**: `Destroy ALB first` 7m 43s, then
  `Terraform destroy` 0m 14s.
- **ADR-0029's release pointer fired**, and was noticed only because a `git pull`
  after the session's documents were written brought the tag down:
  `release-20260809-2238-4828f2d`. 22:38Z is inside `promote-prod #11`, so the
  annotated tag on a green prod smoke belongs to THIS cycle. Nobody looked for
  it while it happened — it is on the repository, not on the page.

## Two things recorded as NOT measured

- **The convergence delay.** #32 finished about 15:12:30; the next observation
  was 15:14:48 with the figures already drawn. `max-age=60` is therefore bounded
  above by ~2 minutes and was not measured. Whether a minute of CloudFront TTL
  "reads as converging or as broken" — the question the cursor asked — is
  therefore still open, because nobody was looking at the second it mattered.
- **The map's dating sentence.** It says `dated 2026-08-09`; the previous cycle
  was also 2026-08-09. A fresh date and a stale one are indistinguishable, and
  the same is true of both cost bands. Nothing can be concluded from either.

Also open: `not reached yet` never appeared. `nodeTense` emits it only when
`!record`, and every node carried a record from the previous cycle — so a cycle
following a completed cycle may be structurally unable to exercise 20l's mirror
clause. Raised here; not settled.

## Cost

```text
stage  $0.0529 .. $0.0584    4123 s    32 created: 3 priced, 25 free, 4 not metered, 0 UNPRICED
prod   $0.0182 .. $0.0237    1812 s    34 created: 3 priced, 27 free, 4 not metered, 0 UNPRICED
```

Teardown confirmed independently against the AWS CLI — `account 993912191738`
first, then ecs, rds, alb, nat and eks all empty, under an `&&` chain so a dead
token would abort rather than render five clean-looking blanks.

## Changed here

Documents only. No code, no infrastructure, no gate. The three findings are
recorded with their code paths and their reproductions; the fix belongs to the
next session, because each of them needs a gate and every gate here needs a
break test before it means anything.

## Validation

```bash
  aws sts get-caller-identity --profile demo-admin
  aws ecs list-clusters --profile demo-admin --region us-west-2
  aws rds describe-db-instances --profile demo-admin --region us-west-2
  aws elbv2 describe-load-balancers --profile demo-admin --region us-west-2
  make docs-check
```

One process note, recorded because the log has to be honest about its own
instrument: the participant was asked three times whether the page's `Refresh`
button was pressed and did not answer. Every claim above says "without a
reload", which is what was observed. None of them claims "without a Refresh".
