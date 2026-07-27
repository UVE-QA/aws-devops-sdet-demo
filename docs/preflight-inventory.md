# Preflight Inventory (Phase 0)

> Do not paste secrets into this document.
> No access keys, passwords, tokens, or private SSH keys.
> Only safe identifiers and references are recorded here.

Status: Phase 0 and Phase 1 completed and confirmed.

## AWS Organization

- Existing dedicated demo account: yes
- Management account ID: 029280391941 (org-management / root — do not deploy into it)
- Demo account name: devops-sdet-demo
- Demo account ID: 993912191738
- OU: Projects
- Organization ID: o-p25t094r1c
- Control Tower: not used
- Billing/budget visibility: available in management account

## IAM Identity Center / AWS SSO

- IAM Identity Center region: us-east-1
- Instance ARN id: ssoins-722369375982df70
- Identity store ID: d-90661cc65d
- SSO start URL: https://d-90661cc65d.awsapps.com/start
- Initial setup principal: admin-temp
- Permission sets:
  - AdministratorAccess  -> assigned to admin-temp on the demo account (initial build)
  - AutomationAccess     -> intended for Terraform / CI
  - ReadOnlyAccess       -> read-only inspection
- AWS CLI profile: demo-admin (SSO, region us-west-2, output json)
- Verified: aws sts get-caller-identity --profile demo-admin -> Account 993912191738

## AWS Region

- Primary deployment region: us-west-2

## GitHub

- Owner/org: UVE-QA
- Repository: aws-devops-sdet-demo (**Public** since 2026-07-26, ADR-0022)
- SSH remote: git@github.com:UVE-QA/aws-devops-sdet-demo.git (works from devbox)
- Default branch: main
- GitHub Actions: enabled
- GitHub environments: stage, prod. Variables are ENVIRONMENT-scoped and are not
  inherited: prod carries its own AWS_REGION, OIDC_ROLE_ARN (the prod role),
  TF_VAR_DEMO_ACCOUNT_ID, TF_VAR_BUDGET_EMAIL, TF_VAR_OWNER.
  prod additionally has 2 protection rules — required reviewers (UVE-QA) and
  `main` as the only deployment branch, administrator bypass disabled. That is
  UI state; git cannot assert it.
- Git identity on devbox: UVE-QA / papers.usher.3m@icloud.com
- Local clone: /home/ubuntu/aws-devops-sdet-demo

## Lightsail Devbox

- Instance name: devops-sdet-devbox
- OS: Ubuntu 24.04 LTS
- Size: 2 GB RAM / 2 vCPU / 60 GB ($12/mo)
- AZ: us-west-2a
- Static IP: 34.213.147.86
- Private IP: 172.26.4.52
- Firewall: SSH/22 only
- Installed toolchain:
  - Docker 29.5.3
  - Docker Compose v5.1.4
  - AWS CLI 2.34.63
  - Terraform 1.15.5
  - Node.js 20.20.2
  - Python 3.12.3
  - Git 2.43.0
  - Make 4.3
  - GitHub CLI 2.45.0 (added 2026-07-26; runs workflows, reads run logs, manages
    environment variables, approves deployments)
  - dnsutils (dig)

### Devbox operating notes

- `aws sso login` needs **`--use-device-code`**. The default flow opens a
  callback on `127.0.0.1`, which on a headless box resolves to the laptop's
  loopback and never reaches the CLI waiting here.
- `gh auth login` likewise: `--git-protocol https --web` avoids the SSH-key
  upload prompt entirely. git keeps pushing over SSH; gh only needs API access.
- `make tf-validate` used to leave ~700MB per root level in /tmp on every run.
  Fixed 2026-07-26; if a disk-full appears again, check `/tmp/tmp.*` first.

## DNS

- Public name of prod: `app.demo.uveapp.net` (exists only while prod is up).
- Delegated zone `demo.uveapp.net` lives in the DEMO account, Terraform-managed
  by the permanent level `infra/dns` (ADR-0024). Zone id Z0075526IEV5ME131TFQ.
- Wildcard certificate `*.demo.uveapp.net`, ACM us-west-2, DNS-validated, free.
- Parent zone `uveapp.net` is in **org-management (029280391941)** and holds one
  manual `NS` record for `demo`. That record is untracked by git and is the first
  thing to check if prod's name stops resolving.
- Trap: a SECOND, non-authoritative hosted zone for `uveapp.net` exists in an
  unrelated account, 478937318617 (`vlad.urban.qa`), outside this Organization.
  It looks complete and serves nobody. Ground truth for the delegation is
  `dig +noall +authority NS uveapp.net @a.gtld-servers.net`.

## Budget Alerts

- Budget alert email: papers.usher.3m@icloud.com

## Resource Tagging

- Owner tag value: papers.usher.3m@icloud.com
- Project tag: aws-devops-sdet-demo

## Terraform Remote State

- State bucket (created in Phase 4 bootstrap): aws-devops-sdet-demo-tfstate-993912191738
- State region: us-west-2
- Locking: S3 native lockfile (use_lockfile = true), no DynamoDB

## Manual steps, per fresh account

Everything below is applied LOCALLY under `AWS_PROFILE=demo-admin`, in order,
before any workflow can run. All of it exists today; this list is for rebuilding
from nothing.

```text
1. infra/bootstrap        S3 state bucket
2. infra/bootstrap-oidc   OIDC provider + one deploy role per environment
3. infra/shared-ecr       the shared container registry
4. infra/dns              hosted zone + wildcard certificate
5. one NS record for the delegated zone, by hand, in the parent zone
   (org-management) - see the DNS section above
6. infra/public-site    dashboard bucket + CloudFront + us-east-1 certificate
                        + the narrow publish role (ADR-0027). Needs 4 and 5
                        done: it reads the hosted zone by name, so the plan
                        fails outright if the zone is absent.
7. GitHub environment variables for stage and prod, and prod's protection rules
8. GitHub REPOSITORY variables for the dashboard, from the infra/public-site
   outputs - see below
```

### Repository variables for the dashboard (Phase 11.1b)

Repository-level, not per environment, because both environments publish to the
same bucket with the same values. The six variables in step 7 differ per
environment and stay where they are.

```text
SITE_BUCKET             aws-devops-sdet-demo-site-<account id>
SITE_DISTRIBUTION_ID    from `terraform output distribution_id`
SITE_PUBLISH_ROLE_ARN   from `terraform output publish_role_arn`
SITE_URL                https://demo.uveapp.net
```

All four are identifiers, not credentials: the role ARN names a role that can
only be assumed by a token this repository's workflows produce, and only for
`environment:stage` or `environment:prod`.

Still outstanding, non-blocking:

- VS Code Remote-SSH deferred; working via Lightsail browser SSH for now.
- Delete the stray `demo` NS record in the non-authoritative zone (478937318617).
- The GitHub variable `TF_STATE_BUCKET` on the stage environment is referenced by
  nothing and should go.
