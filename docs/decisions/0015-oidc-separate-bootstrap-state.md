# ADR-0015: GitHub OIDC provider + deploy role in their own bootstrap state

## Status
Accepted (Phase 8). Supersedes the OIDC-placement part of ADR-0014.

## Context
module.iam_github_oidc (GitHub OIDC provider, the Actions deploy role, and the
role's inline policy) used to live INSIDE infra/envs/stage. That made
destroy.yml fail end-to-end on Actions.

When destroy.yml runs terraform destroy UNDER the deploy role, and the OIDC
provider + deploy role + inline policy are part of the stage config being
destroyed, the running session deletes its OWN permissions mid-run. It then
fails on ec2:DetachInternetGateway, and (after the bad retry hack) can no longer
PutObject/GetObject the stage/terraform.tfstate.tflock to write state or release
the lock. Proven, not transient: after a failed run aws iam get-role succeeds
but aws iam list-role-policies is EMPTY. Both Phase-7 teardowns were finished
locally (demo-admin = AdministratorAccess).

## Decision
1. Move module.iam_github_oidc OUT of infra/envs/stage into a new
infra/bootstrap-oidc/ level with its OWN remote state
(key = bootstrap-oidc/terraform.tfstate). GitHub Actions only ever touches
stage/terraform.tfstate, never the OIDC state. destroy.yml therefore tears down
workload infra only; the deploy role survives the cycle, keeps its permissions,
writes state, and reaches completion.
2. Narrow the deploy role's IamManageScoped resources from role/<name_prefix>-*
to exactly the two ECS roles it must manage (<name_prefix>-ecs-execution and
<name_prefix>-ecs-task). The deploy role no longer matches its own ARN
(<name_prefix>-github-deploy), so self-deletion is impossible.
3. Scope the deploy role's GetSecretValue to a wildcard ARN pattern
(<name_prefix>-db-credentials-*) instead of a fixed secret ARN, because the OIDC
level is applied BEFORE stage exists and the DB secret carries a per-cycle
random suffix (recovery_window=0). The ECS execution role still uses the exact
secret ARN (created in the same stage apply).
4. Revert the retry commit (8d3ed9d): retries cannot wait for permissions that
were deleted rather than delayed. destroy.yml returns to a single
terraform destroy -auto-approve step.

github_oidc_role_arn is no longer a stage output; it is an output of
infra/bootstrap-oidc. Workflows already read the role ARN from the OIDC_ROLE_ARN
GitHub environment variable, so no workflow change is needed for that.

## Bootstrap ordering (updates ADR-0014)
Still two local-first runs per cycle, both under AWS_PROFILE=demo-admin:
1. infra/bootstrap/ creates the S3 state bucket (local state, gitignored).
2. infra/bootstrap-oidc/ creates the OIDC provider + deploy role (S3 state, key
bootstrap-oidc/terraform.tfstate).
Only after both does Actions take over: deploy-stage.yml and destroy.yml run
purely via OIDC, end-to-end, with no manual operations.

## Alternatives considered
- C1: -target/state rm to exclude the OIDC module from the stage destroy.
Rejected: fragile, must be remembered every cycle, leaves the role lingering in
state, and does not fix the self-scoped IAM permission.
- Keep the exact DB secret ARN, feed it into the OIDC level via
terraform_remote_state from stage. Rejected: re-couples the two levels and
breaks "the OIDC first apply is independent of stage".

## Consequences
- destroy.yml and deploy-stage.yml run end-to-end on Actions OIDC with no manual
step; the deploy role is stable across cycles.
- One extra local apply at the start of each cycle (bootstrap-oidc). This is
initialization by design, consistent with the "OIDC role survives every cycle"
invariant, not a per-cycle manual chore.
- Slightly broader secret scope (one prefixed wildcard vs one exact ARN) on the
deploy role only; acceptable for a demo and arguably more correct given the
per-cycle suffix.
