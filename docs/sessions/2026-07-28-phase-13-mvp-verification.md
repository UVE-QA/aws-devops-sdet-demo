# 2026-07-28 — Phase 13, MVP verification gate (CLOSED)

One uninterrupted run from an empty account to an empty account, performed as
the cursor demanded: as if by a stranger. All six steps of the Phase 13
definition were exercised. Nothing in the AWS half failed.

## What ran

```text
deploy-stage  #22   green (observed via the dashboard, not step by step)
promote-prod  #5    16m55s total, promote job 14m08s
destroy prod  #14   10m06s total, destroy job 8m27s
destroy stage #15   08m34s total, destroy job 8m30s
```

prod served https://app.demo.uveapp.net for roughly 23 minutes and was then
destroyed. Total billable footprint: one prod deploy/destroy pair and one stage
destroy.

## What it proved

- **The approval gate blocks at dispatch, not mid-deploy.** `promote-prod` sat
  in `waiting` with an empty step list; `pending_deployments` named `prod` and
  the reviewer. No Terraform, no ECR pull, nothing applied before approval.
- **Promotion is by digest, and it was checked against ECR rather than believed.**
  The prod task definition carried
  `@sha256:0c27a1561a47b6b9e07ac9be70e1f246bc44b2aa0180d3d5bfe47ddb214489ea`;
  `aws ecr describe-images --image-ids imageTag=a9a2709...` returned exactly that
  digest. The dashboard asserts both halves, so the dashboard could not be the
  witness for either.
- **Teardown was verified from outside the pipeline, before and after.** The
  same five-resource sweep run under `demo-admin` on the devbox showed three
  stage resources and zero prod resources after `destroy prod` — which is what
  made the prod teardown a fact rather than a self-report — and then all five
  lines empty after `destroy stage`. NAT and EKS were empty throughout, as v0
  requires.
- **The dashboard agreed with the sweep, in both directions.** It reported prod
  `DESTROYED` with `absent` on every resource while the CLI independently said
  the same, and it did not substitute a stale Playwright report for the missing
  one: "the run that wrote this file produced no report".

## What it found

- **`destroy` on prod also stops at the approval gate.** The protection rule
  sits on the `prod` environment, not on a workflow, so tearing prod down is as
  gated as deploying into it. `destroy` on stage does not pause at all.
  `docs/demo-script.md` told the presenter to dispatch destroy and "not wait for
  it", which live reads as a hung workflow. Fixed in da22d7c, together with the
  second set of measured timings.
- **Self-approval is permitted.** The reviewer is the repository owner and the
  approval succeeded, so "prevent self-review" is off. The gate stops accidents,
  not insiders. Stated plainly in the demo script rather than left to be found.
- **`pending_deployments` needs `-F`, not `-f`.** With `-f` the API answers
  `422 For 'items', "18760540879" is not an integer`. Costs one round trip and
  looks like a permissions failure at first glance, which it is not.
- **The UP badge is a snapshot presented in the present tense.** Each card is
  written by the last job that observed that environment; stage read `UP` for 55
  minutes after its last observation. `DESTROYED` cannot go stale the same way,
  because nothing brings an environment back on its own — so the defect is
  one-directional and only bites the green state. NOT FIXED; see follow-ups.

## Failures on the chat side, not the platform side

Recorded because the primer's verification habits are the thing they violated.

- **Claimed `docs/demo-script.md` did not exist** on the strength of its name
  appearing in a required-documents list, and wrote a 130-line replacement.
  The file existed, ran to 209 lines, and was better in every respect. `git am`
  refused: `already exists in index`. The delivery mechanism caught what the
  author did not.
- **Claimed no command had ever been run from the Mac**, because none appeared
  in this session's context. `phase-13-a.patch` had been delivered from the Mac
  that morning.
- Both are the negative form of "a claim about state is not state", which the
  primer already stated in its positive form only. Added as its own habit in
  275d277.
- **Violated "ONE command at a time" for most of the session**, chaining dispatch,
  polling and verification into single blocks, and once labelled a command
  `[devbox]` while writing it in the `ssh devbox '...'` form that only works from
  the Mac. Both cost a round trip.
- A clone left in the session sandbox by an earlier chat was found still in
  place and heavily stale — no `scripts/`, no `site/`, no `promote-prod.yml`,
  ADRs stopping at 0019. The primer predicts exactly this; a fresh clone was
  taken instead.

## Not claimed

- `deploy-stage` #22 was read from the dashboard, not step by step. Its report
  was not opened.
- "Prevent self-review" was inferred from a successful self-approval, not read
  from the GitHub UI.
- The published Playwright report for `promote-prod` #5 was linked but not
  opened.
- No new ADR is proposed. The prod/stage asymmetry follows from ADR-0017's
  environment model plus the protection rules already recorded as UI state; it
  is a consequence, not a new decision.

## Follow-ups

```text
dashboard badge   render the green state with its observation age, or grey it
                  past a threshold. DESTROYED needs no such treatment.
one account       stage and prod share 993912191738. Isolated from the
                  Organizations management account, not from each other
                  (ADR-0017 D1 rejected a second workload account on schedule
                  cost; this run is the first time the pair ran end to end,
                  which is when that trade-off becomes worth revisiting).
```

## Cost

One prod cycle and one stage teardown. Everything billable was destroyed and the
destruction was verified against the AWS CLI, not against Terraform state.
