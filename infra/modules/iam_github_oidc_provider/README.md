# Module: iam_github_oidc_provider

Creates the GitHub OpenID Connect identity provider (no static keys, ADR-0003).

One per AWS account, because AWS allows exactly one OIDC provider per issuer
URL. The deploy roles that trust it live in `iam_github_deploy_role`, one
instance per environment (ADR-0021).

Applied locally under `demo-admin` from `infra/bootstrap-oidc`, in its own
remote state so that no environment teardown can delete it (ADR-0015).

## Thumbprint

`thumbprint` defaults to GitHub's known root CA thumbprint. Verify it is still
current at first apply and update if GitHub rotates it.
