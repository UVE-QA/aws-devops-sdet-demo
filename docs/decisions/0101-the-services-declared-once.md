# ADR-0101: The services, declared once

## Status
Accepted (Phase 47, 2026-09-15). Item 6 of the plan **ADR-0094** records,
its first slice. Applies **ADR-0085**'s shape - one fact, N copies, one
check - to the services themselves. Changes nothing **ADR-0095**, **0096**,
**0097** or **0098** built; the copies those decisions wrote stay where they
are and are compared now.

## Context

The plan's last item reads *a services manifest: the pipeline, the estate and
the dashboard derived from a declared list of services instead of from one
container*. The four items before it built the services; each one added a
service by hand to every place that names one, and by the end of item 4
there were seven such places that had never met:

- `docker-compose.yml` - three services that build, the api's still called
  `app`;
- `infra/envs/stage/main.tf` and `infra/envs/prod/main.tf` - an
  `ecs-service` module each, with the port as a variable, the health check
  as a command, the queue URLs as environment, the secret as an argument,
  and an IAM policy per queue direction named after the service;
- `infra/modules/alb/main.tf` - the listener rule that sends `/api/*` and
  `/health` to the api and everything else to the web, and a target group
  per routed service with its own health path;
- `charts/demo` - an `images.<name>` key per service, a Deployment template
  per service with `containerPort`, probes and the same environment, and an
  Ingress with the same paths as the balancer's rule;
- the build steps of `self-service.yml` and `deploy-stage.yml` - six of
  them, each naming a repository and a build context;
- the three Dockerfiles, each `EXPOSE`ing a port or deliberately not;
- `scripts/lab-install.sh`'s list of repositories to resolve to digests, and
  `scripts/generate-schema.py`'s table of which module is which service.

Nothing compared them. The api's port is `8000` in a Terraform default, a
chart literal and a Dockerfile, and they agree because one person typed all
three. The way this repository has learned to read such a state (ADR-0085,
ADR-0094 D2, `assets/gates.json`) is: the copies will drift the day someone
adds a fourth service in five of the seven places, and nothing will say so.

The owner's word on 2026-09-15, after the shape was argued: *json ок,
делай*.

## Decision

**D1. `services.json`, in the repository root.** One entry per service the
cycle builds, deploys and observes: `name` (what the estate calls it, what
the module's `service` argument and the chart's `images.<name>` key say),
`image` (the ECR repository), `context` (the build directory), `compose`
(its name in the compose file, kept because the api's is historically
`app`), `port` (null for a service behind no balancer), `health` (a path
when the runtime probes over HTTP, else the command every copy runs),
`routes` (the balancer's path rules that reach it; `default` for the
listener's default action; empty for a service nothing routes to),
`queues` (what it publishes and consumes, by the queue modules' names),
`database` (the schema its migrations own, and where they are; null for a
service with no database) and `suites` (the Makefile targets that exercise
it). Nothing in it is new: every field is a fact one of the seven copies
already states, moved to the one place it will be stated first.

JSON and not YAML, and in the root and not `assets/`: the gate that reads it
runs on python3 with nothing installed (`assets/gates.json`: `local`), and
PyYAML is a dependency the repository does not otherwise carry; JSON with
`_`-keys for its own commentary is what `gates.json` and
`topology-groups.json` already are. The root, because the file is about the
pipeline and the estate, not about the page - it sits beside
`docker-compose.yml` and the `Makefile`, the two other files that say what
the project is made of.

**D2. `manifest-check`, both directions.** `scripts/check-manifest.py`
reads the manifest and then every copy, and refuses on each disagreement it
finds - it does not stop at the first, so one run names everything that
drifted. Forward: every service in the manifest is in every copy, with the
same image, context, port, health, routes, queue environment and policies,
secret, probes and Ingress paths. Backward: every service a copy declares
is in the manifest - an `ecs-service` module in stage or prod, a compose
service that builds, an `images.*` key or a Deployment template in the
chart, a build step, a `REPOS` entry in `lab-install.sh`, a row of
`ECS_SERVICES`. The backward direction is the one `gates.json`'s checker
taught: a list that only checks what it names can shrink in silence, and a
service added in one place and not the manifest must be red.

Text, not parsers: Terraform blocks are read as top-level `kind "name" {`
blocks closed by a `}` at column 0, compose services as two-space
children of `services:`, the chart as `key: value` lines. A reader that
misread one would refuse loudly rather than pass quietly, because
everything it reads is compared with something. Proven before it was wired
by five corruptions of a copy of the tree: a chart port changed, a
balancer route dropped, an undeclared module appended, the manifest itself
drifted in two fields, a build step renamed - each named by file and by
what the manifest says instead.

**D3. In the one list of gates, local.** A row in `assets/gates.json`
between `chart-check` and `schema-check`; `make gates` runs it on the
devbox and in CI's gates step, `session-close` runs it. `gates-check`
discovers it by its name.

**D4. Nothing is generated from it in 6a; the generators read it in 6b.**
The first slice makes the fact exist and holds the copies to it. The second,
the same day on the owner's *давай 6b*: `scripts/generate-schema.py` drops
its own table of the three services - which module is which group, where
the page reads each one's numbers, which chart values `helm template` needs,
where the balancer's rules go, which IRSA role is which group - and reads
`services.json` instead; the service-account placeholders come from the
chart's own values file, so the chart says which services carry a role. The
regenerated `schema.json` is byte-identical to the hand-tabled one except
the target groups' source line, which now says where the routes were read
from. Both generators refuse a declared service the estate would not draw:
`generate-topology.py` when `topology-groups.json` has no `ecs_<name>`
group, `generate-schema.py` when an ECS environment draws none. The
manifest gained `status_key` - the key under `resources` the observer
writes a service's ECS reading to, the api's the historical `ecs_service` -
and `manifest-check` holds `observe-environment.sh` to it, in place of the
table it no longer needs to compare. Whether the chart, the modules or the
workflows are ever generated from it is a separate decision each, with a
separate reason. A manifest that generated everything on its first day
would be a rewrite of four working decisions for the sake of a blueprint,
and the demo is being handed to strangers this week.

**D6. The workflows name a service and nothing else about it.** On the
owner's *давай workflows, matrix по манифесту*, and after one finding
changed the shape: the page lights the three `ECR push` nodes by the
**names of the build steps** (`Build, tag, and push the api image`, in
`launch` and in `deploy`), and a GitHub matrix is a job, not a step - a
`build` job per service would be a new job the page's phases, the progress
watcher and `release-lock` do not know, a reshaping of the cycle rather
than of the workflows. So the three steps stay three, and each carries one
word: `scripts/build-service.sh api "$IMAGE_TAG"`. The manifest says the
repository and the context; `scripts/service-images.sh` - `repos`, `tag
<tag>`, `digests <json>` - turns the manifest into what a workflow needs,
JSON keyed by name, and with `--output <prefix>` one step output per
service (`ref_api`) beside the whole set (`refs`), so an apply's image
variables name one service and a loop names none. `promote-prod` resolves
the release's digests, records the last good set, tags every repository
and resolves a rollback target through it; the pointer is armed only when
its keys are exactly the manifest's names, so a service added to the
manifest disarms rollback until the first green release writes the whole
set. `lab-install.sh` resolves its digests the same way. Fifteen spellings
of the repository names across four workflow files and a script are gone;
`manifest-check` refuses a spelled one, a build step for a service the
manifest lacks, a service with no build step, a step not named the way the
page lights it, an image variable for a service that does not exist, and a
`build.<name>` node on the page with no service - or a service with no
node. Proven before the cycle on a stand-in `aws` in PATH: every mode, every
refusal, the pointer in five shapes, the record, the tags, the reuse path
of a build. A real job-level matrix, with the page's phase model reshaped
for it, stays a separate decision.

**D5. Item 5 is done and leaves the page's plan band.** The schema layout
has been on the released page since #32 (ADR-0099), so its roadmap item and
its tile leave `assets/topology-groups.json` under ADR-0094 D2's own rule -
a tile leaves the band the day the board draws the thing. The manifest item
stays, with one tile that names this ADR, until item 6 is done.

## Consequences

- Adding a service means editing `services.json` and the seven copies, and
  forgetting any one of the eight is a red `manifest-check` naming the file.
  Before this ADR it meant editing seven and hoping.
- The manifest states what is; it does not yet decide anything. Until 6b, a
  reader who wants the truth about a service reads `services.json` and can
  trust it exactly as far as the gate is green - which is the same trust
  `topology.json` earns from `site-data-check`.
- The api's compose name `app`, and its target group's name `app`, are the
  two places the history of one container still shows. Both are declared
  rather than renamed: a rename would touch the ECR repository name, the
  image scan and every workflow for no reader's benefit, and the manifest's
  `compose` field and the checker's one-line map are where the mismatch is
  said out loud.
- Slice 6a on `next`, merged on the owner's word after green CI; no cycle
  launched for it, because nothing the cycle runs changed - the copies were
  read, not written. Slice 6b the same day: the schema and the topology are
  derived from the manifest or refuse without it, the pipeline's copies are
  held to it. What the plan band shows once its last item is done is a
  question the generator refuses to answer alone - it refuses an empty plan
  as an invented one (ADR-0094 D2) - and is the owner's to settle before
  item 6 is closed.
- D6 changes what the cycle runs - every build, the promotion's digests,
  the release record and the lab's install - so it is proven by a cycle
  from `next` before it is merged, and the rollback path by the stand-in
  alone: a failed prod smoke is not something a green cycle exercises, and
  a deliberately broken release is a break test for another day.
  Proven by #36 from `next` on 2026-09-15: 66 minutes green, the pointer
  written as the set of three by the new record step, the release tag in
  all three repositories by the loop, the lab installed from the script's
  digests.
- Adding a service is now: `services.json`, a Dockerfile and a compose
  service, the ecs-service module in stage and prod with its policies, the
  chart's values and a Deployment, a build step named for the page and a
  `build.<name>` node, the observer's key. Nine places, one gate naming
  the one that was forgotten; before item 6 it was the same nine and hope.
