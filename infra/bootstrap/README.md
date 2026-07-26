# infra/bootstrap — Terraform state bucket

Creates the S3 bucket that holds Terraform remote state for `stage` and `prod`.
This is the FIRST of two chicken-and-egg bootstraps (see ADR-0014); the second
is the first local `apply` of `infra/envs/stage`, which creates the GitHub OIDC
provider and deploy role.

## Why this is separate

The state bucket cannot be stored in the very state it is meant to hold. So this
config uses **local state** (no `backend "s3"` block) and is applied once,
locally, before any environment runs `terraform init` against the S3 backend.

Its local state files (`*.tfstate`) are gitignored and must never be committed.

## When it runs

Phase 6, once, locally, under the SSO profile. NOT in Phase 4 (Phase 4 only
writes this code) and NOT from GitHub Actions.

## Usage (Phase 6 — do not run in Phase 4)

```bash
aws sso login --profile demo-admin --use-device-code
aws sts get-caller-identity --profile demo-admin   # confirm demo account 993912191738
export AWS_PROFILE=demo-admin

cd infra/bootstrap
terraform init                                     # local state, no S3 backend
terraform plan \
  -var="state_bucket_name=aws-devops-sdet-demo-tfstate-993912191738" \
  -var="owner=UVE"
# apply only after explicit confirmation — creates the state bucket
terraform apply \
  -var="state_bucket_name=aws-devops-sdet-demo-tfstate-993912191738" \
  -var="owner=UVE"
```

## After apply

The bucket exists with versioning, SSE (AES256), and public access fully
blocked. Then configure `backend "s3"` in `infra/envs/{stage,prod}` and run
`terraform init` there.

## Teardown

This bucket is intentionally NOT destroyed in the deploy -> demo -> destroy
cycle (ADR-0004, ADR-0011); it has near-zero cost and retains state across
cycles. `force_destroy = false` guards against accidental deletion.
