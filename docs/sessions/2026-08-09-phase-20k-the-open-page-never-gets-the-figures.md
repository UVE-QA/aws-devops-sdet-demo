# 2026-08-09 — Phase 20k: the cycle the page was built for, watched — and the open page never gets the figures

The cursor's next allowed step had said **a live cycle** since 20g, and had been
stepped over three times in favour of work that could be done on fixtures. This
session ran it, and ran it further than 20h did: stage up, promoted to prod
through the approval gate, then both environments torn down and both priced.

Evidence — the runs, the approval gate asked three ways, both pricing lines
lifted from the job logs rather than from a green check, and the teardown
reading — in `docs/sessions/2026-08-09-phase-20k-cycle-evidence.log`.

Cost, computed by the thing under test, both bands published and both dated:

```text
stage   $0.052648 .. $0.0581     32 created: 3 priced, 25 free, 4 not metered, 0 UNPRICED
prod    $0.017217 .. $0.022735   34 created: 3 priced, 27 free, 4 not metered, 0 UNPRICED
```

**The same stage environment cost three times what it cost yesterday**, with the
identical resource breakdown — `32 created: 3 priced, 25 free, 4 not metered` in
both cycles, against 20h's `$0.0178 .. $0.0235`. Nothing about the rates changed:
stage stood roughly three times as long, because this cycle held it up through a
promotion and a prod teardown. That is ADR-0045's claim — the meter is a
LIFETIME, not a creation — asked of two cycles of the same environment rather
than argued from one.

prod had never been deployed by any session that watched the page, never been
priced, and `cost/prod/latest.json` had never existed. It does now.

## What the cycle was for, and what it found

Everything 20i fixed was fixed **on fixtures**. This session watched those
fixes against real records, and they hold — every one of them. What it also
found is that the page they are written into cannot deliver them to a reader who
leaves the tab open, which is the way a dashboard is read.

### The finding: the run layer is read once, at load

`readRunLayer()` in `assets/index.template.html` reads the five things the map
draws its FIGURES from:

```text
timeline/<env>/nodes-apply.json      the at-rest numbers on every apply node
timeline/<env>/nodes-destroy.json    the same for the teardown node
timeline/<env>/latest.json           the last run of either kind
results/<env>/latest.json            the suite verdicts
cost/<env>/latest.json               the cost box
```

It is called exactly once, in the bootstrap chain. The poll loop `tick()` reads
`status/*.json` and the GitHub runs and jobs — and nothing else. The `Refresh`
button calls `tick(true)`, so it does not touch the run layer either.

Four symptoms, all observed live, all one root:

```text
1  promote-prod went green and the open page said phase 6 `not run yet` -
   WORSE than the `done` it had shown minutes earlier while the run was in
   flight. nodes-apply.json for prod had been fetched at load, when prod had no
   apply record at all, and was never asked again.
2  destroy prod went green and `prod - everything above` still said
   `not run yet`, while timeline/prod/nodes-destroy.json said `measured` and
   carried the phase at 467s.
3  prod's price was published and could not reach the cost box.
4  the Refresh button changed the WORDS - `destroyed`, "these figures are from
   the cycle that ended" - because those come from status/*.json, which is
   polled. Fresh words over stale figures.
```

Left alone for three minutes — six bucket polls at the cadence the page prints
about itself — it did not converge. One hard reload fixed all four at once, and
that was a **prediction made before the reload and confirmed by it**: the prod
teardown node became `measured · 7m 47s` and the cost box grew its second line.

This could not have been found on fixtures. `make measure-page` mocks all three
remote sources and never polls; every gate here lifts a pure block out of the
page and calls it with data it is handed. The defect lives in when the page
ASKS, and nothing in this repository was watching that.

### What held, live, for the first time

```text
- the GitHub half of the prod approval gate. Rules present and real
  (required_reviewers, branch_policy, can_admins_bypass false, one reviewer,
  prevent_self_review false), the run PAUSED, and a human approved it - twice,
  because destroy.yml declares `environment: prod` as well.
- 20i's four tense clauses, against real records rather than fixtures:
  `last time 8m 16s` beside a finished phase, `destroyed` with "these figures
  are from the cycle that ended" on every node of a torn-down environment,
  suites reading "2 of 2 - from the previous run", and the cost box in a
  bordered box with a label over it.
- ADR-0043's per-step binding, on prod: `seed assertion` reading
  "running now - its report arrives when the step ends" while `smoke` beside it
  still said "not run yet - 2 tests collected".
- 20c's phase wording: `its phase is running - which node is unknown`, with the
  stage node in the same phase NOT lit, which is the clause that says a live
  phase does not mean a live node.
```

### Two non-findings, written down as such

**The 403 that was my own fetcher.** `cost/stage/latest.json` returned 403 to
the chat session's fetch tool while its run-named twin returned 200. The object
was in the bucket, 19105 bytes, written one second after the twin, and the
devbox got `200` for all three URLs. An hour of the apply window went into
this, and the apply window is not repeatable. Recorded because the shape
recurs: the instrument was the defect, and the control that settled it was a
different client on a different network path.

**The destroy phase that was not lit.** At 1m39s into `destroy prod` the map
showed phase 8 unlit while the run panel showed the run. The map was right: the
phase's binding is exactly two steps, and the run was still on `Adopt live
resources Terraform does not manage`, with `Destroy ALB first` queued. Called a
finding, checked against `data/topology.json`, and withdrawn in the same
session. What remains is smaller and real — while a cycle is in flight but has
not reached a phase, that phase says `not run yet`, the same words as a phase
that never ran, on the same screen as a panel saying the run is in progress.
It is the mirror of 20h's `not run yet` about something that had just run.

## One more instance, in the last screenshot of the session

With both environments down, the run panel read `destroy stage #43 SUCCESS
9M 17S` and the map's `stage - everything above` read `8m 4s` - the PREVIOUS
teardown's figure. The page had been reloaded before that run finished, so the
node it belongs to had already been fetched for the last time. The finding is
not rare and it is not a race: it is what the page does every time.

## Two things a reader did, filed next to the decisions they are about

Neither is a defect against anything decided. Both are what the person who ran
the cycle actually did in front of the page, which is the only way this kind of
evidence arrives.

**The legend was not opened.** ADR-0048 D2 made it a cut, closed by default,
because every node now carries the word for its own state. Asked what the
coloured left edge on a node meant, the person watching the cycle asked the chat
rather than the summary one click away. Same shape as 20h's cost line being read
past — the page had the answer and the reader did not find it.

**At rest, the brightest things on the page are the teardown and the tests.**
With both environments destroyed, everything the cycle BUILT is dimmed, and the
two kinds of node that are not about infrastructure that currently exists keep
full colour. Each rule is deliberate: ADR-0051 exempts the destroy node — "it is
the one node a teardown actually measured, and greying it would erase the
evidence that the teardown ran" — and a suite's purple edge is the legend's own
channel, "observed by its report, not by Terraform". The SUM of the two was
decided by nobody, and it inverts the visual hierarchy of the page's most common
state. For the session that re-tones or repacks.

## Changed here

`<base target="_blank">` in the template head: every link now leaves in a new
tab. Found by using the page rather than by reading it — following a run log
took the reader off the dashboard mid-cycle. One `base` rather than a `target`
per anchor, because four of this page's links are static and eight are built by
string concatenation in the script, and the per-anchor version is a rule that
has to be remembered at every future call site. Consequence stated in the
template and accepted: the published Playwright report opens in a new tab too.

No ADR. The link change is a one-line preference with its reasoning in the
template beside it; the refresh finding is a defect, not a decision, and the
decision about how the page should re-read its figures belongs to the session
that makes it.

## Validation

The teardown, from the devbox, against the AWS CLI rather than against Terraform
state, with a permanent level as the control in the same block under `set -e`:

```text
account 993912191738
CONTROL ecr aws-devops-sdet-demo-app
ecs
rds
alb
nat
eks
```

Five empty readings are evidence only because `ecr` in the same block is not.
No NAT gateway and no EKS cluster, as v0 requires.

The gates, with the template change applied:

```bash
make site-page-check site-data-check docs-check
make page-tense-check
make live-state-check
```

## Cost

Two priced cycles, `$0.052648 .. $0.0581` for stage and
`$0.017217 .. $0.022735` for prod, both computed from resource lifetimes by the
fold under test. Nothing
else was created. Both environments verified gone from AWS, against the CLI
rather than against Terraform state, with a control on a permanent level in the
same block.
