# Discussion Log — Decisions & Rationale

Compact record of the design decisions made while preparing this project,
kept so the context is not lost and does not need re-deriving. Summary only —
not a transcript. New decisions go to `docs/decisions/` as ADRs.

## Current state (update at every phase gate)

Phase 0–7 = done. **Phase 8: the lifecycle half is CLOSED (2026-07-25). The
feature half is still not started, but it is now PLANNED (2026-07-25).**

The full `deploy → demo → destroy` cycle runs end-to-end through GitHub Actions
with zero manual AWS operations. This was the project's headline goal.

Stage infrastructure is FULLY DESTROYED in AWS — zero billable resources.
Nothing is billing except the near-zero state bucket. The OIDC provider + deploy
role from `infra/bootstrap-oidc` are still present (IAM, free) because a stage
teardown does not touch that state level.

**The plan for everything after Phase 8 now lives in `docs/next-phases.md`**
(in git), shaped by **ADR-0017**. It supersedes the unordered wish-list in
`project-prompt.md` §14. Two tracks:

```text
MVP     9  prod + promotion + HTTPS      (9.0 reconcile scaffold, 9.1 build)
       10  thin application slice
       11  public dashboard (S3 + CloudFront)
       12  minimum viable documentation
       13  MVP verification gate (empty → empty in one run)
Polish 14  release resilience / rollback
       15  security gates (Trivy, Checkov, gitleaks, Dependabot)
       16  full test depth + observability
       17  prod data continuity (optional)
       18  remaining documentation
       19  guarded self-service launch + out-of-band watchdog
```

Repo (origin/main), most recent first:

```text
1f50243  docs: move discussion-log into git (last artifact outside the source of truth)
bbe8bd0  docs: close the 2026-07-25 planning session — phase-gates Phase 9, summary, index
ee0a25e  docs: next-phases — Phase 9.0 reconcile the stale prod scaffold
f8f32e5  chore: commit the control layer (CLAUDE.md, skills, sessions) + ADR-0017 + next-phases
8912aa9  docs: phase-gates — Phase 7 done, Phase 8 lifecycle closed
f08f2f4  docs: ADR-0016 destroy the ALB before the network
6944229  chore(deploy): manual dispatch only, drop the push trigger
58ec209  fix(oidc): allow eks:ListClusters for the teardown verification step
b110b41  fix(destroy): unblock teardown via Actions
b71b846  fix(deploy): create ECR before build; fail loudly on empty repo URL
5735430  refactor(oidc): C2 — move OIDC provider+deploy role to infra/bootstrap-oidc
8d3ed9d  fix(destroy): retry terraform destroy (WRONG fix — REVERTED in C2/5735430)
181cabd  chore(ci): bump actions to Node 24
497a4b2  docs: mark Phase 7 done (destroy validation)
2c1efcc  fix(oidc): allow environment:<name> sub in deploy role trust policy
1675f53  docs: mark Phase 6 done (36ecfba) + carry-forward learnings
36ecfba  fix: in-image DB-assert script for run-task (build context is app/)
a309763  chore: commit bootstrap provider lock (aws 5.100.0, amd64+arm64)
2c4162b  fix: add depends_on=[module.alb] to ecs in stage
40eb757  feat: phase 5 github actions workflows (ci, deploy-stage, destroy)
0256dc8  feat: phase 4 terraform foundation
```

GitHub configured: 6 ENVIRONMENT variables under environment `stage`, no secrets
(OIDC). Environment `stage` created; `prod` environment not yet created.

SSO login on the headless devbox: use `aws sso login --profile demo-admin
--use-device-code`. Identity confirmed: Account 993912191738.

---

### Phase 8 session 4 (2026-07-25) — planning + two structural findings

Ran in **Cowork on the MacBook**, not Claude Code on the devbox. Files were
produced locally and moved across with `scp`. Nothing was deployed; no AWS
resource was touched.

**Goal:** decide what happens to the application and to the project as a whole
now that the lifecycle is closed, and produce a real plan before writing more
code.

#### Decisions — recorded as ADR-0017

- **D1** prod lives in the SAME AWS account as stage, separated by state key,
  name prefix, deploy role, GitHub Environment and VPC. A separate member
  account is the stronger AWS Organizations story but was rejected on schedule
  cost — the finish line was already months out.
- **D2** hybrid availability: the dashboard is always on, every workload
  environment is on demand. The dashboard is **S3 (private) + CloudFront + OAC
  in AWS, not GitHub Pages** — hosting the showcase of an AWS project outside
  AWS demonstrates nothing. This forces a permanent state level
  `infra/public-site/`.
- **D2a** prod keeps NO data between cycles. `skip_final_snapshot = true`,
  `backup_retention_period = 0` are indefensible on a real production database,
  so the honest interview framing is **"a production-shaped environment with a
  promotion gate"**, not "production". Volunteer that; do not get caught by it.
- **D3** public HTTPS on an owned domain. `<domain>` → dashboard,
  `app.<domain>` → prod ALB. **The CloudFront certificate must be issued in
  us-east-1**; the ALB certificate stays regional in us-west-2.
- **D4** external access is phased: view-only first (Phase 11), authorised
  self-service launch last (Phase 19), with mandatory guardrails.

Rejected and recorded: always-on prod (~$40–60/month against a $20 alarm, and it
would make the project's own cost-control claim false); prod on the Lightsail
devbox; GitHub Pages; a second member account for now.

#### Ordering changed mid-session

The session began with a documentation-first recommendation. Once the stated
priority became "fastest path to a shareable MVP", the order was rebuilt
prod-first: prod is the only genuinely missing half of the cycle and the
riskiest work, so it goes while the context is fresh. Documentation was cut to
README + architecture + demo-script (Phase 12) with the rest deferred to
Phase 18.

#### Finding 1 — the control layer had never been committed

`CLAUDE.md`, `.claude/skills/` (9 skills + registry), `docs/sessions/`,
`docs/skills-structure.md`, `docs/project-instructions-pointer.md` and
`docs/decisions/0000-template.md` existed **only** in a non-git folder on the
MacBook (`~/Projects/aws-devops-sdet-demo`), created 2026-06-06. The repo had
93 tracked files and none of them.

Consequence: Claude Code on the devbox had been starting with **no anchor file
and no skills for seven weeks**, while `CLAUDE.md` — the file asserting that
GitHub is the source of truth — sat outside the source of truth.

Found by accident. A verification command intended for the MacBook was pasted
into the devbox session; the resulting `find` dump of the home directory
exposed what the repo did and did not contain.

Fixed in `f8f32e5` (18 files, 93 → 111 tracked). The June `README.md` was
deliberately NOT committed: it claims "pre-devbox scaffold, app/infra built
later", which contradicts reality. It is rewritten in Phase 12.

#### Finding 2 — `infra/envs/prod` is a stale scaffold that contradicts two ADRs

It exists in git (6 files, Phase 4 mirror of stage, never applied,
`desired_count = 0`) and was never updated by the C2 refactor:

```text
- still contains module "iam_github_oidc" → the exact construct ADR-0015
  removed from stage because destroy deletes its own permissions mid-run
- passes db_secret_arn where the post-C2 module takes db_secret_arn_pattern
  → this directory cannot plan against the current modules AT ALL
- no depends_on = [module.alb] on ecs (2c4162b went to stage only)
  → the ADR-0016 ENI/IGW teardown race is built in from birth
- declares its own ECR repo (…-app-prod) → conflicts with promotion-by-digest;
  decide one shared ECR vs cross-repo image copy BEFORE promote-prod.yml
- destroy.yml offers "prod" in its dropdown with nothing behind it
```

The second bullet is the serious one: **an entire IaC directory has been failing
to validate for seven weeks and CI never said so**, because `terraform validate`
does not cover the whole tree.

Phase 9 was therefore redefined to start with **9.0 — reconciliation, not
construction**.

#### New invariants adopted (now in `docs/next-phases.md`)

```text
- a fix to a SHARED invariant is applied to EVERY environment directory in the
  same commit, not only to the one currently being exercised
- CI validates EVERY IaC directory; an unvalidated directory rots invisibly
- "GitHub is the source of truth" is a claim to VERIFY, not to assume
```

Both findings have the same shape as the infrastructure bugs this project
already documents: something looked finished, was never exercised on the path
that would expose it, and stayed broken until an accident surfaced it.

---

### Phase 8 session 3 (2026-07-25) — verification cycle DONE ✅

Goal: run the C2 verification cycle that session 2 left open. Result: closed, but
only after three further latent bugs were found and fixed. **C2 itself was sound —
no self-deletion of permissions occurred in any run this session.**

**Proof of completion:**
- `deploy-stage #18` green (14m23s) from a fully destroyed account.
- `destroy #7` green END-TO-END (8m21s), including the "no billable resources
  remain" verification step. First time destroy.yml ever completed on Actions.
- Live demo verified between the two: `/health` 200, `/api/db-check` =
  `{"status":"ok","db":"connected"}`, ECS running 1/1, task def revision 9.

**Bug 1 (b71b846) — empty ECR_URL on a from-scratch cycle.**
`deploy-stage.yml` resolved `ecr_repository_url` via `terraform output -raw`
against an EMPTY stage state (ECR is created by the stage apply, which had not
run yet). `terraform output` failed, but `echo "ecr_url=$(...)"` swallowed the
error, so the step went GREEN with an empty value. `docker build` then got the
tag `":<sha>"` → `invalid reference format`.
Why it never appeared before: earlier green runs (#10, #12) ran on top of a
stage already applied locally, so the repository existed.
Fix: a targeted `terraform apply -target=module.ecr` before the build (keeps ECR
under Terraform management), plus `set -euo pipefail` and an explicit empty-check.

**Bug 2 (b110b41) — two independent teardown failures. See ADR-0016.**
- `iam:ListInstanceProfilesForRole` was dropped when C2 narrowed
  `IamManageScoped` to the two ECS roles. The AWS provider calls it while
  deleting ANY IAM role, so both ECS role deletions failed with AccessDenied.
- **No dependency edge exists between `module.alb` and the IGW.** Terraform
  destroys them CONCURRENTLY; the ALB's ENIs still held mapped public IPs →
  `DependencyViolation` on `DetachInternetGateway` after ~20 min of retries.
  Fix: a targeted `terraform destroy -target=module.alb` before the full
  destroy. A targeted destroy also removes dependents, so `module.ecs` goes
  first and its task ENIs are released too.

**Bug 3 (58ec209) — the guard could not verify its own invariant.**
`destroy.yml` asserts "no EKS in v0" via `aws eks list-clusters`, but the deploy
role had no `eks:ListClusters`. The teardown had already succeeded; the run went
red on the assertion. Fix: a read-only `TeardownVerifyRead` statement.

**Also fixed (6944229): `deploy-stage.yml` had `on: push: branches: [main]`.**
Every push to main deployed ALB + RDS + ECS. Three of that session's deploys were
unintended side effects of documentation commits. Now `workflow_dispatch` only.

**IMPORTANT correction to the Phase 7 analysis.** The destroy #3 failure on
`ec2:DetachInternetGateway` was recorded as a consequence of the deploy role
self-deleting its permissions. Session 3 reproduced the identical failure with
the role's permissions fully intact — so that failure was, at least in part, the
IGW/ALB ordering race of Bug 2, not permission loss. ADR-0015 remains valid:
self-deletion was real, proven separately, and separately fixed.

**Method note that paid off:** the race is NONDETERMINISTIC. A local
`terraform destroy` of the same graph succeeded, with IGW and ALB both reporting
"Destruction complete after 27s". A bug that sometimes passes is why this sat
undiagnosed for two months. Read the concurrency in the log, not just the error.

**Session gotchas:**
- Recovery from the failed Actions destroy was again a LOCAL `terraform destroy`
  under demo-admin. Same pattern as Phase 6/7.
- No stuck `.tflock` this time — the role kept S3 access throughout, itself
  evidence C2 worked.
- After a full teardown, `stage/terraform.tfstate` shrinks to ~182 bytes rather
  than disappearing. That is the expected empty-state marker.

### Phase 8 session 2 (C2 refactor — OIDC to its own bootstrap state)

Goal: make `destroy.yml` run fully end-to-end via Actions OIDC by removing the
self-deletion-of-permissions trap. Root cause (proven in session 1):
`module.iam_github_oidc` lived inside `infra/envs/stage`, so `terraform destroy`
under the deploy role deleted the role's own inline policy + the OIDC provider
mid-run.

**Decision recorded as ADR-0015.** Supersedes the OIDC-placement part of ADR-0014.

**Done (commit 5735430) — VERIFIED against AWS in session 3:**
- **New level `infra/bootstrap-oidc/`** with its own remote state, S3 backend
  `key = bootstrap-oidc/terraform.tfstate`.
- **Stage cleaned:** removed `module "iam_github_oidc"`, its output, and the
  `github_owner/repo/branch` variables. (Session 3 also removed the matching dead
  `TF_VAR_github_*` env from deploy-stage.yml — Terraform had been ignoring them.)
  **NOTE: `infra/envs/prod` was NOT cleaned — see session 4, finding 2.**
- **Module `iam_github_oidc` changed (two security improvements):**
  1. `db_secret_arn` → `db_secret_arn_pattern` (wildcard). The OIDC level is
     applied BEFORE stage exists, and the DB secret carries a per-cycle random
     suffix, so `GetSecretValue` must be scoped to
     `arn:...:secret:<name_prefix>-db-credentials-*`. The ECS execution role
     still uses the EXACT secret ARN — unchanged.
  2. `IamManageScoped` resources narrowed from `role/<name_prefix>-*` to exactly
     the two ECS roles. The old wildcard ALSO matched the deploy role itself,
     giving it `iam:DeleteRolePolicy` over itself — the deeper cause of
     self-deletion. (Session 3 caveat: narrowing the RESOURCES was right, but the
     ACTION list was left incomplete — see Bug 2.)
- **Reverted retry hack 8d3ed9d**: back to a plain `terraform destroy`.

### Phase 8 session 1 (repeatable lifecycle via CI) — context that led to C2

- **Node 24 actions bump (181cabd).** checkout v4→v5, setup-node v4→v5,
  setup-python v5→v6. Residual "Node.js 20 deprecated" warning is informational.
- **Repeatability-check — CLOSED ✅.** Two fresh applies of stage after a full
  destroy, each "34 added, 0 changed, 0 destroyed", no name conflicts.
- **deploy-stage.yml via Actions OIDC — green at #10, #12**, but on top of an
  already-applied stage. The from-scratch path was only proven in session 3.
- **gotcha: stage has NO `demo_account_id` variable.** Local apply -var set is
  `owner`, `state_bucket_name`, `budget_email`, `app_image` only.

### Phase 6 result (DONE — first AWS stage deploy)

All checks PASSED against AWS: `/health` 200 (no DB), `/api/health` ok (no DB),
`/api/db-check` connected; run-task migrate / seed / db-assert exit 0;
Playwright smoke against the ALB URL passed. No NAT, no EKS.

Resource naming (identifiers change every cycle):

```text
VPC + 2 public subnets (10.0.0.0/24, 10.0.1.0/24) + 2 private-db subnets
ALB      aws-devops-sdet-demo-stage-alb
ECS      cluster ...-stage-cluster, service ...-stage-app
RDS      aws-devops-sdet-demo-stage-db...rds.amazonaws.com:5432
secret   aws-devops-sdet-demo-stage-db-credentials-<suffix>
role     arn:aws:iam::993912191738:role/aws-devops-sdet-demo-stage-github-deploy
ECR      993912191738.dkr.ecr.us-west-2.amazonaws.com/aws-devops-sdet-demo-app
```

### Phase 6 learnings / gotchas (IMPORTANT, carry forward)

- **Run long applies under SSH-disconnect protection.** RDS takes ~5-10 min. A
  dropped apply got SIGHUP mid-create, leaving a stuck S3 lockfile + orphaned
  resources. Use `nohup ... &` + `tail -f`, or tmux.
- **Recovery pattern for an interrupted apply:** read the lock id from the
  `.tflock` JSON in S3, `terraform force-unlock <id>`, `terraform import` each
  orphan, `plan` until `0 to destroy`, then re-apply.
- **app_image has no real default.** Local apply MUST pass
  `-var="app_image=<ECR_URL>:<sha>"`.
- **DB-assert build-context bug (fixed, 36ecfba).** The image is built from
  context `./app` and does NOT contain `tests/`. `app/scripts/assert_seed.py`
  ships via `COPY scripts ./scripts`. `tests/db/assert_seed.py` remains the local
  `make test-db` gate vs compose.
- **CloudWatch log stream format** is `app/app/<task-id>`, NOT `ecs/app/<task-id>`.
- **Image build note:** buildkit produces an OCI manifest list; ECS Fargate
  pulled it fine.

### Phase 7 result (DONE — destroy validation, 2026-06-08)

Stage fully destroyed; AWS CLI verification all empty. State bucket intentionally
REMAINS. The teardown was completed via LOCAL `terraform destroy`, NOT via
destroy.yml end-to-end (that was achieved on 2026-07-25 — session 3). The first
destroy.yml run surfaced two latent deploy-role bugs:

1. **Trust policy missing the environment sub.** destroy.yml runs as
   `workflow_dispatch` with `environment: stage`, so GitHub sends
   `sub=repo:UVE-QA/aws-devops-sdet-demo:environment:stage`. Fix (2c1efcc):
   `github_environments` var, both sub forms concatenated.
2. **Permissions policy absent in AWS (state/AWS drift)** from the interrupted
   Phase 6 apply.

**Phase 7 learnings (carry forward):**
- **A `-target` apply does NOT reconcile the rest of the config.** Read the
  destroy plan itself; don't panic on an intermediate targeted-plan.
- **"has been deleted" in a refresh ≠ resource never existed.** Confirm against
  AWS CLI first.
- **Latent OIDC-role bugs only surface on the FIRST real run of a given path.**
  Expect this every time a path runs for the first time.

---

## Project shape

- Portfolio/demo platform for DevOps / Cloud / QA-SDET interviews. The app stays
  minimal; the value is the cloud delivery construction, IaC, CI/CD, test
  automation, security model, and budget-safe lifecycle.
- Phase-gated execution. No jumping ahead; each phase ends with summary +
  validation + STOP + explicit confirmation.
- All prompts/instructions/skills in English. Chat discussion may be Russian.

## Infrastructure decisions

- **Account model:** dedicated AWS Organizations member account. Never deploy
  workload into the management account. Human access via IAM Identity Center
  (profile `demo-admin`); GitHub access via OIDC. No static keys.
- **Region:** us-west-2. **Tag:** Project = aws-devops-sdet-demo (+ Owner=UVE).
- **MVP architecture:** single app container (FastAPI static HTML + API) →
  Browser → ALB → ECS Fargate → RDS PostgreSQL.
- **Terraform state levels.** Three exist today; **six** at the end of the MVP
  track. Levels marked NOT BUILT are decided, not implemented:

```text
1. infra/bootstrap       S3 state bucket. LOCAL state, applied once. Permanent.
2. infra/bootstrap-oidc  OIDC provider + deploy roles. S3 state. Permanent.
3. infra/shared-ecr      container registry. S3 state. Permanent.
                         NOT BUILT — ADR-0018, Phase 9.0.
4. infra/public-site     dashboard S3+CloudFront. S3 state. Permanent.
                         NOT BUILT — Phase 11.
5. infra/envs/stage      workload. Destroyed every cycle.
6. infra/envs/prod       workload. Destroyed every cycle. Stale scaffold until
                         Phase 9.0 reconciles it.
```

  Only levels 5 and 6 are ever destroyed. Anything that must survive a teardown
  — including the artifact that PROVES the teardown works — belongs above them.
  The registry qualifies and nobody noticed until prod needed to run an image
  that stage's own teardown would delete (ADR-0018).
- **Two chicken-and-egg bootstraps, both first run LOCALLY (demo-admin):** the
  state bucket, then the OIDC provider + deploy role.
- **Deploy-role IAM scope:** S3 on the state bucket + ECR/ECS/RDS/logs/secrets/
  EC2/budgets via `*` + `IamManageScoped` on EXACTLY the two ECS roles +
  `GetSecretValue` on `<name_prefix>-db-credentials-*` + `PassRole` on the ECS
  roles + read-only `GetOpenIDConnectProvider` + read-only `TeardownVerifyRead`.
  It deliberately has NO rights over its own role → cannot self-delete.
  **Lesson: when narrowing an IAM statement, narrow the RESOURCES, but re-derive
  the ACTION list from what the provider actually calls.**
- **DB password:** `random_password` (length 32) → Secrets Manager; ECS reads it
  via the task `secrets` block, never plaintext env, never in repo.
- **No-NAT egress:** Fargate task in a public subnet with a public IP reaches
  ECR/Secrets/Logs over the IGW. The cost of this choice is the ENI/IGW teardown
  ordering problem (ADR-0016).
- **Health checks:** `/health` and `/api/health` must NOT touch the DB;
  `/api/db-check` is the only DB endpoint. Otherwise ECS cannot reach steady
  state before the migrate task runs — a deadlock.
- **DB driver:** psycopg2-binary. **Postgres 16** pinned (compose == RDS).
- **Provider lockfile** committed for linux_amd64 + linux_arm64.

## Repeatable lifecycle (deploy → demo → destroy → repeat)

- **Survives every cycle:** the state bucket, `infra/bootstrap-oidc`, (from
  Phase 9.0) `infra/shared-ecr`, and (from Phase 11) `infra/public-site`.
- **Destroyed every cycle:** ECS/ALB/RDS/logs/VPC. ECR leaves this list in
  Phase 9.0 — see ADR-0018.
- Start of a cycle (LOCAL, demo-admin): `aws sso login --use-device-code` →
  apply `infra/bootstrap` → apply `infra/bootstrap-oidc` → (from Phase 9.0)
  apply `infra/shared-ecr` → then `deploy-stage.yml` via the Actions UI. The
  permanent levels are applied once per ACCOUNT, not once per cycle; a normal
  cycle finds them already there.
- End of a cycle: `destroy.yml` via the Actions UI, confirm = `DESTROY`.
- Idempotency fixes: ECR `force_delete = true` (becomes `false` once the
  registry moves to a permanent level — its only purpose was per-cycle teardown,
  ADR-0018); Secrets Manager
  `recovery_window_in_days = 0`; RDS `skip_final_snapshot = true` +
  `backup_retention_period = 0`; CloudWatch log group Terraform-managed.
- Safety nets: Budgets module (free), monthly limit $20, alerts at 50% ACTUAL /
  100% FORECASTED; `destroy.yml` ends with a verification step that exits
  non-zero if anything billable remains.

## CI/CD

- Workflows: `ci.yml`, `deploy-stage.yml`, `destroy.yml`. OIDC only.
  `promote-prod.yml` is added in Phase 9.
- CI is deterministic and AWS-free.
- One-off tasks (migrate/seed/db-assert) reuse the SAME ECS task definition via
  `aws ecs run-task` command overrides (ADR-0007): `["alembic","upgrade","head"]`,
  `["python","scripts/seed.py"]`, `["python","scripts/assert_seed.py"]`
  (NOTE: `scripts/`, not `tests/db/`).
- run-task network: public subnets + ECS app SG + assignPublicIp=ENABLED.

### Workflow status (current)

- **ci.yml**: `local-ci` reuses the Makefile targets; `terraform-checks` runs
  `terraform fmt -check -recursive` + `make tf-validate`. **Known gap: validate
  does not cover every IaC directory — `infra/envs/prod` was never checked.
  Fixed in Phase 9.0.**
- **deploy-stage.yml**: `workflow_dispatch` ONLY. `environment: stage`.
  Order: OIDC → ECR login → init → targeted apply of `module.ecr` → resolve
  `ecr_repository_url` (fails loudly if empty) → build/push by SHA → apply with
  `TF_VAR_app_image` → run-task migrate/seed/db-assert → Playwright smoke →
  artifact. Green from scratch at #18.
- **destroy.yml**: `workflow_dispatch` (environment + confirm). Guard fails
  unless confirm == DESTROY. Order: OIDC → init → targeted destroy of
  `module.alb` → full destroy → verification. Green end-to-end at #7 (8m21s).
  **Its `prod` dropdown choice is a placeholder with nothing behind it.**

### GitHub repo config (carry forward)

- 6 ENVIRONMENT variables under environment `stage`, no secrets:
  `AWS_REGION`, `OIDC_ROLE_ARN`, `TF_STATE_BUCKET`, `TF_VAR_BUDGET_EMAIL`,
  `TF_VAR_DEMO_ACCOUNT_ID`, `TF_VAR_OWNER`.
- GOTCHA: the variable is `OIDC_ROLE_ARN`, NOT `GITHUB_OIDC_ROLE_ARN` — GitHub
  reserves the `GITHUB_` prefix.
- Env-scoped vars are visible only to jobs with `environment:` set.
- The deploy role trust allows both `ref:refs/heads/main` and
  `environment:<name>` subs (`github_environments`, default ["stage"]).
- `gh` CLI is NOT installed on the devbox — run workflows via the GitHub UI.
- A `prod` GitHub Environment with required reviewers is created in Phase 9.

## Open debts / next steps

- **Phase 9.0 reconciliation** is the immediate next action. See ADR-0017 and
  `docs/next-phases.md`.
- **Documentation debt, now scheduled rather than floating.** Still missing:
  README.md, docs/architecture.md, docs/demo-script.md (Phase 12);
  docs/cost-control.md, docs/interview-talking-points.md,
  docs/lightsail-devbox.md (Phase 18). Present: phase-gates.md,
  preflight-inventory.md, next-phases.md, decisions/0001–0017, sessions/.
- **`architecture.md` must be written against the SIX-level state model**
  (ADR-0018), not the three-level model of ADR-0015 — otherwise it is stale on
  arrival. This has now been revised twice before being written, which is the
  argument for writing it in Phase 12 and not earlier.
- **Skills freshness:** `tf-workflow` and `teardown` should mention the
  multi-level bootstrap and the targeted apply/destroy passes. Likely stale.
- **project-prompt.md** should reflect the repo shape after C2 (§7 repo
  structure, §10 bootstrap ordering) and note that **§14 is superseded by
  docs/next-phases.md**.
- **Repository visibility: public at Phase 11, not before (decided 2026-07-25).**
  Phase 11's dashboard reads run history from the PUBLIC GitHub API, so the repo
  must be public by then; a portfolio repo nobody can open is a contradiction
  anyway. Prerequisite: gitleaks over the FULL history plus a conscious decision
  about the account id, the devbox IP and the SSO start URL. Deferred rather
  than rejected — see docs/next-phases.md 11.0.
- **Deferred idea: a session-start skill that clones the repo into the chat
  sandbox** and reads CLAUDE.md / phase-gates.md / next-phases.md /
  discussion-log.md itself. Verified feasible: the Cowork sandbox reaches
  github.com over HTTPS (SSH out is blocked). Blocked only by the repo being
  private, since asking for a PAT is against the project's own rules. Unblocks
  itself at Phase 11. Its appeal is that the clone lives in the ephemeral
  sandbox, so it is NOT a second working copy on a laptop.
- **RESOLVED (1f50243): this file now lives in git at `docs/discussion-log.md`.**
  The copy inside the Claude Project is a MIRROR, refreshed at phase gates for
  chats that have no devbox access. Never edit the mirror; edit the repo.

## Collaboration / context model

- One working copy, on the Lightsail devbox (`ubuntu@34.213.147.86`,
  `~/aws-devops-sdet-demo`); laptops connect via SSH. GitHub is the source of
  truth. Don't sync repos via Dropbox/iCloud or scp between machines.
- **`~/Projects/aws-devops-sdet-demo` on the MacBook** is NOT a working copy. As
  of session 4 everything unique in it has been committed, so it holds nothing
  the repo does not — except the stale June `README.md`, `discussion-log.md` and
  `project-prompt.md`. It can be archived or deleted.
- **`~/Projects/_claude-transfer` on the MacBook** is the buffer for files
  produced in chat that still need to reach the devbox. It should be empty most
  of the time; anything sitting there is uncommitted. Contains `send.sh` and
  `README-TRANSFER.md`.
- SSH alias configured on the MacBook: `ssh devbox`, `scp file devbox:/tmp/`
  (`~/.ssh/config`, with `ServerAliveInterval 60`).
- Context in layers to save tokens: ADRs (always, the "why"), `phase-gates.md`
  (where we are), session summaries on demand.
- `CLAUDE.md` is the always-read anchor/router; skills load on demand. **Both are
  in git as of f8f32e5.**
- **Manual Project-file sync (IMPORTANT):** `discussion-log.md` and
  `project-prompt.md` are READ-ONLY copies inside the Claude Project and are NOT
  in git; chat edits do not save back. At EVERY phase gate the user must
  manually replace these Project files with the freshly generated full versions.
- **Project-file update workflow:** new full version → user commits any
  git-tracked parts → user uploads the new file to the Project → user DELETES
  the old version. Keep exactly one current copy of each; no -2/-3 copies.

## Skills design

- Skills = operations (verbs); phases = state (phase-gates + CLAUDE.md).
- 9 skills: meta (session-protocol, phase-gate, skill-maintenance), infra
  (local-dev, tf-workflow, deploy-stage, teardown), product (app-dev, test-dev).
- The `description` is the trigger mechanism: rich trigger phrases (EN+RU) + an
  explicit "Do NOT use for" boundary naming the neighbour skill.
- app-dev → test-dev: any contract change must sync tests before the task is done.
- New skills added via `skill-maintenance`. ~9 is the comfortable ceiling.

## Deliberately out of scope

Recorded with reasons in `docs/next-phases.md`: EKS/Helm/ArgoCD, React/Vite,
Grafana/Prometheus/Loki, WAF and CloudFront in front of the app, the dashboard on
the devbox, private ECS subnets + NAT, blue/green and autoscaling, a second
workload member account, a general nightly-teardown backstop. Being able to
explain why something was NOT built is itself an interview asset.

## Tooling decisions

- **Claude Code on the devbox**, via VS Code Remote-SSH or bare SSH. Bare SSH
  from Terminal.app proved sufficient for operations-heavy sessions and avoids
  UI contention. **Cowork on the MacBook** was used for session 4 (planning and
  document production) — a reasonable split: Cowork for thinking and writing,
  Claude Code on the devbox for anything that touches the repo or AWS.
- Devbox tool versions: Docker 29.6.2, Compose v5.3.1, AWS CLI 2.34.63,
  Terraform 1.15.8, Node 20.20.2, Python 3.12.3, Git 2.43.0, Make 4.3.
- **Shell gotchas that cost time:** long heredocs get mangled over browser SSH
  (write long docs in short flat chunks and verify each); pasted example commands
  containing `...` will be run literally; `exit` typed into a `tail -f` does
  nothing — use Ctrl+C; typing at a `>` continuation prompt appends to the
  command you are already building (this cost one `scp` into `/tmp/clear`).
- **Prefer a checked-in patch script over a long interactive heredoc** for
  surgical edits to long docs: it fails loudly, changes nothing on mismatch, and
  is reviewable before it runs.
