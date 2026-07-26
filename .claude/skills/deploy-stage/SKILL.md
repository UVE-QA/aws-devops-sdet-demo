---
name: deploy-stage
description: >
  Use for deploying the stage environment to AWS end to end: "deploy to AWS",
  "deploy stage", "ship it", "push to ECR and deploy", "provision the
  environment", "first deploy", "set up OIDC", "run the deploy workflow",
  "задеплой", "разверни stage", "выкати на AWS", "первый деплой". Covers the
  full orchestration: bootstrap the S3 state bucket, the FIRST apply done
  LOCALLY (creates the OIDC provider + deploy role), then subsequent deploys
  via GitHub Actions OIDC, plus ECR push, migrate/seed via ecs run-task, and
  the post-deploy smoke + db-check.
  Do NOT use for: low-level terraform command mechanics alone (see tf-workflow),
  local Docker Compose (see local-dev), or destroying (see teardown).
---

# Deploy Stage (full AWS orchestration)

Brings the stage environment up on AWS. Two chicken-and-egg bootstraps make
ordering critical; get them wrong and the first deploy can't authenticate.

Target: Browser → ALB → ECS Fargate (one app container) → RDS PostgreSQL.

## One-time bootstraps (run LOCALLY, demo-admin)

1. **State bucket** — the S3 bucket can't live in state it doesn't yet hold.
   ```bash
   export AWS_PROFILE=demo-admin   # after: aws sso login --profile demo-admin --use-device-code
   cd infra/bootstrap
   terraform init && terraform plan
   terraform apply                 # only after confirmation; creates the bucket
   ```
2. **First stage apply, LOCAL** — creates the GitHub OIDC provider + deploy
   role. Actions cannot assume a role that does not exist yet, so this first
   apply must be local.
   ```bash
   cd infra/envs/stage
   terraform init                  # S3 backend
   terraform plan -out tfplan
   terraform apply tfplan          # only after confirmation
   ```

For Terraform command details, defer to `tf-workflow`.

## Subsequent deploys (GitHub Actions, OIDC)

`deploy-stage.yml` does: OIDC auth → ECR login → docker build/tag (commit
SHA)/push → terraform init/plan/apply → migrate → seed → wait steady →
smoke → db-assert → upload report. No static AWS keys.

## One-off tasks (migrate / seed / db-assert)

Reuse the SAME task definition with a command override — do not make separate
task defs.

```bash
aws ecs run-task --cluster <c> --task-definition <td> \
  --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}' \
  --profile demo-admin --region us-west-2
# seed:  ["python","scripts/seed.py"]
# check: ["python","tests/db/assert_seed.py"]
```

## Post-deploy verification

```bash
# ALB_URL from terraform output
curl -s "$ALB_URL/health"        # OK without DB
curl -s "$ALB_URL/api/db-check"  # connected after migrate+seed
aws ecs list-clusters --profile demo-admin --region us-west-2
aws rds describe-db-instances --profile demo-admin --region us-west-2
aws elbv2 describe-load-balancers --profile demo-admin --region us-west-2
```

Confirm the account is the dedicated demo account, never the management
account, and that the OIDC role ARN is in the demo account.
