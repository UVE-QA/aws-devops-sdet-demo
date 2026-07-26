# Session Primer

Read this first in any new session. It is a **pointer**, not a summary — it says
what to read, in what order, who is allowed to write, and what has burned us
before. It deliberately holds almost no state, so it does not go stale.

The cursor lives in `docs/phase-gates.md`. Nothing else claims to know the
current phase — including this file.

---

## Roles: who reads, who writes

```text
Claude Code on the devbox   the ONLY writer. Reads and writes git natively,
                            commits and pushes. No manual transfer steps.
Chat / Cowork session       READ ONLY. Loads current state itself, thinks,
                            plans, drafts. Never commits.
Claude Project files        a mirror of last resort. Not a source.
Project memory              permanent identifiers only. Never status.
```

Text produced in a chat reaches the repo through a devbox session, not through
the chat. Every manual `scp` ritual this project has suffered came from a chat
trying to be a writer.

## A. Claude Code on the devbox (full repo access)

`CLAUDE.md` is read automatically and sends you here. Then:

```text
1. git pull
2. docs/phase-gates.md      the cursor: current phase, last validated step,
                            what is allowed next
3. docs/next-phases.md      the plan: MVP track 9-13, polish track 14-19.
                            Supersedes project-prompt.md §14.
4. docs/decisions/          the "why". Newest first; 0015, 0016, 0017 shape
                            everything currently in flight
5. docs/discussion-log.md   the narrative. Read the top "Current state" block;
                            go deeper only for history
6. docs/sessions/INDEX.md   only when you need a specific past session
```

Then STOP and state the phase, the next allowed step, and any blocker before
touching anything.

## B. Chat / Cowork session (no native repo access)

Try to clone the repository into the session sandbox over HTTPS. The sandbox
reaches `github.com` over HTTPS; SSH out is blocked; pushing is not possible
because it would require a token, and asking for tokens is forbidden here.

- **Clone succeeds** → read the same order as section A. You now have current
  state; do not use the Project mirror at all.
- **Clone fails** → the repository is still private. Say so explicitly. Fall
  back to the Project mirror files and treat them as possibly stale — ask for
  `git -C ~/aws-devops-sdet-demo log --oneline -5` before relying on them.

This is not hypothetical: on 2026-07-25 the mirror was seven weeks stale, and
the control layer it described was not in the repository at all.

---

## Working agreements

```text
- Phase gates are real. End of a phase: summary → validation → STOP →
  explicit confirmation. Do not advance without it.
- ONE command at a time. Not one block of three — one. Wait for real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next one.
- Label every command [mac] or [devbox]. The wrong host has already cost a
  wasted round trip.
- Explicit confirmation before ANY billable action. Review the plan first.
- Never ask for secrets. Account ids, ARNs, regions, repo names are fine;
  keys, tokens, passwords are not.
- Give one correct method, not options A/B.
- Prefer a checked-in patch script over a long interactive heredoc when editing
  long documents: it fails loudly and changes nothing on mismatch.
```

## Language

```text
English   everything that lands in the repository or is pasted into a session:
          docs, ADRs, skills, code, commit messages, startup prompts.
Russian   live discussion in chat only.
```

## Session naming

Auto-generated chat titles are derived from content and cannot be relied on.
Rename the chat manually right after the first reply.

```text
Phase <N>[.<sub>] — <topic>     phase work
Ops — <topic>                   maintenance outside the phases

Phase 9.0 — reconcile prod scaffold
Phase 11.0 — publish repository
Phase 12 — README, architecture, demo script
Ops — devbox maintenance
```

## Verification habits that keep paying off

```text
- "It looked finished" is the recurring failure mode here, not "it broke".
  Every serious bug so far was something never exercised on the path that
  would expose it.
- A claim about state is not state. Check git, check AWS, check the file —
  do not trust a document, including this one.
- After a teardown, confirm against the AWS CLI, not against Terraform state.
- A fix to a shared invariant goes to EVERY environment directory in the same
  commit, not only the one being exercised.
```

## The transfer workflow (while chats cannot write)

```text
mac:     ~/Projects/_claude-transfer/    buffer; should be empty almost always
         send.sh <file> <repo/path>      copies to the devbox, never commits
devbox:  ~/aws-devops-sdet-demo/         the ONE working copy
github:  UVE-QA/aws-devops-sdet-demo     source of truth
ssh:     ssh devbox / scp file devbox:/tmp/
```

Anything sitting in the buffer has not been committed yet. Delete it after it
lands. This whole section disappears once the repository is public and chats
load context themselves.

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
```

Anything that must survive a teardown — including the artifact that PROVES the
teardown works — belongs above the env levels.

## Known traps (verify against phase-gates.md; these get fixed and go stale)

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

---

## Appendix — paste-in starter for a new chat session

```text
AWS project session — CHAT SIDE, READ ONLY.
Session title: Phase <N> — <topic>

Try to clone https://github.com/UVE-QA/aws-devops-sdet-demo into your sandbox
over HTTPS. If it succeeds, read in this order:
  docs/session-primer.md
  docs/phase-gates.md          (the cursor — the only file that knows the phase)
  docs/next-phases.md
  docs/decisions/              (newest first; 0015, 0016, 0017 are live)
  docs/discussion-log.md       (top "Current state" block only)

If the clone fails, the repo is still private. Say so explicitly, fall back to
the Project mirror files, and treat them as possibly stale — ask me to run
`git -C ~/aws-devops-sdet-demo log --oneline -5` before relying on them.

Then STOP and report: current phase, next allowed step, blockers.

Rules for this chat:
- You READ. You do not write to the repo. Anything that changes files is done
  by Claude Code on the devbox.
- ONE command at a time, labelled [mac] or [devbox]. Wait for real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next.
- English for anything that lands in the repo or is pasted into a session.
  Russian is fine for live discussion.
- Never ask for secrets. Explicit confirmation before any billable action.
```

## Appendix — starter for a devbox session

```text
New session. Read docs/session-primer.md, then docs/phase-gates.md,
docs/next-phases.md, and the newest ADRs.

Then STOP: state the current phase, the next allowed step, and any blockers.
Change nothing until I confirm.
```
