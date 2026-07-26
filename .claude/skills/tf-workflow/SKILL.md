---
name: tf-workflow
description: >
  Use for the mechanics of Terraform commands in any phase: "terraform plan",
  "terraform validate", "fmt the terraform", "what will this change", "review
  the plan", "apply the module", "format the tf files", "проверь terraform",
  "покажи план", "отформатируй". Covers fmt, validate (with -backend=false so
  no AWS creds are needed), init against the S3 backend, plan, and the
  apply/destroy confirmation rule, plus local (demo-admin) vs CI (OIDC) auth.
  Do NOT use for: the full first-deploy orchestration with bootstrap, OIDC and
  migrations (see deploy-stage), or tearing everything down (see teardown).
  This skill is the low-level Terraform engine those skills build on.
---

# Terraform Workflow (command mechanics)

This is the low-level engine: how to run Terraform safely against the shared
S3 state. Higher-level skills (deploy-stage, teardown) call into this flow.

## Auth

- Local: `export AWS_PROFILE=demo-admin` (run `aws sso login --profile
  demo-admin --use-device-code` first; SSO sessions expire).
- CI: GitHub OIDC assumes the deploy role. No static keys anywhere.

## Format and validate (no AWS creds needed)

```bash
terraform fmt -recursive
terraform validate            # in a module dir
# For env dirs that declare the S3 backend, validate without initializing it:
terraform init -backend=false && terraform validate
```

Doing validate with `-backend=false` is what lets CI validate without AWS
credentials.

## Init against the shared S3 backend (needs creds)

```bash
cd infra/envs/stage
terraform init                # configures the S3 backend + state lock
```

State is remote in S3 with `use_lockfile = true`. Local and CI share the same
state — never switch to local state, it will diverge and break destroy.

## Plan

```bash
terraform plan -out tfplan
terraform show tfplan         # review before applying
```

Always read the plan. Flag any resource that creates ongoing cost
(RDS, ALB, ECS service, NAT, EIP) before applying.

## Apply / destroy — confirmation rule

Never run `terraform apply` or `terraform destroy` without explicit user
confirmation. State the cost impact, then wait.

```bash
terraform apply tfplan        # only after confirmation
```

## Provider lock (consistency across devbox + CI)

```bash
terraform providers lock -platform=linux_amd64 -platform=linux_arm64
```

Commit `.terraform.lock.hcl` so provider hashes match in CI.
