# Prompt for Claude Code: AWS DevOps/SDET Demo Platform v1

## Role

You are working as an autonomous senior DevOps / Cloud / SDET engineer inside a new Git repository named:

```text
aws-devops-sdet-demo
```

Your task is to help build the first working version of a portfolio/demo project that demonstrates AWS Organizations-aware deployment, IAM Identity Center / AWS SSO, GitHub Actions CI/CD, Terraform IaC, Docker, ECS Fargate, ECR, ALB, RDS PostgreSQL, Playwright smoke testing, DB assertions, and safe teardown.

This is **v1 of the implementation prompt**.

Important: this project must be built **phase by phase**. Do not skip ahead. Do not proceed to the next phase until the user explicitly confirms that the previous phase is complete.

---

# 0. Execution Model: Mandatory Phase Gates

You must follow a gated execution model.

## 0.1 Core Rule

At the end of every phase:

```text
STOP.
Print a concise checklist of what was completed.
Print exact validation commands.
Ask the user to confirm completion before continuing.
Do not start the next phase until the user explicitly confirms.
```

Acceptable confirmation examples:

```text
continue
confirmed
done
phase complete
go next
```

If the user reports an error, fix that phase only. Do not advance.

## 0.2 Do Not Batch Everything

Do not generate or modify the entire project in one uncontrolled pass unless explicitly asked.

The correct flow is:

```text
Phase 0 → collect/discover required context
STOP for confirmation

Phase 1 → prepare Lightsail devbox docs/checks
STOP for confirmation

Phase 2 → create local app skeleton
STOP for confirmation

Phase 3 → local Docker Compose + tests
STOP for confirmation

Phase 4 → Terraform foundation
STOP for confirmation

Phase 5 → GitHub OIDC + workflows
STOP for confirmation

Phase 6 → first AWS stage deploy
STOP for confirmation

Phase 7 → destroy validation
STOP for confirmation

Phase 8 → next-phase feature expansion
```

## 0.3 Safety Rule

Never ask for or store raw secrets.

Do **not** request:

```text
- AWS access key secret
- AWS secret access key
- AWS root password
- GitHub personal access token value
- database password value
- private SSH key contents
```

Instead, collect only safe identifiers and references:

```text
- AWS account IDs
- AWS account names
- AWS Organization OU names
- IAM Identity Center permission set names
- AWS CLI profile names
- IAM role names/ARNs
- GitHub owner/repo names
- GitHub environment/secret variable names
- region names
- email address for budget alerts, if the user chooses
```

Secrets must be provided out-of-band by the user directly into AWS, GitHub, local environment variables, or SSO-based auth flows.

---

# 1. Main Goal

Create a minimal but complete end-to-end delivery chain:

```text
Developer on Lightsail devbox
  → AWS SSO login to dedicated demo member account
  → git push
  → GitHub
  → GitHub Actions CI
  → GitHub Actions OIDC assume-role into demo account
  → Docker build
  → ECR push
  → Terraform deploy
  → ECS Fargate app service
  → RDS PostgreSQL
  → migration task
  → seed task
  → Playwright smoke test
  → DB assertion
  → destroy workflow
```

The demo must be suitable for interviews for roles such as:

```text
DevOps Engineer
Cloud Engineer
QA Automation Engineer
SDET
```

The value of the project is not the app itself. The value is the delivery flow, account isolation, infrastructure, automation, testing, environment lifecycle, and cost control.

---

# 2. AWS Account Model

The user already has an AWS Organization with project/member accounts. IAM Identity Center / AWS SSO is used for human authentication.

The demo must be deployed into a **dedicated AWS Organizations member account**, not into the management account.

Recommended target account:

```text
Account name: devops-sdet-demo
Purpose: portfolio/demo AWS account
OU: Sandbox / Demo / Workloads, depending on existing org structure
Region: us-west-2
```

## 2.1 Account Separation

Use this model:

```text
AWS Organization
  ├─ Management account
  │   └─ billing / organizations / IAM Identity Center only
  │
  ├─ existing project accounts
  │
  └─ devops-sdet-demo account
      ├─ ECR
      ├─ ECS Fargate
      ├─ ALB
      ├─ RDS PostgreSQL
      ├─ CloudWatch
      ├─ IAM GitHub OIDC deploy role
      ├─ AWS Budgets
      └─ Terraform-managed resources
```

Do not deploy workload resources into:

```text
- the Organization management account
- unrelated project accounts
- personal/root account scope
```

## 2.2 Human Access

Human/operator access must use IAM Identity Center / AWS SSO.

Expected local AWS CLI profile:

```text
demo-admin
```

Expected commands:

```bash
aws sso login --profile demo-admin --use-device-code
aws sts get-caller-identity --profile demo-admin
```

Terraform local commands must support:

```bash
export AWS_PROFILE=demo-admin
```

## 2.3 GitHub Actions Access

GitHub Actions must not use SSO.

GitHub Actions must use:

```text
GitHub Actions OIDC
  → assume IAM role inside devops-sdet-demo account
  → deploy resources there
```

No static AWS access keys in GitHub.

---

# 3. Phase 0: Discovery / Preflight Inventory

This phase must happen before implementation.

Goal: collect safe context about the existing AWS Organization, accounts, SSO access, GitHub repository, and credential model.

Do not create application code in Phase 0.

Do not create Terraform resources in Phase 0.

Do not run Terraform apply in Phase 0.

## 3.1 Ask the User for Safe Inventory Data

Ask the user to provide or confirm the following:

### AWS Organization

```text
1. Is there an existing dedicated demo account?
   - yes/no
   - account name
   - account ID, if available

2. If not, what should the new account be called?
   Recommended: devops-sdet-demo

3. What OU should contain the demo account?
   Examples:
   - Sandbox
   - Workloads
   - Demo
   - Projects

4. Is AWS Control Tower used?
   - yes/no/unknown

5. Is billing/budget visibility available in the management account?
   - yes/no/unknown
```

### IAM Identity Center / AWS SSO

```text
6. IAM Identity Center region
   Example: us-west-2 or us-east-1

7. SSO start URL
   Example format: https://example.awsapps.com/start

8. User/group that should get access to demo account
   Example: user email or group name

9. Permission set to use for initial setup
   Recommended for initial build: AdministratorAccess on demo account only

10. Desired AWS CLI profile name
    Recommended: demo-admin
```

### AWS Region

```text
11. Primary deployment region
    Default: us-west-2
```

### GitHub

```text
12. GitHub owner/org name

13. GitHub repository name
    Recommended: aws-devops-sdet-demo

14. Default branch
    Recommended: main

15. Should GitHub environments be used?
    Recommended:
    - stage
    - prod later

16. GitHub Actions allowed?
    yes/no
```

### Lightsail Devbox

```text
17. Is Lightsail devbox already created?
    yes/no

18. If yes:
    - instance name
    - public/static IP
    - Ubuntu version
    - instance size

19. If no:
    Recommended:
    - Ubuntu 24.04 LTS
    - 2 GB RAM minimum
    - 4 GB RAM preferred
    - static IP attached
```

### Budget Alerts

```text
20. Budget alert email
    Optional.
    Do not require if user prefers to skip budget module initially.
```

### Resource Tagging

```text
21. Owner identifier for resource tags
    Used for the Owner tag on all Terraform-managed resources.
    Example: name, email, or team handle. Not a secret.
```

### Terraform Remote State

```text
22. Terraform state model
    v0 uses a remote S3 backend so local (demo-admin) and
    GitHub Actions (OIDC) operate on the SAME state.
    Confirm:
    - S3 state bucket name
      Recommended: aws-devops-sdet-demo-tfstate-<demo_account_id>
    - state region (default: same as deployment region, us-west-2)
    - locking: S3 native lockfile (use_lockfile = true), no DynamoDB
    This bucket is created by a bootstrap step at the start of Phase 4,
    before any terraform apply.
```

## 3.2 Do Not Collect Secrets

Explicitly state:

```text
Do not paste passwords, secret keys, private SSH keys, database passwords, AWS root credentials, or GitHub tokens.
```

## 3.3 Validate Current AWS Identity

If the user has access to AWS CLI on the devbox, ask them to run:

```bash
aws sso login --profile demo-admin --use-device-code
aws sts get-caller-identity --profile demo-admin
```

Expected output fields to capture:

```text
Account
Arn
UserId
```

The `Account` must match the intended demo member account.

## 3.4 Phase 0 Output

At the end of Phase 0, produce:

```text
- AWS account model summary
- selected demo account name/ID
- selected AWS region
- selected AWS CLI profile
- GitHub owner/repo/branch
- Lightsail devbox status
- owner tag value
- Terraform state bucket name/region
- missing prerequisites
- next exact manual steps
```

Then STOP and ask for confirmation.

Do not proceed until confirmed.

---

# 4. Phase 1: Lightsail Devbox Preparation

Do this only after Phase 0 is confirmed.

The primary development environment is an AWS Lightsail Ubuntu devbox.

The repository must support running all local development commands on a remote Linux server through SSH.

Important assumptions:

```text
- Do not assume Docker Desktop.
- Do not assume macOS-specific tooling.
- All commands must work on Ubuntu Linux.
- Local development means Docker Compose running on the Lightsail devbox.
- The developer accesses the app through SSH port forwarding.
- PostgreSQL must stay private inside the Docker network.
- Do not expose PostgreSQL publicly.
- Do not expose development app ports publicly by default.
```

Expected dev workflow:

```text
Laptop / any computer
  ↓ VS Code Remote-SSH (preferred) or bare SSH
Lightsail Ubuntu devbox
  ├─ git repo
  ├─ Docker
  ├─ Docker Compose
  ├─ app container
  ├─ postgres container
  ├─ Playwright tests
  ├─ Terraform CLI
  ├─ AWS CLI
  └─ Claude Code
```

Lightsail is the **development machine**, not the final production-like AWS deployment target.

Final AWS demo target remains:

```text
ECR
ECS Fargate
ALB
RDS PostgreSQL
CloudWatch
IAM
GitHub Actions OIDC
Terraform
```

## 4.1 Devbox Setup Docs

Create documentation:

```text
docs/lightsail-devbox.md
```

Include:

```text
- recommended Lightsail instance size
- Ubuntu version recommendation
- static IP recommendation
- initial server update commands
- Docker installation
- Docker Compose verification
- Git installation
- GitHub SSH key setup
- AWS CLI installation
- AWS SSO profile configuration
- Terraform installation
- Node.js installation
- Python tooling if needed
- VS Code Remote-SSH usage (preferred Claude Code client)
- Claude Code access modes: VS Code Remote-SSH vs bare SSH (see Phase 1 client notes)
- .vscode/ project settings and extensions.json (recommended extensions)
- new-machine checklist (VS Code + Remote-SSH + SSH key)
- SSH tunnel example
- firewall/security rules
- backup/snapshot recommendations
```

Include SSH tunnel example:

```bash
ssh -L 8000:localhost:8000 ubuntu@LIGHTSAIL_STATIC_IP
```

Then open locally:

```text
http://localhost:8000
```

## 4.2 Security Rules

Document:

```text
- open only 22/tcp by default
- restrict SSH to trusted IP if possible
- do not expose PostgreSQL
- do not expose 5432 publicly
- do not expose dev app ports publicly by default
- use UFW
- use Lightsail firewall
- use GitHub as source of truth
- use Lightsail snapshots before major changes
```

## 4.3 Devbox Validation Commands

Provide commands:

```bash
docker --version
docker compose version
git --version
aws --version
terraform version
node --version
python3 --version
aws sso login --profile demo-admin --use-device-code
aws sts get-caller-identity --profile demo-admin
```

## 4.4 Claude Code Client and VS Code Remote-SSH

Claude Code runs ON the devbox (where the repo, Docker, Terraform, and AWS CLI
live), regardless of how it is accessed. Two access modes:

```text
- VS Code Remote-SSH + Claude Code extension  → preferred default
- bare SSH + `claude` in the shell            → fallback
```

Preferred default — VS Code Remote-SSH:

```text
- See the repo tree, review CC's changes as inline diffs (valuable for IaC),
  and run terraform/docker/aws in the integrated terminal in one window.
- The CC engine and skills (.claude/skills/) work identically to bare SSH.
```

Use bare SSH + `claude` when:

```text
- the connection to the devbox is weak/unstable (Remote-SSH is heavier),
- the Lightsail instance is small (VS Code Server consumes RAM/CPU),
- running a pure agentic pass ("run the phase, I'll collect the result"),
- working from a phone or a machine without VS Code.
```

Instance-size note (cost control): VS Code Server on the devbox competes for
RAM/CPU with the running Postgres + app containers and Playwright. On a very
small Lightsail size (≈1-2 GB RAM), prefer bare SSH for heavy local runs
(compose + Playwright), or size the instance one step up. Record the chosen
size and this trade-off in docs/lightsail-devbox.md.

Where VS Code settings live (Remote-SSH model):

```text
On the devbox / in the repo (auto-applied, no per-laptop setup):
- Remote extensions install into ~/.vscode-server on the devbox (install once).
- Project settings live in the repo under .vscode/ (settings.json,
  extensions.json, launch.json) and travel via git to every machine.

Per-laptop, one-time (cannot be auto-pulled):
- Install VS Code + the Remote-SSH extension on the client.
- Add the devbox to ~/.ssh/config with that laptop's own SSH key.
- Personal editor prefs (theme, keybindings) sync via VS Code Settings Sync.

Do NOT sync SSH private keys via Settings Sync. Each laptop has its own key,
added to the devbox authorized_keys. This matches the SSH security rules above.
```

Recommended in the repo to make a new laptop "just connect":

```text
- .vscode/extensions.json listing recommended extensions (incl. Claude Code),
  so VS Code offers to install them onto the devbox on first open.
- A short "new machine" checklist in docs/lightsail-devbox.md (install VS Code,
  Remote-SSH, add SSH key, open the folder on the devbox).
```

Then STOP and ask for confirmation.

---

# 5. Hard Constraints

Follow these constraints strictly:

```text
- Do not use EKS in v0.
- Do not create NAT Gateway in v0.
- Do not use static AWS access keys in GitHub.
- Use GitHub Actions OIDC for AWS authentication.
- Do not commit secrets.
- Do not hardcode credentials.
- Use cost-conscious AWS defaults.
- Do not create AWS resources automatically.
- Do not run terraform apply unless explicitly asked later.
- Do not run terraform destroy unless explicitly asked later.
- Do not use placeholder pseudo-code for core app logic.
- Generate working code/configs/scripts/docs.
- Make reasonable implementation decisions without asking clarifying questions after Phase 0 is complete.
```

Default AWS region unless overridden in Phase 0:

```text
us-west-2
```

Project name/tag:

```text
aws-devops-sdet-demo
```

---

# 5a. Repeatable Lifecycle (Periodic Demo)

This environment is brought up and torn down repeatedly: deploy, run the
interview demo, then destroy everything so nothing keeps billing. The design
must make every cycle clean and idempotent.

What survives every cycle (created once, never destroyed):

```text
- the Terraform state S3 bucket (infra/bootstrap) — near-zero cost
- the GitHub OIDC provider + deploy role, IF created by the local
  first apply; otherwise they are recreated each cycle. Document which.
```

What MUST be destroyed every cycle (all billable v0 resources):

```text
ECS service/cluster, ALB, RDS instance, app ECR repository,
CloudWatch log group, VPC and networking.
```

Idempotency / re-apply rules (so the NEXT apply after a destroy succeeds):

```text
- ECR: force_delete = true (destroy removes repo even with images).
- Secrets Manager: recovery_window_in_days = 0 (no name reservation that
  blocks the next apply), or a random suffix on the secret name.
- RDS: skip_final_snapshot = true, backup_retention_period = 0 (no leftover
  snapshots/backups across cycles).
- CloudWatch log group: Terraform-managed (not ECS auto-created) so it is
  actually removed.
- No resources with hardcoded global-unique names that linger after delete.
```

Safety nets against a forgotten teardown:

```text
- Budgets module enabled by default (free) with email alert.
- destroy.yml ends with a verification step listing any remaining billable
  resources.
- Optional later (Phase 8, not v0): scheduled nightly teardown via Actions
  cron as a backstop.
```

Standard cycle:

```text
deploy-stage.yml (or local apply) → demo → destroy.yml (confirm=DESTROY)
→ verify nothing billable remains → repeat next time
```

---

# 6. Key Architecture Decision

Use a **single containerized app** for v0.

Do **not** split frontend and backend yet.

Target architecture:

```text
Browser
  ↓
AWS ALB
  ↓
ECS Fargate: single app container
  ↓
RDS PostgreSQL
```

The app container must:

```text
- serve simple static HTML at /
- expose /health
- expose /api/health
- expose /api/db-check
- connect to PostgreSQL
- support migration command
- support seed command
- support DB assertion command if practical
```

Critical health-check rule (single-container v0):

```text
- /health and /api/health MUST NOT touch the database.
  They are liveness checks and must return OK as soon as the
  web process is up, even before migrations run or RDS is reachable.
- /api/db-check is the ONLY endpoint that opens a DB connection.
- ALB target group health check and container healthcheck both use /health.
```

Rationale: there is only one container. If /health depended on the DB,
ECS could never reach steady state before the migration task runs,
and the migration task cannot run until the service is healthy — a deadlock.

Do not use React/Vite in v0. Use simple static HTML served by FastAPI.

---

# 7. Repository Structure

**Historical note (Phase 12).** What follows was written in Phase 0 as an
instruction to create a structure. It is now a DESCRIPTION of one that exists,
corrected to what `git ls-files` actually shows. The original said one bootstrap
level; there are seven root Terraform levels, and three workflows became five.
Where this file and the repository disagree, the repository wins.

```text
aws-devops-sdet-demo/
  app/                     one container: serves web, runs migrations and seed
    Dockerfile             python:3.12-slim, psycopg2-binary, non-root
    requirements.txt
    alembic.ini
    alembic/versions/      0001 create demo_items, 0002 nullable description
    src/                   main.py, db.py, models.py, static/index.html
    scripts/               migrate.sh, seed.py, assert_seed.py,
                           assert_ui_write.py

  tests/                   WHERE A SPEC LIVES DECIDES WHERE IT RUNS (ADR-0025)
    api/                   pytest + httpx contract suite, DESTRUCTIVE
    db/                    assert_seed.py, the standalone seed assertion
    playwright/
      playwright.config.ts projects bound to the two directories below
      tests/smoke/         read-only - the ONLY suite prod runs
      tests/regression/    destructive - stage and local only
      scripts/assert-spec-coverage.sh   a spec in neither directory fails here

  infra/
    bootstrap/             S3 state bucket. Local state, applied by hand.
    bootstrap-oidc/        OIDC provider + ONE DEPLOY ROLE PER ENVIRONMENT
                           (ADR-0015, ADR-0021)
    shared-ecr/            the registry prod promotes from (ADR-0018)
    dns/                   delegated zone + ALB certificate (ADR-0024)
    public-site/           the dashboard: S3 + CloudFront + OAC + the
                           us-east-1 certificate + a narrow publish role
                           (ADR-0027)
    envs/stage/            per cycle
    envs/prod/             per cycle, behind an approval gate
    modules/               network, ecr, alb, ecs, rds, observability, budgets,
                           iam_github_oidc_provider, iam_github_deploy_role

  scripts/                 ecs-run-task.sh, observe-environment.sh,
                           publish-status.sh, publish-site.sh, send.sh

  assets/index.template.html  the dashboard's SOURCE (20a)
  site/index.html          the dashboard, BUILT from it by `make site-page`:
                           one published file, no runtime dependency

  .github/workflows/       ci.yml, deploy-stage.yml, promote-prod.yml,
                           destroy.yml, publish-site.yml

  .claude/skills/          nine skills + a registry (ADR-0013)
  CLAUDE.md                what a Claude Code session on the devbox reads first

  docs/
    README-level entry points:
      ../README.md         what it is, how to run it, what it proves
      architecture.md      the levels, the request path, the trade-offs
      demo-script.md       the ten-minute walkthrough
    state and process:
      phase-gates.md       the cursor - the only file that claims to know
                           where the project stands
      next-phases.md       the plan: MVP track 9-13, polish track 14-19
      discussion-log.md    the narrative
      session-primer.md    how a session starts; attached to a new chat
      transfer-buffer.md   how a chat's work reaches git (ADR-0028)
      sessions/INDEX.md    one row per session
    reference:
      decisions/           the ADRs
      preflight-inventory.md, security-posture.md, skills-structure.md,
      project-instructions-pointer.md, project-prompt.md (this file)

  docker-compose.yml       postgres 16 (not published) + app:8000
  Makefile                 the local and CI targets
  README.md
  .gitignore
  .env.example
```

Not present, deliberately: `docs/cost-control.md`,
`docs/interview-talking-points.md` and `docs/lightsail-devbox.md` are Phase 18.
This file does not list them as if they existed.

---

# 8. Phase 2: Minimal Local App Skeleton

Do this only after Phase 1 is confirmed.

Use:

```text
Python
FastAPI
SQLAlchemy
Alembic
PostgreSQL
```

## 8.1 Endpoints

Implement:

```text
GET /
GET /health
GET /api/health
GET /api/db-check
```

Expected behavior:

```text
GET /              → returns static HTML
GET /health        → returns simple JSON health status, NO DB access
GET /api/health    → returns API health status, NO DB access
GET /api/db-check  → checks PostgreSQL connection and returns DB status
```

Example JSON:

```json
{
  "status": "ok",
  "service": "aws-devops-sdet-demo"
}
```

For DB check:

```json
{
  "status": "ok",
  "db": "connected"
}
```

If DB is unreachable, return non-OK status and useful error information without exposing secrets.

## 8.2 Static Frontend Requirements

For v0, use simple static HTML.

The page at `/` must show:

```text
AWS DevOps SDET Demo
App status
API health status
DB check status
```

The page should call:

```text
/api/health
/api/db-check
```

and display results in the browser.

Add stable selectors for Playwright:

```html
<h1 data-testid="app-title">AWS DevOps SDET Demo</h1>
<div data-testid="api-health-status"></div>
<div data-testid="db-check-status"></div>
```

## 8.3 Database Model

Use PostgreSQL.

Create one simple table for v0:

```sql
demo_items
```

Columns:

```text
id          integer/bigint primary key
name        text not null unique
created_at  timestamp not null default now()
```

Use Alembic migration to create this table.

Then STOP and ask for confirmation.

---

# 9. Phase 3: Local Docker Compose + Tests

Do this only after Phase 2 is confirmed.

## 9.1 Local Development

Create `docker-compose.yml` with:

```text
postgres
app
```

Local ports:

```text
app:      8000
postgres: 5432
```

PostgreSQL local defaults:

```text
POSTGRES_DB=demo
POSTGRES_USER=demo
POSTGRES_PASSWORD=demo
```

PostgreSQL version (pin and keep identical to RDS):

```text
postgres:16   (docker-compose image must match the RDS major version 16)
```

Database driver:

```text
- Use psycopg2-binary in app/requirements.txt.
- Do NOT use plain psycopg2: on a slim base image it needs
  libpq-dev + gcc and will fail the Docker build otherwise.
- DATABASE_URL scheme stays postgresql+psycopg2://...
```

App must read:

```text
DATABASE_URL
```

Example:

```text
postgresql+psycopg2://demo:demo@postgres:5432/demo
```

Add `.env.example` with all required variables.

Do not commit real `.env`.

## 9.2 Migration Requirements

Use Alembic.

Create a migration that creates:

```text
demo_items
```

Provide a migration command that works locally and in containerized environments.

Expected command:

```bash
make migrate
```

Inside container:

```bash
alembic upgrade head
```

## 9.3 Seed Requirements

Create seed script:

```text
app/scripts/seed.py
```

It must:

```text
- connect to PostgreSQL using DATABASE_URL
- insert one row into demo_items
- row name must be seed-item-001
- be idempotent
- exit zero if row already exists
```

Expected command:

```bash
make seed
```

## 9.4 DB Assertion Requirements

Create DB assertion script:

```text
tests/db/assert_seed.py
```

It must:

```text
- connect to PostgreSQL using DATABASE_URL
- check that demo_items table exists
- check that row seed-item-001 exists
- print clear success/failure output
- exit non-zero on failure
```

Expected command:

```bash
make test-db
```

## 9.5 Playwright Requirements

Use Playwright with TypeScript.

Create:

```text
tests/playwright/package.json
tests/playwright/playwright.config.ts
tests/playwright/tests/smoke.spec.ts
```

Smoke test must:

```text
- open BASE_URL, default http://localhost:8000
- verify title/header contains AWS DevOps SDET Demo
- verify API health status is visible
- verify DB check status is visible
- verify DB status eventually shows connected/ok
```

Configure:

```text
- screenshot on failure
- trace on failure
- video on failure if simple
- HTML report
```

Environment variable:

```text
BASE_URL
```

Default:

```text
http://localhost:8000
```

## 9.6 Docker Requirements

Create one Dockerfile for app.

The image must support:

```text
- running the web app
- running migrations
- running seed
```

Use a simple production-like command:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Expose:

```text
8000
```

Use clean dependency installation and avoid unnecessary image bloat.

## 9.7 Makefile Requirements

Create a Makefile with these commands:

```text
make local-up
make local-down
make migrate
make seed
make test-smoke
make test-db
make docker-build
make tf-fmt
make tf-validate
```

Expected behavior:

```text
make local-up       → docker compose up -d --build
make local-down     → docker compose down
make migrate        → run Alembic migration inside app container
make seed           → run seed script inside app container
make test-smoke     → run Playwright smoke tests
make test-db        → run DB assertion script
make docker-build   → build app Docker image
make tf-fmt         → terraform fmt recursively
make tf-validate    → terraform init/validate for stage
```

All commands must be Ubuntu-compatible.

Then STOP and ask for confirmation.

---

# 10. Phase 4: Terraform Foundation

Do this only after Phase 3 is confirmed.

## 10.0 Terraform State Bootstrap and Backend

Terraform state must be remote and shared between local (demo-admin) runs
and GitHub Actions (OIDC) runs. If state is local, the two will diverge and
the destroy workflow will fail to find resources, leaving cost running.

State backend: S3 with native lockfile (no DynamoDB).

```text
- S3 bucket: aws-devops-sdet-demo-tfstate-<demo_account_id>
- versioning: enabled
- encryption: enabled (SSE-S3 or SSE-KMS)
- public access: fully blocked
- key layout: stage/terraform.tfstate, prod/terraform.tfstate
- locking: use_lockfile = true
```

Bootstrap ordering (chicken-and-egg):

```text
1. The state bucket cannot be stored in state it does not yet hold.
   Create it with a small standalone bootstrap, run LOCALLY under
   AWS_PROFILE=demo-admin. Provide it as infra/bootstrap/ (Terraform with
   local state, committed .tfstate ignored) OR as documented aws s3api
   commands. Prefer infra/bootstrap/ Terraform.
2. Only after the bucket exists, configure backend "s3" in
   infra/envs/stage and infra/envs/prod and run terraform init.
```

Backend block (per environment):

```hcl
terraform {
  backend "s3" {
    bucket       = "aws-devops-sdet-demo-tfstate-<demo_account_id>"
    key          = "stage/terraform.tfstate"
    region       = "us-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
```

Bootstrap order of the FIRST apply of real infrastructure:

**Corrected in Phase 12.** The paragraph this replaces said the first apply of
`infra/envs/stage` creates the OIDC provider and the deploy role. That has been
false since **ADR-0015**: a destroy running under a role whose permissions live
in the same state deletes those permissions mid-run. The role moved out into its
own permanent level, and **ADR-0021** then split the account-wide provider from
the per-environment roles, because AWS allows exactly one OIDC provider per
issuer per account and a copied module would have died on `EntityAlreadyExists`.

The real order on a fresh account - all of it LOCAL, under
`AWS_PROFILE=demo-admin`, and all of it permanent:

```text
1. infra/bootstrap        the S3 state bucket. It cannot be stored in state it
                          does not yet hold, so this level keeps local state.
2. infra/bootstrap-oidc   the OIDC provider + one deploy role per environment.
                          Until this exists, no workflow can authenticate.
3. infra/shared-ecr       the registry both environments use.
4. infra/dns              hosted zone + the ALB certificate.
5. one NS record by hand in the parent zone, in org-management. Untracked by
   git, and the first thing to check if the name stops resolving.
6. infra/public-site      the dashboard. Reads the hosted zone by name, so its
                          plan fails outright if step 4 is missing.
7. GitHub environment variables, prod's protection rules, and the four
   repository variables for the dashboard.
```

Only after 1-2 can `deploy-stage.yml` authenticate at all. After that the
environments are applied BY ACTIONS and never by hand; `docs/preflight-inventory.md`
is the authoritative copy of this list.

Use Terraform with AWS provider.

Use consistent tags everywhere:

```text
Project      = "aws-devops-sdet-demo"
Environment  = var.environment
ManagedBy    = "terraform"
Owner         = var.owner
AccountModel = "aws-organizations-member-account"
```

## 10.1 Terraform Authentication

Terraform must support local SSO auth through:

```bash
export AWS_PROFILE=demo-admin
```

Terraform must support GitHub Actions auth through OIDC-assumed role.

Do not hardcode provider credentials.

## 10.2 Network Module

Create:

```text
VPC
2 public subnets
2 private DB subnets
Internet Gateway
public route table
public subnet route table associations
```

Do not create:

```text
NAT Gateway
```

Rationale: v0 is cost-conscious.

## 10.3 ECR Module

Create one ECR repository:

```text
aws-devops-sdet-demo-app
```

Add lifecycle policy to limit old images if practical.

Repeatable-teardown requirement:

```text
- force_delete = true for stage, so `terraform destroy` removes the
  repository even when it still contains pushed images. Without this,
  destroy fails on a non-empty repository and leaves cost/clutter.
```

## 10.4 ALB Module

Create:

```text
public ALB
HTTP listener on port 80
one target group for app
health check path /health
```

Output:

```text
alb_dns_name
alb_url
```

## 10.5 RDS Module

Create:

```text
PostgreSQL RDS instance
private DB subnet group
security group
```

Requirements:

```text
- engine version: postgres 16 (must match docker-compose image)
- publicly_accessible = false
- deletion protection disabled for demo
- skip_final_snapshot = true for stage (no leftover final snapshot cost)
- backup_retention_period = 0 for stage (no automated backups to leave behind)
- small cost-conscious instance class variable (e.g. db.t4g.micro)
- RDS SG allows 5432 only from ECS app SG
```

Password handling (no secrets in repo, no secrets in tfvars):

```text
- Generate the master password with the random_password resource.
- Store the connection details in AWS Secrets Manager (or SSM SecureString).
  Recommended: a single Secrets Manager secret holding the full DATABASE_URL
  or { username, password, host, port, dbname }.
- Do NOT put the password in environment variables, outputs, tfvars,
  or container `environment`.
- Mark relevant Terraform values as sensitive.
- The ECS task definition reads the secret via the `secrets` block
  (valueFrom = secret ARN), not via plaintext env.
- recovery_window_in_days = 0 for stage. A deleted Secrets Manager secret
  normally enters a 7-30 day recovery window and keeps its name reserved;
  the next apply in a periodic cycle would then fail with "already
  scheduled for deletion". Window 0 deletes immediately so the cycle is
  repeatable. (Alternative: append a random suffix to the secret name.)
```

Do not expose DB publicly.

## 10.6 ECS Module

Create:

```text
ECS cluster
Fargate task definition
Fargate app service
CloudWatch log configuration
ECS security group
```

v0 networking:

```text
- app service runs in public subnets
- assign_public_ip = true
- inbound to app allowed only from ALB security group
- outbound allowed for app
```

Container:

```text
- name: app
- port: 8000
- image: variable
- DB connection injected via task definition `secrets` (valueFrom = Secrets
  Manager ARN), NOT via plaintext `environment`
- container healthcheck hits /health (no DB dependency)
```

IAM roles:

```text
- task execution role: pull from ECR, write CloudWatch logs,
  read the Secrets Manager secret (secretsmanager:GetSecretValue scoped
  to the DB secret ARN)
- task role: minimal; expand only when the app needs AWS APIs
```

Egress / no-NAT note:

```text
- The task runs in a PUBLIC subnet with assign_public_ip = true, so it
  reaches ECR, Secrets Manager, and CloudWatch over the Internet Gateway.
  This is why v0 needs no NAT Gateway. If the task is ever moved to a
  private subnet, NAT Gateway or VPC endpoints become mandatory.
  Document this trade-off in docs/architecture.md.
```

One-off commands/tasks:

```text
migration task/command
seed task/command
DB assertion task/command if practical
```

Use the same task definition with `aws ecs run-task` containerOverrides
(command) for migrate / seed / db-assert. Do not create separate task
definitions in v0. Document the exact run-task commands.

## 10.7 IAM GitHub OIDC Module

Create:

```text
GitHub OIDC provider
deploy role for GitHub Actions
```

The trust policy must restrict access to:

```text
repository owner
repository name
branch/environment where practical
```

The deploy role permissions must include (least-privilege, demo-scoped):

```text
- S3 access to the Terraform state bucket (state read/write)
- ECR push/pull
- ECS register/run/update
- secretsmanager:GetSecretValue scoped to the DB secret
- the AWS actions Terraform needs to manage v0 resources
  (network, alb, ecs, rds, logs, budgets)
- pass the ECS task/execution roles (iam:PassRole scoped to those roles)
```

Variables:

```text
github_owner
github_repo
github_branch
demo_account_id
```

First-apply note:

```text
This module is created by the first LOCAL terraform apply
(AWS_PROFILE=demo-admin). GitHub Actions cannot assume a role that does
not exist yet, so the OIDC provider and deploy role must exist before
deploy-stage.yml runs. See §10.0.
```

Avoid static AWS keys.

## 10.8 Observability Module

Create:

```text
CloudWatch log group for app
```

Variable:

```text
log_retention_days
```

Repeatable-teardown requirements:

```text
- The log group MUST be created and managed by Terraform (do not let ECS
  auto-create it), so it is removed by `terraform destroy` instead of
  lingering and accumulating logs across cycles.
- Default log_retention_days short for stage (1-7), to cap cost even if a
  group is somehow left behind.
```

## 10.9 Budgets Module

Create the budget module. For this project it is REQUIRED, not optional,
because the environment is brought up and torn down repeatedly and a
forgotten teardown must trigger an alert.

Variables:

```text
budget_email
monthly_budget_limit
actual_threshold
forecast_threshold
```

If the user truly has no email, allow disabling cleanly via a flag, but the
default for stage is enabled. Note: AWS Budgets itself is free.

## 10.10 Terraform Environments

Create:

```text
infra/envs/stage
infra/envs/prod
```

`stage` must be the primary working environment.

`prod` may mirror stage as a scaffold, but do not implement full prod deployment unless simple.

Stage outputs must include:

```text
alb_url
ecr_repository_url
ecs_cluster_name
ecs_service_name
rds_endpoint
github_oidc_role_arn
db_secret_arn        (ARN only, never the secret value)
```

Do not output secrets.

Then STOP and ask for confirmation.

---

# 11. Phase 5: GitHub Actions and OIDC

Do this only after Phase 4 is confirmed.

Create three workflows.

## 11.1 `.github/workflows/ci.yml`

Trigger:

```yaml
on:
  pull_request:
  push:
    branches: [ main ]
```

Jobs:

```text
- checkout
- setup Python
- install app dependencies
- basic backend checks
- docker build app image
- setup Node.js
- install Playwright dependencies
- start full local stack with docker compose (app + postgres)
- run migrate + seed against the local stack
- run Playwright smoke test against the local stack (deterministic, not optional)
- run DB assertion against the local stack
- tear down the local stack
- terraform fmt check
- terraform validate for stage
```

Do not require AWS credentials for CI. CI validates everything locally
(Docker Compose) and never touches AWS.

**Corrected in Phase 12.** The sentence that stood here said to run
`terraform init -backend=false` so CI needs no AWS credentials. That is not what
the flag does: in a directory already initialized for real it reuses the cached
S3 configuration in `.terraform/` and reads remote state. It passed in CI only
because a fresh checkout has no `.terraform/`, and it was false on the devbox.
Use `make tf-validate`, which isolates `TF_DATA_DIR` per level and discovers
every root level rather than validating one.

## 11.2 `.github/workflows/deploy-stage.yml`

Trigger:

```yaml
on:
  push:
    branches: [ main ]
  workflow_dispatch:
```

Steps:

```text
- checkout
- configure AWS credentials through GitHub OIDC
- login to ECR
- build Docker image
- tag image with commit SHA
- push image to ECR
- terraform init in infra/envs/stage (S3 backend)
- terraform plan
- terraform apply -auto-approve
- get ALB URL from Terraform output
- run migration via `aws ecs run-task` with a command override
- run seed via `aws ecs run-task` with a command override
- wait for the ECS service to reach steady state
- run Playwright smoke against ALB URL
- run DB assertion via `aws ecs run-task` with a command override
- upload Playwright report as artifact
```

One-off task convention (pick ONE approach, do not mix):

```text
- Reuse the SAME Fargate task definition as the app service.
- Run migrate / seed / db-assert with `aws ecs run-task` using a
  containerOverrides command, e.g. ["alembic","upgrade","head"],
  ["python","scripts/seed.py"], ["python","tests/db/assert_seed.py"].
- Do NOT create separate task definitions for each in v0.
- Provide the exact aws ecs run-task commands in docs.
```

Use GitHub environment variables/secrets only for non-AWS static values such as:

```text
AWS_REGION
GITHUB_OIDC_ROLE_ARN
TF_VAR_github_owner
TF_VAR_github_repo
TF_VAR_demo_account_id
TF_VAR_budget_email
```

Do not use static AWS access keys.

## 11.3 `.github/workflows/destroy.yml`

Trigger:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment to destroy"
        required: true
        type: choice
        options:
          - stage
          - prod
      confirm:
        description: "Type DESTROY to confirm"
        required: true
```

Behavior:

```text
- fail unless confirm is exactly DESTROY
- configure AWS credentials through OIDC
- select infra/envs/<environment>
- terraform init
- terraform destroy -auto-approve
- final verification step: query and print any remaining billable resources
  and fail the job if anything cost-bearing is still present
```

Final verification step (runs after destroy, prints the result):

```bash
aws ecs list-clusters
aws rds describe-db-instances
aws elbv2 describe-load-balancers
aws ec2 describe-nat-gateways
aws eks list-clusters
aws ec2 describe-addresses           # unattached Elastic IPs
aws ecr describe-repositories        # the shared registry is EXPECTED to remain
```

```text
- Expected after a clean teardown: no ECS service, no RDS instance,
  no ALB, no NAT gateway, no EKS cluster, no unattached EIP.
- The app ECR repository is EXPECTED TO REMAIN. It was destroyed with the
  environment until ADR-0018 moved it to its own permanent state level, so
  that it survives a teardown and can still hold the image prod is running.
  destroy.yml therefore fails only on ENVIRONMENT-PREFIXED repositories.
- The permanent state levels are intentionally NOT destroyed and are all
  expected to remain: infra/bootstrap (state bucket), infra/bootstrap-oidc
  (OIDC provider + deploy roles), infra/shared-ecr, infra/dns (zone + ACM
  certificate) and infra/public-site (the dashboard).
- If anything cost-bearing remains, the step should surface it clearly
  (and ideally exit non-zero) so it is not silently left running.
```

This workflow is important for cost control and is the primary teardown
path for the repeatable demo cycle.

Then STOP and ask for confirmation.

---

# 12. Phase 6: First AWS Stage Deploy

Do this only after Phase 5 is confirmed.

Before deploy:

```text
- confirm AWS_PROFILE=demo-admin works locally
- confirm account ID is the dedicated demo account
- confirm the Terraform state bucket exists (bootstrap done)
- confirm no deployment targets the management account
```

State bootstrap (run once, locally, before the first apply):

```bash
aws sts get-caller-identity --profile demo-admin
export AWS_PROFILE=demo-admin
cd infra/bootstrap
terraform init
terraform plan
# apply only after explicit confirmation — creates the S3 state bucket
terraform apply
```

First stage apply (LOCAL — creates the OIDC role GitHub Actions will use):

```bash
export AWS_PROFILE=demo-admin
cd infra/envs/stage
terraform init          # initializes the S3 backend
terraform plan
```

Only run:

```bash
terraform apply
```

after explicit user confirmation. This first apply MUST be local so the
GitHub OIDC provider and deploy role are created. After this, GitHub Actions
(deploy-stage.yml) can authenticate via OIDC for subsequent applies.

After deploy:

```text
- verify ALB URL
- verify /health (must return OK without DB)
- run migration task (aws ecs run-task command override)
- run seed task (aws ecs run-task command override)
- verify /api/db-check returns connected
- run Playwright smoke
- run DB assertion
- confirm GitHub OIDC role ARN is in the demo account, not management
```

Then STOP and ask for confirmation.

---

# 13. Phase 7: Destroy Validation

Do this only after Phase 6 is confirmed.

Validate teardown through GitHub Actions workflow or local Terraform.

The destroy workflow must require:

```text
confirm = DESTROY
```

Expected result:

```text
- ECS service/cluster removed
- ALB removed
- RDS removed (no final snapshot, no automated backups left)
- ECR repository removed (force_delete)
- CloudWatch log group removed
- VPC/networking removed
- no expensive resources left running
- Terraform state bucket (infra/bootstrap) intentionally remains
```

After destroy, provide AWS CLI checks for:

```text
ECS services
RDS instances
ALBs
NAT gateways
EKS clusters
unattached Elastic IPs
ECR repositories
```

There should be:

```text
- no NAT Gateway
- no EKS cluster
- no app ECR repository
- no leftover ALB / RDS / ECS
```

Repeatability check (important for the periodic demo):

```text
- After a destroy, run a fresh `terraform apply` for stage again and confirm
  it succeeds with NO name conflicts (Secrets Manager, ECR, log group).
- This proves the deploy → demo → destroy → deploy cycle is clean.
```

Then STOP and ask for confirmation.

---

# 14. Phase 8: Next Feature Expansion

Only after the full v0 construction works, add richer demo logic.

Possible next phases:

```text
- richer FastAPI domain model
- Facility Intake Demo domain
- React/Vite frontend
- Playwright regression suite
- SQL assertions for business lifecycle
- prod deployment with manual approval
- HTTPS with ACM
- CloudFront
- WAF
- private ECS subnets
- NAT Gateway or VPC endpoints
- autoscaling
- blue/green deploy
- EKS branch
- Helm
- ArgoCD or Flux
- Grafana/Prometheus on Lightsail
- Loki logs
- security scanning
- Trivy
- Checkov
- Dependabot
```

---

# 15. Documentation Requirements

Create detailed but concise docs.

## 15.1 `README.md`

Must include:

```text
- project purpose
- architecture overview
- AWS Organizations account model
- SSO-based human access
- GitHub OIDC machine access
- Mermaid architecture diagram
- local development on Lightsail devbox
- local setup commands
- local test commands
- AWS prerequisites
- Terraform deployment flow
- deploy-stage workflow explanation
- destroy workflow explanation
- cost-control notes
- MVP limitations
- next phases
```

## 15.2 `docs/preflight-inventory.md`

Must include a safe checklist for:

```text
- AWS Organization account inventory
- demo account selection/creation
- OU selection
- Control Tower status
- IAM Identity Center region/start URL
- SSO permission set
- AWS CLI profile
- GitHub owner/repo
- GitHub branch
- GitHub environments
- Lightsail devbox status
- owner identifier for resource tags
- Terraform state bucket name and region
- budget email
```

Must clearly state:

```text
Do not paste secrets into this document.
```

## 15.3 `docs/phase-gates.md`

Must include:

```text
- phase list
- completion criteria for each phase
- validation commands
- explicit confirmation requirement before next phase
```

## 15.4 `docs/lightsail-devbox.md`

Must include:

```text
- recommended Lightsail instance size
- Ubuntu version recommendation
- static IP recommendation
- initial server update commands
- Docker installation
- Docker Compose verification
- Git installation
- GitHub SSH key setup
- AWS CLI installation
- AWS SSO profile configuration
- Terraform installation
- Node.js installation
- Python tooling if needed
- VS Code Remote-SSH usage (preferred Claude Code client)
- Claude Code access modes: VS Code Remote-SSH vs bare SSH (see Phase 1 client notes)
- .vscode/ project settings and extensions.json (recommended extensions)
- new-machine checklist (VS Code + Remote-SSH + SSH key)
- SSH tunnel example
- firewall/security rules
- backup/snapshot recommendations
```

Include SSH tunnel example:

```bash
ssh -L 8000:localhost:8000 ubuntu@LIGHTSAIL_STATIC_IP
```

Then open locally:

```text
http://localhost:8000
```

## 15.5 `docs/architecture.md`

Include:

```text
- AWS Organization model
- local dev architecture
- AWS stage architecture
- resource list
- network layout
- security group explanation
- Terraform remote state model (S3 backend, why shared local + CI state)
- DB password flow (random_password → Secrets Manager → ECS secrets)
- health-check model (/health no DB, /api/db-check is the only DB endpoint)
- why ECS Fargate instead of EKS for v0
- why no NAT Gateway in v0 (public subnet + public IP reaches ECR/Secrets/Logs
  over the IGW; private subnets would require NAT or VPC endpoints)
- why single app container in v0 (frontend + backend + DB access in one image)
- the two chicken-and-egg bootstraps (state bucket; OIDC role first apply local)
```

## 15.6 `docs/demo-script.md`

Create an interview demo script:

```text
1. Show AWS account isolation model.
2. Show SSO profile and caller identity.
3. Show repo structure.
4. Show app locally on Lightsail devbox.
5. Show Docker Compose.
6. Show Makefile.
7. Show Playwright smoke test.
8. Show DB assertion.
9. Show Terraform modules.
10. Show GitHub Actions CI.
11. Show GitHub OIDC deploy model.
12. Show deploy-stage workflow.
13. Show AWS ECS/RDS/ALB resources in demo account.
14. Show smoke test artifact.
15. Show destroy workflow.
16. Explain next phases.
```

## 15.7 `docs/cost-control.md`

Must include:

```text
- why demo account is isolated
- why no EKS in v0
- why no NAT Gateway in v0
- why destroy workflow exists
- RDS cost warning
- ALB cost warning
- Lightsail fixed-cost devbox role
- budget module (required, with alert email)
- the repeatable deploy → demo → destroy cycle
- what survives teardown (state bucket, optionally OIDC role) and why
- what must be destroyed every cycle (ECS, ALB, RDS, ECR, logs, VPC)
- idempotency notes: ECR force_delete, Secrets Manager recovery window 0,
  RDS no final snapshot / no backups
- destroy.yml verification step and how to read it
- reminders to destroy stage after every demo
```

## 15.8 `docs/next-phases.md`

Include future improvements:

```text
- richer FastAPI domain model
- React/Vite frontend
- Playwright regression suite
- SQL assertions for business lifecycle
- prod deployment with manual approval
- HTTPS with ACM
- CloudFront
- WAF
- private ECS subnets
- NAT Gateway or VPC endpoints
- autoscaling
- blue/green deploy
- EKS branch
- Helm
- ArgoCD
- Grafana/Prometheus on Lightsail
- Loki logs
- security scanning
- Trivy
- Checkov
- Dependabot
```

## 15.9 `docs/interview-talking-points.md`

Include talking points for:

```text
DevOps Engineer
Cloud Engineer
QA Automation / SDET
Security
FinOps / cost control
```

---

# 16. `.gitignore`

Create appropriate `.gitignore`.

Must ignore:

```text
.env
*.tfstate
*.tfstate.*
.terraform/
__pycache__/
.pytest_cache/
node_modules/
playwright-report/
test-results/
.DS_Store
```

Prefer committing `.terraform.lock.hcl` for reproducible provider versions. Document this decision.

Generate the lock for the platforms used by both the Lightsail devbox and
GitHub Actions runners so provider hashes match in CI:

```bash
terraform providers lock -platform=linux_amd64 -platform=linux_arm64
```

The bootstrap local state (`infra/bootstrap/`) is already excluded by the
`*.tfstate` rules above and must never be committed.

---

# 17. Acceptance Criteria

The generated repository must satisfy:

```text
- Phase 0 inventory is completed and confirmed
- Lightsail devbox requirements are documented and confirmed
- AWS CLI SSO profile works against the demo member account
- Account ID is verified before Terraform deploy
- Docker Compose starts local app and PostgreSQL
- simple frontend opens at /
- /health returns OK
- /api/health returns OK
- /health and /api/health do NOT open a DB connection
- /api/db-check confirms DB access
- make migrate creates demo_items
- make seed inserts seed-item-001
- make test-db verifies seed-item-001 exists
- make test-smoke runs Playwright smoke test
- Docker image builds (psycopg2-binary, no build failure)
- Terraform fmt passes
- Terraform validate passes for EVERY root level (`make tf-validate`, isolated
  TF_DATA_DIR, no AWS creds). The original line said "for stage, with
  -backend=false"; see the correction in 11.1 and Phase 9.0.
- infra/bootstrap creates the S3 state bucket
- stage and prod use the S3 backend (backend.tf present)
- RDS password is generated and stored in Secrets Manager, never in repo/tfvars/outputs
- ECS task definition reads DB creds via `secrets` valueFrom, not plaintext env
- GitHub Actions workflow files are present
- CI runs migrate + seed + smoke + db-assert against local Docker Compose
- GitHub OIDC deploy role targets only the demo account
- first stage apply documented as local (creates OIDC provider/role)
- README explains exact run/demo steps
- docs/lightsail-devbox.md explains remote devbox setup
- docs/preflight-inventory.md exists
- docs/phase-gates.md exists
- destroy workflow requires confirm=DESTROY
- destroy workflow ends with a remaining-resource verification step
- ECR repo uses force_delete so destroy succeeds with images present
- Secrets Manager uses recovery_window_in_days = 0 (re-apply after destroy works)
- RDS uses skip_final_snapshot and backup_retention_period = 0 for stage
- CloudWatch log group is Terraform-managed and removed on destroy
- budgets module is enabled by default with an alert email
- state bucket (infra/bootstrap) is excluded from the destroy cycle
- a full deploy → destroy → deploy cycle completes without name conflicts
```

---

# 18. Implementation Order

Follow this exact order:

```text
0. Perform Phase 0 discovery/preflight inventory.
1. Stop and wait for confirmation.
2. Prepare Phase 1 Lightsail devbox documentation/checks.
3. Stop and wait for confirmation.
4. Create repository structure.
5. Create .gitignore and .env.example.
6. Implement minimal FastAPI app.
7. Implement static HTML frontend.
8. Implement PostgreSQL connection.
9. Implement SQLAlchemy model.
10. Implement Alembic setup and migration.
11. Stop and wait for confirmation.
12. Implement seed script.
13. Implement DB assertion script.
14. Implement Dockerfile.
15. Implement docker-compose.yml.
16. Implement Makefile.
17. Implement Playwright smoke test.
18. Stop and wait for confirmation.
19. Implement infra/bootstrap (S3 state bucket).
20. Implement backend.tf for stage and prod (S3 backend).
21. Implement Terraform modules.
22. Implement stage Terraform environment.
23. Scaffold prod Terraform environment.
24. Stop and wait for confirmation.
25. Implement GitHub Actions ci.yml.
26. Implement GitHub Actions deploy-stage.yml.
27. Implement GitHub Actions destroy.yml.
28. Stop and wait for confirmation.
29. Bootstrap state bucket locally (apply infra/bootstrap).
30. Validate first AWS stage deploy plan.
31. Ask for explicit permission before the first LOCAL apply
    (creates OIDC provider and deploy role).
32. Validate deployment.
33. Stop and wait for confirmation.
34. Validate destroy workflow.
35. Stop and wait for confirmation.
36. Continue to next feature expansion only after user request.
```

---

# 19. Do Not Do Yet

Do not implement these in v0:

```text
- EKS
- Helm
- ArgoCD
- React/Vite frontend
- complex business domain
- multiple microservices
- NAT Gateway
- WAF
- CloudFront
- HTTPS/ACM
- blue/green deployment
- autoscaling
- multi-account AWS Organizations expansion beyond demo account
- advanced observability stack
```

Add them only to `docs/next-phases.md`.

---

# 20. Expected Final Response After Each Phase

After each phase, print:

```text
- phase completed
- files created/modified
- exact validation commands
- expected outputs
- risks/blockers
- what must be confirmed before next phase
```

Do not claim that AWS resources were created unless Terraform apply was actually executed.

Do not claim that tests passed unless they were actually run.

If some checks could not be run, state that clearly.

Then ask for confirmation before continuing.
