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
- Repository: aws-devops-sdet-demo (Private)
- SSH remote: git@github.com:UVE-QA/aws-devops-sdet-demo.git (works from devbox)
- Default branch: main
- GitHub Actions: enabled
- GitHub environments: stage (prod later)
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

## Budget Alerts

- Budget alert email: papers.usher.3m@icloud.com

## Resource Tagging

- Owner tag value: papers.usher.3m@icloud.com
- Project tag: aws-devops-sdet-demo

## Terraform Remote State

- State bucket (created in Phase 4 bootstrap): aws-devops-sdet-demo-tfstate-993912191738
- State region: us-west-2
- Locking: S3 native lockfile (use_lockfile = true), no DynamoDB

## Missing Prerequisites / Next Manual Steps

- Terraform state bucket not yet created (Phase 4, infra/bootstrap, local apply).
- GitHub OIDC provider + deploy role not yet created (first local stage apply, Phase 6).
- VS Code Remote-SSH deferred; working via Lightsail browser SSH for now.
