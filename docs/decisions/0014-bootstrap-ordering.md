# ADR-0014: Bootstrap ordering — two chicken-and-egg first runs

## Status
Accepted (Phase 0)

## Context
Two resources cannot be created in the normal flow because they are
prerequisites of that flow:
1. The S3 state bucket cannot be stored in the very state it is supposed to
   hold — it must exist before any `terraform init` with the S3 backend.
2. The GitHub OIDC deploy role is created by Terraform, but GitHub Actions
   cannot assume a role that does not exist yet — so it cannot create its own
   role on the first run.
Both must be resolved before CI can run applies.

## Decision
Both bootstraps run LOCALLY, once, under `AWS_PROFILE=demo-admin`, in Phase 6:
1. `infra/bootstrap/` (Terraform with LOCAL state) creates the state bucket
   before any backend init. Its `*.tfstate` is gitignored, never committed.
2. The FIRST `terraform apply` of `infra/envs/stage` runs locally, creating the
   OIDC provider and deploy role (module `iam_github_oidc`).
After both, GitHub Actions (`deploy-stage.yml`) authenticates via OIDC and runs
all subsequent applies.

## Alternatives considered
- Create the state bucket via raw `aws s3api` commands instead of Terraform:
  workable, but loses IaC consistency and the README/versioning/encryption in
  one place. Prefer `infra/bootstrap/`.
- Create the OIDC role by hand in the console: defeats the IaC goal and is not
  reproducible across cycles.

## Consequences
- Phase 4 only WRITES this code; the applies happen in Phase 6 after explicit
  confirmation. Phase 4 never runs apply.
- The state bucket survives every cycle (ADR-0004); the OIDC provider/role are
  recreated per cycle unless deliberately retained — documented in cost-control.
- This ordering is documented in README and docs/phase-gates.md so the first
  run is never attempted from CI.
