# ADR-0089: Six small things the page said badly

## Status
Accepted (Phase 40, 2026-09-12). The remainder of the owner's review of
2026-09-11, after the six in **ADR-0086**. Widens ADR-0086 D3's channel, moves
one binding of **ADR-0043**, and re-arranges the row **ADR-0084** put the name on.

## Context

The same cycle that produced ADR-0086 produced a second list: things that were
not false, only badly said. Each of them is small; together they are most of what
a reader actually looks at while a cycle runs.

1. The run panel, headed *the step in flight*, drew three steps for every
   finished job — `Post Configure AWS credentials`, `Post Checkout`, `Complete
   job`. By the hold, four of a self-service run's five jobs are over, so the
   panel was three quarters runner housekeeping.
2. `Recent lifecycle runs` came out from behind its `<details>` in ADR-0082 and
   kept the summary's contents without the summary's layout: the verdict badge
   sat against the text with no gap, and the sentence after it inherited the
   heading's capitals — `LAST: SELF-SERVICE LAUNCH BY THE OWNER #20`, shouted.
3. `Wait for ECS service to be stable` was bound to **Provision**, so the map
   said *migrate + seed — its phase is running* while nothing had migrated
   anything: the apply was waiting for the service it had just created.
4. Both environments read a yellow **UNKNOWN** through the whole of an apply,
   three inches above a board lighting up node by node. `unknown` is the right
   answer to *this reading could not be checked* and the wrong one to *a cycle is
   building it right now*, which the page knew.
5. The cost box read `stage $0.0238` alone during the hold, with prod up behind
   HTTPS and spending. `openCost()` declines for several good reasons and each of
   them removed the environment from the line entirely.
6. And the estimate added in ADR-0087 made the top row too wide: under about
   1450px the whole control group dropped onto a second line beneath a rule,
   which reads as a different section of the page. The owner: *разнеси по разным
   сторонам табы и кнопку с плашками, строку слева от табов перемести выше или
   ниже*.

## Decision

**D1. A finished job that went green shows no steps.** The line above it carries
the verdict and the duration, and the disclosure below still holds all of them. A
FAILED job keeps its window, because `stepWindow()` centres on the failing step
and that is the one line worth putting in front of a reader without a click.

**D2. The history heading lays itself out like the summary it used to be**: badge,
then the sentence in sentence case, pushed to the right-hand slot. Addressed by
id rather than by `:has(.verdict)` — there is one heading like this, and a
selector reaching for any future one would decide the layout of a heading nobody
has written yet.

**D3. Waiting for the service is the tail of the apply.** The binding moves to
`stage-apply`, and prod's two waits — the service and the public HTTPS name —
move to `prod-apply` with it. Provision keeps what provisions: migrate, seed and
the seed assertion.

**D4. The panel says `being created` when a document says so.** The map already
reads the partial apply (ADR-0076), attributes it to the run in flight and
shelf-lifes it; it now sends that conclusion along the channel ADR-0086 D3 opened
for teardowns, which becomes `cycle:environment` and carries both halves of one
question. The panel keeps the vocabulary and the badge; the reading below it
stays marked as older than what is happening, and the application link stays
down, because a half-built environment has no business offering one.

**D5. An environment that is up never vanishes from the cost box.** Where the
open figure cannot be computed the line says so — *up now, and this page cannot
price it yet* — instead of dropping the environment. A missing line reads as
nothing to pay, which is the one thing it never means.

**D6. The header is two rows: the name above, the controls below.** Tabs at one
end, the launch control at the other. Three things did not fit on one line and
two do. The first attempt kept one row and let the clause ellipsize, which did
not work and is worth writing down: **a wrapping flex container breaks lines on
each item's hypothetical size, before any shrinking is applied**, so the clause's
full width pushed the control onto a second line and only then did the name grow
back to fill the first.

## Consequences

- The header costs 33px more height, on every part. That is the price of the
  arrangement the owner asked for, and it buys a control group that no longer
  moves as the window narrows.
- `cycle:teardown` is now `cycle:environment`. One event, two fields, one
  listener: a second event for the second half would have been two things to keep
  in step.
- D5 makes a branch visible that used to be silent, which means a reader can now
  see the page decline to price something. That is the intended trade and it is
  ADR-0067's rule applied to its own failure mode: publish the inputs, say so
  when they are not there.
- D4 leans on the progress document for a WORD in the panel, not only for the
  board. The shelf life and the run-id attribution that protect the board protect
  this too; there is no new source and no new request.
- None of these six was caught by a gate either. Four were the owner's, reading
  the page while it ran.
