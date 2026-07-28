# 2026-07-28 — Phase 14, release resilience

Automatic rollback when a prod release fails, and a release identity that
cannot silently change. Closed the same day, including a full live cycle in
which a knowingly broken image was promoted on purpose.

## What the phase had to correct before it could start

The plan said "automatic rollback to the previous task definition". That does
not work here and the reason is structural, not a detail: Terraform owns the
service's task definition, and prod is created and destroyed on every cycle
(ADR-0017 D2a). `terraform destroy` deregisters the revision, and a deregistered
revision cannot start tasks. So at the moment a promotion fails, the previous
revision is absent or unusable — on *every* promotion, since every promotion is
the first of its cycle unless two happen without a teardown between them.

A mechanism whose target is missing on the normal path is not a mechanism. The
target became a digest pointer at a permanent level instead (ADR-0029), which is
the fourth time this project has independently arrived at "anything that must
survive a teardown belongs above the environment levels".

## What was built

```text
ADR-0029             release identity, immutability, rollback semantics
infra/shared-ecr     IMMUTABLE registry, max_image_count 10 -> 30,
                     the last-good-digest parameter with ignore_changes
infra/bootstrap-oidc ssm:GetParameter/PutParameter on that one parameter,
                     on the PROD role only - stage does not get the statement
deploy-stage.yml     :latest dropped; a re-run on the same commit reuses the
                     image instead of colliding with its own tag
promote-prod.yml     pointer read before the apply; three release records on a
                     green smoke; rollback by a second apply plus a re-run of
                     the smoke; two loud refusals when there is no target
```

Both permanent levels were applied locally under `demo-admin`. Neither is
touched by a cycle.

## What it found

- **The rollback trigger was too broad, and the live run is what showed it.**
  "The apply succeeded and something after it failed" also covers the release
  bookkeeping, which runs *after* the smoke goes green — so a failed git tag
  would have rolled back a prod that had just proved itself healthy. That is
  exactly what `promote-prod` #6 did, and the only reason nothing was rolled
  back is that the pointer was still empty. The condition is now "the apply
  succeeded AND the smoke did not pass", with a skipped smoke counting as not
  passed.
- **SSM reserves every parameter name beginning with `aws`**, and this project is
  called `aws-devops-sdet-demo`. The apply failed with `AccessDeniedException:
  No access to reserved parameter name`, which reads exactly like a missing IAM
  grant and is nothing of the kind. The path gained a `/release/` prefix and the
  reason is written at the resource, so the segment does not get tidied away
  later. This is the sixth time the "a genuinely new path costs one failed run"
  prediction was made and the first in five where it was right — and the first
  in a while where the failure was on the AWS side at all.
- **A runner has no committer identity**, so `git tag -a` exits 128 with
  `empty ident name`, three seconds into a step that had already published the
  ECR half of the release.
- **`aws_ecr_lifecycle_policy` is REPLACED, not updated, when its policy changes.**
  The stop-condition stated before the apply — "any destroy or replace, stop" —
  was too coarse and had to be retracted after reading the plan: the registry
  itself was `~ update in-place` and only the policy resource was `-/+`.
  Retracted with the reasoning shown rather than waved through.
- **`gh run view --log` and `--log-failed` both returned nothing** for a failed
  run, which is indistinguishable from "no failures". The job-level API
  (`actions/jobs/<id>/logs`) returned 2202 lines immediately.
- **`TF_VAR_budget_email` is a GitHub *variable*, not a secret**, so GitHub does
  not mask it and it appears in the step env dump of a public repository's logs.
  Noticed while reading an unrelated log. Not fixed here; see follow-ups.

## What was observed, and how

```text
deploy-stage #23    success 16m05s, image 05f17955..., no :latest pushed
promote-prod #6     smoke GREEN, pointer written, ECR tag
                    release-20260728-0434-05f1795 created, git tag FAILED;
                    the empty-pointer refusal printed verbatim
promote-prod #7     broken image; services-stable failed 9m53s; smoke skipped;
                    rollback resolved, applied, and the RE-RUN smoke passed;
                    run red. 15m00s
prod task def       revision 7 carried @sha256:b9d47c3f..., read from the ECS
                    API rather than from the run that claimed the rollback
destroy prod #16    success 10m22s (behind the approval gate, as in Phase 13)
destroy stage #17   success 9m01s
teardown            alb/rds/ecs/nat/eks all empty from the devbox under
                    demo-admin, sts first, each result assigned under `&&` -
                    and all of them non-empty from the same commands 20 min
                    earlier
expired-digest      exercised on the devbox with a digest that had genuinely
refusal             just been deleted; the same command answered `present` for
                    a live digest, so the check was seen working in both
                    directions
```

One thing confirmed by accident and worth keeping: on #7 `Set up Node.js` was
skipped, and the rollback's re-run smoke still worked. The comment claiming the
runner's preinstalled Node makes that step independent of the setup step is
therefore true, and was tested rather than assumed.

## Deliberate deviations, recorded rather than hidden

- **The broken image was built on the devbox and pushed straight to ECR**, not
  produced by `deploy-stage`. It bypasses "promote only what stage tested", which
  is precisely the rule the test needed to violate, and it kept a knowingly
  broken commit out of `main` and out of CI. Its tag was deleted afterwards.
- **The git tag for `release-20260728-0434-05f1795` was created by hand**, after
  #6 failed at that step. The release genuinely happened — the image is in prod,
  the ECR tag and the pointer both exist — so this reconciles git to observed
  reality rather than inventing it, and the tag's own message says it was made
  by hand and why.

## Not claimed

- The Playwright report published by #7 was linked but not opened.
- prod was never fetched from an outside host this session. Its health rests on
  the workflow's own smoke and on the ECS API, not on a browser.
- The `ci` annotation warnings were not read, again.
- The two untagged manifests left in the registry after deleting the broken tag
  were identified only by their push time, which matches the devbox push. What
  they are was not established; the untagged rule expires them in a day.

## Follow-ups

```text
budget email      TF_VAR_budget_email is a variable, so it is printed in the
                  logs of a public repository. Moving it to secrets is one UI
                  change plus `${{ secrets... }}` in three workflows.
dashboard badge   unchanged from Phase 13: the green state has no observation
                  age. Seen again today, stage reading UP three hours after its
                  last observation.
one account       unchanged from Phase 13.
```

## Cost

One stage cycle and one prod cycle, with prod up for about 2h40m across two
promotions. Everything billable was destroyed and the destruction was verified
against the AWS CLI, not against Terraform state.
