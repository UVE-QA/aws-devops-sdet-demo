# Phase 47 — The services, declared once

**2026-09-15**, on `next`. **ADR-0101**, one record, five decisions; item 6
of the plan begun, slice 6a. No cycle: nothing the cycle runs was written.

## What the owner asked

> давай начнем насколько времени хватит
> главное не оставить демо в промежуточном нерабочем состоянии

Two constraints in two lines, and they decide the slice. Whatever is built
today must leave `main` exactly as the recruiters see it, and must leave
`next` in a state worth merging even if the session stops mid-way. So the
slice that reads every copy of the services and writes none of them: the
manifest and the gate that holds the copies to it. The generators reading
it, and anything generated from it, come after.

## What was found before anything was written

Seven places declare the services, and none of them knows about the
others. `docker-compose.yml` builds three (the api's still called `app`).
`infra/envs/stage/main.tf` and `prod/main.tf` hold an `ecs-service` module
each, with the port as a variable, the health as a command, the queue URLs
as environment, the secret as an argument, and a policy per queue direction
named after the service. `infra/modules/alb/main.tf` sends `/api/*` and
`/health` to the api and the rest to the web. `charts/demo` has an
`images.<name>` key per service, a Deployment each with `containerPort` and
probes, and an Ingress with the balancer's paths. Six build steps in two
workflows name a repository and a context each. Three Dockerfiles `EXPOSE`
a port or deliberately not. `scripts/lab-install.sh` lists the repositories
it resolves to digests, and `scripts/generate-schema.py` carries a table of
which module is which service. The api's port is `8000` in three of them
because one person typed it three times.

## What was built

`services.json` in the repository root: one entry per service - name,
image, build context, compose name, port, health, routes, queues, database,
suites - every field a fact one of the copies already stated. JSON and not
YAML, on the owner's *json ок*: the gate runs on python3 with nothing
installed, and `gates.json` and `topology-groups.json` are already JSON
with `_`-keys for their own commentary.

`scripts/check-manifest.py`, as `manifest-check` in `assets/gates.json`
(local; 14 gates runnable on the devbox now). Forward: every service in the
manifest is in every copy with the same image, context, port, health,
routes, queue environment and policies, secret, probes and Ingress paths.
Backward: every service any copy declares is in the manifest - an
`ecs-service` module, a compose service that builds, an `images.*` key or a
Deployment template, a build step, a `REPOS` entry, an `ECS_SERVICES` row.
It reads text, not parsers - top-level Terraform blocks, two-space compose
children, `key: value` chart lines - and compares everything it reads, so
a misreading refuses rather than passes.

Proven before it was wired, on five corruptions of a copy of the tree:

| corruption | what the gate said |
|---|---|
| chart `containerPort: 8080` | `api.yaml: containerPort ['8080'], the manifest says 8000` |
| balancer rule without `/health` | `rule "api" forwards ['/api/*'], the manifest says ['/api/*', '/health']` |
| a `module "sidecar"` appended | `module "sidecar" is an ecs-service that services.json does not declare` |
| manifest: api port 8001, worker consumes nothing | six findings across the Dockerfile, both environments and the chart |
| `web` build step renamed | `builds aws-devops-sdet-demo-ui from ./web, which services.json does not declare` and `no build step pushes aws-devops-sdet-demo-web` |

Item 5 set DONE in the plan; its roadmap item and tile left
`topology-groups.json` under ADR-0094's own rule, and the manifest's tile
took the band.

## Slice 6b, the same session

*давай 6b, пока время есть.* `scripts/generate-schema.py` carried its own
table of the three services - group, observation path, chart placeholders,
the balancer's targets, the IRSA groups - and 6a had compared it with the
manifest. Now it reads the manifest: the ECS parts and their observation
paths from `status_key`, the target groups from `routes`, the IRSA groups
from the names, the `helm template` placeholders from the names and the
chart's own `serviceAccounts` values. The regenerated `schema.json` is
byte-identical to the hand-tabled one except the target groups' source
line and the header. Both generators refuse a declared service the estate
would not draw - proven with a `sidecar` appended to the manifest: the
topology generator names the missing `ecs_sidecar` group, the schema
generator the environment that draws none. `manifest-check` now holds
`observe-environment.sh` to `status_key` in place of the table it no
longer has to compare.

## Slice 6c, the same session: the workflows

*давай workflows, matrix по манифесту.* Before writing, one finding: the
page lights the three `ECR push` nodes by the names of the build steps, and
a GitHub matrix is a job, not a step. A `build` job per service would be a
new job the page's phases, the progress watcher and `release-lock` do not
know - the cycle reshaped, not the workflows. Said to the owner with both
prices; the owner chose the steps: *да, делай второе, потом цикл*.

So the three build steps stay three and each says one word:
`scripts/build-service.sh api "$IMAGE_TAG"`. `scripts/service-images.sh`
turns the manifest into what a workflow needs - `repos`, `tag <tag>`,
`digests <json>` - as JSON keyed by name, and writes one step output per
service beside the whole set, so `TF_VAR_api_image` can name a service and
a loop names none. `promote-prod` resolves the release, records the last
good set, tags every repository and resolves a rollback through it; the
pointer arms only when its keys are exactly the manifest's names.
`lab-install.sh` the same. Fifteen spellings of the repository names across
four workflows and a script are gone, and `manifest-check` refuses one that
comes back, a build step without a service, a service without a step, a
step the page would not light, and a `build.*` node without a service.

The SSO token had expired and the owner was asked to log in; meanwhile a
stand-in `aws` in PATH proved every mode and every refusal of the script,
the pointer in five shapes, the record, the tags and a build's reuse path.
The cycle from `next` is the proof that counts, and the owner allowed it.

Then the owner logged in and the real registry answered the same way as
the stand-in: three URLs, three digests for the last green launch's tag,
the live pointer resolving to three images, a never-built tag refused with
the reason. #36 from `next`, launched at 06:00 UTC: green end to end in 66
minutes, every job. The three images built by name on the first attempt;
promote resolved the release through the manifest, saw the pointer as an
armed set of three, recorded `{api, web, worker}` and put
`release-20260915-0634-fb2092b` in all three repositories through the loop;
the lab installed what the script resolved. Merged to `main` on the
owner's *да, вливай*.

## The two verdicts, and the plan closed

The owner, asked the two questions that were the owner's: the picture's
translucency - *leave as is for now*; the plan band once its last item is
done - *убрать блок совсем*. And a correction worth keeping: *matrix* had
been read as the GitHub construct, when what the owner wanted was only
that the service tiles show what is really going on - which they do, by
the steps' names and by the observations, and which is why the three build
steps stayed three. The chart and the modules were weighed as generator
output and declined (ADR-0101 D7); item 6 is done; the plan of 2026-09-12
is complete. The `What comes next` band left the page with its data and
its refusals, and `generate-topology.py` refuses a `roadmap` key now.

## What is still open

The tail the plan left behind, on the owner's word: per-service database
users (ADR-0098 D2), a lab site, the blunted break tests, the release-tag
403, the size of `runs.json`. The picture's translucency, open to a later
verdict.
The owner's verdict on the picture's translucency, still pending. Per-service
database users (ADR-0098 D2), the lab site, the blunted break tests, the
release-tag 403, the size of `runs.json`.
