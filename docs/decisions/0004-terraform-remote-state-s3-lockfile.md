# ADR-0004: Terraform remote state in S3 with native lockfile

## Status
Accepted (Phase 0)

## Context
Terraform runs from two places: locally (operator under `demo-admin`) and from
GitHub Actions (OIDC). If state is local, the two diverge: resources created in
one place are invisible to the other, and the destroy workflow fails to find
resources, leaving billable infrastructure running. State must be shared.

## Decision
Use a remote S3 backend shared by local and CI runs. State bucket:
`aws-devops-sdet-demo-tfstate-993912191738`, versioning enabled, encryption
enabled, public access fully blocked. Locking uses the S3 native lockfile
(`use_lockfile = true`); no DynamoDB table. Key layout:
`stage/terraform.tfstate`, `prod/terraform.tfstate`.

## Decision details
- The bucket is created by a standalone `infra/bootstrap` with LOCAL state,
  before any backend init (see ADR-0014 for ordering).
- Each environment declares `backend "s3"` in `backend.tf`.
- The GitHub deploy role is granted S3 access to this bucket (see ADR-0003).

## Consequences
- Local and CI operate on one source of truth; destroy reliably finds and
  removes resources.
- No DynamoDB to provision or pay for; native lockfile is sufficient for a
  single-operator demo.
- The state bucket survives every deploy/destroy cycle (near-zero cost) and is
  intentionally excluded from teardown (see ADR-0011).
