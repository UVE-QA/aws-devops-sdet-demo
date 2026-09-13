# Phase 41 — The container is two, and a release is a set

**2026-09-13**, one session, continuing the one that opened the phase.
**ADR-0095** verified by a cycle, and amended twice by the cycle that failed;
**ADR-0093 D2** amended by what the page said while it ran.

The phase was built on `next` on 2026-09-12 and proven locally: two images,
every suite through the web container, every gate green. This session ran it
for real, twice. The first cycle failed three ways and none of them was the
split. The second was green end to end, and `main` is `next` now.

## The two cycles

```text
#24  34731290270  02:45  failure   launch fell at `Terraform apply`; the
                                   teardown ran and its sweep went red;
                                   destroy-prod failed in 2 s with 0 steps
#25  34732345301  02:09  success   57 m — launch 17, promote 13, destroy 10,
                                   hold 5, destroy-prod 10, release-lock
```

Both were dispatched from `next` on the owner's word (*применяй и запускай
цикл сейчас*, then *да, применяй, добавляй next в policy и делай 3*). AWS
after each was read under `demo-admin`, not inferred: after #24 no roles,
clusters, instances, balancers or VPCs; after #25 the same, plus the default
VPC that was always there.

## What the first cycle found

**A name one character too long.** `${prefix}-web-tg` is 33 characters and
a target group's cap is 32; `terraform validate` does not know that, and the
plan refused before the apply. It is `${prefix}-web` now. The api's group
keeps `-tg`, which nothing renames.

**The deploy role still knew the old pair of roles.** `IamManageScoped` in
`modules/iam_github_deploy_role` granted `CreateRole … PassRole` on exactly
`<prefix>-ecs-execution` and `<prefix>-ecs-task`, and ADR-0095 D3 had turned
those into four. The apply never reached `CreateRole`, so it surfaced in the
sweep instead: `get-role` on four names the role was not allowed to ask about
came back `AccessDenied`, the one arm of `sweep-orphans.sh` that separates
*gone* from *could not ask* said *could not ask*, and the gate went red — as
designed, over the right thing, one layer away from the cause. Fixed as a
`flatten` over `["api", "web"]`, applied to `infra/bootstrap-oidc` under
`demo-admin` with the owner's yes: 0 to add, 2 to change, 0 to destroy. This
is the third place that knows the services by name; the manifest of plan
item 5 is where they meet. **ADR-0095 D9.**

**A job that fails before its first step.** `destroy-prod` was `failure` in
two seconds with zero steps and no log blob. The `prod` GitHub Environment
carried a deployment branch policy of `main` alone, and a job bound to
`environment: prod` from any other branch is refused before it starts —
`promote` would have met the same wall on a cycle that got that far. A cycle
from `next` that cannot reach prod is not the proof ADR-0093 D1 asks for, so
`next` was added to the policy with the owner's yes. The AWS side needed
nothing: the prod deploy role trusts `environment:prod` and no branch, and the
environment's own policy decides which branches may bind to it. Recorded in
the primer as UI state git cannot assert. **ADR-0095 D10.**

## What the page said while it ran

The owner sent a screenshot: **`stage — UNKNOWN`**, *Run #23 finished 21 h
ago and did not write a status file*, and three lines down, *written by
self-service #24 · 1 min ago*. Both true, and the panel was wrong.

ADR-0093's filter — the page reports the released line — was applied once,
at the source, so that every question the page asks would agree about which
runs it describes. Two of those questions are not about the released line.
*Is this reading the newest word on stage* was answered against the newest
run of `main`, which was a day old, while a `next` cycle had written the file
a minute earlier. *Is anything using the environments now* was answered the
same way, so the button stood open under a cycle that was using them — the
disagreement between halves ADR-0093 D3 had named and not enforced.

There is one stage, and whichever line's cycle touched it last is the newest
word on it. So `state.allRuns` keeps everything the API returned; the
staleness judgement and the busy state read it, and name a foreign run with
its branch, so a reader who cannot find `#24` in the history is told why in
the same sentence. The history, the panel, the quota and the estimate still
read the filtered list. **ADR-0093 D2 amended.**

Under gate: `check-page-inflight.mjs` has two more states, at-rest plus one
`next` run each — `foreign-writer`, whose file must read as current, and
`foreign-in-flight`, which must put stage in `unknown` by name and branch and
close the button. Both were run against the filtered rule first and failed
on every line they check; then against the new one and passed. The intruder
the two existing states plant moved older than the run that wrote stage's
file, so the *shown nowhere* claim and this one do not pull one fixture in
two directions. Not covered, and said so in the ADR: the *being torn down*
tense reads the released line's current run, so a `next` teardown shows as
`unknown` rather than as a teardown.

The live page kept saying `UNKNOWN` through the whole of #25, because the fix
was on `next` and the page publishes from `main`. That is the arrangement
working as written, and it is why the merge is the last step of a phase and
not the first.

## What the second cycle proved

Everything ADR-0095 promised, read from the account rather than from the
log: both images built and pushed in one job (29 s and 9 s); `terraform
apply` 477 s; both services stable; the api's execution role holding the
secret policy and the web's not; promotion pinning `api@sha256:6453b8…` and
`web@sha256:030f46…`; the pointer going from a bare pre-split digest — which
the workflow reported as *not armed*, exactly as D5 says — to `{api, web}` in
one put; `release-20260913-0240-0931b2f` in both registries;
`app.demo.uveapp.net/` answering 200 `text/html` from nginx and `/health` 200
from FastAPI through the listener rule; both teardowns green, the sweep now
confirming four roles instead of failing to ask about them.

## The merge

`main` was fast-forwarded to `next` on the owner's *да, вливай* — 94 files,
the whole of Phase 41 and the two fixes above. The published page carries
the amended D2 from that publish on. The precondition of ADR-0093 D1, a green
cycle from `next`, was met by #25 and by nothing before it.

## What is still open

From ADR-0093: the *being torn down* tense for a `next` teardown; the
deferred lab site (D4). From the plan: queue and worker, the EKS lab, data
ownership, the services manifest — which now has three lists to reconcile.
The two break tests that stopped biting, and the bucket release-tag 403 of
2026-09-05, are where they were.
