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
| 11.1  | Public dashboard               | ✅ done (11.1a, 11.1b, 11.1c) | f4fb868   |
| 12    | Minimum viable documentation   | ✅ done     | sessions/2026-07-27 |
| 13    | MVP verification gate          | ✅ done     | sessions/2026-07-28 |
| 14    | Release resilience             | ✅ done     | sessions/2026-07-28-phase-14-release-resilience.md |
| 15a   | Dependabot + secret gate       | ✅ done     | sessions/2026-07-28-phase-15a-supply-chain-gates.md |
| 15b   | Trivy + Checkov + action pins  | ✅ done     | sessions/2026-07-28-phase-15b-scanning-gates.md |
| 16a   | Contract depth + regression    | ✅ done     | sessions/2026-07-29-phase-16a-contract-depth.md |
| 16b   | Structured logs + 5xx alarm    | ✅ done     | sessions/2026-07-31-phase-16b-structured-logs-and-5xx-alarm.md |
| 18    | Remaining documentation        | ✅ done     | sessions/2026-08-02-phase-18-documentation.md |
| 19.0  | Self-service: decisions + plan | ✅ done     | sessions/2026-08-02-phase-19-0-decisions-and-plan.md |
| 19a   | Self-service scaffold          | ✅ done (nothing applied) | sessions/2026-08-02-phase-19a-scaffold.md |
| 19b   | Self-service applied + refusals | ✅ done (no cycle run) | sessions/2026-08-05-phase-19b-apply-and-refusals.md |
| 19c   | Live launch, TTL, both watchdog paths | ✅ closed by 19e | sessions/2026-08-05-phase-19c-live-launch-and-teardown.md |
| 19d   | The record, the lock, the state lock | ✅ witnessed live 2026-08-06 | sessions/2026-08-05-phase-19d-cancelled-run-recovery.md |
| 19e   | Break test; teardown claim narrowed | ✅ done | sessions/2026-08-06-phase-19e-break-test-and-teardown-gap.md |
| 19f   | Teardown gates that see the remainder | ✅ done | sessions/2026-08-07-phase-19f-teardown-sees-what-it-leaves.md |
| 19g   | Teardown that finishes on its own | ⬜ next (the ordering) | next-phases.md |

Phase 17 (prod data continuity) is still open and still optional, in
`docs/next-phases.md`. Phase 18 was pulled forward of both remaining phases
because it changes no infrastructure and both draw on it - 19 in particular
needs the FinOps talking points and the measured per-cycle cost it records.

Phase 19 is SPLIT into 19a (scaffold, $0), 19b (apply and prove the refusals
without a cycle) and 19c (one live launch, and the TTL proven by killing it).
19a and 19b are done. 19c RAN on 2026-08-05: the button was wired to the applied
endpoint, pressed anonymously from a browser, and a full cycle completed; the TTL
and BOTH watchdog paths were exercised against real environments. It is NOT
closed, because it found a state its guardrails cannot leave on their own - see
the 19c section below. The endpoint is parked again, by hand.
Its two decisions were made ahead of all three: **ADR-0034** for the trigger
path and **ADR-0035** for the guardrails; 19c is the first evidence about
whether they hold, and the answer is mostly yes with one structural gap.

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
- Validation (as run in Phase 4; superseded — see Phase 9.0. Kept for the record,
  with the current command beside it, because a stale copyable command is what
  gets copied):
```bash
  terraform fmt -recursive -check
  cd infra/envs/stage && terraform init -backend=false && terraform validate   # DO NOT USE
  make tf-validate                                                             # use this
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
    **Amended in Phase 15 (2026-07-28): TF_VAR_BUDGET_EMAIL is now an
    environment SECRET, in both `stage` and `prod`. Still no AWS credential of
    any kind — the one secret this repository has is an email address, moved
    there so Actions masks it in public logs.**
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
    (ships via COPY scripts ./scripts); the workflow runs it
    inside the image, where it lives at `/app/scripts/assert_seed.py`.
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
  aws ecr describe-repositories --profile demo-admin --region us-west-2   # app repo PRESENT
```
  That last line reversed its meaning and this block did not follow. Until
  **ADR-0018** the registry lived inside the stage state, so its absence proved
  the teardown had worked. Since ADR-0018 it is a permanent state level and
  `aws-devops-sdet-demo-app` is EXPECTED to survive every destroy - it holds the
  image prod may still be running. An empty result here is now a defect, not a
  pass. `destroy.yml` was corrected in the same ADR (it matches only
  environment-prefixed repositories); this file and `project-prompt.md` kept
  printing the old assertion, and they are what a human reads when checking an
  account by hand. Found in Phase 13 by doing exactly that.
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

#### 11.1c — dashboard content, then a live cycle  [CLOSED 2026-07-26]
- The content half of the phase, and the first time the status plumbing written
  in 11.1b runs at all. Everything below is code that has never executed against
  a real run: `observe-environment.sh` and `publish-status.sh` are invoked by
  `deploy-stage`, `promote-prod` and `destroy`, and no cycle has happened since
  they were added. This section says so rather than implying otherwise.
- `site/index.html` is now the dashboard: one file, no build step, no
  dependencies, no credential. It reads exactly the two sources ADR-0026 allows
  and nothing else.
```text
  environments   status/<env>.json from this bucket - ALB, ECS, RDS, image
                 digest, app URL, report URL, and the run that wrote it
  current cycle  the public Actions API: the newest lifecycle run, its jobs and
                 EVERY STEP with state and duration - what is done, what is
                 running, what has not started. That was the explicit request:
                 a viewer must see WHERE a cycle is, not only how it ended.
  history        the last twelve lifecycle runs, each labelled with the
                 environment it touched
  architecture   permanent levels vs per-cycle levels, in the order things
                 happen, because that split IS the design
```
- **The staleness detector is the point of the page, so it is scoped.** A source
  may only assert what it observes; the page therefore compares each
  environment's status file against the newest run THAT WRITES THAT FILE. `ci`
  and `publish-site` write none, so a documentation commit does not turn the
  panels amber. See the 11.1c implementation note in ADR-0026.
- One line of YAML was needed to make that possible: `destroy.yml` now sets
  `run-name: destroy ${{ inputs.environment }}`, because the anonymous API does
  not expose `workflow_dispatch` inputs and an unnamed destroy run is one that
  an outside reader cannot attribute to an environment. Without it the page's
  only honest option is to mark BOTH environments unknown — which it still does
  for runs that predate the change.
- Degradation is explicit everywhere, because an empty result is not a clean
  result: a rate-limited API renders a named banner and the time of the last
  successful read, never an empty history; an environment with no file renders
  "no observation", never "destroyed"; and while the API is unreadable a panel
  labels its own value **unverified** rather than implying it is current.
- Rate limit budget: 60 anonymous requests per hour per IP. A page load costs
  two, and the page polls only while a run is in flight, every three minutes —
  40 an hour at the worst. A dashboard that exhausts its own budget while nobody
  is watching would be reporting on nothing.
- Verified BEFORE any of it ran, in the chat sandbox, because the interesting
  states are the ones a live cycle will not show on demand: the render logic was
  driven by six fixtures through a stub DOM. `ci` after a destroy leaves both
  panels `destroyed`; a `deploy-stage` in flight turns stage `unknown` and names
  the run; a matching run id renders `up`; missing files render "no observation";
  a 403 renders the banner, an unavailable history and two `unverified` badges;
  an unnamed destroy marks both environments unknown. This is a proxy for the
  real thing and not a substitute for it — but it is how the failure paths get
  seen at all, since a green cycle exercises none of them.
- Criteria to close 11.1c:
```text
  1. publish-site green, https://demo.uveapp.net/ still 200
  2. a full cycle through Actions with no manual AWS operation:
     deploy-stage -> promote-prod (pausing for review) -> destroy prod ->
     destroy stage
  3. status/stage.json and status/prod.json exist in the bucket, each written by
     the run that observed it, and the dashboard renders stage `up` DURING the
     cycle and `destroyed` after it
  4. the per-stage panel shows a run in flight at least once - watched, not
     inferred afterwards from a finished run
  5. the published Playwright report opens from the dashboard without a GitHub
     account
```
- Cost: one ordinary cycle. Nothing new is billable; the dashboard level was
  already applied in 11.1b and the status writes are S3 puts and invalidations.
- Prediction, recorded so it can be wrong in writing like the last three: the
  status steps run under `if: always()` and have never executed, so the most
  likely failure is a missing IAM read or a shell assumption in
  `observe-environment.sh` against a HALF-torn-down environment — the `partial`
  branch is the one nothing has ever produced.

##### 11.1c — what the cycle actually showed

- **STATUS: CLOSED (2026-07-26).** All five criteria met, in one cycle, with no
  manual AWS operation anywhere in it:
```text
  publish-site  30229498666   8s     apex 200, asserted by the workflow
  deploy-stage  #21          16m05s  first attempt
  promote-prod  #4           14m17s  paused for a required reviewer, promoted the
                                     digest stage tested, no rebuild
  destroy prod  #12           8m39s  paused for a reviewer, then green
  destroy stage #13           8m31s  green
```
- The state plumbing written in 11.1b executed for the first time and worked on
  the first attempt in all four runs: `observe-environment.sh` under the deploy
  role, `publish-status.sh` under the publish role, both under `if: always()`.
- **The transition was WATCHED, not reconstructed.** stage went
  `no observation → up`, prod went `no observation → up → unknown → destroyed`,
  and the panel named the run responsible at each step. The `unknown` in the
  middle is the two sources disagreeing on purpose: `promote-prod` had reported
  `up`, a destroy was in flight, and nothing had observed AWS since — so the page
  refused to render either "up" or "destroyed" and said which run it was waiting
  for.
- Promotion by digest is now legible to a reader rather than asserted: stage
  showed `...app:70bb5d5...` and prod `...app@sha256:094e7838...` at the same
  time, on the same page.
- `run-name: destroy <environment>` proved itself in one screen: runs #12 and #13
  are attributed to `prod` and `stage`, while every destroy before them still
  reads `stage, prod` — the honest fallback for runs that predate the change.
- The published report opens from the dashboard with no GitHub account. Traces
  and screenshots are now recorded for PASSING tests too (this session), because
  the report is read by people for whom every run is a green one.

**Three defects were found by running it, none of them by review.** All three
were the same shape — a page saying something it was not in a position to say:

```text
1. an environment with no status file said "nothing has reported" and stopped,
   while a deploy was 16 minutes into doing exactly that. It now names the
   in-flight run.
2. the step list said "step detail could not be read" while promote-prod waited
   for its reviewer. GitHub returns a job with an EMPTY step list until the job
   starts; the page turned an absence into a failed read. It now distinguishes
   read-failed, queued, and held-at-the-approval-gate, and names the `waiting`
   status instead of flattening it into "running".
3. refresh was GitHub-only, every three minutes, which from outside is
   indistinguishable from a dead page. The two sources now run at the speed each
   one costs: the bucket every 30 s, GitHub paced by the rate-limit headers it
   returns.
```

- The prediction this file recorded was **WRONG**, which is now four in a row:
  the likeliest failure was supposed to be a missing IAM read or the untested
  `partial` branch of `observe-environment.sh`. Nothing on the AWS side failed at
  all. Every defect was in the browser, in the half that no fixture had covered
  because it needs a real run to exist. `partial` remains unproduced by anything:
  prod WAS partial mid-teardown, and the page could not show it, because only the
  workflow observes and it observes at the start and at the end.
- One trap caught in the act, in a command written IN THIS SESSION to check the
  security posture: `grep -rn 'pull_request_target' .github/ || echo none` was run
  from the wrong directory and printed `none` — grep exits 1 for "no matches" and
  2 for "could not look", and `||` cannot tell them apart. An error rendered as a
  clean result, in the same session that documents that exact failure mode twice.
  The corrected form prints the exit code so absence and failure are different
  things on screen.
- Asked for while approving `destroy prod #12` by hand: an approve button on the
  dashboard. Shipped as the honest half — a **Review deployment on GitHub →**
  link, shown while a run is `waiting`. A button that actually approves needs a
  token that can write to this repository, and this page is a static file in a
  public bucket: publishing it would hand write access to every visitor, and the
  approval would be recorded as whoever the token belongs to rather than as a
  person. The real version needs a browser sign-in and a backend, which is a
  phase with an ADR; the price is written down in `docs/next-phases.md` so the
  decision gets made on the price rather than on how small the button looks.
- Cost of the cycle: one ordinary deploy/promote/destroy. Nothing new is
  billable; after `destroy stage #13` the only things left are the five permanent
  levels, and each destroy verified that itself, scoped to its own environment.

### Phase 12 — Minimum viable documentation  [DONE 2026-07-27]
- Plan: `docs/next-phases.md` Phase 12 (M4). Decision: **ADR-0028**.
- Delivered:
```text
  README.md               the first this repository has ever had. `git log
                          --all -- README.md` was empty at the base commit;
                          Phase 8 deliberately left the stale one uncommitted
                          rather than publish something false.
  docs/architecture.md    the request path, the seven state levels split five
                          permanent to two per cycle, and the trade-offs made
                          on purpose - no NAT and what it costs in teardown
                          ordering, the ALB first, two certificates two regions.
  docs/demo-script.md     ten minutes with no waiting in them, because the
                          cycle starts forty minutes before the call.
  project-prompt.md       §7 and §10 rewritten from `git ls-files` and from
                          ADR-0015/0021; the file now says which of its
                          paragraphs are historical.
  tf-workflow skill       stopped teaching a validation command that reads
                          remote state.
  scripts/send.sh         control-layer tooling brought into git (ADR-0028),
  docs/transfer-buffer.md with the bare-name lookup bug fixed at last.
  make docs-check         a new gate, in ci.yml.
```
- **The diagrams are Mermaid and were PARSED, not eyeballed**, with mermaid's own
  parser in the session sandbox. The check was made to fail twice on purpose: on
  a malformed diagram, and on a file containing no diagram at all - because a
  documentation check that finds nothing to check is the e1e577a shape again.
- **`make docs-check` is new and was seen red six times before it shipped**: an
  unknown make target, a path that does not exist, an undeclared route, a
  misspelt workflow, a renamed entry in its own living-document list, and a make
  target inside a code span after the rule was narrowed to code spans. It checks
  six documents: the three written here plus this file, the primer and
  `transfer-buffer.md`.
- Running it is what found the things reading it would not have. Two false
  positives on the first runs - `app/app/<task-id>` is a CloudWatch log stream,
  not a directory, and "would make that possible" is English, not a make target -
  and one true one: this file named the assert-seed script by a path
  that exists only inside the image (`/app/scripts/assert_seed.py`) as though it
  were a directory in the repository. All three are fixed; the last had been
  sitting in the cursor since Phase 6, and the gate caught it again while this
  very paragraph was being written.
- The stale-command fix went to EVERY copyable occurrence in the same commit, not
  only to the skill: project-prompt §11.1 and §14, and the Phase 4 validation
  block above, which now prints the superseded command marked DO NOT USE beside
  the current one. `ci.yml` was checked rather than assumed - it runs
  `make tf-validate`.
- ADR-0028 closes a question the transfer buffer's own README had left open for
  an ADR rather than settling by reflex. The argument against was real - moving
  `send.sh` into git recreates the two-copies problem - and lost on rate of
  change: the primer goes stale within a single session, `send.sh` has changed
  once since it was written.
- **NO CYCLE WAS RUN IN THIS PHASE, and that is a deliberate exception to the
  standing invariant** that a destroy must pass end-to-end at the end of every
  phase. This phase changed no HCL, no workflow that touches AWS, and no
  application code; a cycle would have proven nothing it did not already prove on
  2026-07-26, at the cost of about 45 minutes and one billable deploy/destroy
  pair. Recorded here rather than left silent, because an invariant skipped
  quietly is indistinguishable from one forgotten. Phase 13 is a full
  empty-to-empty verification run and is the next thing due.
- Validation (all AWS-free). Written in the session sandbox, then RUN on the
  devbox and in CI, in that order, because the sandbox is a proxy for both:
```bash
  make docs-check                      # 6 documents, 0 findings   sandbox + devbox
  make tf-validate                     # 7 root levels OK          devbox
  node check.mjs docs/architecture.md  # 3 Mermaid blocks, 0 invalid   sandbox
  bash -n scripts/send.sh              # plus all three lookup cases exercised
```
- **CI observed, not assumed: `ci` #68 (30317752288) green on the first attempt,
  1m53s, at 683c655** — both jobs, including the new "The living documents
  describe things that exist" step in `terraform-checks`. A green
  `make docs-check` has exactly one meaning: the target exits 0 by no other path
  than all six living documents being present with zero findings. A missing one
  refuses out loud rather than passing quietly, which is the property that was
  tested by deleting one.
- `make tf-validate` was re-run on the devbox after this patch because the
  `Makefile` was edited; seven root levels, all OK. The edit added a target, and
  a target added next to a working one is exactly where a stray tab or a broken
  `.PHONY` line hides.
- Not read this session, therefore not claimed: `ci` #68 carries 2 annotation
  warnings. Earlier notes describe three Node 20 deprecation annotations on every
  run; whether these are those two, or two of those three, was not checked.
- Criteria to close: a reader who has never seen the project can run it and
  explain it from the repository alone. **MET** as far as this side can assert:
  every command in the three living documents is checked mechanically by
  `make docs-check`. What it cannot assert is comprehension - the first genuinely
  new reader is the test, and Phase 13 performs the run "as if by a stranger".
- Cost: **$0**. Nothing was applied and nothing was destroyed.
- The Commit column for this row names the session summary, not a hash. A commit
  cannot contain its own hash, which is why the 11.1 row said `(this patch)` for
  a day and had to be repaired here - a placeholder with nothing scheduled to
  replace it. A filename is stable, and because this file is now in the
  living set, `make docs-check` fails if that summary stops existing.

### Phase 13 — MVP verification gate
- Criteria: one uninterrupted run from an empty account to an empty account,
  performed as if by a stranger, with anything found fixed here. **MET.** All six
  steps of the `docs/next-phases.md` definition were exercised on 2026-07-28.
- **Observed, not inferred: `promote-prod` #5 held in `waiting` with an empty
  step list** until approved, and `pending_deployments` named the `prod`
  environment and its reviewer. The gate blocks at dispatch; nothing was applied
  before approval.
- **The digest was checked against the registry, not against the page that
  claims it.** `aws ecr describe-images --image-ids imageTag=a9a2709...` returned
  the same `sha256:0c27a15...` that the prod task definition carried. The
  dashboard asserts both halves and therefore cannot witness either.
- **Teardown was verified from the devbox, before and after, under
  `demo-admin`** — not from Terraform state and not from the destroy job's own
  check:
```bash
  aws sts get-caller-identity --profile demo-admin   # first, always
  aws elbv2 describe-load-balancers --profile demo-admin --region us-west-2 \
    --query 'LoadBalancers[].LoadBalancerName' --output text
  aws rds describe-db-instances --profile demo-admin --region us-west-2 \
    --query 'DBInstances[].DBInstanceIdentifier' --output text
  aws ecs list-clusters --profile demo-admin --region us-west-2 \
    --query 'clusterArns[]' --output text
  aws ec2 describe-nat-gateways --profile demo-admin --region us-west-2 \
    --filter Name=state,Values=available --query 'NatGateways[].NatGatewayId' --output text
  aws eks list-clusters --profile demo-admin --region us-west-2 --query 'clusters[]' --output text
```
  Run once with stage still up, it showed three stage resources and zero prod
  resources — which is what made the prod teardown a fact. Run again after
  `destroy stage`, all five were empty. An empty result is only evidence when a
  non-empty one was seen from the same command minutes earlier.
- Measured: `promote-prod` 14m08s, `destroy prod` 10m06s, `destroy stage`
  8m34s, appended alongside the 2026-07-26 figures in `docs/demo-script.md`
  rather than replacing them.
- **Found here and fixed here: `destroy` on prod also stops at the approval
  gate.** The rule sits on the environment, not the workflow, so a teardown is as
  gated as a deploy; `destroy` on stage does not pause. The demo script had told
  the presenter not to wait for it (da22d7c).
- **Found here, recorded, NOT fixed: the UP badge is a snapshot in the present
  tense.** stage read `UP` for 55 minutes after its last observation. The defect
  is one-directional — `DESTROYED` cannot go stale, because nothing raises an
  environment on its own — and the follow-up is in the session summary.
- Self-approval is permitted (the reviewer is the repository owner and the
  approval succeeded). Inferred from behaviour, not read from the GitHub UI, and
  written into the demo script as a thing to say rather than a thing to be caught
  by.
- Cost: one prod deploy/destroy pair and one stage destroy. prod was public for
  about 23 minutes. Everything billable is gone and the absence was verified
  against the AWS CLI.
- The Commit column names the session summary rather than a hash, for the reason
  given under Phase 12.

### Phase 14 — Release resilience
- Criteria: a failed prod release rolls back automatically, and a release is
  identified by something that cannot silently change. **MET**, with the phase's
  own premise corrected first (ADR-0029): "roll back to the previous task
  definition" is meaningless in an environment destroyed every cycle, because
  the previous revision is deregistered and cannot start tasks. The target is a
  digest pointer at a permanent level instead.
- **Rollback observed firing, not reasoned about.** `promote-prod` #7 promoted a
  knowingly broken image (container exits immediately); `services-stable` failed
  after 9m53s, the four steps between it and the rollback were skipped, prod was
  re-applied with the pointer's digest and the smoke was RE-RUN and passed. The
  run stayed red, which is the intent — rollback is damage control, not a pass.
- **Verified against ECS, not against the run that claims it**: after the
  rollback, `aws-devops-sdet-demo-prod-app:7` carried
  `@sha256:b9d47c3f...`, the digest the pointer named.
- **Both no-target refusals were exercised.** The empty-pointer branch fired
  live on `promote-prod` #6 and printed its message verbatim. The
  expired-digest branch was run on the devbox against the real registry using a
  digest that had genuinely just been deleted — and the same check answered
  `present` for a live digest in the same command, so it is not a check that
  only ever refuses.
- Found here and fixed here, neither visible on review:
```text
  the rollback trigger was too broad. "apply succeeded and something later
  failed" includes the release bookkeeping that runs AFTER a green smoke, so a
  failed git tag would have rolled back a prod that had just passed. #6 hit
  exactly that and was saved only by having nothing to roll back to.

  SSM refuses any parameter name beginning with "aws", and this project is
  called aws-devops-sdet-demo. The apply failed with AccessDeniedException
  "No access to reserved parameter name", which reads like an IAM problem.

  a runner has no committer identity, so `git tag -a` exits 128 with
  "empty ident name" - after the ECR half of the release was already published.
```
- Validation (AWS-free parts in the sandbox, the rest on the devbox):
```bash
  terraform fmt -recursive -check    # clean
  make tf-validate                   # 7 root levels OK
  make docs-check                    # 6 documents, 0 findings
```
- Teardown verified from the devbox under `demo-admin`, `sts` first and every
  result assigned under `&&`: alb, rds, ecs, nat and eks all empty — and they
  had all been non-empty twenty minutes earlier from the same commands.
- Timings measured: `deploy-stage` #23 16m05s, `promote-prod` #6 14m12s,
  `promote-prod` #7 (failed release + rollback) 15m00s, `destroy prod` #16
  10m22s, `destroy stage` #17 9m01s.
- The two `ci` annotation warnings, carried as unread since Phase 12, were read
  here: both are the Node.js 20 deprecation, for `actions/upload-artifact@v4`
  and `hashicorp/setup-terraform@v3`. Two, not three.
- Cost: one stage cycle and one prod cycle, prod up for about 2h40m across two
  promotions. Everything billable is gone and the absence was verified against
  the AWS CLI.

### Phase 15a — Dependabot and the secret gate
- Criteria: dependency updates are raised by a mechanism rather than by someone
  remembering to read a log, and the secret scan is a gate rather than a
  memory. **MET**, at $0 and with no AWS API call.
- **Dependabot raised the two known Node 20 deprecations AND four nobody had
  seen.** Annotations report a runtime deprecation, not staleness, so
  `actions/checkout`, `setup-python`, `setup-node` and
  `aws-actions/configure-aws-credentials` had aged silently — the last of them
  two majors behind, and it authenticates every AWS workflow in the project.
- **PR #3 is held, not merged.** It changes five workflows; `ci` runs one of
  them, and the other four are dispatch-only. A green check on that PR would be
  a statement about `ci.yml` alone. It merges immediately before the next full
  cycle, so `deploy-stage` exercises it on stage.
- **The break test did not break the gate, and that was the finding.** A planted
  AWS access key id scanned GREEN through a real commit. The chain was sound —
  120 commits scanned, the planted one among them — so four probes were run
  against the tool instead:

```bash
  gitleaks stdin -v --no-banner                        # the key alone: no leaks
  gitleaks dir break-test.txt -v --no-banner           # same, via a path
  gitleaks stdin --enable-rule aws-access-token        # the rule EXISTS, no leaks
  # the README's own sidekiq secret: FOUND, exit 1 — the scanner can fail
```
  In gitleaks 8.30 an AKIA identifier on its own is not a finding; the identifier
  plus a secret key is caught by `generic-api-key` on entropy, not by
  `aws-access-token`. The 11.1a instruction to "assert on the AWS rule
  specifically" cannot be carried out and is retired here.
- Re-run with the pair: RuleID `generic-api-key`, `File break-test.txt`,
  `Secret REDACTED`, exit 1. Red, and redacted — a gate must not publish the
  secret it just found in the logs of a public repository. The branch was never
  pushed.
- **Both refusals fired for real, and the non-refusal was checked too**: the
  missing-scanner refusal on the devbox, where gitleaks was not installed at all
  two days after it paid the Phase 11.0 debt; the shallow-clone refusal on a
  `--depth 1` clone; and a full clone with the scanner present did NOT refuse.
- Validation:
```bash
  make secret-scan     # 119 commits across every ref, no leaks
  make docs-check      # 6 documents, 0 findings
```
  On `ci` #80 the same job printed both counts — `make` before the scan and
  gitleaks after — and they agreed at 119. Read from the job-level API, because
  `gh run view --log` has printed nothing for a run with failures before.
- Cost: $0. Nothing was applied to AWS and no environment existed at any point.

### Phase 15b — Trivy, Checkov, and pinned actions
- Criteria: the infrastructure and the shipped image are scanned by a gate
  rather than by intention, every exception is a decision with a written
  reason, and the open question about tag-versus-SHA pinning is answered.
  **MET**, at $0 and with no AWS API call.
- **Checkov: 62 failures across 50 distinct checks on the first run.** Four
  were cheap, real and free, and were fixed rather than skipped: the ALB drops
  invalid header fields; the VPC default security group is declared with no
  rules; the CloudFront distribution carries the managed security-headers
  policy, resolved BY NAME so a wrong one fails at plan time instead of at
  apply with an unlookup-able GUID; and the dashboard bucket is versioned,
  because `status/` and `reports/` are written by the workflows and exist
  nowhere else. The other 46 are in `.checkov.yaml` with the reason beside each
  group, and the repository-wide blind spot is stated in the file itself.
- **Four of the 46 are the scanner, not the posture.** `infra/modules/alb`
  terminates TLS only when a certificate is passed; Checkov scans the module
  standalone, cannot evaluate the `dynamic` default_action, and reports the
  HTTP→HTTPS redirect as missing and the TLS floor as absent on a listener that
  has no TLS to configure. Half of that group is not a false positive: stage
  really does serve plain HTTP, deliberately (ADR-0017 D3).
- **Trivy went RED then GREEN in CI, on a real vulnerability.** `ci` #89 failed
  on three HIGH findings in `starlette`, fixed in 0.49.1, 1.1.0 and 1.3.1.
  Dependabot's PR #5 had independently proposed `fastapi 0.115.6 → 0.140.13`,
  which resolves `starlette 1.3.1` — checked by resolving it in a clean
  virtualenv rather than by reading a version range. Merging it produced
  `0 fixable, 23 with no fix available` on `ci` #91. The scanner and the bot
  reached the same fix from opposite directions.
- The deliberate red was chosen over the tidy order. Merging #5 first would
  have made the first-ever run of the `image-scan` job green, and a CI job that
  has only been seen green is indistinguishable from one that cannot fail.
- **A gate on a shared dependency reddens every open PR.** Once `image-scan`
  was on `main`, #1, #2, #3 and #4 all failed on the same three `starlette`
  findings, none of which they introduced. Until #5 landed, none of the four
  carried a readable signal.
- **The scan was pointed at the wrong image, and the refusal is what found
  it.** `docker compose config --images app` filters by service on the devbox
  and did NOT on the GitHub runner, which returned every service; `head -1`
  took `postgres:16`. It failed loudly only because postgres is not built in
  that job. In `local-ci`, where it IS pulled, the same logic would have
  scanned Postgres, printed a plausible verdict and gone green. Fixed at the
  root: the image name is a literal in the Compose file and in the Makefile,
  and the target refuses if the two have drifted.
- Actions pinned by commit SHA, 32 references (**ADR-0030**), SHAs resolved
  with `git ls-remote refs/tags/vX^{}` rather than copied from a page. PR #3
  closed as superseded. `make action-pins` keeps it from decaying.
- **Every new gate was broken on purpose, and the tools were proven able to
  fail first.** Checkov: a security group opening port 22 (three checks fired),
  plus all three refusals — scanner missing, config missing, zero checks
  evaluated. Trivy: all four verdict branches against fixtures before shipping,
  then the live red and green above. `action-pins`: an unpinned tag, a pin
  with its version comment removed, and the workflows directory moved away.
- **`checkov -d` on a directory with no Terraform exits 0** — verified, not
  assumed. That is the same empty-result shape gitleaks already has a refusal
  for, and it is why `summarise-checkov.py` refuses when nothing was evaluated.
- The devbox did not have Checkov installed, and the refusal said so before
  anything could pass. Same finding as gitleaks in 15a, two days later.
- Validation (both hosts, identical numbers):
```bash
  make iac-scan       # checkov 3.3.8, 46 skipped, 177 passed, 0 failed
  make image-scan     # 0 fixable, 23 with no fix available
  make action-pins    # 32 action references, all pinned
  make docs-check     # 6 documents, 0 findings
  terraform fmt -check -recursive infra && make tf-validate
```
- All five Dependabot pull requests are resolved rather than left open: #5
  merged as the Trivy fix, #3 closed as superseded by ADR-0030 (Dependabot
  closed it itself once the versions were in `main`), #1, #2 and #4 merged.
  `ci` is green on the result across all four jobs, and the Node 20
  deprecation annotations that Phase 14 read and 15a chased are gone.
- Cost: $0. Nothing was applied to AWS and no environment existed at any point.

### Phase 16a — Contract depth and the regression suite
- Criteria: the rest of the read/update surface exists with its negatives, the
  browser suite drives it, and the database assertion says something a 200
  cannot. **MET**, and closed with a full AWS cycle rather than at code
  complete.
- Contract decisions recorded BEFORE the code (**ADR-0031**): the envelope gains
  `total`/`limit`/`offset` while `count` keeps meaning "items in this response";
  the limit defaults to 20 and caps at 100; the order stays ascending, so the UI
  moves to the last page after a create instead of the API changing its order;
  PATCH is partial via `exclude_unset`, so absent and null are different
  requests.
- **The database assertion now proves an UPDATE.** A second probe is created
  under one name and RENAMED through the browser, and the check requires
  `updated_at > created_at` — which a row merely created under that name cannot
  satisfy, because both columns take the same `now()` on insert. On
  `deploy-stage` #25 it read: updated 0.226s after creation.
- **A break test that failed to break, and the finding was the suite.**
  `.offset(offset + 1)` in the list query passed all 50 contract tests. Every
  pagination assertion was about rows the test had just created — the newest,
  at the end of an ascending list — while an off-by-one drops the FIRST row.
  Both walks now count what they collected against the reported `total`; the
  same break then turns four tests red.
- **A test that skipped itself on its first run.** The last-page delete test
  checked whether the last page happened to hold one row. It now builds that
  arrangement and asserts it before exercising anything.
- **stage failed where localhost could not.** Two pagination tests timed out
  against the ALB, twice each including the retry, because `data-loaded` is a
  one-way flag: a spec that clicked Next and waited for it was answered by the
  render from before the click, then read a stale button state. The page now
  counts renders in `data-renders` and clears `data-loaded` at the top of
  `load()`.
- Measured: `deploy-stage` #24 17m59s (failed on the two timing tests), #25
  10m20s, `promote-prod` #8 14m26s, `destroy prod` #18 8m30s, `destroy stage`
  #19 8m44s.
- The Phase 15b debt is paid: `setup-terraform` v4 and
  `configure-aws-credentials` v6 ran in all four dispatch-only workflows for the
  first time and none of them failed.
- Validation:
```bash
  make test-api            # 50 passed
  make test-regression     # 12 passed + both probes asserted in the database
  make test-db             # DB assertion: all checks passed
  make test-spec-coverage  # 3 spec files, all resolved by a project
  make docs-check          # 6 documents, 0 findings
```
- Teardown verified from the devbox under `demo-admin`, `sts` first, every
  result assigned under `set -e`, and with a POSITIVE CONTROL in the same
  command: `alb`, `rds`, `ecs`, `nat` and `eks` all empty while
  `aws ecr describe-repositories` returned the shared registry. Phases 13 and 14
  ran this before and after; this session had only an after, so the control
  stands in for the non-empty reading.
- Cost: about $0.09 at list prices — stage up ~1h15m, prod ~23m.

### Phase 16b — Structured logs and the 5xx alarm
- Criteria: the application writes structured logs carrying a request id, a
  CloudWatch metric filter counts 5xx from those logs, and one alarm reads that
  metric. **MET**, and closed with a full cycle rather than at code complete.
- Structural decisions recorded BEFORE the code (**ADR-0032**): the signal comes
  from the application's own log rather than from the ALB's free
  `HTTPCode_Target_5XX_Count`, because the log line names the path and the
  request id and the metric is therefore the same artifact as the evidence; the
  environment is carried by the metric NAMESPACE rather than by a dimension,
  since a dimension value is a billable custom metric of its own; and the alarm
  is created with **no notification action**, because an SNS email subscription
  needs a confirmation click and a topic beside a per-cycle environment would
  ask for one every cycle. The channel has to outlive what it reports on — the
  fifth arrival at the ADR-0027 rule, and the first from something other than
  state.
- **Two break tests, both fired, both before delivery.** `status` serialised as
  a string turned the shape assertion red with the message that names the
  consequence — *"status serialised as str; the metric filter compares it
  numerically and would match nothing"*. Removing the logging call from the
  exception path — the naive middleware that logs only successful responses —
  turned the unhandled-exception test red with *"expected exactly one access
  line, got 0"*. Both were restored and the suite returned to 6 passed.
- **A defect no fixture had shown, found in the first real container.** uvicorn
  attaches `color_message` to its own startup lines via `extra=` — the same
  message again, wrapped in ANSI escapes for a terminal. The formatter promotes
  every `extra=` field to the top level, which is exactly how `status` becomes a
  comparable number, so `\u001b[36m` and a duplicate of each startup line were
  on their way to CloudWatch. A named drop-list fixes it; the new assertion was
  broken on purpose by removing that list.
- A new suite directory, `tests/unit/`, for the same reason ADR-0025 split the
  Playwright suites: where a spec lives decides what it can see. Both properties
  above are invisible to every HTTP client, so no existing suite could hold them.
- `make docs-check` refused the first draft of the README change with
  *"`tests/unit` is neither a tracked file nor a directory"* — the gate checks
  `git ls-files`, and the directory had not been added yet. Working as designed,
  and worth knowing before it appears in CI.
- The ECS task definition gained an `environment` block, which it had never had:
  every non-secret value until now was baked into the image. `APP_ENV` goes to
  **stage and prod in the same commit**, per the shared-invariant rule.
- Validated on the devbox before the cycle: `terraform fmt -check` clean on the
  first attempt (the HCL was aligned by hand — terraform cannot be installed in
  a chat sandbox, 403), `make tf-validate` OK on all seven levels, `make
  test-unit` 7 passed, `make test-api` 52 passed, `make iac-scan` 178 passed /
  0 failed, `make docs-check` 0 findings, and `ci.yml` green in all four jobs
  including the new in-process step.
- **The AWS half of the break test, joined to the local half by a literal.** The
  line the local fault actually produced — `/api/db-check` with PostgreSQL
  stopped, `"status":503` — was put into the stage log group with exactly one
  field changed, `env` from `local` to `stage`. Measured in this order, with the
  positive control taken BEFORE anything was injected:
```text
  sts get-caller-identity   993912191738
  alarm state               OK, "no datapoints were received ... treated as
                            [NonBreaching]" - CloudWatch stating decision 5 of
                            ADR-0032 in its own words
  { $.status >= 500 }       no events
  { $.status = 200 }        real stage lines, env "stage" - the same filter
                            grammar as the metric filter, against live traffic,
                            so the empty result above means something
  after injection           the metric read 1.0 at 20:08
  alarm history             OK -> ALARM 20:09:09, ALARM -> OK 20:10:09
```
- **Two findings, both a document disagreeing with a command.**
  `default_value = 0` on the metric transformation emits a zero for every
  NON-matching event, and the ALB health-checks the service every 30 seconds —
  so the metric existed and was billable from the first health check, while
  ADR-0032 claimed it does not exist until the first 5xx. Neither was found by
  review; a flat line of 0.0 datapoints minutes before any failure settled it.
  And the alarm held ALARM for exactly sixty seconds — with no notification
  action, the only surviving record was `describe-alarm-history`. A signal that
  has to be looked at in the right minute is not a signal.
- Both fixed in the same patch: the `default_value` removed, so the ADR's cost
  claim becomes true, and the alarm widened to 1 datapoint out of 5 periods.
- After the amendment: `deploy-stage` re-run applied it in 8m54s reusing the
  image, the metric read EMPTY for the five minutes before the second injection
  — proving `default_value` gone, while the ALB was health-checking throughout —
  and the alarm read ALARM at +2.5 minutes and still ALARM at +5.
- prod was exercised on purpose, not taken on trust: the change is in a SHARED
  module, and prod once kept a broken shape here for seven weeks because a
  shared fix was only ever run in stage. Its alarm reads `OK 5 1 notBreaching
  aws-devops-sdet-demo/prod`, its metric is empty, and its log group is live —
  the positive control that makes the empty metric mean something. No line was
  injected into prod; the signal was already proven and prod was publicly
  answering at the time.
- Measured: `deploy-stage` #26 17m59s→17m41s (RDS created), #27 8m54s,
  `promote-prod` #9 14m32s, `destroy prod` #20 9m47s, `destroy stage` #21 8m38s.
- Teardown verified from the devbox under `demo-admin`, `sts` first, every
  result under `set -e`, with a POSITIVE CONTROL in the same command: `alb`,
  `rds`, `ecs`, `nat`, `eks` and `alarms` all empty while `ecr` returned the
  shared registry.
- Cost: about $0.17 at list prices — stage up ~2h across two applies, prod ~40m.

### Phase 18 — Remaining documentation  [DONE 2026-08-02]
- Plan: `docs/next-phases.md` Phase 18. No ADR — pure documentation, no new
  structural decision, no invariant introduced.
- Delivered:
```text
  docs/cost-control.md              the permanent vs per-cycle split, real
                                    Terraform defaults, the two measured
                                    cycle costs already on record (16a
                                    $0.09, 16b $0.17), the budget alarm
                                    config, and the "always destroy" rule
  docs/interview-talking-points.md  DevOps / Cloud / QA-SDET / Security /
                                    FinOps, each point traced to an ADR or
                                    a session summary rather than to what
                                    the project was supposed to become
  docs/lightsail-devbox.md          the devbox's role versus the AWS
                                    deploy target, the SSH tunnel, both
                                    non-default login flags and why each
                                    is needed, session-open's place in it
```
- **None of the three joins the LIVING set** `scripts/check-docs-references.py`
  enforces (README.md, architecture, demo-script, phase-gates, session-primer,
  transfer-buffer) — that list is deliberately narrow, and widening it is a
  separate decision this phase did not make. Every `make <target>`, ADR number,
  and repository path the three documents cite was still checked by hand against
  this working copy before this patch, the same four kinds of claim
  `docs-check` verifies mechanically for the living set:
```bash
  grep -ohE 'ADR-[0-9]{4}' docs/cost-control.md docs/interview-talking-points.md \
    docs/lightsail-devbox.md | sort -u    # 12 references, all resolve under
                                          # docs/decisions/
  grep -ohE 'make [a-zA-Z0-9_.-]+' <same three files>   # 2 references
                                          # (session-open, tf-validate),
                                          # both real Makefile targets
  <every infra/, docs/, tests/, .github/ path cited>    # all exist
```
  Zero findings on all three kinds. `make docs-check` itself was also re-run
  unchanged, to confirm this phase did not regress the living set:
```bash
  make docs-check   # 6 documents, 0 findings
```
- **No cycle was run, same deliberate exception as Phase 12**: no HCL, no
  AWS-touching workflow and no application code changed. The cost figures in
  `docs/cost-control.md` are the ones already measured and recorded closing
  16a and 16b, cited rather than re-derived.
- Criteria to close (`docs/next-phases.md` Phase 18 has none written explicitly;
  applying the Phase 12 standard): the documents describe what is actually
  built, every command and path in them checked rather than assumed, and
  nothing in them describes a later phase as though it were done. **MET.**
- Cost: **$0**.

### Phase 19.0 — Self-service: decisions and plan  [DONE 2026-08-02]
- Plan: `docs/next-phases.md` Phase 19, which this session amended. Two ADRs,
  no code, nothing applied. Deliberately decisions-only: Phase 19 is the one
  phase where the expensive mistake is a design that cannot refuse.
- **ADR-0034 — the trigger path.** A Lambda Function URL and a GitHub App, at
  a new permanent state level. The button reverses this project's one direction
  of trust: everywhere else GitHub authenticates to AWS through OIDC, and here
  AWS has to authenticate to GitHub, where no OIDC exists. So the claim "no
  static keys anywhere" becomes "no static AWS keys anywhere, and exactly one
  static GitHub credential in Secrets Manager, readable by one Lambda role".
  Stated rather than discovered at interview.
- **The sixth arrival at the ADR-0027 rule.** The lock, the day counter and the
  kill switch are state ABOUT a cycle, so a control living inside the
  environment it controls is destroyed by the thing it is controlling.
  Registry, hosted zone, dashboard, release pointer, notification channel, and
  now a spend control.
- **The public path cannot reach prod, by IAM rather than by an input.** The
  launch workflow resolves the stage deploy role only and declares no prod
  environment, so no value of any input produces a prod credential.
- **The nonce is a speed bump and is labelled as one.** Whoever can read the
  page can get one; it is not authorization. The design goal is not "only the
  right people can press it" but "it does not matter who presses it", which is
  why the cost bound has to hold under an adversary.
- **ADR-0035 — five guardrails, five refusals, five break tests**, with real
  numbers rather than adjectives: TTL 90 minutes, three launches a day, worst
  case about $0.30/day against the $0.09 and $0.17 cycles already measured.
  The cap FAILS CLOSED - an unreadable counter is not zero launches today,
  the same sentence as the expired SSO token that printed nine empty lines.
- **One finding, and it amends the plan rather than implementing it.** The
  out-of-band watchdog was specified as a cron on the Lightsail devbox. A cron
  has no human, and the devbox reaches AWS through IAM Identity Center with a
  device code somebody types - so an unattended path from there means a static
  credential on disk, against the project's loudest invariant. The domain
  actually distrusted is GitHub Actions, not AWS, and a watchdog independent of
  Actions need not be independent of AWS - one that were could not act anyway.
  EventBridge Scheduler plus a Lambda buys the same independence at no
  credential. Recorded as ADR-0035 §5 and amended in `docs/next-phases.md`.
- Criteria to close: the two decisions recorded before anything is built, the
  plan split into fundable pieces, and the one place the plan contradicted an
  invariant found and corrected. **MET.** Nothing was applied; no AWS API was
  called this session.
- Cost: **$0**.

### Phase 19a — Self-service scaffold  [DONE 2026-08-02, nothing applied]
- Plan: `docs/next-phases.md` Phase 19a. No new ADR: **ADR-0034** and
  **ADR-0035** were recorded in 19.0, ahead of the code, which is the whole
  reason this phase had nothing to decide and only something to write.
- Delivered:
```text
  infra/self-service/          the sixth permanent level: control store,
                               launch Lambda + Function URL, watchdog Lambda +
                               EventBridge schedule, kill-switch Lambda + SNS
                               topic, the secret CONTAINER, and the narrow
                               callback role the workflow releases the lock with
  infra/self-service/src/      three handlers plus control.py, which imports no
                               AWS SDK at all
  .github/workflows/self-service.yml   launch -> destroy (if: always()) ->
                               release-lock (if: always()), stage only
  tests/unit/test_launch_refusals.py   21 assertions over every refusal
  make self-service-package    vendors PyJWT + cryptography, refuses on an
                               empty package
  the dashboard button         behind a flag, pointing at nothing
```
- **The public path cannot reach prod, and now cannot reach the OWNER's stage
  either.** The workflow declares no prod environment and resolves only the
  stage deploy role, per ADR-0034. The watchdog's blunt teardown adds a second
  guarantee in IAM: every delete is conditioned on `Project`, on
  `Environment=stage`, AND on a `Launch` tag that is present and non-empty.
- **The finding this phase produced, and it is a guardrail eating its owner.**
  ADR-0035 says a resource with a missing deadline is expired rather than
  exempt. Applied literally, that rule deletes the owner's own stage
  environment: an owner-run cycle carries no deadline, because no deadline is
  exactly what "a human is watching this one" looks like. The fix is the
  `Launch` tag - empty for an owner cycle, set by the launch workflow - and it
  goes to **stage and prod in the same commit**, per the shared-invariant rule,
  even though nothing public can reach prod.
- **The runtime has no crypto, which the plan did not say.** Minting a GitHub
  App installation token means signing an RS256 JWT, and the Lambda Python
  runtime ships boto3 and nothing else this needs. `make self-service-package`
  vendors PyJWT and cryptography for the runtime's platform, refuses when pip is
  missing or when nothing was vendored, and Terraform additionally refuses to
  apply a package under 500 KB - an empty zip deploys happily and fails at the
  first request, in a place nothing is watching.
- **Two corrections came from running the validation, and both were about a
  tool rather than about the code.** `terraform fmt -check` was red because a
  multi-line value ENDS the alignment group: `sid` before `actions = [` stands
  alone, and so does `Version` before `Statement = [{`. The approximate checker
  written in the sandbox measured that assumption instead of the tool — the same
  shape as a break test that fails to break. Twelve lines, whitespace only,
  `git diff --ignore-all-space` empty before it was committed. And Checkov found
  `CKV_AWS_297` (EventBridge Scheduler without a CMK), a tenth decision the skip
  list had not predicted from reading the resources.
- Criteria to close: written, validated statically, nothing applied. **MET**,
  on the devbox, since terraform, checkov and a Lambda-platform pip are not
  installable in a chat sandbox:
```text
  terraform fmt -check   clean, after the fix
  make tf-validate       eight root levels, infra/self-service OK first time
  make test-unit         28 passed
  make iac-scan          290 passed, 0 failed, 56 skipped by decision
  make docs-check        6 documents, 0 findings
  make action-pins       43 references, all SHAs
  ci.yml on push         green in all four jobs, run 30779260262
```
- Cost: **$0**. No AWS API was called for this phase.

### Phase 19b — Self-service applied, and the refusals proven  [DONE 2026-08-05]
- Plan: `docs/next-phases.md` Phase 19b. No new ADR; **ADR-0034** gained two
  amendments, both written beside the sentences they correct.
- Applied: `infra/self-service`, 25 resources, about **$0.45/month permanent**
  (the Secrets Manager secret is $0.40 of it). The GitHub App was created by
  hand, installed on one repository with `actions: read-write`, and its private
  key pasted into the secret by the owner - out-of-git state, now listed in
  `docs/preflight-inventory.md` beside the NS record and the protection rules.
- **Two defects found by applying, both green the day before.** The concurrency
  reservations cannot be applied while the account's Lambda `Concurrent
  executions` quota is 10, because a reservation may not take the unreserved
  pool below 10 - so they are `-1` and the account ceiling is the bound; no
  quota increase was requested. And a public function URL has required BOTH
  `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` since October 2025,
  while the provider creates only the first: every request, anonymous and signed
  alike, was refused `403` with the function never invoked. Fixed with provider
  `~> 6.0` on this level alone, which introduced zero drift.
- **A third came from using a guardrail rather than testing it.** Nothing in the
  repository turns the kill switch off - no `disengage`, no target, no line in
  any document - and its refusal names the budget alarm whichever way it was
  engaged. Recorded in `infra/self-service/README.md`; the message is 19c's.
- Criteria to close: every refusal this phase owns seen firing, with the output
  kept, and no environment created. **MET.**
```text
  not_configured     503   store proven readable: the kill switch is read first
  kill_switch        503   real Budgets message shape; refusal CHANGED, reason
                           stored verbatim, and it releases when the item is
                           deleted
  store_unavailable  503   both halves named the store: issue_nonce on the GET,
                           get_flag(killswitch) on the POST
  locked             409   named the holder AND its run_url; `gh run list`
                           showed nothing queued, with a positive control
  daily_cap          429   refused, AND the lock was released - two assertions
```
- Not provable without a cycle, and therefore 19c: the takeover of an EXPIRED
  lock, the TTL, and the watchdog's blunt path. `TF_VAR_budget_topic_arns` is
  now set on both environments - wired, and unverified until a deploy runs.
- The endpoint is left **parked**: the kill switch is engaged by hand, with a
  reason recorded that says it is not a budget event. 19c starts by clearing it.
- Cost: **$0** per cycle, no cycle run; about **$0.45/month** standing from now.

### Phase 19c — One live launch, the TTL, and both watchdog paths  [NOT CLOSED 2026-08-05]
- Plan: `docs/next-phases.md` 19c. No new ADR - the finding below needs a
  DECISION, and that decision is 19d.
- Wired first: 19b applied the level and left `site/index.html` at
  `enabled: false, endpoint: ""`. The button existed in AWS and nowhere a
  visitor could reach it. The panel hides itself while disabled, so nothing
  looked wrong.
- **Proven, each against something real:**
```text
  anonymous press -> dispatch    browser, no AWS credential in the path; the run
                                 is attributed to the GitHub App, not a human
  full cycle                     deploy 14m32s, destroy 8m31s, dashboard
                                 reported it and greyed its stale values
  TTL 90 minutes                 expires_at - acquired_at = 5400, from the lock
                                 the code wrote
  ExpiresAt / Launch tags        on the resources, so the deadline survives the
                                 loss of both the lock and Actions
  `locked`                       409 against a REAL lock, not a seeded one
  always() after cancellation    destroy AND release-lock both ran
  watchdog path 1                dispatched destroy.yml by itself, twice
  watchdog path 2 (blunt)        deleted a real ECS service, ALB and RDS, in
                                 that order, witnessed by the AWS CLI
```
- **Three defects fixed, each found by running:** two `access-control-allow-origin`
  headers on every reply, which only a browser could see (`make
  self-service-cors-check` now asserts exactly one, and fails on zero as loudly
  as on two - seen red on the real defect, then green); all three repository
  variables `release-lock` reads missing, so that job had never once worked; and
  the page pointing at an empty endpoint.
- **The finding that keeps this phase open.** A run cancelled mid-apply leaves an
  S3 state lock AND resources that never reached state. `destroy` then dies on the
  lock, `release-lock` releases anyway because it never asks how destroy went, and
  the watchdog's `dispatch_destroy` skips its own record when `lock is None` - so
  `dispatched_at` stays 0, the grace period never starts, and the blunt path
  cannot engage in the one case it exists for. Seen in the log: two
  `dispatched_destroy` five minutes apart with no `waiting_for_destroy` between.
  Recovery took `force-unlock` plus deleting three unmanaged orphans by hand;
  "re-run destroy", the recovery the watchdog documents, spent two full
  fifteen-minute timeouts failing.
- Criteria to close: that gap decided and fixed, and a cancelled run cleaned up
  by the system rather than by hand. **NOT MET.** Decided and fixed in 19d; the
  live half is what both phases now wait on.
- Account verified empty afterwards, positive control in the same command.
  Endpoint parked. 2 of 3 daily launches used.

### Phase 19d — The record, the lock and the state lock  [IN PROGRESS 2026-08-05]
- Plan: `docs/next-phases.md` 19d. **ADR-0036**, which amends ADR-0035
  guardrails 1 and 5 and is written against a STATE rather than a defect: three
  things that were each green in isolation combined into one from which the only
  exit was a human.
- Written, and not yet witnessed against AWS:
```text
  D1  the watchdog's record moves off the LOCK onto an item of its own, scoped
      by the launch ids it acted on and carrying a ttl. `note_on_lock` goes
      with it, and the decision moves to `infra/self-service/src/sweep.py`,
      which imports no AWS SDK and is driven branch by branch in tests/unit
  D2  `release-lock` reads `needs.destroy.result` and releases only on success.
      A destroy that failed means something is still alive, and the button has
      to stay shut
  D3  `scripts/break-stale-state-lock.sh`, a preflight in destroy.yml AND in
      the self-service destroy job, on stage and prod in the same commit. It
      breaks a lock whose holder is this job's own runner user when no other
      run is in progress, and refuses otherwise
```
- Batched with it, all four from 19c's "did not settle" list: the kill switch
  reports the `source` it was thrown with instead of always naming the budget
  alarm, and now refuses `GET` as well as `POST` — which is what
  `infra/self-service/README.md` always claimed; `run_url` is removed from the
  `locked` refusal, because the lock is taken before the dispatch and there is
  no moment at which the code knows a run URL; and the dashboard adopts
  `ttl_minutes` and `daily_cap` from the endpoint's reply rather than
  hardcoding them.
- **Four findings while writing it, three from running rather than reading:**
  the first version of the D1 assertion asserted `dispatched_destroy` where the
  code correctly answered `within_deadline` — the test modelled a cancelled run
  that was already past its deadline, which is not what a cancellation leaves,
  so it measured the author's assumption rather than the code; the preflight
  aborted with `GITHUB_REPOSITORY: unbound variable` under `set -u` when run
  outside Actions, which is the right exit code for the wrong reason and the
  message names a shell variable instead of the refusal; and its positive
  branch was first measured through a pipe into `tail`, which reported `exit=0`
  over a `terraform: command not found` — the same instrument error the primer
  has recorded since 2026-07-28.
- Criteria to close: a cancelled run cleaned up with nobody in the loop, and the
  account verified empty afterwards with a positive control in the same command.
  It is the same criterion 19c is still holding.

### Phase 19f — Teardown gates that see the remainder  [DONE 2026-08-07]
- Plan: `docs/next-phases.md` 19f = **ADR-0037** D2-D4. No new ADR; ADR-0037 D4
  gained an amendment, written beside the sentence it corrects.
- Shipped and confirmed on live evidence, in one cancelled launch
  (ss-b05240b2b90c10b7):
```text
  D2  scripts/revoke-cross-sg-rules.sh revoked 2 cross-group rules against REAL
      groups, and the destroy then deleted alb-sg without resistance. The same
      group in the same situation held destroy for 15m22s on 2026-08-06
  D3  Verify AND the new sweep both RAN on a job that had already failed, and
      said what was alive. On 2026-08-06 the identical situation produced a run
      that reported success while an ECS cluster survived
  D4  the sweep named 6 orphans at 00:57 and is green on an empty account
  IAM tag:GetResources applied to infra/bootstrap-oidc under demo-admin;
      confirmed against the ROLE with simulate-principal-policy, which answered
      implicitDeny for iam:CreateUser in the same call
```
- **The criterion is NOT met, and that is the finding.** The remainder still took
  three manual AWS calls. The gap is now exact, and it is an ORDERING: resources
  created by a cancelled apply never enter state, so Terraform can neither delete
  them nor delete what depends on them; the watchdog's blunt path clears the
  billable ones only AFTER the dispatched destroy has failed on exactly those
  resources; and nothing dispatches the destroy that would then succeed. Decided
  in 19g.
- **D3 is not safe as ADR-0037 wrote it.** The step was last, so it had only ever
  run with working credentials. `always()` lets it run after a FAILED credentials
  step, and every `aws` call then answers nothing - which is what an empty
  account looks like. destroy.yml's copy had neither `set -euo pipefail` nor an
  `sts` call. Applied literally, the decision would have turned a skipped step
  into a green one.
- **The tagging API is discovery, never a verdict**, and it was wrong in both
  directions within one hour: it did not report the RDS instance 40 seconds into
  the teardown because it was still `creating`, and it reported a security group
  one minute after a successful destroy that `describe-security-groups` answered
  `InvalidGroup.NotFound` for. The stale direction would have reddened every
  teardown from the first day - and a red destroy job keeps the launch lock
  (ADR-0036 D2), so the public button would have stayed shut until its TTL after
  every launch. Findings are now confirmed against the owning service, and
  `unconfirmed` is its own class because "I could not check" must not read as "it
  is gone".
- **An exclusion is not replaced by a mechanism that merely looks more general.**
  Task definitions were excluded by type, then the exclusion was removed on the
  theory that confirmation subsumed it. With no existence rule for the kind, 22
  deregistered revisions became `unconfirmed` and the gate went red on an empty
  account - the same failure from the other side.
- Cost: about **$0.02** of RDS for the 100 minutes between the cancellation and
  the blunt path, plus $0 for everything else. One of the day's three launches.
- Validation: tf-fmt clean, tf-validate 8 levels, test-unit 63, docs-check 0
  findings, iac-scan 290/0, action-pins 43, ci green on every push, and
  `destroy.yml` green end to end on the emptied account.

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
