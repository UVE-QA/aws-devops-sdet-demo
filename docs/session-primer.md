# Session Primer

Read this first in any new session. It is a **pointer**, not a summary — it says
what to read, in what order, who does what, and what has burned us before. It
deliberately holds almost no state, so it does not go stale.

The cursor lives in `docs/phase-gates.md`. Nothing else claims to know the
current phase — including this file.

---

## How a session works

**Every session starts in a new chat.** The chat is the entry point and the
driver: it loads the current state, reports where the project is, then runs the
session — discussion, decisions, and step-by-step instructions. Execution
happens on the devbox.

```text
chat      DRIVES the session. Loads state, reports it, discusses, decides,
          authors documents, and issues commands one at a time, each labelled
          [mac] or [devbox]. It does not commit directly.
devbox    EXECUTES. Commands run there; files land there; git lives there.
you       the bridge between the two.
send.sh   delivery in one command (buffer → repo path → optional commit+push).
```

Optionally the chat can hand a task to a **Claude Code session on the devbox**
when the work is heavy file editing — that session reads `CLAUDE.md`, lands
here, and writes directly. Use it when a task touches many files; use the chat
for everything that needs thinking, planning, or judgement first.

What must never happen: the chat inventing state instead of loading it, or a
document reaching the repo without going through git.

## A. Loading state — chat session

Try to clone the repository into the session sandbox over HTTPS. The sandbox
reaches `github.com` over HTTPS; SSH out is blocked; pushing is not possible,
because that would need a token and asking for tokens is forbidden here.

- **Clone succeeds** → read the order in section B. Ignore the Project mirror.
- **Clone fails** → the repository is still private. Say so explicitly, fall
  back to the Project mirror files, and treat them as possibly stale — ask for
  `git -C ~/aws-devops-sdet-demo log --oneline -5` before relying on them.

This is not hypothetical: on 2026-07-25 the mirror was seven weeks stale, and
the control layer it described was not in the repository at all.

## B. Loading state — Claude Code on the devbox

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

## C. Closing a session

```text
- run the relevant validation
- update docs/phase-gates.md if the phase status changed
- write a summary in docs/sessions/ and add a row to INDEX.md
- record new structural decisions as ADRs
- commit and push; work is only shared once pushed
- leave the transfer buffer empty
```

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

## Delivering files from a chat to the repo

```text
mac:     ~/Projects/_claude-transfer/    buffer; should be empty almost always
devbox:  ~/aws-devops-sdet-demo/         the ONE working copy
github:  UVE-QA/aws-devops-sdet-demo     source of truth
ssh:     ssh devbox / scp file devbox:/tmp/

./send.sh <local-file> <repo/path> ["commit message"]
    without a message: delivers and shows git status, you commit after review
    with a message:    delivers, commits, pushes, clears the buffer copy
```

Anything sitting in the buffer has not been committed yet. The read half of
this disappears once the repository is public.

**The chat knows where its files are; you do not. So the chat supplies the
path.** A chat session writes into an outputs folder whose path contains that
session's own identifiers, so it is different in every chat and can never be
written down here. Immediately after authoring a file, and BEFORE any mention of
`send.sh`, the chat must emit a ready-to-run `[mac]` command that copies the
file from its current outputs folder into the buffer, with the full path already
substituted:

```text
cp "<the chat's own outputs path>/<file>" ~/Projects/_claude-transfer/
```

File cards in the chat are for reading the file, not for delivering it. Assuming
a card lands in the buffer by itself costs a round trip every time.

## Current shape of the project (structural, changes rarely)

```text
Browser → ALB → ECS Fargate → RDS PostgreSQL, one FastAPI container.
Region us-west-2, one dedicated AWS Organizations member account.
GitHub OIDC only; no static AWS keys anywhere.

Terraform state levels — only the last two are ever destroyed:
  infra/bootstrap        S3 state bucket, local state, permanent
  infra/bootstrap-oidc   OIDC provider + deploy roles, permanent
  infra/shared-ecr       container registry, permanent        (ADR-0018)
  infra/public-site      dashboard S3+CloudFront, permanent   (Phase 11)
  infra/envs/stage       workload, destroyed every cycle
  infra/envs/prod        workload, destroyed every cycle      (Phase 9)
```

Anything that must survive a teardown — including the artifact that PROVES the
teardown works — belongs above the env levels. The container registry was the
second thing to qualify and the first one nobody noticed: it only becomes
obvious once prod runs an image that stage's teardown would delete (ADR-0018).

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

This is the entry point. Paste it as the first message of a new chat, then
rename the chat per the naming convention above.

```text
AWS project session. You are the driver for this session.

First, load state. Try to clone
https://github.com/UVE-QA/aws-devops-sdet-demo into your sandbox over HTTPS
and read, in this order:
  docs/session-primer.md
  docs/phase-gates.md          (the cursor — the only file that knows the phase)
  docs/next-phases.md
  docs/decisions/              (newest first)
  docs/discussion-log.md       (top "Current state" block only)

If the clone fails the repo is still private: say so, fall back to the Claude
Project mirror files, treat them as possibly stale, and ask me to run
`git -C ~/aws-devops-sdet-demo log --oneline -5` before relying on them.

Then STOP and report: current phase, next allowed step, blockers. Propose what
this session should cover and wait for my confirmation.

Then run the session: discuss, decide, draft, and give me instructions.
- ONE command at a time, labelled [mac] or [devbox]. Wait for my real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next.
- Files you author go to the repo through ~/Projects/_claude-transfer and
  ./send.sh <file> <repo/path> ["commit message"]. You never commit directly.
- Explicit confirmation before any billable AWS action. Never ask for secrets.
- English for anything that lands in the repo or is pasted into a session;
  Russian is fine for discussion.

At the end, close the session properly: validation, phase-gates update, a
summary in docs/sessions/ with a row in INDEX.md, ADRs for new structural
decisions, commit and push, and an empty transfer buffer.
```

## Appendix — starter for a Claude Code session on the devbox

Use when the work is heavy file editing and the chat hands it over.

```text
New session. Read docs/session-primer.md, then docs/phase-gates.md,
docs/next-phases.md, and the newest ADRs.

Then STOP: state the current phase, the next allowed step, and any blockers.
Change nothing until I confirm.
```
