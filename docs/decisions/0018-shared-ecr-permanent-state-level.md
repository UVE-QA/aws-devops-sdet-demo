# ADR-0018: The container registry is shared and lives at a permanent state level

## Status
Accepted (Phase 9.0). Amends the state-level model of ADR-0015 and ADR-0017.
Closes the ECR question that `docs/next-phases.md` 9.0 deliberately left open.

## Context

Promotion by digest is the core of the Phase 9 promotion path: `deploy-stage.yml`
builds an image once, and `promote-prod.yml` deploys **that same digest** to prod
without rebuilding. A rebuild would mean prod runs a different artifact from the
one the tests passed against, which defeats the point of having a promotion gate
at all.

Today the registry is declared inside the workload environments:

```text
infra/envs/stage/main.tf   module "ecr"  repository_name = "aws-devops-sdet-demo-app"
infra/envs/prod/main.tf    module "ecr"  repository_name = "aws-devops-sdet-demo-app-prod"
```

`docs/next-phases.md` identified the conflict between the per-environment prod
repository and promotion-by-digest, and named two candidate answers — one shared
registry, or an explicit cross-repository copy — while explicitly deferring the
choice until `promote-prod.yml` was about to be written. That moment is now,
because `infra/envs/prod` is being rewritten in this phase and should be
rewritten once.

**The parenthetical "(simplest)" attached to the shared-registry option was an
assumption, not a conclusion, and it is wrong as stated.** A shared registry that
stays inside `infra/envs/stage` is not simple; it is broken:

```text
module "ecr" lives in stage state, with force_delete = true
  -> destroy.yml for stage deletes the repository AND its images
  -> prod has promoted a digest FROM that repository
  -> prod's running tasks survive only until the next pull
  -> any restart, scale event or new task revision -> ImagePullFailure
```

Stage teardown is not an exceptional event in this project — it runs at the end
of every cycle, and `docs/next-phases.md` requires a green destroy at the end of
every phase. So the failure would be routine, and it would surface in prod,
asynchronously, well after the teardown that caused it.

This is the same shape as the two findings that produced this phase: something
written down, never traced along the path that would break it. It was written in
the same document that diagnosed that pattern in `infra/envs/prod`.

The project already has the principle needed to resolve it, stated in
`docs/session-primer.md`:

> Anything that must survive a teardown — including the artifact that PROVES the
> teardown works — belongs above the env levels.

A registry holding the artifact that prod is running is exactly such a thing. It
was simply never recognised as one, because until prod existed there was nothing
to promote and the registry could be rebuilt from source on the next cycle
without anyone noticing.

## Decision

1. **A new permanent state level `infra/shared-ecr/`** holds one ECR repository,
   `aws-devops-sdet-demo-app`, shared by every environment. Own state key
   `shared-ecr/terraform.tfstate` in the existing bucket. Applied locally under
   `AWS_PROFILE=demo-admin`, like `infra/bootstrap` and `infra/bootstrap-oidc`.
   No `terraform destroy` in the normal lifecycle.

2. **`module "ecr"` is removed from BOTH `infra/envs/stage` and
   `infra/envs/prod`**, along with the `ecr_repository_url` output. Removing it
   from stage in the same change is not incidental: leaving stage as the owner
   would keep exactly the deletion path this ADR exists to close.

3. **`force_delete = false`** on the shared repository. `force_delete = true`
   existed to make per-cycle teardown idempotent (ADR-0011); at a permanent level
   its only remaining effect is to make accidental image loss easier.

4. **A lifecycle policy bounds storage**: expire untagged images after 1 day,
   keep the most recent 10 tagged images. Without it a permanent registry grows
   without limit, and "budget-safe by default" becomes a claim rather than a
   property.

5. **The state-level model becomes SIX levels, not five.** Every document
   asserting five — `docs/session-primer.md`, `docs/discussion-log.md` — is
   corrected in the same commit as the code, per the shared-invariant rule
   adopted in Phase 9.0.

```text
1. infra/bootstrap        S3 state bucket. LOCAL state, applied once. Permanent.
2. infra/bootstrap-oidc   OIDC provider + deploy roles. Permanent.
3. infra/shared-ecr       container registry. Permanent.              (this ADR)
4. infra/public-site      dashboard S3+CloudFront. Permanent.         (Phase 11)
5. infra/envs/stage       workload. Destroyed every cycle.
6. infra/envs/prod        workload. Destroyed every cycle.            (Phase 9.1)
```

6. **`destroy.yml`'s verification step is updated.** It currently asserts that
   `aws ecr describe-repositories` comes back empty. That assertion becomes false
   by design, and a verification step that is expected to fail is worse than no
   verification step. It must assert that no *environment-scoped* repository
   remains, and state in a comment why the shared one is expected to survive.

## Consequences

**Removes a workaround rather than adding one.** `deploy-stage.yml` currently
runs `terraform apply -target=module.ecr` before the build, then resolves
`ecr_repository_url` via `terraform output`. Both exist only because the registry
did not exist in an empty stage state — the fix for bug `b71b846`, where an empty
output produced the docker tag `":<sha>"` and the step went green anyway. With a
permanent registry the repository always exists, and both steps disappear. That
retires the whole class of bug, not just the instance.

**The workflow still must fail loudly on a missing registry.** The lesson of
`b71b846` was not "resolve the URL differently", it was "an empty value must not
pass silently". The URL is now deterministic
(`<account>.dkr.ecr.<region>.amazonaws.com/aws-devops-sdet-demo-app`), but the
workflow must still verify the repository exists — via
`aws ecr describe-repositories --repository-names` — and fail if it does not.
Determinism is not existence.

**Cost.** ECR storage is ~$0.10/GB-month; the app image is a few hundred MB, so
this is cents per month, bounded by the lifecycle policy. The same order as the
state bucket, whose permanence is already accepted. It is a real change to the
claim "after teardown nothing bills", which becomes "after teardown nothing
bills beyond the state bucket and the registry, both cents". Say the honest
version; the reasoning is a better interview answer than the slogan.

**One more local apply per fresh account.** The cycle's local bootstrap becomes
three applies (`bootstrap`, `bootstrap-oidc`, `shared-ecr`) instead of two. Only
on a from-scratch account; the level survives normal cycles untouched.

**Images now outlive the environments that built them.** That is the point, and
it also means a stale image can be promoted. `promote-prod.yml` must take the
digest from a specific green stage run, never a floating tag such as `latest`.

**Watch:** the deploy role's IAM scope is written against ECR via `*` today, so
the level change needs no policy edit. If that statement is ever narrowed to
specific repository ARNs, the shared repository must be included — narrowing IAM
resources without re-deriving the action list is precisely how ADR-0016's
`iam:ListInstanceProfilesForRole` was lost.

## Alternatives rejected

**Cross-repository image copy in `promote-prod.yml`.** Keep per-environment
registries and copy the image from stage's to prod's during promotion. Rejected:
prod's registry is destroyed with prod anyway, so the copy must re-run on every
prod deploy; it adds a failure mode (a partial copy is a broken promotion) and it
makes "we never rebuild the artifact" true only in a narrow technical sense while
the bytes are moved around on each release.

**Shared registry left in `infra/envs/stage`.** The literal reading of
"one shared ECR" in `docs/next-phases.md`. Rejected: this is the broken
configuration described in Context — stage teardown removes prod's image.

**Registry folded into `infra/bootstrap-oidc`.** Fewer levels, and that level is
already applied locally at the right moment. Rejected: the level is named for,
and reasoned about as, the identity boundary. Mixing an artifact store into it
means neither the name nor any future ADR about it can stay accurate. Levels are
cheap; misleading names are not.

**Registry folded into `infra/bootstrap`.** Rejected: that level keeps LOCAL
state, which lives on the devbox. The registry must be manageable from CI and
from any machine, so it needs remote state.
