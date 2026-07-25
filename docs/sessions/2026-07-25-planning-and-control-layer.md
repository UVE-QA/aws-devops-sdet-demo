# Session 2026-07-25 — planning session: MVP track, ADR-0017, control layer into git

- Phase: 8 (lifecycle half closed; feature expansion not started)
- Request: decide what happens to the application and to the project as a whole
  after the deploy → demo → destroy cycle closed; produce a real plan for the
  remaining phases before writing any more code.
- Tooling note: this session ran in Cowork on the MacBook, not Claude Code on
  the devbox. Files were produced locally and transferred by `scp`.

## Decisions taken (recorded in ADR-0017)

- **D1** prod lives in the SAME AWS account as stage, separated by state key,
  name prefix, deploy role, GitHub Environment and VPC. A separate member
  account was rejected on schedule cost, not on merit.
- **D2** hybrid availability: the dashboard is always on, every workload
  environment is on demand. The dashboard is hosted on S3 + CloudFront + OAC in
  AWS — not GitHub Pages — and needs its own permanent Terraform state level
  `infra/public-site/`.
- **D2a** prod keeps NO data between cycles. Honest framing for interviews:
  "a production-shaped environment with a promotion gate", not "production".
- **D3** public HTTPS on an owned domain. Note: the CloudFront certificate must
  be issued in us-east-1, the ALB certificate stays in us-west-2.
- **D4** external access is phased — view-only first, self-service launch last.

## Plan produced

`docs/next-phases.md` replaces the unordered wish-list in project-prompt.md §14
with two tracks and an explicitly stated MVP finish line:

```text
MVP     9  prod + promotion + HTTPS      (9.0 reconcile scaffold, 9.1 build)
       10  thin application slice
       11  public dashboard
       12  minimum viable documentation
       13  MVP verification gate (empty → empty in one run)
Polish 14  release resilience / rollback
       15  security gates (Trivy, Checkov, gitleaks, Dependabot)
       16  full test depth + observability
       17  prod data continuity (optional)
       18  remaining documentation
       19  guarded self-service launch + out-of-band watchdog
```

Ordering was deliberately changed mid-session from documentation-first to
prod-first, once the stated goal became "fastest path to a shareable MVP".

## Two findings that mattered more than the plan

**1. The control layer had never been committed.** `CLAUDE.md`,
`.claude/skills/` (9 skills + registry), `docs/sessions/`,
`docs/skills-structure.md`, `docs/project-instructions-pointer.md` and the ADR
template existed ONLY in a non-git folder on the MacBook, created 2026-06-06.
The repo had 93 tracked files and none of them. Claude Code on the devbox had
been starting with no anchor file and no skills for seven weeks.

Found by accident: a verification command intended for the MacBook was run on
the devbox, and the resulting `find` dump of the home directory exposed what the
repo did and did not contain.

Fixed in `f8f32e5` (18 files, 93 → 111 tracked). The stale `README.md` was
deliberately NOT committed — its June version claims "pre-devbox scaffold,
app/infra built later", which contradicts reality. It is rewritten in Phase 12.

**2. `infra/envs/prod` is a stale Phase 4 scaffold that contradicts two ADRs.**

```text
- still contains module "iam_github_oidc"  → the construct ADR-0015 removed
  from stage precisely because destroy deletes its own permissions mid-run
- passes db_secret_arn where the post-C2 module takes db_secret_arn_pattern
  → this directory cannot plan against the current modules at all
- no depends_on = [module.alb] on ecs → the ADR-0016 ENI/IGW race, built in
- declares its own ECR repo, which conflicts with promotion-by-digest
- destroy.yml offers "prod" in its dropdown with nothing behind it
```

The second bullet is the important one: **an entire IaC directory has been
failing to validate for seven weeks and CI never said so**, because
`terraform validate` does not cover the whole tree.

## Lessons recorded as invariants in next-phases.md

- A fix to a shared invariant is applied to EVERY environment directory in the
  same commit, not only to the one currently being exercised. C2 (ADR-0015) and
  the ecs/alb ordering fix (ADR-0016) both went to stage only.
- CI validates EVERY IaC directory. An unvalidated directory rots invisibly.
- "GitHub is the source of truth" is a claim that has to be verified, not
  assumed. The project's own operating guide lived outside the source of truth
  while the document asserting that rule sat in the same untracked folder.

The shape of both findings is the same as the infrastructure bugs this project
already documents: something looked finished, was never exercised on the path
that would expose it, and stayed broken until an accident surfaced it.

## Commands run

```bash
# on the devbox
git ls-files | wc -l              # 93 → 111
git check-ignore -v <paths>       # nothing ignored — simply never committed
git ls-files infra/envs/prod      # 6 files: the scaffold IS tracked
tar xzf /tmp/control-layer.tar.gz
git add -A && git commit && git push
```

## Result

- `docs/decisions/0017-prod-environment-model.md` — new ADR
- `docs/next-phases.md` — new plan, MVP-first
- control layer committed; the repo is now self-contained for a cold start
- Phase 9 redefined: it begins with reconciliation, not construction

## Blockers

None. Phase 9 is unblocked but must start with 9.0.

## Next step

Phase 9.0 — reconcile `infra/envs/prod` against ADR-0015 and ADR-0016, extend
`terraform validate` to the whole `infra/` tree, and decide the ECR question
(one shared repository vs cross-repository image copy) before writing
`promote-prod.yml`.
