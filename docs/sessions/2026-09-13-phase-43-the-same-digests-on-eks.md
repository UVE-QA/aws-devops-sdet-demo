# Phase 43 — The same digests on EKS

**2026-09-13**, the same session, continued into the evening.
**ADR-0097**, one record, ten decisions, four slices, four cycles.

Item 3 of the plan: a third environment that runs the three images stage
tested on Kubernetes instead of ECS — beside stage and prod, reached from
the same button, torn down with them. Terraform makes the cluster and the
platform; a Helm chart in this repository installs the application by
digest; the page observes the cluster through kubectl. Discussed before
written — the owner took every recommendation in one line — and built in
four slices, each green on its own before the next.

## What was decided

A whole environment, not a cluster bolted onto stage: its own VPC, database,
secret, queue, state key and deploy role, so the comparison between the two
runtimes is a comparison and not a shared tenancy. Managed nodes rather than
Fargate, because the story is the second runtime and not the absence of
servers. Terraform owns the cluster, the node group, the OIDC provider, the
access entries, three IRSA roles, the namespace, the database Secret and the
load balancer controller; Helm owns three Deployments, two Services, one
Ingress and two ServiceAccounts, installed with `--atomic --wait`. IRSA is
the task role: each service account trusts one IAM role holding one
permission. Authentication mode API, the creator the first admin. The
teardown trap the plan named — a balancer the controller builds and
Terraform does not own — is met with the controller's default tags, so the
sweep can see it, and with an uninstall that waits for the balancer to be
gone before the destroy reaches the subnets. Checkov's three findings on the
cluster are decisions with reasons. The cost model prices the control plane
and the nodes from two more captured rates.

## Slice one and two, by hand

`infra/modules/eks` and `infra/envs/lab`, validated on nine levels; the lab
deploy role in `bootstrap-oidc`; `charts/demo` with a `chart-check` gate
(lint, render, and the refusal without digests). Then the cheap proof: a
local apply under `demo-admin`, which took three applies to go green and
found three things — the secret read raced the RDS create; an access entry
wants the SSO role's full ARN, path included; and the creator must not be
given a second entry. Cluster 9m24s, nodes 1m47s, controller 22s; the
chart's hooks and three pods up on the first install; the balancer tagged;
54 api contract tests and 2 smoke green through the Ingress, the worker
consuming through IRSA; uninstall and the balancer gone in 38 s; destroy 38
resources in 11m53s, the node group most of it.

## Slice three, by four cycles

The `lab` job beside `promote`, `destroy-lab` after it, the lab's uninstall
inside `destroy.yml`, five sweep arms, the adoption map's lab entries, the
observation's `eks` block. Then the cycles, each finding one thing the local
proof could not:

```text
#27  34770893807  failure   the publish role trusted stage and prod alone;
                            stage's and prod's sweeps asked their roles about
                            the lab's five role names and got AccessDenied
#28  34774107150  failure   CreateNodegroup validates its service-linked role
                            with the caller's iam:GetRole, and the deploy role
                            could not look
#29  34777285974  failure   the lab end to end in CI - apply 1146 s, chart,
                            the suites through the Ingress, teardown 13 m,
                            sweep clean, $0.04..$0.08 - and one red step:
                            the results fold found no suite.api.lab on the map
#30  34780714051  success   63 minutes, three environments, every job green
```

Three permanent levels changed on the way, each a one-line permission and
each applied with the owner's yes — the third under a standing yes the owner
gave for the day and for that kind of change alone. Two of the findings
reshaped scripts rather than roles: the sweep's channel for unindexed names
is per environment now, because an environment cannot have a role its deploy
role is not allowed to ask about; and the teardown uninstalls the chart
before the revocation and the sweep, because cycle #29's pre-destroy sweep
met the controller's balancer, listener and target groups and tried to adopt
a balancer into a configuration with no module for one.

The refusal ADR-0035 gained the day before was proven live during #27: a
nonce issued, a press posted, `409 busy — run #27, from branch next`, the
day's counter untouched.

## Slice four, the page

Three lab phases on the map — *Apply*, *Install* (the chart with its hooks),
*Quality gate* (api contract, smoke) — and `lab — everything above` under
*Destroy*; three environments everywhere the page listed two; the lab's panel
showing the cluster, the node group and the Deployments in place of three
services; the run layer reading the lab's documents. Twenty-seven lab
documents across every fixture family, synthesised from cycle #29's own with
the clock shifted; the in-flight gate's *figures dated* claim learned that
"the cycle that ended" over a destroyed environment at rest is true rather
than premature. Every page gate green before #30 ran, and #30 proved the
fold, the join and the documents.

## What the owner said on the way

The endpoint's lock does not see a cycle that did not come through the
button — asked during #26, fixed and applied the same evening, proven during
#27. The released line is asked for by name now, after the forty-run window
emptied of `main` and the panel read *No lifecycle run found* under a running
button. And the Cycle map follows `main` alone while a cycle from `next`
runs — acceptable while the work on `next` is a matter of days, recorded as
conditional: if it runs into the working week, the run in flight is to be
shown from any branch, named with its branch.

## The merge

`main` fast-forwarded to `next` on the owner's *да, вливай*: thirteen
commits, the whole of Phase 43 and the two page fixes. The published page
draws three environments and eleven phases. The estate is 200 resource
blocks across nine levels, 62 permanent and 138 per cycle.

## What is still open

The Cycle map for a `next` cycle, on the condition above. The services
manifest, which has five lists to reconcile now. The outbox with item 4.
From before: the lab site, the two blunted break tests, the release-tag 403.
