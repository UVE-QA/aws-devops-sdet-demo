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
| 19g   | Teardown that finishes on its own | ✅ done, uninterrupted run 2026-08-08 | sessions/2026-08-08-phase-19g-nobody-in-the-loop.md |
| 20.0  | Visible cycle: decisions + plan | ✅ done | ADR-0039 |
| 20a   | The generated map, on the page | ✅ done | sessions/2026-08-08-phase-20a-the-map-on-the-page.md |
| 20b.1 | The stream captured, folded, gated | ✅ done, $0 | sessions/2026-08-08-phase-20b-1-a-killed-apply-is-not-a-cycle.md |
| 20b.2 | The timeline from a live cycle, on the page | ✅ done — the apply half was never lit; see below | sessions/2026-08-08-phase-20b-2-a-cancelled-run-erases-nothing.md |
| 20c   | The suites answer for themselves | ✅ done — the page reads both sources | sessions/2026-08-08-phase-20c-the-suites-answer-for-themselves.md + sessions/2026-08-08-phase-20c-a-node-answers-for-its-own-step.md |
| 20d   | Cost, computed from lifetimes  | ✅ done — the reconciliation clause retired, not deferred | sessions/2026-08-08-phase-20d-cost-is-a-lifetime.md |
| 20f   | The fold runs in the cycle     | ✅ done — no cycle ordered, $0 | sessions/2026-08-08-phase-20f-the-cost-fold-runs-in-the-cycle.md |
| 20e.0 | Dashboard discovery + sketch   | ✅ done — no code, $0 | sessions/2026-08-09-phase-20e-discovery-and-sketch.md |
| 20e.1 | Contrast floor gated; three blockers closed | ✅ done — palette moved, layout not started, $0 | sessions/2026-08-09-phase-20e-1-the-floor-is-met-before-the-layout.md |

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
the 19c section below. That state was closed by 19g on 2026-08-08.
Its two decisions were made ahead of all three: **ADR-0034** for the trigger
path and **ADR-0035** for the guardrails; 19c is the first evidence about
whether they hold, and the answer is mostly yes with one structural gap.

**The endpoint is LIVE, and that is the finished state of Phase 19** (decided
2026-08-08). Two sentences in this file and in `docs/discussion-log.md` said it
was parked behind a hand-thrown kill switch; the control store had no
`killswitch` item at all, and had not had one since 19g's launches cleared it on
2026-08-07. The finding is not the exposure - the guardrails standing behind
that button are the subject of this whole phase - it is that two documents
agreed with each other and neither agreed with the account. Turning it off again
is one `delete-item`, documented in `infra/self-service/README.md`.

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
  and nothing else. (**"No build step" stopped being true in 20a**, when the map
  arrived needing an inline icon sprite. The PUBLISHED page is still one file
  with no runtime dependency; the source is now `assets/index.template.html`.
  Noted here rather than edited away: this entry records what 11.1c delivered.)
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

### Phase 19g — Teardown that finishes on its own  [DONE 2026-08-08]
- Plan: `docs/next-phases.md` 19g. **ADR-0038**, which completes ADR-0037 and
  demotes ADR-0035 guardrail 5 - the blunt path stops being a step in the
  ordinary recovery from a cancellation and goes back to being the recovery for
  "Actions is the broken thing".
- The three candidate shapes were read against the code rather than compared as
  descriptions, and two of them cannot meet the criterion at all:
```text
  re-dispatch  the blunt path deletes what BILLS. The cluster and the security
               groups a cancelled apply leaves are free, so a re-dispatched
               destroy does not manage them either and the run ends red on the
               same three manual calls
  widen        deleting the rest in the right order is Terraform's job.
               Reimplementing a dependency graph in a Lambda is larger than the
               defect, and it costs the IAM narrowness that makes the blunt
               path safe to have
  import       the teardown fails because it does not OWN three resources. Let
               it adopt them and the FIRST destroy succeeds - the watchdog is
               never needed and state and AWS agree at the end
```
- The ordering dissolves rather than being patched: the watchdog already
  dispatches destroy once, and that dispatch has always been the retry. It was
  ineffective only because the destroy it dispatched could not adopt.
- Shipped: `scripts/adopt-orphans.sh`, `scripts/adopt_orphans.py`,
  `SWEEP_KEEP_DIR` and `--json` on the 19f sweep, and the step wired into
  `destroy.yml` (both environments) and the self-service destroy job. No new
  AWS permission: `terraform import` reads, and the deploy role already reads
  what it manages plus `tag:GetResources` since 19f.
- Break tests kept, all offline, exit codes measured to a file:
```text
  the map     count added to a mapped resource: RED, naming it
              a resource renamed inside a module: RED
              a module renamed in infra/envs/stage: RED
  the plan    a kind with no rule, a counted subnet (which says WHY, rather
              than "no rule"), a security group with no Name tag, a name from
              another environment, and two groups sharing one Name tag -
              which adopts NEITHER and names the address both claimed
  the script  two imports green; the same two with every import failing, which
              CONTINUES and exits 0 by design; an empty plan; an unknown
              environment; no argument
  the sweep   unchanged with and without SWEEP_KEEP_DIR - the two runs' output
              is identical and both exit 1 on the same planted orphan
```
- One finding while writing it, and it is the reason two of the map's tests
  exist: the first version of "no mapped resource is counted" read the ALB
  security group as indexed. It was matching `for_each` four spaces in, inside a
  `dynamic "ingress"` block, which is not a count on the resource - the test was
  measuring its own regex. The patch script used to make the edits had the same
  shape of defect: it computed every replacement from the original text and
  wrote them one after another, so a second edit to one file silently discarded
  the first, and it reported success twice.
- **Two cancelled launches, and three defects each found by the previous fix
  working.** Full record in the session summary.
```text
  L1 04:09  the adoption step DID NOT RUN: the patch was on the devbox and not
            on main, and the workflow comes from main. My sequencing error
     05:36  watchdog dispatched destroy by itself, 92 min after the launch.
            Adoption: 4 orphans, 4 adopted, 0 failed. Destroy still failed -
            the RDS instance was UNCONFIRMED, and adoption reads `orphans`
     07:30  after the parser fix, destroy green in 1m12s and ZERO UNCONFIRMED
            lines where the same situation had two
  L2 07:41  adoption adopted 4 of 4 INCLUDING module.rds.aws_db_instance.this.
            Destroy died on a null endpoint address - an instance three
            minutes old has none, and Terraform evaluates config during a
            destroy too
     07:54  after that fix, destroy green in 5m27s; the adopted instance was
            deleted as an ordinary managed resource
```
- **The defect underneath all of it.** `sweep-orphans.sh` read a resource's kind
  as everything up to the first SLASH, and AWS separates kind from name with a
  slash OR a colon - so `rds:db`, `rds:subgrp`, `logs:log-group` and
  `secretsmanager:secret` were four `case` arms that had never once been
  reached. It also corrects ADR-0037's diagnosis, which blamed the missed RDS
  instance on its `creating` status: it was never reportable at all. Invisible
  where it was tested, because none of those kinds is tagged once an environment
  is gone - including on a deliberate read-only run against the empty account
  ninety minutes before it fired.
- Criteria to close: a cancelled launch reclaimed with ZERO manual AWS calls and
  nobody in the loop, the account verified empty with a positive control in the
  same command. **MET on 2026-08-08**, on the first launch of the day and in one
  run:
```text
  00:42:55  ALB active, cluster up, three SGs up, RDS creating - the fullest
            orphan set any cancel here has produced
  00:44:15  cancelled (normal cancel; a force-cancel would take the
            `if: always()` destroy job with it, which is the thing under test)
  00:44:24  destroy starts by itself
  00:45:26  sweep before the teardown: verdict `orphans`, exit 1, five of them
  00:45:43  adopted 4 of 4; 0 could not be imported; the fifth named
            UNADOPTABLE (a listener, which leaves with its load balancer)
  00:49:01  final sweep: verdict `clean`, present 0, control 49
  00:49:09  destroy SUCCESS, 4m45s after the cancellation
  00:49:12  release-lock SUCCESS - it releases only on destroy=success
            (ADR-0036 D2), so it is a second, independent witness
  00:56:57  verified from OUTSIDE the run: stage destroyed, no ACTIVE cluster,
            no project-tagged security group, positive control non-empty
```
- The three defects of 2026-08-07 each met their own case for the first time in
  that one run: `rds:db` was REPORTED (the colon/slash parser), the instance was
  adopted at two minutes old and the destroy survived it (the null address), and
  the live sweep printed ZERO `unconfirmed` lines where the day before it printed
  two. The watchdog and the blunt path were not needed and did not fire.
- Shipped alongside: `scripts/watch-launch.sh`. The watch loop had been typed
  into a terminal on three separate days and broke the same two ways each time -
  started outside the repository, and killed by an SSH disconnect. Both are
  properties of where and how it was started, so they belong in the thing being
  started. No field it prints may be blank: a value, `none`, or `ERR`, and the
  account re-read every tick.
- Cost: about $0.03 - one launch, an ALB and an RDS instance for six minutes.
  The 2026-08-07 pair cost about $0.10.

### Phase 20.0 — The cycle visible without a log: decisions and plan  [DONE 2026-08-08]
- Criteria: the shape of the visible-cycle work decided and recorded as an ADR
  before any of it is written, and the plan in `docs/next-phases.md`. **MET** -
  **ADR-0039** (four decisions) and the Phase 20 section with 20a-20d.
- The phase exists because the dashboard reports STATE and not what the project
  DOES. Its one section that tries is hand-written prose, and that prose was
  telling every visitor there were five permanent state levels while standing on
  the sixth.
- Found before any of it was planned, and fixed in its own commit: FIVE
  reader-facing places described the applied, live, publicly-pressed
  `infra/self-service` as written-and-never-applied - README, architecture,
  cost-control, interview-talking-points, and the dashboard itself. A sixth,
  `docs/architecture.md`'s "seven state levels" heading, was correct while there
  were five permanent levels and never revisited.
- **No gate could have caught any of it.** `make docs-check` verifies that every
  path, target, route and workflow a document NAMES exists; nothing checks that
  what a document CLAIMS is true. This is the third arrival of the species in
  three days and the largest: 19g found two documents disagreeing with the
  control store, this found five disagreeing with the account, in the files an
  outside reader actually opens.
- The structural answer is not a bigger linter. ADR-0039 D1 GENERATES the
  architecture section from `infra/`, so the class of defect ends rather than
  being policed - and the prose is allowed to survive only as a second rendering
  of the same generated file.
- Also corrected: `docs/cost-control.md` said "none of this is running" and
  carried no measured figures. It now carries 19f's $0.02, 19g's $0.03 and the
  $0.10 pair, and records that **19c closed without a cost figure at all** - a
  gap in the record rather than a zero, and one that 20d is meant to stop
  recurring.
- **D5 arrived after the other four and changed D1's gate.** The requirement is
  one desktop screen without scrolling, and legibility is allowed to beat
  fidelity. Taken naively that contradicts a picture generated so it cannot lie;
  it does not, once the line is drawn between the DATA (exact, generated) and the
  DRAWING (grouping, layout, non-linear duration - editorial and labelled). The
  gate therefore checks COVERAGE rather than depiction: every resource in
  `infra/` is assigned to exactly one display group, including "deliberately not
  shown". That is the spec-coverage guard's shape, which this repository already
  runs over the Playwright suites.
- Validation:
```bash
  make docs-check
  grep -rn "NOT APPLIED\|never been applied\|NOT BUILT" README.md docs/*.md site/index.html
```
  The grep must return only Phase 20's own "planned, not built" line in
  `docs/interview-talking-points.md`, which is true.
- **A SECOND SWEEP, after `session-close` printed clean, found SIX more** - and
  not one of them a phrase. They were counts: `docs/architecture.md` saying
  "Three levels are permanent for that one reason" above a list of four,
  `docs/demo-script.md` with "Seven root levels: five permanent" and
  "twenty-seven ADRs" against thirty-nine, `.claude/skills/tf-workflow/SKILL.md`
  with "the seven root levels" and a list missing `infra/self-service`, and -
  the expensive one - `docs/session-primer.md` listing seven levels, the file
  every new session reads first, missing the sixth permanent level since 19b.
- The first sweep missed all six because it grepped for the wording it had
  already found (`NOT APPLIED`, `never been applied`, `NOT BUILT`). A COUNT goes
  stale without a word changing around it and reads as precision while it does.
  The search was shaped by what it had already caught.
- Also recorded, because it was reported wrongly in this session: the Mac copy
  of the primer was IN SYNC with the repository and the repository was WRONG.
  Synchronised and correct are separate questions.
- Consequence taken rather than noted: ADR-0039 D1 now requires `topology.json`
  to carry the counts, with prose rendering them instead of spelling them out.
- Cost: **$0**. Nothing was applied to AWS and no environment existed at any
  point.
- Next allowed step: 20a. It applies nothing and costs nothing.

### Phase 20a — The generated map  [PART DONE 2026-08-08: layout settled]
- Criteria for the whole sub-phase: `site/data/topology.json` generated from
  `infra/` and `tests/`; counts carried in the same file; the layout; a
  `site-data-check` target in CI with its two break tests; the hand-written
  section in `site/index.html` replaced. **PARTLY MET** — the LAYOUT half only.
- What is done: the layout, decided by looking at it rather than by reasoning
  about it. A standalone pilot page, built by its own target from a hand-built
  `site/data/topology.json`, rendered at 1440 / 1180 / 834 / 390. What it
  settled, and what it left open on purpose, is in `docs/next-phases.md` under
  20a. **RETIRED when the map reached `site/index.html` on the same day** — the
  page, its template and its target are gone, and this paragraph no longer names
  them because `make docs-check` reads a name in a living document as a claim
  that the thing exists.
- The finding worth carrying: folding the chain node by node drew a SEQUENCE
  inside an apply, where Terraform has a graph. Sequence now belongs to the
  phase; the nodes inside one are a set with no arrows. ADR-0026's rule reaches
  pictures too.
- Icons: ADR-0039 asked 20a to establish AWS's terms rather than guess. Done —
  and the answer is that AWS's three relevant pages neither permit nor exclude a
  public web page. The position taken, with the terms quoted, is in
  `assets/aws-icons/NOTICE.md`; the ADR's Consequences carry the same answer.
- NOT done, and not claimed: the generator, the `site-data-check` target and its
  two break tests, and folding the map into `site/index.html`. The pilot deliberately
  did not touch `index.html`, and `topology.json` is a fixture that says so in
  its first field.
- Two refusals of the sprite builder were exercised on purpose, both red: a
  missing icon file, and a template that has lost its injection marker.
- Cost: **$0**. Nothing applied to AWS, no environment at any point. The pilot
  page WAS published — `publish-site` fires on any push to `site/**` — and
  carried fixture numbers labelled as fixture numbers on the page and in the
  file. It was removed from the bucket by the same mechanism when 20a closed:
  `publish-site.sh` syncs with `--delete`.
- Validation (as it stood; the targets it named are retired):
```bash
  make docs-check
  git diff --stat
```
- Next allowed step: finish 20a — the generator and its drift gate.

### Phase 20a (continued) — The generator, and the gate  [DONE 2026-08-08]
- Criteria for this half: `site/data/topology.json` GENERATED from `infra/` and
  `tests/`, the counts carried in the same file, `make site-data-check` wired
  into `ci.yml`, and its break tests. **MET.** The remaining half —
  `site/index.html` — was deliberately left out of this session for a smaller
  surface and one publish instead of two, and 20a stays open on it.
- **The generator refused on its first run against unmodified `infra/`, and was
  right.** Nine resource blocks carry `count` or `for_each`; the fixture counted
  each as one, so "116 resources" was never the number of things AWS creates.
  The unit changed rather than the guess: every count now says resource BLOCKS,
  each of the nine is acknowledged by name with its reason, and a tenth appearing
  without an entry is red. They split three ways: four `for_each`, two
  `count 0 or 1`, and three `count = 2` the fixture drew as one each.
- **The same check then measured its own regex**, exactly as Phase 19g's did that
  morning: `for_each` four spaces inside a `dynamic "ingress"` block reported the
  ALB security group and the HTTP listener as repeated. Anchoring on indentation
  is a claim about formatting; the question is about depth. Replaced with a brace
  walk. Reading a documented trap does not make you avoid it.
- What is derived and what is not, stated so it cannot spread:
```text
  derived    levels, module instantiations, every resource block and its level,
             spec files per suite, workflows, ADRs, every count on the page
  editorial  assets/topology-groups.json - grouping and phase arrangement only.
             It holds no number and says so in its first field
  absent     duration, cost, identifier, result. A cycle says those. 20b and
             20c fill them, and until then the map renders unobserved
```
- Five break tests, all red, exit codes written to a FILE, tree committed first.
  Evidence: `docs/sessions/2026-08-08-phase-20a-break-tests.log`.
```text
  1  a resource block added to a module and assigned to nothing
  2  the generated file deleted
  3  a count edited by hand in the committed file - "adrs": 40 -> 27, which is
     the number docs/demo-script.md was carrying earlier the same day
  4  an assigned resource deleted from a module - a stale assignment
  5  a node removed from a phase while its module is still instantiated
```
  A sixth path is green AND RECORDED rather than red: the group meaning
  deliberately not shown. It holds `aws_default_security_group`, which creates
  nothing - the module's own comment says AWS makes it with the VPC and Terraform
  adopts it. Break test 5 is what proves that skip is not blanket.
- **The map printed `undefineds`, and only a screenshot said so.** The CSS class
  defaulted a missing `state` to absent; the body branched on the raw field, so
  every node in a generated file took the measured branch. Nothing in the JSON was
  wrong and no check here would have spoken. Rendered through Playwright at real
  viewports 1440/1180/834/390: `scrollWidth == clientWidth` at all four.
- Cost: **$0**. Nothing applied, no AWS API called.
- Validation:
```bash
  make site-data-check
  make site-page && make docs-check
  git diff --stat
```
- **Added on review, same session:** the band the map was missing, and the cut.
```text
  outside   the Lightsail devbox and GitHub - repo + Actions. Neither is in
            infra/, which is why neither had appeared, and neither is a phase:
            nothing creates or destroys them. A band ABOVE the cycle. The
            GitHub card's claim about the trust path is TIED to a resource -
            `backed_by` names aws_iam_openid_connect_provider.github and the
            gate is red if it is not declared
  icons     Lightsail's official icon WAS added, from the same package release
            and the same `48` set as the others, so it shares their viewBox.
            GitHub keeps a glyph: its brand page NAMES this case and permits it
            (assets/github-logo/NOTICE.md) - a different kind of answer from
            AWS's, which neither permits nor excludes a public page - but the
            mark may not be redrawn, so the asset has to be downloaded
  counts    adding one icon made four written numbers false at once: "seventeen"
            in two comments and in a plan, and "~48 KB" for the sprite. All four
            replaced by measurement or by no number. One of them was in
            assets/aws-icons/NOTICE.md, the file that exists to explain why the
            icons are safe to use
  cut       the front page's prose, GENERATED from topology.json rather than
            kept (ADR-0039 D1). The generator now emits `members` - the exact
            terraform address behind every node - so the cut names all 116
            blocks the map folds into 26 marks. Only judgements and links stay
            hand-written
```
- Three measurements, and the third dates a defect to BEFORE this session:
```text
  phone, cut OPEN   a terraform address is one unbroken token; `dt` and `dd`
                    carried them and pushed the page 103px past a 390 viewport.
                    With the cut SHUT it fitted and said nothing
  scrollbar         opening the cut made the page taller, the scrollbar
                    appeared, the viewport narrowed, and the map had been laid
                    out against the wider one. scrollbar-gutter: stable, plus a
                    re-render on toggle
  .node .head       up to 22px wider than its own node, at every width, with
                    the cut shut, and on the PRE-PATCH build measured by
                    stashing this one
```
  The pilot's `scrollWidth == clientWidth` was true of the DOCUMENT. The head
  spills into the node's own padding, which no screenshot and no document-level
  measure can see. NOT fixed here: `.node .head` is layout, and layout in this
  project is decided by looking.
- Next allowed step: the last piece of 20a — fold the map and its cut into
  `site/index.html` in place of the hand-written section. Then 20b.

### Phase 20a (closed) — The map on the page  [DONE 2026-08-08]
- Criteria for this last half: the hand-written "What happens, in the order it
  happens" section in `site/index.html` replaced by the map and its cut, both
  rendering the generated `site/data/topology.json`. **MET.** 20a is closed.
- **The page became a BUILD OUTPUT, which was not in the plan.** The map needs
  the icon sprite inline, so `site/index.html` is now built from
  `assets/index.template.html` by `make site-page`. That buys a new way to be
  wrong - a committed output invites being edited in place, and the edit
  survives only until the next build silently reverts it - so `make
  site-page-check` requires the committed page to be byte-identical to a fresh
  build, and runs in `ci.yml`. The template lives outside `site/` because
  `publish-site` syncs the whole directory to the public bucket and a template
  served without its sprite renders a map with no icons.
- **The pilot is retired**, page and template and target. `publish-site.sh`
  syncs with `--delete`, so the published copy went with the commit. Two
  renderings of one file, maintained separately, is the defect this phase
  exists to remove; keeping the pilot would have been an instance of it.
- **Two layout defects, both invisible to the pilot's own check.**
```text
  packer     a row renders phase | gap | arrow | gap | phase, and the greedy
             packer charged itself ONE gap per join. At 1180 the first row came
             out 7px wider than the box it was packed into. The pilot measured
             the DOCUMENT, and a child overflowing its own parent never reaches
             it; found by measuring each ROW against its own container
  .node .head  up to 22px wider than its node, carried forward from the
             generator session, which recorded it and left it because layout
             here is decided by looking. Fixed with a two-row grid in the head:
             icon and name on one line, the environment tag beneath
```
- The head took three attempts, and the two failures are the interesting part:
  `overflow-wrap: anywhere` stopped the overflow and produced "Applicati on Load
  Balancer"; `flex-wrap: wrap` stopped the mid-word breaks and put the icon on a
  line of its own, away from the name it belongs to. The tag was what was
  stealing the width - it is redundant with the phase header, which already says
  `stage` or `prod`, and it is kept because 20c gives suites an identity of
  suite x environment.
- Six ways to make the gate red, five red and both controls green, exit codes
  written to a FILE, tree committed first. Evidence:
  `docs/sessions/2026-08-08-phase-20a-page-break-tests.log`.
```text
  1  the built page edited by hand
  2  the built page deleted
  3  the TEMPLATE edited and the page not rebuilt - the drift the gate is for
  4  the template loses its injection marker
  5  an icon the page asks for is missing
  0/6  controls: the untouched tree, before and after
```
- Also corrected on the way past, and all three are the same species this phase
  keeps finding: the sprite builder's docstring said "17 objects" over a list of
  EIGHTEEN; it printed a character count while calling it bytes (118,577 against
  118,667 on disk, which is what em dashes cost); and three documents said
  `site/index.html` has no build step, which stopped being true in this commit.
- Cost: **$0**. Nothing applied, no AWS API called. The page publishes on push.
- Validation:
```bash
  make site-page-check
  make site-data-check
  make docs-check
  git diff --stat
```
- Next allowed step: **20b** — the timeline from Terraform's own `-json` event
  stream. It needs one cycle, about $0.03.

### Phase 20b.1 (closed) — The stream captured, folded, gated  [DONE 2026-08-08]
- Criteria: every terraform apply and destroy in the four AWS workflows emits
  `-json` and has its stream captured; a script folds the streams into one
  timeline per environment per job AND back into a legible log; the fold is
  gated against fixtures that are real terraform output; nothing is applied and
  no AWS API is called. **MET.**
- Split from 20b deliberately, on the shape 19 used: 20b.1 is $0 and writes
  everything, 20b.2 spends one cycle proving it against terraform and AWS. The
  fold's correctness is decidable without a cycle; whether the workflows publish
  what the page can draw is not.
```text
  scripts/tf-stream.sh       runs terraform with -json, captures the stream
  scripts/fold-timeline.py   folds the streams into a timeline AND a readable log
  scripts/check-timeline.py  the gate
  make timeline-check        it, in ci.yml
  tests/fixtures/timeline/   six cases, every one a real terraform run
```
- **The readable log is half the deliverable, not a nicety.** `-json` replaces
  terraform's human-readable output in the Actions UI, so the fold prints a
  per-resource table and every diagnostic in full — errors OUTSIDE the collapsed
  group, because a collapsed error is a lost error.
- **Three signals decide whether a timeline is complete, and the weakest wins**:
  the `.rc` file written after terraform returns (missing means it never
  returned), the exit code, and the terminal `change_summary` whose operation is
  `apply` or `destroy`. The `.cmd` file exists because an apply that dies before
  finishing emits a `change_summary` saying `plan`, so a fold reading only the
  stream would label a half-finished apply a plan.
- Two things the plan did not have, both found by writing it:
```text
  key       run id PLUS JOB. self-service launches an environment and destroys
            it again inside ONE run, in two jobs; a key of run id alone would
            have the teardown's timeline overwrite the launch's, leaving one
            object that looks like a complete record and is half of one
  --exclude publish-site.sh syncs site/ with --delete and would have removed
            every published timeline at the next push to main, silently: the map
            would keep working from the one published minutes earlier
```
- Seven ways to make the gate red, seven red and both controls green, exit codes
  taken directly rather than through a pipe, tree committed first. Evidence:
  `docs/sessions/2026-08-08-phase-20b-1-timeline-break-tests.log`.
```text
  1  a plausible exit code 0 planted beside the KILLED stream
  2  the terminal change_summary deleted from a complete stream
  3  one line of a stream corrupted mid-write
  4  the fold's missing-.rc rule removed
  5  a resource that only ever STARTED counted as complete
  6  the fixture directory emptied - it refuses rather than passing 0/0
  7  the readable log stops printing error diagnostics
  0/7  controls: the untouched tree, before and after
```
- **The fixtures are real terraform runs, and `apply-killed` was really killed.**
  Generated by `tests/fixtures/timeline/generate.sh`, offline and free, using the
  built-in `terraform_data`.
- **The OpenTofu caveat is discharged.** They were authored against OpenTofu
  1.10.6 - the only binary the chat session could reach - and regenerated on the
  devbox with **terraform 1.15.8**. All six expectations held with no edit, and
  the event counts are identical: 16, 15, 14, 10, 13, 13. The decisive evidence
  is not the counts, which could mean nothing was regenerated, but the streams
  themselves: `"terraform":"1.15.8"`, `@module: terraform.ui`, `ui: 1.3` where the
  fork wrote `tofu` and `ui: 1.2`. The fold was written against the schema and not
  against a fork's quirk, and it survived a gap larger than any version bump.
- Recorded rather than fixed: **the devbox runs 1.15.8 and the workflows pin
  1.15.5.** Changing what CI runs deserves its own reason and its own session;
  `tests/fixtures/timeline/cases/GENERATED-BY` carries whichever binary produced
  the fixtures, so the question can never be answered from memory.
- Cost: **$0**. Nothing applied, no AWS API called.
- Validation, all of it run on the devbox on 2026-08-08:
```bash
  tests/fixtures/timeline/generate.sh   # terraform 1.15.8, 6/6 unchanged
  make timeline-check
  make docs-check
  git diff --stat
```
- Next allowed step: **20b.2** — one cycle. Publish a timeline from a real apply
  and a real destroy, find out what a module does to a resource address, light
  the map's nodes from it, and break it the way fixtures cannot: a cancelled RUN
  must publish INCOMPLETE. About $0.03.

### Phase 20b.2 — the timeline from a live cycle, on the page  ✅ DONE 2026-08-08
- Criteria: the map's nodes carry the figures a real cycle measured; a run that
  did not finish is SAID rather than silently drawn; every resource a cycle
  touches lands on a node, is recorded as deliberately not drawn, or is named.
  **The $0 half is done, gated and broken on purpose. The cycle has not run.**
- Split the way 20b.1 was and for the same reason: everything decidable without
  AWS is settled first, at nothing, and the billable run is spent only on what
  only AWS can answer.
```text
  scripts/node-states.py        the join: a timeline onto the map's nodes
  scripts/check-node-states.py  the gate
  make node-states-check        it, in ci.yml
  tests/fixtures/node-states/   4 cases folded from real terraform runs, 1
                                hand-written and saying so, 1 stub topology
  tests/fixtures/timeline/cases/apply-module   resources inside modules
  assets/index.template.html    the run layer: at-rest figures, the unfinished
                                run, the live pulse
```
- **ADR-0040**, two decisions found by writing the CONSUMER of 20b.1's timeline
  rather than by planning it. `latest.json` cannot be the at-rest source: it is
  overwritten by a cancelled run, so one cancelled run would erase a good
  measurement. And the join belongs on the runner in Python rather than on the
  page in JavaScript, because the gate over it is Python and the pair would be
  one definition on two hosts.
- **The module question is ANSWERED, offline, and it cost nothing.** 20b.1 left
  `hook.resource.module` and the shape of an address inside a module read from
  the documentation, and planned to find out during the billable run. It did not
  need to: a local module holding `terraform_data` is as real a terraform run as
  the other fixtures, so `apply-module` was added to
  `tests/fixtures/timeline/generate.sh` with an expectation written from the
  documentation, naming the exact address strings. Run on the devbox against
  terraform 1.15.8 it held to the character:
```text
  addr    module.child.terraform_data.only        fully qualified by the module
          module.pair[0].terraform_data.many[0]   the MODULE's index as well as
                                                  the resource's
  module  module.pair[0] — redundant with addr, which is why the join reads addr
          alone. Empty at the root
```
  The six existing fixtures regenerated to identical expectations and identical
  event counts (16, 15, 14, 10, 13, 13), as in 20b.1. The general form is worth
  keeping: **a question about a tool's own output is usually answerable offline,
  and answering it before the billable run turns a discovery into a
  confirmation.**
- **Six break tests, all red, both controls green**, run on the devbox with the
  tree committed first and exit codes taken directly rather than through a pipe.
  Evidence: `docs/sessions/2026-08-08-phase-20b-2-break-tests.log`.
```text
  1  a live binding names a step the job does not have
  2  a live binding names a job the workflow does not have
  3  the environment filter removed from the node index — stage and prod hold
     IDENTICAL member addresses, so half the map lights from the other
     environment's cycle. The stub topology carries a prod node holding stage's
     members precisely so this reddens
  4  the index stripping stops seeing count, so nothing repeated matches
  5  a hidden group forgets which addresses it hides — they must become UNKNOWN
     rather than being quietly counted as not-shown
  6  the fixture directory emptied — it refuses rather than passing 0/0
  0/6  controls: the untouched tree, before and after
```
- **`make session-open` was naming the wrong phase, and had been for a day.** It
  read "the last data row of the status table", which is the FURTHEST-OUT phase
  rather than the next one: since 20.0 added three planned rows in one go it
  announced `20d — blocked on 20b` to every session that opened. Reading the
  status column instead is no better in the other direction — the first row that
  is not done is phase 8, open and parked since July. It now reads the last
  `- Next allowed step:` line and the `###` heading above it, which is the line
  the document already writes for this purpose and the one the primer tells a
  chat to name itself from. It refuses if that line is missing.
- **The first fix pointed at a different wrong row.** `/^#{2,3} /` is an
  interval quantifier, and under the devbox's mawk 1.3.4 it matched
  `## Completion criteria & validation` and none of the thirty-three
  `### Phase` headings. Plain `/^### /` is correct. Caught by running it rather
  than by reading it.
- Cost so far: **$0**. Nothing applied, no AWS API called.
- Validation, all of it run on the devbox on 2026-08-08, and `ci.yml` green on
  the push with the new step confirmed to have executed:
```bash
  tests/fixtures/timeline/generate.sh   # terraform 1.15.8, 7 cases
  make timeline-check                   # 7/7
  make node-states-check                # 5 cases, 4 from real terraform runs
  make site-data-check
  make site-page-check
  make docs-check
```
- **THE LIVE CYCLE RAN on 2026-08-08, and the apply FAILED — on a real defect,
  not on this phase's code.** `EntityAlreadyExists` creating
  `module.ecs.aws_iam_role.task` and `.execution`: both roles were in AWS and in
  no Terraform state, orphans of an earlier cycle. **They survived because the
  teardown is verified by "no billable resources remain", and an IAM role is not
  billable.** The check was green and the environment was not empty. That is a
  teardown finding, it belongs to nobody's current phase, and it is written up in
  `docs/next-phases.md` rather than fixed here.
- **The failure handed over the live break test for free, which is better than
  arranging one.** The plan was to cancel a destroy mid-flight; reality produced
  an unfinished cycle nobody staged:
```text
  latest.json          published, status "errored", reason "at least one
                       resource errored"
  nodes-apply.json     403 — never written
  the page             "the most recent run did not finish", numbers unchanged
```
  ADR-0040 D1 proven on a real event. A cancelled run cannot erase a
  measurement, and the timeline still says what happened.
- **The teardown then ran green and published what the map draws**: 261 seconds,
  26 resources, `nodes-destroy.json` complete. The `Adopt live resources
  Terraform does not manage` step did its job on the way through.
- **The coverage gate spoke, on real data, about something no fixture had:**
  `module.network.data.aws_availability_zones.available`, action `read`. Terraform
  emits `apply_start`/`apply_complete` for DATA SOURCES too, once per invocation.
  A data block is not a resource block — `generate-topology.py` counts resources
  and D1's gate is about resources — so a data source can never be assigned to a
  group, and leaving it in `unknown` would be a permanent false positive in the
  one channel that is supposed to be rare. It has its own bucket now, and a
  fixture: `terraform_remote_state` reads a local state file, so the case is as
  offline and free as the rest.
- **Two defects only a live run could show, both in the layer written this
  session.** The Destroy phase lit BOTH environment nodes while only stage was
  being torn down — live is per phase, and that phase holds one node per
  environment while `destroy.yml` tears down exactly one per run; the map now
  takes the environments from the dashboard's own `run-name` parse rather than
  re-deriving them. And a phase that says "running now" and nothing else cannot
  be told apart from a page that has stopped updating, so the header carries how
  long it has been running.
- One more, found by reading the published file rather than the page:
  `observed.unknown` counted EVENTS while the list beside it named unique
  addresses — "unknown: 2" above one address. The counts are of the
  deduplicated lists now.
- Cost of the live half: one stage apply that failed after ~8 minutes with RDS
  and ALB created, and one teardown. Under $0.05.
- **CLOSED with one criterion openly unmet, named rather than quietly dropped:
  the apply half was never lit.** `nodes-apply.json` has never existed, because
  the only apply this cycle produced failed on the orphan above, and the map's
  service nodes are still unobserved. Closing anyway is a judgement, and the
  reason is that the missing evidence costs nothing to obtain LATER and cannot
  be obtained NOW: another apply fails identically until the orphan roles are
  dealt with, and 20c needs a cycle of its own regardless. The path is not
  unexercised — the teardown drove the same capture, fold, join and publish end
  to end.
- Next allowed step: **the teardown finding, before any cycle.** It is not
  optional and it is not 20c's: two IAM roles left by an earlier teardown make
  every `deploy-stage` fail at the ECS module, so the next cycle of any kind is
  blocked until they are dealt with and the teardown grows a gate that can see a
  free leftover. `docs/next-phases.md` carries the three decisions it needs.
  Whatever is chosen has to redden on a planted orphan before it counts.

### Ops — the gate that sees a free leftover  ✅ DONE 2026-08-08
Not a phase. The teardown finding 20b.2 uncovered was assigned to nobody on
purpose, and Phase 19 had been declared finished hours earlier — `19h` was
proposed, questioned and withdrawn rather than reopen a phase a document had just
closed. **ADR-0041**, and the summary in
`docs/sessions/2026-08-08-ops-the-gate-that-sees-a-free-leftover.md`.
- Criteria: the two IAM roles blocking every `deploy-stage` are gone, and the
  teardown can see the class they belong to. Both met.
- **The gate was green on a non-empty account, and that was reproduced BEFORE
  anything was written:** `scripts/sweep-orphans.sh stage` said
  `verdict: clean, exit 0` against the live account at 17:50 with both roles
  alive. That run is the control for the whole session — at 19:20 the same
  command in the same account said `orphans, exit 1`, and only the code had
  changed. Both halves are in
  `docs/sessions/2026-08-08-ops-live-break-test.log`.
- Why nothing could see them: the teardown's gate asks about BILLABLE resources
  and a role is free; a partial teardown had dropped them out of state; and the
  tagging API does not index `iam:role`, so the sweep was never handed one. Its
  fail-closed confirmation was blameless.
- The wrong-region explanation was killed by a control INSIDE the same answer:
  `get-resources` in us-east-1 returns the `token.actions.githubusercontent.com`
  OIDC provider and no role at all, though the two permanent `github-deploy`
  roles carry the same tags in the same state level. Only the resource type
  differs.
- **A prefix scan was approved and then found unrunnable by reading the policy
  before writing the code.** The deploy role has `iam:GetRole` on exactly two
  ARNs and neither `iam:ListRoles` nor `iam:ListRoleTags`; scanning needed a new
  account-wide grant applied to a permanent state level, to build a gate. So
  discovery comes from the CONFIGURATION instead — a collision can only happen on
  a name the configuration will create — which also excludes the permanent
  deploy role structurally rather than by trusting a tag.
- **The session put a defect into its own patch and caught it on the specimen.**
  Adopting the orphan role alone would have been worse than adopting nothing:
  `DeleteRole` refuses while a policy is attached, so the import hands `destroy`
  a `DeleteConflict` — red, and still leaking, with the launch lock kept and the
  public button shut (ADR-0036 D2). Found by asking AWS what was attached BEFORE
  removing anything; the teardown had leaked four objects, not two. Patch 1 was
  applied on the devbox and deliberately not pushed until patch 2 mapped the
  dependents.
- Validation, offline first and then live:
```bash
  make test-unit          # 112
  make docs-check
  make site-data-check
  make site-page-check
  # `gh run watch` takes a run id and has no -w; the flag belongs to `gh run
  # list`. Written as `gh run watch -w ci` here until 20c tried to copy it.
  gh run watch "$(gh run list -w ci -L 1 --json databaseId --jq '.[0].databaseId')"
                          # green on 4d95caa, all four jobs
  gh workflow run destroy.yml -f environment=stage -f confirm=DESTROY
  aws iam get-role --profile demo-admin --role-name aws-devops-sdet-demo-stage-ecs-task
```
- The live run: `verdict: orphans` under the deploy role's own OIDC credential,
  `adopted 4 of 4; 0 could not be imported`, destroy in dependency order with no
  `DeleteConflict`, final sweep `clean` — and then `aws iam get-role` answered
  `NoSuchEntity` for both, because every step of that workflow was green and this
  project has been fooled by that exact shape before.
- Two things found on the way and fixed here: CI went red on `site-data-check`
  for the new ADR (the map publishes the ADR count, and its drift message named
  `infra/` and `tests/` while the drift was in `docs/decisions/`), and one
  measurement measured the wrong thing — `gh run list -L 1` returned the
  `publish-site` run, so `ci exit: 0` was about a different workflow.
- Chat session links are no longer published: `.claude/settings.json` sets
  `attribution.sessionUrl: false`. **Unproven** — this session's commits arrived
  by `git am`, where the trailer never appears, so the first commit from a Claude
  Code session on the devbox is the test.
- Cost: one `destroy.yml` run, no resource created, IAM deletions free. Under
  $0.01.
- Next allowed step: **20c — the tests panel.** The cycle is unblocked and the
  account is empty, so 20c can have the cycle 20b.2 could not finish: its apply
  half has still never been lit, `nodes-apply.json` has never existed, and the
  map's service nodes are unobserved. `docs/next-phases.md` carries what 20c is
  for; two items were added to it there rather than done here — a
  `make session-close` check for chat links in unpushed commits, and the
  `ExpiresAt` predicate as a second gate (ADR-0041 D6).

### Phase 20c — The suites answer for themselves  🟡 HALF DONE 2026-08-08
Inventory, fold, wiring and ONE LIVE CYCLE. **ADR-0042**, and the summary in
`docs/sessions/2026-08-08-phase-20c-the-suites-answer-for-themselves.md`.
- Criteria: an inventory collected from the suites rather than written beside
  them; a fold from the reporters' own output onto the suite nodes; a cycle
  proving both; the page drawing them. All but the last are met.
- **Reading the repository before writing code killed three lines of the plan**:
  `tests/db` has no collector and was given `--list` rather than a description;
  the map's gate lives in a job with no test dependencies, so the inventory gate
  runs in `local-ci`; and the db assertion exists twice, with the cloud running
  the copy `make test-db` does not. That mirror had been asked for by a comment
  at the top of each file for eleven phases and is now a refusal.
- Eleven deliberate defects offline, green control before the first and after
  the last, in
  `docs/sessions/2026-08-08-phase-20c-the-suites-answer-for-themselves.log`. One
  did NOT break as designed: "refusing to report zero" is unreachable for the
  pytest suites, because pytest exits 5 first.
- **The cycle: apply 31276975666, destroy 31277877190.** The apply half of 20b.2
  is lit at last - `nodes-apply.json` had never existed - with real per-group
  durations and identifiers. Real results published: api 52, regression 12,
  smoke 2.
- **And it broke one thing, in the half that had never run.** `db` came back
  `incomplete, 1 passed, 1 not_run` for a suite that passed both checks:
  `aws logs get-log-events --output text` joins an array with TABS, so three log
  events arrived as one line. A race was assumed and a fix for it written BEFORE
  the log was read; the log refuted it in one command. Fixed at the capture
  (`--output json`, `jq -r` per message); the real bytes are fixture
  `a-flattened-log-capture-is-incomplete`, which pins that the fold names the gap
  rather than filling it in.
- Three findings for the page, from watching the cycle rather than from code:
  every node of a running phase claims "running now" while terraform creates one;
  a phase that has FINISHED falls back to "nothing recorded yet" until the run
  publishes at the end, which is indistinguishable from never having run; and
  `suite.db.stage` is drawn in the quality gate while its step runs in Provision
  - stage and prod disagree about this today.
- Validation:
```bash
  make suite-inventory-check   # clean on sandbox, devbox and the runner
  make results-check           # 10/10
  make test-unit               # 112
  make docs-check
  curl -fsS https://demo.uveapp.net/results/stage/latest.json | jq .nodes
  aws sso login --profile demo-admin --use-device-code   # then ecs/rds/alb/nat/eks
```
- Teardown confirmed against the AWS CLI under a live credential, not against
  Terraform state and not against the green run: account 993912191738, all of
  ecs, rds, alb, nat and eks empty.
- Cost: one full cycle, about 25 minutes of RDS and ALB. **20d computed it:
  $0.0183 .. $0.0238.** Not reconciled against a bill, and that is no longer
  pending work - the clause was retired in ADR-0045 D6.
- Next allowed step: closed by the section below, on 2026-08-08.

### Phase 20c — A node answers for its own step  ✅ DONE 2026-08-08
The page. **ADR-0043**, and the summary in
`docs/sessions/2026-08-08-phase-20c-a-node-answers-for-its-own-step.md`.
- Criteria: `site/index.html` reads `site/data/suites.json` and
  `results/<env>/latest.json`; the three findings above are answered; a suite
  node has its own `live` binding. All met.
- **The three findings were one mistake**: liveness was attached to the BOX a
  node is drawn in, and a box is a layout decision. A suite node now carries its
  own `live` binding, checked against the workflow by the same code that checks
  a phase's; a node without one inherits its phase and is MARKED as having
  inherited, so seven nodes stop claiming to run while Terraform creates one; and
  a phase whose steps are over in a run still going says so, instead of showing
  the sentence a phase that has never run shows. stage and prod stop disagreeing
  about `db` because neither is guessing.
- **The one fold that cannot move to Python** is gated where it lives.
  `make live-state-check` lifts the marked block out of the BUILT page and runs
  it against twelve recorded Actions observations - the code the visitor's
  browser executes, not a copy. It reads the built page, so a template edited
  without rebuilding reddens it, which is how the first run of the fixtures went
  red.
- Ten deliberate defects, green control either side, in
  `docs/sessions/2026-08-08-phase-20c-a-node-answers-for-its-own-step.log`,
  including all three findings put back. The sharpest line: `suite.db.stage` -
  "the machine reported nothing" - while its step was running.
- **A fourth defect, found writing the gate rather than watching the cycle**: the
  phase clock restarted at every bound step, so a four-minute apply read as ten
  seconds old. The old code's own comment said it should run from the first step
  to begin; the code under it did the other thing.
- Validation:
```bash
  make site-data-check     # clean, 116 resources across 8 levels
  make site-page-check     # byte-identical to a fresh build
  make live-state-check    # 12/12
  make results-check       # 10/10
  make docs-check          # 6 documents, 0 findings
```
- Cost: nothing. No AWS call, no cycle, no credential; verified offline against
  fixtures and a headless render.
- **Found after this section was written, by running its own validation:**
  publishing the page deleted the results it had just learned to read. The site
  sync excludes the prefixes the lifecycle writes and `results/` was never added
  to that list (**ADR-0044**, and
  `docs/sessions/2026-08-08-ops-the-site-sync-deleted-the-results.md`). Fixed,
  and gated by `make publish-prefixes-check`. Nothing above is untrue - but the
  suite half of the published map is EMPTY until a cycle runs again, and that is
  the reason, not a regression in the page.
- Next allowed step: **20d - cost, computed and reconciled.** It was blocked on
  20b and is not any more, and 20c's cycle of 2026-08-08 is the first one a bill
  can be reconciled against. Start with the dated rate table; the reconciliation
  is the point, not the formality.
  *(Written before 20d ran. The rate table was right; the reconciliation was
  not - see the section below and ADR-0045 D6.)*

### Phase 20d — Cost is a lifetime, not a creation  ✅ DONE 2026-08-08
The computation. **ADR-0045**, and the summary in
`docs/sessions/2026-08-08-phase-20d-cost-is-a-lifetime.md`.
- Criteria: a dated rate table captured rather than typed; a fold from the
  cycle's own timelines to a per-cycle figure, labelled COMPUTED; a gate over
  each; the estimate applied to a real cycle. All met.
- **Reading the cycle before writing the fold killed the obvious design.**
  `elapsed_seconds` is in every timeline and is how long TERRAFORM took to build
  a resource; the meter runs for as long as the resource EXISTS. The ALB of
  2026-08-08 took 173 seconds to create and then stood for 1582 more. The same
  read produced the second decision: the estimate is a BAND, because nothing in
  the stream can see the instant AWS starts charging — 852 to 1381 seconds for
  RDS, 62% apart.
- Three inputs, three homes, no file holding two kinds of thing: prices CAPTURED
  into `site/data/rates.json` with their SKUs, the shape DERIVED from `infra/` and
  recorded nowhere, the judgement EDITORIAL in `assets/cost-model.json`.
- `make rates-check` is coverage read from the configuration: every kind the
  per-cycle levels declare is priced, free, or named as not metered. The fold
  refuses from the other side for a kind it observes and cannot price — 0
  UNPRICED across the 32 resources of the real cycle.
- **The real cycle: $0.0183 .. $0.0238**, and five sixths of it accrued OUTSIDE
  every phase. Cost per phase is not a property a lifetime has; overlap
  attribution is, and the first thing it says is that the phases are not where
  the money is.
- Thirteen deliberate defects, green control either side, in
  `docs/sessions/2026-08-08-phase-20d-cost-is-a-lifetime.log`. One did NOT test
  what it was aimed at — a forced `closed = True` crashed the fold instead of
  producing a plausible wrong answer, and was re-aimed at `state` alone. One gap
  the log names: every coverage refusal but the last carried the missing-table
  finding as well, so the green control after the capture is the only clean one.
- ADR-0039 D3's promised reconciliation against a real bill is RETIRED
  (ADR-0045 D6): an estimate is what was asked for, Cost Explorer needs another
  credential and answers a day late, and Budgets watches actual spend already.
- Validation:
```bash
  make cost-check          # 6/6 fixtures
  make rates-check         # clean: 26 kinds, 3 priced, 19 free, 4 named
  make docs-check          # 6 documents, 0 findings
  make site-data-check
  make rates               # needs pricing:GetProducts; run by hand
```
- Cost: nothing. One free read-only price-list call; no cycle, no environment.
- Next allowed step: **20e — the page is compact, and the map is the page.** It
  is layout only, changes no data and no gate, and it is where this phase's
  numbers would first become visible. Before any of it, settle the two
  collisions `docs/next-phases.md` already names: hover is not a carrier on a
  phone, and a timer drawn on a node is a claim the page cannot make. Wiring the
  fold into the destroy job is the other open thread, and it needs the pairing
  rule broken on purpose first.
  *(SUPERSEDED the same evening. One of the two "collisions" was a collision
  with a spontaneous example rather than with a decision, and the order of the
  two remaining threads is reversed — see the section below.)*

### Phase 20 — the plan corrected before it was followed  2026-08-08
No code. The section of `docs/next-phases.md` that the cursor was pointing at
described **hover** as plan, with a costed collision worked out beneath it. Asked
about it directly, the person who wrote the request said it had been a spontaneous
example and was never a decision — so the document had been carrying an intention
nobody held, in the one place a session goes to find out what to do next.

- That is this project's own recurring defect wearing new clothes. A stale
  document usually says something that WAS true; this one said something that
  never was, and it was formatted exactly like the four lines around it that
  were. The costed collision beneath it made it read as MORE considered, not
  less.
- The real requirement, restated in the words it was given in: the dashboard
  should be compact and informative, and today it is a long strip you cannot
  navigate. That is **wayfinding**, not density — a denser page with no route
  through it is the same defect in less space. The UI phase now opens with a
  discovery step of its own.
- Three findings from reading the page and ADR-0043 are recorded in the plan so
  the UI phase does not rediscover them: the per-node prose is ADR-0043 D4's
  disclosure and cannot be hidden behind anything; a free skyline pack can place
  phase 7 above phase 6, and sequence is `generated, exact`; and the body markup
  is 3.0% of `site/index.html`, so "compact" cannot mean fewer bytes.
- The two threads swap places. Wiring the cost fold is **20f** and comes first;
  the UI phase keeps the name **20e** and comes second, because ADR-0045 and a
  dated session summary already use "20e" to mean the phase that renders the
  cost, and a session record is not rewritten to free up a name.
- Validation: none needed — no code, no gate, no infrastructure changed.
- Cost: nothing.
- Next allowed step: **20f — the cost fold runs in the cycle.** `scripts/fold-cost.py`
  into `destroy.yml` beside `scripts/node-states.py`, an apply timeline anchored
  on the rule `nodes-apply.json` already follows, and the pairing rule with its
  four refusals. It is written and broken offline against fixtures; no cycle is
  ordered for it. One line on the page — last cycle, the band, the date — and
  nothing more, because where it belongs is 20e's question.
  *(Done the same session. The rule grew a fifth clause once the break test
  found one of the four was testing nothing.)*

### Phase 20f — The teardown prices the cycle it just ended  ✅ DONE 2026-08-08
**ADR-0046**, and the summary in
`docs/sessions/2026-08-08-phase-20f-the-cost-fold-runs-in-the-cycle.md`.
- Criteria: the fold wired into the teardown; an apply anchor it can trust; a
  pairing rule with a break test; one line on the page. All met.
- **The pairing rule is five clauses, not four.** Same environment, an apply that
  is complete, a teardown that does not start before the apply finished, and two
  resource sets with something in common — plus a timeline that names no
  environment at all, which the break test found untested. The intersection
  clause is deliberately WEAK: ADR-0038 adopts orphans before a teardown, so only
  a pair with nothing in common is refused, and the existing partial-orphan
  fixture stays green.
- The anchor rides an existing rule rather than a new one:
  `timeline/<env>/apply.json` is written inside the block that publishes
  `nodes-apply.json`, on the same kind and the same completeness, so the anchor
  and the at-rest numbers cannot disagree about which cycle they came from.
- **The break test broke, and the instrument was the defect.** Four one-clause
  breaks each reddened the same fixture; the identical loop then reported all
  four green. CPython validates a `.pyc` on (mtime in whole seconds, source
  size), every break leaves the file at exactly 18911 bytes, and the loop runs
  inside a second. Five gates load a script under test through `importlib`; all
  five now write no cache.
- `make publish-prefixes-check` went RED unprompted on `cost/`, the first prefix
  added since ADR-0044, and named the remedy. First time that gate has caught
  something it was not shown in advance.
- Deliberately not covered: pricing cannot fail a teardown
  (`continue-on-error` — a red destroy job holds the launch lock), there is no
  phase attribution, and no live cycle was ordered. The next teardown is the
  first live exercise and costs nothing extra to wait for.
- Validation:
```bash
  make docs-check cost-check rates-check node-states-check results-check \
       timeline-check site-page-check site-data-check live-state-check \
       publish-prefixes-check action-pins
```
- Cost: nothing. No cycle, no AWS call, nothing applied.
- Next allowed step: **20e — the dashboard is navigable.** Its discovery step
  first, per `docs/next-phases.md`: what a visitor is trying to reach and in what
  order, before a line of layout. The three findings recorded there are the
  starting material, and the timer question has a rule available from ADR-0043
  that costs neither of ADR-0039 D4's variants. Separately and smaller: the
  wired fold has never run live, so the next teardown of either environment is
  worth watching for the cost line appearing.
  *(Discovery ran on 2026-08-09 and renamed its own phase. "Navigable" was the
  wrong target — see the section below and ADR-0047.)*

### Phase 20e.0 — The dashboard is composed, not scrolled  ✅ DONE 2026-08-09
Discovery and a sketch. No implementation. **ADR-0047**, and the summary in
`docs/sessions/2026-08-09-phase-20e-discovery-and-sketch.md`.
- Criteria: what a visitor is trying to reach, established before a line of
  layout; the requirement restated in the words it was given in; a sketch built
  from real data, measured. All met.
- **"Navigable" was the wrong target, and the discovery is what found it.** A
  section index would have made a long strip traversable; the requirement is
  that it stop being a long strip — a dashboard, composed in blocks, showing
  where things are, how they connect, which tools are used and in what order,
  with the detail under cuts. The desktop monitor is the primary target.
- The complaint measured rather than quoted: 3.6 screens at 1920x1080 and 10.5
  at 390x844, with **0 in-page anchors, 0 `<nav>`, 0 sticky elements** — the
  page has no navigation affordance at all. The per-cycle map is 46% of it, and
  the repository link sits in the footer at 100% of scroll depth.
- **A channel nobody had measured.** Five of the map's six states are carried by
  a 1px border and nothing else; three are under WCAG 1.4.11's 3:1 floor in the
  light theme (working 2.67, done 2.41, suite 1.98), and the pulse fades a 1px
  ring to `opacity: 0`. The first measurement was WRONG and caught itself:
  `color-mix()` resolves to `color(srgb 0.44 …)`, the parser divided by 255, and
  six colours came back at 20.92:1. Re-measured with a control reading 21:1 for
  black on white in both notations.
- The tools are missing, not just their marks: Terraform, Docker, Playwright,
  pytest and Alembic appear nowhere on the map. Named in text (ADR-0047 D4);
  vendor marks are separate work, as `assets/github-logo/NOTICE.md` already is.
- The sketch — `docs/sessions/2026-08-09-phase-20e-sketch.html`, real topology
  and suite data, placeholder run figures, and it says so on its own face — is
  1.1 screens at 1920x1080 and 1.0 at 2560x1440, with 0 boxes overflowing their
  own parent at any of the four viewports. Measured per-parent, not against the
  document, which is 20a's lesson: the document measure would have missed the
  74px table overflow it caught on the phone.
- Open and named: the Launch button has no place in the composition, the legend
  has no home, a compact node has nowhere for durations and suite counts, the
  phone is 4.2 screens and deferred, the contrast gate does not exist yet, and
  the map's column span total is a literal that must become computed.
- Validation:
```bash
  make docs-check
  make site-data-check
```
- Cost: nothing. No cycle, no AWS call, nothing applied. `site/` and `assets/`
  untouched.
- Next allowed step: **20e.1 — the composition implemented on the real page.**
  `assets/index.template.html`, rebuilt with `make site-page`, gated by
  `make site-page-check`. Take the four open items in order of what blocks
  layout: the Launch button and the legend decide space, the node's duration and
  counts decide the node, the phone comes last. The contrast floor of ADR-0047
  D6 needs a gate before the palette moves again, and it should be broken on
  purpose once like every other gate here.

### Phase 20e.1 — The floor is met before the layout  ✅ DONE 2026-08-09
Three decisions and a gate. The composition itself is NOT started. **ADR-0048**,
the summary in `docs/sessions/2026-08-09-phase-20e-1-the-floor-is-met-before-the-layout.md`,
break tests in `docs/sessions/2026-08-09-phase-20e-1-contrast-gate-break-tests.log`.
- Criteria: the three open items that block layout decided before any layout; the
  contrast floor of ADR-0047 D6 enforced by something that refuses; that gate
  broken on purpose. All met.
- **The three that blocked space.** The Launch button is the Environments panel's
  footer — it acts on what that panel observes, and its refusals are that panel's
  subject; the identity bar is navigation and a control that spends money does not
  belong in it. The legend is a cut in the map's header, because D6 put a word on
  every node and a decoder is no longer what it is — and the sketch's "State
  encoding" strip does NOT go on the page. A node's figures live on one state line,
  `<word> · <figure>`, word first, with no separator printed when there is no
  figure.
- **`make contrast-check`** renders the BUILT page's own stylesheet in chromium
  rather than parsing CSS, because the engine is what resolves `color-mix()`. A
  control runs first on every invocation — black on white must read 21.00 through
  both notations — and a control that is off refuses without a verdict.
- **It reproduced ADR-0047's table to the hundredth on five of six states**,
  written from scratch and sharing no code with the discovery's script, which was
  never committed. The sixth, `absent`, reads 1.15/1.12 against 1.34/1.35: the
  older figure is unreachable, since `#d8dbe2` on pure white is 1.27. ADR-0048 D4
  supersedes that row and nothing follows from it.
- **The palette moved before the layout, and the fix landed before the gate.**
  working 2.67→3.22, done 2.41→3.37, suite 1.98→3.38 in the light theme; each
  boundary is now a token in `:root`, so `.node.done` and `.phase.done` share one
  definition instead of two matching literals. A gate arriving red on a shared
  dependency reddens every open pull request, which the image scan already did once.
- **Broken seven ways**, green control either side: a state under the floor, a
  token lightened with no state colour edited, the discovery's own parser defect
  replanted (refused on the control at 1.01), an empty contract, no contract, a
  probe that is not a colour, and the built page missing. An eighth refusal fired
  unplanned during development, on playwright resolving without a named export.
- **Deferred deliberately:** ADR-0047 D5's computed column span total. It is
  computable today and nothing would read it, and a number nothing reads has never
  been exercised.
- Validation:
```bash
  make contrast-check
  make site-page-check site-data-check docs-check
```
- Cost: nothing. No cycle, no AWS call, nothing applied. `site/` changes, so the
  next push republishes the static page.
- Next allowed step: **20e.1 continued — the composition on the real page.**
  `assets/index.template.html`, rebuilt with `make site-page`, gated by
  `make site-page-check`. The three decisions above are the inputs; ADR-0047 D5's
  span total lands in the same commit as the grid that reads it. The phone stays
  last. Separately and still true: the wired cost fold has never run live, so the
  next teardown of either environment is worth watching for the cost line.

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
