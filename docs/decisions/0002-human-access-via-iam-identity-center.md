# ADR-0002: Human access via IAM Identity Center (AWS SSO)

## Status
Accepted (Phase 0)

## Context
Operators need CLI and console access to the demo member account. Long-lived
IAM users with static access keys are a standing credential-leak risk and must
be rotated manually. The Organization already runs IAM Identity Center.

## Decision
Humans authenticate through IAM Identity Center (SSO portal
`https://d-90661cc65d.awsapps.com/start`, Identity Center in us-east-1) using
the `AdministratorAccess` permission set on the demo account, via the local AWS
CLI profile `demo-admin`. No static access keys for human operators.

## Decision details
- Local profile: `demo-admin` (SSO-based).
- Validate with:
  - `aws sso login --profile demo-admin --use-device-code`
  - `aws sts get-caller-identity --profile demo-admin` (Account must be the
    demo account, 993912191738).
- Terraform local runs export `AWS_PROFILE=demo-admin`.

## Consequences
- Credentials are short-lived and centrally revocable; nothing to rotate or
  leak in the repo.
- The first local Terraform applies (state bucket; first stage apply) run under
  this profile (see ADR-0014).
- Machine access (GitHub Actions) does NOT use SSO — it uses OIDC (see
  ADR-0003).
