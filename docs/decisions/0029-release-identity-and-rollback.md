# ADR-0029: A release is a digest that passed prod smoke, and rollback targets a pointer that outlives the environment

## Status
Accepted (Phase 14). Builds on ADR-0018 (the registry is permanent) and
ADR-0017 D2a (prod is created and destroyed on every cycle). Fourth application
of the rule stated in ADR-0027.

## Context

Phase 14 asks for two things: automatic rollback when the prod smoke fails, and
release versioning with image immutability by digest. Half of the second already
existed — `promote-prod.yml` resolves the dispatched tag to a digest and pins
`TF_VAR_app_image` to `<url>@sha256:...`, so prod runs the exact bytes stage
tested. What did not exist was any enforcement that a tag keeps meaning the same
digest, any record of what was released, and any rollback at all.

The obvious reading of "roll back to the previous task definition" does not
survive contact with this project's environment model.

```text
aws_ecs_service.app.task_definition = aws_ecs_task_definition.app.arn
```

Terraform owns the service's task definition, and prod is destroyed at the end
of every cycle. `terraform destroy` deregisters the revision, and a deregistered
revision cannot start new tasks. So at the moment a promotion's smoke fails,
the previous revision of that family either does not exist or is unusable —
on **every** promotion, not on an unlucky one, because every promotion is the
first promotion of its cycle unless two happen back to back without a teardown
in between.

A rollback mechanism whose target is absent on the normal path is not a
mechanism. It is a step that would have only ever been seen refusing.

## Decision

### 1. The digest is the identity; a release is a digest that passed prod smoke

Not the tag, not the commit. Tags point at digests and the commit describes
intent; only the digest names the bytes that ran. A digest becomes a *release*
at exactly one moment: when the read-only smoke against prod goes green.

That moment does three things at once, or none of them:

```text
ECR tag    release-<UTC yyyymmdd-hhmm>-<short sha>  added to the promoted digest
git tag    the same name, annotated, on the promoted commit
pointer    /aws-devops-sdet-demo/prod/last-good-image-digest = that digest
```

Adding a new tag to an existing manifest is permitted under an immutable
registry; what immutability forbids is repointing a tag that already exists.

### 2. The registry becomes immutable and `latest` is dropped

`image_tag_mutability = "IMMUTABLE"` on the shared repository, with no
exclusion rule, because there is nothing to exclude. `deploy-stage.yml` pushed
`:latest` alongside `:<sha>` and **nothing has ever read it** — no workflow, no
module, no script, no Makefile target. ADR-0018 already forbade promoting a
floating tag. Keeping a mutable pointer inside a registry whose entire claim is
immutability would preserve a convenience nobody used at the cost of the
property everything else depends on.

### 3. The rollback target is an SSM parameter at a permanent level

The last-good digest lives in Parameter Store, created by `infra/shared-ecr`:
the level that already owns the release artifact, and one of the levels that is
never destroyed. This is the same argument as ADR-0018, ADR-0024 and ADR-0027,
reaching the same conclusion for the fourth time: **anything that must survive a
teardown belongs above the environment levels**, and a rollback target is
useless precisely when the environment it names has just been rebuilt.

Standard-tier parameters are free.

### 4. Rollback is a second `terraform apply`, not an `update-service`

On smoke failure `promote-prod` re-applies `infra/envs/prod` with
`TF_VAR_app_image` set to the pointer's digest, waits for the service to
stabilise, and **re-runs the smoke against the rolled-back version**.

Re-applying rather than calling `aws ecs update-service` keeps Terraform
authoritative. An `update-service` rollback would leave the service running one
revision while state described another — drift that the next apply would
silently undo, in an environment where "the next apply" is the next release.

Re-running the smoke is what stops this from becoming another gate that is only
ever seen green: a rollback that restored a broken service would otherwise report
success.

**The run fails regardless.** Rollback is damage control, not a pass. A promotion
whose smoke failed is a failed promotion even when the recovery worked, and the
release tags and the pointer are not written.

### 5. Refuse loudly rather than roll back to nothing

Two cases where there is no usable target, both of which end the run with an
explicit message and prod left standing for inspection:

```text
pointer empty      the first promotion after this ADR ships, exactly once
digest missing     the pointer names an image the lifecycle policy expired
```

The second is checked against the registry before the rollback apply is
attempted, not assumed. `max_image_count` rises from 10 to 30 to make it
unlikely; verifying is what makes it safe. ECR lifecycle rules only ever expire
and cannot protect a prefix, so there is no configuration that removes this case
— only a cap that makes it rare and a check that makes it visible.

## Consequences

- **Two permanent levels need a local apply under `demo-admin`**, from the
  devbox, before any of this works in Actions: `infra/shared-ecr` for the
  parameter and the immutability flag, and `infra/bootstrap-oidc` for the prod
  deploy role's new `ssm:GetParameter` / `ssm:PutParameter` on that one
  parameter path. The deploy policy already carries `ecr:*`, so the release tag
  needs no IAM change. Both applies are free and neither is destroyed by a cycle.
- **`promote-prod.yml` gains `contents: write`**, needed to push the annotated
  git tag. It is a widening of the most privileged workflow in the repository and
  is recorded here rather than left to be noticed in a diff. It applies to the
  repository, not to AWS; the AWS side is unchanged and still has no static keys.
- Schema rollback is an explicit **non-goal**. Migrations are forward-only and
  the image rollback does not touch them. This is tolerable only because prod
  keeps no data between cycles (ADR-0017 D2a), and it stops being tolerable the
  moment Phase 17 gives prod continuity — at which point this ADR needs a
  successor, not an amendment.
- The rollback path adds roughly three to four minutes to a failing promotion:
  a second apply, a stability wait, and a second smoke run. A successful
  promotion is unaffected.
- The pointer is per-environment by path even though only prod writes one today.
  A stage rollback would be a new parameter, not a new design.
- Deleting the parameter is enough to disarm rollback, and would do so
  silently on the next failure — the refusal in §5 is what makes that audible.
