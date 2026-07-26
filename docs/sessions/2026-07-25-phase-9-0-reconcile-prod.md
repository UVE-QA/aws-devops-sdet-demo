# Session 2026-07-25 — Phase 9.0: reconcile the prod scaffold, close the validation gap

- Phase: 9.0 (reconciliation). Closed. 9.1 not started.
- Request: run Phase 9.0 as planned in `docs/next-phases.md` — make
  `infra/envs/prod` valid against the post-C2 modules, decide the ECR question,
  and make CI enforce validation across the whole tree.
- Tooling: Cowork chat on the MacBook driving, devbox executing. Files were
  authored in the chat, delivered as guarded patch scripts over `scp`, and
  committed on the devbox.
- **No AWS API was called and nothing was applied.** Zero cost.

## Result

```text
7 commits    0ce9326  ADR-0018
             ffe060d  primer: six state levels, chat supplies the transfer path
             2027654  discussion-log: same
             ab22a58  shared ECR at a permanent state level
             1987c1f  prod reconciled against the post-C2 modules
             e05cc02  validate every root level, hermetically
             e1e577a  tf-validate fails when it discovers nothing
```

`infra/envs/prod` validates for the first time in seven weeks. All five root
levels pass `terraform fmt -check` and `make tf-validate`, with no AWS
credentials present. CI green (`ci #33`).

## Decision — ADR-0018: the registry moves to a permanent state level

`docs/next-phases.md` had left the ECR question open with two candidates and a
parenthetical calling the shared-registry option "(simplest)". Tracing it showed
the parenthetical was an assumption, and wrong: a shared registry inside
`infra/envs/stage` is deleted by stage teardown, taking the image prod has
promoted with it. Prod would survive until its next pull, then fail with
`ImagePullFailure` — asynchronously, long after the teardown that caused it.

So the registry became level 3 of six, `infra/shared-ecr/`, permanent, applied
locally once per account. `module "ecr"` was removed from BOTH environments in
the same commit.

The change **removes** two workarounds rather than adding any. `deploy-stage.yml`
had a targeted `apply -target=module.ecr` before the build plus a
`terraform output` lookup, both introduced to fix `b71b846` — an empty ECR URL
that produced the docker tag `":<sha>"` and passed silently. With a permanent
registry the repository always exists, so both steps are gone. The URL now comes
from `aws ecr describe-repositories` and still fails loudly, with a message that
names the fix.

Costs accepted and recorded: ECR storage (cents/month, bounded by a lifecycle
policy that expires untagged images after a day and caps tagged history at 10);
one more local apply on a fresh account; and the honest teardown claim becomes
"nothing bills beyond the state bucket and the registry" rather than "nothing
bills".

## What was actually wrong with prod

All five documented items were confirmed against the code, and four more were
found:

```text
documented   module "iam_github_oidc" still present          (ADR-0015)
             db_secret_arn vs db_secret_arn_pattern          → could not plan
             no depends_on = [module.alb] on ecs             (ADR-0016)
             its own ECR repository ...-app-prod             → ADR-0018
             destroy.yml offered "prod" with nothing behind it

new          prod/outputs.tf was missing task_definition_arn,
             ecs_app_security_group_id, public_subnet_ids and container_name —
             exactly the four outputs run-task consumes. promote-prod.yml could
             not have run migrate/seed/db-assert against prod.

             destroy.yml derives the deploy role ARN from the environment name,
             and bootstrap-oidc creates exactly ONE role (name_prefix is a
             scalar). The prod choice therefore died at OIDC authentication, not
             somewhere in Terraform. Removed until 9.1 creates the role.

             destroy.yml still exported TF_VAR_github_owner/github_repo, which
             deploy-stage.yml lost in session 3. Terraform silently ignores an
             undeclared TF_VAR_.

             state_bucket_name was declared and unused in STAGE, dead since C2
             moved the OIDC module out. Removed from both directories.
```

prod and stage now have identical module and output structure, verified by
diffing the two rather than by reading them.

## The validation gap had two halves, not one

The known half: `make tf-validate` only entered `infra/envs/stage`, so an
invalid directory could sit in the repository indefinitely. Root levels are now
**discovered** (`find infra -name '*.tf' -not -path 'infra/modules/*'`), so a new
state level is validated the moment it exists rather than when someone remembers
to add it. Modules are excluded deliberately — `terraform init` inside a module
directory leaves a `.terraform.lock.hcl` that does not belong to a non-root
configuration — and are covered transitively by the levels that use them.

The half nobody knew about: **`terraform init -backend=false` does not skip the
backend** in a directory that has been initialized for real. It reuses the cached
S3 configuration in `.terraform/` and reads state. The Makefile comment promised
"no AWS creds needed"; on the devbox the target failed with a 403 unless an SSO
session was live. It passed in CI only because a fresh checkout has no
`.terraform/` — correct by accident. Fixed with an isolated `TF_DATA_DIR` per
directory, and the claim now has a test: the script re-runs the target with the
entire AWS environment stripped.

## A mistake made inside this session

The first version of the new target had the defect it was written to prevent.
`TF_ROOTS` is computed by `find`; if that expression ever stopped working the
list would come back empty, the loop would run zero times, and the target would
exit **green having validated nothing** — `b71b846` again, an empty value passing
silently, introduced one commit after writing that lesson into a commit message.

Caught by asking "what does a green result here actually prove?" rather than by
any test. Fixed in `e1e577a`: an empty root list is now an explicit failure,
verified with `make tf-validate TF_ROOTS=`.

Worth keeping because it is evidence about the failure mode rather than about
one target: knowing the pattern by name does not stop you writing it.

## Process notes

- Delivery friction: a file authored in the chat does not reach
  `~/Projects/_claude-transfer` by itself. `session-primer.md` now requires the
  chat to emit a ready-to-run `cp` with its own outputs path substituted, before
  any mention of `send.sh` — the path contains per-session identifiers and can
  never be written down.
- Patch scripts with `assert`-guarded exact-match replacements were used for
  every edit to an existing file. Each was rehearsed on a throwaway copy of the
  repository in the chat sandbox before delivery. Re-running one fails loudly
  rather than applying twice.
- Running the validation loop over module directories littered eight
  `.terraform.lock.hcl` files into the working tree. Caught by checking
  `git status` before committing rather than after.
- The repository was read by cloning it into the chat sandbox over HTTPS with a
  short-lived read-only fine-grained token, rather than by trusting the Claude
  Project mirror. The mirror was five commits stale and did not contain
  `session-primer.md` at all — the file the startup prompt names first.

## Open, for 9.1

```text
- a SECOND deploy role for prod in infra/bootstrap-oidc; name_prefix is a scalar
  today, so this needs a second module block or for_each
- GitHub Environment prod with required reviewers; environment:prod in the trust
  policy; restore the prod choice in destroy.yml
- promote-prod.yml: take the image DIGEST from a green stage run, never a
  floating tag. The shared registry outlives the environments, so a stale image
  is now promotable and the digest is the only safe reference.
- prod desired_count is still 0 by design until the role exists
- ACM certificate + Route53 + 443 listener + HTTP→HTTPS redirect
- infra/shared-ecr has never been applied. It is applied locally under
  demo-admin at the start of the next cycle, BEFORE deploy-stage.yml, which now
  fails fast if the repository is absent.
- debt, not urgent: the GitHub variable TF_VAR_DEMO_ACCOUNT_ID is not a Terraform
  variable. Only destroy.yml uses it, to build the role ARN. Fixing it means
  renaming a variable in the GitHub UI, so it was left alone rather than churned.
```
