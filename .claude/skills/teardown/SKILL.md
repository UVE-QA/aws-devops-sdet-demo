---
name: teardown
description: >
  Use when destroying or tearing down the demo environment, after a demo, or to
  stop all AWS billing: "destroy", "teardown", "tear it down", "clean up AWS",
  "stop the costs", "remove everything", "снеси", "погаси", "удали всё",
  "останови расходы", "убери окружение", running destroy.yml or terraform
  destroy for infra/envs/stage. Covers the confirm=DESTROY gate, the
  post-destroy verification step, what survives the cycle (the state bucket),
  and confirming a clean, repeatable teardown so the next deploy works.
  Do NOT use for: building infra (see deploy-stage), routine terraform
  plan/apply (see tf-workflow), or local docker compose down (see local-dev).
---

# Teardown (stop all AWS cost)

This environment is repeatedly deployed → demoed → destroyed. A clean teardown
both stops billing and keeps the next deploy idempotent (no name clashes).

## Preferred path: destroy.yml (GitHub Actions, OIDC)

`workflow_dispatch` with inputs `environment` (stage/prod) and `confirm`.
The job fails unless `confirm` is exactly `DESTROY`. It runs OIDC auth →
`terraform destroy -auto-approve` → a verification step.

## Local fallback (demo-admin)

```bash
export AWS_PROFILE=demo-admin   # after aws sso login --use-device-code
cd infra/envs/stage
terraform init
terraform destroy               # only after explicit confirmation
```

## Post-destroy verification (must be clean)

Verify against the AWS CLI, never against Terraform state, and **start with the
identity check**. Every query below answers an expired SSO token with an empty
list, which reads exactly like a clean account:

```bash
aws sso login --profile demo-admin --use-device-code
export AWS_PROFILE=demo-admin AWS_REGION=us-west-2
aws sts get-caller-identity --query Account --output text   # must be 993912191738
```

Only then:

```bash
aws ecs list-clusters             --query 'clusterArns'
aws rds describe-db-instances     --query 'DBInstances[].DBInstanceIdentifier'
aws elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerName'
aws ec2 describe-nat-gateways     --filter Name=state,Values=available,pending
aws eks list-clusters             --query 'clusters'
aws ec2 describe-addresses        --query 'Addresses[?AssociationId==null].PublicIp'
aws ec2 describe-vpcs             --filters Name=isDefault,Values=false
aws logs describe-log-groups      --query 'logGroups[].logGroupName'
aws secretsmanager list-secrets   --query 'SecretList[].Name'
```

Expected: all nine empty. If anything cost-bearing remains, surface it loudly —
do not leave it running. In a script, assign each result to a variable under
`set -e` so a failed call aborts instead of printing an empty line.

## What intentionally survives

Destroying an environment must NOT remove any of these. A teardown that takes
one of them has taken too much:

- `infra/bootstrap` — the Terraform state bucket. Near-zero cost, needed by the
  next deploy.
- `infra/bootstrap-oidc` — the account-wide OIDC provider and the per-environment
  deploy roles (ADR-0015, ADR-0021). IAM, free. The question of whether to keep
  them is settled: they are a permanent level, because a destroy running under a
  role that deletes its own permissions cannot finish.
- `infra/shared-ecr` — the container registry (**ADR-0018**). The image prod runs
  is the one stage tested, so a registry inside an environment would be deleted
  by that environment's teardown, taking the promoted image with it. An ECR
  repository still present after a destroy is CORRECT, not a leak.
- `infra/dns` — the hosted zone for `demo.uveapp.net` and the wildcard
  certificate (**ADR-0024**). The alias record pointing at the ALB lives in the
  environment and does go away; the zone does not.

## Repeatability check

After a destroy, a fresh `deploy-stage` must succeed with no name conflicts
(Secrets Manager recovery window 0, ECR force_delete, Terraform-managed log
group). If a re-deploy fails on an existing name, that is the bug to fix.
