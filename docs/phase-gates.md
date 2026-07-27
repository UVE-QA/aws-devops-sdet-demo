# Phase Gates — Session Cursor

Status tracker for the phased build of `aws-devops-sdet-demo`.
Each phase ends with: STOP → checklist → validation commands → explicit
confirmation before the next phase. This file is the "where we are" cursor.

## Status overview

| Phase | Title                          | Status      | Commit    |
|-------|--------------------------------|-------------|-----------|
| 0     | Discovery / preflight          | ✅ done     | (pre-3cf1c98) |
| 1     | Lightsail devbox prep          | ✅ done     | (pre-3cf1c98) |
| 2     | Minimal local app skeleton     | ✅ done     | 3cf1c98   |
| 3     | Docker Compose + local tests   | ✅ done     | de781bc   |
| 4     | Terraform foundation           | ✅ done     | 0256dc8   |
| 5     | GitHub Actions + OIDC          | ✅ done     | 40eb757   |
| 6     | First AWS stage deploy         | ✅ done     | 36ecfba   |
| 7     | Destroy validation             | ✅ done     | 497a4b2   |
| 8     | Feature expansion              | 🟡 lifecycle done, features pending | ee0a25e |
| 9     | Prod env, promotion, HTTPS     | ✅ done     | 25d4dab   |
| 10    | Thin application slice         | ✅ done     | 1bf89ac   |
| 11.0  | Publish the repository         | ✅ done (pulled forward) | a1c4402 |
| 11.1  | Public dashboard               | 🟡 11.1a + 11.1b done, 11.1c open | (this patch) |

Phases 9-19 are planned in `docs/next-phases.md` (MVP track 9-13, polish
track 14-19), shaped by ADR-0017. This table tracks only what is done.

## Completion criteria & validation

### Phase 0 — Discovery / preflight
- Criteria: AWS account model confirmed; demo account ID, region, SSO profile,
  GitHub owner/repo/branch, devbox status, owner tag, state bucket name fixed.
- Validation:
```bash
  aws sso login --profile demo-admin --use-device-code
  aws sts get-caller-identity --profile demo-admin   # Account must be the demo account
```

### Phase 1 — Lightsail devbox prep
- Criteria: devbox provisioned (Ubuntu 24.04, static IP, SSH-only); toolchain
  installed and version-verified.
- Validation:
```bash
  docker --version && docker compose version
  aws --version && terraform version
  node --version && python3 --version && git --version
```

### Phase 2 — Minimal local app skeleton
- Criteria: FastAPI app (/, /health, /api/health, /api/db-check); SQLAlchemy
  model demo_items; Alembic revision 0001; static index.html with test ids.
- Validation:
```bash
  python3 -c "import app.src.main"   # imports cleanly
  ls app/alembic/versions/           # revision 0001 present
```

### Phase 3 — Docker Compose + local tests
- Criteria: Dockerfile (psycopg2-binary, non-root); docker-compose (postgres:16
  not exposed + app:8000, healthcheck); migrate/seed/db-assert; Playwright
  smoke; Makefile (9 targets). All run for real.
- Validation:
```bash
  make local-up
  curl -s http://localhost:8000/health
  curl -s http://localhost:8000/api/db-check
  make migrate && make seed
  make test-db
  make test-smoke
  make local-down
```

### Phase 4 — Terraform foundation
- Criteria: infra/bootstrap (S3 state bucket, local state, README);
  infra/envs/{stage,prod}/backend.tf (S3, use_lockfile); 8 modules (network,
  ecr, alb, ecs, rds, iam_github_oidc, observability, budgets); stage filled,
  prod scaffold; outputs without secrets; fmt + validate clean; lockfile
  committed. NO terraform apply/destroy. NO real backend init.
- Validation:
```bash
  terraform fmt -recursive -check
  cd infra/envs/stage && terraform init -backend=false && terraform validate
```

### Phase 5 — GitHub Actions + OIDC
- Criteria: ci.yml (local Docker Compose, fmt, validate -backend=false, no AWS
  creds); deploy-stage.yml (OIDC, build/push, init/plan/apply, run-task
  migrate/seed/db-assert, smoke, artifacts); destroy.yml (confirm=DESTROY,
  verification step).
- Validation: workflow files present; `terraform validate` passes in CI path.
- GitHub config notes (carry forward to Phase 6+):
  - 6 vars live as ENVIRONMENT variables under environment `stage` (not repo-wide):
    AWS_REGION, OIDC_ROLE_ARN, TF_STATE_BUCKET, TF_VAR_BUDGET_EMAIL,
    TF_VAR_DEMO_ACCOUNT_ID, TF_VAR_OWNER. No secrets (OIDC).
  - Visible only to jobs with `environment:` set. deploy-stage (environment: stage)
    and destroy (environment: ${{ inputs.environment }}) see them; ci.yml has no
    environment and needs no AWS, so that is fine. A future AWS job WITHOUT an
    `environment:` would NOT see these — add the environment or duplicate as repo vars.
  - Variable was named OIDC_ROLE_ARN, NOT GITHUB_OIDC_ROLE_ARN: GitHub reserves the
    GITHUB_ prefix for variable names. Workflows reference vars.OIDC_ROLE_ARN.
  - These vars only work AFTER the local first apply creates the deploy role
    aws-devops-sdet-demo-stage-github-deploy (Phase 6). Until then Actions OIDC fails.


### Phase 6 — First AWS stage deploy
- Criteria: bootstrap applied locally (state bucket exists); first stage apply
  LOCAL (creates OIDC provider + deploy role); ALB/ECS/RDS healthy; migrate +
  seed + db-check + smoke pass against AWS.
- Validation:
```bash
  aws ecs list-clusters --profile demo-admin --region us-west-2
  aws rds describe-db-instances --profile demo-admin --region us-west-2
  aws elbv2 describe-load-balancers --profile demo-admin --region us-west-2
```

- Phase 6 learnings (carry forward):
  - Run the first/long applies under SSH-disconnect protection (nohup or tmux):
    RDS takes ~5-10 min and Lightsail browser SSH drops long commands. A dropped
    apply got SIGHUP mid-create, leaving a stuck S3 lockfile + orphaned resources
    (public subnet, ALB) created in AWS but absent from state.
  - Recovery pattern: `terraform force-unlock <id>` (id from the .tflock JSON in
    S3) → `terraform import` each orphan (subnet, ALB) → plan (0 to destroy) →
    re-apply (idempotent, finishes the rest).
  - app_image has no real default: local apply must pass
    -var="app_image=<ECR_URL>:<sha>" or it reverts the service to the :bootstrap
    placeholder. Actions sets TF_VAR_app_image itself.
  - DB-assert bug found & fixed (commit 36ecfba): deploy-stage.yml ran
    python tests/db/assert_seed.py inside the app image, but the image is built
    from context app/ and does not contain tests/. Added app/scripts/assert_seed.py
    (ships via COPY scripts ./scripts); workflow now runs scripts/assert_seed.py.
    tests/db/assert_seed.py stays as the local `make test-db` gate.
  - CloudWatch log stream format is app/app/<task-id> (awslogs-stream-prefix=app),
    not ecs/app/<task-id>.

### Phase 7 — Destroy validation
- Criteria: destroy removes ECS/ALB/RDS/ECR/logs/VPC; state bucket remains;
  re-apply after destroy succeeds with no name conflicts (repeatability).
- Validation:
```bash
  aws ec2 describe-nat-gateways --profile demo-admin --region us-west-2   # none
  aws eks list-clusters --profile demo-admin --region us-west-2           # none
  aws ecr describe-repositories --profile demo-admin --region us-west-2   # app repo gone
```
- STATUS: DONE (2026-06-08). Stage torn down; verified zero billable resources
  (ECS/RDS/ALB/ECR/logs/VPC/secret all empty; no NAT, no EKS, no unattached EIP).
  State bucket aws-devops-sdet-demo-tfstate-993912191738 intentionally remains.
- HOW: teardown completed via LOCAL `terraform destroy` (AWS_PROFILE=demo-admin),
  NOT via destroy.yml end-to-end. The first Actions-OIDC destroy run surfaced two
  latent deploy-role bugs, both fixed in commit 2c1efcc:
  (1) trust policy allowed only sub=ref:refs/heads/main; destroy.yml runs with
      environment:stage -> sub=...:environment:stage was denied. Added
      github_environments var; trust now permits both ref and environment subs.
  (2) the role's permissions inline policy was absent in AWS (state/AWS drift
      from an interrupted Phase 6 apply); the Actions run got AccessDenied on
      s3:PutObject to the state bucket. Re-created via local targeted apply.
  Both fixes are committed and the live role was corrected, but a full
  end-to-end destroy.yml (Actions OIDC) run was NOT re-validated after the fixes.
- CLOSED LATER (in Phase 8): the repeatability-check passed (two fresh applies
  after a full destroy, 34 added each, no name conflicts), and destroy.yml
  finally ran green end-to-end via Actions OIDC on 2026-07-25 (destroy #7,
  8m21s). See the Phase 8 section for the three bugs that had to be fixed first.

### Phase 8 — Repeatable lifecycle via CI + feature expansion
- C2 refactor (ADR-0015): GitHub OIDC provider + deploy role moved OUT of
  infra/envs/stage into infra/bootstrap-oidc/ with its own remote state
  (key bootstrap-oidc/terraform.tfstate). Fixes destroy.yml self-deleting the
  deploy role's own permissions mid-destroy. Also: IamManageScoped narrowed to
  the two ECS roles only (no longer matches the deploy role itself); deploy-role
  GetSecretValue scoped to <name_prefix>-db-credentials-* wildcard; retry commit
  8d3ed9d reverted to a plain terraform destroy step.
- Bootstrap ordering is now TWO local-first applies per cycle (demo-admin):
  (1) infra/bootstrap (S3 state bucket), (2) infra/bootstrap-oidc (OIDC + role).
  After both, deploy-stage.yml and destroy.yml run end-to-end via Actions OIDC.
- Criteria to close: local apply bootstrap-oidc -> local/Actions apply stage ->
  deploy-stage.yml green via Actions -> destroy.yml green via Actions WITHOUT
  failing on self-deleted permissions -> green verification step.
- STATUS: lifecycle CLOSED (2026-07-25). The full cycle is proven through
  Actions: local apply of infra/bootstrap + infra/bootstrap-oidc, then
  deploy-stage #18 green (14m23s; /health 200, /api/db-check connected, smoke and
  db-assert pass), then destroy #7 green end-to-end (8m21s) including the
  "no billable resources remain" verification step. Zero manual AWS operations.
- C2 itself was sound: no self-deletion of permissions occurred in any run. But
  three independent latent bugs sat underneath it, each observable only on a
  from-scratch cycle:
  (1) b71b846 - deploy-stage resolved ecr_repository_url from an empty stage
      state, producing the invalid docker tag ":<sha>". ECR is now created by a
      targeted apply before the build, and an empty URL now fails the step.
  (2) b110b41 - iam:ListInstanceProfilesForRole was lost in the C2 narrowing, so
      both ECS role deletions were denied; and no dependency edge exists between
      the ALB and the IGW, so Terraform destroyed them concurrently and hit
      DependencyViolation on detach. See ADR-0016.
  (3) 58ec209 - eks:ListClusters was missing, so the workflow's own "no EKS in
      v0" assertion could not run and reddened an otherwise clean teardown.
- Also 6944229: deploy-stage.yml no longer triggers on push to main. Every push
  had been deploying billable infrastructure as a side effect.
- Feature expansion itself is still PENDING; only the lifecycle half of Phase 8
  is done. Scope is now defined in docs/next-phases.md, decisions in ADR-0017.
- 2026-07-25 planning session, finding 1: the CONTROL LAYER had never been
  committed. CLAUDE.md, .claude/skills/ (9 skills + registry),
  docs/sessions/, docs/skills-structure.md, docs/project-instructions-pointer.md
  and docs/decisions/0000-template.md existed ONLY in a non-git folder on the
  MacBook, created 2026-06-06. The repo had 93 tracked files and none of them,
  so Claude Code on the devbox had been starting with no anchor and no skills
  for seven weeks. Fixed in f8f32e5 (93 -> 111 tracked files). The stale
  README.md was deliberately NOT committed; it is rewritten in Phase 12.
  Lesson: "GitHub is the source of truth" was asserted by a document that was
  itself outside the source of truth. Verify the claim, do not assume it.
- 2026-07-25 planning session, finding 2: infra/envs/prod is a stale Phase 4
  scaffold that contradicts ADR-0015 and ADR-0016. Details and the fix are
  Phase 9.0 below.

### Phase 9 — Prod environment, promotion, HTTPS  [DONE 2026-07-26]
- Plan: docs/next-phases.md. Decisions: ADR-0017 (same account for prod, hybrid
  availability, HTTPS on an owned domain, phased external access).
- STARTS WITH RECONCILIATION, NOT CONSTRUCTION. infra/envs/prod already exists
  in git as a Phase 4 scaffold mirror (committed, never applied,
  desired_count = 0) and was never updated by the C2 refactor. It looks
  finished and is not:
  (1) it still contains module "iam_github_oidc" - the construct ADR-0015
      removed from stage because a destroy under that role deletes its own
      permissions mid-run;
  (2) it passes db_secret_arn where the post-C2 module takes
      db_secret_arn_pattern, so this directory cannot plan against the current
      modules at all - which proves terraform validate does not cover the
      whole tree;
  (3) it has no depends_on = [module.alb] on the ecs module (commit 2c4162b
      went to stage only), so the ADR-0016 ENI/IGW teardown race is built in;
  (4) it declares its own ECR repository (...-app-prod), which conflicts with
      promotion-by-digest. Decide before writing promote-prod.yml: one shared
      ECR across environments, or an explicit cross-repository image copy;
  (5) destroy.yml offers "prod" in its dropdown with nothing behind it - a
      trap, not a feature. Wire it or remove it.
- Criteria to close 9.0: terraform validate passes for EVERY directory under
  infra/, CI enforces that, and prod differs from stage only in name prefix,
  sizing and intentional prod-only additions.
- STATUS 9.0: DONE (2026-07-25, e1e577a). All five root levels pass
  `terraform fmt -check` and `make tf-validate` with no AWS credentials present;
  CI green at ci #33. prod and stage now have identical module and output
  structure, verified by diffing them. Nothing was applied to AWS.
  Session summary: docs/sessions/2026-07-25-phase-9-0-reconcile-prod.md.
  - ADR-0018 closed the open ECR question: the registry moves OUT of the
    environments into a permanent level infra/shared-ecr. A shared registry left
    in stage state would be deleted by stage teardown, taking the image prod had
    promoted with it. This also retired the two b71b846 workarounds in
    deploy-stage.yml (targeted apply of module.ecr, terraform output lookup).
  - Four defects beyond the five documented ones: prod/outputs.tf was missing
    the four outputs run-task consumes; destroy.yml's prod choice died at OIDC
    authentication because bootstrap-oidc creates exactly one role; destroy.yml
    still exported dead TF_VAR_github_*; state_bucket_name was dead in STAGE too.
  - The validation gap had a second half nobody knew about:
    `terraform init -backend=false` does NOT skip the backend in a directory
    initialized for real — it reuses the cached S3 config in .terraform/ and
    reads state. The target's own comment promised "no AWS creds needed" and was
    false on the devbox; it passed in CI only because a fresh checkout has no
    .terraform/. Now fixed with an isolated TF_DATA_DIR, and the claim is tested
    by re-running with the AWS environment stripped.
  - Root levels are DISCOVERED, not listed, so a new level cannot be added
    without being validated. An empty discovery result is an explicit failure
    (e1e577a) — the first version of the target would have passed green having
    validated nothing, which is b71b846 all over again.
- STATUS 9.1: **DONE (2026-07-26, 25d4dab).** The closing criterion ran end to
  end through Actions with no manual AWS operation: deploy-stage green (14m13s),
  promote-prod PAUSED for required reviewers then green (13m24s, promoted by
  digest, no rebuild), https://app.demo.uveapp.net returned 200 with a
  curl-verified certificate, destroy prod green (8m28s) and destroy stage green
  (8m24s). Post-teardown state verified against the AWS CLI, not Terraform state:
  nothing billable remains beyond the state bucket, the shared registry and one
  hosted zone. Session summary:
  docs/sessions/2026-07-26-phase-9-1-prod-promotion-https.md.
  - HTTPS lives on a DELEGATED SUBDOMAIN, demo.uveapp.net (ADR-0024). The parent
    zone is in org-management, the account this project must not deploy into, so
    delegation is the only acceptable answer rather than the convenient one. A
    new permanent level infra/dns holds the zone and the wildcard certificate;
    the alias record stays in infra/envs/prod because it points at an ALB that is
    rebuilt every cycle. The NS record in the parent zone is manual, one-time and
    untracked by git - the same category as the GitHub protection rules.
  - The teardown verification in destroy.yml searched the WHOLE ACCOUNT for the
    project prefix, so destroying one environment while the other was up would
    have failed a correct teardown. Fixed to an environment-scoped prefix and
    then proven in the same session: prod was destroyed while stage was live and
    the check passed.
  - Two IAM reads were missing and could not have been found by inspection:
    route53:ListTagsForResource and acm:GetCertificate, both issued by data
    sources the configuration never asks to read tags or bodies from. Same class
    as ADR-0016's iam:ListInstanceProfilesForRole. Budget for one failed first
    run on any genuinely new path.
  - Earlier notes said this phase's bootstrap-oidc apply must plan as
    "2 added, 0 changed, 0 destroyed". It planned as 2 added, **1 changed**,
    0 destroyed: the moved OIDC provider's Name tag lost its stage prefix, which
    is correct - the provider is account-wide and the word "stage" in its name
    was always a lie. Assert on "0 destroyed", not on the change count.
- HISTORY 9.1 (2026-07-26, a1c4402). First step, nothing applied to AWS.
  - The OIDC provider is split from the deploy role (ADR-0021). The old combined
    module could not have been instantiated twice: AWS allows one OIDC provider
    per issuer URL per account, so a copied module block would have died on
    EntityAlreadyExists. Found by reading the resource, before any apply.
  - prod's deploy role trusts `environment:prod` and NOTHING else
    (`trust_branch_ref = false`). A `ref:refs/heads/main` subject is satisfied by
    any workflow on the default branch, which would have routed straight around
    the reviewers. One boolean is the whole AWS-side enforcement.
  - `moved` blocks rename the existing provider and stage role in state.
    **The next local apply MUST plan as 1 role + 1 role policy added, 0
    destroyed.** Anything else means a `moved` block is wrong — do not apply
    through it: recreating the provider invalidates the working stage trust.
  - Required reviewers turned out to be unavailable on a private repository
    outside Enterprise, so Phase 11.0 was pulled forward and the repository is
    now public (ADR-0022, ADR-0023). The gate is real in both systems only when
    BOTH halves exist: `trust_branch_ref = false` in IAM and required reviewers
    in GitHub. BOTH NOW EXIST (2026-07-26): the `prod` environment shows
    2 protection rules — required reviewers (UVE-QA) and `main` as the only
    deployment branch — with administrator bypass DISABLED. `Prevent self-review`
    is deliberately off: the sole reviewer is also the triggering account, so
    enabling it would deadlock every promotion. It goes on when a second
    reviewer exists, not before. This is UI state; git cannot assert it, so
    re-check it if promotion ever fails to pause.
  - Session summary: docs/sessions/2026-07-26-phase-9-1-oidc-split.md.
- Everything 9.1 planned is delivered: promote-prod.yml (promotion by digest, no
  rebuild), the prod branch of destroy.yml, and HTTPS (ACM us-west-2 + Route53 +
  443 listener + HTTP->HTTPS redirect).
- Criteria to close 9.1: a full stage -> approve -> prod -> destroy both cycle
  runs through Actions with no manual AWS operation, and https://app.<domain>
  returns 200 with a valid certificate. **MET.**
- Validation:
```bash
  terraform fmt -recursive -check infra
  make tf-validate      # every root level, isolated TF_DATA_DIR, no AWS creds
  curl -sS -o /dev/null -w "%{http_code} %{ssl_verify_result}\n" https://app.demo.uveapp.net/health
```
- Follow-ups left by this phase, none blocking: a stray `demo` NS record sits in
  a NON-authoritative copy of the parent zone (account 478937318617) and should
  be deleted; the GitHub variable TF_STATE_BUCKET is referenced by nothing and
  still exists on the stage environment; three actions are annotated as Node 20
  deprecated on every run.
- New invariants adopted this session (see docs/next-phases.md):
  - a fix to a SHARED invariant is applied to EVERY environment directory in the
    same commit, not only to the one currently being exercised;
  - CI validates EVERY IaC directory - an unvalidated directory rots invisibly.

### Phase 10 — Thin application slice  [DONE 2026-07-26]
- Plan: `docs/next-phases.md` Phase 10. Decision: **ADR-0025**.
- Delivered, all of it unvalidated against a real database:
  `POST/GET/DELETE /api/items` with 201/409/422/404/204; Alembic revision 0002
  (nullable `description`, and the first chain longer than one revision); the
  static page driving the API; 19 pytest/httpx contract cases; Playwright split
  into `smoke` (read-only) and `regression` (destructive); a database assertion
  after a UI action; `scripts/ecs-run-task.sh` shared by both AWS workflows.
- **The finding of this phase**: `promote-prod.yml` ran `npx playwright test` —
  the WHOLE testDir — under a step named "Read-only smoke against prod". The
  comment was an intention the command could not honour, true only while no
  destructive spec existed. The first one would have made prod destructive
  silently. Suites are now split by DIRECTORY and every caller names its
  projects explicitly (ADR-0025).
- A spec outside both directories belongs to no project, runs in no suite and is
  reported by nothing — the e1e577a shape again.
  `tests/playwright/scripts/assert-spec-coverage.sh` fails on it, and was
  verified by breaking it on purpose.
- STATUS: **CLOSED (2026-07-26).** A full cycle ran through Actions from `main`
  at 1bf89ac with no manual AWS operation: deploy-stage 30218469484 green on the
  FIRST attempt (14m54s), promote-prod 30219504665 green after pausing for
  required reviewers (13m31s), destroy prod 30221241572 green (8m24s), destroy
  stage 30221612424 green (8m29s). Post-teardown state verified against the AWS
  CLI: nothing billable remains beyond the four permanent levels. Session
  summary: docs/sessions/2026-07-26-phase-10-aws-validation.md.
  Earlier status, kept because it is the state the cursor correctly refused to
  call done: validated against PostgreSQL on the devbox and green in CI
  (`ci` run 30217591361, first attempt, both jobs), with nothing run against AWS.
- What the devbox run actually established, 2026-07-26:
```text
  migrate     0001 -> 0002 on an EXISTING database, not a schema built from
              nothing. That path had never been exercised before this phase.
  seed        'seed-item-001' already present (id=1) -> no-op. Idempotency
              demonstrated against a genuinely non-empty database.
  spec cover  2 spec files, both resolved by a project
  test-api    19 passed against real PostgreSQL
  test-smoke  2 passed (project smoke)
  test-regr   3 passed (project regression), then the database assertion found
              ui-probe-1785095034 (id=11) written through the browser
  test-db     seed assertion passed
```
- The UI-write gate was also made to FAIL on purpose, with a probe name nothing
  had created: `make test-ui-db UI_PROBE_NAME=deliberately-absent-probe` exits
  non-zero with the row named in the message. A gate never seen red is a
  decoration; both new gates in this phase have now been seen red.
- Criteria to close: the regression green in `ci.yml` against Compose, the
  read-only smoke green against deployed prod, the DB assertion proving a UI
  action reached RDS — and, per the standing invariant, a destroy that passes
  end-to-end at the end of this phase, not only at the end of the MVP.
- Cost when it runs: one `deploy-stage → promote-prod → destroy both` cycle.
  Nothing new is billable; the suites run inside the existing cycle.
- Expect one failed first run somewhere. This phase adds a genuinely new AWS
  path — an ECS task carrying an environment override — and every new path in
  this project so far has cost exactly one run to discover what it needed. CI
  passing on the first attempt does not buy that back: `ci.yml` touches no IAM
  policy, and both IAM gaps this project has had were reads that no amount of
  local green could have predicted.
  **This prediction was WRONG** (2026-07-26): the environment override needed no
  new IAM permission and deploy-stage was green on its first attempt. Recorded
  as wrong rather than deleted — the reasoning was sound and stays the default
  for the next new path.
- Findings of the closing session, none structural, all fixed in the same commit:
  - `aws sso login` requires `--use-device-code` on the headless devbox. That was
    documented in docs/preflight-inventory.md and NOWHERE else, while eight other
    files still printed the flagless form and were the ones actually copied from.
    Documenting a trap once does not remove it while the wrong command stays
    copyable — the promote-prod "read-only" comment in a different costume.
  - a post-teardown check whose SSO token has expired prints an EMPTY list for
    every resource, which is exactly what a clean account looks like. Any such
    check must start with `aws sts get-caller-identity` and assign results to
    variables under `set -e`. The teardown skill now does.
  - the `teardown` skill still expected the ECR repository to be gone after a
    destroy — false since ADR-0018, and it would have made a correct teardown
    look failed. It now lists all four permanent levels a destroy must not touch.
- Operational hazard found while demoing, worth more than it looks: prod appeared
  dead in the browser for ~30 minutes while serving 200s throughout. The macOS
  system resolver was holding a NEGATIVE cache entry for app.demo.uveapp.net,
  which is a dead name most of the time by design (ADR-0017 D2a). `dig` resolved
  and `curl` on the same machine did not, because only the latter uses the system
  resolver. Verify prod with a request that bypasses it, and flush the cache
  (`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`) before
  showing anything to anyone.
- The UI write path against PROD is covered by nothing automated, by design, and
  was exercised by hand once in this cycle. Say that out loud rather than letting
  the suites imply otherwise.

### Phase 11.1 — Public dashboard  [IN PROGRESS]
- Plan: `docs/next-phases.md` Phase 11 (M3). Decisions: **ADR-0026** (where the
  dashboard's two kinds of status come from), **ADR-0027** (the dashboard is a
  permanent state level, S3 behind CloudFront with OAC).
- Split into three steps so the billable one stands alone:
```text
  11.1a  decisions + scaffold, nothing applied      <- this session
  11.1b  local apply of infra/public-site, publish workflow, status.json
  11.1c  dashboard content, then a full cycle with the dashboard live
```

#### 11.1a — decisions and scaffold  [DONE 2026-07-26]
- Closes the debt Phase 11.0 left: **gitleaks over the FULL history, all refs**
  — 81 commits, no findings. The scan was then verified capable of failing, by
  running the same invocation against a throwaway repository containing a fake
  key: exit 1, finding named. A gate seen only green is indistinguishable from a
  gate that cannot fail; this one has now been seen both ways.
  `git rev-list --all --count` returned 81, matching what gitleaks reported it
  had scanned — the scan really did cover every ref, rather than only HEAD.
- ADR-0026 settles the open question the plan left dangling. Two sources, split
  by what each one can actually observe: the public GitHub Actions API for run
  history and per-stage status, `status.json` in the site bucket for the state of
  each environment in AWS. Actions cannot know an environment is destroyed;
  a file written at the end of a run cannot know a run is in progress. Each is
  the other's staleness detector, and the page renders "unknown" rather than a
  stale value when they disagree.
- ADR-0027 puts the dashboard in a new permanent level `infra/public-site`. This
  is the third instance of one rule — after ADR-0018 (registry) and ADR-0024
  (hosted zone) — and the sharpest: **the exhibit cannot be destroyed by the
  thing it exhibits.** A dashboard inside `infra/envs/*` would be deleted by the
  very teardown it exists to report.
- Scaffold written, NOT applied: private bucket, CloudFront + OAC, a second
  certificate in **us-east-1** (CloudFront accepts no other region, while the
  prod ALB accepts only its own — two certificates, two regions, one domain),
  apex and `www` alias records, and a narrow publish role trusting only
  `environment:stage` and `environment:prod`, scoped to this bucket and this
  distribution.
- `docs/security-posture.md` records, with the re-checking command beside each
  claim, why a public repository cannot be used to start a billable run: all
  three AWS workflows are dispatch-only and dispatch needs write access; there is
  no `pull_request_target` anywhere; `ci.yml` is the only workflow a stranger can
  start and it has no AWS path at all; and the OIDC `sub` is scoped to this
  repository plus a branch or environment, which a fork's token cannot match.
  Two residual items are named rather than buried: public Actions logs could
  surface `TF_VAR_budget_email`, and the fork-PR approval setting is UI state
  that git cannot assert.
- Criteria to close 11.1a: `terraform fmt -recursive -check infra` clean and
  `make tf-validate` green with the new level DISCOVERED — root levels must go
  from 6 to 7. Counting them is part of the check: a discovery that silently
  finds nothing is the e1e577a failure this project has already had once.
- **STATUS: CLOSED (2026-07-26).** Both criteria met on the devbox, first
  attempt: `terraform fmt -recursive -check infra` exited 0 with no output, and
  `make tf-validate` printed OK for **seven** root levels with `infra/public-site`
  among them — discovered by the `find` expression, not added to a list, which is
  the property that stops a new level from rotting unvalidated. Nothing was
  applied to AWS and nothing in this step is billable.
- The session predicted "budget for one correction round" on the HCL, because it
  was written without a local `terraform fmt` — terraform is not installed in the
  chat sandbox and could not be fetched there. **The prediction was wrong**: the
  hand-written alignment was clean on the first check. Recorded as wrong rather
  than deleted, exactly as Phase 10's identical miss was. The pre-check that
  substituted for `fmt` was a throwaway script reproducing the `=` alignment
  rule, itself verified by being made to fail on purpose and by running clean
  over two known-good directories. That is still a proxy, and the next author
  writing HCL without terraform to hand should assume the same budget.

#### 11.1b — apply and publish  [CLOSED 2026-07-26]
- First billable step of the phase. Local apply under `demo-admin`; CloudFront
  takes 10-15 minutes to propagate, once, not per cycle.
- **Closing criterion that must not be dropped: the `teardown` skill lists the
  levels a destroy must not touch, and there will then be FIVE, not four.** It is
  deliberately not edited in 11.1a, because a document here must not describe as
  existing in AWS something that only exists in git. **Done in this patch, after
  the apply**, together with the apply order in `docs/preflight-inventory.md` and
  the state-levels block in `docs/session-primer.md`.
- **APPLY: DONE (2026-07-26).** `terraform apply` of `infra/public-site` under
  `demo-admin`, green on the FIRST attempt: **16 added, 0 changed, 0 destroyed**,
  in about 4 minutes, of which the CloudFront distribution took 2m32s and the
  certificate validated in seconds. What exists now:
```text
  bucket        aws-devops-sdet-demo-site-993912191738   private, all four PAB flags true
  distribution  ED562RSB6XC49 / d1nj4thkcagijn.cloudfront.net   Deployed, OAC EURCBXCK61LAM
  certificate   us-east-1 ...00cb8629, ISSUED, InUseBy the distribution
  dns           demo.uveapp.net + www, A and AAAA aliases, resolved authoritatively
  publish role  aws-devops-sdet-demo-site-publish   this bucket + this distribution only
```
- Verified against the **AWS CLI and curl**, not against Terraform state, with
  `aws sts get-caller-identity` first and every result assigned under `set -e`
  inside a `bash -c` — the expired-token-reads-as-clean trap from Phase 10.
  All three URLs answered **403 with `ssl_verify_result=0`**: TLS valid, OAC
  refusing an object that does not exist yet. A 200 at that point would have been
  the suspicious result, because nothing had been uploaded.
- Two predictions this project keeps making were wrong again, and are recorded
  rather than deleted: a genuinely new AWS path did NOT cost one failed run, and
  the plan needed no correction. Both data sources (`aws_route53_zone`,
  `aws_iam_openid_connect_provider`) resolved at PLAN time, which is also the
  cheapest possible proof that `infra/dns` and `infra/bootstrap-oidc` are applied
  — had either been missing, the plan would have failed before anything billable
  was created.
- Side finding: `infra/public-site/.terraform.lock.hcl` was UNTRACKED, and its
  hash set was short one `h1:` entry compared with every other level — the
  `tf-validate` run in 11.1a had written it without ever installing the provider.
  The real `terraform init` completed it. Committed here, so the new level pins
  its provider like the other six.
- Written in this patch, NOT yet exercised: `site/index.html` (placeholder; the
  dashboard content is 11.1c), `scripts/observe-environment.sh`,
  `scripts/publish-status.sh`, `scripts/publish-site.sh`,
  `.github/workflows/publish-site.yml`, and the two-role publish steps appended
  to `deploy-stage`, `promote-prod` and `destroy`.
- Criteria to close 11.1b:
```text
  1. four repository variables exist (SITE_BUCKET, SITE_DISTRIBUTION_ID,
     SITE_PUBLISH_ROLE_ARN, SITE_URL) - see docs/preflight-inventory.md
  2. publish-site runs green and https://demo.uveapp.net/ returns 200, which is
     the workflow's own assertion and not something eyeballed in a browser
  3. `aws sts get-caller-identity` inside that run prints the PUBLISH role, not
     the deploy role - the scoping is the exhibit, so it is asserted
```
  The status-file steps in the three lifecycle workflows are deliberately NOT in
  this list: they can only be validated by a real cycle, which is 11.1c. Written
  now, proven then — and until then they are code that has never run, which this
  file says out loud rather than implying otherwise.
- **STATUS: CLOSED (2026-07-26).** All three criteria met, publish run green on
  the FIRST attempt: `publish-site` 30227614075, 18s, at 2026-07-27 00:31 UTC.
  The two assertions that matter were read out of the run's own log rather than
  claimed:
```text
  identity   arn:aws:sts::993912191738:assumed-role/
             aws-devops-sdet-demo-site-publish/GitHubActions
             — the PUBLISH role, not the deploy role. The scoping is the exhibit,
             so it is asserted inside the run.
  http       attempt 1: 200 — https://demo.uveapp.net/ over a verified TLS
             connection, asserted BY THE WORKFLOW. curl verifies the chain by
             default, so this is also the machine-checked half of "valid
             certificate on the apex".
```
- **The `--exclude` guard in `publish-site.sh` was proven in BOTH directions**,
  which is the habit this project keeps being repaid for. A canary was placed at
  `status/canary.json` and `reports/canary/index.html`, the workflow was re-run,
  and both survived. Then the counterfactual, free via `--dryrun`: the same sync
  WITHOUT the excludes printed two `(dryrun) delete:` lines for exactly those
  keys, and WITH them printed nothing. So "publish the site" would in fact have
  deleted every status file and every published report, and does not.
- Follow-on finding, fixed in the same session: **the `Owner` tag diverged.**
  `infra/public-site` was applied with `Owner=uve` while the other six levels
  carry `Owner=UVE`, because 11.1a wrote the lowercase form into
  `terraform.tfvars.example` and 11.1b copied it. A tag is what a cost or
  ownership query filters on, so one level spelling it differently drops that
  level out of every such query — invisible until someone trusts the query.
  Re-applied as **0 added, 4 changed, 0 destroyed** (the plan said 6; two policy
  documents were no-ops it could not prove in advance), and verified with
  `get-bucket-tagging`, `list-tags-for-resource` and `list-role-tags`.
  `docs/preflight-inventory.md` turned out to document a THIRD value —
  `papers.usher.3m@icloud.com`, which nothing had ever been tagged with. Now
  corrected to what the account actually shows.
- Cost now running: one 4 KB object, one PriceClass_100 distribution, a free
  certificate, six records in an existing zone. Inside the CloudFront free tier
  at portfolio traffic — a tier, not a guarantee, and the figure to watch is
  requests rather than storage.

## Confirmation protocol
Advance only on explicit confirmation: `continue`, `confirmed`, `done`,
`phase complete`, `go next`, `ок`, `дальше`, `подтверждаю`.
On error: fix the current phase only; do not advance.

## Context sync (ADR-0019)
There is nothing to sync by hand. `docs/discussion-log.md` and
`docs/project-prompt.md` are tracked files; the Claude Project holds only a
pointer, which carries no state and therefore cannot go stale.

A phase gate ends IN GIT: update the cursor above, write the session summary in
`docs/sessions/` with a row in `INDEX.md`, record new structural decisions as
ADRs, commit and push. Claude must NOT ask the user to upload anything anywhere.

The mirror was retired because it was measured: on 2026-07-25 it was five
commits stale and did not contain `docs/session-primer.md` at all.
