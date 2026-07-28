---
name: tf-workflow
description: >
  Use for the mechanics of Terraform commands in any phase: "terraform plan",
  "terraform validate", "fmt the terraform", "what will this change", "review
  the plan", "apply the module", "format the tf files", "проверь terraform",
  "покажи план", "отформатируй". Covers fmt, validate (via make tf-validate,
  which is what actually needs no AWS creds), init against the S3 backend, plan,
  the apply/destroy confirmation rule, the seven root state levels and their
  apply order, plus local (demo-admin) vs CI (OIDC) auth.
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

## The seven root levels

Terraform here is not one configuration. Root levels are DISCOVERED by
`make tf-validate` — any directory with `.tf` files outside `infra/modules/` —
so a new one is validated the moment it exists.

```text
infra/bootstrap        permanent   local state; the bucket the others use
infra/bootstrap-oidc   permanent   OIDC provider + one deploy role per env
infra/shared-ecr       permanent   the registry prod promotes from
infra/dns              permanent   delegated zone + ALB certificate
infra/public-site      permanent   the dashboard; a destroy must NEVER touch it
infra/envs/stage       per cycle
infra/envs/prod        per cycle
```

On a fresh account the permanent five are applied LOCALLY, in that order
(`docs/preflight-inventory.md`). On this account they exist; a cycle starts at
`deploy-stage`.

## Format and validate (no AWS creds needed)

```bash
make tf-fmt        # terraform fmt -recursive infra
make tf-validate   # every discovered root level, isolated TF_DATA_DIR
```

**Do not hand-roll `terraform init -backend=false && terraform validate`.** This
skill used to teach exactly that, and it is wrong in a directory that has been
initialized for real: `-backend=false` does NOT skip the backend, it reuses the
cached S3 configuration in `.terraform/` and reads remote state. The claim "no
AWS credentials needed" was false on the devbox and passed in CI only because a
fresh checkout has no `.terraform/`. `make tf-validate` isolates `TF_DATA_DIR`
per level, which is what makes the claim true — and it is tested by re-running
with the AWS environment stripped.

An empty discovery result is an explicit failure, not a pass. A check that
validates nothing and prints nothing is the failure mode this project has
already had once.

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

## Targeted passes that are not optional

Two operations here are deliberately not a single plain command:

```text
destroy   the ALB module is destroyed FIRST, then everything else. Nothing in
          the configuration links the ALB to the internet gateway, so Terraform
          destroys them concurrently and AWS answers DependencyViolation on the
          detach while the ENIs are still attached (ADR-0016). destroy.yml does
          this; a hand-run destroy in envs/* must do it too.
apply     `app_image` has no usable default. A local apply must pass
          -var="app_image=<ECR_URL>:<sha>" or the service reverts to the
          :bootstrap placeholder. Actions sets TF_VAR_app_image itself.
```

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
