# ADR-0095: The container is two, and a release is a set

## Status
Accepted (Phase 41, 2026-09-13). Item 1 of the plan in **ADR-0094**. Reshapes
**ADR-0018**'s single registry into one per service, **ADR-0029**'s release
pointer into a release, and the ECS module of Phase 6 into a cluster and a
service. Does not touch ADR-0006 (no NAT), ADR-0005 (no plaintext secrets) or
ADR-0025's suite split. Narrows **ADR-0077 D2**: the board's column count is
still the estate's, and is capped now.

## Context

The application was one container serving two things: `/api/*` and `/health`
from FastAPI, and a single static `index.html` from `/`, whose JavaScript calls
`/api` on the same origin. The plan's first step is to make that two
containers, and the reason is not the containers. It is what a release becomes
when there are two of them.

The owner's decisions, taken before a line was written:

> app/ оставляем, include ок, ecr готовь, плитку делим … сужать не надо -
> добавляем следующий ряд

## Decision

**D1. The cut is at the origin, and nothing calls anything.** `web` is nginx
serving what the api used to serve from `/` — the static interface, moved to
`web/static/` — plus `/healthz`. `api` is the FastAPI service without `/`. The
browser talks to one load balancer, whose listener sends `/api/*` and
`/health` to the api's target group and everything else to web's. No
server-side rendering, no backend-for-frontend, no service-to-service call, no
CORS: there is nothing yet for two services to say to each other, and a seam
invented before it is needed is a seam nobody tested.

**D2. Routing is the load balancer's, and locally the web container stands in
for it.** Two target groups and one listener rule on the listener that forwards
(`:443` with TLS, `:80` without). On the devbox there is no load balancer, so
`web/nginx.conf` includes `conf.d/local/*.conf` and Compose mounts a proxy for
`/api/` and `/health` there; the AWS image carries the directory empty. One
named difference between the two, in one file, rather than teaching nginx a
routing it does not own in the cloud.

**D3. The ECS module is a cluster and a service.** `modules/ecs-cluster` makes
the cluster; `modules/ecs-service` makes a security group, two roles, a task
definition and a service, and is instantiated as `api` and as `web`. What is
per service is per service on purpose: the api's execution role reads the
database secret and the web's cannot, the RDS group allows 5432 from the api's
group and from nothing else. The policy that grants the read is a plain
resource of the environment attached to the api's role, not a `count`ed one
inside the module: a resource that exists in one instance of a module and not
the other is one the orphan-adoption gate, which reads modules, cannot tell
apart - and it said so. The old module went with no state migration, because
the environments it built are destroyed at the end of every cycle.

**D4. One repository per service, and the api keeps the old one.** Renaming an
ECR repository is creating a new one, and the api's history is in
`aws-devops-sdet-demo-app`; `aws-devops-sdet-demo-web` is added beside it in
`infra/shared-ecr`, a permanent level, applied by hand under `demo-admin` with
the owner's word. The deploy role already holds `ecr:*`, so nothing in
`bootstrap-oidc` moves.

**D5. A release is a set of digests, and the tag is its name.** The commit
SHA is still the tag, and it names one image in each repository; promotion
resolves both digests and pins both. The rollback pointer in SSM holds a JSON
object, `{api, web}`, written in one put at the moment the prod smoke goes
green — so it can never name a web from one release beside an api from
another. A rollback rolls back the set or nothing: a pointer that still holds
the pre-split shape, a bare digest, names the api alone and is reported as
*not armed* rather than used. The release tag goes into both registries.

**D6. Built one after the other, in the same job.** A matrix would build the
two in parallel and hand their digests to the next job through artifacts; that
plumbing belongs with the services manifest of plan item 5, where the list of
services it needs will live. Two steps cost about a minute and no machinery.

**D7. The board splits the tile and wraps the row.** *ECS Fargate* becomes
*ECS — api* and *ECS — web*; the cluster is a hidden group, the room both
services run in and a property of neither. Nine nouns in prod would have
squeezed every tile to 160px at 1512, and the owner's answer was a next row,
not a narrower tile: the column count stays the estate's and is capped by how
many 10.5rem tiles fit - what eight measure across the 1512px board today -
and both rows wrap at the same column so VPC still sits
over VPC. `generate-topology.py` learned to assign one module's blocks to a
different tile per instance, keyed `<dir>@<call>`.

**D8. The scan covers every image it builds.** `make image-scan` iterates over
both; a scan over one of two images would be the vacuous green this project
keeps finding one layer down.

**D9. The deploy role names the four roles, and it is a permanent level.**
*Added after the first cycle, 2026-09-13.* `IamManageScoped` in
`modules/iam_github_deploy_role` granted `iam:CreateRole … PassRole` on exactly
two ARNs, `<prefix>-ecs-execution` and `<prefix>-ecs-task`, which D3 renamed
into four. The first cycle never reached `CreateRole` — a target-group name
was 33 characters against a cap of 32, and the plan refused before the apply
— so it surfaced in the sweep instead: `get-role` on four names the role was
not allowed to ask about, `AccessDenied` read as *unconfirmed*, red. Fixed as
`flatten([for service in ["api", "web"] : …])` and applied to
`infra/bootstrap-oidc` under `demo-admin` with the owner's yes: 0 to add, 2 to
change, 0 to destroy — the two deploy policies, in place. The target group is
`${prefix}-web` (the api's keeps `-tg`, which nothing renames). This list is
now the third place that knows the services by name, after the module and
`adopt_orphans.py`; the services manifest of plan item 5 is where they meet.

**D10. The `prod` environment admits `next`.** The same cycle's `destroy-prod`
failed in two seconds with zero steps and no log: the GitHub Environment `prod`
carried a deployment branch policy of `main` alone, and a job bound to that
environment from any other branch is refused before its first step. `promote`
would have met the same wall. A cycle from `next` that cannot reach prod is not
the proof ADR-0093 D1 asks for, so `next` was added to the policy with the
owner's yes (`POST …/environments/prod/deployment-branch-policies`). The AWS
side needed nothing: the prod deploy role trusts `environment:prod` and no
branch (ADR-0021), and the environment's own policy is what decides which
branches may bind to it. Recorded in the primer as UI state git cannot assert.

## Consequences

- Locally, every suite passes through the web container: 52 api contract, 2
  smoke, 12 regression, all against `http://localhost:8000` where the page and
  `/api` now share one origin. Both images scan clean — the web image, on
  alpine, with nothing at all to report.
- The published estate gains a tile per environment: 17 nouns across two rows,
  135 resource blocks in `infra/`, 58 permanent, 77 per cycle - counted, not
  written.
- The cycle grows by roughly a minute for the second build and a little for the
  second service's stability, and by one Fargate task's worth of cost.
- `scripts/adopt_orphans.py` knows the two services' names - security groups,
  services, target groups, four roles - and the api's role drags its two
  policies into state while the web's drags one; 113 unit tests say so,
  including a new one for the web role.
- The `Build` phase draws two nodes with their own steps; every fixture that
  named `build.ecr`, `stage.ecs` or *Build, tag, and push image* was rewritten,
  and the frozen `live-state/phases.json` was refreshed and the approval's
  binding put back by hand, as its `refresh.py` says to.
- The observation of an environment names the api service by name rather than
  taking whichever the API listed first, and carries the web service beside it;
  the panel's disclosure shows both.
- **Verified by the second cycle from `next`** (#25, 34732345301, 2026-09-13,
  57 minutes, every job green) after the first (#24) failed on the three things
  D9 and D10 record and on a target-group name. Both images built and pushed
  in one job (29 s and 9 s); `terraform apply` 477 s; both services stable;
  the tests through the web container on stage; promotion pinned
  `api@sha256:6453b8…` and `web@sha256:030f46…`, the pointer went from a bare
  pre-split digest — reported *not armed*, as D5 says — to `{api, web}` in one
  put, and `release-20260913-0240-0931b2f` went into both registries;
  `app.demo.uveapp.net/` answered 200 `text/html` from web and `/health` 200
  from the api through the listener rule; both teardowns green, the sweep
  confirming the four roles rather than failing to ask; the account afterwards
  holds the default VPC and nothing else billable.
