# Session Primer

Read this first in any new session. It is a **pointer**, not a summary — it says
what to read and in what order, and what has burned us before. It deliberately
contains almost no state, so it does not go stale.

The cursor lives in `docs/phase-gates.md`. Nothing else claims to know the
current phase.

---

## A. Claude Code on the devbox (full repo access)

```text
1. git pull
2. docs/phase-gates.md      the cursor: current phase, last validated step,
                            what is allowed next
3. docs/next-phases.md      the plan: MVP track 9-13, polish track 14-19
4. docs/decisions/          the "why". Newest first; 0015, 0016, 0017 shape
                            everything currently in flight
5. docs/discussion-log.md   the narrative. Read the top "Current state" block;
                            go deeper only if you need history
6. docs/sessions/INDEX.md   only when you need a specific past session
```

Then STOP and state the phase, the next allowed step, and any blocker before
touching anything.

## B. Chat / Cowork session with NO repo access

The Claude Project holds copies of `discussion-log.md` and `project-prompt.md`.

**They are MIRRORS and they lag.** The repository is the source of truth. Before
relying on the mirror for anything that matters, ask for:

```bash
cd ~/aws-devops-sdet-demo && git log --oneline -5 && git status --short
```

If the mirror is behind, say so out loud rather than reasoning from it. This is
not hypothetical — on 2026-07-25 the mirror was seven weeks stale and the
control layer it described was not in the repo at all.

If the repository is public by then (planned in Phase 11.0), skip all of this
and clone it into the session sandbox instead. The sandbox reaches github.com
over HTTPS; SSH out is blocked.

---

## Working agreements

```text
- Phase gates are real. End of a phase: summary → validation → STOP →
  explicit confirmation. Do not advance without it.
- One command block at a time. Wait for real terminal output before the next.
  No speculative multi-step sequences.
- Label every command block [mac] or [devbox]. The wrong host has already cost
  a wasted round trip.
- Explicit confirmation before ANY billable action. Review the plan first.
- Never ask for secrets. Account ids, ARNs, region names, repo names are fine;
  keys, tokens, passwords are not.
- Prefer a checked-in patch script over a long interactive heredoc for edits to
  long documents: it fails loudly and changes nothing on mismatch.
```

## Verification habits that keep paying off

```text
- Verify the previous step before starting the next one. Several steps in this
  project were silently skipped and only caught by an explicit check.
- "It looked finished" is the recurring failure mode here, not "it broke".
  Every serious bug so far was something that had never been exercised on the
  path that would expose it.
- A claim about state is not state. Check git, check AWS, check the file —
  do not trust a document, including this one.
- After a teardown, confirm against the AWS CLI, not against Terraform state.
```

## The transfer workflow (files produced in a chat)

```text
mac:     ~/Projects/_claude-transfer/    buffer; should be empty almost always
         send.sh <file> <repo/path>      copies to the devbox, never commits
devbox:  ~/aws-devops-sdet-demo/         the ONE working copy
github:  UVE-QA/aws-devops-sdet-demo     source of truth
ssh:     ssh devbox / scp file devbox:/tmp/
```

Anything sitting in the buffer has not been committed yet. Delete it after it
lands.

## Current shape of the project (structural, changes rarely)

```text
Browser → ALB → ECS Fargate → RDS PostgreSQL, one FastAPI container.
Region us-west-2, one dedicated AWS Organizations member account.
GitHub OIDC only; no static AWS keys anywhere.

Terraform state levels — only the last two are ever destroyed:
  infra/bootstrap        S3 state bucket, local state, permanent
  infra/bootstrap-oidc   OIDC provider + deploy roles, permanent
  infra/public-site      dashboard S3+CloudFront, permanent   (Phase 11)
  infra/envs/stage       workload, destroyed every cycle
  infra/envs/prod        workload, destroyed every cycle      (Phase 9)

Anything that must survive a teardown — including the artifact that PROVES the
teardown works — belongs above the env levels.
```

## Known traps, current

```text
- infra/envs/prod is a stale Phase 4 scaffold. It still contains
  module "iam_github_oidc" (removed from stage by ADR-0015) and passes
  db_secret_arn where the module now takes db_secret_arn_pattern. Phase 9.0
  reconciles it. Do not build on it before that.
- terraform validate does not cover the whole infra/ tree. Fixed in Phase 9.0.
- destroy.yml offers a "prod" choice with nothing behind it.
- prod keeps no data between cycles, and app.<domain> is a dead link most of
  the time (ADR-0017 D2a). Say so; do not get caught by it.
```

## Language

Instructions, skills, code and documents in English. Discussion may be Russian.
