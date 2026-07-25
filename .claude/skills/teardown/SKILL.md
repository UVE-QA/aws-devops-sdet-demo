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
export AWS_PROFILE=demo-admin   # after aws sso login
cd infra/envs/stage
terraform init
terraform destroy               # only after explicit confirmation
```

## Post-destroy verification (must be clean)

```bash
aws ecs list-clusters            --profile demo-admin --region us-west-2
aws rds describe-db-instances    --profile demo-admin --region us-west-2
aws elbv2 describe-load-balancers --profile demo-admin --region us-west-2
aws ec2 describe-nat-gateways    --profile demo-admin --region us-west-2
aws eks list-clusters            --profile demo-admin --region us-west-2
aws ec2 describe-addresses       --profile demo-admin --region us-west-2
aws ecr describe-repositories    --profile demo-admin --region us-west-2
```

Expected: no ECS/RDS/ALB, no NAT, no EKS, no unattached EIP, app ECR repo gone.
If anything cost-bearing remains, surface it loudly — do not leave it running.

## What intentionally survives

- The Terraform state bucket (`infra/bootstrap`) — near-zero cost, needed for
  the next deploy. Never part of the destroy cycle.
- Optionally the OIDC provider/role, if you keep them between cycles. Document
  which choice this repo made.

## Repeatability check

After a destroy, a fresh `deploy-stage` must succeed with no name conflicts
(Secrets Manager recovery window 0, ECR force_delete, Terraform-managed log
group). If a re-deploy fails on an existing name, that is the bug to fix.
