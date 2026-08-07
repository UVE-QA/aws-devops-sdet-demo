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
  - AdministratorAccess  -> assigned to admin-temp on the demo account AND on
                            the management account. The second assignment was
                            not written down until Phase 19b needed it to read
                            the organization's policy types; a document that
                            understates access is how a session concludes it has
                            none.
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
  TF_VAR_DEMO_ACCOUNT_ID, TF_VAR_OWNER.
- **TF_VAR_BUDGET_EMAIL is an environment SECRET, not a variable** (Phase 15,
  2026-07-28), and it is environment-scoped in the same way: it must exist in
  BOTH `stage` and `prod`, or `terraform plan` fails with "No value for required
  variable" — loudly, which is the intended failure. A variable is not masked,
  so as a variable it was printed in the logs of a public repository.
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

- Owner tag value: `UVE` — the value of the GitHub variable `TF_VAR_OWNER`, and
  what is actually on every resource in the account. This line previously said
  `papers.usher.3m@icloud.com`, which nothing had ever been tagged with; that is
  the budget alert address, and it is recorded under Budget Alerts above. Checked
  2026-07-26 against `get-bucket-tagging`, `list-tags-for-resource` and
  `list-role-tags`.
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
6a. infra/self-service  the button: control store, three Lambdas, Function URL,
                        EventBridge schedule, SNS topic, secret CONTAINER.
                        Run `make self-service-package` FIRST - the apply
                        refuses a package under 500 KB. Needs provider ~> 6.0,
                        which only this level uses (ADR-0034, Phase 19b).
6b. the GitHub App       created by hand, installed on the repository with
                        `actions: read-write`, private key pasted into the
                        secret created by 6a. App id and installation id go in
                        infra/self-service/terraform.tfvars; the key never
                        touches git or a chat session. Until both ids are set,
                        the endpoint refuses every launch with `not_configured`.
6. infra/public-site    dashboard bucket + CloudFront + us-east-1 certificate
                        + the narrow publish role (ADR-0027). Needs 4 and 5
                        done: it reads the hosted zone by name, so the plan
                        fails outright if the zone is absent.
7. GitHub environment variables for stage and prod, and prod's protection rules
8. GitHub REPOSITORY variables for the dashboard, from the infra/public-site
   outputs - see below
9. infra/self-service   the public launch endpoint and its refusals (ADR-0034).
                        LAST, and optional: everything above works without it,
                        and it is the only level that holds a long-lived
                        credential. Needs `make self-service-package` first.
                        APPLIED 2026-08-05 (Phase 19b), 25 resources, about
                        $0.45/month standing. Duplicated as 6a above, which is
                        where the package and the GitHub App are described.
```

### When the deploy role's policy changes

`infra/bootstrap-oidc` is a permanent level and the only thing that grants the
GitHub deploy roles anything. A change there does NOT reach AWS through any
workflow - Actions assumes the role, it does not create it - so it has to be
applied locally, exactly like the steps above:

```bash
aws sso login --profile demo-admin --use-device-code
AWS_PROFILE=demo-admin terraform -chdir=infra/bootstrap-oidc apply
```

`tag:GetResources` was added this way for the orphan sweep (**ADR-0037** D4,
Phase 19f). A workflow that needs a grant which is not there fails with an
AccessDenied naming the API and not the role, so check this first when a step
that used to work stops.

### The out-of-git state step 9 depends on (Phase 19b)

Same category as the NS record in step 5 and prod's protection rules in step 7 -
real state git cannot assert, listed here because that is where someone rebuilding
will look:

```text
the GitHub App, with `actions: write` on this repository and nothing else
its installation on UVE-QA/aws-devops-sdet-demo
its private key, pasted BY HAND into the Secrets Manager secret the level
  creates. Terraform makes the container and never holds the key.
```

If a launch ever returns 401, check those three before anything else. The
repository variables the launch workflow's release job needs come from that
level's outputs, and are identifiers like the four above:

```text
AWS_REGION                       us-west-2
SELF_SERVICE_CALLBACK_ROLE_ARN   from `terraform output callback_role_arn`
SELF_SERVICE_TABLE               from `terraform output control_table_name`
```

All three were created on 2026-08-05, in Phase 19c, AFTER the first real cycle
failed on the last of its three jobs. The two below the region had been written
down here since 19b and never actually set: a list of what something needs is
evidence that someone wanted it, never that it is there.

`AWS_REGION` is the addition, and the reason it was not predicted is worth more
than the value. It already existed on the `stage` and `prod` environments, which
is where every other job reads it. The release job is the only one that declares
`environment: self-service` - an environment GitHub creates by itself on the
workflow's first run, empty - so it read the variable from a scope that had
nothing in it and got the empty string. A missing variable is not an error, so
the failure surfaced in `configure-aws-credentials` as a missing input, three
jobs and twenty-three minutes away from the omission. `self-service.yml` now
checks all three up front and names every one that is absent.

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
